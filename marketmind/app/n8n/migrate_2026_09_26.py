#!/usr/bin/env python3
"""One-off migration of wf-m0/m1/m2 (2026-09-26 review fixes). Idempotent.
 * price node: comps from $env.COMPS_JSON (live eBay cache, injected at deploy) — no hard-coded table;
   mirrors Python grounding (not_device / no_price), carries comps provenance (key, n, source).
 * POLICY loop (below the parity-checked gate function): honest reason relabel + daily draft cap.
 * Airtable receipt (needed a PAT we don't have) -> 'Receipt ledger' Code node: hash-chained receipts
   in workflow static data + n8n execution id. Runs ONCE on all items (POLICY -> ledger -> route).
 * Per-item escalation Telegram (spam) -> one 'Run summary' Telegram line per execution.
"""
import json
from pathlib import Path

N8N = Path(__file__).resolve().parent

PRICE_JS = r"""// price + facts (code) — margin_z COMPUTED here from LIVE comps (Art V.2: never asked of a model).
// Comps = the Python loop's live eBay DE comps cache (SOLD prices, 30d, used; asking-price fallback per
// family), injected as $env.COMPS_JSON at deploy ({key: [median, mad, n]}) + $env.COMPS_BASIS.
// No comps => margin_z null => gate escalates (fail-closed).
let COMPS = {};
try { COMPS = JSON.parse($env.COMPS_JSON || '{}'); } catch (e) { COMPS = {}; }
const COMPS_SOURCE = String($env.COMPS_SOURCE || 'unconfigured');
const ADVANCE_FEE = /(iban|nl\d{2}[A-Z]{4}\d{4,}|tikkie|paypal\.me|pay (in advance|to reserve)|transfer €?\d+)/i;
// mirror of mm/rerank.py NON_DEVICE_LISTING_RE — repair/part/wanted ads never grounded vs device comps
const ACC_FOR = /\b(case|hoes(je)?|cover|oplader|lader|kabel|screen\s*protector|skin|tas|houder|dock)\s+(voor|for|für)\b/i;
const FAMILY_EXCLUDE = { 'nintendo switch': /\b(lite|switch\s*2)\b/i };
const COMPS_BASIS = String($env.COMPS_BASIS || 'asking');
const NON_DEVICE = /\b(reparatie|reparaties|repareren|repair|reparatur|vervangen|vervanging|onderdel(en)?|onderdeel|parts?|scherm\s*reparatie|accu\s*vervangen|batterij\s*vervangen|screenprotector|gezocht|zoek(e|ende)?|inkoop|wij\s*kopen|opkoper|te\s*huur|huren|lessen|cursus|installeren|service)\b/i;
// mirror of mm/rerank.py COMPS_GENERATIONS — comps family built only from these generations
const GENS = { iphone: ['13', '14', '15'] };
let m = null;
const paused = $env.AUTO_PAUSE === '1';
let crypto = null;
try { crypto = require('crypto'); } catch (e) { crypto = null; }
const h16 = (s) => crypto ? crypto.createHash('sha256').update(s).digest('hex').slice(0, 16)
  : (() => { let h = 0x811c9dc5; for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 0x01000193) >>> 0; } return ('fnv1a-' + h.toString(16)).padStart(16, '0'); })();

for (const it of items) {
  const titleRaw = String(it.json.title || '');
  const title = titleRaw.toLowerCase();
  const desc = String(it.json.description || '');
  const fullText = (title + ' ' + desc).slice(0, 2000);
  const price = Number(it.json.price_eur || it.json.price || 0);

  let key = null;
  for (const k of Object.keys(COMPS).sort((a, b) => b.length - a.length)) {
    if (title.includes(k)) { key = k; break; }
  }
  let note = null;
  if (key && (NON_DEVICE.test(titleRaw) || ACC_FOR.test(titleRaw))) { key = null; note = 'not_device'; }
  else if (key && FAMILY_EXCLUDE[key] && FAMILY_EXCLUDE[key].test(titleRaw)) { key = null; note = 'model_mismatch'; }
  else if (key && GENS[key] && (m = titleRaw.match(/\biphone\s*(\d{1,2})\b/i)) && !GENS[key].includes(m[1])) { key = null; note = 'model_mismatch'; }
  else if (key && !(price > 0)) { note = 'no_price'; }
  const c = key ? COMPS[key] : null;           // [median, mad, n]
  let mz = null;
  if (c && c[1] > 0 && price > 0) mz = (c[0] - price) / c[1];

  const isMine = !!it.json.is_mine;
  it.json.id = it.json.id || it.json.listingId || String(it.json.url || '').slice(-24);
  it.json.text = fullText;
  it.json.facts = {
    margin_z: mz,
    comps: c ? { median: c[0], mad: c[1], n: c[2], source: COMPS_SOURCE, basis: COMPS_BASIS } : null,
    comps_key: key,
    grounding_note: note,
    duplicate_photo: Number(it.json.duplicate_photo || 0),
    offplatform_payment_request: !!(it.json.offplatform_payment_request || ADVANCE_FEE.test(fullText)),
    text: fullText,
    is_mine: isMine
  };
  it.json.over_cap = paused;
  it.json.tier = isMine ? 'T1' : (price > 200 ? 'T3' : (it.json.tier || 'T2'));

  // H1 offer band: min(round5(ask*0.8), floor(ask*0.8)) — same formula as mm/act.py::draft_offer
  const offerEur = price > 0 ? Math.min(Math.round(price * 0.8 / 5) * 5, Math.floor(price * 0.8)) : 0;
  it.json.draft = {
    offer_eur: offerEur,
    offer_ratio: price > 0 ? Math.round(offerEur / price * 100) / 100 : null,
    text_nl: `Hoi! Mooi dat je ${titleRaw || 'dit item'} aanbiedt. Zou je €${offerEur} willen accepteren? Ik kan het ophalen wanneer het uitkomt. (Laat gerust weten of dit past)`
  };
  it.json.ts = new Date().toISOString();
  it.json.input_hash = h16(`${it.json.id}:${price}:${title}`);
  it.json.hash_alg = crypto ? 'sha256/16' : 'fnv1a';
}
return items;"""

POLICY_TAIL_V0 = r"""for (const it of items) {
  // (cap state lives inside the loop so the parity test's gate-function extraction stays unchanged)
  const sdCap = $getWorkflowStaticData('global');
  const today = new Date().toISOString().slice(0, 10);
  if (sdCap.draft_day !== today) { sdCap.draft_day = today; sdCap.drafts_today = 0; }
  const DRAFT_CAP = Number($env.N8N_MAX_DRAFTS || 3);
  const f = it.json.facts || {};
  let g = gateV0(f);
  // honest label (action unchanged): say WHY grounding failed — mirror of mm/decide.py
  if (g.action === 'escalate' && g.reason_codes.length === 1 && g.reason_codes[0] === 'no_comps' && f.grounding_note) {
    g = { ...g, reason_codes: [f.grounding_note] };
  }
  // tier gate (outside policy): T3 or over_cap (AUTO_PAUSE) promotes pursue -> escalate
  if (g.action === 'pursue' && (it.json.tier === 'T3' || it.json.over_cap)) {
    g = { action: 'escalate', reason_codes: ['tier_t3_or_cap'], human_required: true };
  }
  // daily draft cap (Art XII.3) — drafts beyond the cap escalate instead
  if (g.action === 'pursue' && !f.is_mine) {
    if (sdCap.drafts_today >= DRAFT_CAP) g = { action: 'escalate', reason_codes: ['over_cap'], human_required: true };
    else sdCap.drafts_today += 1;
  }
  it.json.gate = g;
  it.json.action_state = g.action === 'pursue' ? (f.is_mine ? 'pursued_auto' : 'drafted') : (g.action === 'skip' ? 'skipped' : 'escalated');
}
return items;"""

POLICY_TAIL_V1 = r"""for (const it of items) {
  // (cap state lives inside the loop so the parity test's gate-function extraction stays unchanged)
  const sdCap = $getWorkflowStaticData('global');
  const today = new Date().toISOString().slice(0, 10);
  if (sdCap.draft_day !== today) { sdCap.draft_day = today; sdCap.drafts_today = 0; }
  const DRAFT_CAP = Number($env.N8N_MAX_DRAFTS || 3);
  let answers = null;
  try {
    if (it.json.choices && it.json.choices[0] && it.json.choices[0].message) {
      answers = JSON.parse(it.json.choices[0].message.content);
    } else if (it.json.judge_answers) {
      answers = it.json.judge_answers;
    }
  } catch (e) {
    answers = null;
  }
  const f = it.json.facts || {};
  let g = gateV1(answers, f);
  if (g.action === 'escalate' && g.reason_codes.length === 1 && g.reason_codes[0] === 'no_comps' && f.grounding_note) {
    g = { ...g, reason_codes: [f.grounding_note] };
  }
  // tier gate (outside policy): T3 or over_cap promotes pursue -> escalate
  if (g.action === 'pursue' && (it.json.tier === 'T3' || it.json.over_cap)) {
    g = { action: 'escalate', reason_codes: ['tier_t3_or_cap'], human_required: true };
  }
  if (g.action === 'pursue' && !f.is_mine) {
    if (sdCap.drafts_today >= DRAFT_CAP) g = { action: 'escalate', reason_codes: ['over_cap'], human_required: true };
    else sdCap.drafts_today += 1;
  }
  it.json.gate = g;
  it.json.judge_answers = answers;
  it.json.action_state = g.action === 'pursue' ? (f.is_mine ? 'pursued_auto' : 'drafted') : (g.action === 'skip' ? 'skipped' : 'escalated');
}
return items;"""

LEDGER_JS = r"""// Receipt ledger (Art VII.1) — append-only, hash-chained receipts kept in workflow static data
// (persisted for production executions) + visible per item in this n8n execution's log.
// Replaces the Airtable node (no PAT). Content-only: no seller fields are written (Art III).
let crypto = null;
try { crypto = require('crypto'); } catch (e) { crypto = null; }
const h16 = (s) => crypto ? crypto.createHash('sha256').update(s).digest('hex').slice(0, 16)
  : (() => { let h = 0x811c9dc5; for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 0x01000193) >>> 0; } return ('fnv1a-' + h.toString(16)).padStart(16, '0'); })();
const sd = $getWorkflowStaticData('global');
sd.ledger = sd.ledger || [];
let prev = sd.last_hash || 'genesis';
const execId = String($execution.id);
for (const it of items) {
  const f = it.json.facts || {};
  const g = it.json.gate || {};
  const body = {
    receipt_id: `n8n-${execId}-${h16(String(it.json.id) + it.json.ts)}`,
    ts: it.json.ts || new Date().toISOString(),
    n8n_execution_id: execId,
    listing_id: String(it.json.id || ''),
    input_hash: it.json.input_hash,
    actor: 'agent',
    policy_branch: `gate_${g.gate_version || (it.json.judge_answers !== undefined ? 'v1' : 'v0')}:${g.action}`,
    action_state: it.json.action_state,
    reason_codes: g.reason_codes || [],
    tier: it.json.tier,
    margin_z: f.margin_z === null || f.margin_z === undefined ? null : Math.round(f.margin_z * 100) / 100,
    comps_key: f.comps_key || null,
    comps_n: f.comps ? f.comps.n : null,
    comps_basis: f.comps ? f.comps.basis : null,
    action_state_note: it.json.action_state === 'drafted' ? 'drafted != sent (Art VII.2)' : '',
    prev_hash: prev
  };
  body.row_hash = h16(JSON.stringify(body));
  prev = body.row_hash;
  sd.ledger.push(body);
  it.json.receipt = body;
}
sd.last_hash = prev;
if (sd.ledger.length > 500) sd.ledger = sd.ledger.slice(-500);
return items;"""

SUMMARY_JS = r"""// Run summary — ONE Telegram line per execution (no per-item escalation spam; bot shared with Hermes)
const rows = $input.all().map(i => i.json.receipt || {});
const n = (s) => rows.filter(r => r.action_state === s).length;
const refused = rows.filter(r => r.action_state === 'skipped' || r.action_state === 'escalated').slice(0, 3)
  .map(r => `  ${r.action_state === 'skipped' ? 'SKIP' : 'ESC '} ${String(r.listing_id).slice(0, 22)} ${(r.reason_codes || []).join(',')}`);
const text = [
  `n8n · Magpie ${$workflow.name.split(' ')[1] || ''} · execution ${$execution.id}`,
  `scanned ${rows.length} · skipped ${n('skipped')} · escalated ${n('escalated')} · drafted ${n('drafted')} (awaiting you) · auto ${n('pursued_auto')}`,
  `comps: ${String($env.COMPS_SOURCE || 'unconfigured')}`,
  refused.length ? 'refused first:' : 'refused first: (none)',
  ...refused,
  `receipts: ${rows.length} hash-chained · head ${rows.length ? rows[rows.length - 1].row_hash : 'n/a'}`,
  'drafted != sent — a human presses Send (Art VII.2)'
].join('\n');
return [{ json: { text, counts: { skipped: n('skipped'), escalated: n('escalated'), drafted: n('drafted'), pursued_auto: n('pursued_auto') }, execution_id: String($execution.id) } }];"""


def node(name, code, pos, nid):
    return {"parameters": {"jsCode": code}, "id": nid, "name": name, "type": "n8n-nodes-base.code",
            "typeVersion": 2, "position": pos}


def migrate(fname: str) -> None:
    p = N8N / fname
    wf = json.loads(p.read_text())
    nodes, conns = wf["nodes"], wf["connections"]
    by = {n["name"]: n for n in nodes}
    if "Receipt ledger (Art VII.1)" in by:
        print(f"{fname}: already migrated"); return

    price = next(n for n in nodes if n["name"].startswith("price"))
    price["parameters"]["jsCode"] = PRICE_JS
    pol = next(n for n in nodes if n["name"].startswith("POLICY"))
    code = pol["parameters"]["jsCode"]
    head = code.split("for (const it of items)")[0]          # parity-checked gate function stays byte-identical
    pol["parameters"]["jsCode"] = head + (POLICY_TAIL_V0 if "gateV0" in head and "gateV1" not in head else POLICY_TAIL_V1)

    airtable = next(n for n in nodes if n["type"].endswith("airtable"))
    esc = next(n for n in nodes if n["name"].startswith("Telegram — escalation"))
    draft_tg = next(n for n in nodes if n["name"].startswith("Telegram — draft-assist"))
    route = next(n for n in nodes if n["name"].startswith("route by action_state"))
    x, y = airtable["position"]
    ledger = node("Receipt ledger (Art VII.1)", LEDGER_JS, [route["position"][0] - 10, route["position"][1] - 220], "ledger-1")
    summary = node("Run summary (1 line/execution)", SUMMARY_JS, [x, y + 120], "summary-1")
    tg_sum = {"parameters": {"chatId": "={{ $env.TELEGRAM_CHAT_ID }}", "text": "={{ $json.text }}", "additionalFields": {}},
              "id": "summary-tg", "name": "Telegram — run summary", "type": "n8n-nodes-base.telegram",
              "typeVersion": 1.2, "position": [x + 220, y + 120]}
    draft_tg["parameters"]["text"] = (
        "=📝 DRAFT (drafted ≠ sent — you press Send, Art VII.2) · n8n exec {{ $execution.id }}\n"
        "{{ $json.title }}\n"
        "ask €{{ $json.price }} → offer €{{ $json.draft.offer_eur }} ({{ Math.round($json.draft.offer_ratio*100) }}% of ask)\n"
        "comps {{ $json.facts.comps_key }}: median €{{ $json.facts.comps.median }} · MAD €{{ $json.facts.comps.mad }} · "
        "n={{ $json.facts.comps.n }} ({{ $json.facts.comps.basis }})\n"
        "margin_z = ({{ $json.facts.comps.median }} − {{ $json.price }}) / {{ $json.facts.comps.mad }} = "
        "{{ Math.round($json.facts.margin_z*100)/100 }}\n"
        "{{ $json.draft.text_nl }}\nreceipt {{ $json.receipt.row_hash }}")
    wf["nodes"] = [n for n in nodes if n is not airtable and n is not esc] + [ledger, summary, tg_sum]

    # rewire: POLICY -> ledger -> {route, summary}; route[drafted] -> draft Telegram; summary -> Telegram summary
    new = {}
    for src, out in conns.items():
        if src in (airtable["name"], esc["name"], draft_tg["name"], route["name"], pol["name"]):
            continue
        new[src] = out
    new[pol["name"]] = {"main": [[{"node": ledger["name"], "type": "main", "index": 0}]]}
    new[ledger["name"]] = {"main": [[{"node": route["name"], "type": "main", "index": 0},
                                     {"node": summary["name"], "type": "main", "index": 0}]]}
    new[route["name"]] = {"main": [[{"node": draft_tg["name"], "type": "main", "index": 0}], [], []]}
    new[summary["name"]] = {"main": [[{"node": tg_sum["name"], "type": "main", "index": 0}]]}
    # M2 low-health branch used to feed Airtable: give it its own ledger pass
    for src, out in list(new.items()):
        for br in out.get("main", []):
            for c in br:
                if c["node"] == airtable["name"]:
                    c["node"] = ledger["name"]
    wf["connections"] = new
    p.write_text(json.dumps(wf, indent=2, ensure_ascii=False) + "\n")
    print(f"{fname}: migrated ({len(wf['nodes'])} nodes)")


if __name__ == "__main__":
    for f in ("wf-m0-scan-decide.json", "wf-m1-full.json", "wf-m2-event-driven.json"):
        migrate(f)
