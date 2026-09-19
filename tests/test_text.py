"""Paragraph numbering and plain text."""

from __future__ import annotations

from app import text

DOC = {
    "type": "doc",
    "content": [
        {
            "type": "heading",
            "attrs": {"level": 1},
            "content": [{"type": "text", "text": "The Lighthouse"}],
        },
        {
            "type": "paragraph",
            "content": [
                {"type": "text", "text": "The keeper had"},
                {"type": "hardBreak"},
                {"type": "text", "text": "not spoken."},
            ],
        },
        {"type": "paragraph"},
        {
            "type": "bulletList",
            "content": [
                {
                    "type": "listItem",
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [{"type": "text", "text": "Salt"}],
                        }
                    ],
                },
                {
                    "type": "listItem",
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [{"type": "text", "text": "Rope"}],
                        }
                    ],
                },
            ],
        },
        {"type": "paragraph", "content": [{"type": "text", "text": "The end."}]},
    ],
}


def test_numbering() -> None:
    assert text.paragraphs(DOC) == [
        {"n": 1, "text": "The Lighthouse"},
        {"n": 2, "text": "The keeper had not spoken."},
        {"n": 3, "text": ""},
        {"n": 4, "text": "Salt"},
        {"n": 5, "text": "Rope"},
        {"n": 6, "text": "The end."},
    ]


def test_render_skips_empty_paragraphs_and_keeps_numbers() -> None:
    rendered = text.render(text.paragraphs(DOC))
    assert rendered.startswith("[1] The Lighthouse\n\n[2] The keeper")
    assert "[3]" not in rendered
    assert "[4] Salt\n\n[5] Rope\n\n[6] The end." in rendered


def test_word_count() -> None:
    assert text.word_count(text.paragraphs(DOC)) == 11


def test_paragraphs_reads_stored_json() -> None:
    assert text.paragraphs('{"type":"doc","content":[]}') == []
    assert text.paragraphs("not json") == []
    assert text.paragraphs(None) == []
