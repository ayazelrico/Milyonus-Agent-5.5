"""Brand constants for Milyonus Agent.

Derived from the official logo: navy -> blue -> cyan gradient with chrome/silver.
The four-pointed star (U+2726) is the terminal glyph.
"""

from __future__ import annotations

NAME = "Milyonus"
PRODUCT = "Milyonus Agent"
GLYPH = "✦"  # ✦
PROMPT = f"{GLYPH} milyonus ›"  # ✦ milyonus ›

# Palette (hex). Shared by terminal styling, docs, and any web surface.
PALETTE: dict[str, str] = {
    "navy_900": "#071233",
    "navy_700": "#0B2A6F",
    "blue_500": "#1E4FD8",
    "cyan_400": "#35C6F4",
    "chrome_200": "#E6EBF1",
    "chrome_500": "#8A939B",
    "ink": "#0B0F1A",
    "ok": "#22C55E",
    "warn": "#F59E0B",
    "risk": "#EF4444",
    "quarantine": "#A855F7",
}

# Rich style names mapped to palette roles.
STYLE_ACCENT = f"bold {PALETTE['cyan_400']}"
STYLE_PRIMARY = PALETTE["blue_500"]
STYLE_MUTED = PALETTE["chrome_500"]
