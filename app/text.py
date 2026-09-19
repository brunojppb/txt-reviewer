"""Plain text and paragraph numbering for TipTap documents."""

from __future__ import annotations

import json
from typing import Any

LIST_TYPES = ("bulletList", "orderedList")


def _node_text(node: dict[str, Any]) -> str:
    """Return the text of one node and everything under it."""
    kind = node.get("type")
    if kind == "text":
        return str(node.get("text", ""))
    if kind == "hardBreak":
        return " "
    children = node.get("content") or []
    return "".join(_node_text(c) for c in children if isinstance(c, dict))


def paragraphs(content: Any) -> list[dict[str, Any]]:
    """Number the paragraphs of a document from 1. Return dicts of n and text."""
    doc = content
    if isinstance(doc, (str, bytes)):
        try:
            doc = json.loads(doc)
        except (TypeError, ValueError):
            return []
    if not isinstance(doc, dict):
        return []

    out: list[dict[str, Any]] = []
    for block in doc.get("content") or []:
        if not isinstance(block, dict):
            continue
        # A list gives one paragraph per item. Every other block gives one.
        if block.get("type") in LIST_TYPES:
            items = [c for c in (block.get("content") or []) if isinstance(c, dict)]
        else:
            items = [block]
        for item in items:
            out.append({"n": len(out) + 1, "text": _node_text(item).strip()})
    return out


def render(paras: list[dict[str, Any]]) -> str:
    """Return the numbered plain text of a document. Empty paragraphs drop out."""
    return "\n\n".join(f"[{p['n']}] {p['text']}" for p in paras if p["text"])


def word_count(paras: list[dict[str, Any]]) -> int:
    """Return the number of words across the paragraphs."""
    return sum(len(p["text"].split()) for p in paras)


def document_word_count(content: Any) -> int:
    """Return the number of words in a document."""
    return word_count(paragraphs(content))
