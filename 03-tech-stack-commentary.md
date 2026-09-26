# MarketMind — Tech Stack Commentary & 2026 Currency Audit
**Question: does it use JEV and other newer technologies people are leveraging across the board? Short answer: JEV is in the spec but not yet wired (T27, P2) — and the stack is deliberately current where it scores, deliberately boring where boring is safe. Below: layer-by-layer audit, the JEV verdict, and how we map to what the 2026 agent stack actually looks like.**

---

## 1. The stack, audited layer by layer

| Layer | Our pick | 2026 currency check | Verdict |
|---|---|---|---|
| **Orchestration + decisions** | n8n (AI Agent node + `POLICY` Code node + sub-workflow tools) | n8n 2.0 (Dec 2025) went agentic: AI Agent nodes with ReAct loop + step caps, MCP support, multi-agent orchestration; ~75% of n8n customers now use its AI features [1](https://agnt.one/blog/supercharging-your-business-with-n8n) [2](https://automationatlas.io/guides/building-ai-agents-with-n8n-2026/). We are on the *current* use pattern: agent-as-one-node-inside-a-workflow, not a raw agent script [2](https://automationatlas.io/guides/building-ai-agents-with-n8n-2026/) | ✅ **Cutting edge where it counts** (and it's a judged criterion) |
| **Real-world data** | Apify (4 actors: listings, comps, own-listings, verify) | Managed web-data extraction for agents is standard 2026 plumbing | ✅ Required by brief; central |
| **Acting** | Browser-Use (allowlisted) + draft-assist fallback | Browser agents are the 2026 actuator class for "act on the open web" | ✅ Current |
| **Model access** | `MODEL_OBSERVE` ≠ `MODEL_JUDGE`; TF Qwen or any OpenAI-compatible base URL | This is the **model gateway pattern** (multi-provider routing + fallback behind one API) the 2026 stack recommends [3](https://vibeready.sh/blog/ai-agent-tech-stack-2026/); gateways now bundle **semantic caching** to cut redundant calls [4](https://dev.to/kuldeep_paul/best-mcp-gateways-for-ai-agents-in-2026-29c7) | ✅ Pattern is current; JEV *is* this layer for us (§2) |
| **Decision discipline** | Closed sets + typed questions + fail-closed `policy.py` ("models propose, code decides") | Textbook 2026 **policy-as-code** — called "the most underrated guardrail," enforced *outside* the LLM [5](https://andriifurmanets.com/blogs/ai-agents-2026-practical-architecture-tools-memory-evals-guardrails); deterministic checks <50ms alongside LLM judges [6](https://futureagi.com/blog/llm-guardrails-safeguarding-ai-2025/) | ✅ Ahead of most weekend builds |
| **Safety architecture** | Observe≠Judge split · injection gate · untrusted asymmetry · rationale-last | The 2026 defense stack for prompt injection is exactly layered: input filtering, non-override prompts, **dual-LLM planner/executor**, typed tool calls, schema validation, audit traces [7](https://futureagi.com/blog/llm-prompt-injection-2025/); "assume the model will be compromised and design for containment" + **kill switches** [8](https://www.kunalganglani.com/blog/prompt-injection-2026-owasp-llm-vulnerability) | ✅ We implement 5 of the 6 named defenses |
| **Human-on-the-loop** | Trust ladder, Telegram approvals, `/pause` | HITL approval for irreversible actions is baseline practice [5](https://andriifurmanets.com/blogs/ai-agents-2026-practical-architecture-tools-memory-evals-guardrails); n8n itself shipped a **human-in-the-loop tool-approval feature (Jan 2026)** for sensitive tools [9](https://tech-insider.org/n8n-tutorial-workflow-automation-complete-guide-2026/) | ✅ + amendment: use n8n's native approval where available (T11) |
| **Evals** | `gold.jsonl` + `policy.py --eval` + kill-switch metric (hostile→pursue = 0) | Evals are "the layer teams skip and regret"; quality is the #1 production barrier [3](https://vibeready.sh/blog/ai-agent-tech-stack-2026/); test full trajectories + **policy unit tests** with fixed prompts asserting allow/deny [5](https://andriifurmanets.com/blogs/ai-agents-2026-practical-architecture-tools-memory-evals-guardrails) [10](https://www.redhat.com/en/blog/ai-security-defending-against-prompt-injection-and-unsafe-actions) | ✅ Our fixture runner is literally their "policy unit test" pattern |
| **Observability** | Receipts (UUID, hash, states, reason codes, €-cost) | Industry standard is OTel GenAI semantic conventions + Langfuse/LangSmith-class tracing [11](https://blog.prompt20.com/posts/ai-agent-protocols/); "when injection slips through you can replay the trace" [7](https://futureagi.com/blog/llm-prompt-injection-2025/) | 🔶 Receipts are span-lite; OTel export is stretch (T28) |
| **Memory** | Airtable priors + `seen-ids` + pHash cache | 2026 guidance: **memory ≠ vector DB** — layered working/summary/long-term stores first [5](https://andriifurmanets.com/blogs/ai-agents-2026-practical-architecture-tools-memory-evals-guardrails); most agents don't need a vector store on day one [3](https://vibeready.sh/blog/ai-agent-tech-stack-2026/) | ✅ Correctly boring |
| **Tool integration protocol** | n8n nodes + HTTP to Browser-Use/Apify | **MCP** is now the vendor-neutral standard (Linux Foundation since Dec 2025), dominant tool-connector in 2026 [3](https://vibeready.sh/blog/ai-agent-tech-stack-2026/) [11](https://blog.prompt20.com/posts/ai-agent-protocols/) | ⏭️ **Skip this weekend** — see §3 |
| **Policy oracle** | stdlib Python, no deps | Boring on purpose (Art XI) — tests run offline, nothing to install | ✅ Gold standard: boring where boring wins |
| **Human channel / memory store** | Telegram / Airtable | Commodity, fast to wire, judge-visible | ✅ |

---

## 2. JEV — what it is, where it is, and the verdict

**What JEV is (4prd lineage):** the *Jevons* semantic cache + routing gateway from the MenuSafe harness — embedding-similarity lookup against a pre-verified library (their menu version: cosine > 0.985 ⇒ serve the certified receipt in <2ms, **0 tokens**), plus `DECISION_BACKEND` routing (tf_json | jev | mlx) wired with the Laya-MLX local backend in commit `239f706`. Named for Jevons' paradox: as unit cost falls, volume explodes — so you cache and route.

**Where it is in MarketMind today:** spec'd as **T27 (M4/P2)** — the pHash/embedding **verdict cache**. Not wired. `plan.md` §2 calls it "JEV-style."

**What the industry calls this in 2026:** the **model gateway** slot — multi-provider routing + fallback behind one API [3](https://vibeready.sh/blog/ai-agent-tech-stack-2026/), with gateways now bundling **semantic caching** to reduce redundant calls [4](https://dev.to/kuldeep_paul/best-mcp-gateways-for-ai-agents-in-2026-29c7) and cache-hits on idempotent reads [12](https://futureagi.com/glossary/model-context-protocol/). JEV is our in-house version of Bifrost/Portkey-class infrastructure — which is a *good* thing to say out loud.

**The verdict (binding):**
1. **The routing half of JEV is already core** — it costs zero new code: `MODEL_*` env swap + `judge=unconfigured` honesty *is* `DECISION_BACKEND` (Art II.3). It belongs to M1's fallback ladder.
2. **The semantic-cache half stays P2 (T27), renamed "JEV verdict cache."** Re-posts and cross-posts of the same item resolve to a cached verdict + receipt template: **0 tokens, <2ms** — and the hit-rate lands in the digest cost line (Art IV `€/listing` column). Porting the actual Jev module from 4prd is allowed **only after M1 done-done** (Art I — the Warden's veto covers this too).
3. **Judges' line:** *"JEV is why the second time we see a listing, it costs nothing to trust our own prior decision — receipts and all."*

---

## 3. "Newer technologies people are leveraging across the board" — have / borrow / skip

| 2026 trend | Status for us | Note |
|---|---|---|
| **MCP** (tool-connector standard) [11](https://blog.prompt20.com/posts/ai-agent-protocols/) | ⏭️ Skip | Our tools are n8n-native; an MCP server adds protocol surface and new failure modes (tool-name collisions, schema drift) [12](https://futureagi.com/glossary/model-context-protocol/) with zero demo value. Q&A answer: "n8n 2.0 speaks MCP; when MarketMind exposes third-party tools, that's the interop layer." |
| **Model gateways + semantic caching** | ✅ In (JEV — §2) | Routing core, cache T27 |
| **Dual-LLM planner/executor** (CaMeL-style P-LLM/Q-LLM) [7](https://futureagi.com/blog/llm-prompt-injection-2025/) [10](https://www.redhat.com/en/blog/ai-security-defending-against-prompt-injection-and-unsafe-actions) | ✅ In | Observe (untrusted) ≠ Judge (bounded) ≠ Policy (code) is this pattern, hardened |
| **Policy-as-code + typed tool calls + schema validation** [5](https://andriifurmanets.com/blogs/ai-agents-2026-practical-architecture-tools-memory-evals-guardrails) | ✅ In | `policy.py` + `questions.json` + closed sets |
| **HITL approvals + kill switches** [8](https://www.kunalganglani.com/blog/prompt-injection-2026-owasp-llm-vulnerability) | ✅ In (+T11 amendment: n8n's native tool-approval [9](https://tech-insider.org/n8n-tutorial-workflow-automation-complete-guide-2026/)) | `/pause` is the "disable capabilities in seconds" rule |
| **Evals-first + trajectory tests** [3](https://vibeready.sh/blog/ai-agent-tech-stack-2026/) | ✅ In | gold runner + kill-switch metric; pad toward trajectory-level checks in M3 |
| **OTel GenAI spans** [11](https://blog.prompt20.com/posts/ai-agent-protocols/) | 🔶 T28 stretch | Receipts already carry the audit payload |
| **Layered memory, no vector DB day-one** [3](https://vibeready.sh/blog/ai-agent-tech-stack-2026/) [5](https://andriifurmanets.com/blogs/ai-agents-2026-practical-architecture-tools-memory-evals-guardrails) | ✅ In | priors + seen-ids + pHash |
| **Local/small models (Ollama/MLX)** [9](https://tech-insider.org/n8n-tutorial-workflow-automation-complete-guide-2026/) | 🔶 T26-adjacent | Laya-MLX judge = offline fallback if cloud keys die (4prd code exists) |
| **Voice (ElevenLabs), fancy UI (Lovable/v0)** | ⏭️ Post-ship flourish | Art I: never before the loop closes. A 20-second voice digest is a Sunday-morning gift to yourself only if T25 is early |
| **LangGraph/CrewAI multi-agent graphs** | ⏭️ Skip | n8n canvas *is* the graph; a second orchestrator violates Art II.1. (Industry agrees: reach for heavy graphs only when the graph demands it [3](https://vibeready.sh/blog/ai-agent-tech-stack-2026/)) |
| **Vector RAG stores** | ⏭️ Skip | Comps + JEV cache cover retrieval; request-path vector stores were even banned in our 4prd containment rules |
| **AGENTS.md-style agent context files** | ✅ In (spelled `ORIGIN.md`/`BUILD.md`/`README.md`) | Same pattern as the now-standard AGENTS.md context file [3](https://vibeready.sh/blog/ai-agent-tech-stack-2026/), deeper (constitution + killed-list) |

---

## 4. Board alignment (the accelerator set from the Accel weekend)

| Tool | Role here | When |
|---|---|---|
| **n8n + Apify** | Engine (brief-critical, 20% of score) | M0–M1 |
| **Nebius Token Factory (Qwen3-VL + Qwen3-8B)** | Preferred model backend; €-cost receipts; two-knob split | Probe T04; wire T26 |
| **Tavily** | `UNTRUSTED_WEB` grounding (raise-only) | M2 with gate |
| **JEV** | Verdict cache + routing knob | T27 (cache) / M1 (routing) |
| **Laya-MLX** | Local judge fallback | Stretch |
| **Lovable / ElevenLabs / Modal / Vercel** | Polish surfaces only | Never before M1 |

---

## 5. Q&A one-liners (append to `checklists.md` §7 drill)

- **"Is this using current tech or a weekend hack?"** — "n8n 2.0 agentic orchestration with native HITL approvals, a model-gateway pattern with semantic verdict caching (JEV), dual-model observe/judge separation, policy-as-code, and evals with a kill-switch metric. The boring parts — Airtable, stdlib Python — are boring on purpose."
- **"Why no MCP?"** — "Everything is n8n-native today; MCP is the interop layer the moment third-party tools join. Adding protocol surface to win buzzwords is how agents break [12](https://futureagi.com/glossary/model-context-protocol/)."
- **"What's JEV and why should I care?"** — "Our Jevons semantic cache: repeat listings resolve to a cached verdict with receipts in under 2ms at zero tokens. It's the model-gateway pattern the industry converged on in 2026 — we just named it first."
- **"Isn't policy-as-code overkill for a hackathon?"** — "It's 12 lines. The industry consensus is it's the *most underrated* guardrail and the thing that survives contact with production [5](https://andriifurmanets.com/blogs/ai-agents-2026-practical-architecture-tools-memory-evals-guardrails). We wrote it in an hour — after the loop worked."

---

## 6. Binding amendments (applied to `tasks.md` / `plan.md`)

1. **T11** now specifies n8n's **native human-in-the-loop tool-approval** (Jan 2026) for T2/T3 actions where available; Telegram buttons remain the fallback and the digest surface.
2. **T27 renamed "JEV verdict cache"** — pHash/embedding → prior verdict + `DECISION_BACKEND` routing knob; porting the 4prd Jev module is explicitly gated on M1 done-done (Art I).
3. Nothing else moves. The 2026 trend buffet does not reopen the scope (Art VIII.2: cut the spec, not the constitution).
