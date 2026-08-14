#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mohsen Bah
# SPDX-License-Identifier: Apache-2.0
"""Compare two campaign / payload result JSON files (before vs after).

Produces per-attack outcome deltas for post-mitigation retest reports.

Examples::

    python3 scripts/compare_campaigns.py \\
      --before reports/baseline-campaign-report.json \\
      --after reports/retest-campaign-report.json \\
      -o reports/retest-delta
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "aiwall.redteam.campaign_delta.v1"


def _load(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text())
    if not isinstance(data, dict):
        raise SystemExit(f"{path}: expected object")
    return data


def _findings_by_id(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for row in report.get("findings") or report.get("results") or []:
        fid = str(row.get("id") or "")
        if not fid:
            continue
        out[fid] = row
    return out


def _outcome(row: dict[str, Any] | None) -> str:
    if row is None:
        return "(missing)"
    return str(row.get("outcome") or "unknown")


def compare(
    *,
    before: dict[str, Any],
    after: dict[str, Any],
    before_label: str,
    after_label: str,
) -> dict[str, Any]:
    b_map = _findings_by_id(before)
    a_map = _findings_by_id(after)
    ids = sorted(set(b_map) | set(a_map))

    deltas: list[dict[str, Any]] = []
    changed = 0
    improved = 0  # bypass/skip/error → hold
    regressed = 0  # hold → bypass/error
    unchanged = 0

    improve_from = {"bypass", "fail", "error", "recorded", "skip", "inconclusive"}
    # treat recorded/skip as non-hold for "improved to hold"
    for fid in ids:
        b = b_map.get(fid)
        a = a_map.get(fid)
        bo, ao = _outcome(b), _outcome(a)
        status = "unchanged" if bo == ao else "changed"
        if status == "unchanged":
            unchanged += 1
        else:
            changed += 1
            if ao == "hold" and bo != "hold":
                improved += 1
                status = "improved"
            elif bo == "hold" and ao in {"bypass", "fail", "error"}:
                regressed += 1
                status = "regressed"
            elif bo == "hold" and ao != "hold":
                # hold → skip etc.
                if ao in {"bypass", "fail", "error"}:
                    regressed += 1
                    status = "regressed"
                else:
                    status = "changed"

        deltas.append(
            {
                "id": fid,
                "technique_id": (a or b or {}).get("technique_id") or "",
                "category": (a or b or {}).get("category") or "",
                "before": bo,
                "after": ao,
                "status": status,
                "before_detail": (b or {}).get("detail") or "",
                "after_detail": (a or {}).get("detail") or "",
                "must_hold": bool((a or b or {}).get("must_hold")),
            }
        )

    return {
        "schema": SCHEMA,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "before_label": before_label,
        "after_label": after_label,
        "summary": {
            "total": len(ids),
            "unchanged": unchanged,
            "changed": changed,
            "improved": improved,
            "regressed": regressed,
        },
        "deltas": deltas,
    }


def render_markdown(delta: dict[str, Any]) -> str:
    s = delta["summary"]
    lines = [
        f"# Campaign delta: `{delta['before_label']}` → `{delta['after_label']}`",
        "",
        f"- Generated: `{delta['generated_at']}`",
        f"- Schema: `{delta['schema']}`",
        "",
        "## Summary",
        "",
        "| Metric | Count |",
        "|---|---|",
        f"| Techniques compared | {s['total']} |",
        f"| Unchanged | {s['unchanged']} |",
        f"| Changed | {s['changed']} |",
        f"| Improved (→ hold) | {s['improved']} |",
        f"| Regressed (hold → fail) | {s['regressed']} |",
        "",
        "## Per-attack deltas",
        "",
        "| Id | Category | Before | After | Status |",
        "|---|---|---|---|---|",
    ]
    for d in delta["deltas"]:
        lines.append(
            f"| `{d['id']}` | {d.get('category') or '—'} | **{d['before']}** | "
            f"**{d['after']}** | {d['status']} |"
        )
    lines.extend(
        [
            "",
            "## Changed detail",
            "",
        ]
    )
    changed_rows = [d for d in delta["deltas"] if d["status"] != "unchanged"]
    if not changed_rows:
        lines.append("_No outcome changes._")
    else:
        for d in changed_rows:
            lines.append(
                f"- **`{d['id']}`** ({d['status']}): `{d['before']}` → `{d['after']}` "
                f"— before: {d.get('before_detail')!r}; after: {d.get('after_detail')!r}"
            )
    lines.extend(["", "---", "", "See `docs/testing-methodology.md` and RoE.", ""])
    return "\n".join(lines)


def write_delta(delta: dict[str, Any], out_dir: Path) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "campaign-delta.json"
    md_path = out_dir / "campaign-delta.md"
    json_path.write_text(json.dumps(delta, indent=2) + "\n")
    md_path.write_text(render_markdown(delta))
    return json_path, md_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--before", required=True, help="Baseline campaign-report.json")
    parser.add_argument("--after", required=True, help="Retest campaign-report.json")
    parser.add_argument("--before-label", default="")
    parser.add_argument("--after-label", default="")
    parser.add_argument(
        "-o",
        "--out",
        default="",
        help="Output directory (default: reports/delta-<stamp>)",
    )
    args = parser.parse_args(argv)

    before_path = Path(args.before)
    after_path = Path(args.after)
    before = _load(before_path)
    after = _load(after_path)

    before_label = (
        args.before_label
        or before.get("campaign_id")
        or before_path.stem
    )
    after_label = args.after_label or after.get("campaign_id") or after_path.stem

    delta = compare(
        before=before,
        after=after,
        before_label=str(before_label),
        after_label=str(after_label),
    )

    if args.out:
        out_dir = Path(args.out)
    else:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        out_dir = ROOT / "reports" / f"delta-{stamp}"

    json_path, md_path = write_delta(delta, out_dir)
    s = delta["summary"]
    print(f"delta  {md_path}")
    print(f"json   {json_path}")
    print(
        f"summary unchanged={s['unchanged']} changed={s['changed']} "
        f"improved={s['improved']} regressed={s['regressed']}"
    )
    return 1 if s["regressed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
