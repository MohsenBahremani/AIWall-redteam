#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mohsen Bah
# SPDX-License-Identifier: Apache-2.0
"""Offline + stub checks for the must-block regression suite."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from run_regression import (  # noqa: E402
    load_registry,
    registry_ids,
    validate_registry_against_payloads,
)


def test_registry() -> None:
    data = load_registry()
    ids = registry_ids(data)
    assert ids == ["SE-01", "SE-02", "SE-03"], ids
    errors = validate_registry_against_payloads(data)
    assert not errors, errors
    baseline = (ROOT / "reports" / "baseline-assessment.md").read_text()
    for cid in ids:
        assert cid in baseline, f"{cid} missing from baseline doc"


def test_stub_holds() -> None:
    rc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "run_regression.py"), "--stub"],
        cwd=str(ROOT),
        check=False,
    ).returncode
    assert rc == 0, "must-block suite must pass against hold stub"


def test_bypass_fails_ci() -> None:
    """Acceptance: suite exits non-zero when a previously-blocked attack succeeds."""
    rc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "run_regression.py"), "--expect-fail"],
        cwd=str(ROOT),
        check=False,
    ).returncode
    assert rc == 0, "expect-fail self-check should succeed (inner suite fails)"


def test_list() -> None:
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "run_regression.py"), "--list"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0
    assert "SE-01" in proc.stdout
    assert "3 must-block" in proc.stdout


def main() -> int:
    # ensure registry JSON is valid UTF-8 object
    raw = json.loads((ROOT / "regression" / "must_block.json").read_text())
    assert raw["schema"] == "aiwall.redteam.must_block.v1"

    tests = [test_registry, test_list, test_stub_holds, test_bypass_fails_ci]
    failed = 0
    for fn in tests:
        try:
            fn()
            print(f"ok  {fn.__name__}")
        except Exception as exc:  # noqa: BLE001
            failed += 1
            print(f"FAIL {fn.__name__}: {exc}", file=sys.stderr)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
