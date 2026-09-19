// Paragraph numbering mirrors app/text.py. A change here needs the same change
// there, or the agent and the browser disagree about paragraph numbers.

import { search } from './quote-search.js'

const LIST_TYPES = new Set(['bulletList', 'orderedList'])

/** Text and text-offset-to-position map of one block. */
function gather(node, nodePos) {
  const segments = []
  let text = ''

  node.descendants((child, offset) => {
    // A child's content starts one position after the node that holds it.
    const from = nodePos + 1 + offset
    if (child.isText) {
      segments.push({ from, text: child.text })
      text += child.text
      return false
    }
    if (child.type.name === 'hardBreak') {
      segments.push({ from, text: ' ' })
      text += ' '
      return false
    }
    return true
  })

  return { text, segments }
}

/**
 * Numbers the paragraphs of a TipTap document.
 *
 * @param {import('@tiptap/pm/model').Node} doc
 * @returns {Array<{n: number, node: object, pos: number, text: string,
 *   segments: Array<{from: number, text: string}>}>}
 */
export function paragraphsOf(doc) {
  const paragraphs = []
  if (!doc) return paragraphs
  let n = 0

  doc.forEach((block, offset) => {
    if (LIST_TYPES.has(block.type.name)) {
      block.forEach((item, itemOffset) => {
        const pos = offset + 1 + itemOffset
        n += 1
        paragraphs.push({ n, node: item, pos, ...gather(item, pos) })
      })
      return
    }
    n += 1
    paragraphs.push({ n, node: block, pos: offset, ...gather(block, offset) })
  })

  return paragraphs
}

/** True when the document already carries a mark with this annotation id. */
function alreadyMarked(doc, id) {
  let found = false
  doc.descendants((node) => {
    if (found) return false
    if (!node.isText) return true
    found = node.marks.some((mark) => mark.type.name === 'annotation' && mark.attrs.id === id)
    return false
  })
  return found
}

/**
 * Puts the annotation mark of one finding on its quote.
 *
 * @param {import('@tiptap/core').Editor} editor
 * @param {{id: string, quote: string, paragraph?: number, pass_slug?: string}} finding
 * @returns {boolean} true when the quote was found
 */
export function anchorFinding(editor, finding) {
  const view = editor?.view
  const markType = editor?.state?.schema?.marks?.annotation
  const quote = finding?.quote
  if (!view || !markType || !finding?.id || !quote) return false

  const { doc } = editor.state
  if (alreadyMarked(doc, finding.id)) return true

  const paragraphs = paragraphsOf(doc)
  const named = paragraphs.find((p) => p.n === finding.paragraph) || null
  const hit = search(paragraphs, named, quote)
  if (!hit) return false

  const attrs = {
    id: finding.id,
    kind: 'finding',
    pass: finding.pass_slug ?? finding.pass ?? null,
  }

  const tr = editor.state.tr
  tr.addMark(hit.from, hit.to, markType.create(attrs))
  // Anchoring is the agent's work, not the writer's, so undo must skip it.
  tr.setMeta('addToHistory', false)
  view.dispatch(tr)
  return true
}
