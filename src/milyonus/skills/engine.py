"""Skill engine — discovery and progressive disclosure (PLAN §5.2).

Three levels of detail so the model spends tokens only on what it needs:
  Level 0  list()          -> [{name, description, category}]  (~cheap)
  Level 1  view(name)      -> full SKILL.md body + metadata
  Level 2  view(name, ref) -> a specific reference file

Skills load from ~/.milyonus/skills/ plus a read-only bundled directory shipped
with the package. Platform-incompatible skills are hidden from the listing.
"""

from __future__ import annotations

import platform
from pathlib import Path

from milyonus.config.paths import skills_dir
from milyonus.skills.model import Skill, SkillParseError, parse_skill_md


def _current_platform() -> str:
    sys = platform.system().lower()
    return {"darwin": "macos", "linux": "linux", "windows": "windows"}.get(sys, sys)


class SkillEngine:
    def __init__(self, roots: list[Path] | None = None) -> None:
        # User skills first (take precedence), then bundled.
        bundled = Path(__file__).resolve().parent.parent.parent.parent / "skills"
        self.roots = roots or [skills_dir(), bundled]
        self._platform = _current_platform()

    def _iter_skill_dirs(self) -> list[Path]:
        seen: set[str] = set()
        dirs: list[Path] = []
        for root in self.roots:
            if not root.exists():
                continue
            for d in sorted(root.iterdir()):
                if d.is_dir() and (d / "SKILL.md").exists() and d.name not in seen:
                    seen.add(d.name)
                    dirs.append(d)
        return dirs

    def _load(self, path: Path) -> Skill | None:
        try:
            return parse_skill_md((path / "SKILL.md").read_text("utf-8"), path)
        except (SkillParseError, OSError):
            return None

    def _compatible(self, skill: Skill) -> bool:
        return not skill.meta.platforms or self._platform in skill.meta.platforms

    def load_all(self) -> list[Skill]:
        skills = [s for p in self._iter_skill_dirs() if (s := self._load(p))]
        return [s for s in skills if self._compatible(s)]

    def get(self, name: str) -> Skill | None:
        for skill in self.load_all():
            if skill.meta.name == name:
                return skill
        return None

    # --- progressive disclosure -----------------------------------------

    def list_level0(self) -> list[dict[str, str]]:
        return [
            {
                "name": s.meta.name,
                "description": s.meta.description,
                "category": s.meta.category,
            }
            for s in self.load_all()
        ]

    def view(self, name: str, ref: str | None = None) -> str:
        skill = self.get(name)
        if skill is None:
            return f"skill bulunamadı: {name}"
        if ref is None:
            refs = skill.reference_files()
            ref_note = f"\n\nReferans dosyaları: {', '.join(refs)}" if refs else ""
            return f"# {skill.meta.name} (v{skill.meta.version})\n\n{skill.body}{ref_note}"
        # Level 2: a specific reference file, path-confined to the skill dir.
        target = (skill.path / ref).resolve()
        if skill.path.resolve() not in target.parents:
            return f"geçersiz referans yolu: {ref}"
        if not target.exists():
            return f"referans dosyası yok: {ref}"
        return target.read_text("utf-8")
