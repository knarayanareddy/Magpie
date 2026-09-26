#!/usr/bin/env python3
"""One-time login for the actuator's DEDICATED DEMO account (US-11). Credentials never touch Magpie.

Opens a visible Chromium window on marktplaats.nl with a persistent profile at out/actuator/profile/ (gitignored).
YOU log in by hand in that window (password, 2FA, whatever Marktplaats asks). When the page shows you logged in,
close the window. Magpie only keeps the browser session cookie inside that profile folder.

  python3 tools/actuator_login.py            # log in (first time / expired)
  python3 tools/actuator_login.py --check    # headless: is the saved session still logged in?
  python3 tools/actuator_login.py --forget   # delete the saved session
"""
from __future__ import annotations
import argparse, shutil, sys, time
from pathlib import Path

APP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP))
from mm.actuator.gates import act_dir  # noqa: E402
from mm.actuator.driver import PROFILE  # noqa: E402


def logged_in(page) -> bool:
    page.goto("https://www.marktplaats.nl/my-account/sell/index.html", wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(2500)
    return "inloggen" not in page.url.lower() and "login" not in page.url.lower() and \
        not page.locator("input[type=password]:visible").count()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--forget", action="store_true")
    a = ap.parse_args()
    prof = PROFILE(act_dir())
    if a.forget:
        shutil.rmtree(prof, ignore_errors=True)
        print("saved actuator session deleted")
        return 0
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        if a.check:
            if not prof.exists():
                print("❌ no saved session — run: python3 tools/actuator_login.py")
                return 1
            ctx = p.chromium.launch_persistent_context(str(prof), headless=True, locale="nl-NL")
            ok = logged_in(ctx.pages[0] if ctx.pages else ctx.new_page())
            ctx.close()
            print("✅ actuator session is logged in" if ok else "❌ session expired — run: python3 tools/actuator_login.py")
            return 0 if ok else 1
        prof.mkdir(parents=True, exist_ok=True)
        ctx = p.chromium.launch_persistent_context(str(prof), headless=False, locale="nl-NL",
                                                   viewport={"width": 1280, "height": 900})
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto("https://www.marktplaats.nl/", wait_until="domcontentloaded")
        print("A Chromium window is open. Log in to your DEDICATED DEMO Marktplaats account there.\n"
              "Magpie does not see your password. Close the window when you're logged in.")
        try:
            while ctx.pages:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        try:
            ctx.close()
        except Exception:
            pass
    print("session saved. Verify with: python3 tools/actuator_login.py --check")
    return 0


if __name__ == "__main__":
    sys.exit(main())
