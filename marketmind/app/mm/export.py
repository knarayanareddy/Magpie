"""EXPORT — CSV export utility for MarketMind triage and reviews.
Outputs app/out/triage_export.csv ready for direct copy-paste or upload into Google Sheets / Excel.
Contains: listing_id, price, health_score, margin_sigma, status, draft_text."""
from __future__ import annotations
import csv, json
from pathlib import Path
from typing import Sequence

HEADERS = ["listing_id", "price", "health_score", "margin_sigma", "status", "draft_text"]


def export_csv(
    dest_path: Path | str,
    receipts: Sequence[dict],
    items_by_id: dict[str, dict] | None = None,
    drafts_by_id: dict[str, dict] | None = None,
    drafts_dir: Path | str | None = None,
) -> Path:
    """Exports receipts and listing facts to RFC 4180 CSV for Google Sheets / Excel import.

    Columns:
      1. listing_id: ID of the listing (e.g. mm-live-switch-01)
      2. price: Asking price in EUR
      3. health_score: 0-100 deterministic health score
      4. margin_sigma: Comps z-score margin (e.g. 2.0) or empty if no comps
      5. status: Final pipeline action state (drafted, escalated, skipped, pursued_auto, pursued_assisted)
      6. draft_text: Personalized draft offer text in Dutch (if drafted/pursued) or empty
    """
    dest = Path(dest_path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    items_by_id = dict(items_by_id or {})
    drafts_by_id = dict(drafts_by_id or {})

    # If receipts is empty (e.g. all feed items deduped this cycle), fallback to receipts.jsonl
    active_receipts = list(receipts)
    if not active_receipts and (dest.parent / "receipts.jsonl").exists():
        try:
            lines = (dest.parent / "receipts.jsonl").read_text(encoding="utf-8").splitlines()
            # Map by listing_id to preserve latest state (e.g., human confirm -> pursued_assisted)
            by_lid: dict[str, dict] = {}
            for line in lines:
                if not line.strip():
                    continue
                r_obj = json.loads(line)
                lid = r_obj.get("listing_id")
                if lid:
                    by_lid[lid] = r_obj
            active_receipts = list(by_lid.values())
        except Exception:
            active_receipts = list(receipts)

    # If items_by_id lacks items (e.g. when called offline), attempt fallback to fixtures
    if not items_by_id:
        try:
            from mm import notice
            sim_items, _ = notice.load("sim", measure=False)
            for itm in sim_items:
                if itm.get("id"):
                    items_by_id[itm["id"]] = itm
        except Exception:
            pass

    rows_to_write = []
    for r in active_receipts:
        lid = str(r.get("listing_id", ""))
        item = items_by_id.get(lid, {})

        # Price extraction
        price_val = item.get("price_eur")
        if price_val is not None and price_val != "":
            try:
                f_p = float(price_val)
                price_out = int(f_p) if f_p.is_integer() else round(f_p, 2)
            except (ValueError, TypeError):
                price_out = price_val
        else:
            price_out = ""

        # Health score
        scores = r.get("scores") or {}
        h_score = scores.get("health", item.get("health", ""))
        if h_score is not None and h_score != "":
            try:
                h_out = int(h_score)
            except (ValueError, TypeError):
                h_out = h_score
        else:
            h_out = ""

        # Margin sigma
        mz = scores.get("margin_z")
        if mz is not None and mz != "":
            try:
                mz_out = round(float(mz), 2)
            except (ValueError, TypeError):
                mz_out = mz
        else:
            mz_out = ""

        # Status
        status_out = r.get("action_state", "")

        # Draft text
        draft_text = ""
        if lid in drafts_by_id:
            d_obj = drafts_by_id[lid]
            if isinstance(d_obj, dict):
                draft_text = d_obj.get("text_nl") or d_obj.get("text", "")
            elif isinstance(d_obj, str):
                draft_text = d_obj
        if not draft_text and drafts_dir:
            d_file = Path(drafts_dir) / f"{lid}.txt"
            if d_file.exists():
                try:
                    draft_text = d_file.read_text(encoding="utf-8").strip()
                except Exception:
                    pass

        rows_to_write.append([
            lid,
            price_out,
            h_out,
            mz_out,
            status_out,
            draft_text,
        ])

    with open(dest, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
        writer.writerow(HEADERS)
        writer.writerows(rows_to_write)

    return dest


def read_csv(csv_path: Path | str) -> list[dict]:
    """Helper to parse the CSV back into dictionaries (used by tests and consumers)."""
    p = Path(csv_path)
    if not p.exists():
        return []
    with open(p, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)
