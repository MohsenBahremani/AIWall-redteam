#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Mohsen Bah
# SPDX-License-Identifier: Apache-2.0
# Run an AIWall-redteam campaign and emit a report under reports/.
#
# Usage:
#   ./scripts/run_campaign.sh                  # smoke: must-hold payloads + pyrit
#   ./scripts/run_campaign.sh --full           # all payloads (still skips heavy requires)
#   ./scripts/run_campaign.sh --dry-run        # no network; inventory + report
#   ./scripts/run_campaign.sh --skip-pyrit
#   ./scripts/run_campaign.sh --with-garak     # also run Garak smoke config
#
# Env: AIWALL_BASE_URL, AIWALL_API_KEY, AIWALL_MODEL (see docs/testing-methodology.md)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PROFILE="smoke"
DRY_RUN=0
SKIP_PYRIT=0
WITH_GARAK=0
SKIP_REQUIRES="child_profile,daily_limit,cost_policy,agent_guardrails"
CATEGORY=""
PYTHON="${PYTHON:-python3}"

usage() {
  sed -n '2,14p' "$0" | sed 's/^# \{0,1\}//'
  exit "${1:-0}"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --smoke) PROFILE="smoke"; shift ;;
    --full) PROFILE="full"; shift ;;
    --dry-run) DRY_RUN=1; shift ;;
    --skip-pyrit) SKIP_PYRIT=1; shift ;;
    --skip-garak) WITH_GARAK=0; shift ;;
    --with-garak) WITH_GARAK=1; shift ;;
    --skip-requires)
      SKIP_REQUIRES="${2:-}"
      shift 2
      ;;
    --category)
      CATEGORY="${2:-}"
      shift 2
      ;;
    -h|--help) usage 0 ;;
    *) echo "unknown arg: $1" >&2; usage 1 ;;
  esac
done

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
CAMPAIGN_ID="campaign-${PROFILE}-${STAMP}"
OUTDIR="${ROOT}/reports/${CAMPAIGN_ID}"
mkdir -p "$OUTDIR"

TARGET="${AIWALL_BASE_URL:-http://127.0.0.1:8080}"

cat >"$OUTDIR/meta.json" <<EOF
{
  "schema": "aiwall.redteam.campaign_meta.v1",
  "campaign_id": "${CAMPAIGN_ID}",
  "profile": "${PROFILE}",
  "target": "${TARGET}",
  "dry_run": $([[ "$DRY_RUN" -eq 1 ]] && echo true || echo false),
  "notes": "Authorized lab only. See docs/rules-of-engagement.md"
}
EOF

echo "Reminder: authorized lab targets only — docs/rules-of-engagement.md"
echo "campaign ${CAMPAIGN_ID}"
echo "outdir   ${OUTDIR}"
echo "target   ${TARGET}"
echo "profile  ${PROFILE} dry_run=${DRY_RUN}"

PAYLOAD_RC=0
PYRIT_RC=0
GARAK_RC=0

if [[ "$DRY_RUN" -eq 1 ]]; then
  echo "== dry-run: expand payloads =="
  if [[ -n "$CATEGORY" ]]; then
    "$PYTHON" scripts/run_payloads.py --dry-run --category "$CATEGORY" \
      | tee "$OUTDIR/payloads-dry-run.txt"
  else
    "$PYTHON" scripts/run_payloads.py --dry-run \
      | tee "$OUTDIR/payloads-dry-run.txt"
  fi
  CATEGORY="$CATEGORY" OUTDIR="$OUTDIR" TARGET="$TARGET" "$PYTHON" scripts/campaign_inventory.py
  SKIP_PYRIT=1
  WITH_GARAK=0
else
  echo "== payloads =="
  PAYLOAD_ARGS=(--skip-requires "$SKIP_REQUIRES" --json-out "$OUTDIR/payloads.json")
  if [[ "$PROFILE" == "smoke" ]]; then
    PAYLOAD_ARGS+=(--must-hold-only)
  fi
  if [[ -n "$CATEGORY" ]]; then
    PAYLOAD_ARGS+=(--category "$CATEGORY")
  fi
  set +e
  "$PYTHON" scripts/run_payloads.py "${PAYLOAD_ARGS[@]}"
  PAYLOAD_RC=$?
  set -e

  if [[ "$SKIP_PYRIT" -eq 0 ]]; then
    echo "== pyrit =="
    set +e
    "$PYTHON" scripts/run_pyrit.py --report "$OUTDIR/pyrit.json"
    PYRIT_RC=$?
    set -e
  else
    echo "== pyrit skipped =="
  fi

  if [[ "$WITH_GARAK" -eq 1 ]]; then
    echo "== garak =="
    mkdir -p "$OUTDIR/garak"
    set +e
    "$PYTHON" scripts/run_garak.py --config garak/configs/aiwall-smoke.yaml
    GARAK_RC=$?
    if [[ -d garak/reports ]]; then
      find garak/reports -maxdepth 1 -type f -name 'aiwall-smoke*' \
        -exec cp -t "$OUTDIR/garak" {} + 2>/dev/null || true
    fi
    set -e
  else
    echo "== garak skipped (pass --with-garak to enable) =="
  fi
fi

echo "== report =="
set +e
"$PYTHON" scripts/generate_report.py --indir "$OUTDIR"
REPORT_RC=$?
set -e

echo ""
echo "Campaign finished: ${OUTDIR}/campaign-report.md"
echo "exit codes: payloads=${PAYLOAD_RC} pyrit=${PYRIT_RC} garak=${GARAK_RC} report=${REPORT_RC}"

if [[ "$DRY_RUN" -eq 1 ]]; then
  exit 0
fi
if [[ "$PAYLOAD_RC" -ne 0 || "$REPORT_RC" -ne 0 ]]; then
  exit 1
fi
exit 0
