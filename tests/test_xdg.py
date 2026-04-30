"""Tests for XDG path resolution."""

import os
from pathlib import Path

import pytest

from pawlette.core import xdg


def test_default_config_dir(monkeypatch):
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    assert xdg.config_dir() == Path.home() / ".config" / "pawlette"


def test_custom_config_dir(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    assert xdg.config_dir() == tmp_path / "config" / "pawlette"


def test_custom_data_dir(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    assert xdg.plugins_dir() == tmp_path / "data" / "pawlette" / "plugins"


def test_ensure_dirs_creates_structure(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("XDG_DATA_HOME",   str(tmp_path / "data"))
    monkeypatch.setenv("XDG_STATE_HOME",  str(tmp_path / "state"))
    monkeypatch.setenv("XDG_CACHE_HOME",  str(tmp_path / "cache"))

    xdg.ensure_dirs()

    assert (tmp_path / "data" / "pawlette" / "plugins").is_dir()
    assert (tmp_path / "state" / "pawlette").is_dir()
    assert (tmp_path / "cache" / "pawlette").is_dir()


def test_dump_returns_all_keys(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    paths = xdg.dump()
    expected_keys = {
        "config_dir", "templates_root", "plugins_dir",
        "themes_dir", "state_dir", "cache_dir",
        "active_palette_file", "matugen_cache_file",
    }
    assert expected_keys.issubset(paths.keys())
