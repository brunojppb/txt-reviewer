import { anchorFinding } from './anchor.js'

const POLL_DELAY = 3000
const SLOW_DELAY = 10000
const FAILURE_LIMIT = 3

/** Fires an htmx event on an element, when both exist. */
function trigger(target, name) {
  const element = typeof target === 'string' ? document.querySelector(target) : target
  if (element && window.htmx) window.htmx.trigger(element, name)
}

async function getJSON(url) {
  const response = await fetch(url, { headers: { Accept: 'application/json' } })
  if (!response.ok) throw new Error(`the server answered ${response.status}`)
  return response.json()
}

/** Tells the server whether the browser found the quote. */
async function reportAnchored(id, anchored) {
  await fetch(`/annotations/${encodeURIComponent(id)}/anchored`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({ anchored: anchored ? '1' : '0' }),
  })
}

/**
 * Polls the document for agent changes and anchors new findings.
 *
 * @param {object} options
 * @param {import('@tiptap/core').Editor} options.editor
 * @param {string} options.docId
 * @param {boolean} [options.readOnly] skip polling on a revision page
 * @returns {() => void} stops the polling
 */
export function mountChanges({ editor, docId, readOnly = false }) {
  if (readOnly || !editor || !docId) return () => {}

  const base = `/documents/${encodeURIComponent(docId)}`
  let seq = null
  let failures = 0
  let timer = 0
  let running = false
  let stopped = false

  async function anchorNewFindings() {
    const findings = await getJSON(`${base}/findings/unanchored`)
    const list = Array.isArray(findings) ? findings : []
    for (const finding of list) {
      const anchored = anchorFinding(editor, finding)
      await reportAnchored(finding.id, anchored)
    }
    trigger('#sidebar', 'refresh')
    trigger(document.body, 'changes')
  }

  async function poll() {
    if (running || document.visibilityState !== 'visible') return
    running = true
    try {
      const data = await getJSON(`${base}/changes`)
      const next = data?.seq ?? 0
      const changed = seq === null || next !== seq
      seq = next
      if (changed) await anchorNewFindings()
      failures = 0
    } catch (error) {
      failures += 1
      console.error('Could not read the document changes', error)
    } finally {
      running = false
    }
  }

  function schedule() {
    if (stopped) return
    window.clearTimeout(timer)
    const delay = failures >= FAILURE_LIMIT ? SLOW_DELAY : POLL_DELAY
    timer = window.setTimeout(async () => {
      await poll()
      schedule()
    }, delay)
  }

  function onVisibility() {
    if (document.visibilityState !== 'visible') return
    poll().then(schedule)
  }

  document.addEventListener('visibilitychange', onVisibility)
  poll().then(schedule)

  return () => {
    stopped = true
    window.clearTimeout(timer)
    document.removeEventListener('visibilitychange', onVisibility)
  }
}
