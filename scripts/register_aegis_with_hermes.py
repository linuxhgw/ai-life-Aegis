#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


TOOL_INCLUDE = [
    "create_task",
    "list_tasks",
    "complete_task",
    "delete_task",
    "schedule_reminder",
    "list_due_reminders",
    "dispatch_due_reminders",
    "set_task_reminders_enabled",
    "record_feedback",
    "record_intervention_event",
    "get_execution_summary",
    "get_current_time",
]


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def hermes_home() -> Path:
    configured = os.environ.get("HERMES_HOME", "").strip()
    return Path(configured).expanduser() if configured else Path.home() / ".hermes"


def load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        import yaml
    except ImportError as exc:
        raise SystemExit(
            "PyYAML is required to update Hermes config.yaml. "
            "Install it with: python3 -m pip install PyYAML"
        ) from exc

    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    return loaded if isinstance(loaded, dict) else {}


def dump_yaml(path: Path, data: dict[str, Any]) -> None:
    try:
        import yaml
    except ImportError as exc:
        raise SystemExit(
            "PyYAML is required to update Hermes config.yaml. "
            "Install it with: python3 -m pip install PyYAML"
        ) from exc

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(data, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )


def run(cmd: list[str], cwd: Path | None = None) -> None:
    print("+ " + " ".join(cmd))
    subprocess.run(cmd, cwd=str(cwd) if cwd else None, check=True)


def ensure_core_mcp_installed(root: Path, *, skip_install: bool) -> Path:
    core_dir = root / "aegis-core-mcp"
    venv_dir = core_dir / ".venv"
    python_bin = venv_dir / "bin" / "python"
    command = venv_dir / "bin" / "aegis-core-mcp"

    if skip_install:
        if not command.exists():
            raise SystemExit(f"Missing MCP command: {command}")
        return command

    if not python_bin.exists():
        run([sys.executable, "-m", "venv", str(venv_dir)])

    run([str(python_bin), "-m", "pip", "install", "-e", ".[dev]"], cwd=core_dir)

    if not command.exists():
        raise SystemExit(f"Install finished but MCP command was not found: {command}")
    return command


def sync_skills(root: Path, home: Path, *, clean: bool) -> list[Path]:
    source_root = root / "aegis-hermes-skills" / "aegis"
    target_root = home / "skills" / "aegis"
    if not source_root.exists():
        raise SystemExit(f"Missing skills source directory: {source_root}")

    target_root.mkdir(parents=True, exist_ok=True)
    copied: list[Path] = []

    description = source_root / "DESCRIPTION.md"
    if description.exists():
        shutil.copy2(description, target_root / "DESCRIPTION.md")

    for skill_md in sorted(source_root.glob("*/SKILL.md")):
        skill_dir = skill_md.parent
        target_dir = target_root / skill_dir.name
        if clean and target_dir.exists():
            shutil.rmtree(target_dir)
        target_dir.mkdir(parents=True, exist_ok=True)
        shutil.copytree(skill_dir, target_dir, dirs_exist_ok=True)
        copied.append(target_dir)

    return copied


def update_hermes_config(
    home: Path,
    command: Path,
    db_path: Path,
    *,
    server_name: str,
    disabled: bool,
) -> Path:
    config_path = home / "config.yaml"
    config = load_yaml(config_path)

    mcp_servers = config.setdefault("mcp_servers", {})
    if not isinstance(mcp_servers, dict):
        raise SystemExit("config.yaml key 'mcp_servers' exists but is not a mapping")

    mcp_servers[server_name] = {
        "command": str(command),
        "env": {
            "AEGIS_CORE_DB_PATH": str(db_path),
        },
        "tools": {
            "include": TOOL_INCLUDE,
        },
        "enabled": not disabled,
    }

    dump_yaml(config_path, config)
    return config_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Register Aegis Core MCP and Aegis Hermes skills in local Hermes."
    )
    parser.add_argument(
        "--hermes-home",
        type=Path,
        default=hermes_home(),
        help="Hermes home directory. Defaults to $HERMES_HOME or ~/.hermes.",
    )
    parser.add_argument(
        "--server-name",
        default="aegis_core",
        help="Hermes MCP server name. Default: aegis_core.",
    )
    parser.add_argument(
        "--db-path",
        type=Path,
        default=repo_root() / "aegis-core-mcp" / ".data" / "aegis-core.db",
        help="SQLite DB path for Aegis Core MCP.",
    )
    parser.add_argument(
        "--skip-install",
        action="store_true",
        help="Do not create/update the aegis-core-mcp virtualenv.",
    )
    parser.add_argument(
        "--clean-skills",
        action="store_true",
        help="Replace existing ~/.hermes/skills/aegis/* skill directories before copying.",
    )
    parser.add_argument(
        "--disabled",
        action="store_true",
        help="Write the MCP server entry with enabled: false.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = repo_root()
    home = args.hermes_home.expanduser().resolve()
    db_path = args.db_path.expanduser().resolve()
    db_path.parent.mkdir(parents=True, exist_ok=True)

    command = ensure_core_mcp_installed(root, skip_install=args.skip_install)
    copied = sync_skills(root, home, clean=args.clean_skills)
    config_path = update_hermes_config(
        home,
        command.resolve(),
        db_path,
        server_name=args.server_name,
        disabled=args.disabled,
    )

    print()
    print(f"Hermes home: {home}")
    print(f"Config updated: {config_path}")
    print(f"MCP server: {args.server_name}")
    print(f"MCP command: {command.resolve()}")
    print(f"Aegis DB: {db_path}")
    print(f"Skills copied: {len(copied)}")
    for path in copied:
        print(f"  - {path}")
    print()
    print("Restart Hermes or run /reload-mcp in an active session.")


if __name__ == "__main__":
    main()
