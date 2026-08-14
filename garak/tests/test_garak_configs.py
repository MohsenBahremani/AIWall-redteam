#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mohsen Bah
# SPDX-License-Identifier: Apache-2.0
"""Offline check: Garak configs target AIWall OpenAI-compatible endpoint."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = ROOT / "garak" / "configs"
REQUIRED = (
    "aiwall-smoke.yaml",
    "aiwall-lab.yaml",
)

try:
    import yaml
except ImportError:
    yaml = None


def _check_config(path: Path) -> list[str]:
    errors: list[str] = []
    if yaml is None:
        # Minimal parse without PyYAML: require key substrings
        text = path.read_text()
        for needle in (
            "openai.OpenAICompatible",
            "OpenAICompatible",
            "/v1/",
            "report_dir",
            "report_prefix",
        ):
            if needle not in text:
                errors.append(f"{path.name}: missing {needle!r}")
        if "uri:" not in text:
            errors.append(f"{path.name}: missing uri")
        return errors

    data = yaml.safe_load(path.read_text())
    if not isinstance(data, dict):
        return [f"{path.name}: not a mapping"]

    plugins = data.get("plugins") or {}
    if plugins.get("target_type") != "openai.OpenAICompatible":
        errors.append(f"{path.name}: target_type must be openai.OpenAICompatible")
    try:
        uri = plugins["generators"]["openai"]["OpenAICompatible"]["uri"]
    except (KeyError, TypeError):
        errors.append(f"{path.name}: missing generators.openai.OpenAICompatible.uri")
        uri = ""
    if uri and not str(uri).rstrip("/").endswith("/v1"):
        if "/v1" not in str(uri):
            errors.append(f"{path.name}: uri should point at …/v1/ (got {uri!r})")

    reporting = data.get("reporting") or {}
    if not reporting.get("report_dir") or not reporting.get("report_prefix"):
        errors.append(f"{path.name}: reporting.report_dir and report_prefix required")

    run = data.get("run") or {}
    spec = run.get("spec") or {}
    include = spec.get("include") or []
    if not include and "probe" not in path.read_text().lower():
        errors.append(f"{path.name}: run.spec.include should list probes")
    if not include:
        # also accept deprecated probe_spec in file text
        if "probes." not in path.read_text() and "probe_spec" not in path.read_text():
            errors.append(f"{path.name}: no probes selected")

    return errors


def main() -> int:
    errors: list[str] = []
    if not CONFIG_DIR.is_dir():
        print(f"missing {CONFIG_DIR}", file=sys.stderr)
        return 1

    for name in REQUIRED:
        path = CONFIG_DIR / name
        if not path.is_file():
            errors.append(f"missing {path.relative_to(ROOT)}")
            continue
        errs = _check_config(path)
        if errs:
            errors.extend(errs)
        else:
            print(f"ok {path.relative_to(ROOT)}")

    readme = ROOT / "garak" / "README.md"
    if not readme.is_file():
        errors.append("missing garak/README.md")
    else:
        text = readme.read_text()
        readme_ok = True
        for needle in ("aiwall-smoke.yaml", "OPENAICOMPATIBLE_API_KEY", "run_garak.py"):
            if needle not in text:
                errors.append(f"garak/README.md missing {needle!r}")
                readme_ok = False
        if readme_ok:
            print("ok garak/README.md")

    # Runner dry-run if PyYAML present
    if yaml is not None:
        sys.path.insert(0, str(ROOT / "scripts"))
        from run_garak import main as run_main

        rc = run_main(["--config", str(CONFIG_DIR / "aiwall-smoke.yaml"), "--dry-run"])
        if rc != 0:
            errors.append("run_garak.py --dry-run failed")
        else:
            print("ok scripts/run_garak.py --dry-run")

    if errors:
        for err in errors:
            print(f"FAIL {err}", file=sys.stderr)
        return 1
    print("PASS: Garak configs target AIWall OpenAI-compatible endpoint")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
