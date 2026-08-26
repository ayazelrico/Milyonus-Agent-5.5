"""Brand invariants — the glyph and prompt must stay stable."""

from milyonus.brand import GLYPH, PALETTE, PROMPT


def test_glyph():
    assert GLYPH == "✦"


def test_prompt_shape():
    assert PROMPT.startswith(GLYPH)
    assert "milyonus" in PROMPT


def test_palette_hex():
    for value in PALETTE.values():
        assert value.startswith("#") and len(value) == 7
