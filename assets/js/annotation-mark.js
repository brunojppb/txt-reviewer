import { Mark, mergeAttributes } from '@tiptap/core'

/**
 * TipTap mark that ties a span of text to one annotation record.
 *
 * Adds the commands `setAnnotation({ id, kind, pass })` and
 * `unsetAnnotationById(id)`.
 */
export const Annotation = Mark.create({
  name: 'annotation',

  // Typing at the edge of a highlight must not extend it.
  inclusive: false,

  // An empty excludes list lets two highlights cover the same text.
  excludes: '',

  addAttributes() {
    return {
      id: {
        default: null,
        parseHTML: (element) => element.getAttribute('data-annotation-id'),
        renderHTML: (attributes) =>
          attributes.id ? { 'data-annotation-id': attributes.id } : {},
      },
      kind: {
        default: 'comment',
        parseHTML: (element) => element.getAttribute('data-kind') || 'comment',
        renderHTML: (attributes) => ({ 'data-kind': attributes.kind || 'comment' }),
      },
      // The slug of the pass that found this, or null for a manual annotation.
      pass: {
        default: null,
        parseHTML: (element) => element.getAttribute('data-pass') || null,
        renderHTML: (attributes) => (attributes.pass ? { 'data-pass': attributes.pass } : {}),
      },
    }
  },

  parseHTML() {
    return [{ tag: 'mark[data-annotation-id]' }]
  },

  renderHTML({ mark, HTMLAttributes }) {
    const kind = mark.attrs.kind || 'comment'
    return [
      'mark',
      mergeAttributes(HTMLAttributes, {
        class: `annotation annotation--${kind}`,
      }),
      0,
    ]
  },

  addCommands() {
    return {
      setAnnotation:
        (attributes) =>
        ({ commands }) =>
          commands.setMark(this.name, attributes),

      unsetAnnotationById:
        (id) =>
        ({ tr, state, dispatch }) => {
          const markType = state.schema.marks[this.name]
          if (!markType || !id) return false

          let found = false
          // removeMark never changes the text length, so the positions read from
          // the starting document stay valid for every step.
          state.doc.descendants((node, pos) => {
            if (!node.isText) return
            node.marks.forEach((mark) => {
              if (mark.type !== markType || mark.attrs.id !== id) return
              found = true
              if (dispatch) tr.removeMark(pos, pos + node.nodeSize, mark)
            })
          })

          return found
        },
    }
  },
})

export default Annotation
