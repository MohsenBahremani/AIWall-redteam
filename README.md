# AIWall-redteam

Adversarial testing for [AIWall](https://github.com/MohsenBah/AIWall): payloads, campaigns, and mitigation validation.

Validates that gateway controls hold under prompt injection, secret exfiltration, unsafe content, agent tool abuse, and cost abuse.

**Do not run anything from this repo against systems you do not own or have explicit authorization to test.**

## Before you test

1. Read [docs/rules-of-engagement.md](docs/rules-of-engagement.md) — scope, safety, disclosure.
2. Read [docs/testing-methodology.md](docs/testing-methodology.md) — lab target setup and scoring.
3. Stand up a **lab** AIWall (prefer local/mock upstream). Confirm a benign request audits as `allow`.

Offline doc check:

```bash
python3 docs/tests/test_methodology_docs.py
```

## Purpose

| Content | Description |
|---|---|
| **Rules / methodology** | Authorization, safety, lab setup, scoring (this milestone) |
| **Attack catalog** | Scenarios mapped to OWASP LLM Top 10 / MITRE ATLAS (next) |
| **Payload library** | Category-organized probes |
| **Garak / PyRIT** | Automated campaigns against the AIWall endpoint |
| **Reports / regression** | Baseline, retest, CI must-block suite |

## Layout

```text
AIWall-redteam/
├── docs/
│   ├── rules-of-engagement.md
│   ├── testing-methodology.md
│   └── tests/
├── payloads/          (upcoming)
├── garak/             (upcoming)
├── pyrit/             (upcoming)
├── scripts/           (upcoming)
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
