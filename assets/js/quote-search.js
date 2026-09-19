// Finds a quote inside a block of text and maps the hit back to document
// positions. anchor.js uses it for a finding's quote, edits.js for an edit's
// target inside that quote.

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

/** Collapses whitespace, straightens quotes, lowercases, and maps back. */
export function normalize(text) {
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
export function rangeOf(segments, start, end) {
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

/** Finds a quote inside a block by exact text match. */
export function findExact(block, quote) {
  const index = block.text.indexOf(quote)
  if (index < 0) return null
  return rangeOf(block.segments, index, index + quote.length)
}

/** Finds a quote inside a block after normalizing both. */
export function findNormalized(block, quote) {
  const needle = normalize(quote).text.trim()
  if (!needle) return null

  const hay = normalize(block.text)
  const index = hay.text.indexOf(needle)
  if (index < 0) return null

  const start = hay.map[index]
  const end = hay.map[index + needle.length - 1] + 1
  return rangeOf(block.segments, start, end)
}

/** Searches for a quote across paragraphs, trying exact then normalized matches. */
export function search(paragraphs, named, quote) {
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
