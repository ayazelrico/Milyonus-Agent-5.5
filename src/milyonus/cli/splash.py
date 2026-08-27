"""Terminal branding for the Milyonus TUI — a cool, fast startup splash.

Draws the four-pointed star mark and a block "MILYONUS" wordmark with a
navy → cyan brand gradient (truecolor), then types out the tagline. Everything
degrades gracefully: no TTY, NO_COLOR, or reduced-motion → a clean static banner
with no animation. Kept fast (well under a second) and never blocks input.
"""

from __future__ import annotations

import os
import sys
import time

from rich.console import Console
from rich.text import Text

from milyonus import __version__
from milyonus.brand import PALETTE

# --- brand gradient ---------------------------------------------------------

_NAVY = (0x1E, 0x4F, 0xD8)  # blue-500
_CYAN = (0x35, 0xC6, 0xF4)  # cyan-400
_CHROME = (0xE6, 0xEB, 0xF1)


def _lerp(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> str:
    r = round(a[0] + (b[0] - a[0]) * t)
    g = round(a[1] + (b[1] - a[1]) * t)
    bl = round(a[2] + (b[2] - a[2]) * t)
    return f"#{r:02x}{g:02x}{bl:02x}"


def _gradient_line(s: str, t0: float, t1: float) -> Text:
    """Colour a string left→right across the navy→cyan gradient."""
    text = Text()
    n = max(len(s) - 1, 1)
    for i, ch in enumerate(s):
        t = t0 + (t1 - t0) * (i / n)
        text.append(ch, style=_lerp(_NAVY, _CYAN, t))
    return text


# --- ASCII art --------------------------------------------------------------

# 5-row block wordmark. Each glyph is 5 columns; joined with a single space.
_FONT: dict[str, list[str]] = {
    "M": ["█   █", "██ ██", "█ █ █", "█   █", "█   █"],
    "I": ["█████", "  █  ", "  █  ", "  █  ", "█████"],
    "L": ["█    ", "█    ", "█    ", "█    ", "█████"],
    "Y": ["█   █", " █ █ ", "  █  ", "  █  ", "  █  "],
    "O": [" ███ ", "█   █", "█   █", "█   █", " ███ "],
    "N": ["█   █", "██  █", "█ █ █", "█  ██", "█   █"],
    "U": ["█   █", "█   █", "█   █", "█   █", " ███ "],
    "S": [" ████", "█    ", " ███ ", "    █", "████ "],
}


def _wordmark(word: str = "MILYONUS") -> list[str]:
    rows = ["", "", "", "", ""]
    for ch in word:
        glyph = _FONT[ch]
        for r in range(5):
            rows[r] += glyph[r] + " "
    return [r.rstrip() for r in rows]


def _plain(console: Console) -> None:
    console.print(
        f"[bold {PALETTE['cyan_400']}]✦ MILYONUS AGENT[/] [{PALETTE['chrome_200']}]{__version__}[/]"
    )


def render_splash(
    console: Console | None = None,
    *,
    animate: bool | None = None,
    model: str = "",
    session: str = "",
    workspace: str = "",
) -> None:
    console = console or Console()

    interactive = sys.stdout.isatty() and not os.environ.get("NO_COLOR")
    if animate is None:
        animate = interactive and not os.environ.get("MILYONUS_NO_ANIM")

    if not interactive:
        _plain(console)
        if model:
            console.print(f"[dim]{model} · session {session}[/]")
        return

    word_rows = _wordmark()
    width = max(len(r) for r in word_rows)
    indent = "  "

    console.print()
    # top accent: gradient sparkles
    top = Text(indent)
    top.append_text(_gradient_line("✦ · ˚ · ✦", 0.1, 0.9))
    top.append("  ", style="default")
    top.append("MILYONUS AGENT", style=f"bold {PALETTE['cyan_400']}")
    top.append(f"  v{__version__}", style=PALETTE["chrome_500"])
    console.print(top)
    console.print()

    # the block wordmark with the navy->cyan gradient
    for row in word_rows:
        line = Text(indent)
        line.append_text(_gradient_line(row, 0.05, 0.98))
        console.print(line)

    # gradient underline
    rule = Text(indent)
    rule.append_text(_gradient_line("▔" * width, 0.05, 0.98))
    console.print(rule)

    # tagline — typed out for a touch of motion
    tagline = "Remembers.  Verifies.  Evolves."
    if animate:
        sys.stdout.write(indent + " ")
        for ch in tagline:
            sys.stdout.write(f"\033[3;38;2;198;207;216m{ch}\033[0m")
            sys.stdout.flush()
            time.sleep(0.012)
        sys.stdout.write("\n")
    else:
        console.print(f"{indent} [italic #C6CFD8]{tagline}[/]")

    if model:
        info = Text(indent + " ")
        info.append("✦ ", style=PALETTE["cyan_400"])
        info.append(model, style=PALETTE["chrome_200"])
        if session:
            info.append(f"  ·  session {session}", style=PALETTE["chrome_500"])
        console.print(info)
    if workspace:
        console.print(f"{indent} [dim]workspace: {workspace}  ·  /help for commands  ·  Ctrl+D to exit[/]")
    console.print()
