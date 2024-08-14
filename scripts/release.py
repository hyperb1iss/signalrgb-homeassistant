#!/usr/bin/env python3
"""Release management script for SignalRGB Home Assistant Integration."""

# ruff: noqa: E501
# pylint: disable=broad-exception-caught, line-too-long

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from collections import OrderedDict
from typing import List, Tuple

import semver
from colorama import Style, init
from wcwidth import wcswidth

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

# ANSI Color Constants
COLOR_RESET = Style.RESET_ALL
COLOR_BORDER = "\033[38;2;75;0;130m"
COLOR_STAR = "\033[38;2;255;255;0m"
COLOR_ERROR = "\033[38;2;255;0;0m"
COLOR_SUCCESS = "\033[38;2;50;205;50m"
COLOR_BUILD_SUCCESS = "\033[38;2;255;215;0m"
COLOR_VERSION_PROMPT = "\033[38;2;147;112;219m"
COLOR_STEP = "\033[38;2;255;0;130m"
COLOR_WARNING = "\033[38;2;255;165;0m"

# Gradient colors for the banner
GRADIENT_COLORS = [
    (255, 0, 0),
    (0, 0, 255),
    (0, 255, 0),
    (0, 0, 255),
    (255, 0, 0),
]


def print_colored(message: str, color: str) -> None:
    """Print a message with a specific color."""
    print(f"{color}{message}{COLOR_RESET}")


def print_step(step: str) -> None:
    """Print a step in the process with a specific color."""
    print_colored(f"\n✨ {step}", COLOR_STEP)


def print_error(message: str) -> None:
    """Print an error message with a specific color."""
    print_colored(f"❌ Error: {message}", COLOR_ERROR)


def print_success(message: str) -> None:
    """Print a success message with a specific color."""
    print_colored(f"✅ {message}", COLOR_SUCCESS)


def print_warning(message: str) -> None:
    """Print a warning message with a specific color."""
    print_colored(f"⚠️  {message}", COLOR_WARNING)


def generate_gradient(colors: List[Tuple[int, int, int]], steps: int) -> List[str]:
    """Generate a list of color codes for a smooth multi-color gradient."""
    gradient = []
    segments = len(colors) - 1
    steps_per_segment = max(1, steps // segments)

    for i in range(segments):
        start_color = colors[i]
        end_color = colors[i + 1]
        for j in range(steps_per_segment):
            t = j / steps_per_segment
            r = int(start_color[0] * (1 - t) + end_color[0] * t)
            g = int(start_color[1] * (1 - t) + end_color[1] * t)
            b = int(start_color[2] * (1 - t) + end_color[2] * t)
            gradient.append(f"\033[38;2;{r};{g};{b}m")

    return gradient


def strip_ansi(text: str) -> str:
    """Remove ANSI color codes from a string."""
    ansi_escape = re.compile(r"\x1B[@-_][0-?]*[ -/]*[@-~]")
    return ansi_escape.sub("", text)


def apply_gradient(text: str, gradient: List[str], line_number: int) -> str:
    """Apply gradient colors diagonally to text."""
    return "".join(
        f"{gradient[(i + line_number) % len(gradient)]}{char}"
        for i, char in enumerate(text)
    )


def center_text(text: str, width: int) -> str:
    """Center text, accounting for ANSI color codes and Unicode widths."""
    visible_length = wcswidth(strip_ansi(text))
    padding = (width - visible_length) // 2
    return f"{' ' * padding}{text}{' ' * (width - padding - visible_length)}"


def center_block(block: List[str], width: int) -> List[str]:
    """Center a block of text within a given width."""
    return [center_text(line, width) for line in block]


def create_banner() -> str:
    """Create a FULL RGB banner with diagonal gradient."""
    banner_width = 80
    content_width = banner_width - 4  # Accounting for border characters
    cosmic_gradient = generate_gradient(GRADIENT_COLORS, banner_width)

    logo = [
        "███████╗██╗ ██████╗ ███╗   ██╗ █████╗ ██╗     ██████╗  ██████╗ ██████╗ ",
        "██╔════╝██║██╔════╝ ████╗  ██║██╔══██╗██║     ██╔══██╗██╔════╝ ██╔══██╗",
        "███████╗██║██║  ███╗██╔██╗ ██║███████║██║     ██████╔╝██║  ███╗██████╔╝",
        "╚════██║██║██║   ██║██║╚██╗██║██╔══██║██║     ██╔══██╗██║   ██║██╔══██╗",
        "███████║██║╚██████╔╝██║ ╚████║██║  ██║███████╗██║  ██║╚██████╔╝██████╔╝",
        "╚══════╝╚═╝ ╚═════╝ ╚═╝  ╚═══╝╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚═════╝ ",
        center_text("🏠 Home Assistant Integration 🏠", content_width),
    ]

    centered_logo = center_block(logo, content_width)

    banner = [
        center_text(f"{COLOR_STAR}･ ｡ ☆ ∴｡　　･ﾟ*｡★･ ∴｡　　･ﾟ*｡☆ ･ ｡ ☆ ∴｡", banner_width),
        f"{COLOR_BORDER}╭{'─' * (banner_width - 2)}╮",
    ]

    for line_number, line in enumerate(centered_logo):
        gradient_line = apply_gradient(line, cosmic_gradient, line_number)
        banner.append(f"{COLOR_BORDER}│ {gradient_line} {COLOR_BORDER}│")

    release_manager_text = COLOR_STEP + "Release Manager"

    banner.extend(
        [
            f"{COLOR_BORDER}╰{'─' * (banner_width - 2)}╯",
            center_text(
                f"{COLOR_STAR}∴｡　　･ﾟ*｡☆ {release_manager_text}{COLOR_STAR} ☆｡*ﾟ･　 ｡∴",
                banner_width,
            ),
            center_text(
                f"{COLOR_STAR}･ ｡ ☆ ∴｡　　･ﾟ*｡★･ ∴｡　　･ﾟ*｡☆ ･ ｡ ☆ ∴｡", banner_width
            ),
        ]
    )

    return "\n".join(banner)


def print_logo() -> None:
    """Print the banner/logo for the release manager."""
    print(create_banner())


def check_tool_installed(tool_name: str) -> None:
    """Check if a tool is installed."""
    if shutil.which(tool_name) is None:
        print_error(f"{tool_name} is not installed. Please install it and try again.")
        sys.exit(1)


def get_current_version() -> str:
    """Get the current version from the manifest file."""
    try:
        manifest_path = os.path.join("custom_components", "signalrgb", "manifest.json")
        with open(manifest_path, "r", encoding="utf-8") as file:
            manifest = json.load(file)
            version = manifest.get("version")
            if version is None or not isinstance(version, str):
                raise ValueError("Version not found or invalid in manifest.json")
            return str(version)
    except FileNotFoundError:
        print_error("manifest.json not found.")
        sys.exit(1)
    except json.JSONDecodeError:
        print_error("Invalid JSON in manifest.json.")
        sys.exit(1)


def update_manifest(new_version: str) -> None:
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


def update_pyproject_toml(new_version: str) -> None:
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


def copy_integration(src_path: str, dest_path: str) -> None:
    """Copy the integration from source to destination."""
    try:
        if os.path.exists(dest_path):
            shutil.rmtree(dest_path)
        shutil.copytree(src_path, dest_path)
        print_success(f"Copied integration from {src_path} to {dest_path}")
    except Exception as e:
        print_error(f"Failed to copy integration: {str(e)}")
        sys.exit(1)


def commit_and_push(version: str) -> None:
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


def update_hass() -> None:
    """Update the Home Assistant integration."""
    print_step("Updating Home Assistant integration")
    src_path = os.path.join(os.getcwd(), "custom_components", "signalrgb")
    dest_path = os.path.join(CUSTOM_COMPONENTS_DIR, "signalrgb")
    copy_integration(src_path, dest_path)
    print_success("Home Assistant integration updated")
    print_colored(
        "⚠️  Remember to reload Home Assistant to apply the changes.",
        COLOR_BUILD_SUCCESS,
    )


def confirm_release(new_version: str) -> bool:
    """Prompt the user to confirm the release."""
    print_warning(f"You are about to release version {new_version} of {PROJECT_NAME}.")
    print_warning(
        "This action will update the manifest, commit changes, and push to the repository."
    )
    confirmation = input(
        f"{COLOR_VERSION_PROMPT}Are you sure you want to proceed? (y/N): {COLOR_RESET}"
    ).lower()
    return confirmation == "y"


def main() -> None:
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
        print_colored(f"Current version: {current_version}", COLOR_STEP)
        print_colored(f"New version: {args.version}", COLOR_VERSION_PROMPT)

        if not confirm_release(args.version):
            print_warning("Release process aborted.")
            sys.exit(0)

        update_manifest(args.version)
        update_pyproject_toml(args.version)
        commit_and_push(args.version)

        print_success(
            f"\n🎉✨ {PROJECT_NAME} v{args.version} has been successfully prepared for release! ✨🎉"
        )
        print_colored(
            "Note: The GitHub release will be created by CI.", COLOR_BUILD_SUCCESS
        )


if __name__ == "__main__":
    main()
