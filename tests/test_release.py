"""Release versions must agree before publication."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from scripts.release import install_integration, prepare_release, verify_release


@pytest.fixture
def release_tree(tmp_path: Path) -> Path:
    """Create the files shared by PyPI and HACS consumers."""
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "test"\nversion = "1.1.0"\n')
    component = tmp_path / "custom_components/signalrgb"
    component.mkdir(parents=True)
    (component / "manifest.json").write_text('{"domain": "signalrgb", "version": "1.1.0"}')
    return tmp_path


def test_verify_matching_versions(release_tree: Path) -> None:
    """A matching stable tag is eligible for publication."""
    verify_release("v1.1.0", release_tree)


@pytest.mark.parametrize("tag", ["1.1.0", "v1.2.0", "v01.1.0", "v1.1.0rc1", "v$(false)"])
def test_verify_rejects_invalid_release(release_tree: Path, tag: str) -> None:
    """Unmatched or malformed tags cannot publish an artifact."""
    with pytest.raises(ValueError):
        verify_release(tag, release_tree)


def test_verify_rejects_manifest_mismatch(release_tree: Path) -> None:
    """The wheel version alone is insufficient for a HACS release."""
    (release_tree / "custom_components/signalrgb/manifest.json").write_text('{"version":"1.0.0"}')
    with pytest.raises(ValueError, match="must match"):
        verify_release("v1.1.0", release_tree)


def test_prepare_updates_both_versions(release_tree: Path) -> None:
    """Preparation changes local versions and refreshes the lock, without publishing."""
    with patch("scripts.release.subprocess.run") as command:
        prepare_release("1.2.0", release_tree)
    command.assert_called_once_with(["uv", "lock"], cwd=release_tree, check=True)
    verify_release("v1.2.0", release_tree)


@pytest.mark.parametrize("version", ["1.0.0", "1.1.0", "invalid"])
def test_prepare_rejects_non_upgrade(release_tree: Path, version: str) -> None:
    """Rejected releases leave the installation version unchanged."""
    with pytest.raises(ValueError):
        prepare_release(version, release_tree)
    verify_release("v1.1.0", release_tree)


def test_install_requires_config(release_tree: Path, tmp_path: Path) -> None:
    """An arbitrary directory is not silently treated as a Home Assistant install."""
    with pytest.raises(ValueError, match=r"configuration\.yaml"):
        install_integration(tmp_path / "missing", release_tree)


def test_install_preserves_unrelated_files(release_tree: Path, tmp_path: Path) -> None:
    """An upgrade removes stale component modules without touching other integrations."""
    config = tmp_path / "ha"
    config.mkdir()
    (config / "configuration.yaml").touch()
    component = config / "custom_components/signalrgb"
    component.mkdir(parents=True)
    (component / "diagnostics.py").write_text("obsolete")
    unrelated = config / "custom_components/other"
    unrelated.mkdir()
    (unrelated / "__init__.py").write_text("keep")
    install_integration(config, release_tree)
    assert not (component / "diagnostics.py").exists()
    assert (unrelated / "__init__.py").read_text() == "keep"
    assert json.loads((component / "manifest.json").read_text())["version"] == "1.1.0"


def test_install_copy_failure_preserves_existing(release_tree: Path, tmp_path: Path) -> None:
    """A failed staging copy leaves the working installation intact."""
    config = tmp_path / "ha"
    config.mkdir()
    (config / "configuration.yaml").touch()
    component = config / "custom_components/signalrgb"
    component.mkdir(parents=True)
    (component / "__init__.py").write_text("working")
    with (
        patch("scripts.release.shutil.copytree", side_effect=OSError("disk full")),
        pytest.raises(OSError, match="disk full"),
    ):
        install_integration(config, release_tree)
    assert (component / "__init__.py").read_text() == "working"


def test_install_swap_failure_restores_existing(release_tree: Path, tmp_path: Path) -> None:
    """A failed replacement restores the previous component directory."""
    config = tmp_path / "ha"
    config.mkdir()
    (config / "configuration.yaml").touch()
    component = config / "custom_components/signalrgb"
    component.mkdir(parents=True)
    (component / "__init__.py").write_text("working")
    original_rename = Path.rename

    def fail_incoming(path: Path, target: Path) -> Path:
        if path.name == "incoming":
            raise OSError("rename failed")
        return original_rename(path, target)

    with (
        patch.object(Path, "rename", fail_incoming),
        pytest.raises(OSError, match="rename failed"),
    ):
        install_integration(config, release_tree)
    assert (component / "__init__.py").read_text() == "working"


@pytest.mark.parametrize("failure", [OSError("rename failed"), KeyboardInterrupt()])
def test_install_failed_rollback_keeps_backup(
    release_tree: Path, tmp_path: Path, failure: BaseException
) -> None:
    """Even interrupted installs retain the old files if restoration also fails."""
    config = tmp_path / "ha"
    config.mkdir()
    (config / "configuration.yaml").touch()
    component = config / "custom_components/signalrgb"
    component.mkdir(parents=True)
    (component / "__init__.py").write_text("working")
    original_rename = Path.rename

    def fail_replacement_and_restore(path: Path, target: Path) -> Path:
        if path.name in {"incoming", "previous"}:
            raise failure
        return original_rename(path, target)

    with (
        patch.object(Path, "rename", fail_replacement_and_restore),
        pytest.raises(OSError, match="recover it from") as error,
    ):
        install_integration(config, release_tree)
    backups = list((config / "custom_components").glob(".signalrgb-*/previous"))
    assert len(backups) == 1
    assert (backups[0] / "__init__.py").read_text() == "working"
    assert str(backups[0]) in str(error.value)
