# Garak against AIWall

[Garak](https://github.com/NVIDIA/garak) LLM vulnerability scans aimed at the AIWall OpenAI-compatible gateway (`/v1/chat/completions`).

Read [docs/rules-of-engagement.md](../docs/rules-of-engagement.md) before any run.

## Configs

| File | Purpose |
|---|---|
| [`configs/aiwall-smoke.yaml`](configs/aiwall-smoke.yaml) | One small probe (`dan.Dan_11_0`), fast lab check |
| [`configs/aiwall-lab.yaml`](configs/aiwall-lab.yaml) | Broader LLM01-oriented probe set |

Both use `openai.OpenAICompatible` with `uri` pointing at AIWall (`…/v1/`).

## Run

```bash
# Lab AIWall up (mock/local upstream preferred)
export AIWALL_BASE_URL=http://127.0.0.1:8080
export AIWALL_API_KEY=…                    # if auth enabled
export OPENAICOMPATIBLE_API_KEY="${AIWALL_API_KEY:-aiwall-lab}"

python3 -m pip install 'garak>=0.10'
python3 scripts/run_garak.py --config garak/configs/aiwall-smoke.yaml
```

`run_garak.py` rewrites the generator `uri` from `AIWALL_BASE_URL` and invokes `python -m garak`. Reports land under `garak/reports/` (`report_prefix` from the YAML).

### Interpreting results through AIWall

- Garak scores **model** behavior (jailbreak success, etc.).
- AIWall may **block** probes (HTTP 403). Garak often records those as generator errors — treat that as a **control hold**, then confirm with:
  ```bash
  curl -sS "$AIWALL_BASE_URL/events/export.jsonl?window_hours=1" | tail
  ```
- Pair Garak findings with [attack-catalog.md](../docs/attack-catalog.md) and payload must-hold probes.

## Offline check

```bash
python3 garak/tests/test_garak_configs.py
```

## Reports

Generated artifacts (jsonl / html / hitlog) are gitignored except placeholders. Keep baseline copies under `reports/` when you publish baseline assessments.
