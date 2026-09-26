"""TRIAGE — visual inspection grid for escalated and reviewed listings (Darko improvement #2).
Generates app/out/triage.html for glanceable human-in-the-loop review.
Strictly adheres to Art XIII & design.md lockfile: Paper #F3EFE7, Ink #1C1915, Rule #C9C2B4, Brick #8C3A2B.
Radius 2px. No gradients. No emoji icons. Honest affordances (directs to CLI --confirm)."""
from __future__ import annotations
import html, json
from pathlib import Path

CARD_CSS = """
* { box-sizing: border-box; }
body {
  font-family: "IBM Plex Sans", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  background: #F3EFE7;
  color: #1C1915;
  margin: 0;
  padding: 24px;
}
header {
  border-bottom: 2px solid #C9C2B4;
  padding-bottom: 12px;
  margin-bottom: 24px;
  display: flex;
  justify-content: space-between;
  align-items: baseline;
}
h1 {
  font-size: 1.25rem;
  margin: 0;
  font-weight: 700;
  letter-spacing: -0.01em;
  color: #1C1915;
  text-transform: uppercase;
}
.stats {
  font-family: "IBM Plex Mono", "Courier New", monospace;
  font-size: 0.85rem;
  color: #55514B;
}
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 16px;
}
.card {
  background: #FFFFFF;
  border: 1px solid #C9C2B4;
  border-radius: 2px;
  display: flex;
  flex-direction: column;
}
.card img {
  width: 100%;
  height: 180px;
  object-fit: cover;
  background: #E8E3DA;
  border-bottom: 1px solid #C9C2B4;
}
.no-photo {
  width: 100%;
  height: 180px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #E8E3DA;
  color: #7A756D;
  font-family: "IBM Plex Mono", monospace;
  font-size: 0.8rem;
  border-bottom: 1px solid #C9C2B4;
}
.body {
  padding: 14px;
  display: flex;
  flex-direction: column;
  flex: 1;
  gap: 8px;
}
.price-row {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
}
.price {
  font-family: "IBM Plex Mono", monospace;
  font-size: 1.15rem;
  font-weight: 700;
  color: #1C1915;
}
.health-badge {
  font-family: "IBM Plex Mono", monospace;
  font-size: 0.75rem;
  padding: 2px 6px;
  border: 1px solid #C9C2B4;
  border-radius: 2px;
  background: #F3EFE7;
  color: #55514B;
}
.title {
  font-size: 0.95rem;
  font-weight: 600;
  line-height: 1.3;
}
.meta {
  font-family: "IBM Plex Mono", monospace;
  font-size: 0.78rem;
  color: #55514B;
  line-height: 1.4;
}
.status-tag {
  display: inline-block;
  padding: 2px 5px;
  font-weight: 700;
  font-size: 0.72rem;
  border-radius: 2px;
  text-transform: uppercase;
  font-family: "IBM Plex Mono", monospace;
}
.status-drafted {
  border: 1px solid #1C1915;
  color: #1C1915;
  background: #E8E3DA;
}
.status-escalated {
  border: 1px solid #8C3A2B;
  color: #8C3A2B;
  background: #F9EBE8;
}
.badges {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}
.badge {
  font-family: "IBM Plex Mono", monospace;
  font-size: 0.7rem;
  padding: 1px 5px;
  border-radius: 2px;
  background: #F3EFE7;
  border: 1px solid #C9C2B4;
  color: #55514B;
}
.cli-box {
  background: #F3EFE7;
  border: 1px solid #C9C2B4;
  border-radius: 2px;
  padding: 8px;
  font-family: "IBM Plex Mono", monospace;
  font-size: 0.72rem;
  word-break: break-all;
  color: #1C1915;
}
.actions {
  display: flex;
  border-top: 1px solid #C9C2B4;
}
.actions button {
  flex: 1;
  padding: 8px;
  background: #FFFFFF;
  border: none;
  cursor: pointer;
  font-family: "IBM Plex Sans", sans-serif;
  font-size: 0.8rem;
  font-weight: 600;
  color: #1C1915;
}
.actions button:hover {
  background: #E8E3DA;
}
.toast {
  position: fixed;
  bottom: 20px;
  right: 20px;
  background: #1C1915;
  color: #F3EFE7;
  padding: 10px 16px;
  border-radius: 2px;
  font-family: "IBM Plex Mono", monospace;
  font-size: 0.8rem;
  display: none;
  max-width: 450px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.15);
}
"""


def render(run_id: str, receipts: list[dict], items_by_id: dict[str, dict]) -> str:
    """Returns responsive HTML string for visual escalation and review triage adhering to design.md."""
    escalated = [r for r in receipts if r.get("action_state") == "escalated"]
    drafted = [r for r in receipts if r.get("action_state") in ("drafted", "pursued_assisted")]
    skipped = [r for r in receipts if r.get("action_state") == "skipped"]

    cards_html = []
    display_rows = escalated + drafted

    for r in display_rows:
        lid = str(r.get("listing_id", ""))
        item = items_by_id.get(lid, {})
        imgs = item.get("images") or []
        img_url = imgs[0] if imgs else ""
        mz = r.get("scores", {}).get("margin_z")
        h_score = r.get("scores", {}).get("health", item.get("health", "—"))
        reasons = r.get("reason_codes", [])
        state = r.get("action_state", "escalated")

        badge_cls = "status-drafted" if state in ("drafted", "pursued_assisted") else "status-escalated"
        status_word = "DRAFT AWAITING HUMAN" if state == "drafted" else state.upper()
        badges_markup = "".join(f'<span class="badge">{html.escape(rc, quote=True)}</span>' for rc in reasons)

        mz_display = f"{mz:.1f}σ margin" if mz is not None else "no comps"
        photo_markup = (f'<img src="{html.escape(img_url, quote=True)}" alt="item photo" loading="lazy" '
                        f'onerror="this.onerror=null;this.parentElement.innerHTML=\'<div class=\\\'no-photo\\\'>Photo Unavailable</div>\';">'
                        if img_url else '<div class="no-photo">No Photo Available</div>')

        cli_hint = (f'python3 app/run_walking_skeleton.py --confirm {lid}'
                    if state == "drafted" else f'Status: {state.upper()} · review receipts')

        card = f"""
        <div class="card" data-listing-id="{html.escape(lid, quote=True)}">
          {photo_markup}
          <div class="body">
            <div class="price-row">
              <div class="price">€{html.escape(str(item.get('price_eur', '?')), quote=True)}</div>
              <span class="health-badge">Listing Health {html.escape(str(h_score), quote=True)}/100</span>
            </div>
            <div class="title">{html.escape(str(item.get('title', lid)), quote=True)}</div>
            <div class="meta">
              <span class="status-tag {badge_cls}">{html.escape(status_word, quote=True)}</span> · {html.escape(mz_display, quote=True)}<br>
              ID: {html.escape(lid, quote=True)}
            </div>
            <div class="badges">{badges_markup}</div>
            <div class="cli-box">CLI: <code>{html.escape(cli_hint, quote=True)}</code></div>
          </div>
          <div class="actions">
            <button type="button" class="btn-review" data-id="{html.escape(lid, quote=True)}" data-state="{html.escape(state, quote=True)}">Mark Reviewed in Browser</button>
          </div>
        </div>
        """
        cards_html.append(card)

    cards_joined = "\n".join(cards_html) if cards_html else "<p style='color:#7A756D;'>No escalated or drafted items this run.</p>"
    total_count = len(receipts)
    esc_count = len(escalated)
    draft_count = len(drafted)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>MarketMind Triage — {html.escape(run_id, quote=True)}</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>{CARD_CSS}</style>
</head>
<body>
  <header>
    <h1>MarketMind Triage</h1>
    <div class="stats">{html.escape(run_id, quote=True)} · {total_count} processed · {esc_count} escalated · {draft_count} drafted</div>
  </header>
  <div class="grid">
    {cards_joined}
  </div>
  <div id="toast" class="toast">Action noted</div>
  <script>
    document.querySelectorAll('.btn-review').forEach(function(btn) {{
      btn.addEventListener('click', function() {{
        var id = this.getAttribute('data-id');
        var state = this.getAttribute('data-state');
        var card = document.querySelector('[data-listing-id="' + CSS.escape(id) + '"]');
        if (card) {{
          card.style.opacity = '0.5';
        }}
        var toast = document.getElementById('toast');
        var msg = (state === 'drafted')
          ? 'Noted locally. To emit signed receipt, run CLI: python3 app/run_walking_skeleton.py --confirm ' + id
          : 'Escalation noted locally for ' + id;
        toast.textContent = msg;
        toast.style.display = 'block';
        setTimeout(function() {{ toast.style.display = 'none'; }}, 3500);
      }});
    }});
  </script>
</body>
</html>"""


def write(path: Path, run_id: str, receipts: list[dict],
          items_by_id: dict[str, dict]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(render(run_id, receipts, items_by_id), encoding="utf-8")
