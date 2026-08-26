"""Prompt builder: identity present, and memory is fenced as data with the rule."""

from milyonus.prompt.builder import MemorySnapshot, build_system_prompt


def test_identity_always_present():
    p = build_system_prompt()
    assert "Milyonus Agent" in p


def test_empty_memory_no_fence():
    p = build_system_prompt(memory=MemorySnapshot())
    assert "<milyonus:memory" not in p


def test_memory_is_fenced_and_ruled():
    snap = MemorySnapshot(user_profile="Türkçe konuşur", agent_notes="proje: milyonus")
    p = build_system_prompt(memory=snap)
    assert "PAST OBSERVATIONS" in p  # the not-instructions rule
    assert '<milyonus:memory kind="user-profile">' in p
    assert '<milyonus:memory kind="agent-notes">' in p
    assert "Türkçe konuşur" in p


def test_extra_sections_appended():
    p = build_system_prompt(extra_sections=["# Skills\n- pdf"])
    assert "# Skills" in p
