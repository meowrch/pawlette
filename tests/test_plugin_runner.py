import stat
from pathlib import Path
from unittest.mock import MagicMock

from pawlette.plugins import run_plugins


def _make_plugin(directory: Path, name: str, script: str) -> Path:
    p = directory / name
    p.write_text(script)
    p.chmod(p.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    return p


def _fake_palette() -> MagicMock:
    m = MagicMock()
    m.to_env.return_value = {"PAWLETTE_BG": "#1e1e2e", "PAWLETTE_PRIMARY": "#cba6f7"}
    return m


def test_successful_plugin(tmp_path):
    _make_plugin(tmp_path, "ok.sh", "#!/bin/sh\nexit 0\n")
    results = run_plugins(_fake_palette(), tmp_path)
    assert results == {"ok.sh": True}


def test_failing_plugin(tmp_path):
    _make_plugin(tmp_path, "fail.sh", "#!/bin/sh\nexit 1\n")
    results = run_plugins(_fake_palette(), tmp_path)
    assert results == {"fail.sh": False}


def test_plugin_receives_env(tmp_path):
    out_file = tmp_path / "out.txt"
    _make_plugin(
        tmp_path,
        "env_check.sh",
        f"#!/bin/sh\necho $PAWLETTE_BG > {out_file}\n",
    )
    run_plugins(_fake_palette(), tmp_path)
    assert out_file.read_text().strip() == "#1e1e2e"


def test_nonexistent_plugins_dir(tmp_path):
    results = run_plugins(_fake_palette(), tmp_path / "nonexistent")
    assert results == {}


def test_non_executable_file_skipped(tmp_path):
    p = tmp_path / "not_exec.sh"
    p.write_text("#!/bin/sh\nexit 0\n")
    # Do NOT chmod +x
    results = run_plugins(_fake_palette(), tmp_path)
    assert results == {}
