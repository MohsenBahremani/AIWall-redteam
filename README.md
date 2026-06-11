# AIWall-redteam

Adversarial testing payloads, attack campaigns, and mitigation validation for AIWall and AI gateway deployments.

This repository validates that AIWall controls actually work under attack — prompt injection, secret exfiltration, unsafe content, agent tool abuse, and cost abuse scenarios.

## Status

**Placeholder repository.** Content will be added after [AIWall](https://github.com/MohsenBah/AIWall) has working policy and scanning controls (Phase 7 of the product roadmap).

Do not run anything from this repo against systems you do not own or have explicit authorization to test.

## Purpose

| Content | Description |
|---|---|
| **Attack catalog** | Documented adversarial scenarios mapped to MITRE ATLAS |
| **Payload library** | Prompt injection, secret exfiltration, and agent abuse samples |
| **Garak configs** | Automated LLM vulnerability scanning campaigns |
| **PyRIT scenarios** | Multi-turn adversarial orchestration tests |
| **Evaluation scripts** | Run campaigns and generate mitigation reports |
| **Regression tests** | Ensure blocked attacks stay blocked across releases |

## Planned Structure

```text
AIWall-redteam/
├── docs/
│   ├── testing-methodology.md
│   ├── rules-of-engagement.md
│   ├── attack-catalog.md
│   └── mitigation-validation.md
├── payloads/
│   ├── prompt-injection/
│   ├── secret-exfiltration/
│   ├── unsafe-content/
│   ├── agent-tool-abuse/
│   └── cost-abuse/
├── garak/
│   ├── configs/
│   └── reports/
├── pyrit/
│   ├── orchestrators/
│   └── scorers/
├── scripts/
│   ├── run_campaign.sh
│   └── generate_report.py
└── reports/
    ├── baseline-assessment.md
    └── post-mitigation-retest.md
```

## Relationship to AIWall

```text
AIWall (core product)
    |
    +-- policy engine, secret scanner, guardrails
    |
    v
AIWall-redteam (this repo)
    |
    +-- attack payloads and campaigns
    +-- mitigation validation reports
    +-- regression tests for controls
```

Successful attacks become product requirements. Blocked attacks become regression tests.

## Rules of Engagement

1. **Only test systems you own or have written authorization to test.**
2. Do not use payloads against production AI services without explicit approval.
3. Treat all payloads as sensitive — they are designed to bypass controls.
4. Report newly discovered bypasses through AIWall issues, not public disclosure before a fix exists.
5. Read `docs/rules-of-engagement.md` (when published) before running any campaign.

## Contributing

Contributions welcome once the testing methodology and first attack catalog are published. All submissions must include a clear description of the scenario, expected control behavior, and MITRE ATLAS mapping where applicable. Use DCO sign-off on commits.

## License

[Apache License 2.0](LICENSE)

Payloads and attack samples in this repository are provided for **authorized security testing and research only**. The authors are not responsible for misuse.

## Topics

`ai-security` · `llm-security` · `ai-redteam` · `prompt-injection` · `adversarial-ml` · `garak` · `pyrit` · `mitre-atlas` · `security-testing`
