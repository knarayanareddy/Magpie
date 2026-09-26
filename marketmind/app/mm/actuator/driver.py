"""DRIVER (US-11) — Playwright execution of an APPROVED, CLAIMED actuator token. No LLM, no generic navigation.

Design rules
- Only the three allowlisted flows exist below; each is a fixed sequence of role/text locators.
- Host allowlist is re-checked after every navigation; any off-host URL aborts.
- A PAYMENT GUARD scans every page state: if anything that looks like a checkout/payment/paid upsell is visible
  (betalen, iDEAL, Afrekenen, €-priced bump options…) the run STOPS before any click (Art V.3). Marktplaats'
  "Omhoogplaatsen" is a PAID feature, so bump_own_listing only ever uses the free "Verlengen" path and otherwise
  escalates.
- Unknown page (login wall, captcha, changed layout) => stop + screenshot + escalate. Never retries.
- DRY-RUN by default: the flow is executed up to (not including) the final button; ACT_LIVE=1 presses it.
- Artefacts: out/actuator/runs/<run_id>/{NN-step.png, video.webm, trace.json}.
"""
from __future__ import annotations
import json, os, re, time
from pathlib import Path
from urllib.parse import urlparse

from .gates import ALLOWED_HOSTS, Refused, act_dir, receipt

PROFILE = lambda d: d / "profile"                                   # persistent login (gitignored under out/)
PAYMENT_RE = re.compile(r"\b(betalen|betaal\s*nu|afrekenen|ideal|creditcard|paypal|tikkie|bestelling\s+plaatsen|"
                        r"direct\s+kopen|koop\s+nu|checkout|kosten:\s*€)\b", re.I)
LOGIN_RE = re.compile(r"\b(inloggen|log\s*in\s*met|wachtwoord)\b", re.I)
CAPTCHA_RE = re.compile(r"captcha|ik ben geen robot|verify you are human|cloudflare", re.I)


class Stop(Exception):
    def __init__(self, code: str, detail: str = ""):
        super().__init__(code)
        self.code, self.detail = code, detail


class Run:
    def __init__(self, d: Path, token: str, e: dict, live: bool, headed: bool):
        self.d, self.token, self.e, self.live, self.headed = d, token, e, live, headed
        self.id = time.strftime("%Y%m%d-%H%M%S") + "-" + token
        self.dir = d / "runs" / self.id
        self.dir.mkdir(parents=True, exist_ok=True)
        self.steps: list[dict] = []
        self.page = None

    # ---- witness
    def shot(self, name: str) -> None:
        n = len(self.steps) + 1
        path = self.dir / f"{n:02d}-{name}.png"
        try:
            self.page.screenshot(path=str(path))
        except Exception:
            path = None
        self.steps.append({"n": n, "step": name, "url": self._url_safe(), "ts": time.time(),
                           "screenshot": path.name if path else None})

    def _url_safe(self) -> str:
        try:
            u = urlparse(self.page.url)
            return f"{u.scheme}://{u.hostname}{u.path}"[:160]      # no query strings (tokens) in the trace
        except Exception:
            return ""

    # ---- guards (run after every navigation / before every click)
    def guard(self, *, allow_login_text: bool = False) -> None:
        host = urlparse(self.page.url).hostname
        if host not in ALLOWED_HOSTS:
            raise Stop("off_host_navigation", str(host))
        body = self.page.locator("body").inner_text(timeout=5000)[:20000]
        if CAPTCHA_RE.search(body):
            raise Stop("captcha_or_bot_check")
        if self.page.locator("[role=dialog] input[type=password], input[type=password]:visible").count():
            raise Stop("not_logged_in", "login form visible — run tools/actuator_login.py")
        if PAYMENT_RE.search(self._dialog_text()):
            raise Stop("payment_step_visible", "refusing: a payment/checkout step is on screen (Art V.3)")

    def _dialog_text(self) -> str:
        try:
            return " ".join(self.page.locator("[role=dialog]:visible").all_inner_texts())[:5000]
        except Exception:
            return ""

    def goto(self, url: str) -> None:
        self.page.goto(url, wait_until="domcontentloaded", timeout=30000)
        self.page.wait_for_timeout(1500)
        self._dismiss_cookies()
        self.guard()

    def _dismiss_cookies(self) -> None:
        for name in ("Accepteren", "Akkoord", "Alles accepteren"):
            b = self.page.get_by_role("button", name=name)
            if b.count():
                try:
                    b.first.click(timeout=2000)
                    self.page.wait_for_timeout(500)
                except Exception:
                    pass
                return

    def click(self, locator, step: str) -> None:
        if not locator.count():
            raise Stop("element_missing", step)
        self.guard()
        locator.first.click(timeout=8000)
        self.page.wait_for_timeout(1200)
        self.guard()
        self.shot(step)


# ---------------------------------------------------------------- the three flows
def _send_message(r: Run) -> dict:
    r.goto(r.e["url"])
    r.shot("ad-opened")
    r.click(r.page.get_by_role("button", name="Bericht"), "message-composer-opened")
    box = r.page.locator("[role=dialog] textarea, textarea:visible")
    if not box.count():
        raise Stop("composer_not_found")
    box.first.fill(r.e["params"]["text"])
    r.shot("message-typed")
    send = r.page.locator("[role=dialog]").get_by_role("button", name=re.compile(r"^(Verstuur|Versturen|Verzenden|Stuur)", re.I))
    if not send.count():
        raise Stop("send_button_not_found")
    if not r.live:
        return {"final": "dry_run_stopped_before_send"}
    r.click(send, "message-sent")
    return {"final": "sent"}


def _own_ad_menu(r: Run) -> None:
    """Own ad page shows owner controls when logged in as the owner; otherwise this is not our ad."""
    r.goto(r.e["url"])
    r.shot("own-ad-opened")
    if r.page.get_by_role("button", name="Bericht").count() and not r.page.get_by_role(
            "link", name=re.compile(r"Wijzig|Bewerk", re.I)).count():
        raise Stop("not_owner_session", "logged-in account does not own this ad")


def _edit_own_price(r: Run) -> dict:
    _own_ad_menu(r)
    r.click(r.page.get_by_role("link", name=re.compile(r"^(Wijzig|Bewerk)", re.I)), "edit-form-opened")
    price = r.page.get_by_label(re.compile(r"^Prijs|Vraagprijs", re.I))
    if not price.count():
        price = r.page.locator("input[name*=price i]:visible, input[id*=price i]:visible")
    if not price.count():
        raise Stop("price_field_not_found")
    current = price.first.input_value()
    if current and re.sub(r"\D", "", current.split(",")[0]) not in (str(r.e["params"]["old_price_eur"]), ""):
        raise Stop("price_changed_since_request", f"page shows {current}")
    price.first.fill(str(r.e["params"]["new_price_eur"]))
    r.shot("price-typed")
    save = r.page.get_by_role("button", name=re.compile(r"^(Opslaan|Wijzigingen opslaan|Plaats|Bijwerken)", re.I))
    if not save.count():
        raise Stop("save_button_not_found")
    if not r.live:
        return {"final": "dry_run_stopped_before_save"}
    r.click(save, "price-saved")
    return {"final": "saved"}


def _bump_own_listing(r: Run) -> dict:
    _own_ad_menu(r)
    renew = r.page.get_by_role("button", name=re.compile(r"^Verlengen|Gratis verlengen", re.I))
    if not renew.count():
        renew = r.page.get_by_role("link", name=re.compile(r"^Verlengen|Gratis verlengen", re.I))
    if not renew.count():
        # "Omhoogplaatsen" is paid on Marktplaats => never clicked (Art V.3)
        raise Stop("free_renew_unavailable", "only paid 'Omhoogplaatsen' offered — refusing (Art V.3)")
    if not r.live:
        return {"final": "dry_run_stopped_before_renew"}
    r.click(renew, "renewed")
    return {"final": "renewed"}


FLOWS = {"send_message": _send_message, "edit_own_price": _edit_own_price, "bump_own_listing": _bump_own_listing}


def execute(token: str, e: dict, *, live: bool, headed: bool = False, d: Path | None = None) -> dict:
    """Run one claimed token. Always writes a receipt + trace; returns the outcome dict."""
    d = d or act_dir()
    from playwright.sync_api import sync_playwright
    r = Run(d, token, e, live, headed)
    outcome: dict = {"run_id": r.id, "live": live}
    prof = PROFILE(d)
    if not prof.exists():
        outcome.update(status="escalated", code="no_session", detail="run tools/actuator_login.py first")
    else:
        with sync_playwright() as p:
            ctx = p.chromium.launch_persistent_context(
                str(prof), headless=not headed, locale="nl-NL", viewport={"width": 1280, "height": 900},
                record_video_dir=str(r.dir), record_video_size={"width": 1280, "height": 900})
            ctx.set_default_timeout(15000)
            r.page = ctx.pages[0] if ctx.pages else ctx.new_page()
            try:
                res = FLOWS[e["action"]](r)
                outcome.update(status="pursued_auto" if live else "dry_run_ok", **res)
            except Stop as s:
                r.shot(f"stopped-{s.code}")
                outcome.update(status="escalated", code=s.code, detail=s.detail)
            except Exception as ex:                                    # layout drift, timeouts: stop, never retry
                try:
                    r.shot("error")
                except Exception:
                    pass
                outcome.update(status="escalated", code="driver_error", detail=f"{type(ex).__name__}: {str(ex)[:160]}")
            finally:
                ctx.close()
    (r.dir / "trace.json").write_text(json.dumps({"token": token, "action": e["action"], "listing_id": e["listing_id"],
                                                  "digest": e["digest"], "live": live, "steps": r.steps,
                                                  "outcome": outcome}, indent=2))
    videos = sorted(p.name for p in r.dir.glob("*.webm"))
    state = {"pursued_auto": "pursued_auto", "dry_run_ok": "drafted"}.get(outcome["status"], "escalated")
    reasons = [outcome.get("final") or outcome.get("code") or "unknown"] + ([] if live else ["dry_run"])
    receipt(d, e["action"], e["listing_id"], state, reasons, actor="agent",
            scores={"live": live, "digest": e["digest"], "steps": len(r.steps)},
            extra={"run_id": r.id, "video": videos[0] if videos else None})
    outcome["artefacts"] = str(r.dir)
    return outcome
