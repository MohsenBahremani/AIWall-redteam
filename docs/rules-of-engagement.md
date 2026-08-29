# Rules of engagement

Authorized security testing only. Read this before running any payload, Garak/PyRIT campaign, or script from this repository.

## Authorization

| Allowed | Not allowed |
|---|---|
| AIWall instances **you own** (homelab, laptop, your org’s lab) | Third-party AI SaaS, employers, schools, or customers **without written approval** |
| Explicit written authorization that names the target, window, and tester | “Security research” against live production without a change ticket / RoE sign-off |
| Local mock upstreams and disposable API keys | Using stolen, shared, or production secrets as test material |

If authorization is unclear, **do not run**.

## Scope (in)

- AIWall as an OpenAI-compatible **gateway** (`/v1/chat/completions` and related routes)
- Controls: policy engine, secret scanning, family/category blocks, cost/daily limits, agent guardrails / approvals
- Observability: audit export (`aiwall.audit.v1`), control-panel events, detection packs in [AIWall-detections](https://github.com/MohsenBahremani/AIWall-detections)

## Scope (out)

- Attacking model providers’ shared infrastructure (OpenAI, Anthropic, etc.) beyond your own billed sandbox account used as an upstream
- Social engineering of humans, phishing, or account takeover of third parties
- Denial-of-service against anything you do not own (including flooding paid APIs in a way that incurs unbounded cost without a budget cap)
- Publishing working bypasses for unpatched AIWall issues before maintainers have a chance to fix them

## Safety controls (mandatory)

1. **Lab target first** — prefer AIWall + a local/mock upstream (e.g. Ollama or a stub) so failed blocks never send secrets to a real vendor.
2. **Fake secrets only** — payloads must use clearly synthetic tokens (see testing methodology). Never paste live credentials into prompts.
3. **Budget cap** — set AIWall cost / daily-limit policies (or provider spend limits) before cost-abuse tests.
4. **Agent isolation** — agent tool-abuse tests run on disposable VMs/containers, not on hosts with production data.
5. **Stop on unexpected impact** — if a test affects a non-lab system, halt and escalate to the system owner.

## Data handling

- Treat payload files and campaign reports as **sensitive** (they encode bypass ideas).
- Do not commit real API keys, personal data, or production audit dumps.
- Prefer redacted reports (`request_id`, decision, reason) when sharing outside the lab.

## Disclosure

1. File bypasses against [AIWall](https://github.com/MohsenBahremani/AIWall) (private security contact if/when published; otherwise a GitHub issue marked clearly as a security finding and coordinated with maintainers).
2. Do not open a public “here’s how to bypass” write-up until a fix or mitigating config is available, or maintainers explicitly approve.
3. Successful attacks that are *intended* product gaps become **requirements**; blocked attacks become **regression** cases in `regression/must_block.json`, which `scripts/run_regression.py` and CI enforce on every change.

## Tester checklist

- [ ] Written authorization (or personal ownership) for this target
- [ ] Lab AIWall URL and API key documented in notes (not committed)
- [ ] Upstream is mock/local or a capped sandbox account
- [ ] Read [testing-methodology.md](testing-methodology.md)
- [ ] Know how to stop the campaign (`Ctrl-C`, disable client, revoke key)

## Related

- [testing-methodology.md](testing-methodology.md) — how to set up and score tests
- Repo README — high-level purpose and layout
