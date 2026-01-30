import os
from pathlib import Path

import pytest

from bing_search_cli import config as config_module
from bing_search_cli.config import Config, load_config, save_config, update_config


def test_config_save_and_load(tmp_path, monkeypatch):
    monkeypatch.setenv("BSC_CONFIG_DIR", str(tmp_path))
    cfg = Config(
        bing_api_key="key",
        azure_openai_endpoint="https://example.openai.azure.com/",
        azure_openai_deployment="gpt5.2-nano",
    )
    save_config(cfg)

    loaded = load_config()
    assert loaded.bing_api_key == "key"
    assert loaded.azure_openai_endpoint == "https://example.openai.azure.com/"
    assert loaded.azure_openai_deployment == "gpt5.2-nano"


def test_env_overrides_config(tmp_path, monkeypatch):
    monkeypatch.setenv("BSC_CONFIG_DIR", str(tmp_path))
    cfg = Config(bing_api_key="file-key")
    save_config(cfg)

    monkeypatch.setenv("BING_API_KEY", "env-key")
    loaded = load_config()
    assert loaded.bing_api_key == "env-key"


def test_update_config(tmp_path, monkeypatch):
    monkeypatch.setenv("BSC_CONFIG_DIR", str(tmp_path))
    cfg = Config()
    updated = update_config(cfg, {"search_provider": "grounding"})
    assert updated.search_provider == "grounding"
