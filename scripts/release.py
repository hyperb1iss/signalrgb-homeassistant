#!/usr/bin/env python3
"""Prepare and verify local release files, or install into an explicit HA directory."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import tomllib

ROOT = Path(__file__).resolve().parents[1]
VERSION_PATTERN = re.compile(r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)")


def validate_version(version: str) -> str:
    """Require a stable semantic version before touching release files."""
    if VERSION_PATTERN.fullmatch(version) is None:
        raise ValueError("Use a stable version such as 1.2.0")
    return version


def verify_release(tag: str, root: Path = ROOT) -> None:
    """Reject tags that disagree with either installation artifact."""
    if not tag.startswith("v"):
        raise ValueError("Release tags must start with v")
    version = validate_version(tag[1:])
    project = tomllib.loads((root / "pyproject.toml").read_text())
    manifest = json.loads((root / "custom_components/signalrgb/manifest.json").read_text())
    if project["project"]["version"] != version or manifest["version"] != version:
        raise ValueError("Tag, pyproject.toml and manifest.json versions must match")


def prepare_release(version: str, root: Path = ROOT) -> None:
    """Update version files and the lockfile without committing or publishing."""
    validate_version(version)
    project_path = root / "pyproject.toml"
    manifest_path = root / "custom_components/signalrgb/manifest.json"
    project_text = project_path.read_text()
    project = tomllib.loads(project_text)
    current = project["project"]["version"]
    manifest = json.loads(manifest_path.read_text())
    if manifest["version"] != current:
        raise ValueError("Existing project and manifest versions disagree")
    if tuple(map(int, version.split("."))) <= tuple(map(int, current.split("."))):
        raise ValueError("The release version must be newer than the current version")
    updated, count = re.subn(
        rf'^version = "{re.escape(current)}"$',
        f'version = "{version}"',
        project_text,
        count=1,
        flags=re.MULTILINE,
    )
    if count != 1:
        raise ValueError("Cannot locate the project version field")
    manifest["version"] = version
    project_path.write_text(updated)
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    subprocess.run(["uv", "lock"], cwd=root, check=True)  # noqa: S607


def install_integration(config_dir: Path, root: Path = ROOT) -> None:
    """Copy the integration into an explicitly selected Home Assistant config."""
    config_dir = config_dir.expanduser().resolve()
    if not (config_dir / "configuration.yaml").is_file():
        raise ValueError("The config directory must contain configuration.yaml")
    destination = config_dir / "custom_components/signalrgb"
    source = root / "custom_components/signalrgb"
    if destination.is_symlink() or destination.resolve() == source.resolve():
        raise ValueError("Refusing to replace a symlink or the source integration")
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=".signalrgb-", dir=destination.parent))
    staging = temporary / "incoming"
    backup = temporary / "previous"
    preserve_backup = False
    try:
        shutil.copytree(source, staging, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        if destination.exists():
            destination.rename(backup)
        staging.rename(destination)
    except BaseException:
        if backup.exists():
            try:
                backup.rename(destination)
            except BaseException as err:
                preserve_backup = True
                raise OSError(
                    f"Could not restore the previous installation; recover it from {backup}"
                ) from err
        raise
    finally:
        if not preserve_backup:
            shutil.rmtree(temporary)


def main() -> None:
    """Run an explicit local maintenance operation."""
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prepare = commands.add_parser("prepare", help="Update local release versions and lockfile")
    prepare.add_argument("version")
    verify = commands.add_parser("verify", help="Check a release tag against version files")
    verify.add_argument("tag")
    install = commands.add_parser(
        "update-hass", help="Install into a Home Assistant config directory"
    )
    install.add_argument("--config-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == "prepare":
            prepare_release(args.version)
        elif args.command == "verify":
            verify_release(args.tag)
        else:
            install_integration(args.config_dir)
    except (ValueError, OSError, subprocess.CalledProcessError) as err:
        parser.exit(1, f"{err}\n")


if __name__ == "__main__":
    main()
