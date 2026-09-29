# Changelog

## [Unreleased]

### Changed

- README headings no longer carry internal roadmap numbers (`Garak (7.4)` is now `Garak`). Section order and content are unchanged.
- Jailbreak classifier covers PI-02 safety-bypass framing (`jailbreak-detected`) without a child profile.
- SE-03 notes output DLP (`output-secret-detected`) in addition to input scanning and extraction-rate.
- AT-02 expected hold is `sensitive-file-access:<rule_id>`.
- Attack catalog and PI-01 / PI-03 payloads now describe the shipped injection and jailbreak holds. The README baseline section is labeled as the 2026-08 snapshot.

### Fixed

- Regression runner corrected, and the PyRIT/Garak lab scripts hardened.
- Payload stub test passes `model_override` for `cmd_run`.

## [0.1.0] - 2026-08-27

### Added

- Attack catalog, payload library, Garak/PyRIT runners, and campaign scripts.
- Regression `must_block.json` and bridge docs to AIWall-detections.

### Compatibility

- Expects AIWall audit export `aiwall.audit.v1` and detection pack `0.1.0` for reason/hit alignment.
