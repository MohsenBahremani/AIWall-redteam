# AIWall-redteam

Adversarial testing for [AIWall](https://github.com/MohsenBah/AIWall): payloads, campaigns, and mitigation validation.

Validates that gateway controls hold under prompt injection, secret exfiltration, unsafe content, agent tool abuse, and cost abuse.

**Do not run anything from this repo against systems you do not own or have explicit authorization to test.**

## Before you test

1. Read [docs/rules-of-engagement.md](docs/rules-of-engagement.md) — scope, safety, disclosure.
2. Read [docs/testing-methodology.md](docs/testing-methodology.md) — lab target setup and scoring.
3. Skim [docs/attack-catalog.md](docs/attack-catalog.md) — techniques + OWASP/ATLAS maps.
4. Stand up a **lab** AIWall (prefer local/mock upstream). Confirm a benign request audits as `allow`.

## Payload library (7.3)

Fixtures live under [`payloads/`](payloads/) (one JSON file per catalog technique). Synthetic secrets are expanded at run time.

```bash
# Offline
python3 docs/tests/test_methodology_docs.py
python3 payloads/tests/test_payloads.py
python3 scripts/run_payloads.py --list
python3 scripts/run_payloads.py --dry-run

# Lab target (authorized only)
export AIWALL_BASE_URL=http://127.0.0.1:8080
export AIWALL_API_KEY=…   # if gateway_auth / profile keys enabled
python3 scripts/run_payloads.py --category secret-exfiltration --must-hold-only
# Skip probes that need child keys / cost policies / etc.:
python3 scripts/run_payloads.py --skip-requires child_profile,daily_limit,cost_policy,agent_guardrails
```

Details: [payloads/README.md](payloads/README.md).

## Garak (7.4)

OpenAI-compatible scans through AIWall:

```bash
pip install -r requirements.txt
export AIWALL_BASE_URL=http://127.0.0.1:8080
export OPENAICOMPATIBLE_API_KEY="${AIWALL_API_KEY:-aiwall-lab}"
python3 scripts/run_garak.py --config garak/configs/aiwall-smoke.yaml
# reports → garak/reports/
python3 garak/tests/test_garak_configs.py
```

Details: [garak/README.md](garak/README.md).

## PyRIT (7.5)

Prompt-send campaigns with AIWall-aware target + scorers (`aiwall_pyrit/` avoids shadowing installed `pyrit`):

```bash
pip install -r requirements.txt   # or: pip install 'pyrit>=0.10'
export AIWALL_BASE_URL=http://127.0.0.1:8080
export AIWALL_API_KEY=…           # if auth enabled
python3 scripts/run_pyrit.py
# reports → aiwall_pyrit/reports/
python3 aiwall_pyrit/tests/test_pyrit_campaign.py
```

Details: [aiwall_pyrit/README.md](aiwall_pyrit/README.md).

## Campaign runner (7.6)

One command runs probes and writes a report under `reports/`:

```bash
# Offline (inventory only)
./scripts/run_campaign.sh --dry-run

# Lab smoke: must-hold payloads + PyRIT
export AIWALL_BASE_URL=http://127.0.0.1:8080
export AIWALL_API_KEY=…
./scripts/run_campaign.sh --skip-pyrit          # payloads only
./scripts/run_campaign.sh                       # payloads + pyrit
./scripts/run_campaign.sh --full --with-garak   # broader + Garak

# Aggregate existing artifacts
python3 scripts/generate_report.py --indir reports/campaign-smoke-…
python3 reports/tests/test_campaign_report.py
```

Each run creates `reports/campaign-<profile>-<stamp>/` with `campaign-report.md` + `.json`.

## Baseline assessment (7.7)

Lab results against Docker AIWall (`block-secrets`): [reports/baseline-assessment.md](reports/baseline-assessment.md).

- **Held:** SE-01 … SE-03 (secret paste → HTTP 403 / `secret-detected`)
- **Skipped / inconclusive:** child profile, agent guardrails, hard cost limits, prompt-injection scoring (no upstream key)

## Must-block regression (7.8)

CI fails if a previously-blocked attack starts succeeding. Registry: [`regression/must_block.json`](regression/must_block.json).

```bash
python3 scripts/run_regression.py --stub          # pass on hold stub
python3 scripts/run_regression.py --expect-fail   # prove suite fails on bypass
python3 regression/tests/test_regression.py
# Lab: AIWALL_BASE_URL=http://127.0.0.1:8080 python3 scripts/run_regression.py
```

GitHub Actions: [`.github/workflows/ci.yml`](.github/workflows/ci.yml).

## Post-mitigation retest (7.9)

Before/after deltas vs baseline: [reports/post-mitigation-retest.md](reports/post-mitigation-retest.md).

```bash
python3 scripts/compare_campaigns.py \
  --before reports/baseline-campaign-report.json \
  --after reports/retest-campaign-report.json \
  -o /tmp/delta
python3 reports/tests/test_compare_campaigns.py
```

Current control retest: **14/14 unchanged**, SE holds stable, **0 regressions**.

## Purpose

| Content | Description |
|---|---|
| **Rules / methodology** | Authorization, safety, lab setup, scoring |
| **Attack catalog** | Techniques mapped to OWASP LLM Top 10 / MITRE ATLAS |
| **Payload library** | Category-organized probes + runner |
| **Garak** | Configs + runner for AIWall OpenAI-compatible endpoint |
| **PyRIT** | Orchestrators + scorers (`aiwall_pyrit/`) |
| **Campaign / reports** | `run_campaign.sh` + `generate_report.py` |
| **Regression** | Must-block suite (`regression/`) + CI |
| **Baseline / retest** | Assessment + per-attack deltas |

## Layout

```text
AIWall-redteam/
├── docs/
├── payloads/
├── scripts/
│   ├── payload_lib.py
│   ├── run_payloads.py
│   ├── run_garak.py
│   ├── run_pyrit.py
│   ├── run_campaign.sh
│   ├── generate_report.py
│   ├── compare_campaigns.py
│   ├── run_regression.py
│   └── campaign_inventory.py
├── garak/
├── aiwall_pyrit/
├── regression/
│   ├── must_block.json
│   ├── tests/
│   └── README.md
└── reports/
    ├── baseline-assessment.md
    ├── post-mitigation-retest.md
    ├── baseline-*.json / retest-*.json
    ├── campaign-*/          (generated)
    └── tests/
```

## Relationship to AIWall

```text
AIWall (policies, scanners, guardrails)
        │
        v
AIWall-redteam ── probes ──► audit export (aiwall.audit.v1)
        │
        +── holds → regression candidates
        +── bypasses → product requirements / fixes
```

Optional: ship the same export into [AIWall-detections](https://github.com/MohsenBah/AIWall-detections) to confirm SIEM/Loki detections.

## Contributing

DCO sign-off. Include scenario, expected control behavior, and OWASP/ATLAS mapping when adding attacks. Fake secrets only.

## License

[Apache License 2.0](LICENSE)

Payloads and attack samples are for **authorized security testing and research only**. The authors are not responsible for misuse.
