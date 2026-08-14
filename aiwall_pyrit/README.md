# PyRIT against AIWall

[PyRIT](https://github.com/Azure/PyRIT) orchestrators and scorers aimed at the AIWall OpenAI-compatible gateway.

Local helpers live under [`aiwall_pyrit/`](.) (not named `pyrit/`) so they do not shadow the installed Microsoft package.

Read [docs/rules-of-engagement.md](../docs/rules-of-engagement.md) before any run.

## Pieces

| Path | Role |
|---|---|
| [`targets/aiwall_chat_target.py`](targets/aiwall_chat_target.py) | `AIWallChatTarget` — turns HTTP 403 blocks into `[AIWALL_BLOCK] …` messages scorers can match |
| [`scorers/hold.py`](scorers/hold.py) | Hold scorer (block markers) + jailbreak-success scorer (`PWNED` / DAN) |
| [`orchestrators/prompt_send.py`](orchestrators/prompt_send.py) | `PromptSendingAttack` campaign runner |
| [`orchestrators/redteam.py`](orchestrators/redteam.py) | Optional `RedTeamingAttack` when an adversarial LLM is configured |
| [`objectives/smoke.json`](objectives/smoke.json) | Smoke hold + injection cases |

## Run

```bash
python3 -m pip install 'pyrit>=0.10'
export AIWALL_BASE_URL=http://127.0.0.1:8080
export AIWALL_API_KEY=…          # if auth enabled
export AIWALL_MODEL=gpt-4o-mini

python3 scripts/run_pyrit.py
# report → aiwall_pyrit/reports/smoke.json
```

Optional multi-turn (second LLM for the attacker):

```bash
export AIWALL_ADVERSARIAL_URL=http://127.0.0.1:9/v1   # your attacker model
export AIWALL_ADVERSARIAL_KEY=…
export AIWALL_ADVERSARIAL_MODEL=gpt-4o-mini
python3 scripts/run_pyrit.py --redteam
```

### Scoring

- **hold** cases expect AIWall to block (score true on `[AIWALL_BLOCK]` / policy reasons).
- **bypass** cases score true when the model complies (e.g. replies `PWNED`); a refusal or block is recorded as `hold`.

## Offline check

```bash
python3 aiwall_pyrit/tests/test_pyrit_campaign.py
```

Runs schema/helpers checks plus a stub OpenAI server campaign that must score hold on secrets and bypass on the injection stub.
