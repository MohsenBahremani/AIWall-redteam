#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mohsen Bah
# SPDX-License-Identifier: Apache-2.0
"""Offline checks for generate_report + campaign dry-run."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from generate_report import (  # noqa: E402
    SCHEMA,
    _normalize_findings,
    build_report,
    generate_from_indir,
    render_markdown,
    write_report,
)


def test_build_and_render() -> None:
    payloads = {
        "schema": "aiwall.redteam.payload_results.v1",
        "target": "http://127.0.0.1:8080",
        "results": [
            {
                "id": "SE-01",
                "technique_id": "SE-01",
                "category": "secret-exfiltration",
                "must_hold": True,
                "outcome": "hold",
                "detail": "hold",
                "http_status": 403,
            },
            {
                "id": "SE-99",
                "technique_id": "SE-99",
                "category": "secret-exfiltration",
                "must_hold": True,
                "outcome": "bypass",
                "detail": "must_hold bypass",
                "http_status": 200,
            },
        ],
    }
    pyrit = {
        "schema": "aiwall.redteam.pyrit_report.v1",
        "results": [
            {
                "id": "smoke-hold-secret",
                "mode": "hold",
                "technique_id": "SE-01",
                "outcome": "hold",
                "detail": "ok",
            }
        ],
    }
    report = build_report(
        campaign_id="test-campaign",
        target="http://127.0.0.1:8080",
        findings=_normalize_findings(payloads=payloads, pyrit=pyrit),
        sources={"payloads": "p.json", "pyrit": "r.json"},
    )
    assert report["schema"] == SCHEMA
    assert report["summary"]["must_hold_bypasses"] == 1
    assert report["summary"]["holds"] >= 1
    assert len(report["product_followups"]) == 1
    md = render_markdown(report)
    assert "must-hold bypasses" in md.lower() or "Product follow-ups" in md
    assert "SE-99" in md


def test_indir_roundtrip() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        indir = Path(tmp)
        (indir / "meta.json").write_text(
            json.dumps(
                {
                    "campaign_id": "c-tmp",
                    "target": "http://lab",
                    "notes": "n",
                }
            )
        )
        (indir / "payloads.json").write_text(
            json.dumps(
                {
                    "schema": "aiwall.redteam.payload_results.v1",
                    "target": "http://lab",
                    "results": [
                        {
                            "id": "x",
                            "technique_id": "PI-01",
                            "category": "prompt-injection",
                            "must_hold": False,
                            "outcome": "recorded",
                            "detail": "ok",
                            "http_status": 200,
                        }
                    ],
                }
            )
        )
        report = generate_from_indir(indir)
        assert report["campaign_id"] == "c-tmp"
        json_path, md_path = write_report(report, indir)
        assert json_path.is_file() and md_path.is_file()
        loaded = json.loads(json_path.read_text())
        assert loaded["summary"]["total"] == 1


def test_cli_exit_on_bypass() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        indir = Path(tmp)
        (indir / "meta.json").write_text(json.dumps({"campaign_id": "bye", "target": "t"}))
        (indir / "payloads.json").write_text(
            json.dumps(
                {
                    "results": [
                        {
                            "id": "bad",
                            "technique_id": "SE-01",
                            "category": "secret-exfiltration",
                            "must_hold": True,
                            "outcome": "bypass",
                            "detail": "open",
                        }
                    ]
                }
            )
        )
        rc = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "generate_report.py"), "--indir", str(indir)],
            check=False,
        ).returncode
        assert rc == 1


def test_campaign_dry_run() -> None:
    script = ROOT / "scripts" / "run_campaign.sh"
    assert script.is_file()
    proc = subprocess.run(
        ["bash", str(script), "--dry-run", "--skip-pyrit"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert "Campaign finished:" in proc.stdout
    # Find newest campaign dir
    reports = sorted((ROOT / "reports").glob("campaign-smoke-*"), key=lambda p: p.stat().st_mtime)
    assert reports, "expected a campaign-smoke-* directory"
    latest = reports[-1]
    assert (latest / "campaign-report.md").is_file()
    assert (latest / "campaign-report.json").is_file()
    data = json.loads((latest / "campaign-report.json").read_text())
    assert data["schema"] == SCHEMA
    assert data["summary"]["total"] >= 1


def main() -> int:
    tests = [
        test_build_and_render,
        test_indir_roundtrip,
        test_cli_exit_on_bypass,
        test_campaign_dry_run,
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
