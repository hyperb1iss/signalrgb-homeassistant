#!/usr/bin/env python3
"""Release management script for SignalRGB Home Assistant Integration."""

# pylint: disable=line-too-long,broad-exception-caught

import argparse
import json
import os
import shutil
import subprocess
import sys
from collections import OrderedDict

import semver
from colorama import Fore, Style, init

# Initialize colorama for cross-platform colored output
init(autoreset=True)

# Constants
PROJECT_NAME = "SignalRGB Home Assistant Integration"
REPO_NAME = "hyperb1iss/signalrgb-homeassistant"
PROJECT_LINK = f"https://github.com/{REPO_NAME}"
ISSUE_TRACKER = f"{PROJECT_LINK}/issues"
HASS_CONFIG_DIR = os.getenv(
    "HASS_CONFIG_DIR", os.path.expanduser("~/dev/ha_core/config")
)
CUSTOM_COMPONENTS_DIR = os.path.join(HASS_CONFIG_DIR, "custom_components")

# Colorful ASCII Art Banner
LOGO = f"""
{Fore.CYAN}                              ･ ｡ ☆ ∴｡　　･ﾟ*｡★･
{Fore.YELLOW} ╭─────────────────────────────────────────────────────────────────────────╮
{Fore.MAGENTA} │ ███████╗██╗ ██████╗ ███╗   ██╗ █████╗ ██╗     ██████╗  ██████╗ ██████╗  │
{Fore.MAGENTA} │ ██╔════╝██║██╔════╝ ████╗  ██║██╔══██╗██║     ██╔══██╗██╔════╝ ██╔══██╗ │
{Fore.MAGENTA} │ ███████╗██║██║  ███╗██╔██╗ ██║███████║██║     ██████╔╝██║  ███╗██████╔╝ │
{Fore.MAGENTA} │ ╚════██║██║██║   ██║██║╚██╗██║██╔══██║██║     ██╔══██╗██║   ██║██╔══██╗ │
{Fore.MAGENTA} │ ███████║██║╚██████╔╝██║ ╚████║██║  ██║███████╗██║  ██║╚██████╔╝██████╔╝ │
{Fore.MAGENTA} │ ╚══════╝╚═╝ ╚═════╝ ╚═╝  ╚═══╝╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚═════╝  │
{Fore.CYAN} │                        Home Assistant Integration                       │
{Fore.YELLOW} ╰─────────────────────────────────────────────────────────────────────────╯
{Fore.CYAN}                     ∴｡　　･ﾟ*｡☆ Release Manager ☆｡*ﾟ･　 ｡∴
{Fore.YELLOW}                            ･ ｡ ☆ ∴｡　　･ﾟ*｡★･
"""


def print_logo():
    """Print the colorful ASCII art banner."""
    print(LOGO)


def print_step(step):
    """Print a step message in blue."""
    print(Fore.BLUE + f"\n✨ {step}" + Style.RESET_ALL)


def print_error(message):
    """Print an error message in red."""
    print(Fore.RED + f"❌ Error: {message}" + Style.RESET_ALL)


def print_success(message):
    """Print a success message in green."""
    print(Fore.GREEN + f"✅ {message}" + Style.RESET_ALL)


def check_tool_installed(tool_name):
    """Check if a tool is installed."""
    if shutil.which(tool_name) is None:
        print_error(f"{tool_name} is not installed. Please install it and try again.")
        sys.exit(1)


def get_current_version():
    """Get the current version from the manifest file."""
    try:
        manifest_path = os.path.join("custom_components", "signalrgb", "manifest.json")
        with open(manifest_path, "r", encoding="utf-8") as file:
            manifest = json.load(file)
            return manifest.get("version")
    except FileNotFoundError:
        print_error("manifest.json not found.")
        sys.exit(1)
    except json.JSONDecodeError:
        print_error("Invalid JSON in manifest.json.")
        sys.exit(1)


def update_manifest(new_version):
    """Update the version in the manifest file."""
    manifest_path = os.path.join("custom_components", "signalrgb", "manifest.json")
    try:
        with open(manifest_path, "r", encoding="utf-8") as file:
            manifest = json.load(file)

        manifest["version"] = new_version
        manifest["documentation"] = PROJECT_LINK
        manifest["issue_tracker"] = ISSUE_TRACKER

        ordered_manifest = OrderedDict(
            [("domain", manifest["domain"]), ("name", manifest["name"])]
            + sorted(
                [(k, v) for k, v in manifest.items() if k not in ["domain", "name"]]
            )
        )

        with open(manifest_path, "w", encoding="utf-8") as file:
            json.dump(ordered_manifest, file, indent=2)
            file.write("\n")  # Add a newline at the end of the file
        print_success(f"Updated version in manifest.json to {new_version}")
    except Exception as e:
        print_error(f"Failed to update manifest: {str(e)}")
        sys.exit(1)


def update_pyproject_toml(new_version):
    """Update the version in pyproject.toml."""
    pyproject_path = "pyproject.toml"
    try:
        with open(pyproject_path, "r", encoding="utf-8") as file:
            lines = file.readlines()

        with open(pyproject_path, "w", encoding="utf-8") as file:
            for line in lines:
                if line.startswith("version ="):
                    file.write(f'version = "{new_version}"\n')
                else:
                    file.write(line)

        print_success(f"Updated version in pyproject.toml to {new_version}")
    except FileNotFoundError:
        print_error("pyproject.toml not found.")
        sys.exit(1)
    except Exception as e:
        print_error(f"Failed to update pyproject.toml: {str(e)}")
        sys.exit(1)


def copy_integration(src_path, dest_path):
    """Copy the integration from source to destination."""
    try:
        if os.path.exists(dest_path):
            shutil.rmtree(dest_path)
        shutil.copytree(src_path, dest_path)
        print_success(f"Copied integration from {src_path} to {dest_path}")
    except Exception as e:
        print_error(f"Failed to copy integration: {str(e)}")
        sys.exit(1)


def commit_and_push(version):
    """Commit and push changes to the repository."""
    print_step("Committing and pushing changes")
    try:
        subprocess.run(
            ["git", "add", "custom_components", "pyproject.toml"], check=True
        )
        subprocess.run(
            ["git", "commit", "-m", f":rocket: Release version {version}"], check=True
        )
        subprocess.run(["git", "push"], check=True)
        subprocess.run(["git", "tag", f"v{version}"], check=True)
        subprocess.run(["git", "push", "--tags"], check=True)
        print_success(f"Changes committed and pushed for version {version}")
    except subprocess.CalledProcessError as e:
        print_error(f"Git operations failed: {str(e)}")
        sys.exit(1)


def update_hass():
    """Update the Home Assistant integration."""
    print_step("Updating Home Assistant integration")
    src_path = os.path.join(os.getcwd(), "custom_components", "signalrgb")
    dest_path = os.path.join(CUSTOM_COMPONENTS_DIR, "signalrgb")
    copy_integration(src_path, dest_path)
    print_success("Home Assistant integration updated")
    print(
        Fore.YELLOW
        + "⚠️  Remember to reload Home Assistant to apply the changes."
        + Style.RESET_ALL
    )


def main():
    """Main function to handle command-line arguments and execute the appropriate commands."""
    parser = argparse.ArgumentParser(
        description=f"Release management for {PROJECT_NAME}"
    )
    parser.add_argument(
        "command", choices=["update-hass", "release"], help="Command to run"
    )
    parser.add_argument(
        "version",
        nargs="?",
        help="Version number for release (required for release command)",
    )
    args = parser.parse_args()

    print_logo()
    print_step(f"Starting {args.command} process")

    check_tool_installed("git")

    if args.command == "update-hass":
        update_hass()
    elif args.command == "release":
        if not args.version:
            print_error("Version number is required for the release command.")
            sys.exit(1)

        try:
            semver.parse(args.version)
        except ValueError:
            print_error("Invalid semantic version.")
            sys.exit(1)

        current_version = get_current_version()
        print(Fore.CYAN + f"Current version: {current_version}" + Style.RESET_ALL)
        print(Fore.MAGENTA + f"New version: {args.version}" + Style.RESET_ALL)

        update_manifest(args.version)
        update_pyproject_toml(args.version)
        commit_and_push(args.version)

        print(
            Fore.GREEN
            + f"\n🎉✨ {PROJECT_NAME} v{args.version} has been successfully prepared for release! ✨🎉"
            + Style.RESET_ALL
        )
        print(
            Fore.YELLOW
            + "Note: The GitHub release will be created by CI."
            + Style.RESET_ALL
        )


if __name__ == "__main__":
    main()
