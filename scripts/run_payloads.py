#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mohsen Bah
# SPDX-License-Identifier: Apache-2.0
"""List, dry-run, or execute payload fixtures against a configured AIWall target.

Environment:
  AIWALL_BASE_URL   default http://127.0.0.1:8080
  AIWALL_API_KEY    optional Bearer token (profile or gateway key)
  AIWALL_MODEL      optional model id override for all payloads

Examples::

    python3 scripts/run_payloads.py --list
    python3 scripts/run_payloads.py --dry-run
    AIWALL_BASE_URL=http://127.0.0.1:8080 python3 scripts/run_payloads.py \\
        --category secret-exfiltration --must-hold-only
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from payload_lib import (  # noqa: E402
    CATEGORIES,
    expand_templates,
    load_all,
    template_values,
)


def _headers(api_key: str | None) -> dict[str, str]:
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    return headers


def _post_json(url: str, body: dict[str, Any], headers: dict[str, str], timeout: float) -> tuple[int, dict | list | str]:
    data = json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode()
            status = resp.getcode() or 200
    except urllib.error.HTTPError as exc:
        status = exc.code
        raw = exc.read().decode() if exc.fp else ""
    except urllib.error.URLError as exc:
        raise ConnectionError(str(exc.reason if hasattr(exc, "reason") else exc)) from exc

    try:
        parsed: dict | list | str = json.loads(raw) if raw else {}
    except json.JSONDecodeError:
        parsed = raw
    return status, parsed


def _decision_from_body(body: dict | list | str) -> tuple[str | None, str | None]:
    if not isinstance(body, dict):
        return None, None
    err = body.get("error")
    if isinstance(err, dict):
        reason = err.get("reason")
        # AIWall often returns policy name; decision inferred from HTTP by caller
        return "block", str(reason) if reason else None
    return None, None


def _evaluate(payload: dict[str, Any], status: int, body: dict | list | str) -> tuple[bool, str]:
    expected = payload.get("expected") or {}
    must_hold = bool(expected.get("must_hold"))
    statuses = expected.get("http_status") or []
    decisions = expected.get("decision") or []
    reasons = expected.get("reason_any") or []

    decision, reason = _decision_from_body(body)
    if status == 200 and decision is None:
        decision = "allow"

    if statuses and status not in statuses:
        return (not must_hold), f"http {status} not in {statuses}"

    if reasons and reason and reason not in reasons:
        # Soft: if must_hold and we got 403 without matching reason, still fail
        if must_hold:
            return False, f"reason {reason!r} not in {reasons}"
    if reasons and must_hold and status == 403 and not reason:
        # 403 without parseable reason — accept as hold if http matched
        return True, "http hold (no reason field)"

    if decisions and decision and decision not in decisions:
        if must_hold:
            return False, f"decision {decision!r} not in {decisions}"

    if must_hold:
        if status in (statuses or [403]) or decision in (decisions or ["block", "redact"]):
            if reasons and reason and reason not in reasons:
                return False, f"must_hold reason miss: {reason!r}"
            return True, "hold"
        return False, "must_hold bypass"

    return True, "recorded"


def cmd_list(category: str | None) -> int:
    payloads = load_all(category)
    for p in payloads:
        flags = ",".join(p.get("requires") or []) or "-"
        must = "MUST" if (p.get("expected") or {}).get("must_hold") else "soft"
        print(f"{p['id']:6}  {p['category']:22}  {must:4}  req={flags}  {p.get('name')}")
    print(f"{len(payloads)} payload(s)")
    return 0


def cmd_dry_run(category: str | None) -> int:
    values = template_values()
    payloads = load_all(category)
    for raw in payloads:
        expanded = expand_templates(copy_payload(raw), values)
        body = expanded["request"]["json"]
        blob = json.dumps(body)
        if "AKIA" in blob and "{{" not in json.dumps(raw["request"]["json"]):
            # Expanded secrets should appear only after expand
            pass
        if "{{" in blob:
            print(f"FAIL {raw['id']}: unresolved template in body", file=sys.stderr)
            return 1
        # Ensure raw fixtures never contained a fully expanded live-looking key without template
        print(f"ok dry-run {raw['id']} -> {expanded['request']['path']} ({len(blob)} bytes json)")
    print(f"PASS: {len(payloads)} payloads expand cleanly")
    return 0


def copy_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return json.loads(json.dumps({k: v for k, v in payload.items() if not k.startswith("_")}))


def cmd_run(
    *,
    category: str | None,
    base_url: str,
    api_key: str | None,
    model_override: str | None,
    must_hold_only: bool,
    timeout: float,
    skip_requires: set[str],
    json_out: Path | None = None,
    only_ids: set[str] | None = None,
) -> int:
    base = base_url.rstrip("/")
    payloads = load_all(category)
    values = template_values()
    headers = _headers(api_key)

    ran = 0
    holds = 0
    fails = 0
    skipped = 0
    results: list[dict[str, Any]] = []

    for raw in payloads:
        if only_ids is not None and raw.get("id") not in only_ids:
            continue
        expected = raw.get("expected") or {}
        if must_hold_only and not expected.get("must_hold"):
            skipped += 1
            results.append(
                {
                    "id": raw.get("id"),
                    "technique_id": raw.get("technique_id"),
                    "category": raw.get("category"),
                    "must_hold": bool(expected.get("must_hold")),
                    "outcome": "skip",
                    "detail": "not must_hold",
                    "http_status": None,
                }
            )
            continue
        requires = set(raw.get("requires") or [])
        if requires & skip_requires:
            print(f"skip {raw['id']}: requires {sorted(requires & skip_requires)}")
            skipped += 1
            results.append(
                {
                    "id": raw.get("id"),
                    "technique_id": raw.get("technique_id"),
                    "category": raw.get("category"),
                    "must_hold": bool(expected.get("must_hold")),
                    "outcome": "skip",
                    "detail": f"requires {sorted(requires & skip_requires)}",
                    "http_status": None,
                }
            )
            continue

        expanded = expand_templates(copy_payload(raw), values)
        if model_override:
            expanded["request"]["json"]["model"] = model_override
        path = expanded["request"]["path"]
        url = base + path
        try:
            status, body = _post_json(url, expanded["request"]["json"], headers, timeout)
        except ConnectionError as exc:
            print(f"FAIL {raw['id']}: connection error: {exc}", file=sys.stderr)
            results.append(
                {
                    "id": raw.get("id"),
                    "technique_id": raw.get("technique_id"),
                    "category": raw.get("category"),
                    "must_hold": bool(expected.get("must_hold")),
                    "outcome": "error",
                    "detail": str(exc),
                    "http_status": None,
                }
            )
            if json_out:
                _write_payload_json(json_out, base, results)
            return 1

        ok, detail = _evaluate(expanded, status, body)
        ran += 1
        if ok:
            holds += 1 if expected.get("must_hold") else 0
            outcome = "hold" if expected.get("must_hold") else "recorded"
            print(f"ok  {raw['id']}: http={status} {detail}")
        else:
            fails += 1
            outcome = "bypass" if expected.get("must_hold") else "fail"
            print(f"FAIL {raw['id']}: http={status} {detail}", file=sys.stderr)
            if isinstance(body, dict):
                print(f"     body={json.dumps(body)[:300]}", file=sys.stderr)

        results.append(
            {
                "id": raw.get("id"),
                "technique_id": raw.get("technique_id"),
                "category": raw.get("category"),
                "must_hold": bool(expected.get("must_hold")),
                "outcome": outcome,
                "detail": detail,
                "http_status": status,
            }
        )

    if only_ids is not None:
        missing = only_ids - {r["id"] for r in results}
        if missing:
            print(f"FAIL missing payload ids: {sorted(missing)}", file=sys.stderr)
            fails += len(missing)

    print(f"ran={ran} must_hold_ok~={holds} fail={fails} skipped={skipped}")
    if json_out:
        _write_payload_json(json_out, base, results)
    return 1 if fails else 0


def _write_payload_json(path: Path, base_url: str, results: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": "aiwall.redteam.payload_results.v1",
        "target": base_url,
        "results": results,
    }
    path.write_text(json.dumps(payload, indent=2) + "\n")
    print(f"json {path}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--list", action="store_true", help="List payloads")
    parser.add_argument("--dry-run", action="store_true", help="Expand templates only")
    parser.add_argument("--category", choices=CATEGORIES, help="Limit to one category")
    parser.add_argument("--must-hold-only", action="store_true")
    parser.add_argument(
        "--skip-requires",
        default="",
        help="Comma-separated requires flags to skip (e.g. child_profile,daily_limit)",
    )
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument(
        "--json-out",
        default="",
        help="Write structured results JSON (for campaign reports)",
    )
    parser.add_argument(
        "--ids",
        default="",
        help="Comma-separated payload ids to run (e.g. SE-01,SE-02)",
    )
    args = parser.parse_args(argv)

    if args.list:
        return cmd_list(args.category)
    if args.dry_run:
        return cmd_dry_run(args.category)

    base = os.environ.get("AIWALL_BASE_URL", "http://127.0.0.1:8080")
    key = os.environ.get("AIWALL_API_KEY")
    model_override = os.environ.get("AIWALL_MODEL") or None
    skip = {x.strip() for x in args.skip_requires.split(",") if x.strip()}
    # Default: skip probes that need special lab setup unless operator clears the set
    if not skip and not args.must_hold_only:
        # When running full suite without flags, still attempt all; operator can skip
        pass
    print(f"target {base} (key={'set' if key else 'none'})")
    if model_override:
        print(f"model  {model_override} (AIWALL_MODEL override)")
    print("Reminder: authorized lab targets only — see docs/rules-of-engagement.md")
    json_out = Path(args.json_out) if args.json_out else None
    only_ids = {x.strip() for x in args.ids.split(",") if x.strip()} or None
    return cmd_run(
        category=args.category,
        base_url=base,
        api_key=key,
        model_override=model_override,
        must_hold_only=args.must_hold_only,
        timeout=args.timeout,
        skip_requires=skip,
        json_out=json_out,
        only_ids=only_ids,
    )


if __name__ == "__main__":
    raise SystemExit(main())
