#!/usr/bin/env python3
"""NIGHT MODE for the deployed n8n M0 workflow — runs in n8n cloud, so the hero run survives the laptop being off.

What it changes on the DEPLOYED workflow (the repo templates are untouched; parity tests unaffected):
  - schedule: every NIGHT_INTERVAL_MIN minutes (default 10)
  - Telegram becomes quiet: the per-tick run summary is only sent when (a) something was drafted, (b) the night
    mode was just armed (proof message), or (c) the first tick after 08:00 Europe/Amsterdam (morning digest with
    overnight totals accumulated in workflow static data)
  - the wording of those messages comes from GLM-5.3 on Tinker (words only). Every number is computed by the
    Code nodes and appended verbatim; if GLM fails or returns nothing, the code-built text is sent alone.
    GLM never sees a decision it could change and never decides anything (Art V).
  - comps variables refreshed from out/comps_cache.json (eBay DE sold)

  python3 n8n/night_mode.py            # arm (deploy + activate)
  python3 n8n/night_mode.py --status   # active? last executions
  python3 n8n/night_mode.py --off      # deactivate (the laptop-free kill switch is also the n8n app toggle)
"""
from __future__ import annotations
import copy, json, sys, time
from pathlib import Path

N8N_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(N8N_DIR))
import deploy_n8n as dep  # noqa: E402

WID = "2wmNJ9ZtWc0j516a"                      # MarketMind M0 (deployed)
CRED_GLM = "Magpie · Tinker GLM-5.3 (Bearer)"
TINKER_URL = "https://tinker.thinkingmachines.dev/services/tinker-prod/oai/api/v1/chat/completions"
GLM_MODEL = "zai-org/GLM-5.3:peft:262144"
NIGHT_INTERVAL_MIN = 10
SUMMARY = "Run summary (1 line/execution)"
TG_SUMMARY = "Telegram — run summary"
GATE, GLM, COMPOSE = "Night gate (code)", "GLM-5.3 words (Tinker)", "Compose — numbers from code"

GATE_JS = r"""// NIGHT GATE — decides WHETHER to notify (code, not the model) and accumulates overnight totals.
const sd = $getWorkflowStaticData('global');
const s = $input.first().json;                       // from Run summary: {text, counts, execution_id}
const c = s.counts || {};
const n = sd.night = sd.night || { since: new Date().toISOString(), runs: 0, scanned: 0, skipped: 0, escalated: 0, drafted: 0 };
n.runs += 1; n.scanned += (c.skipped||0)+(c.escalated||0)+(c.drafted||0)+(c.pursued_auto||0);
n.skipped += c.skipped||0; n.escalated += c.escalated||0; n.drafted += (c.drafted||0)+(c.pursued_auto||0);
const ams = new Date().toLocaleString('en-CA', { timeZone: 'Europe/Amsterdam', hour12: false });   // 'YYYY-MM-DD, HH:MM:SS'
const day = ams.slice(0, 10), hour = Number(ams.slice(12, 14));
let kind = null;
if (!sd.armed) { kind = 'armed'; sd.armed = new Date().toISOString(); }
else if ((c.drafted||0) + (c.pursued_auto||0) > 0) kind = 'draft';
else if (hour >= 8 && hour < 12 && sd.morning_day !== day) { kind = 'morning'; sd.morning_day = day; }
if (!kind) return [];                                 // quiet tick: nothing goes to Telegram
const facts = kind === 'morning'
  ? `overnight since ${n.since.slice(0,16)}Z: ${n.runs} runs, ${n.scanned} new listings decided, ${n.skipped} skipped, ${n.escalated} escalated, ${n.drafted} drafted`
  : kind === 'armed'
  ? `night mode armed; first run decided ${(c.skipped||0)+(c.escalated||0)+(c.drafted||0)} new listings (${c.drafted||0} drafted)`
  : `${c.drafted||0} new offer draft(s) waiting for a human; this run: ${c.skipped||0} skipped, ${c.escalated||0} escalated`;
const out = { kind, facts, code_text: s.text, night: { ...n } };
if (kind === 'morning') sd.night = { since: new Date().toISOString(), runs: 0, scanned: 0, skipped: 0, escalated: 0, drafted: 0 };
out.glm_body = {
  model: 'MODEL_PLACEHOLDER', max_tokens: 500, temperature: 0.2,
  messages: [
    { role: 'system', content: 'You write ONE short, plain sentence (max 25 words) for a phone notification about an autonomous classifieds agent called Magpie. Use only the facts given. Never add numbers, prices, advice to buy, or claims not in the facts. No emojis, no markdown.' },
    { role: 'user', content: `Notification type: ${kind}. Facts: ${facts}.` }
  ]
};
return [{ json: out }];"""

COMPOSE_JS = r"""// COMPOSE — GLM supplies words only; every number below comes from the Code nodes (Art IV/V).
const g = $('Night gate (code)').first().json;
const r = $input.first().json || {};
let line = '';
try { line = String(((r.choices || [])[0] || {}).message?.content || '').trim().split('\n')[0].slice(0, 220); } catch (e) { line = ''; }
// the model may REPEAT numbers from the facts but never introduce new ones (Art IV)
const allowed = new Set((g.facts.match(/\d+/g) || []));
if ((line.match(/\d+/g) || []).some(x => !allowed.has(x))) line = '';
const head = { armed: '🌙 Magpie night mode (n8n cloud · laptop-free)', draft: '🟢 Magpie — draft awaiting you', morning: '☀️ Magpie overnight digest' }[g.kind];
const text = [head, line ? `“${line}” — GLM-5.3` : '(GLM wording unavailable — facts only)', '', g.facts,
  g.kind === 'morning' ? '' : '', g.code_text].filter(x => x !== undefined).join('\n').replace(/\n{3,}/g, '\n\n');
return [{ json: { text } }];"""


def build(wf: dict, glm_cred: dict) -> dict:
    wf = copy.deepcopy(wf)
    nodes, conns = wf["nodes"], wf["connections"]
    names = {n["name"] for n in nodes}
    for n in nodes:
        if n["type"].endswith("scheduleTrigger"):
            n["parameters"]["rule"] = {"interval": [{"field": "minutes", "minutesInterval": NIGHT_INTERVAL_MIN}]}
    summ = next(n for n in nodes if n["name"] == SUMMARY)
    x, y = summ["position"]
    if GATE not in names:
        nodes += [
            {"parameters": {"jsCode": GATE_JS.replace("MODEL_PLACEHOLDER", GLM_MODEL)}, "id": "night-gate", "name": GATE,
             "type": "n8n-nodes-base.code", "typeVersion": 2, "position": [x + 200, y + 180]},
            {"parameters": {"method": "POST", "url": TINKER_URL, "authentication": "genericCredentialType",
                            "genericAuthType": "httpHeaderAuth", "sendHeaders": True,
                            "headerParameters": {"parameters": [{"name": "User-Agent", "value": "OpenAI/Python 1.99.0"}]},
                            "sendBody": True, "specifyBody": "json", "jsonBody": "={{ JSON.stringify($json.glm_body) }}",
                            "options": {"timeout": 60000}},
             "id": "night-glm", "name": GLM, "type": "n8n-nodes-base.httpRequest", "typeVersion": 4.2,
             "position": [x + 400, y + 180], "credentials": {"httpHeaderAuth": glm_cred},
             "onError": "continueRegularOutput", "retryOnFail": True, "maxTries": 2, "waitBetweenTries": 3000},
            {"parameters": {"jsCode": COMPOSE_JS}, "id": "night-compose", "name": COMPOSE,
             "type": "n8n-nodes-base.code", "typeVersion": 2, "position": [x + 600, y + 180]},
        ]
    else:  # re-arm: refresh code
        for n in nodes:
            if n["name"] == GATE:
                n["parameters"]["jsCode"] = GATE_JS.replace("MODEL_PLACEHOLDER", GLM_MODEL)
            if n["name"] == COMPOSE:
                n["parameters"]["jsCode"] = COMPOSE_JS
            if n["name"] == GLM:
                n["credentials"] = {"httpHeaderAuth": glm_cred}
    conns[SUMMARY] = {"main": [[{"node": GATE, "type": "main", "index": 0}]]}
    conns[GATE] = {"main": [[{"node": GLM, "type": "main", "index": 0}]]}
    conns[GLM] = {"main": [[{"node": COMPOSE, "type": "main", "index": 0}]]}
    conns[COMPOSE] = {"main": [[{"node": TG_SUMMARY, "type": "main", "index": 0}]]}
    return {"name": wf["name"], "nodes": nodes, "connections": conns,
            "settings": {"executionOrder": wf.get("settings", {}).get("executionOrder", "v1")}}


def tinker_key() -> str:
    for line in (Path.home() / ".hermes" / ".env").read_text().splitlines():
        if line.startswith(("TINKER_API_KEY=", "TML_API_KEY=")):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit("no TINKER_API_KEY in ~/.hermes/.env")


def main() -> int:
    env = dep.load_env()
    api = dep.N8N(env.get("N8N_BASE_URL", "https://knreddy.app.n8n.cloud"), env["N8N_API_KEY"], dry=False)
    if "--off" in sys.argv:
        api.call("POST", f"/workflows/{WID}/deactivate")
        print("night mode OFF (workflow deactivated)")
        return 0
    if "--pull" in sys.argv:
        # evidence: copy the night's n8n ledger receipts to out/ (laptop was off; n8n kept the executions)
        dest = dep.APP / "out" / "n8n_night_receipts.jsonl"
        seen = set()
        if dest.exists():
            seen = {json.loads(l).get("row_hash") for l in dest.read_text().splitlines() if l.strip()}
        ex = api.list_all(f"/executions?workflowId={WID}&status=success")
        added = 0
        with open(dest, "a") as fh:
            for e in sorted(ex, key=lambda e: int(e["id"])):
                full = api.call("GET", f"/executions/{e['id']}?includeData=true")
                runs = full.get("data", {}).get("resultData", {}).get("runData", {}).get("Receipt ledger (Art VII.1)")
                if not runs:
                    continue
                for it in (runs[-1].get("data", {}).get("main") or [[]])[0]:
                    rec = {**(it["json"].get("receipt") or {}), "n8n_execution": e["id"]}
                    if rec.get("row_hash") and rec["row_hash"] not in seen:
                        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
                        seen.add(rec["row_hash"])
                        added += 1
        print(f"pulled {added} new n8n receipts -> {dest} (total {len(seen)})")
        return 0
    if "--status" in sys.argv:
        w = api.call("GET", f"/workflows/{WID}")
        ex = api.call("GET", f"/executions?workflowId={WID}&limit=8").get("data", [])
        print(f"active={w['active']} · nodes={len(w['nodes'])} · night gate={'yes' if any(n['name'] == GATE for n in w['nodes']) else 'no'}")
        for e in ex:
            print(f"  exec {e['id']:>4} {e.get('status'):8} {e.get('mode'):8} {str(e.get('startedAt'))[:19]}")
        return 0
    state = json.loads(dep.STATE_FILE.read_text()) if dep.STATE_FILE.exists() else {}
    cred = dep.ensure_credential(api, state, CRED_GLM, "httpHeaderAuth",
                                 {"name": "Authorization", "value": f"Bearer {tinker_key()}"})
    dep.STATE_FILE.write_text(json.dumps(state, indent=2))
    print("credential:", cred and cred.get("name"))
    dep.upsert_variables(api, env)                                         # fresh comps (eBay DE sold)
    w = api.call("GET", f"/workflows/{WID}")
    if w.get("active"):
        api.call("POST", f"/workflows/{WID}/deactivate")
    body = build(w, cred)
    sd_before = w.get("staticData")
    if sd_before:
        body["staticData"] = sd_before                 # keep seen-ids, ledger chain head, draft cap
    try:
        api.call("PUT", f"/workflows/{WID}", body)
    except SystemExit as e:                             # older API schema without staticData on PUT
        if "staticData" not in str(e):
            raise
        body.pop("staticData", None)
        api.call("PUT", f"/workflows/{WID}", body)
    after = (api.call("GET", f"/workflows/{WID}").get("staticData") or {}).get("global", {})
    print(f"static data kept: seen={len(after.get('seen', []))} ledger_head={str(after.get('last_hash'))[:16]} "
          f"drafts_today={after.get('drafts_today')}")
    api.call("POST", f"/workflows/{WID}/activate")
    w = api.call("GET", f"/workflows/{WID}")
    print(f"night mode ARMED · active={w['active']} · every {NIGHT_INTERVAL_MIN} min · nodes={len(w['nodes'])}"
          f" · {time.strftime('%H:%M:%S')}")
    return 0 if w["active"] else 1


if __name__ == "__main__":
    sys.exit(main())
