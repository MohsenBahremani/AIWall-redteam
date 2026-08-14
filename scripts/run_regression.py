#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mohsen Bah
# SPDX-License-Identifier: Apache-2.0
"""Run the must-block regression suite against a configured AIWall target.

Fails (exit 1) if any registered case bypasses. Used by CI with a local stub,
or against a lab gateway via AIWALL_BASE_URL.

Examples::

    python3 scripts/run_regression.py --list
    AIWALL_BASE_URL=http://127.0.0.1:8080 python3 scripts/run_regression.py
    python3 scripts/run_regression.py --stub   # self-contained hold stub (CI)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from payload_lib import load_all  # noqa: E402
from run_payloads import cmd_run  # noqa: E402

REGISTRY = ROOT / "regression" / "must_block.json"


def load_registry(path: Path = REGISTRY) -> dict[str, Any]:
    data = json.loads(path.read_text())
    if data.get("schema") != "aiwall.redteam.must_block.v1":
        raise SystemExit(f"{path}: unexpected schema {data.get('schema')!r}")
    cases = data.get("cases") or []
    if not cases:
        raise SystemExit(f"{path}: empty cases")
    return data


def registry_ids(data: dict[str, Any]) -> list[str]:
    return [str(c["id"]) for c in data["cases"]]


def validate_registry_against_payloads(data: dict[str, Any]) -> list[str]:
    """Return error strings if registry does not match must_hold payloads."""
    errors: list[str] = []
    by_id = {p["id"]: p for p in load_all()}
    for case in data["cases"]:
        cid = case["id"]
        if cid not in by_id:
            errors.append(f"registry id {cid} has no payload")
            continue
        p = by_id[cid]
        if not (p.get("expected") or {}).get("must_hold"):
            errors.append(f"{cid}: payload is not must_hold")
        if p.get("technique_id") != case.get("technique_id"):
            errors.append(
                f"{cid}: technique_id mismatch registry={case.get('technique_id')} payload={p.get('technique_id')}"
            )
    return errors


def _start_hold_stub() -> tuple[HTTPServer, str]:
    """Stub that blocks synthetic secrets like AIWall block-secrets."""

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args) -> None:  # noqa: A003
            return

        def do_POST(self) -> None:  # noqa: N802
            length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(length).decode()
            if "AKIA" in body or "ghp_" in body:
                payload = json.dumps(
                    {
                        "error": {
                            "message": "Request blocked by AIWall policy: block-secrets",
                            "type": "policy_blocked",
                            "code": "policy_blocked",
                            "policy": "block-secrets",
                            "reason": "secret-detected",
                        }
                    }
                ).encode()
                self.send_response(403)
            else:
                payload = json.dumps(
                    {
                        "id": "chatcmpl-stub",
                        "choices": [{"message": {"role": "assistant", "content": "ok"}}],
                    }
                ).encode()
                self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    port = server.server_address[1]
    return server, f"http://127.0.0.1:{port}"


def _start_bypass_stub() -> tuple[HTTPServer, str]:
    """Broken stub: always 200 — used to prove the suite fails on bypass."""

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args) -> None:  # noqa: A003
            return

        def do_POST(self) -> None:  # noqa: N802
            length = int(self.headers.get("Content-Length", "0"))
            self.rfile.read(length)
            payload = json.dumps(
                {
                    "id": "chatcmpl-open",
                    "choices": [{"message": {"role": "assistant", "content": "leaked"}}],
                }
            ).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    port = server.server_address[1]
    return server, f"http://127.0.0.1:{port}"


def run_suite(*, base_url: str, api_key: str | None, ids: list[str], json_out: Path | None) -> int:
    print(f"regression must-block ids={','.join(ids)}")
    print(f"target {base_url}")
    print("Reminder: authorized lab targets only — docs/rules-of-engagement.md")
    return cmd_run(
        category=None,
        base_url=base_url,
        api_key=api_key,
        must_hold_only=False,
        timeout=30.0,
        skip_requires=set(),
        json_out=json_out,
        only_ids=set(ids),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--list", action="store_true", help="List registry cases")
    parser.add_argument(
        "--registry",
        default=str(REGISTRY),
        help="Path to must_block.json",
    )
    parser.add_argument(
        "--stub",
        action="store_true",
        help="Run against an in-process hold stub (no external AIWall)",
    )
    parser.add_argument(
        "--expect-fail",
        action="store_true",
        help="Use a bypass stub and require non-zero exit (CI self-check)",
    )
    parser.add_argument(
        "--json-out",
        default="",
        help="Optional results JSON path",
    )
    args = parser.parse_args(argv)

    data = load_registry(Path(args.registry))
    ids = registry_ids(data)

    if args.list:
        for case in data["cases"]:
            print(f"{case['id']:6}  {case.get('category')}  {case.get('reason')}")
        print(f"{len(ids)} must-block case(s)")
        return 0

    errors = validate_registry_against_payloads(data)
    if errors:
        for e in errors:
            print(f"FAIL registry: {e}", file=sys.stderr)
        return 1

    server = None
    try:
        if args.expect_fail:
            server, base = _start_bypass_stub()
            key = None
        elif args.stub:
            server, base = _start_hold_stub()
            key = None
        else:
            base = os.environ.get("AIWALL_BASE_URL", "http://127.0.0.1:8080")
            key = os.environ.get("AIWALL_API_KEY")

        json_out = Path(args.json_out) if args.json_out else None
        rc = run_suite(base_url=base, api_key=key, ids=ids, json_out=json_out)

        if args.expect_fail:
            if rc != 0:
                print("ok  expect-fail: suite correctly failed on bypass stub")
                return 0
            print("FAIL expect-fail: suite returned 0 against open stub", file=sys.stderr)
            return 1
        return rc
    finally:
        if server is not None:
            server.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
