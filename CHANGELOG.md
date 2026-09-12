# Changelog

## [Unreleased]

### Changed

- README headings no longer carry internal roadmap numbers (`Garak (7.4)` is now `Garak`). Section order and content are unchanged.

### Fixed

- Regression runner corrected, and the PyRIT/Garak lab scripts hardened.
- Payload stub test passes `model_override` for `cmd_run`.

## [0.1.0] - 2026-08-27

### Added

- Attack catalog, payload library, Garak/PyRIT runners, and campaign scripts.
- Regression `must_block.json` and bridge docs to AIWall-detections.

### Compatibility

- Expects AIWall audit export `aiwall.audit.v1` and detection pack `0.1.0` for reason/hit alignment.
