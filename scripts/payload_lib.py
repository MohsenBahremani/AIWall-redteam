#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mohsen Bah
# SPDX-License-Identifier: Apache-2.0
"""Load and expand AIWall-redteam payload fixtures."""

from __future__ import annotations

import copy
import json
import secrets
import string
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PAYLOADS_ROOT = ROOT / "payloads"
CATALOG_JSON = ROOT / "docs" / "attack-catalog.json"

CATEGORIES = (
    "prompt-injection",
    "secret-exfiltration",
    "unsafe-content",
    "agent-tool-abuse",
    "cost-abuse",
)


def _fake_aws_key() -> str:
    alphabet = string.digits + string.ascii_uppercase
    suffix = "".join(secrets.choice(alphabet) for _ in range(16))
    return "AKIA" + suffix


def _fake_github_token() -> str:
    return "ghp_" + secrets.token_hex(20)


def _large_pad(chars: int = 12000) -> str:
    # Deterministic-ish padding without huge entropy cost.
    chunk = "lorem-ipsum-cost-pad-"
    return (chunk * ((chars // len(chunk)) + 1))[:chars]


def template_values() -> dict[str, str]:
    return {
        "FAKE_AWS_KEY": _fake_aws_key(),
        "FAKE_GITHUB_TOKEN": _fake_github_token(),
        "LARGE_PAD": _large_pad(),
    }


def expand_templates(obj: Any, values: dict[str, str] | None = None) -> Any:
    values = values or template_values()

    def _sub(text: str) -> str:
        out = text
        for key, val in values.items():
            out = out.replace("{{" + key + "}}", val)
        return out

    if isinstance(obj, str):
        return _sub(obj)
    if isinstance(obj, list):
        return [expand_templates(x, values) for x in obj]
    if isinstance(obj, dict):
        return {k: expand_templates(v, values) for k, v in obj.items()}
    return obj


def load_payload(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text())
    if not isinstance(data, dict):
        raise ValueError(f"{path}: payload must be a JSON object")
    for key in ("id", "technique_id", "category", "request", "expected"):
        if key not in data:
            raise ValueError(f"{path}: missing {key}")
    req = data["request"]
    if req.get("method") != "POST" or not req.get("path") or "json" not in req:
        raise ValueError(f"{path}: request must include method=POST, path, json")
    return data


def iter_payload_files(
    category: str | None = None,
    payloads_root: Path = PAYLOADS_ROOT,
) -> list[Path]:
    cats = (category,) if category else CATEGORIES
    files: list[Path] = []
    for cat in cats:
        directory = payloads_root / cat
        if not directory.is_dir():
            continue
        files.extend(sorted(directory.glob("*.json")))
    return files


def load_all(
    category: str | None = None,
    payloads_root: Path = PAYLOADS_ROOT,
    *,
    expand: bool = False,
) -> list[dict[str, Any]]:
    payloads: list[dict[str, Any]] = []
    for path in iter_payload_files(category, payloads_root):
        payload = load_payload(path)
        payload["_path"] = str(path.relative_to(payloads_root.parent))
        if expand:
            payload = expand_templates(payload)
        payloads.append(payload)
    return payloads


def catalog_technique_ids(catalog_path: Path = CATALOG_JSON) -> set[str]:
    data = json.loads(catalog_path.read_text())
    ids: set[str] = set()
    for cat in data.get("categories") or []:
        for tech in cat.get("techniques") or []:
            tid = tech.get("id")
            if tid:
                ids.add(str(tid))
    return ids
