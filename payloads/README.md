# Payload library

Category-organized probes for AIWall (Phase 7.3). Each file is one catalog technique.

| Directory | Catalog category |
|---|---|
| `prompt-injection/` | PI-* |
| `secret-exfiltration/` | SE-* |
| `unsafe-content/` | UC-* |
| `agent-tool-abuse/` | AT-* |
| `cost-abuse/` | CA-* |

## Schema

Each `*.json` payload:

| Field | Meaning |
|---|---|
| `id` / `technique_id` | Catalog id (e.g. `SE-01`) |
| `category` | Directory name |
| `request` | HTTP method, path, JSON body for `/v1/chat/completions` |
| `expected` | Soft or hard expectations (`decision`, `reason_any`, `http_status`, `must_hold`) |
| `requires` | Lab flags: `secret_policy`, `child_profile`, `agent_guardrails`, `cost_policy`, `daily_limit` |
| `templates` | Placeholders expanded at run time (never commit live secrets) |

Template tokens (expanded by the runner):

- `{{FAKE_AWS_KEY}}` — synthetic `AKIA…` access key id
- `{{FAKE_GITHUB_TOKEN}}` — synthetic `ghp_…` token
- `{{LARGE_PAD}}` — long padding for cost probes

## Load / run

```bash
# List / validate fixtures (no network)
python3 scripts/run_payloads.py --list
python3 scripts/run_payloads.py --dry-run

# Against a lab AIWall (read RoE first)
export AIWALL_BASE_URL=http://127.0.0.1:8080
export AIWALL_API_KEY=…          # optional if gateway_auth off
python3 scripts/run_payloads.py --category secret-exfiltration
```

`--must-hold-only` runs probes with `expected.must_hold: true` and exits non-zero on bypass.

Offline tests: `python3 payloads/tests/test_payloads.py`
