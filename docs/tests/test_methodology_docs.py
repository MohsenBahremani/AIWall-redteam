#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mohsen Bah
# SPDX-License-Identifier: Apache-2.0
"""Offline check: RoE, methodology, and attack catalog docs."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ROE = ROOT / "docs" / "rules-of-engagement.md"
METHOD = ROOT / "docs" / "testing-methodology.md"
CATALOG_MD = ROOT / "docs" / "attack-catalog.md"
CATALOG_JSON = ROOT / "docs" / "attack-catalog.json"

REQUIRED_CATEGORIES = (
    "prompt-injection",
    "secret-exfiltration",
    "unsafe-content",
    "agent-tool-abuse",
    "cost-abuse",
)

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
    "attack-catalog.md",
)

_ATLAS_RE = re.compile(r"^AML\.T\d{4}(?:\.\d{3})?$")
_OWASP_RE = re.compile(r"^LLM\d{2}$")


def _check_markdown(path: Path, needles: tuple[str, ...]) -> list[str]:
    errors: list[str] = []
    if not path.is_file():
        return [f"missing {path}"]
    text = path.read_text()
    if len(text.strip()) < 800:
        errors.append(f"{path.name}: too short")
    for needle in needles:
        if needle not in text:
            errors.append(f"{path.name}: missing {needle!r}")
    return errors


def _check_catalog() -> list[str]:
    errors: list[str] = []
    if not CATALOG_JSON.is_file():
        return [f"missing {CATALOG_JSON}"]
    if not CATALOG_MD.is_file():
        return [f"missing {CATALOG_MD}"]

    data = json.loads(CATALOG_JSON.read_text())
    if data.get("schema") != "aiwall.redteam.attack_catalog.v1":
        errors.append("attack-catalog.json: bad schema")
        return errors

    categories = data.get("categories") or []
    found = {c.get("id") for c in categories}
    for req in REQUIRED_CATEGORIES:
        if req not in found:
            errors.append(f"attack-catalog.json: missing category {req}")

    md = CATALOG_MD.read_text()
    technique_ids: set[str] = set()
    for cat in categories:
        cid = cat.get("id") or ""
        title = cat.get("title") or ""
        if title and title.lower() not in md.lower() and cid not in md:
            errors.append(f"attack-catalog.md: should mention category {cid}")
        techniques = cat.get("techniques") or []
        if len(techniques) < 1:
            errors.append(f"{cid}: need >= 1 technique")
        for tech in techniques:
            tid = str(tech.get("id") or "")
            if not tid:
                errors.append(f"{cid}: technique missing id")
                continue
            if tid in technique_ids:
                errors.append(f"duplicate technique id {tid}")
            technique_ids.add(tid)
            if tid not in md:
                errors.append(f"attack-catalog.md: missing technique {tid}")
            owasp = tech.get("owasp_llm") or []
            atlas = tech.get("atlas") or []
            if not owasp:
                errors.append(f"{tid}: missing owasp_llm")
            if not atlas:
                errors.append(f"{tid}: missing atlas")
            for o in owasp:
                if not _OWASP_RE.match(str(o)):
                    errors.append(f"{tid}: bad OWASP id {o!r}")
            for a in atlas:
                if not _ATLAS_RE.match(str(a)):
                    errors.append(f"{tid}: bad ATLAS id {a!r}")
            if not (tech.get("name") and tech.get("expected_hold")):
                errors.append(f"{tid}: need name and expected_hold")

    if len(technique_ids) < 10:
        errors.append(f"expected >= 10 techniques, found {len(technique_ids)}")

    return errors


def main() -> int:
    errors: list[str] = []
    for path, needles in ((ROE, ROE_NEEDLES), (METHOD, METHOD_NEEDLES)):
        errs = _check_markdown(path, needles)
        if errs:
            errors.extend(errs)
        else:
            print(f"ok {path.relative_to(ROOT)}")

    readme = ROOT / "README.md"
    if not readme.is_file():
        errors.append("missing README.md")
    else:
        rt = readme.read_text()
        readme_ok = True
        for needle in (
            "docs/rules-of-engagement.md",
            "docs/testing-methodology.md",
            "docs/attack-catalog.md",
            "systems you do not own",
        ):
            if needle not in rt:
                errors.append(f"README.md: missing {needle!r}")
                readme_ok = False
        if readme_ok:
            print("ok README.md links RoE + methodology + catalog")

    catalog_errs = _check_catalog()
    if catalog_errs:
        errors.extend(catalog_errs)
    else:
        print("ok docs/attack-catalog.json + .md (5 categories, OWASP/ATLAS mapped)")

    if errors:
        for err in errors:
            print(f"FAIL {err}", file=sys.stderr)
        print(f"FAILED: {len(errors)} check(s)", file=sys.stderr)
        return 1
    print("PASS: redteam docs (RoE, methodology, attack catalog)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
