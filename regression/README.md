# Must-block regression suite

Cases that **must stay blocked** (from the Phase 7.7 baseline). CI fails if any bypass.

Registry: [`must_block.json`](must_block.json)

| Id | Category | Baseline reason |
|---|---|---|
| SE-01 | secret-exfiltration | AWS key → `secret-detected` |
| SE-02 | secret-exfiltration | GitHub token / dotenv → `secret-detected` |
| SE-03 | secret-exfiltration | Exfil framing with key in input → `secret-detected` |

## Run

```bash
# List
python3 scripts/run_regression.py --list

# CI / offline: hold stub (pass) + bypass stub self-check (suite must fail)
python3 scripts/run_regression.py --stub
python3 scripts/run_regression.py --expect-fail
python3 regression/tests/test_regression.py

# Lab AIWall (authorized only)
export AIWALL_BASE_URL=http://127.0.0.1:8080
python3 scripts/run_regression.py
```

Adding a new regression case: confirm it holds in a campaign, then append to `must_block.json` with `must_hold: true` on the payload.
