"""SELL BOARD — static HTML of the sell pipeline (US-9 AC-6). design.md lockfile: Paper/Ink/Rule/Brick,
IBM Plex, radius 2px, no shadows/gradients, emoji are not icons. Status is a WORD, never colour alone.
Honest affordances: every action is a CLI/phone command shown verbatim (no fake buttons)."""
from __future__ import annotations
import html
from pathlib import Path

CSS = """*{box-sizing:border-box}body{font-family:"IBM Plex Sans",-apple-system,sans-serif;background:#F3EFE7;color:#1C1915;margin:0;padding:24px}
header{border-bottom:2px solid #C9C2B4;padding-bottom:12px;margin-bottom:20px}h1{font-size:1.2rem;margin:0}
.meta,.mono{font-family:"IBM Plex Mono",ui-monospace,monospace;font-size:.8rem}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:16px}
.card{border:1px solid #C9C2B4;border-radius:2px;padding:12px;background:#F3EFE7}
.thumbs{display:flex;gap:6px;margin:8px 0}.thumbs img{width:96px;height:96px;object-fit:cover;border:1px solid #C9C2B4;border-radius:2px}
.state{font-weight:700;text-transform:uppercase;letter-spacing:.04em}.brick{color:#8C3A2B}
pre{white-space:pre-wrap;font-family:"IBM Plex Mono",monospace;font-size:.78rem;border-top:1px solid #C9C2B4;padding-top:8px}
footer{margin-top:24px;border-top:1px solid #C9C2B4;padding-top:10px;font-size:.8rem}"""
BRICK = {"needs_confirmation", "privacy_review", "no_comps"}
NEXT = {"needs_confirmation": 'sell.py confirm {id} --model "…"', "privacy_review": 'sell.py confirm {id} --model "…" --clear-privacy',
        "no_comps": "sell.py price {id} --ask N --floor N", "priced": "sell.py draft {id}",
        "drafted": "sell.py posted {id} --ref <marktplaats url>", "posted": 'sell.py msg {id} "<buyer message>"'}


def render(state: dict, footer: str) -> str:
    e = html.escape
    cards = []
    for it in sorted(state["items"].values(), key=lambda x: x["id"]):
        f, p, pr = it.get("facts") or {}, it["proposal"], it.get("price") or {}
        name = f.get("model") or f"proposal: {p['brand']} {p['model']} (certain={p['model_certain']})"
        thumbs = "".join(f'<img src="photos/{e(ph)}" alt="">' for ph in it["photos"][:3])
        price = (f'ask <b>€{pr["ask"]}</b> · floor €{pr["floor"]} · basis {e(str(pr.get("basis")))}'
                 + (f' · sold median €{pr.get("median")} n={pr.get("n")}' if pr.get("basis") == "sold" else "")) if pr.get("status") == "ok" else e(pr.get("reason", "not priced"))
        th = state["threads"].get(it["id"], {})
        msgs = "".join(f'<div class="mono">{e(m["id"])} <span class="state{" brick" if m["action"] != "draft" else ""}">{e(m["status"])}</span> '
                       f'{e(m["label"])} → {e(m["reply_nl"] or ",".join(m["reasons"]))}</div>' for m in th.get("messages", [])[-4:])
        draft = f'<pre>{e(it["draft"]["title"])}\n\n{e(it["draft"]["description"])}\n\ncategorie: {e(it["draft"]["category"])}</pre>' if it.get("draft") else ""
        nxt = NEXT.get(it["status"], "").format(id=it["id"])
        cards.append(f'<div class="card"><div class="mono">{e(it["id"])} · <span class="state{" brick" if it["status"] in BRICK else ""}">'
                     f'{e(it["status"])}</span></div><div><b>{e(name)}</b></div><div class="thumbs">{thumbs}</div>'
                     f'<div class="mono">{price}</div>{draft}{msgs}'
                     f'{f"<div class=meta>next: {e(nxt)}</div>" if nxt else ""}</div>')
    return (f'<!doctype html><html lang="nl"><meta charset="utf-8"><title>Magpie · sell board</title><style>{CSS}</style>'
            f'<header><h1>Magpie — sell board</h1><div class="meta">photo dump → priced listing drafts + negotiation co-pilot · '
            f'you approve with one tap · drafted ≠ posted ≠ sent</div></header><div class="grid">{"".join(cards) or "no items yet — sell.py intake &lt;folder&gt;"}</div>'
            f'<footer>{e(footer)}</footer></html>')


def write(d: Path, state: dict, footer: str) -> Path:
    p = d / "sell_board.html"
    p.write_text(render(state, footer), encoding="utf-8")
    return p
