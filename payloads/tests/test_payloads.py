#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mohsen Bah
# SPDX-License-Identifier: Apache-2.0
"""Offline checks: payloads cover the catalog and load/expand/run against a stub target."""

from __future__ import annotations

import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from payload_lib import (  # noqa: E402
    CATEGORIES,
    catalog_technique_ids,
    expand_templates,
    load_all,
    load_payload,
)
from run_payloads import cmd_dry_run, cmd_run  # noqa: E402


def test_catalog_coverage() -> None:
    ids = catalog_technique_ids()
    payloads = load_all()
    got = {p["technique_id"] for p in payloads}
    missing = ids - got
    extra = got - ids
    assert not missing, f"payloads missing for catalog techniques: {sorted(missing)}"
    assert not extra, f"payloads without catalog entries: {sorted(extra)}"
    assert len(payloads) >= 10
    for cat in CATEGORIES:
        assert any(p["category"] == cat for p in payloads), cat


def test_expand_secrets_not_in_raw_files() -> None:
    for p in load_all(category="secret-exfiltration"):
        raw = json.dumps(p["request"])
        assert "{{FAKE_" in raw
        expanded = expand_templates(p)
        blob = json.dumps(expanded["request"])
        assert "{{" not in blob
        assert "AKIA" in blob or "ghp_" in blob


def test_dry_run() -> None:
    assert cmd_dry_run(None) == 0


def test_run_against_stub_target() -> None:
    """Configured target stub: 403+secret-detected for SE-*, 200 otherwise."""

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args) -> None:  # noqa: A003
            return

        def do_POST(self) -> None:  # noqa: N802
            length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(length).decode()
            if "AKIA" in body or "ghp_" in body:
                payload = json.dumps(
                    {"error": {"message": "blocked", "reason": "secret-detected", "policy": "block-secrets"}}
                ).encode()
                self.send_response(403)
            else:
                payload = json.dumps({"id": "chatcmpl-stub", "choices": []}).encode()
                self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

    server = HTTPServer(("127.0.0.1", 0), Handler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base = f"http://127.0.0.1:{port}"
        # Secret must-hold probes should pass against stub
        rc = cmd_run(
            category="secret-exfiltration",
            base_url=base,
            api_key=None,
            model_override=None,
            must_hold_only=True,
            timeout=5.0,
            skip_requires=set(),
        )
        assert rc == 0, "secret must-hold suite should pass on stub"
    finally:
        server.shutdown()


def main() -> int:
    errors = 0
    for name, fn in (
        ("catalog_coverage", test_catalog_coverage),
        ("expand_secrets", test_expand_secrets_not_in_raw_files),
        ("dry_run", test_dry_run),
        ("run_stub", test_run_against_stub_target),
    ):
        try:
            fn()
            print(f"ok {name}")
        except Exception as exc:  # noqa: BLE001
            print(f"FAIL {name}: {exc}", file=sys.stderr)
            errors += 1
    # sanity: each file loads
    for p in load_all():
        load_payload(ROOT / p["_path"])
    if errors:
        print(f"FAILED: {errors}", file=sys.stderr)
        return 1
    print(f"PASS: {len(load_all())} payloads load and run against stub target")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
