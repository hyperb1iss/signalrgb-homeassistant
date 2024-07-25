#!/usr/bin/env python

import os
import shutil
import json
import subprocess
import argparse
from collections import OrderedDict

BASE_PATH = "/home/bliss/dev"
PROJECT_LINK = "https://github.com/hyperb1iss/signalrgb-homeassistant"
ISSUE_TRACKER = f"{PROJECT_LINK}/issues"


def copy_integration(src_path, dest_path):
    if os.path.exists(dest_path):
        shutil.rmtree(dest_path)
    shutil.copytree(src_path, dest_path)
    print(f"Copied integration from {src_path} to {dest_path}")


def update_manifest_version(manifest_path, new_version):
    with open(manifest_path, "r") as f:
        manifest = json.load(f)

    # Update version and links
    manifest["version"] = new_version
    manifest["documentation"] = PROJECT_LINK
    manifest["issue_tracker"] = ISSUE_TRACKER

    # Create a new OrderedDict with the required order
    ordered_manifest = OrderedDict()
    ordered_manifest["domain"] = manifest["domain"]
    ordered_manifest["name"] = manifest["name"]

    # Add the rest of the items in alphabetical order
    for key in sorted(manifest.keys()):
        if key not in ["domain", "name"]:
            ordered_manifest[key] = manifest[key]

    with open(manifest_path, "w") as f:
        json.dump(ordered_manifest, f, indent=2)

    print(f"Updated manifest version to {new_version} and reordered entries")


def git_commit_and_tag(version):
    commit_message = f"Release version {version}"
    subprocess.run(["git", "add", "custom_components"], check=True)
    subprocess.run(["git", "commit", "-m", commit_message], check=True)
    subprocess.run(
        ["git", "tag", "-a", f"v{version}", "-m", f"Version {version}"], check=True
    )
    print(f"Changes committed and tagged as v{version}")


def main():
    parser = argparse.ArgumentParser(
        description="Release management for SignalRGB Home Assistant integration"
    )
    parser.add_argument("version", help="New version number for the release")
    args = parser.parse_args()

    # Paths
    ha_src_path = f"{BASE_PATH}/ha_core/homeassistant/components/signalrgb"
    custom_components_path = (
        f"{BASE_PATH}/signalrgb-homeassistant/custom_components/signalrgb"
    )
    manifest_path = os.path.join(custom_components_path, "manifest.json")

    # Copy integration files
    copy_integration(ha_src_path, custom_components_path)

    # Update manifest version
    update_manifest_version(manifest_path, args.version)

    # Commit changes and create tag
    git_commit_and_tag(args.version)

    print("Release process completed successfully!")


if __name__ == "__main__":
    main()
