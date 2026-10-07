"""Shared test configuration."""

import os

import pytest

from cryptoaudit.config.settings import Settings


@pytest.fixture(autouse=True)
def isolated_settings(monkeypatch):
    """Tests never read a developer's backend/.env or CRYPTOAUDIT_* environment variables."""
    monkeypatch.setitem(Settings.model_config, "env_file", None)
    for key in list(os.environ):
        if key.startswith("CRYPTOAUDIT_"):
            monkeypatch.delenv(key)
