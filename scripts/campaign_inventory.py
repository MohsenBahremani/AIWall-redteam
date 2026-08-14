#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mohsen Bah
# SPDX-License-Identifier: Apache-2.0
"""Write inventory-only payloads.json for campaign --dry-run."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from payload_lib import load_all  # noqa: E402


def main() -> int:
    outdir = Path(os.environ["OUTDIR"])
    target = os.environ.get("TARGET", "")
    category = os.environ.get("CATEGORY") or None
    rows = []
    for p in load_all(category):
        exp = p.get("expected") or {}
        rows.append(
            {
                "id": p.get("id"),
                "technique_id": p.get("technique_id"),
                "category": p.get("category"),
                "must_hold": bool(exp.get("must_hold")),
                "outcome": "skip",
                "detail": "dry-run (not executed)",
                "http_status": None,
            }
        )
    path = outdir / "payloads.json"
    path.write_text(
        json.dumps(
            {
                "schema": "aiwall.redteam.payload_results.v1",
                "target": target,
                "results": rows,
            },
            indent=2,
        )
        + "\n"
    )
    print(f"json {path} ({len(rows)} inventory rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
