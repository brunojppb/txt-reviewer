import { findExact, findNormalized } from './quote-search.js'
import { scheduleLayout } from './sidebar.js'

const state = { editor: null, sidebar: null }

/** Returns the span an annotation's mark covers, or null when it has none. */
export function markRange(doc, id) {
  let from = null
  let to = null
  doc.descendants((node, pos) => {
    if (!node.isText) return true
    const holds = node.marks.some(
      (mark) => mark.type.name === 'annotation' && mark.attrs.id === id,
    )
    if (!holds) return false
    if (from === null || pos < from) from = pos
    if (to === null || pos + node.nodeSize > to) to = pos + node.nodeSize
    return false
  })
  return from === null ? null : { from, to }
}

/** Text of a span with the map back to document positions. */
function blockOf(doc, from, to) {
  const segments = []
  let text = ''
  doc.nodesBetween(from, to, (node, pos) => {
    if (!node.isText) return true
    const start = Math.max(pos, from)
    const end = Math.min(pos + node.nodeSize, to)
    if (end <= start) return false
    const slice = node.text.slice(start - pos, end - pos)
    segments.push({ from: start, text: slice })
    text += slice
    return false
  })
  return { text, segments }
}

/**
 * Finds the words an edit names, inside the quote of its finding.
 *
 * @returns {{from: number, to: number} | null} null when the writer changed them
 */
export function findTarget(editor, annotationId, target) {
  const doc = editor?.state?.doc
  if (!doc || !annotationId || !target) return null
  const span = markRange(doc, annotationId)
  if (!span) return null
  const block = blockOf(doc, span.from, span.to)
  return findExact(block, target) || findNormalized(block, target)
}

/** Widens a cut by one neighbouring space so two words do not collide. */
function cutRange(doc, range) {
  const before = range.from > 0 ? doc.textBetween(range.from - 1, range.from) : ''
  if (before === ' ') return { from: range.from - 1, to: range.to }
  const end = Math.min(doc.content.size, range.to + 1)
  const after = end > range.to ? doc.textBetween(range.to, end) : ''
  if (after === ' ') return { from: range.from, to: end }
  return range
}

/**
 * Replaces a span with the wording of an edit. An empty replacement cuts it.
 *
 * @returns {boolean} true when the editor took the change
 */
export function applyEdit(editor, range, replacement) {
  const { state: editorState, view } = editor
  const { doc } = editorState
  if (!replacement) {
    const span = cutRange(doc, range)
    view.dispatch(editorState.tr.delete(span.from, span.to))
    return true
  }
  // The new words stay inside the highlight, so the finding keeps one span
  // while its other edits wait.
  const marks = doc.resolve(range.from + 1).marks()
  view.dispatch(
    editorState.tr.replaceWith(
      range.from,
      range.to,
      editorState.schema.text(replacement, marks),
    ),
  )
  return true
}

/** Dims a row whose words the writer already changed, or restores it. */
function setDrifted(row, drifted) {
  row.classList.toggle('is-drifted', drifted)
  const button = row.querySelector('.annotation-edit__accept')
  if (!button) return
  button.disabled = drifted
  button.textContent = drifted ? 'text changed' : 'Accept'
}

/**
 * Dims every row whose words the editor can no longer find.
 *
 * A finding that never anchored has no span to search, so all of its rows
 * dim. Undo can make a row findable again, so this restores as well.
 */
export function refreshRows() {
  if (!state.sidebar || !state.editor) return
  state.sidebar.querySelectorAll('.annotation-edit').forEach((row) => {
    const annotationId = row.closest('.annotation-card')?.dataset.annotationId
    const found = Boolean(findTarget(state.editor, annotationId, row.dataset.target))
    setDrifted(row, !found)
  })
}

async function accept(row) {
  const card = row.closest('.annotation-card')
  const annotationId = card?.dataset.annotationId
  const editId = row.dataset.editId
  if (!card || !annotationId || !editId) return

  const range = findTarget(state.editor, annotationId, row.dataset.target)
  if (!range) {
    setDrifted(row, true)
    return
  }

  applyEdit(state.editor, range, row.dataset.replacement || '')

  try {
    const response = await fetch(
      `/annotations/${encodeURIComponent(annotationId)}/edits/${encodeURIComponent(editId)}/applied`,
      { method: 'POST' },
    )
    if (!response.ok) throw new Error(`the server answered ${response.status}`)
    const html = (await response.text()).trim()
    if (html) {
      card.outerHTML = html
      refreshRows()
    } else {
      // No edit is left, so the server filed the finding and the mark goes.
      state.editor?.commands.unsetAnnotationById(annotationId)
      card.remove()
      document.body.dispatchEvent(
        new CustomEvent('annotation:closed', { detail: { id: annotationId } }),
      )
    }
  } catch (error) {
    console.error('Could not record the edit', error)
  }
  scheduleLayout()
}

function onClick(event) {
  const button = event.target.closest('.annotation-edit__accept')
  if (!button || button.disabled) return
  const row = button.closest('.annotation-edit')
  if (row) accept(row)
}

/**
 * Wires the Accept button of every edit row in the sidebar.
 *
 * @param {object} options
 * @param {import('@tiptap/core').Editor} options.editor
 * @returns {() => void} stops the wiring
 */
export function mountEdits({ editor }) {
  const sidebar = document.getElementById('sidebar')
  if (!sidebar || !editor) return () => {}

  state.editor = editor
  state.sidebar = sidebar
  sidebar.addEventListener('click', onClick)
  // New cards arrive through htmx swaps and through the polling in changes.js.
  sidebar.addEventListener('htmx:afterSettle', refreshRows)
  refreshRows()

  return () => {
    sidebar.removeEventListener('click', onClick)
    sidebar.removeEventListener('htmx:afterSettle', refreshRows)
  }
}
