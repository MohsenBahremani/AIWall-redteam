#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mohsen Bah
# SPDX-License-Identifier: Apache-2.0
"""Offline checks for campaign delta compare (Phase 7.9)."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from compare_campaigns import SCHEMA, compare, render_markdown, write_delta  # noqa: E402


def _report(findings: list[dict]) -> dict:
    return {"campaign_id": "t", "findings": findings}


def test_unchanged() -> None:
    rows = [
        {"id": "SE-01", "category": "secret-exfiltration", "must_hold": True, "outcome": "hold"},
        {"id": "PI-01", "category": "prompt-injection", "must_hold": False, "outcome": "skip"},
    ]
    delta = compare(
        before=_report(rows),
        after=_report(rows),
        before_label="b",
        after_label="a",
    )
    assert delta["schema"] == SCHEMA
    assert delta["summary"]["unchanged"] == 2
    assert delta["summary"]["regressed"] == 0


def test_improved_and_regressed() -> None:
    before = _report(
        [
            {"id": "UC-01", "outcome": "skip", "must_hold": True, "category": "unsafe-content"},
            {"id": "SE-01", "outcome": "hold", "must_hold": True, "category": "secret-exfiltration"},
        ]
    )
    after = _report(
        [
            {"id": "UC-01", "outcome": "hold", "must_hold": True, "category": "unsafe-content"},
            {"id": "SE-01", "outcome": "bypass", "must_hold": True, "category": "secret-exfiltration"},
        ]
    )
    delta = compare(before=before, after=after, before_label="b", after_label="a")
    assert delta["summary"]["improved"] == 1
    assert delta["summary"]["regressed"] == 1
    md = render_markdown(delta)
    assert "UC-01" in md and "SE-01" in md


def test_cli_baseline_vs_retest() -> None:
    before = ROOT / "reports" / "baseline-campaign-report.json"
    after = ROOT / "reports" / "retest-campaign-report.json"
    assert before.is_file() and after.is_file()
    with tempfile.TemporaryDirectory() as tmp:
        rc = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "compare_campaigns.py"),
                "--before",
                str(before),
                "--after",
                str(after),
                "-o",
                tmp,
            ],
            check=False,
        ).returncode
        assert rc == 0
        data = json.loads(Path(tmp, "campaign-delta.json").read_text())
        assert data["summary"]["regressed"] == 0
        assert data["summary"]["unchanged"] == 14


def test_post_mitigation_doc() -> None:
    path = ROOT / "reports" / "post-mitigation-retest.md"
    text = path.read_text()
    for needle in ("SE-01", "unchanged", "before", "after", "delta"):
        assert needle.lower() in text.lower() or needle in text
    snap = ROOT / "reports" / "retest-delta.json"
    assert snap.is_file()
    data = json.loads(snap.read_text())
    assert data["summary"]["regressed"] == 0


def main() -> int:
    tests = [
        test_unchanged,
        test_improved_and_regressed,
        test_cli_baseline_vs_retest,
        test_post_mitigation_doc,
    ]
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
