from __future__ import annotations

from datetime import datetime
import json
from typing import Iterable, List, Dict

from .config import CONFIG_DIR, HISTORY_PATH


def append_history(entry: Dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with HISTORY_PATH.open("a", encoding="utf-8") as file:
        file.write(json.dumps(entry, ensure_ascii=False) + "\n")


def load_history(limit: int = 10) -> List[Dict]:
    if not HISTORY_PATH.exists():
        return []
    entries: List[Dict] = []
    with HISTORY_PATH.open("r", encoding="utf-8") as file:
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
