import { createEditor } from './editor.js'
import { mountSidebar, scheduleLayout } from './sidebar.js'
import { mountPasses } from './passes.js'
import { mountChanges } from './changes.js'

const SAVE_DELAY = 800

/** Reads the JSON the page embeds in `#doc-data`. */
function readDocData() {
  const node = document.getElementById('doc-data')
  if (!node) return null
  try {
    return JSON.parse(node.textContent || '{}')
  } catch (error) {
    console.error('Could not read #doc-data', error)
    return null
  }
}

function parseContent(content) {
  if (typeof content !== 'string') return content || undefined
  try {
    return JSON.parse(content)
  } catch (error) {
    console.error('Could not read the document content', error)
    return undefined
  }
}

/** Writes the editor word count into `#word-count`. */
function updateWordCount(editor) {
  const node = document.getElementById('word-count')
  if (!node) return
  const words = editor.getText().split(/\s+/).filter(Boolean).length
  node.textContent = `${words.toLocaleString('en-US')} words`
}

function setStatus(text) {
  const node = document.getElementById('save-status')
  if (node) node.textContent = text
}

/** Saves the content 800 ms after the last change. */
function createAutosave(docId) {
  let timer = 0

  return (editor) => {
    window.clearTimeout(timer)
    setStatus('Saving…')
    timer = window.setTimeout(async () => {
      try {
        const response = await fetch(`/documents/${encodeURIComponent(docId)}/content`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ content: editor.getJSON() }),
        })
        if (!response.ok) throw new Error(`the server answered ${response.status}`)
        setStatus('Saved')
      } catch (error) {
        console.error('Autosave failed', error)
        setStatus('Save failed')
      }
    }, SAVE_DELAY)
  }
}

function boot() {
  const data = readDocData()
  const element = document.getElementById('editor')
  if (!data || !element) return

  const readOnly = Boolean(data.read_only ?? data.readOnly ?? element.dataset.readOnly === 'true')
  const docId = data.id ?? data.document_id ?? null
  const save = readOnly || !docId ? null : createAutosave(docId)

  const editor = createEditor({
    element,
    content: parseContent(data.content),
    readOnly,
    docId,
    onUpdate: (instance) => {
      scheduleLayout()
      updateWordCount(instance)
      save?.(instance)
    },
  })

  updateWordCount(editor)
  mountPasses({ docId })
  mountSidebar({ editor, editorElement: editor.view.dom })
  mountChanges({ editor, docId, readOnly })
  // Handy for debugging from the browser console.
  window.workshopEditor = editor
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', boot, { once: true })
} else {
  boot()
}
