"""`milyonus admin ...` — the operator-only surface for T0 writes (H1).

This surface is deliberately separate from the agent tools and every messaging
channel. Nothing the model sees can reach it. All commands require the operator's
private key (kept OFF this host); the host holds only the public key and can
verify, never forge.
"""

from __future__ import annotations

import base64
from pathlib import Path

import typer
from rich.console import Console

from milyonus.brand import GLYPH, PALETTE

admin_app = typer.Typer(help="Operator-only: manage T0 (highest authority) memory.")
t0_app = typer.Typer(help="Signed, two-phase T0 writes.")
admin_app.add_typer(t0_app, name="t0")
console = Console()


@admin_app.command("keygen")
def keygen(
    private: str = typer.Option(
        ..., help="Where to write the operator PRIVATE key (keep it OFF this host)"
    ),
) -> None:
    """Generate an operator keypair. Install the public key on the agent host,
    keep the private key on your own trusted device."""
    from milyonus.security.operator import crypto_available, generate_keypair

    if not crypto_available():
        console.print(
            f"[{PALETTE['risk']}]cryptography missing — pip install milyonus-agent[admin][/]"
        )
        raise typer.Exit(code=1)
    pub = generate_keypair(Path(private).expanduser())
    console.print(f"[{PALETTE['ok']}]{GLYPH} keypair created[/]")
    console.print(f"  private key: {private}  [dim](keep secret, off this host)[/]")
    console.print(f"  public key : {pub}  [dim](installed for verification)[/]")


@t0_app.command("add")
def t0_add(
    content: str = typer.Argument(..., help="The operator claim (becomes T0 after activation)"),
    key: str = typer.Option(..., help="Path to the operator PRIVATE key"),
) -> None:
    """Stage a signed T0 claim (passive until a second `activate`)."""
    from milyonus.memory.store import MemoryStore
    from milyonus.memory.t0 import T0Error, stage_message, stage_t0
    from milyonus.security.operator import sign

    sig = base64.b64encode(sign(Path(key).expanduser(), stage_message(content))).decode()
    try:
        mid = stage_t0(MemoryStore(), content, signature_b64=sig)
    except T0Error as exc:
        console.print(f"[{PALETTE['risk']}]{exc}[/]")
        raise typer.Exit(code=1) from exc
    console.print(
        f"[{PALETTE['warn']}]{GLYPH} T0 staged (passive)[/] {mid}\n"
        f"  activate with a second signature after the review gap:\n"
        f"  [dim]milyonus admin t0 activate {mid} --key {key}[/]"
    )


@t0_app.command("activate")
def t0_activate(
    item_id: str = typer.Argument(...),
    key: str = typer.Option(..., help="Path to the operator PRIVATE key"),
) -> None:
    """Activate a staged T0 (requires the second signature AND the review gap)."""
    from milyonus.config.loader import load_config
    from milyonus.memory.store import MemoryStore
    from milyonus.memory.t0 import T0Error, activate_message, activate_t0
    from milyonus.security.operator import sign

    store = MemoryStore()
    item = store.get(item_id)
    if item is None:
        console.print(f"[{PALETTE['risk']}]not found: {item_id}[/]")
        raise typer.Exit(code=1)
    sig = base64.b64encode(
        sign(Path(key).expanduser(), activate_message(item_id, item.evidence_hash))
    ).decode()
    try:
        activate_t0(store, item_id, signature_b64=sig, config=load_config().memory)
    except T0Error as exc:
        console.print(f"[{PALETTE['risk']}]{exc}[/]")
        raise typer.Exit(code=1) from exc
    console.print(f"[{PALETTE['ok']}]{GLYPH} T0 activated[/] {item_id} — now an operator default")


@t0_app.command("list")
def t0_list() -> None:
    """List staged and active T0 memory."""
    from milyonus.memory.store import MemoryStore
    from milyonus.security.operator import fingerprint

    store = MemoryStore()
    staged = store.staged_t0()
    active = [m for m in store.active() if m.trust_tier == "T0"]
    console.print(f"[bold]{GLYPH} Operator key:[/] {fingerprint()}")
    console.print(f"[bold]Staged (passive):[/] {len(staged)}")
    for m in staged:
        console.print(f"  [{PALETTE['warn']}]○[/] {m.id}  {m.content}")
    console.print(f"[bold]Active T0:[/] {len(active)}")
    for m in active:
        console.print(f"  [{PALETTE['ok']}]●[/] {m.id}  {m.content}")
