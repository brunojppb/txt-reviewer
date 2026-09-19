import { Extension } from '@tiptap/core'
import { Plugin, PluginKey } from '@tiptap/pm/state'
import { Decoration, DecorationSet } from '@tiptap/pm/view'

export const annotationStateKey = new PluginKey('annotationState')

// ProseMirror redraws marks whose DOM changes behind its back, so active,
// resolved and dimmed styling goes through decorations instead of class
// toggles.
function buildDecorations(doc, { activeId, resolved, dimPass, preview }) {
  const decorations = []
  doc.descendants((node, pos) => {
    if (!node.isText) return
    node.marks.forEach((mark) => {
      if (mark.type.name !== 'annotation') return
      const id = mark.attrs.id
      const classes = []
      if (id === activeId) classes.push('is-active')
      if (resolved.has(id)) classes.push('is-resolved')
      if (dimPass && mark.attrs.pass !== dimPass) classes.push('is-dimmed')
      if (classes.length) {
        decorations.push(
          Decoration.inline(pos, pos + node.nodeSize, { class: classes.join(' ') }),
        )
      }
    })
  })
  if (preview && preview.to > preview.from) {
    decorations.push(Decoration.inline(preview.from, preview.to, { class: 'is-preview' }))
  }
  return DecorationSet.create(doc, decorations)
}

/**
 * Paints the active, resolved, dimmed and preview annotation states over the
 * marks.
 *
 * Command: `setAnnotationState({ activeId, resolved, dimPass, preview })`
 * where `resolved` is an iterable of annotation ids, `dimPass` is a pass slug
 * or null, and `preview` is a `{from, to}` document range or null. Omitted
 * fields keep their value.
 */
export const AnnotationState = Extension.create({
  name: 'annotationState',

  addCommands() {
    return {
      setAnnotationState:
        (next) =>
        ({ tr, dispatch }) => {
          if (dispatch) tr.setMeta(annotationStateKey, next)
          return true
        },
    }
  },

  addProseMirrorPlugins() {
    return [
      new Plugin({
        key: annotationStateKey,
        state: {
          init: () => ({
            activeId: null,
            resolved: new Set(),
            dimPass: null,
            preview: null,
            decorations: DecorationSet.empty,
          }),
          apply(tr, prev, _oldState, newState) {
            const meta = tr.getMeta(annotationStateKey)
            if (!meta && !tr.docChanged) return prev
            const activeId = meta && 'activeId' in meta ? meta.activeId : prev.activeId
            const resolved = meta && 'resolved' in meta ? new Set(meta.resolved) : prev.resolved
            const dimPass = meta && 'dimPass' in meta ? meta.dimPass || null : prev.dimPass
            // Positions move when the text moves, so a stale preview must go.
            const preview = tr.docChanged
              ? null
              : meta && 'preview' in meta
                ? meta.preview || null
                : prev.preview
            return {
              activeId,
              resolved,
              dimPass,
              preview,
              decorations: buildDecorations(newState.doc, {
                activeId,
                resolved,
                dimPass,
                preview,
              }),
            }
          },
        },
        props: {
          decorations: (state) => annotationStateKey.getState(state).decorations,
        },
      }),
    ]
  },
})
