# Detections bridge

AIWall-redteam techniques map to SIEM sample lines and rules in
[AIWall-detections](https://github.com/MohsenBahremani/AIWall-detections).

| Resource | Location |
|---|---|
| Machine-readable map | `AIWall-detections/validation/redteam_bridge.json` |
| Operator guide | [AIWall-detections docs/redteam-bridge.md](https://github.com/MohsenBahremani/AIWall-detections/blob/main/docs/redteam-bridge.md) |
| Sample corpus | `AIWall-detections/validation/samples/aiwall.audit.v1.sample.jsonl` |

## Workflow

1. Run payloads or `scripts/run_regression.py` against a lab AIWall.
2. Export audit JSONL from AIWall (`GET /events/export.jsonl`).
3. Confirm holds match `expected.reason_any` on the payload.
4. If a new stable reason appears, open a PR on AIWall-detections to add a sample line, expected hit, and bridge row.
5. Score a live export: `AIWall-detections/scripts/validate_export.sh --with-regression` (from a sibling checkout).

Must-block cases in `regression/must_block.json` (SE-01…SE-03) already have detection coverage via `req-secret-001` / Wazuh 107210.
