#!/usr/bin/env python3
"""ACT CLI (US-11) — request → human approve → execute one allowlisted Marktplaats action on the demo account.

  python3 act.py status                                   # session, budget, pending approvals, last runs
  python3 act.py request bump   <m-number>                # own ad (from out/own_accounts.json)
  python3 act.py request price  <m-number> <new_eur>      # own ad, downward reprice only
  python3 act.py request message <draft_id>               # buy side: send a Magpie draft to that listing's seller
  python3 act.py approve <token>                          # the HUMAN step (actor=human receipt)
  python3 act.py run <token> [--live] [--headed]          # dry-run unless --live AND ACT_LIVE=1
  python3 act.py fallback <token>                         # draft-assist: open the ad + copy text; human presses Send

Nothing here can pay, bid, buy or post an ad (Art V.3, ToS art. 4).
"""
from __future__ import annotations
import argparse, json, os, subprocess, sys, time
from pathlib import Path

APP = Path(__file__).resolve().parent
sys.path.insert(0, str(APP))
from mm.actuator import gates  # noqa: E402

OUT = APP / "out"


def context() -> dict:
    own = json.loads((OUT / "own_accounts.json").read_text()) if (OUT / "own_accounts.json").exists() else {}
    drafted = {}
    for u in (OUT / "drafts").glob("*.url") if (OUT / "drafts").exists() else []:
        drafted[u.stem] = u.read_text().strip()
    return {"own_listing_ids": set(own.get("listing_ids", [])), "own_urls": own.get("urls", {}),
            "drafted": drafted, "drafted_listing_urls": set(drafted.values()),
            "feed_urls": set(drafted.values()) | set(own.get("urls", {}).values()),
            "state_path": OUT / "state.json"}


def cmd_request(a) -> int:
    ctx = context()
    if a.kind in ("bump", "price"):
        url = ctx["own_urls"].get(a.ref)
        if not url:
            print(f"❌ {a.ref} is not a registered own ad with a known URL (run tools/import_own_ads.py)")
            return 2
        action = "bump_own_listing" if a.kind == "bump" else "edit_own_price"
        params = {}
        if a.kind == "price":
            st = json.loads((OUT / "sell" / "state.json").read_text()) if (OUT / "sell" / "state.json").exists() else {"items": {}}
            item = next((i for i in st["items"].values() if (i.get("posted") or {}).get("ref") == a.ref), None)
            old = (item or {}).get("posted", {}).get("listed_price_eur")
            if not old:
                print(f"❌ no listed price known for {a.ref} (Bieden ads have none) — can't reprice safely")
                return 2
            params = {"old_price_eur": int(old), "new_price_eur": int(a.value)}
    else:
        url = ctx["drafted"].get(a.ref)
        txt = OUT / "drafts" / f"{a.ref}.txt"
        if not url or not txt.exists():
            print(f"❌ draft {a.ref} has no feed URL on record (only drafts made after US-11 carry one)")
            return 2
        action, params = "send_message", {"text": txt.read_text().strip()}
    try:
        res = gates.request(action, url, params, context=ctx)
    except gates.Refused as e:
        print(f"⛔ refused: {e.code} {e.detail}")
        return 3
    print(f"request ready: {res['summary']}\n  approve (human): python3 act.py approve {res['token']}"
          f"   · expires in {res['expires_in_s'] // 60} min")
    return 0


def cmd_approve(a) -> int:
    token = a.token
    if token == "oldest":                                   # phone one-tap: the oldest un-approved live request
        t = gates._load_tokens(gates.act_dir())
        pend = sorted(((v["created"], k) for k, v in t.items()
                       if not v.get("used") and not v.get("approved_at") and v["expires"] > time.time()))
        if not pend:
            print("nothing awaiting approval")
            return 0
        token = pend[0][1]
    try:
        e = gates.approve(token)
    except gates.Refused as ex:
        print(f"⛔ {ex.code}")
        return 3
    print(f"✅ approved by human: {e['action']} on {e['listing_id']}\n  run: python3 act.py run {token}"
          f"   (dry-run)  ·  add --live with ACT_LIVE=1 to press the final button")
    return 0


def cmd_run(a) -> int:
    live = bool(a.live and os.environ.get("ACT_LIVE") == "1")
    if a.live and not live:
        print("ℹ --live ignored: ACT_LIVE=1 is not set → dry-run")
    try:
        e = gates.claim(a.token, live=live, state_path=OUT / "state.json")
    except gates.Refused as ex:
        print(f"⛔ {ex.code} {ex.detail}")
        return 3
    from mm.actuator import driver
    out = driver.execute(a.token, e, live=live, headed=a.headed)
    icon = {"pursued_auto": "✅", "dry_run_ok": "🧪"}.get(out["status"], "⚠")
    print(f"{icon} {e['action']} {e['listing_id']}: {out['status']} "
          f"{out.get('final') or out.get('code', '')} {out.get('detail', '')}\n  witness: {out['artefacts']}")
    if out["status"] == "escalated":
        print(f"  fallback (draft-assist): python3 act.py fallback {a.token}")
    return 0 if out["status"] in ("pursued_auto", "dry_run_ok") else 4


def cmd_fallback(a) -> int:
    t = gates._load_tokens(gates.act_dir())
    e = t.get(a.token)
    if not e or not e.get("approved_at"):
        print("⛔ fallback needs a human-approved token")
        return 3
    gates.ad_id(e["url"])                                                  # still allowlisted target only
    text = e["params"].get("text") or {"edit_own_price": f"Nieuwe prijs: €{e['params'].get('new_price_eur')}",
                                        "bump_own_listing": "Verlengen (gratis) in Mijn Advertenties"}[e["action"]]
    subprocess.run(["pbcopy"], input=text.encode(), check=False)
    subprocess.run(["open", e["url"]], check=False)
    gates.receipt(gates.act_dir(), e["action"], e["listing_id"], "pursued_assisted", ["draft_assist_fallback"],
                  actor="human", scores={"digest": e["digest"], "live": False})
    print(f"📋 draft-assist: text copied to clipboard, ad opened in your browser — you press Send/Save.")
    return 0


def cmd_status(a) -> int:
    d = gates.act_dir()
    prof = d / "profile"
    ok, msg = gates.rc.verify_chain(d / "receipts.jsonl") if (d / "receipts.jsonl").exists() else (True, "no receipts yet")
    t = gates._load_tokens(d)
    pend = [f"{k} {v['action']} {v['listing_id']} ({'approved' if v.get('approved_at') else 'awaiting approve'}, "
            f"{int((v['expires'] - time.time()) / 60)} min left)" for k, v in t.items()
            if not v.get("used") and v["expires"] > time.time()]
    runs = sorted((d / "runs").glob("*"))[-3:]
    print(f"actuator · session: {'saved' if prof.exists() else 'NONE (python3 tools/actuator_login.py)'} · "
          f"live budget today {gates.budget_used_today(d)}/{os.environ.get('ACT_MAX_PER_DAY', '5')} · "
          f"kill switch {'ON' if gates.kill_switch_on(OUT / 'state.json') else 'off'} · chain: {msg}")
    print("pending: " + ("; ".join(pend) if pend else "none"))
    for r in runs:
        tr = json.loads((r / "trace.json").read_text()) if (r / "trace.json").exists() else {}
        o = tr.get("outcome", {})
        print(f"  run {r.name}: {tr.get('action')} {tr.get('listing_id')} → {o.get('status')} {o.get('final') or o.get('code', '')}")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest="cmd", required=True)
    sp.add_parser("status")
    r = sp.add_parser("request")
    r.add_argument("kind", choices=["bump", "price", "message"])
    r.add_argument("ref")
    r.add_argument("value", nargs="?")
    for name in ("approve", "fallback"):
        sp.add_parser(name).add_argument("token")
    rn = sp.add_parser("run")
    rn.add_argument("token")
    rn.add_argument("--live", action="store_true")
    rn.add_argument("--headed", action="store_true")
    a = ap.parse_args()
    if a.cmd == "request" and a.kind == "price" and not a.value:
        ap.error("price needs <new_eur>")
    return {"status": cmd_status, "request": cmd_request, "approve": cmd_approve, "run": cmd_run,
            "fallback": cmd_fallback}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
