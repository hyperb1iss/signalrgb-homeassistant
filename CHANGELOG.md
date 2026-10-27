# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

- Require Home Assistant 2026.10.4 or newer and use its current form schemas.
- Use the documented SignalRGB API v1 with Home Assistant's shared HTTP session.
- Share typed runtime data and a coordinator across entities, with immediate
  state refreshes after commands.
- Update the development dependencies and CI, and separate local release
  preparation from tag-triggered publication.
- Replace obsolete API setup instructions with local and network connection
  checks, and document integration scope and application URL alternatives.

### Added

- Reconfiguration of an existing connection's host and port.

### Fixed

- Avoid temporary HTTP client leaks during configuration validation (the
  cleanup problem reported by @Tycorc in PR #17).
- Keep the preset selection unknown until applied locally instead of assuming
  the first available preset is active.

## [1.1.0] - 2026-04-08

### Added

- Granular exception handling for `ConnectionError`, `APIError`, and `NotFoundError`
  from the SignalRGB SDK; clearer log messages when something goes wrong
- `make coverage`, `make typecheck`, and `make fix` targets
- `CHANGELOG.md` (this file)
- Pre-commit safety hooks: `check-json`, `check-toml`, `check-added-large-files`,
  `check-merge-conflict`, `detect-private-key`, `check-case-conflict`, `mixed-line-ending`

### Changed

- **Minimum Home Assistant version bumped to 2026.4.0** (requires Python 3.14.2+)
- Coordinator polling now uses `get_current_state()`; drops from 4 API round-trips
  per poll cycle to 2
- Type checking migrated from mypy to [ty](https://docs.astral.sh/ty/) (Astral's
  Rust-based type checker)
- Linting consolidated to ruff only; pylint removed
- CI migrated to [hyperb1iss/shared-workflows](https://github.com/hyperb1iss/shared-workflows):
  `python-ci.yml@v1` for lint + test, `github-release.yml@v1` for AI-authored release notes
- Ruff line-length bumped 88 → 100 to match the Astral stack conventions
- Entity IDs no longer explicitly set; HA auto-generates from `unique_id` + device
  name (fixes invalid entity IDs on HA 2026.02+ which rejected ULID-derived uppercase)
- Coordinator raises `UpdateFailed` instead of `HomeAssistantError` (the former is
  the correct exception type for `DataUpdateCoordinator.update_method`)

### Removed

- `pylint` and `mypy` dev dependencies (replaced by `ruff` + `ty`)
- Legacy `requirements.txt` (redundant with `pyproject.toml`)
- Explicit `entity_id` assignments in light, button, and select entities

### Fixed

- Pre-commit `ruff-format` hook had a files regex copy-pasted from HA core that
  excluded `custom_components/`; pre-commit wasn't actually formatting the source
- Pre-commit hook versions no longer diverge from `pyproject.toml` dev deps
- Missing trailing newline in `translations/en.json`

## [1.0.1] - 2025-07-06

### Changed

- Update all dependencies to latest versions

## [1.0.0] - 2025-03-15

### Added

- Migrate to the async SignalRGB client for non-blocking HA integration
- Move client initialization to executor to avoid blocking the event loop
  during SSL certificate operations
- `uv lock` step in the release process

### Changed

- Bump SignalRGB SDK dependency to v1.0.0
- Improve UI responsiveness with faster state updates

## [0.8.0] and earlier

See the [git history](https://github.com/hyperb1iss/signalrgb-homeassistant/commits/main)
and [releases page](https://github.com/hyperb1iss/signalrgb-homeassistant/releases) for
details on earlier versions.

[Unreleased]: https://github.com/hyperb1iss/signalrgb-homeassistant/compare/v1.1.0...HEAD
[1.1.0]: https://github.com/hyperb1iss/signalrgb-homeassistant/compare/v1.0.1...v1.1.0
[1.0.1]: https://github.com/hyperb1iss/signalrgb-homeassistant/compare/v1.0.0...v1.0.1
[1.0.0]: https://github.com/hyperb1iss/signalrgb-homeassistant/compare/v0.8.0...v1.0.0
