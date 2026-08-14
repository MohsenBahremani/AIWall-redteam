#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mohsen Bah
# SPDX-License-Identifier: Apache-2.0
"""Offline check: Phase 7.1 RoE + methodology docs define scope, safety, setup."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ROE = ROOT / "docs" / "rules-of-engagement.md"
METHOD = ROOT / "docs" / "testing-methodology.md"

ROE_NEEDLES = (
    "## Authorization",
    "## Scope (in)",
    "## Scope (out)",
    "## Safety controls",
    "## Disclosure",
)

METHOD_NEEDLES = (
    "## Target setup",
    "## Scoring",
    "## Attack categories",
    "aiwall.audit.v1",
    "events/export.jsonl",
)


def main() -> int:
    errors = 0
    for path, needles in ((ROE, ROE_NEEDLES), (METHOD, METHOD_NEEDLES)):
        if not path.is_file():
            print(f"missing {path}", file=sys.stderr)
            errors += 1
            continue
        text = path.read_text()
        if len(text.strip()) < 800:
            print(f"FAIL {path.name}: too short", file=sys.stderr)
            errors += 1
        for needle in needles:
            if needle not in text:
                print(f"FAIL {path.name}: missing {needle!r}", file=sys.stderr)
                errors += 1
        print(f"ok {path.relative_to(ROOT)}")

    readme = ROOT / "README.md"
    if not readme.is_file():
        print("missing README.md", file=sys.stderr)
        errors += 1
    else:
        rt = readme.read_text()
        readme_ok = True
        for needle in (
            "docs/rules-of-engagement.md",
            "docs/testing-methodology.md",
            "systems you do not own",
        ):
            if needle not in rt:
                print(f"FAIL README.md: missing {needle!r}", file=sys.stderr)
                errors += 1
                readme_ok = False
        if readme_ok:
            print("ok README.md links RoE + methodology")

    if errors:
        print(f"FAILED: {errors} check(s)", file=sys.stderr)
        return 1
    print("PASS: rules of engagement + testing methodology docs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
