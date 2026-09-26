#!/usr/bin/env python3
"""Execute the n8n Code nodes of a workflow JSON locally in Node with a stubbed n8n runtime
($env/$vars, $getWorkflowStaticData, $execution, $workflow, $input, require). Runs the node chain
fan-out -> dedupe -> price -> POLICY -> ledger -> summary on real items and checks agreement with Python.
Usage: python3 test_n8n_nodes.py [items.json]   (defaults to a synthetic set if no file given)"""
from __future__ import annotations
import json, os, subprocess, sys
from pathlib import Path

APP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP))
from mm import decide  # noqa: E402

WF = APP / "n8n" / "wf-m0-scan-decide.json"


def code_of(wf, prefix):
    return next(n for n in wf["nodes"] if n["name"].startswith(prefix))["parameters"]["jsCode"]


def run_chain(items, comps, env_extra=None):
    wf = json.loads(WF.read_text())
    env = {"COMPS_JSON": json.dumps({k: [v["median"], v["mad"], v.get("n", 0)] for k, v in comps.items()}),
           "COMPS_SOURCE": "test", "AUTO_PAUSE": "0", "N8N_MAX_DRAFTS": "3", **(env_extra or {})}
    stages = [code_of(wf, "seen-ids"), code_of(wf, "price"), code_of(wf, "POLICY"), code_of(wf, "Receipt ledger")]
    summary = code_of(wf, "Run summary")
    js = f"""
const $env = {json.dumps(env)};
const __sd = {{}};
function $getWorkflowStaticData(k) {{ return (__sd[k] = __sd[k] || {{}}); }}
const $execution = {{ id: 'local-1' }};
const $workflow = {{ name: 'MarketMind M0 — local' }};
let items = {json.dumps([{"json": it} for it in items])};
""" + "".join(f"\nitems = (function(items){{ {s} }})(items);" for s in stages) + f"""
const $input = {{ all: () => items }};
const summary = (function(){{ {summary} }})();
console.log(JSON.stringify({{ items: items.map(i => i.json), summary: summary[0].json, sd: __sd }}));
"""
    out = subprocess.run(["node", "-e", js], capture_output=True, text=True, timeout=60)
    if out.returncode:
        raise RuntimeError(out.stderr)
    return json.loads(out.stdout.strip().splitlines()[-1])


def main() -> int:
    fails = []
    comps = {"iphone": {"median": 450.0, "mad": 50.0, "n": 11}, "nintendo switch": {"median": 190.0, "mad": 21.0, "n": 14}}
    src = sys.argv[1] if len(sys.argv) > 1 else None
    if src:
        raw = json.loads(Path(src).read_text())
        items = [{"listingId": r.get("listingId"), "url": r.get("url"), "title": r.get("title"),
                  "description": r.get("description", ""), "price": r.get("price")} for r in raw]
        cache = APP / "out" / "comps_cache.json"
        if cache.exists():
            comps = json.loads(cache.read_text())
    else:
        items = [
            {"listingId": "m1", "title": "Nintendo Switch V2 met Mario Kart", "price": 150},
            {"listingId": "m2", "title": "iPhone Achterkant Back glas vervangen", "price": 55},
            {"listingId": "m3", "title": "iPhone 14 128GB", "price": 0},
            {"listingId": "m4", "title": "Nintendo Switch", "description": "betaal vooraf via tikkie", "price": 120},
            {"listingId": "m5", "title": "Obscure tin toy", "price": 20},
            {"listingId": "m6", "title": "Nintendo Switch Lite Geel", "price": 109},
            {"listingId": "m7", "title": "SP Case voor iPhone 14 - Topstaat", "price": 24},
            {"listingId": "m8", "title": "Iphone 11 128GB", "price": 150},
            {"listingId": "m1", "title": "Nintendo Switch V2 met Mario Kart", "price": 150},  # dup id
        ]
    res = run_chain(items, comps)
    got = {r["id"]: (r["action_state"], r["gate"]["reason_codes"]) for r in res["items"]}
    mism = 0
    for it in items:
        iid = it.get("listingId")
        if iid not in got:
            continue
        py_item = {"id": iid, "title": it["title"], "description": it.get("description", ""),
                   "price_eur": float(it.get("price") or 0)}
        d = decide.decide(py_item, decide.facts_for(py_item, comps))
        n8n_action = {"drafted": "pursue", "pursued_auto": "pursue", "escalated": "escalate", "skipped": "skip"}[got[iid][0]]
        cap_or_tier = got[iid][1] in (["over_cap"], ["tier_t3_or_cap"])
        ok = (n8n_action == d.action and got[iid][1] == d.reasons) or (cap_or_tier and d.action == "pursue")
        mism += not ok
        print(f"{'✓' if ok else '✗'} {iid:12} py={d.action}:{d.reasons}  n8n={got[iid][0]}:{got[iid][1]}  | {it['title'][:40]}")
    if mism:
        fails.append(f"{mism} python/n8n decision mismatches")
    rec = [r["receipt"] for r in res["items"]]
    chain_ok = all(rec[i]["prev_hash"] == (rec[i - 1]["row_hash"] if i else "genesis") for i in range(len(rec)))
    print(f"{'✓' if chain_ok else '✗'} n8n ledger hash chain links ({len(rec)} receipts)")
    if not chain_ok:
        fails.append("ledger chain")
    seller_leak = any(k in json.dumps(rec) for k in ("sellerName", "sellerId"))
    print(f"{'✓' if not seller_leak else '✗'} receipts carry no seller fields (Art III)")
    if seller_leak:
        fails.append("seller leak")
    if not src:
        dedup_ok = len(res["items"]) == 8
        print(f"{'✓' if dedup_ok else '✗'} seen-ids dedupe drops repeated listingId")
        if not dedup_ok:
            fails.append("dedupe")
    print("summary:\n" + res["summary"]["text"])
    print(f"\nN8N NODE TESTS: {'PASS' if not fails else 'FAIL ' + str(fails)}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
