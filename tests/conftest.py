from __future__ import annotations

from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def project_root() -> Path:
    return PROJECT_ROOT


@pytest.fixture
def config_dir(project_root: Path) -> Path:
    return project_root / "config"


@pytest.fixture
def templates_dir(config_dir: Path) -> Path:
    return config_dir / "templates"
