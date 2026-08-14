#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mohsen Bah
# SPDX-License-Identifier: Apache-2.0
"""Aggregate campaign artifacts into JSON + Markdown reports.

Reads optional files from a campaign directory:

  payloads.json   (schema aiwall.redteam.payload_results.v1)
  pyrit.json      (schema aiwall.redteam.pyrit_report.v1)
  meta.json       (campaign id, target, notes — written by run_campaign.sh)
  garak/          (optional; presence noted in report)

Examples::

    python3 scripts/generate_report.py --indir reports/campaign-20260101T120000Z
    python3 scripts/generate_report.py --payloads /tmp/p.json --pyrit /tmp/r.json -o /tmp/out
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "aiwall.redteam.campaign_report.v1"


def _load_json(path: Path | None) -> dict[str, Any] | None:
    if path is None or not path.is_file():
        return None
    data = json.loads(path.read_text())
    return data if isinstance(data, dict) else None


def _normalize_findings(
    *,
    payloads: dict[str, Any] | None,
    pyrit: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []

    if payloads:
        for row in payloads.get("results") or []:
            findings.append(
                {
                    "source": "payload",
                    "id": row.get("id"),
                    "technique_id": row.get("technique_id") or "",
                    "category": row.get("category") or "",
                    "must_hold": bool(row.get("must_hold")),
                    "outcome": row.get("outcome") or "unknown",
                    "detail": row.get("detail") or "",
                    "http_status": row.get("http_status"),
                }
            )

    if pyrit:
        for row in pyrit.get("results") or []:
            findings.append(
                {
                    "source": "pyrit",
                    "id": row.get("id"),
                    "technique_id": row.get("technique_id") or "",
                    "category": "",
                    "must_hold": (row.get("mode") or "") == "hold",
                    "outcome": row.get("outcome") or "unknown",
                    "detail": row.get("detail") or "",
                    "http_status": None,
                }
            )

    return findings


def _summarize(findings: list[dict[str, Any]]) -> dict[str, Any]:
    outcomes = Counter(str(f.get("outcome") or "unknown") for f in findings)
    by_category: dict[str, Counter[str]] = {}
    for f in findings:
        cat = str(f.get("category") or "(uncategorized)")
        by_category.setdefault(cat, Counter())[str(f.get("outcome") or "unknown")] += 1

    actionable_bypass = [
        f
        for f in findings
        if f.get("must_hold") and f.get("outcome") == "bypass"
    ]
    return {
        "total": len(findings),
        "outcomes": dict(outcomes),
        "holds": outcomes.get("hold", 0) + outcomes.get("recorded", 0),
        "bypasses": outcomes.get("bypass", 0),
        "errors": outcomes.get("error", 0) + outcomes.get("fail", 0),
        "skipped": outcomes.get("skip", 0),
        "must_hold_bypasses": len(actionable_bypass),
        "by_category": {k: dict(v) for k, v in sorted(by_category.items())},
    }


def build_report(
    *,
    campaign_id: str,
    target: str,
    findings: list[dict[str, Any]],
    sources: dict[str, Any],
    notes: str = "",
) -> dict[str, Any]:
    summary = _summarize(findings)
    return {
        "schema": SCHEMA,
        "campaign_id": campaign_id,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "target": target,
        "notes": notes,
        "summary": summary,
        "sources": sources,
        "findings": findings,
        "product_followups": [
            {
                "id": f.get("id"),
                "technique_id": f.get("technique_id"),
                "source": f.get("source"),
                "detail": f.get("detail"),
            }
            for f in findings
            if f.get("must_hold") and f.get("outcome") == "bypass"
        ],
    }


def render_markdown(report: dict[str, Any]) -> str:
    s = report["summary"]
    lines = [
        f"# Campaign report: `{report['campaign_id']}`",
        "",
        f"- Generated: `{report['generated_at']}`",
        f"- Target: `{report.get('target') or '(unknown)'}`",
        f"- Schema: `{report['schema']}`",
        "",
        "## Summary",
        "",
        f"| Metric | Count |",
        f"|---|---|",
        f"| Total findings | {s['total']} |",
        f"| Holds / recorded | {s['holds']} |",
        f"| Bypasses | {s['bypasses']} |",
        f"| Must-hold bypasses | {s['must_hold_bypasses']} |",
        f"| Errors | {s['errors']} |",
        f"| Skipped | {s['skipped']} |",
        "",
        "## By category",
        "",
    ]
    by_cat = s.get("by_category") or {}
    if by_cat:
        lines.append("| Category | Outcomes |")
        lines.append("|---|---|")
        for cat, oc in by_cat.items():
            bits = ", ".join(f"{k}={v}" for k, v in sorted(oc.items()))
            lines.append(f"| {cat} | {bits} |")
        lines.append("")
    else:
        lines.append("_No categorized findings._")
        lines.append("")

    followups = report.get("product_followups") or []
    lines.append("## Product follow-ups (must-hold bypasses)")
    lines.append("")
    if followups:
        for item in followups:
            lines.append(
                f"- `{item.get('id')}` ({item.get('technique_id') or '?'}, "
                f"{item.get('source')}): {item.get('detail')}"
            )
    else:
        lines.append("_None — no must-hold bypasses in this run._")
    lines.append("")

    lines.append("## Findings")
    lines.append("")
    lines.append("| Source | ID | Technique | Outcome | Detail |")
    lines.append("|---|---|---|---|---|")
    for f in report.get("findings") or []:
        detail = str(f.get("detail") or "").replace("|", "\\|")[:80]
        lines.append(
            f"| {f.get('source')} | `{f.get('id')}` | {f.get('technique_id') or '—'} | "
            f"**{f.get('outcome')}** | {detail} |"
        )
    lines.append("")

    sources = report.get("sources") or {}
    lines.append("## Sources")
    lines.append("")
    for key, val in sources.items():
        lines.append(f"- **{key}**: `{val}`")
    if report.get("notes"):
        lines.extend(["", "## Notes", "", str(report["notes"]), ""])
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(
        "Authorized lab use only. See `docs/rules-of-engagement.md` and "
        "`docs/testing-methodology.md`."
    )
    lines.append("")
    return "\n".join(lines)


def write_report(report: dict[str, Any], out_dir: Path) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "campaign-report.json"
    md_path = out_dir / "campaign-report.md"
    json_path.write_text(json.dumps(report, indent=2) + "\n")
    md_path.write_text(render_markdown(report))
    return json_path, md_path


def generate_from_indir(indir: Path) -> dict[str, Any]:
    meta = _load_json(indir / "meta.json") or {}
    payloads = _load_json(indir / "payloads.json")
    pyrit = _load_json(indir / "pyrit.json")
    findings = _normalize_findings(payloads=payloads, pyrit=pyrit)
    target = (
        meta.get("target")
        or (payloads or {}).get("target")
        or ""
    )
    sources: dict[str, Any] = {}
    if payloads is not None:
        sources["payloads"] = str(indir / "payloads.json")
    if pyrit is not None:
        sources["pyrit"] = str(indir / "pyrit.json")
    garak_dir = indir / "garak"
    if garak_dir.is_dir() and any(garak_dir.iterdir()):
        sources["garak"] = str(garak_dir)
    return build_report(
        campaign_id=str(meta.get("campaign_id") or indir.name),
        target=str(target),
        findings=findings,
        sources=sources,
        notes=str(meta.get("notes") or ""),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--indir",
        default="",
        help="Campaign directory containing payloads.json / pyrit.json / meta.json",
    )
    parser.add_argument("--payloads", default="", help="Explicit payloads.json path")
    parser.add_argument("--pyrit", default="", help="Explicit pyrit.json path")
    parser.add_argument("--campaign-id", default="", help="Override campaign id")
    parser.add_argument("--target", default="", help="Override target URL")
    parser.add_argument(
        "-o",
        "--out",
        default="",
        help="Output directory (default: --indir, or reports/generated)",
    )
    args = parser.parse_args(argv)

    if args.indir:
        indir = Path(args.indir)
        if not indir.is_dir():
            print(f"missing indir: {indir}", file=sys.stderr)
            return 1
        report = generate_from_indir(indir)
        out_dir = Path(args.out) if args.out else indir
    else:
        payloads = _load_json(Path(args.payloads)) if args.payloads else None
        pyrit = _load_json(Path(args.pyrit)) if args.pyrit else None
        if payloads is None and pyrit is None:
            print("provide --indir or --payloads/--pyrit", file=sys.stderr)
            return 1
        findings = _normalize_findings(payloads=payloads, pyrit=pyrit)
        campaign_id = args.campaign_id or "ad-hoc"
        target = args.target or (payloads or {}).get("target") or ""
        sources = {}
        if args.payloads:
            sources["payloads"] = args.payloads
        if args.pyrit:
            sources["pyrit"] = args.pyrit
        report = build_report(
            campaign_id=campaign_id,
            target=str(target),
            findings=findings,
            sources=sources,
        )
        out_dir = Path(args.out) if args.out else ROOT / "reports" / "generated"

    if args.campaign_id:
        report["campaign_id"] = args.campaign_id
    if args.target:
        report["target"] = args.target

    json_path, md_path = write_report(report, out_dir)
    s = report["summary"]
    print(f"report {md_path}")
    print(f"json   {json_path}")
    print(
        f"summary holds={s['holds']} bypasses={s['bypasses']} "
        f"must_hold_bypasses={s['must_hold_bypasses']} errors={s['errors']} "
        f"skipped={s['skipped']} total={s['total']}"
    )
    # Non-zero if must-hold bypasses (useful for CI later)
    return 1 if s["must_hold_bypasses"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
