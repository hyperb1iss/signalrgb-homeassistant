#!/usr/bin/env python3

import argparse
import json
import os
import shutil
import subprocess
import sys
from collections import OrderedDict

import colorama
from colorama import Fore, Style

# Initialize colorama for cross-platform colored output
colorama.init(autoreset=True)

# Constants
PROJECT_NAME = "SignalRGB Home Assistant Integration"
PROJECT_LINK = "https://github.com/hyperb1iss/signalrgb-homeassistant"
ISSUE_TRACKER = f"{PROJECT_LINK}/issues"
HASS_CONFIG_DIR = os.getenv(
    "HASS_CONFIG_DIR", os.path.expanduser("~/dev/ha_core/config")
)
CUSTOM_COMPONENTS_DIR = os.path.join(HASS_CONFIG_DIR, "custom_components")


def print_banner(version: str) -> None:
    """Print a beautiful banner for the release script."""
    banner = f"""
{Fore.MAGENTA}╔{'═' * 60}╗
║ {Fore.CYAN}🚀 {PROJECT_NAME} Release Manager {Fore.MAGENTA}║
║ {Fore.YELLOW}Version: {version}{' ' * (49 - len(version))} {Fore.MAGENTA}║
╚{'═' * 60}╝{Style.RESET_ALL}
"""
    print(banner)


def print_message(message: str, color: str = Fore.GREEN) -> None:
    """Print a colored message."""
    print(f"{color}{message}{Style.RESET_ALL}")


def check_tool_installed(tool_name: str) -> None:
    """Check if a tool is installed."""
    if shutil.which(tool_name) is None:
        print_message(
            f"❌ {tool_name} is not installed. Please install it and try again.",
            Fore.RED,
        )
        sys.exit(1)


def copy_integration(src_path: str, dest_path: str, verbose: bool = False) -> None:
    """Copy the integration files to the destination."""
    try:
        if os.path.exists(dest_path):
            shutil.rmtree(dest_path)
            if verbose:
                print_message(
                    f"🗑️ Removed existing directory at {dest_path}", Fore.BLUE
                )
        shutil.copytree(src_path, dest_path)
        print_message(f"✅ Copied integration from {src_path} to {dest_path}")
    except OSError as e:
        print_message(f"❌ Error copying integration: {e}", Fore.RED)
        sys.exit(1)


def update_manifest(
    manifest_path: str, new_version: str, verbose: bool = False
) -> None:
    """Update the manifest.json file with the new version and reorder entries."""
    try:
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)

        manifest["version"] = new_version
        manifest["documentation"] = PROJECT_LINK
        manifest["issue_tracker"] = ISSUE_TRACKER

        ordered_manifest = OrderedDict(
            [
                ("domain", manifest["domain"]),
                ("name", manifest["name"]),
            ]
            + sorted(
                [(k, v) for k, v in manifest.items() if k not in ["domain", "name"]],
                key=lambda x: x[0],
            )
        )

        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(ordered_manifest, f, indent=2)

        print_message(
            f"✅ Updated manifest version to {new_version} and reordered entries"
        )
        if verbose:
            print_message(
                f"📄 New manifest: {json.dumps(ordered_manifest, indent=2)}", Fore.BLUE
            )
    except (OSError, json.JSONDecodeError) as e:
        print_message(f"❌ Error updating manifest: {e}", Fore.RED)
        sys.exit(1)


def git_commit_and_tag(version: str, verbose: bool = False) -> None:
    """Commit changes and create a new tag."""
    try:
        commit_message = f"🚀 Release version {version}"
        subprocess.run(["git", "add", "custom_components"], check=True)
        subprocess.run(["git", "commit", "-m", commit_message], check=True)
        subprocess.run(
            ["git", "tag", "-a", f"v{version}", "-m", f"Version {version}"], check=True
        )
        print_message(f"✅ Changes committed and tagged as v{version}")
        if verbose:
            print_message(f"🔖 Created tag: v{version}", Fore.BLUE)
    except subprocess.CalledProcessError as e:
        print_message(f"❌ Error committing/tagging: {e}", Fore.RED)
        sys.exit(1)


def update_hass(src_path: str, verbose: bool = False) -> None:
    """Update Home Assistant integration."""
    src_path = os.path.join(os.getcwd(), "custom_components", "signalrgb")
    dest_path = os.path.join(CUSTOM_COMPONENTS_DIR, "signalrgb")

    print_message(
        f"🔄 Updating Home Assistant integration from {src_path} to {dest_path}",
        Fore.BLUE,
    )
    copy_integration(src_path, dest_path, verbose)
    print_message(
        "⚠️  Remember to reload Home Assistant to apply the changes.", Fore.YELLOW
    )


def do_release(src_path: str, version: str, verbose: bool = False) -> None:
    """Perform the release process."""
    print_banner(version)
    manifest_path = os.path.join(src_path, "manifest.json")

    update_manifest(manifest_path, version, verbose)
    git_commit_and_tag(version, verbose)

    print_message(f"\n🎉 Release [{version}] process completed successfully!", Fore.CYAN)
    print_message(
        "⚠️  Don't forget to push the changes and the new tag to GitHub.", Fore.YELLOW
    )


def main() -> None:
    """Main function to handle argument parsing and command execution."""
    parser = argparse.ArgumentParser(
        description=f"Release management for {PROJECT_NAME}"
    )
    parser.add_argument(
        "command", choices=["update-hass", "release"], help="Command to run"
    )
    parser.add_argument(
        "version",
        nargs="?",
        help="Version number for the release (required for release command)",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose output"
    )

    args = parser.parse_args()

    # Paths
    src_path = os.path.join(os.getcwd(), "custom_components", "signalrgb")

    # Check for necessary tools
    check_tool_installed("git")

    if args.command == "update-hass":
        update_hass(src_path, args.verbose)
    elif args.command == "release":
        if not args.version:
            print_message("❌ Version number is required for release command.", Fore.RED)
            sys.exit(1)
        do_release(src_path, args.version, args.verbose)


if __name__ == "__main__":
    main()
