from __future__ import annotations

import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pawlette.extraction import Palette

log = logging.getLogger(__name__)


def _load_plugin_config(config_dir: Path, plugin_stem: str) -> dict[str, str]:
    """Read [plugins.<plugin_stem>] section from pawlette.toml.

    Returns a flat dict of string values, or empty dict if not found.
    """
    try:
        import tomllib
    except ImportError:
        try:
            import tomli as tomllib  # type: ignore[no-redef]
        except ImportError:
            return {}

    toml_path = config_dir / "pawlette.toml"
    if not toml_path.exists():
        return {}

    try:
        data = tomllib.loads(toml_path.read_text(encoding="utf-8"))
        section = data.get("plugins", {}).get(plugin_stem, {})
        return {k: str(v) for k, v in section.items()}
    except Exception as exc:
        log.warning("Could not read plugin config for %r: %s", plugin_stem, exc)
        return {}


def _build_cmd(plugin: Path) -> list[str]:
    """Return the command list to run *plugin*.

    .py files are invoked via the current Python interpreter so they work
    inside virtualenvs without a shebang line.
    All other files are executed directly (must be executable + have shebang).
    """
    if plugin.suffix == ".py":
        return [sys.executable, str(plugin)]
    return [str(plugin)]


def run_plugins(
    palette: "Palette",
    plugins_dir: Path,
    config_dir: Path | None = None,
    *,
    timeout: int = 30,
) -> dict[str, bool]:
    """Execute all executable files in *plugins_dir* with palette env vars.

    Parameters
    ----------
    palette:
        Active Palette — passed to plugins as PAWLETTE_* env vars.
    plugins_dir:
        Directory containing plugin executables.
    config_dir:
        Directory containing pawlette.toml (for plugin config sections).
        Defaults to ~/.config/pawlette.
    timeout:
        Per-plugin timeout in seconds.

    Returns
    -------
    Dict mapping plugin filename to True (success) / False (failure).
    """
    if not plugins_dir.exists():
        log.debug("Plugins directory %s does not exist — skipping", plugins_dir)
        return {}

    if config_dir is None:
        from pawlette.core import xdg

        config_dir = xdg.config_dir()

    # Inherit current environment, then overlay palette vars
    env = os.environ.copy()
    env.update(palette.to_env())

    results: dict[str, bool] = {}

    plugins = sorted(
        p
        for p in plugins_dir.iterdir()
        if p.is_file() and (p.suffix == ".py" or os.access(p, os.X_OK))
    )

    if not plugins:
        log.debug("No executable plugins found in %s", plugins_dir)
        return {}

    for plugin in plugins:
        log.info("Running plugin: %s", plugin.name)
        cmd = _build_cmd(plugin)

        # Inject [plugins.<stem>] config as PAWLETTE_PLUGIN_* env vars
        plugin_env = env.copy()
        plugin_cfg = _load_plugin_config(config_dir, plugin.stem)
        for key, value in plugin_cfg.items():
            env_key = "PAWLETTE_PLUGIN_" + key.upper()
            plugin_env[env_key] = value
            log.debug("  %s=%s", env_key, value)

        try:
            result = subprocess.run(
                cmd,
                env=plugin_env,
                timeout=timeout,
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                log.info("Plugin %s OK", plugin.name)
                if result.stdout.strip():
                    log.debug(
                        "Plugin %s stdout:\n%s", plugin.name, result.stdout.strip()
                    )
                results[plugin.name] = True
            else:
                log.warning(
                    "Plugin %s exited with code %d:\n%s",
                    plugin.name,
                    result.returncode,
                    result.stderr.strip(),
                )
                results[plugin.name] = False
        except subprocess.TimeoutExpired:
            log.error("Plugin %s timed out after %ds", plugin.name, timeout)
            results[plugin.name] = False
        except OSError as exc:
            log.error("Plugin %s could not be executed: %s", plugin.name, exc)
            results[plugin.name] = False

    return results
