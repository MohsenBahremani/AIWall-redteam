# Attack catalog

Enumerates adversarial **techniques** AIWall-redteam will exercise, mapped to [OWASP LLM Top 10](https://genai.owasp.org/llm-top-10/) and [MITRE ATLAS](https://atlas.mitre.org/).

Machine-readable source: [`attack-catalog.json`](attack-catalog.json).  
Safety and lab setup: [rules-of-engagement.md](rules-of-engagement.md), [testing-methodology.md](testing-methodology.md).

Payloads for each category live under `payloads/<category>/` (Phase 7.3). Use `scripts/run_payloads.py` against a lab target.

## Summary matrix

| Category | Technique ids | Primary OWASP | Primary ATLAS |
|---|---|---|---|
| [Prompt injection](#prompt-injection) | PI-01 … PI-03 | LLM01 | AML.T0051 / AML.T0054 / AML.T0056 |
| [Secret exfiltration](#secret-exfiltration) | SE-01 … SE-03 | LLM02 | AML.T0057 / AML.T0055 |
| [Unsafe content](#unsafe-content) | UC-01 … UC-02 | LLM05 | AML.T0048 |
| [Agent tool abuse](#agent-tool-abuse) | AT-01 … AT-03 | LLM06 | AML.T0050 / AML.T0053 |
| [Cost abuse](#cost-abuse) | CA-01 … CA-03 | LLM10 | AML.T0034 / AML.T0046 |

Detection overlap (when audit reasons fire): [AIWall-detections coverage matrix](https://github.com/MohsenBah/AIWall-detections/blob/main/docs/coverage-matrix.md).

---

## Prompt injection

**Intent:** Override or extract instructions so the model (or agent) behaves outside the operator’s intent.

| Id | Technique | OWASP | ATLAS | AIWall control today | Expected hold |
|---|---|---|---|---|---|
| **PI-01** | Direct instruction override | LLM01 | AML.T0051 | Custom policies; no dedicated injector yet | Policy-dependent; often still `allow` |
| **PI-02** | Jailbreak / safety bypass | LLM01 | AML.T0054, AML.T0051 | Category / family policies | `category-blocked` when classifiers match |
| **PI-03** | System / meta-prompt extraction | LLM07, LLM01 | AML.T0056, AML.T0051 | Gap | Usually `allow` — track bypasses as product work |

**Notes:** Gateway-level injection detection is an intentional gap, tracked in the AIWall-detections ATLAS coverage matrix (AML.T0051, AML.T0054, AML.T0056). Results from these techniques feed detection and product backlogs rather than matching any current Wazuh rule.

---

## Secret exfiltration

**Intent:** Move credentials or secrets into an upstream model path (or coerce the model to help exfiltrate them).

| Id | Technique | OWASP | ATLAS | AIWall control today | Expected hold |
|---|---|---|---|---|---|
| **SE-01** | Credential paste to provider | LLM02 | AML.T0057, AML.T0055 | Secret scanner + block/redact/warn | `secret-detected` / `secret-redacted` |
| **SE-02** | Env / config dump | LLM02 | AML.T0057, AML.T0055 | dotenv / entropy detectors | block or redact per policy |
| **SE-03** | Inference-path exfil framing | LLM02 | AML.T0024, AML.T0057 | Input scanning; limited output DLP | Hold if secret in **input**; output-only is a gap |

**Synthetic secrets only** — see RoE and methodology.

Playbook: [secret-leak-detected](https://github.com/MohsenBah/AIWall-detections/blob/main/playbooks/secret-leak-detected.md).

---

## Unsafe content

**Intent:** Violate family / category policy (especially **child** profiles).

| Id | Technique | OWASP | ATLAS | AIWall control today | Expected hold |
|---|---|---|---|---|---|
| **UC-01** | Explicit / sexual (child profile) | LLM05, LLM09 | AML.T0048 | Child preset + categories | `category-blocked` |
| **UC-02** | Unsafe / violence categories | LLM05 | AML.T0048 | Category policies | `category-blocked` when matched |

Playbook: [child-safety-block](https://github.com/MohsenBah/AIWall-detections/blob/main/playbooks/child-safety-block.md).

---

## Agent tool abuse

**Intent:** Abuse shell, file, or plugin tools attached to an agent through the OpenAI-compatible tool interface.

| Id | Technique | OWASP | ATLAS | AIWall control today | Expected hold |
|---|---|---|---|---|---|
| **AT-01** | Destructive shell | LLM06 | AML.T0050, AML.T0053 | `agent_guardrails` block / approval | `block` or `approval-denied` |
| **AT-02** | Sensitive file read | LLM06, LLM02 | AML.T0053, AML.T0055 | File path rules | block / require_approval |
| **AT-03** | Medium-risk shell (e.g. sudo) | LLM06 | AML.T0050 | warn band | `warn` (partial) |

Playbook: [suspicious-agent-action](https://github.com/MohsenBah/AIWall-detections/blob/main/playbooks/suspicious-agent-action.md).  
Run only on disposable lab hosts (RoE).

---

## Cost abuse

**Intent:** Exhaust spend, quotas, or capacity (unbounded consumption).

| Id | Technique | OWASP | ATLAS | AIWall control today | Expected hold |
|---|---|---|---|---|---|
| **CA-01** | Single-request cost threshold | LLM10 | AML.T0034 | Cost policies | `cost-threshold` |
| **CA-02** | Daily usage limit | LLM10 | AML.T0034, AML.T0046 | Profile daily caps | `daily-limit` |
| **CA-03** | Chaff / flood | LLM10 | AML.T0046, AML.T0029 | Daily limits / rate limits | limit or error; no shared-infra DoS |

Cap lab budgets before running CA-* probes.

---

## Maintaining the catalog

1. Add a technique → update `attack-catalog.json` (id, OWASP, ATLAS, expected hold).
2. Refresh this markdown table to match.
3. Run `python3 docs/tests/test_methodology_docs.py` (includes catalog checks).
4. When payloads exist, put them under the category’s `payload_dir` and reference the technique id.
