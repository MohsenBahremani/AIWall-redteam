#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mohsen Bah
# SPDX-License-Identifier: Apache-2.0
"""Offline + stub-target checks for AIWall PyRIT campaigns."""

from __future__ import annotations

import asyncio
import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from aiwall_pyrit.orchestrators.prompt_send import expand_prompt, run_prompt_send_cases  # noqa: E402
from aiwall_pyrit.targets.aiwall_chat_target import (  # noqa: E402
    BLOCK_PREFIX,
    format_block_message,
    parse_block_from_exception,
)


OBJ = ROOT / "aiwall_pyrit" / "objectives" / "smoke.json"


def test_objectives_schema() -> None:
    data = json.loads(OBJ.read_text())
    assert data["schema"] == "aiwall.redteam.pyrit_objectives.v1"
    campaigns = data["campaigns"]
    assert len(campaigns) >= 2
    modes = {c["mode"] for c in campaigns}
    assert "hold" in modes
    assert any(c["id"] == "smoke-hold-secret" for c in campaigns)


def test_expand_prompt() -> None:
    out = expand_prompt("key={{FAKE_AWS_KEY}}")
    assert "{{" not in out
    assert out.startswith("key=AKIA")
    assert len(out) > len("key=AKIA")


def test_block_parsing() -> None:
    msg = format_block_message("secret-detected", {"error": {"policy": "block-secrets"}})
    assert BLOCK_PREFIX in msg
    assert "secret-detected" in msg
    assert "policy=block-secrets" in msg

    class Exc(Exception):
        pass

    text = (
        "Error code: 403 - {'error': {'message': 'blocked', 'type': 'aiwall_policy', "
        "'code': 'blocked', 'reason': 'secret-detected'}}"
    )
    parsed = parse_block_from_exception(Exc(text))
    assert parsed is not None
    assert BLOCK_PREFIX in parsed
    assert parse_block_from_exception(Exc("connection reset")) is None


def test_campaign_against_stub() -> None:
    """Stub OpenAI: 403+secret for AKIA, PWNED content for injection prompts."""

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args) -> None:  # noqa: A003
            return

        def do_POST(self) -> None:  # noqa: N802
            length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(length).decode()
            if "AKIA" in body:
                payload = json.dumps(
                    {
                        "error": {
                            "message": "blocked",
                            "type": "aiwall_policy",
                            "code": "blocked",
                            "reason": "secret-detected",
                            "policy": "block-secrets",
                        }
                    }
                ).encode()
                self.send_response(403)
            elif "PWNED" in body.upper() or "Ignore all previous" in body:
                content = "PWNED"
                payload = json.dumps(
                    {
                        "id": "chatcmpl-stub",
                        "object": "chat.completion",
                        "created": 1,
                        "model": "gpt-4o-mini",
                        "choices": [
                            {
                                "index": 0,
                                "message": {"role": "assistant", "content": content},
                                "finish_reason": "stop",
                            }
                        ],
                        "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
                    }
                ).encode()
                self.send_response(200)
            else:
                payload = json.dumps(
                    {
                        "id": "chatcmpl-stub",
                        "object": "chat.completion",
                        "created": 1,
                        "model": "gpt-4o-mini",
                        "choices": [
                            {
                                "index": 0,
                                "message": {"role": "assistant", "content": "Hello"},
                                "finish_reason": "stop",
                            }
                        ],
                        "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
                    }
                ).encode()
                self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

    server = HTTPServer(("127.0.0.1", 0), Handler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    async def _run() -> list:
        from pyrit.setup import IN_MEMORY, initialize_pyrit_async
        from aiwall_pyrit.targets.aiwall_chat_target import AIWallChatTarget

        await initialize_pyrit_async(memory_db_type=IN_MEMORY, silent=True)
        target = AIWallChatTarget(
            endpoint=f"http://127.0.0.1:{port}/v1",
            api_key="stub",
            model_name="gpt-4o-mini",
        )
        cases = json.loads(OBJ.read_text())["campaigns"]
        return await run_prompt_send_cases(target=target, cases=cases)

    try:
        results = asyncio.run(_run())
    finally:
        server.shutdown()

    by_id = {r.case_id: r for r in results}
    assert by_id["smoke-hold-secret"].outcome == "hold", by_id["smoke-hold-secret"]
    assert by_id["smoke-injection"].outcome == "bypass", by_id["smoke-injection"]


def main() -> int:
    tests = [
        test_objectives_schema,
        test_expand_prompt,
        test_block_parsing,
        test_campaign_against_stub,
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
