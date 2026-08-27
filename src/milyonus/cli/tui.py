"""Interactive terminal session — the primary development surface.

Wires provider + tools + loop together and renders a live conversation with the
✦ prompt. Assistant text streams token-by-token; tool calls appear as labeled
panels; danger-class tools trigger an inline approval prompt. Ctrl+C interrupts
the current turn (not the session); Ctrl+D / empty EOF exits.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from prompt_toolkit import PromptSession
from prompt_toolkit.patch_stdout import patch_stdout
from rich.console import Console

from milyonus.brand import GLYPH, PALETTE, PROMPT
from milyonus.cli.splash import render_splash
from milyonus.config.env import load_env
from milyonus.config.loader import load_config
from milyonus.core.budget import Budget
from milyonus.core.loop import AgentLoop
from milyonus.core.store import SessionStore
from milyonus.memory.pipeline import MemoryPipeline
from milyonus.memory.render import build_snapshot
from milyonus.memory.store import MemoryStore
from milyonus.memory.tool import make_memory_tools
from milyonus.memory.verifier import ModelVerifier, RuleBasedVerifier
from milyonus.proactive.tool import make_schedule_tool
from milyonus.prompt.builder import build_system_prompt, skill_index_section
from milyonus.providers.base import Message, ProviderError, ToolCall
from milyonus.providers.router import build_provider
from milyonus.security.context_files import safe_context_sections
from milyonus.security.risk import RiskEngine
from milyonus.skills.engine import SkillEngine
from milyonus.skills.manage import SkillManager
from milyonus.skills.tool import make_skill_tools
from milyonus.tools.fs.tools import make_fs_tools
from milyonus.tools.registry import ToolRegistry
from milyonus.tools.terminal.tools import make_shell_tool
from milyonus.tools.web.tools import make_web_tools


def _handle_command(text: str, console: Console, loop, cfg, history: list) -> bool:
    """Handle a /slash command. Returns True if the session should exit."""
    cmd, _, arg = text[1:].partition(" ")
    cmd, arg = cmd.lower().strip(), arg.strip()

    if cmd in ("exit", "quit", "q"):
        return True
    if cmd in ("help", "?"):
        console.print(
            f"[{PALETTE['cyan_400']}]commands:[/]\n"
            "  /model [name]   show or switch the model this session\n"
            "  /usage          tokens & iterations used this session\n"
            "  /clear          clear the conversation history\n"
            "  /help           this list\n"
            "  /exit           quit"
        )
    elif cmd == "model":
        if not arg:
            console.print(f"  model: [bold]{loop.provider.name}:{loop.provider.model}[/]")
        else:
            try:
                new_provider = build_provider(cfg.provider, model=arg)
                loop.provider = new_provider
                console.print(
                    f"  [{PALETTE['ok']}]switched to[/] "
                    f"[bold]{new_provider.name}:{new_provider.model}[/]"
                )
            except Exception as exc:  # noqa: BLE001 - surface to the user
                console.print(f"  [{PALETTE['risk']}]could not switch:[/] {exc}")
    elif cmd == "usage":
        b = loop.budget
        console.print(
            f"  iterations {b.used_iterations}/{b.max_iterations} · "
            f"tokens {b.used_tokens} · pressure {b.pressure():.0%}"
        )
    elif cmd == "clear":
        history.clear()
        console.print(f"  [{PALETTE['chrome_500']}]history cleared[/]")
    else:
        console.print(f"  [{PALETTE['warn']}]unknown command:[/] /{cmd}  (try /help)")
    return False


def _make_registry(root: Path, *extra_tool_groups: list) -> ToolRegistry:
    reg = ToolRegistry()
    for tool in make_fs_tools(root):
        reg.register(tool)
    reg.register(make_shell_tool(root))
    for tool in make_web_tools():
        reg.register(tool)
    for group in extra_tool_groups:
        for tool in group:
            reg.register(tool)
    return reg


async def _run_session(root: Path) -> int:
    console = Console()
    load_env()
    try:
        cfg = load_config()
    except Exception as exc:
        console.print(f"[{PALETTE['risk']}]Config error:[/] {exc}")
        return 1

    provider = build_provider(cfg.provider)

    # Verified-memory wiring: a separate cheap verifier model gates promotion.
    mem_store = MemoryStore()
    try:
        verifier_provider = build_provider(cfg.provider, model=cfg.provider.verifier_model)
        verifier = ModelVerifier(verifier_provider, fallback=RuleBasedVerifier())
    except Exception:
        verifier = RuleBasedVerifier()
    pipeline = MemoryPipeline(mem_store, config=cfg.memory, verifier=verifier)

    store = SessionStore()
    sid = store.create_session("cli", user_ref="local")

    memory_tools = make_memory_tools(pipeline, session_id=sid, user_ref="local")

    # Skill engine + self-management (procedural memory, PLAN §5).
    skill_engine = SkillEngine()
    skill_manager = SkillManager()
    skill_tools = make_skill_tools(skill_engine, skill_manager)

    registry = _make_registry(root, memory_tools, skill_tools, [make_schedule_tool()])
    risk_engine = RiskEngine()

    # Frozen L1 snapshot injected once at session start (PLAN §4.6).
    snapshot = build_snapshot(mem_store, config=cfg.memory)
    skills_section = skill_index_section(skill_engine.list_level0())

    # Scan repo context files (AGENTS.md, .cursorrules, …); inject only clean
    # ones, and warn about any dropped as poisoned (PLAN §6 layer 5).
    ctx_sections, ctx_results = safe_context_sections(root)
    for r in ctx_results:
        if not r.included:
            console.print(
                f"[{PALETTE['risk']}]⚠ context file skipped (injection):[/] {r.path.name}"
            )

    extra = [s for s in ([skills_section] + ctx_sections) if s]
    system = build_system_prompt(memory=snapshot, extra_sections=extra or None)
    budget = Budget(max_iterations=50, max_tokens=cfg.provider.max_output_tokens * 200)

    render_splash(
        console,
        model=f"{provider.name}:{provider.model}",
        session=sid,
        workspace=str(root),
    )

    async def on_text(chunk: str) -> None:
        console.print(chunk, end="", markup=False, highlight=False)

    async def on_tool(call: ToolCall) -> None:
        console.print(
            f"\n[{PALETTE['blue_500']}]→ tool[/] [bold]{call.name}[/] [dim]{call.arguments}[/]"
        )

    async def approve(call: ToolCall, risk: str) -> bool:
        # RiskEngine decides: auto-run reversible work, confirm the rest, block
        # hard-dangerous patterns outright (PLAN §6.1).
        decision, reason, findings = risk_engine.classify(call, risk)
        for f in findings:
            fc = PALETTE["risk"] if f.severity == "block" else PALETTE["warn"]
            console.print(f"  [{fc}]• {f.signal}: {f.detail}[/]")
        if decision == "auto":
            return True
        if decision == "block":
            console.print(f"\n[{PALETTE['risk']}]✗ blocked[/] {reason}")
            return False
        irreversible = risk_engine._is_irreversible(call)
        color = PALETTE["risk"] if irreversible else PALETTE["warn"]
        console.print(
            f"\n[{color}]⚠ approval required[/] [bold]{call.name}[/] "
            f"[dim]{call.arguments}[/]  ({reason})"
        )
        # Irreversible actions cannot be granted 'always'; only y/N.
        prompt = "  allow? [y/N] " if irreversible else "  allow? [y/N/session] "
        ans = (await asyncio.to_thread(input, prompt)).strip().lower()
        if ans in ("session", "s") and not irreversible:
            risk_engine.grant_session(call, irreversible=False)
            return True
        return ans in ("y", "yes")

    loop = AgentLoop(
        provider=provider,
        tools=registry,
        system_prompt=system,
        budget=budget,
        approve=approve,
        on_text=on_text,
        on_tool=on_tool,
        max_output_tokens=cfg.provider.max_output_tokens,
    )

    history: list[Message] = []
    ptk: PromptSession = PromptSession()
    turn = 0
    while True:
        try:
            with patch_stdout():
                user_input = await ptk.prompt_async(f"\n{PROMPT} ")
        except (EOFError, KeyboardInterrupt):
            console.print(f"\n[{PALETTE['chrome_500']}]See you {GLYPH}[/]")
            break

        user_input = user_input.strip()
        if not user_input:
            continue
        if user_input.startswith("/"):
            if _handle_command(user_input, console, loop, cfg, history):
                break  # /exit or /quit
            continue

        history.append(Message(role="user", content=user_input))
        store.append_message(sid, turn=turn, role="user", content=user_input)
        turn += 1
        try:
            answer = await loop.run_turn(history)
        except ProviderError as exc:
            console.print(f"\n[{PALETTE['risk']}]Provider error:[/] {exc}")
            continue
        except KeyboardInterrupt:
            console.print(f"\n[{PALETTE['warn']}](turn interrupted)[/]")
            continue
        store.append_message(sid, turn=turn, role="assistant", content=answer)
        turn += 1
        console.print()  # newline after streamed answer

    store.close()
    mem_store.close()
    return 0


def run_tui(root: Path | None = None) -> int:
    return asyncio.run(_run_session(root or Path.cwd()))
