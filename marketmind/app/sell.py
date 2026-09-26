#!/usr/bin/env python3
"""Magpie SELL side (US-9) — photo dump → priced listing drafts + negotiation co-pilot. You approve with one tap.

  python3 sell.py intake <folder>                         # sanitize (EXIF/GPS stripped) + group + vision proposal
  python3 sell.py status                                  # pipeline + pending approvals (+ writes out/sell/sell_board.html)
  python3 sell.py confirm s001 --model "iPhone 14 128GB" [--condition used] [--defect "kras op scherm"] [--acc "doos"]
  python3 sell.py price   s001 --ask 300 --floor 250      # human override / way out of no_comps
  python3 sell.py draft   s001                            # Dutch listing draft (confirmed facts only)
  python3 sell.py posted  s001 --ref https://www.marktplaats.nl/v/...   # you posted it (actor=human)
  python3 sell.py msg     s001 "Wil je 200 euro?"         # paste a buyer message → classified + reply drafted
  python3 sell.py approve [msg003]                        # one tap: approve the oldest (or given) drafted reply
  python3 sell.py close   s001 --sold 260 | --withdrawn
  python3 sell.py verify                                  # hash-chain check of out/sell/receipts.jsonl

Isolated from the buy-side loop: own state/receipts under out/sell/. Magpie never posts and never sends —
it drafts; you paste/send in Marktplaats (drafted ≠ posted ≠ sent, Art VII.2). No payments, ever (Art V.3).
"""
from __future__ import annotations
import argparse, json, os, sys
from pathlib import Path

APP = Path(__file__).resolve().parent
sys.path.insert(0, str(APP))
env_file = APP / ".env"
if env_file.exists():
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

from mm import receipts as rc  # noqa: E402
from mm.report import FOOTER  # noqa: E402
from mm.sell import board, service  # noqa: E402
from mm.sell.store import SellState, locked, sell_dir  # noqa: E402


def _status_text(d: Path, short: bool = False) -> str:
    st = SellState(d)
    items = sorted(st.data["items"].values(), key=lambda x: x["id"])
    counts: dict[str, int] = {}
    for it in items:
        counts[it["status"]] = counts.get(it["status"], 0) + 1
    lines = [f"Magpie sell · {len(items)} items · " + (" · ".join(f"{k} {v}" for k, v in sorted(counts.items())) or "empty")]
    for it in items[: (8 if short else 100)]:
        f, pr = it.get("facts") or {}, it.get("price") or {}
        name = f.get("model") or f"? {it['proposal']['brand']} {it['proposal']['model']}"
        money = f" ask €{pr['ask']} floor €{pr['floor']}" if pr.get("status") == "ok" else ""
        lines.append(f"  {it['id']} {it['status']:18} {name[:34]}{money}")
    pend = service.pending(d)
    lines.append(f"pending approvals: {len(pend)}" + (f" · oldest {pend[0][1]['id']} ({pend[0][0]}): "
                                                      f"{(pend[0][1]['reply_nl'] or '')[:90]}" if pend else ""))
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="sell.py", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=None, help=argparse.SUPPRESS)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("intake"); s.add_argument("folder")
    s = sub.add_parser("status"); s.add_argument("--short", action="store_true")
    s = sub.add_parser("confirm"); s.add_argument("item"); s.add_argument("--model", required=True)
    s.add_argument("--brand"); s.add_argument("--condition"); s.add_argument("--category"); s.add_argument("--query")
    s.add_argument("--defect", action="append"); s.add_argument("--acc", action="append")
    s.add_argument("--no-defects", action="store_true"); s.add_argument("--clear-privacy", action="store_true")
    s = sub.add_parser("price"); s.add_argument("item"); s.add_argument("--ask", type=int, required=True); s.add_argument("--floor", type=int, required=True)
    s = sub.add_parser("draft"); s.add_argument("item")
    s = sub.add_parser("posted"); s.add_argument("item"); s.add_argument("--ref", default="")
    s = sub.add_parser("msg"); s.add_argument("item"); s.add_argument("text")
    s = sub.add_parser("approve"); s.add_argument("message", nargs="?")
    s = sub.add_parser("close"); s.add_argument("item"); g = s.add_mutually_exclusive_group(required=True)
    g.add_argument("--sold", type=int); g.add_argument("--withdrawn", action="store_true")
    sub.add_parser("verify")
    a = ap.parse_args(argv)
    d = sell_dir(a.out)
    try:
        with locked(d):
            if a.cmd == "intake":
                items = service.run_intake(Path(a.folder).expanduser(), d)
                print(f"intake: {len(items)} new item(s) from {a.folder} (EXIF/GPS stripped, originals untouched)")
                for it in items:
                    p = it["proposal"]
                    print(f"  {it['id']} {it['status']:18} photos={len(it['photos'])} proposal: {p['brand']} {p['model']} "
                          f"(certain={p['model_certain']}, vision={p['vision']}) → confirm with the exact model")
            elif a.cmd == "status":
                print(_status_text(d, a.short))
            elif a.cmd == "confirm":
                it = service.confirm(a.item, d, model=a.model, brand=a.brand, condition=a.condition, category=a.category,
                                     query=a.query, defects=[] if a.no_defects else a.defect, accessories=a.acc,
                                     clear_privacy=a.clear_privacy)
                pr = it["price"]
                hints = it["facts"]["vision_hints"]
                if (hints["defects"] or hints["accessories"]) and not (a.defect or a.acc):
                    print(f"  vision hints (NOT in the listing unless you confirm them): defects={hints['defects']} "
                          f"accessories={hints['accessories']} → re-run confirm with --defect/--acc to include")
                if pr["status"] == "ok":
                    print(f"{a.item} priced from {pr['n']} eBay.de sold comps (30d, used): ask €{pr['ask']} · floor €{pr['floor']} "
                          f"· median €{pr['median']} · P40–P60 €{pr['p40']}–€{pr['p60']} → next: sell.py draft {a.item}")
                else:
                    print(f"{a.item} {pr['status']} ({pr.get('reason')}) — set it yourself: sell.py price {a.item} --ask N --floor N")
            elif a.cmd == "price":
                it = service.set_price(a.item, d, ask=a.ask, floor=a.floor)
                print(f"{a.item} priced by you: ask €{a.ask} · floor €{a.floor} → next: sell.py draft {a.item}")
            elif a.cmd == "draft":
                it = service.draft(a.item, d)
                dr = it["draft"]
                print(f"=== DRAFT {a.item} (drafted ≠ posted — paste into Marktplaats) ===\nTitel: {dr['title']}\n"
                      f"Categorie: {dr['category']}\nPrijs: €{dr['ask_eur']}\n\n{dr['description']}\n\n"
                      f"Foto's: " + ", ".join(str(d / 'photos' / p) for p in dr["photos"]))
            elif a.cmd == "posted":
                service.mark_posted(a.item, d, url_or_ref=a.ref)
                print(f"{a.item} marked posted (actor=human). Paste buyer messages with: sell.py msg {a.item} \"…\"")
            elif a.cmd == "msg":
                m = service.message(a.item, d, a.text)
                if m["action"] == "draft":
                    print(f"{m['id']} {m['label']} → DRAFT reply (approve with: sell.py approve {m['id']}):\n  {m['reply_nl']}")
                else:
                    print(f"{m['id']} {m['label']} → {m['action'].upper()} {','.join(m['reasons'])}"
                          + (f" · {m['note']}" if m.get("note") else "") + " — no reply drafted")
            elif a.cmd == "approve":
                iid, m = service.approve(d, a.message)
                print(f"✅ approved {m['id']} ({iid}) — now send it in the Marktplaats chat (approved ≠ sent):\n{m['reply_nl']}")
            elif a.cmd == "close":
                service.close(a.item, d, outcome="sold" if a.sold is not None else "withdrawn", price_eur=a.sold)
                print(f"{a.item} closed: {'sold €' + str(a.sold) if a.sold is not None else 'withdrawn'}")
            elif a.cmd == "verify":
                p = d / "receipts.jsonl"
                ok, msg = rc.verify_chain(p) if p.exists() else (True, "no receipts yet")
                print(f"sell receipts: {msg}")
                return 0 if ok else 1
            board.write(d, SellState(d).data, FOOTER)
    except (KeyError, ValueError, PermissionError, FileNotFoundError) as e:
        print(f"❌ {e.args[0] if e.args else e}")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
