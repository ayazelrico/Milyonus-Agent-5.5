"""Skill tools the agent calls (PLAN §5).

skills_list / skill_view implement progressive disclosure; skill_manage lets the
agent grow its own procedural memory. Creation goes through the manager's repro
gate + scanner, so a skill the agent writes is validated before it becomes live.
"""

from __future__ import annotations

import json
from typing import Any

from milyonus.skills.engine import SkillEngine
from milyonus.skills.manage import SkillManager
from milyonus.skills.model import SkillMeta
from milyonus.tools.registry import Tool


def make_skill_tools(engine: SkillEngine, manager: SkillManager) -> list[Tool]:
    async def skills_list(_args: dict[str, Any]) -> str:
        items = engine.list_level0()
        if not items:
            return "no registered skills"
        return json.dumps(items, ensure_ascii=False)

    async def skill_view(args: dict[str, Any]) -> str:
        return engine.view(args["name"], args.get("ref"))

    async def skill_manage(args: dict[str, Any]) -> str:
        action = args["action"]
        name = args["name"]
        if action == "delete":
            return manager.delete(name).message
        body = args.get("body", "")
        if action == "create":
            meta = SkillMeta(
                name=name,
                description=args.get("description", name),
                category=args.get("category", "general"),
                tags=args.get("tags", []),
                provenance="self-learned",
            )
            result = await manager.create(meta, body, force=args.get("force", False))
            return result.message
        if action == "patch":
            result = await manager.patch(name, body, force=args.get("force", False))
            return result.message
        return f"unknown action: {action}"

    return [
        Tool(
            name="skills_list",
            description="List available skills (name, description, category).",
            parameters={"type": "object", "properties": {}},
            handler=skills_list,
            risk="safe",
        ),
        Tool(
            name="skill_view",
            description="Show a skill's full content or a reference file.",
            parameters={
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "ref": {"type": "string", "description": "Optional reference file"},
                },
                "required": ["name"],
            },
            handler=skill_view,
            risk="safe",
        ),
        Tool(
            name="skill_manage",
            description=(
                "Create/update/delete your own skill. Creation passes a security "
                "scan and a reproducibility gate."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["create", "patch", "delete"]},
                    "name": {"type": "string"},
                    "description": {"type": "string"},
                    "category": {"type": "string"},
                    "body": {"type": "string", "description": "SKILL.md body"},
                },
                "required": ["action", "name"],
            },
            handler=skill_manage,
            risk="caution",
        ),
    ]
