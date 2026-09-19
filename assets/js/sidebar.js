const GAP = 8

const state = {
  editor: null,
  editorElement: null,
  sidebar: null,
  activeId: null,
  order: [],
  resolved: [],
}

let frame = 0

// Ids whose card is on its way from the server. Layout must not invent an
// orphan card for them in the meantime.
const pending = new Set()

/** Runs layoutSidebar once on the next animation frame. */
function scheduleLayout() {
  if (frame) return
  frame = requestAnimationFrame(() => {
    frame = 0
    layoutSidebar()
  })
}

function marksFor(id) {
  if (!state.editorElement) return []
  return Array.from(
    state.editorElement.querySelectorAll(`mark[data-annotation-id="${CSS.escape(id)}"]`),
  )
}

function cardFor(id) {
  if (!state.sidebar) return null
  return state.sidebar.querySelector(
    `.annotation-card[data-annotation-id="${CSS.escape(id)}"]`,
  )
}

/** First mark element per annotation id, in document order. */
function collectMarks() {
  const found = new Map()
  const nodes = state.editorElement.querySelectorAll('mark[data-annotation-id]')
  nodes.forEach((node) => {
    const id = node.dataset.annotationId
    if (id && !found.has(id)) found.set(id, node)
  })
  return found
}

/** Tells the sidebar that a card for this id is on its way. */
export function beginAnnotation(id) {
  pending.add(id)
}

/** Tells the sidebar that the card arrived, or that the attempt failed. */
export function endAnnotation(id) {
  pending.delete(id)
}

function buildOrphanCard(id, kind) {
  const card = document.createElement('article')
  card.className = 'annotation-card is-orphan'
  card.dataset.annotationId = id
  card.dataset.kind = kind
  card.dataset.orphan = 'true'

  const badge = document.createElement('span')
  badge.className = `annotation-badge annotation-badge--${kind}`
  badge.textContent = kind
  card.append(badge)

  const note = document.createElement('p')
  note.className = 'annotation-card__note'
  note.textContent = 'No annotation record'
  card.append(note)

  const remove = document.createElement('button')
  remove.type = 'button'
  remove.className = 'annotation-card__delete'
  remove.dataset.removeMark = id
  remove.textContent = 'Delete highlight'
  card.append(remove)

  return card
}

/** Adds the "highlight removed" note to a card whose mark is gone. */
function markDetached(card) {
  card.classList.add('is-detached')
  if (card.querySelector('[data-detached-note]')) return
  const note = document.createElement('p')
  note.className = 'annotation-card__note'
  note.dataset.detachedNote = 'true'
  note.textContent = 'highlight removed'
  card.append(note)
}

function clearDetached(card) {
  card.classList.remove('is-detached')
  card.querySelector('[data-detached-note]')?.remove()
}

function topWithin(element, container) {
  return element.getBoundingClientRect().top - container.getBoundingClientRect().top
}

function updateCounter() {
  const counter = document.getElementById('annotation-counter')
  if (!counter) return
  const total = state.order.length
  const index = state.activeId ? state.order.indexOf(state.activeId) : -1
  counter.textContent = `${index >= 0 ? index + 1 : 0} / ${total}`
}

/**
 * Places every annotation card next to its highlight and sizes the sidebar.
 *
 * Cards that would overlap move down. Cards without a highlight, and
 * highlights without a card, get their own treatment.
 */
export function layoutSidebar() {
  if (!state.sidebar || !state.editorElement) return

  const marks = collectMarks()
  const cards = Array.from(state.sidebar.querySelectorAll('.annotation-card[data-annotation-id]'))

  const byId = new Map()
  cards.forEach((card) => {
    const id = card.dataset.annotationId
    const kept = byId.get(id)
    if (!kept) {
      byId.set(id, card)
      return
    }
    // A real record always replaces a generated orphan card.
    const loser = kept.dataset.orphan ? kept : card
    loser.remove()
    byId.set(id, loser === kept ? card : kept)
  })

  // A highlight with no record gets a generated card.
  marks.forEach((mark, id) => {
    if (byId.has(id) || pending.has(id)) return
    const card = buildOrphanCard(id, mark.dataset.kind || 'comment')
    state.sidebar.append(card)
    byId.set(id, card)
  })

  const detached = []
  const resolved = []
  byId.forEach((card, id) => {
    if (card.dataset.status === 'resolved') resolved.push(id)
    if (marks.has(id)) {
      clearDetached(card)
    } else if (!card.dataset.orphan) {
      markDetached(card)
      detached.push(id)
    }
  })

  // Orphan cards whose mark disappeared have nothing left to point at.
  byId.forEach((card, id) => {
    if (card.dataset.orphan && !marks.has(id)) {
      card.remove()
      byId.delete(id)
    }
  })

  state.order = [...marks.keys(), ...detached]

  let bottom = 0
  state.order.forEach((id) => {
    const card = byId.get(id)
    if (!card) return
    const mark = marks.get(id)
    const natural = mark ? topWithin(mark, state.sidebar) : bottom
    const top = Math.max(natural, bottom)
    card.style.top = `${top}px`
    bottom = top + card.offsetHeight + GAP
  })

  state.sidebar.style.height = `${Math.max(bottom - GAP, 0)}px`

  if (state.activeId && !state.order.includes(state.activeId)) {
    state.activeId = null
  }
  state.resolved = resolved
  paintActive()
  updateCounter()
}

function paintActive() {
  state.sidebar
    ?.querySelectorAll('.annotation-card.is-active')
    .forEach((card) => card.classList.remove('is-active'))
  if (state.activeId) cardFor(state.activeId)?.classList.add('is-active')

  // Mark styling goes through the editor so ProseMirror does not redraw it away.
  state.editor?.commands.setAnnotationState({
    activeId: state.activeId,
    resolved: state.resolved,
  })
}

/**
 * Makes one annotation the active one on both its highlight and its card.
 *
 * @param {string} id
 * @param {{scrollIntoView?: boolean}} [options]
 */
export function activateAnnotation(id, { scrollIntoView = true } = {}) {
  state.activeId = id
  paintActive()
  updateCounter()

  if (!scrollIntoView) return
  const mark = marksFor(id)[0]
  if (!mark) return
  const rect = mark.getBoundingClientRect()
  const offscreen = rect.top < 0 || rect.bottom > window.innerHeight
  if (offscreen) mark.scrollIntoView({ block: 'center', behavior: 'smooth' })
}

function step(direction) {
  const total = state.order.length
  if (!total) return
  const current = state.activeId ? state.order.indexOf(state.activeId) : -1
  const next =
    current < 0
      ? direction > 0
        ? 0
        : total - 1
      : (current + direction + total) % total
  activateAnnotation(state.order[next])
}

function onEditorClick(event) {
  const mark = event.target.closest?.('mark[data-annotation-id]')
  if (!mark) return
  activateAnnotation(mark.dataset.annotationId, { scrollIntoView: false })
}

function onSidebarClick(event) {
  const remove = event.target.closest?.('[data-remove-mark]')
  if (remove) {
    removeMark(remove.dataset.removeMark)
    return
  }
  const card = event.target.closest?.('.annotation-card[data-annotation-id]')
  if (!card) return
  // Activation must not pull focus out of the card's own textarea or buttons.
  activateAnnotation(card.dataset.annotationId, { scrollIntoView: false })
}

function removeMark(id) {
  if (!id) return
  state.editor?.commands.unsetAnnotationById(id)
  cardFor(id)?.remove()
  scheduleLayout()
}

function onKeydown(event) {
  if (!event.altKey) return
  if (event.key !== 'ArrowDown' && event.key !== 'ArrowUp') return

  const tag = document.activeElement?.tagName
  if (tag === 'TEXTAREA' || tag === 'INPUT') return

  event.preventDefault()
  step(event.key === 'ArrowDown' ? 1 : -1)
}

function onAnnotationDeleted(event) {
  const id = event.detail?.id ?? event.detail?.value?.id
  if (!id) return
  state.editor?.commands.unsetAnnotationById(id)
  if (state.activeId === id) state.activeId = null
  scheduleLayout()
}

/**
 * Wires the annotation sidebar: card placement, active state, prev and next.
 *
 * @param {object} options
 * @param {import('@tiptap/core').Editor} options.editor
 * @param {HTMLElement} options.editorElement the mounted editor element
 * @returns {boolean} false when the page has no sidebar
 */
export function mountSidebar({ editor, editorElement }) {
  const sidebar = document.getElementById('sidebar')
  if (!sidebar || !editorElement) return false

  state.editor = editor
  state.editorElement = editorElement
  state.sidebar = sidebar

  editorElement.addEventListener('click', onEditorClick)
  sidebar.addEventListener('click', onSidebarClick)
  document.addEventListener('keydown', onKeydown)

  document.getElementById('annotation-prev')?.addEventListener('click', () => step(-1))
  document.getElementById('annotation-next')?.addEventListener('click', () => step(1))

  sidebar.addEventListener('htmx:afterSwap', scheduleLayout)
  sidebar.addEventListener('htmx:afterSettle', scheduleLayout)
  document.body.addEventListener('annotation:deleted', onAnnotationDeleted)

  window.addEventListener('resize', scheduleLayout)
  new ResizeObserver(scheduleLayout).observe(editorElement)

  scheduleLayout()
  return true
}

export { scheduleLayout }
