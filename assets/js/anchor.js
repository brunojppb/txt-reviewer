// Paragraph numbering mirrors app/text.py. A change here needs the same change
// there, or the agent and the browser disagree about paragraph numbers.

const LIST_TYPES = new Set(['bulletList', 'orderedList'])

const STRAIGHT_QUOTES = {
  '‘': "'",
  '’': "'",
  '‚': "'",
  '‛': "'",
  '′': "'",
  '“': '"',
  '”': '"',
  '„': '"',
  '‟': '"',
  '″': '"',
}

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

/** Collapses whitespace, straightens quotes, lowercases, and maps back. */
function normalize(text) {
  const out = []
  const map = []
  let lastWasSpace = false

  for (let i = 0; i < text.length; i += 1) {
    const char = text[i]
    if (/\s/.test(char)) {
      if (lastWasSpace) continue
      lastWasSpace = true
      out.push(' ')
      map.push(i)
      continue
    }
    lastWasSpace = false
    const straight = STRAIGHT_QUOTES[char] || char
    const lower = straight.toLowerCase()
    out.push(lower.length === 1 ? lower : straight)
    map.push(i)
  }

  return { text: out.join(''), map }
}

/** Turns a text range inside one paragraph into a document range. */
function rangeOf(segments, start, end) {
  let offset = 0
  let from = null
  let to = null

  for (const segment of segments) {
    const segmentStart = offset
    const segmentEnd = offset + segment.text.length
    if (from === null && start >= segmentStart && start < segmentEnd) {
      from = segment.from + (start - segmentStart)
    }
    if (to === null && end > segmentStart && end <= segmentEnd) {
      to = segment.from + (end - segmentStart)
    }
    offset = segmentEnd
  }

  return from !== null && to !== null && to > from ? { from, to } : null
}

function findExact(paragraph, quote) {
  const index = paragraph.text.indexOf(quote)
  if (index < 0) return null
  return rangeOf(paragraph.segments, index, index + quote.length)
}

function findNormalized(paragraph, quote) {
  const needle = normalize(quote).text.trim()
  if (!needle) return null

  const hay = normalize(paragraph.text)
  const index = hay.text.indexOf(needle)
  if (index < 0) return null

  const start = hay.map[index]
  const end = hay.map[index + needle.length - 1] + 1
  return rangeOf(paragraph.segments, start, end)
}

function search(paragraphs, named, quote) {
  const order = [
    () => (named ? findExact(named, quote) : null),
    () => (named ? findNormalized(named, quote) : null),
    () => paragraphs.reduce((hit, p) => hit || findExact(p, quote), null),
    () => paragraphs.reduce((hit, p) => hit || findNormalized(p, quote), null),
  ]

  for (const attempt of order) {
    const hit = attempt()
    if (hit) return hit
  }
  return null
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
