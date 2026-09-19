import { Extension } from '@tiptap/core'

const ITEMS = [
  { label: 'Text', keywords: 'paragraph body', run: (chain) => chain.setParagraph() },
  { label: 'Heading 1', keywords: 'h1 title', run: (chain) => chain.setNode('heading', { level: 1 }) },
  { label: 'Heading 2', keywords: 'h2', run: (chain) => chain.setNode('heading', { level: 2 }) },
  { label: 'Heading 3', keywords: 'h3', run: (chain) => chain.setNode('heading', { level: 3 }) },
  { label: 'Bullet list', keywords: 'ul unordered', run: (chain) => chain.toggleBulletList() },
  { label: 'Numbered list', keywords: 'ol ordered', run: (chain) => chain.toggleOrderedList() },
  { label: 'Quote', keywords: 'blockquote', run: (chain) => chain.toggleBlockquote() },
  { label: 'Code block', keywords: 'pre monospace', run: (chain) => chain.toggleCodeBlock() },
  { label: 'Divider', keywords: 'hr rule horizontal', run: (chain) => chain.setHorizontalRule() },
]

/** Reads the slash query under the caret, or null when the menu must stay shut. */
function readQuery(editor) {
  const { selection } = editor.state
  if (!selection.empty) return null

  const { $from } = selection
  if ($from.parent.type.name !== 'paragraph') return null

  const text = $from.parent.textContent
  if (!text.startsWith('/')) return null

  // The caret must sit at the end of the slash text.
  if ($from.parentOffset !== text.length) return null

  const query = text.slice(1)
  return /\s/.test(query) ? null : query
}

function matches(query) {
  const needle = query.trim().toLowerCase()
  if (!needle) return ITEMS
  return ITEMS.filter(
    (item) =>
      item.label.toLowerCase().includes(needle) || item.keywords.includes(needle),
  )
}

function createElement() {
  const element = document.createElement('div')
  element.className = 'slash-menu'
  element.setAttribute('role', 'listbox')
  element.hidden = true
  document.body.append(element)
  return element
}

function close(storage) {
  storage.open = false
  storage.items = []
  storage.index = 0
  if (storage.element) storage.element.hidden = true
}

/** Replaces the slash text with the chosen block. */
function apply(editor, item) {
  const { $from } = editor.state.selection
  const from = $from.start()
  const to = $from.pos
  item.run(editor.chain().focus().deleteRange({ from, to })).run()
}

function render(editor, storage) {
  const element = storage.element
  element.replaceChildren()

  if (!storage.items.length) {
    const empty = document.createElement('p')
    empty.className = 'slash-menu__empty'
    empty.textContent = 'No blocks match'
    element.append(empty)
    return
  }

  storage.items.forEach((item, index) => {
    const button = document.createElement('button')
    button.type = 'button'
    button.className = 'slash-menu__item'
    button.textContent = item.label
    button.setAttribute('role', 'option')
    button.setAttribute('aria-selected', String(index === storage.index))
    button.classList.toggle('is-selected', index === storage.index)
    button.addEventListener('mousedown', (event) => event.preventDefault())
    button.addEventListener('click', () => {
      close(storage)
      apply(editor, item)
    })
    element.append(button)
  })
}

function position(editor, storage) {
  const coords = editor.view.coordsAtPos(editor.state.selection.from)
  storage.element.style.left = `${coords.left + window.scrollX}px`
  storage.element.style.top = `${coords.bottom + window.scrollY + 6}px`
}

function refresh(editor, storage) {
  if (!storage.element || !editor.isEditable) return

  const query = readQuery(editor)
  if (query === null) {
    close(storage)
    return
  }

  const items = matches(query)
  storage.open = true
  storage.query = query
  storage.items = items
  storage.index = Math.min(storage.index, Math.max(items.length - 1, 0))
  storage.element.hidden = false
  render(editor, storage)
  position(editor, storage)
}

/**
 * Notion-style block menu that opens when the writer types `/` in an empty
 * paragraph.
 */
export const SlashMenu = Extension.create({
  name: 'slashMenu',

  addStorage() {
    return { open: false, query: '', items: [], index: 0, element: null }
  },

  onCreate() {
    this.storage.element = createElement()
  },

  onUpdate() {
    refresh(this.editor, this.storage)
  },

  onSelectionUpdate() {
    refresh(this.editor, this.storage)
  },

  onBlur() {
    close(this.storage)
  },

  onDestroy() {
    this.storage.element?.remove()
    this.storage.element = null
  },

  addKeyboardShortcuts() {
    const move = (step) => {
      const { storage, editor } = this
      if (!storage.open || !storage.items.length) return false
      const count = storage.items.length
      storage.index = (storage.index + step + count) % count
      render(editor, storage)
      return true
    }

    return {
      ArrowDown: () => move(1),
      ArrowUp: () => move(-1),
      Enter: () => {
        const { storage, editor } = this
        if (!storage.open) return false
        const item = storage.items[storage.index]
        close(storage)
        if (!item) return true
        apply(editor, item)
        return true
      },
      Escape: () => {
        if (!this.storage.open) return false
        close(this.storage)
        return true
      },
    }
  },
})

export default SlashMenu
