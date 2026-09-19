const state = { passId: null, slug: null, filterOn: false }
const listeners = new Set()

let storageKey = null

function byId(id) {
  return document.getElementById(id)
}

function read() {
  if (!storageKey) return null
  try {
    const raw = window.localStorage.getItem(storageKey)
    return raw ? JSON.parse(raw) : null
  } catch (error) {
    console.error('Could not read the pass state', error)
    return null
  }
}

function write() {
  if (!storageKey) return
  try {
    window.localStorage.setItem(storageKey, JSON.stringify(state))
  } catch (error) {
    console.error('Could not store the pass state', error)
  }
}

/** The pass list in display order, from the select or from the panel rows. */
function options() {
  const select = byId('pass-select')
  if (select) {
    return Array.from(select.options).map((option) => ({
      passId: option.value,
      slug: option.dataset.slug || null,
    }))
  }
  const panel = byId('passes-panel')
  if (!panel) return []
  return Array.from(panel.querySelectorAll('.pass-row')).map((row) => ({
    passId: row.dataset.passId,
    slug: row.dataset.slug || null,
  }))
}

function announce() {
  listeners.forEach((listener) => {
    try {
      listener(getPassState())
    } catch (error) {
      console.error('A pass state listener failed', error)
    }
  })
}

function paint() {
  const select = byId('pass-select')
  if (select && state.passId && select.value !== state.passId) select.value = state.passId

  const filter = byId('pass-filter')
  if (filter) {
    filter.setAttribute('aria-pressed', String(state.filterOn))
    filter.classList.toggle('is-on', state.filterOn)
  }

  const panel = byId('passes-panel')
  panel?.querySelectorAll('.pass-row').forEach((row) => {
    row.classList.toggle('is-current', Boolean(state.passId) && row.dataset.passId === state.passId)
  })
}

function apply({ passId, slug, filterOn }, { store = true } = {}) {
  if (passId !== undefined) state.passId = passId || null
  if (slug !== undefined) state.slug = slug || null
  if (filterOn !== undefined) state.filterOn = Boolean(filterOn)
  paint()
  if (store) write()
  announce()
}

/** Picks a pass by id, taking its slug from the known pass list. */
function selectPass(passId) {
  if (!passId) return
  const known = options().find((option) => option.passId === passId)
  apply({ passId, slug: known ? known.slug : state.slug })
}

function stepPass(direction) {
  const list = options()
  if (!list.length) return
  const current = list.findIndex((option) => option.passId === state.passId)
  const next = (current + direction + list.length) % list.length
  apply(list[next])
}

/** Copies the panel counts into the toolbar and re-marks the current row. */
function syncPanel() {
  const panel = byId('passes-panel')
  const counter = byId('pass-run-count')
  if (panel && counter) {
    const root = panel.querySelector('[data-run-count]') || panel
    const runs = root.dataset.runCount
    const passes = root.dataset.passCount
    counter.textContent = runs === undefined || passes === undefined ? '' : `${runs} / ${passes} run`
  }

  const list = options()
  if (!state.passId && list.length) {
    apply(list[0], { store: false })
    return
  }
  // A stored pass keeps its slug once the rows name it.
  const known = list.find((option) => option.passId === state.passId)
  if (known && known.slug && known.slug !== state.slug) {
    apply({ slug: known.slug }, { store: false })
    return
  }
  paint()
}

/** The pass the writer is on, and whether the sidebar filter is on. */
export function getPassState() {
  return { passId: state.passId, slug: state.slug, filterOn: state.filterOn }
}

/**
 * Calls `cb` with the pass state now and after every change.
 *
 * @param {(state: {passId: string|null, slug: string|null, filterOn: boolean}) => void} cb
 * @returns {() => void} unsubscribes
 */
export function onChange(cb) {
  listeners.add(cb)
  cb(getPassState())
  return () => listeners.delete(cb)
}

/**
 * Wires the pass toolbar, the passes panel, and the stored pass choice.
 *
 * @param {{docId?: string|null}} [options]
 * @returns {boolean} false when the page has no pass controls
 */
export function mountPasses({ docId = null } = {}) {
  const select = byId('pass-select')
  const panel = byId('passes-panel')
  const toggle = byId('passes-toggle')
  if (!select && !panel && !toggle) return false

  storageKey = docId ? `workshop:pass:${docId}` : null

  const stored = read()
  const list = options()
  const known = stored && list.find((option) => option.passId === stored.passId)
  // With no list yet the stored choice stands, so a late panel load keeps it.
  const fallback = list[0] || { passId: stored?.passId ?? null, slug: stored?.slug ?? null }
  apply(
    {
      passId: known ? known.passId : fallback.passId,
      slug: known ? known.slug : fallback.slug,
      filterOn: Boolean(stored?.filterOn),
    },
    { store: false },
  )

  select?.addEventListener('change', () => selectPass(select.value))
  byId('pass-prev')?.addEventListener('click', () => stepPass(-1))
  byId('pass-next')?.addEventListener('click', () => stepPass(1))

  byId('pass-filter')?.addEventListener('click', () => {
    apply({ filterOn: !state.filterOn })
  })

  toggle?.addEventListener('click', () => {
    if (!panel) return
    panel.hidden = !panel.hidden
    toggle.setAttribute('aria-expanded', String(!panel.hidden))
  })

  if (panel) {
    panel.addEventListener('click', (event) => {
      const row = event.target.closest?.('.pass-row')
      if (!row || !panel.contains(row)) return
      apply({ passId: row.dataset.passId, slug: row.dataset.slug || null })
    })
    panel.addEventListener('htmx:afterSwap', syncPanel)
    panel.addEventListener('htmx:afterSettle', syncPanel)
    syncPanel()
  }

  return true
}
