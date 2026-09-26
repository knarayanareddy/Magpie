"""LISTING DRAFT — Dutch title/description from CONFIRMED facts only (US-9 AC-3). drafted != posted.

No generative model writes listing claims: the text is a template over fields the human confirmed
(model, condition, defects, accessories) + computed price. So a draft can never promise a spec the
item doesn't have. Magpie never posts; the human pastes this into Marktplaats.
"""
from __future__ import annotations

COND_NL = {"new": "Nieuw (ongebruikt)", "like_new": "Zo goed als nieuw", "used": "Gebruikt, goed werkend",
           "damaged": "Beschadigd — zie foto's en beschrijving", "unknown": "Gebruikt"}
# Marktplaats top-level category names (suggestion for the human; posting is manual)
CAT_NL = {"phone": "Telecommunicatie › Mobiele telefoons", "tablet": "Computers en Software › Tablets",
          "laptop": "Computers en Software › Laptops", "console": "Spelcomputers en Games › Spelcomputers",
          "game": "Spelcomputers en Games › Games", "camera": "Audio, Tv en Foto › Fotocamera's",
          "lens": "Audio, Tv en Foto › Objectieven", "audio": "Audio, Tv en Foto › Koptelefoons en Headsets",
          "watch": "Sieraden, Tassen en Uiterlijk › Horloges", "bike": "Fietsen en Brommers",
          "furniture": "Huis en Inrichting", "clothing": "Kleding", "book": "Boeken", "toy": "Speelgoed",
          "kitchen": "Witgoed en Apparatuur", "tool": "Doe-het-zelf en Verbouw", "other": "Overige"}
MAX_TITLE = 60   # Marktplaats title limit


def _clean(s: str) -> str:
    return " ".join(str(s or "").replace("\n", " ").split())


def render(item: dict) -> dict:
    """item must be confirmed + priced. Returns {title, description, category, ask_eur, photos}."""
    f = item["facts"]
    brand, model = _clean(f["brand"]), _clean(f["model"])
    name = model if brand.lower() in model.lower() or brand.lower() == "unknown" else f"{brand} {model}"
    cond = COND_NL.get(f["condition"], COND_NL["unknown"])
    title = f"{name} — {cond.split(' —')[0].split(',')[0]}"[:MAX_TITLE]
    lines = [f"Te koop: {name}.", "", f"Staat: {cond}."]
    if f.get("defects"):
        lines.append("Gebreken (eerlijk vermeld): " + "; ".join(_clean(d) for d in f["defects"]) + ".")
    if f.get("accessories"):
        lines.append("Inclusief: " + ", ".join(_clean(a) for a in f["accessories"]) + ".")
    lines += ["", f"Vraagprijs €{item['price']['ask']} — redelijke biedingen welkom.",
              "Ophalen of verzenden via het Marktplaats-platform (Gelijk Oversteken / verzendlabel van Marktplaats).",
              "Geen betalingen vooraf buiten het platform."]
    return {"title": title, "description": "\n".join(lines), "category": CAT_NL.get(f["category"], CAT_NL["other"]),
            "ask_eur": item["price"]["ask"], "photos": item["photos"]}
