from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import json
import os
from typing import Any, Dict

CONFIG_DIR = Path(os.environ.get("BSC_CONFIG_DIR", Path.home() / ".bing-search-cli"))
CONFIG_PATH = CONFIG_DIR / "config.json"
HISTORY_PATH = CONFIG_DIR / "history.jsonl"


@dataclass
class Config:
    ai_project_endpoint: str | None = None
    ai_project_connection_id: str | None = None
    ai_project_model_deployment: str = "gpt-4o-mini"
    log_level: str = "INFO"
    sdk_log_level: str = "ERROR"
    trace_enabled: bool = False
    prewarm_enabled: bool = True
    streaming_enabled: bool = True
    warmup_enabled: bool = True
    warmup_delay_ms: int = 1200
    warmup_prompt: str = "OK"


ENV_MAP = {
    "AI_PROJECT_ENDPOINT": "ai_project_endpoint",
    "AI_PROJECT_CONNECTION_ID": "ai_project_connection_id",
    "AI_PROJECT_MODEL_DEPLOYMENT": "ai_project_model_deployment",
    "BSC_LOG_LEVEL": "log_level",
    "BSC_SDK_LOG_LEVEL": "sdk_log_level",
    "BSC_TRACE": "trace_enabled",
    "BSC_PREWARM": "prewarm_enabled",
    "BSC_STREAM": "streaming_enabled",
    "BSC_WARMUP": "warmup_enabled",
    "BSC_WARMUP_DELAY_MS": "warmup_delay_ms",
    "BSC_WARMUP_PROMPT": "warmup_prompt",
}


def load_config() -> Config:
    config = Config()
    if CONFIG_PATH.exists():
        data = json.loads(CONFIG_PATH.read_text())
        for key, value in data.items():
            if hasattr(config, key):
                setattr(config, key, value)

    for env_key, attr in ENV_MAP.items():
        if env_key in os.environ:
            value = os.environ[env_key]
            if attr in {"trace_enabled", "prewarm_enabled", "streaming_enabled", "warmup_enabled"}:
                setattr(config, attr, value.lower() in ("1", "true", "yes", "on"))
            elif attr == "warmup_delay_ms":
                try:
                    setattr(config, attr, int(value))
                except ValueError:
                    pass
            elif attr == "warmup_prompt":
                setattr(config, attr, value)
            else:
                setattr(config, attr, value)

    return config


def save_config(config: Config) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(asdict(config), indent=2, sort_keys=True))


def update_config(config: Config, updates: Dict[str, Any]) -> Config:
    for key, value in updates.items():
        if hasattr(config, key):
            if key in {"trace_enabled", "prewarm_enabled", "streaming_enabled", "warmup_enabled"}:
                if isinstance(value, bool):
                    setattr(config, key, value)
                else:
                    setattr(config, key, str(value).lower() in ("1", "true", "yes", "on"))
            elif key == "warmup_delay_ms":
                try:
                    setattr(config, key, int(value))
                except ValueError:
                    pass
            elif key == "warmup_prompt":
                setattr(config, key, str(value))
            else:
                setattr(config, key, value)
    save_config(config)
    return config


def redact(value: str | None) -> str:
    if not value:
        return ""
    if len(value) <= 6:
        return "***"
    return f"{value[:3]}***{value[-3:]}"


def format_config(config: Config) -> str:
    return (
        "Current configuration:\n"
        f"  ai_project_endpoint: {config.ai_project_endpoint or ''}\n"
        f"  ai_project_connection_id: {redact(config.ai_project_connection_id)}\n"
        f"  ai_project_model_deployment: {config.ai_project_model_deployment}\n"
        f"  log_level: {config.log_level}\n"
        f"  sdk_log_level: {config.sdk_log_level}\n"
        f"  trace_enabled: {config.trace_enabled}\n"
        f"  prewarm_enabled: {config.prewarm_enabled}\n"
        f"  streaming_enabled: {config.streaming_enabled}\n"
        f"  warmup_enabled: {config.warmup_enabled}\n"
        f"  warmup_delay_ms: {config.warmup_delay_ms}\n"
        f"  warmup_prompt: {config.warmup_prompt}\n"
        f"  config_path: {CONFIG_PATH}\n"
        f"  history_path: {HISTORY_PATH}"
    )
