import os
from pathlib import Path

import pytest

from bing_search_cli import config as config_module
from bing_search_cli.config import Config, load_config, save_config, update_config


def test_config_save_and_load(tmp_path, monkeypatch):
    monkeypatch.setenv("BSC_CONFIG_DIR", str(tmp_path))
    cfg = Config(
        ai_project_endpoint="https://example.services.ai.azure.com/api/projects/test",
        ai_project_model_deployment="gpt-4o-mini",
    )
    save_config(cfg)

    loaded = load_config()
    assert loaded.ai_project_endpoint == "https://example.services.ai.azure.com/api/projects/test"
    assert loaded.ai_project_model_deployment == "gpt-4o-mini"


def test_env_overrides_config(tmp_path, monkeypatch):
    monkeypatch.setenv("BSC_CONFIG_DIR", str(tmp_path))
    cfg = Config(ai_project_endpoint="file-endpoint")
    save_config(cfg)

    monkeypatch.setenv("AI_PROJECT_ENDPOINT", "env-endpoint")
    loaded = load_config()
    assert loaded.ai_project_endpoint == "env-endpoint"


def test_update_config(tmp_path, monkeypatch):
    monkeypatch.setenv("BSC_CONFIG_DIR", str(tmp_path))
    cfg = Config()
    updated = update_config(cfg, {"ai_project_model_deployment": "gpt-4o"})
    assert updated.ai_project_model_deployment == "gpt-4o"
