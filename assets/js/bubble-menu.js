import { activateAnnotation, beginAnnotation, endAnnotation, layoutSidebar } from './sidebar.js'

const MARKS = [
  { name: 'bold', label: 'B', title: 'Bold', command: (chain) => chain.toggleBold() },
  { name: 'italic', label: 'I', title: 'Italic', command: (chain) => chain.toggleItalic() },
  { name: 'strike', label: 'S', title: 'Strike', command: (chain) => chain.toggleStrike() },
  { name: 'code', label: '<>', title: 'Code', command: (chain) => chain.toggleCode() },
]

const KINDS = [
  { kind: 'comment', label: 'Comment' },
  { kind: 'suggestion', label: 'Suggest' },
  { kind: 'question', label: 'Question' },
]

function button(className, text, title) {
  const el = document.createElement('button')
  el.type = 'button'
  el.className = className
  el.textContent = text
  el.title = title
  // The editor must keep its selection while the button takes the click.
  el.addEventListener('mousedown', (event) => event.preventDefault())
  return el
}

/**
 * Builds the floating format bar and appends it to the document body.
 *
 * Returns the bar element and a `sync` function that refreshes the pressed
 * state of the format buttons.
 */
export function createBubbleBar({ getEditor, docId = null, readOnly = false } = {}) {
  const element = document.createElement('div')
  element.className = 'bubble-menu'
  element.setAttribute('role', 'toolbar')
  element.setAttribute('aria-label', 'Text formatting')

  const markButtons = MARKS.map((mark) => {
    const el = button('bubble-menu__button', mark.label, mark.title)
    el.addEventListener('click', () => {
      const editor = getEditor()
      if (!editor) return
      mark.command(editor.chain().focus()).run()
    })
    element.append(el)
    return { mark, el }
  })

  if (!readOnly) {
    const divider = document.createElement('span')
    divider.className = 'bubble-menu__divider'
    divider.setAttribute('aria-hidden', 'true')
    element.append(divider)

    KINDS.forEach(({ kind, label }) => {
      const el = button('bubble-menu__button', label, `Add a ${label.toLowerCase()} annotation`)
      el.dataset.annotateKind = kind
      el.addEventListener('click', () => {
        annotate({ kind, getEditor, docId, element })
      })
      element.append(el)
    })
  }

  // The BubbleMenu plugin appends the bar on show and removes it on hide.
  // Appending it here would leave it visible before the first selection.
  element.style.visibility = 'hidden'

  const sync = () => {
    const editor = getEditor()
    if (!editor) return
    markButtons.forEach(({ mark, el }) => {
      el.classList.toggle('is-active', editor.isActive(mark.name))
    })
  }

  return { element, sync }
}

/**
 * Applies a new annotation mark to the selection and creates its record.
 *
 * Removes the mark again when the server call fails.
 */
async function annotate({ kind, getEditor, docId, element }) {
  const editor = getEditor()
  if (!editor || !docId) return

  const id = crypto.randomUUID()
  beginAnnotation(id)
  editor.chain().focus().setAnnotation({ id, kind }).run()

  const buttons = element.querySelectorAll('[data-annotate-kind]')
  buttons.forEach((el) => {
    el.disabled = true
  })

  try {
    const response = await fetch(`/documents/${encodeURIComponent(docId)}/annotations`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({ id, kind }),
    })
    if (!response.ok) throw new Error(`the server answered ${response.status}`)
    insertCard(await response.text(), id)
  } catch (error) {
    editor.chain().focus().unsetAnnotationById(id).run()
    window.alert(`Could not create the annotation: ${error.message}`)
  } finally {
    endAnnotation(id)
    buttons.forEach((el) => {
      el.disabled = false
    })
  }
}

/** Puts a freshly returned annotation card in the sidebar and activates it. */
function insertCard(html, id) {
  const sidebar = document.getElementById('sidebar')
  if (!sidebar) return

  const template = document.createElement('template')
  template.innerHTML = html.trim()
  const card = template.content.firstElementChild
  if (!card) return

  sidebar.append(card)
  window.htmx?.process(card)

  layoutSidebar()
  activateAnnotation(id, { scrollIntoView: false })
  card.querySelector('textarea')?.focus()
}
