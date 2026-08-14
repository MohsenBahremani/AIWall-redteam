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

## Purpose

| Content | Description |
|---|---|
| **Rules / methodology** | Authorization, safety, lab setup, scoring |
| **Attack catalog** | Techniques mapped to OWASP LLM Top 10 / MITRE ATLAS |
| **Payload library** | Category-organized probes + runner |
| **Garak / PyRIT** | Automated campaigns against the AIWall endpoint (next) |
| **Reports / regression** | Baseline, retest, CI must-block suite |

## Layout

```text
AIWall-redteam/
├── docs/
│   ├── rules-of-engagement.md
│   ├── testing-methodology.md
│   ├── attack-catalog.md
│   ├── attack-catalog.json
│   └── tests/
├── payloads/
│   ├── prompt-injection/
│   ├── secret-exfiltration/
│   ├── unsafe-content/
│   ├── agent-tool-abuse/
│   ├── cost-abuse/
│   └── tests/
├── scripts/
│   ├── payload_lib.py
│   └── run_payloads.py
├── garak/             (upcoming)
├── pyrit/             (upcoming)
└── reports/           (upcoming)
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
