#!/usr/bin/env python3
"""Resolve and bootstrap a project-scoped Obsidian memory vault."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path
from typing import Any


CONFIG_VERSION = 1
REQUIRED_DIRS = (
    ".obsidian",
    "Architecture",
    "Daily",
    "End-to-End Flows",
    "Initiatives",
    "Knowledge",
    "Secrets",
    "Templates",
)


def canonical(path: str | Path) -> Path:
    return Path(path).expanduser().resolve()


def default_config_path() -> Path:
    override = os.environ.get("OBSIDIAN_PROJECT_MEMORY_CONFIG")
    if override:
        return canonical(override)
    return Path.home() / ".codex" / "obsidian-project-memory" / "config.json"


def project_root(raw: str | None) -> Path:
    if raw:
        return canonical(raw)
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            check=True,
            capture_output=True,
            text=True,
        )
        return canonical(result.stdout.strip())
    except (FileNotFoundError, subprocess.CalledProcessError):
        return Path.cwd().resolve()


def load_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"version": CONFIG_VERSION, "master_vault": None, "projects": {}}
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"Config must contain a JSON object: {path}")
    data.setdefault("version", CONFIG_VERSION)
    data.setdefault("master_vault", None)
    data.setdefault("projects", {})
    if not isinstance(data["projects"], dict):
        raise ValueError(f"Config field 'projects' must be an object: {path}")
    return data


def save_config(path: Path, config: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent, delete=False
    ) as handle:
        json.dump(config, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        temporary = Path(handle.name)
    temporary.replace(path)


def resolve_vault(
    root: Path, explicit: str | None, config: dict[str, Any]
) -> tuple[Path, str]:
    if explicit:
        return canonical(explicit), "explicit"

    mapped = config["projects"].get(str(root))
    if mapped:
        return canonical(mapped), "config"

    if (root / ".obsidian").is_dir():
        return root, "project-root"

    sibling = root.parent / f"{root.name}-memory"
    if (sibling / ".obsidian").is_dir():
        return sibling.resolve(), "sibling"
    return sibling.resolve(), "new-sibling"


def frontmatter(note_type: str, tags: list[str], today: str) -> str:
    rendered_tags = ", ".join(tags)
    return (
        "---\n"
        f"type: {note_type}\n"
        f"tags: [{rendered_tags}]\n"
        f"updated: {today}\n"
        "---\n"
    )


def write_missing(path: Path, content: str, created: list[str]) -> None:
    if path.exists():
        return
    path.write_text(content, encoding="utf-8")
    created.append(str(path))


def slugify(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip()).strip("-")
    return slug or "project"


def bootstrap_vault(root: Path, vault: Path, today: str) -> list[str]:
    created: list[str] = []
    for relative in REQUIRED_DIRS:
        directory = vault / relative
        if not directory.exists():
            directory.mkdir(parents=True, exist_ok=True)
            created.append(str(directory))

    name = root.name
    write_missing(
        vault / ".obsidian" / "daily-notes.json",
        json.dumps(
            {"folder": "Daily", "format": "YYYY-MM-DD", "template": "Templates/Daily"},
            indent=2,
        )
        + "\n",
        created,
    )
    write_missing(
        vault / ".obsidian" / "templates.json",
        json.dumps({"folder": "Templates"}, indent=2) + "\n",
        created,
    )
    write_missing(
        vault / "Home.md",
        frontmatter("home", ["project", "memory"], today)
        + f"\n# {name}\n\n"
        + f"Project root: `{root}`\n\n"
        + "## Navigation\n\n"
        + "- [[Architecture/_Overview|Architecture]]\n"
        + "- [[Knowledge/Open-Tails|Open tails]]\n"
        + "- [[Working Style|Working style]]\n",
        created,
    )
    write_missing(
        vault / "Architecture" / "_Overview.md",
        frontmatter("architecture", ["project", "architecture"], today)
        + "\n# Architecture overview\n\n"
        + "Document the system structure, boundaries, runtime, and important data flows here.\n",
        created,
    )
    write_missing(
        vault / "Knowledge" / "Open-Tails.md",
        frontmatter("knowledge", ["project", "open-tails"], today)
        + "\n# Open tails\n\n"
        + "| Priority | Status | Item | Owner | Evidence |\n"
        + "|---|---|---|---|---|\n",
        created,
    )
    write_missing(
        vault / "Secrets" / "_Index.md",
        frontmatter("secrets-index", ["project", "secrets"], today)
        + "\n# Secrets index\n\n"
        + "Keep project credentials and access references in focused child notes. Never commit this vault to the project repository.\n",
        created,
    )
    write_missing(
        vault / "Templates" / "Daily.md",
        "---\n"
        + "type: daily\n"
        + "tags: [project, daily]\n"
        + "updated: {{date:YYYY-MM-DD}}\n"
        + "date: {{date:YYYY-MM-DD}}\n"
        + "---\n\n"
        + "# {{date:YYYY-MM-DD}}\n\n"
        + "## Work log\n",
        created,
    )
    write_missing(
        vault / "Working Style.md",
        frontmatter("working-style", ["project", "workflow"], today)
        + "\n# Working style\n\n"
        + "Record project-specific collaboration, verification, release, and documentation conventions here.\n",
        created,
    )
    write_missing(
        vault / "Daily" / f"{today}.md",
        "---\n"
        + "type: daily\n"
        + "tags: [project, daily]\n"
        + f"updated: {today}\n"
        + f"date: {today}\n"
        + "---\n\n"
        + f"# {today}\n\n"
        + "## Work log\n",
        created,
    )
    return created


def ensure_master_card(master: Path, root: Path, vault: Path, today: str) -> list[str]:
    created: list[str] = []
    projects = master / "Projects"
    projects.mkdir(parents=True, exist_ok=True)
    card = projects / f"{slugify(root.name)}.md"
    write_missing(
        card,
        frontmatter("project", ["project", "index"], today)
        + f"\n# {root.name}\n\n"
        + f"- Project root: `{root}`\n"
        + f"- Project vault: `{vault}`\n"
        + f"- Registered: {today}\n",
        created,
    )
    return created


def build_result(
    root: Path,
    vault: Path,
    source: str,
    config_path: Path,
    master: Path | None,
    created: list[str],
    today: str,
) -> dict[str, Any]:
    return {
        "project_root": str(root),
        "vault": str(vault),
        "resolution": source,
        "config": str(config_path),
        "master_vault": str(master) if master else None,
        "created": created,
        "read_first": [
            str(vault / "Home.md"),
            str(vault / "Daily" / f"{today}.md"),
            str(vault / "Knowledge" / "Open-Tails.md"),
        ],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("bootstrap", "status"):
        child = subparsers.add_parser(command)
        child.add_argument("--project-root")
        child.add_argument("--vault")
        child.add_argument("--master-vault")
        child.add_argument("--config", default=str(default_config_path()))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        root = project_root(args.project_root)
        config_path = canonical(args.config)
        config = load_config(config_path)
        vault, source = resolve_vault(root, args.vault, config)
        today = date.today().isoformat()
        master_raw = args.master_vault or config.get("master_vault")
        master = canonical(master_raw) if master_raw else None
        created: list[str] = []

        if args.command == "bootstrap":
            created.extend(bootstrap_vault(root, vault, today))
            config["version"] = CONFIG_VERSION
            config["projects"][str(root)] = str(vault)
            if args.master_vault:
                config["master_vault"] = str(master)
            save_config(config_path, config)
            if master:
                created.extend(ensure_master_card(master, root, vault, today))

        result = build_result(
            root, vault, source, config_path, master, created, today
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
