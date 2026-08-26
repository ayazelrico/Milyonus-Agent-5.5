"""RiskEngine — risk-tiered autonomy (PLAN §6.1).

Answers Hermes's "bias-to-action" multiplier (report §9.3): instead of preferring
action under uncertainty across the board, Milyonus classifies each tool call and
only auto-runs the reversible, local, low-impact ones. Irreversible, outward, or
credential-touching calls ALWAYS require approval — and no "always allow" grant
can cover that class.

The decision has three outcomes:
  AUTO     -> run without asking.
  CONFIRM  -> ask the user; an "always/session" allow may apply on repeat.
  BLOCK    -> refuse regardless (the always-approval class after a deny, or a
              hard-blocked pattern from the pre-exec scanner).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from milyonus.providers.base import ToolCall
from milyonus.security.preexec import PreExecFinding, scan_command

Decision = Literal["auto", "confirm", "block"]

# Tool risk classes come from the tool's declared `risk`. These map to defaults.
_ALWAYS_CONFIRM_TOOLS = {"run_shell"}  # danger-class shell always at least confirms

# Argument shapes that force confirmation regardless of the tool's base class:
# outward-reaching or irreversible effects (PLAN §6.1).
_IRREVERSIBLE_HINTS = (
    "delete",
    "remove",
    "rm ",
    "drop ",
    "truncate",
    "send",
    "email",
    "publish",
    "post ",
    "transfer",
    "deploy",
)


@dataclass
class RiskEngine:
    # Tools/args the user granted "always allow" for this session. Keyed by a
    # normalized signature. The irreversible class is never added here.
    session_grants: set[str] = field(default_factory=set)

    def _signature(self, call: ToolCall) -> str:
        return call.name

    def _is_irreversible(self, call: ToolCall) -> bool:
        # Check both the tool name (e.g. delete_record) and the argument values
        # (e.g. a shell command containing "rm"). Either triggers the class.
        name = call.name.lower().replace("_", " ")
        blob = name + " " + " ".join(str(v) for v in call.arguments.values()).lower()
        return any(h.strip() in blob for h in _IRREVERSIBLE_HINTS)

    def classify(
        self, call: ToolCall, base_risk: str
    ) -> tuple[Decision, str, list[PreExecFinding]]:
        """Return (decision, reason, preexec_findings)."""
        findings: list[PreExecFinding] = []

        # Shell/command content gets a pre-execution scan first.
        command = call.arguments.get("command")
        if isinstance(command, str):
            findings = scan_command(command)
            if any(f.severity == "block" for f in findings):
                sigs = ", ".join(f.signal for f in findings)
                return ("block", f"pre-execution scan blocked: {sigs}", findings)

        # Safe tools with no irreversible hint run automatically.
        if base_risk == "safe" and not self._is_irreversible(call):
            return ("auto", "reversible, low impact", findings)

        # Irreversible/outward always confirms and can never be pre-granted.
        if self._is_irreversible(call):
            return (
                "confirm",
                "irreversible or outward-reaching action — approval required",
                findings,
            )

        # danger-class or caution tools: confirm unless a session grant exists.
        if self._signature(call) in self.session_grants:
            return ("auto", "session grant present", findings)
        if base_risk in ("caution", "danger") or call.name in _ALWAYS_CONFIRM_TOOLS:
            return ("confirm", f"{base_risk}-class tool", findings)

        return ("auto", "default safe", findings)

    def grant_session(self, call: ToolCall, *, irreversible: bool) -> bool:
        """Record an 'always allow for session'. Refuses for the irreversible
        class. Returns whether the grant was accepted."""
        if irreversible:
            return False
        self.session_grants.add(self._signature(call))
        return True
