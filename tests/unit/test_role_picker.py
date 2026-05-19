from __future__ import annotations

import pytest

from resume_builder.role import RoleNotFoundError, StaticRolePicker


def test_static_picker_lists_roles(config_dir):
    picker = StaticRolePicker(config_dir / "roles.json")
    ids = {r.id for r in picker.list_available()}
    assert {"cybersecurity-blueteam", "fullstack-web"} <= ids


def test_static_picker_pick(config_dir):
    picker = StaticRolePicker(config_dir / "roles.json")
    role = picker.pick("cybersecurity-blueteam")
    assert role.label.startswith("Cybersecurity")
    assert "SIEM" in role.keywords


def test_static_picker_missing(config_dir):
    picker = StaticRolePicker(config_dir / "roles.json")
    with pytest.raises(RoleNotFoundError):
        picker.pick("does-not-exist")
