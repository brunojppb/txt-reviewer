import { Extension } from '@tiptap/core'
import { Plugin, PluginKey } from '@tiptap/pm/state'
import { Decoration, DecorationSet } from '@tiptap/pm/view'

export const annotationStateKey = new PluginKey('annotationState')

// ProseMirror redraws marks whose DOM changes behind its back, so active and
// resolved styling goes through decorations instead of class toggles.
function buildDecorations(doc, { activeId, resolved }) {
  const decorations = []
  doc.descendants((node, pos) => {
    if (!node.isText) return
    node.marks.forEach((mark) => {
      if (mark.type.name !== 'annotation') return
      const id = mark.attrs.id
      const classes = []
      if (id === activeId) classes.push('is-active')
      if (resolved.has(id)) classes.push('is-resolved')
      if (classes.length) {
        decorations.push(
          Decoration.inline(pos, pos + node.nodeSize, { class: classes.join(' ') }),
        )
      }
    })
  })
  return DecorationSet.create(doc, decorations)
}

/**
 * Paints the active and resolved annotation states over the marks.
 *
 * Command: `setAnnotationState({ activeId, resolved })` where `resolved` is
 * an iterable of annotation ids. Omitted fields keep their value.
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
          init: () => ({ activeId: null, resolved: new Set(), decorations: DecorationSet.empty }),
          apply(tr, prev, _oldState, newState) {
            const meta = tr.getMeta(annotationStateKey)
            if (!meta && !tr.docChanged) return prev
            const activeId = meta && 'activeId' in meta ? meta.activeId : prev.activeId
            const resolved = meta && 'resolved' in meta ? new Set(meta.resolved) : prev.resolved
            return {
              activeId,
              resolved,
              decorations: buildDecorations(newState.doc, { activeId, resolved }),
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
