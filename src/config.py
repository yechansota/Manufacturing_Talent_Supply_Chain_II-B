"""Configuration helpers: load the pre-registration file and resolve repo paths."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = REPO_ROOT / "config" / "prereg.yaml"


def load_config(path: str | Path | None = None) -> dict[str, Any]:
    """Load prereg.yaml (the single source of truth for analysis choices)."""
    cfg_path = Path(path) if path else DEFAULT_CONFIG
    with open(cfg_path, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def repo_path(relative: str, root: str | Path | None = None) -> Path:
    """Resolve a path from the config relative to the repo root."""
    base = Path(root) if root else REPO_ROOT
    return (base / relative).resolve()
