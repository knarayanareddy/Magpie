#!/usr/bin/env python3
"""Register the DEMO account's own ads from the logged-in actuator session (US-11). Read-only: nothing is saved
on Marktplaats. Ownership proof = the ad is on this session's 'Mijn advertenties' AND its owner edit form opens.

Writes out/own_accounts.json -> "demo": {listing_ids, urls, prices, price_types, registered_at} (gitignored).
The actuator only acts on these ids for own-listing actions. Personal accounts stay read-only (Art XI).

  python3 tools/register_demo_ads.py
"""
from __future__ import annotations
import json, re, sys, time
from pathlib import Path

APP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP))
from mm.actuator.driver import LAUNCH_ARGS, PROFILE, edit_url, euros, price_field  # noqa: E402
from mm.actuator.gates import act_dir  # noqa: E402

OWN = APP / "out" / "own_accounts.json"


def main() -> int:
    prof = PROFILE(act_dir())
    if not prof.exists():
        print("❌ no actuator session — run: python3 tools/actuator_login.py")
        return 1
    from playwright.sync_api import sync_playwright
    found: dict[str, dict] = {}
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(str(prof), headless=True, locale="nl-NL", **LAUNCH_ARGS)
        pg = ctx.pages[0] if ctx.pages else ctx.new_page()
        pg.goto("https://www.marktplaats.nl/my-account/sell/index.html", wait_until="domcontentloaded", timeout=30000)
        pg.wait_for_timeout(3000)
        if pg.locator("input[type=password]:visible").count() or "login" in pg.url.lower():
            print("❌ session expired — run: python3 tools/actuator_login.py")
            ctx.close()
            return 1
        hrefs = pg.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
        for h in hrefs:
            m = re.match(r"https://www\.marktplaats\.nl(/v/[a-z0-9\-]+/[a-z0-9\-]+/(m\d{9,11})[a-z0-9\-]*)", h)
            if m:
                found.setdefault(m.group(2), {"url": "https://www.marktplaats.nl" + m.group(1)})
        for lid, info in found.items():
            pg.goto(edit_url(lid), wait_until="domcontentloaded", timeout=30000)
            pg.wait_for_timeout(2500)
            if f"/plaats/{lid}/edit" not in pg.url or not pg.get_by_role("button", name="Opslaan").count():
                info["owner_edit"] = False
                continue
            f = price_field(pg)
            pt = pg.locator("#Dropdown-prijstype")
            info.update(owner_edit=True, price_eur=euros(f.first.input_value()) if f.count() else None,
                        price_type=pt.first.input_value() if pt.count() else None,
                        title=(pg.locator("input[name='title'], #title").first.input_value()[:80]
                               if pg.locator("input[name='title'], #title").count() else ""))
        ctx.close()
    own = json.loads(OWN.read_text()) if OWN.exists() else {"seller_ids": [], "listing_ids": [], "accounts": {}}
    ok = {k: v for k, v in found.items() if v.get("owner_edit")}
    own["demo"] = {"listing_ids": sorted(ok), "urls": {k: v["url"] for k, v in ok.items()},
                   "prices": {k: v.get("price_eur") for k, v in ok.items()},
                   "price_types": {k: v.get("price_type") for k, v in ok.items()},
                   "titles": {k: v.get("title") for k, v in ok.items()},
                   "registered_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    OWN.write_text(json.dumps(own, indent=2, ensure_ascii=False))
    print(f"demo account: {len(ok)} own ad(s) registered (ownership verified via owner edit form)")
    for k, v in ok.items():
        print(f"  {k}  €{v.get('price_eur')} [{v.get('price_type')}]  {v.get('title', '')[:60]}")
    skipped = [k for k, v in found.items() if not v.get("owner_edit")]
    if skipped:
        print(f"  ⚠ not editable by this session (skipped): {skipped}")
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())
