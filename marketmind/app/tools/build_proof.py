#!/usr/bin/env python3
"""Build marketmind/proof/ — a redacted, judge-inspectable evidence pack from live run artefacts.

Sources (gitignored runtime files): app/out/receipts.jsonl, comps_cache.json, state.json,
telegram_log.jsonl, n8n_exec_*.json + the Apify API (run ids, metadata only).
Redaction (Art III / audit C4): receipts are content-only already (no seller fields); listing ids are
kept (public Marktplaats ids), titles/descriptions/URLs/images/seller data are NOT exported. No tokens.
Re-run any time:  python3 marketmind/app/tools/build_proof.py
"""
from __future__ import annotations
import collections, glob, hashlib, json, os, sys, time, urllib.request
from pathlib import Path

APP = Path(__file__).resolve().parents[1]
MM = APP.parent
OUT, PROOF = APP / "out", MM / "proof"
sys.path.insert(0, str(APP))
from mm import receipts as rc  # noqa: E402

SELLER_KEYS = ("seller", "sellerName", "sellerId", "sellerType", "location", "url", "images", "description", "title")


def env() -> dict:
    e = {}
    for l in (APP / ".env").read_text().splitlines():
        if "=" in l and not l.lstrip().startswith("#"):
            k, v = l.split("=", 1); e[k.strip()] = v.strip()
    return e


def apify_runs(token: str, actor: str, since: str, limit: int = 1000) -> list[dict]:
    url = f"https://api.apify.com/v2/acts/{actor.replace('/', '~')}/runs?desc=1&limit={limit}"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    items = json.load(urllib.request.urlopen(req, timeout=30))["data"]["items"]
    return [{"run_id": r["id"], "status": r["status"], "started": r["startedAt"], "finished": r.get("finishedAt"),
             "dataset_id": r["defaultDatasetId"]} for r in items if r["startedAt"] >= since]


def main() -> int:
    PROOF.mkdir(exist_ok=True)
    e = env()
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    # 1. receipts: chain check on the FULL log, then export redacted copy
    ok, msg = rc.verify_chain(OUT / "receipts.jsonl")
    rows = [json.loads(l) for l in (OUT / "receipts.jsonl").read_text().splitlines() if l.strip()]
    leaks = [k for r in rows for k in SELLER_KEYS if k in r]
    red = [{k: r.get(k) for k in ("receipt_id", "ts", "listing_id", "input_hash", "actor", "hostile", "policy_branch",
                                  "action_state", "tier", "reason_codes", "scores", "action_state_note",
                                  "prev_hash", "row_hash") if k in r} for r in rows]
    (PROOF / "receipts.redacted.jsonl").write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in red) + "\n")
    live = [r for r in rows if not str(r.get("listing_id", "")).startswith("mm-")]
    states = collections.Counter(r["action_state"] for r in live)
    reasons = collections.Counter(",".join(r["reason_codes"]) for r in live)
    hostile_pursue = sum(1 for r in rows if r.get("hostile") and r["action_state"] in ("drafted", "pursued_auto"))

    # 2. comps provenance
    comps = json.loads((OUT / "comps_cache.json").read_text())
    comps_ts = time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime((OUT / "comps_cache.json").stat().st_mtime))
    (PROOF / "comps_provenance.json").write_text(json.dumps(
        {"fetched_at": comps_ts,
         "basis": sorted({v.get("basis", "asking") for v in comps.values()}),
         "basis_note": "sold = eBay.de completed sales 30d used (defects/successor models excluded); asking = fallback",
         "method": "median + MAD over accessory-filtered results (mm/rerank.py); margin_z=(median-ask)/MAD",
         "families": comps}, indent=2))

    # 3. Apify run ids (metadata only)
    first_ts = live[0]["ts"][:10] + "T00:00:00Z" if live else now
    runs = {}
    for key in ("APIFY_ACTOR_LISTINGS", "APIFY_ACTOR_COMPS"):
        try:
            runs[e[key]] = apify_runs(e["APFY_TOKEN"], e[key], first_ts)
        except Exception as ex:  # honest gap, not a fake
            runs[e.get(key, key)] = f"unavailable: {type(ex).__name__}"
    (PROOF / "apify_runs.json").write_text(json.dumps(runs, indent=1))

    # 4. n8n executions (redacted: per-node counts + ledger receipts + telegram message ids)
    n8n = []
    for f in sorted(glob.glob(str(OUT / "n8n_exec_*.json"))):
        x = json.loads(Path(f).read_text())
        rd = x["data"]["resultData"]["runData"]
        ledger = [i["json"]["receipt"] for i in rd.get("Receipt ledger (Art VII.1)", [{}])[0].get("data", {}).get("main", [[]])[0]]
        tg = [i["json"].get("result", {}).get("message_id") for n, runs_ in rd.items() if n.startswith("Telegram")
              for i in runs_[0]["data"]["main"][0]]
        chain = all(ledger[i]["prev_hash"] == (ledger[i - 1]["row_hash"] if i else ledger[0]["prev_hash"])
                    for i in range(len(ledger)))
        n8n.append({"execution_id": x["id"], "workflow_id": x["workflowId"], "mode": x["mode"], "status": x["status"],
                    "started": x["startedAt"], "stopped": x["stoppedAt"],
                    "nodes": {n: sum(len(b or []) for b in (r[-1].get("data", {}).get("main") or [])) for n, r in rd.items()},
                    "counts": dict(collections.Counter(r["action_state"] for r in ledger)),
                    "reasons": dict(collections.Counter(",".join(r["reason_codes"]) for r in ledger)),
                    "ledger_chain_links": chain, "ledger_head": ledger[-1]["row_hash"] if ledger else None,
                    "telegram_message_ids": tg, "receipts": ledger})
    (PROOF / "n8n_executions.json").write_text(json.dumps(n8n, indent=1, ensure_ascii=False))

    # 5. Telegram message ids from the Python loop
    tlog = OUT / "telegram_log.jsonl"
    tmsgs = [json.loads(l) for l in tlog.read_text().splitlines() if l.strip()] if tlog.exists() else []
    (PROOF / "telegram_messages.json").write_text(json.dumps(tmsgs, indent=1, ensure_ascii=False))

    st = json.loads((OUT / "state.json").read_text())
    hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()[:16] for p in sorted(PROOF.glob("*.json*"))}
    summary = {
        "built_at": now, "receipts_total": len(rows), "receipts_live": len(live),
        "live_window": [live[0]["ts"], live[-1]["ts"]] if live else None,
        "chain": msg, "chain_ok": ok, "chain_head": rows[-1]["row_hash"] if rows else None,
        "hostile_to_pursue": hostile_pursue, "seller_fields_in_receipts": len(leaks),
        "live_action_states": dict(states), "live_reasons_top": dict(reasons.most_common(10)),
        "dhash_index_size": len(st.get("phash", {})), "seen_ids": len(st.get("seen", {})),
        "apify_runs": {k: (len(v) if isinstance(v, list) else v) for k, v in runs.items()},
        "n8n_executions": [{k: x[k] for k in ("execution_id", "status", "mode", "started", "counts",
                                              "ledger_chain_links", "telegram_message_ids")} for x in n8n],
        "telegram_python_messages": len(tmsgs), "file_sha256_16": hashes,
    }
    (PROOF / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False))
    print(json.dumps({k: summary[k] for k in ("receipts_live", "chain", "hostile_to_pursue", "seller_fields_in_receipts",
                                               "apify_runs", "n8n_executions", "telegram_python_messages")}, indent=1))
    return 0 if ok and not leaks and hostile_pursue == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
