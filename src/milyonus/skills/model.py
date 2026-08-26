"""Skill model and SKILL.md parsing (PLAN §5, agentskills.io-compatible).

A skill is procedural memory: an on-demand instruction document the agent loads
when relevant. Each lives in its own directory under ~/.milyonus/skills/<name>/
with a SKILL.md (YAML frontmatter + Markdown body) and optional reference files.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass(slots=True)
class SkillMeta:
    name: str
    description: str
    version: str = "0.1.0"
    platforms: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    category: str = "general"
    requires_toolsets: list[str] = field(default_factory=list)
    fallback_for_toolsets: list[str] = field(default_factory=list)
    required_environment_variables: list[str] = field(default_factory=list)
    provenance: str = "self-learned"  # self-learned | hub | user


@dataclass(slots=True)
class Skill:
    meta: SkillMeta
    body: str
    path: Path

    def reference_files(self) -> list[str]:
        """Relative paths of non-SKILL.md files in the skill directory."""
        out: list[str] = []
        for f in sorted(self.path.rglob("*")):
            if f.is_file() and f.name != "SKILL.md":
                out.append(str(f.relative_to(self.path)))
        return out


class SkillParseError(Exception):
    pass


def _split_frontmatter(text: str) -> tuple[dict, str]:
    if not text.startswith("---"):
        raise SkillParseError("SKILL.md YAML frontmatter ile başlamalı (---)")
    parts = text.split("---", 2)
    if len(parts) < 3:
        raise SkillParseError("frontmatter kapanışı (---) bulunamadı")
    try:
        meta = yaml.safe_load(parts[1]) or {}
    except yaml.YAMLError as exc:
        raise SkillParseError(f"YAML hatası: {exc}") from exc
    if not isinstance(meta, dict):
        raise SkillParseError("frontmatter bir eşleme (mapping) olmalı")
    return meta, parts[2].strip()


def parse_skill_md(text: str, path: Path) -> Skill:
    raw, body = _split_frontmatter(text)
    if "name" not in raw or "description" not in raw:
        raise SkillParseError("frontmatter 'name' ve 'description' içermeli")
    ns = (
        (raw.get("metadata") or {}).get("milyonus", {})
        if isinstance(raw.get("metadata"), dict)
        else {}
    )
    meta = SkillMeta(
        name=str(raw["name"]),
        description=str(raw["description"]),
        version=str(raw.get("version", "0.1.0")),
        platforms=list(raw.get("platforms", [])),
        tags=list(ns.get("tags", [])),
        category=str(ns.get("category", "general")),
        requires_toolsets=list(ns.get("requires_toolsets", [])),
        fallback_for_toolsets=list(ns.get("fallback_for_toolsets", [])),
        required_environment_variables=list(ns.get("required_environment_variables", [])),
        provenance=str(ns.get("provenance", "self-learned")),
    )
    return Skill(meta=meta, body=body, path=path)


def render_skill_md(meta: SkillMeta, body: str) -> str:
    """Serialize a skill back to SKILL.md text."""
    fm = {
        "name": meta.name,
        "description": meta.description,
        "version": meta.version,
    }
    if meta.platforms:
        fm["platforms"] = meta.platforms
    ns: dict = {
        "tags": meta.tags,
        "category": meta.category,
        "provenance": meta.provenance,
    }
    if meta.requires_toolsets:
        ns["requires_toolsets"] = meta.requires_toolsets
    if meta.fallback_for_toolsets:
        ns["fallback_for_toolsets"] = meta.fallback_for_toolsets
    if meta.required_environment_variables:
        ns["required_environment_variables"] = meta.required_environment_variables
    fm["metadata"] = {"milyonus": ns}
    front = yaml.safe_dump(fm, sort_keys=False, allow_unicode=True).strip()
    return f"---\n{front}\n---\n\n{body.strip()}\n"
