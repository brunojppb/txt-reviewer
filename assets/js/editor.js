import { Editor } from '@tiptap/core'
import StarterKit from '@tiptap/starter-kit'
import { Placeholder } from '@tiptap/extension-placeholder'
import { BubbleMenu } from '@tiptap/extension-bubble-menu'
import { Annotation } from './annotation-mark.js'
import { AnnotationState } from './annotation-state.js'
import { SlashMenu } from './slash-menu.js'
import { createBubbleBar } from './bubble-menu.js'

/**
 * Creates the TipTap editor for a document or a revision snapshot.
 *
 * @param {object} options
 * @param {HTMLElement} options.element mount point
 * @param {object} options.content TipTap document JSON
 * @param {boolean} [options.readOnly] render without editing
 * @param {string} [options.docId] document id used by the annotate buttons
 * @param {(editor: Editor) => void} [options.onUpdate] called after every change
 * @returns {Editor}
 */
export function createEditor({ element, content, readOnly = false, docId = null, onUpdate }) {
  let editor = null

  const bar = createBubbleBar({ getEditor: () => editor, docId, readOnly })

  editor = new Editor({
    element,
    content,
    editable: !readOnly,
    extensions: [
      StarterKit.configure({ heading: { levels: [1, 2, 3] } }),
      Placeholder.configure({
        placeholder: 'Type / for commands',
        emptyNodeClass: 'is-editor-empty',
        emptyEditorClass: 'is-editor-empty',
      }),
      Annotation,
      AnnotationState,
      SlashMenu,
      BubbleMenu.configure({
        element: bar.element,
        appendTo: () => document.body,
        options: { placement: 'top', offset: 8 },
      }),
    ],
    onUpdate: ({ editor: instance }) => {
      onUpdate?.(instance)
    },
    onSelectionUpdate: () => bar.sync(),
    onTransaction: () => bar.sync(),
    onDestroy: () => bar.element.remove(),
  })

  return editor
}
