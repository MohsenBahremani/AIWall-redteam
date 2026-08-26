#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mohsen Bah
# SPDX-License-Identifier: Apache-2.0
"""Run Garak against AIWall using a checked-in YAML config.

Overrides generator uri from AIWALL_BASE_URL (default http://127.0.0.1:8080).
Optional AIWALL_MODEL overrides plugins.target_name (e.g. llama3.2:1b for Ollama-only labs).
Requires: pip install 'garak>=0.10' and an authorized lab target.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

try:
    import yaml
except ImportError:  # pragma: no cover - stdlib fallback message
    yaml = None  # type: ignore


def _load_yaml(path: Path) -> dict:
    if yaml is None:
        raise SystemExit("PyYAML required: pip install pyyaml  (or install garak)")
    data = yaml.safe_load(path.read_text())
    if not isinstance(data, dict):
        raise SystemExit(f"{path}: expected mapping")
    return data


def _set_uri(cfg: dict, base_url: str) -> str:
    uri = base_url.rstrip("/") + "/v1/"
    plugins = cfg.setdefault("plugins", {})
    generators = plugins.setdefault("generators", {})
    openai = generators.setdefault("openai", {})
    compat = openai.setdefault("OpenAICompatible", {})
    compat["uri"] = uri
    plugins.setdefault("target_type", "openai.OpenAICompatible")
    return uri


def _set_model(cfg: dict, model: str) -> None:
    cfg.setdefault("plugins", {})["target_name"] = model


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        default=str(ROOT / "garak" / "configs" / "aiwall-smoke.yaml"),
        help="Path to garak YAML config",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Write resolved config to stdout / temp and exit (no garak)",
    )
    args = parser.parse_args(argv)

    config_path = Path(args.config)
    if not config_path.is_file():
        print(f"missing config: {config_path}", file=sys.stderr)
        return 1

    base = os.environ.get("AIWALL_BASE_URL", "http://127.0.0.1:8080")
    cfg = _load_yaml(config_path)
    uri = _set_uri(cfg, base)
    model = os.environ.get("AIWALL_MODEL", "").strip()
    if model:
        _set_model(cfg, model)

    reporting = cfg.setdefault("reporting", {})
    report_dir = Path(reporting.get("report_dir") or "garak/reports")
    if not report_dir.is_absolute():
        report_dir = ROOT / report_dir
    report_dir.mkdir(parents=True, exist_ok=True)
    reporting["report_dir"] = str(report_dir)

    print("Reminder: authorized lab targets only — docs/rules-of-engagement.md")
    print(f"config  {config_path}")
    print(f"uri     {uri}")
    if model:
        print(f"model   {model} (AIWALL_MODEL override)")
    print(f"reports {report_dir}")

    if not os.environ.get("OPENAICOMPATIBLE_API_KEY"):
        # Garak requires the env var even when AIWall auth is off.
        os.environ["OPENAICOMPATIBLE_API_KEY"] = os.environ.get(
            "AIWALL_API_KEY", "aiwall-lab"
        )
        print("OPENAICOMPATIBLE_API_KEY defaulted for OpenAICompatible generator")

    with tempfile.NamedTemporaryFile(
        "w",
        suffix=".yaml",
        prefix="aiwall-garak-",
        delete=False,
    ) as tmp:
        if yaml is None:
            raise SystemExit("PyYAML required")
        yaml.safe_dump(cfg, tmp, sort_keys=False)
        tmp_path = Path(tmp.name)

    if args.dry_run:
        print(tmp_path.read_text())
        tmp_path.unlink(missing_ok=True)
        print("PASS: dry-run resolved config")
        return 0

    garak = shutil.which("garak")
    cmd = [sys.executable, "-m", "garak", "--config", str(tmp_path)]
    if garak:
        # Prefer module form for venv consistency
        pass
    print("exec:", " ".join(cmd))
    try:
        proc = subprocess.run(cmd, cwd=str(ROOT), check=False)
    finally:
        tmp_path.unlink(missing_ok=True)

    if proc.returncode != 0:
        print(
            f"garak exited {proc.returncode} "
            "(403s from AIWall may surface as generator errors — check audit export)",
            file=sys.stderr,
        )
    # Still consider report presence a success signal for operators
    reports = list(report_dir.glob("*.report.jsonl")) + list(
        report_dir.glob("*.hitlog.jsonl")
    )
    if reports:
        print("report files:")
        for path in sorted(reports)[-5:]:
            print(f"  {path}")
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
