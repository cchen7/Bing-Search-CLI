from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
import os
from typing import List, Dict


def _get_config_dir() -> Path:
    return Path(os.environ.get("BSC_CONFIG_DIR", Path.home() / ".bing-search-cli"))


def _get_history_path() -> Path:
    return _get_config_dir() / "history.jsonl"


def append_history(entry: Dict) -> None:
    config_dir = _get_config_dir()
    history_path = _get_history_path()
    config_dir.mkdir(parents=True, exist_ok=True)
    with history_path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(entry, ensure_ascii=False) + "\n")


def load_history(limit: int = 10) -> List[Dict]:
    history_path = _get_history_path()
    if not history_path.exists():
        return []
    entries: List[Dict] = []
    with history_path.open("r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return entries[-limit:]


def now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
