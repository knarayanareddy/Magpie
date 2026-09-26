"""EXPAND — compounding seed discovery from quality listings (Darko improvement #4).
When the pipeline finds a verified deal or high-signal item, expands search space by:
1. Identifying seller profile URLs for additional catalog discovery
2. Extracting high-frequency keyword seeds for follow-up search sweeps

Art XII.1: all URLs are strictly on allowlisted Marktplaats domains via Apify actors.
Art III: no personal profiling — examines listing attributes only."""
from __future__ import annotations
from collections import Counter
import re

STOP_WORDS = {
    "de", "het", "een", "en", "van", "voor", "met", "in", "op",
    "te", "is", "niet", "je", "dat", "die", "er", "aan", "bij",
    "nog", "als", "maar", "of", "naar", "om", "dan", "ook", "al",
    "dit", "was", "zo", "uit", "kan", "zijn", "ik", "ze", "mijn",
    "the", "and", "for", "with", "this", "that", "from", "has", "are",
    "zo goed als nieuw", "nieuw", "gebruikt", "te koop"
}

BASE_TERMS = {"nintendo", "switch", "canon", "lens", "ps4", "ps5", "pro"}


def extract_seeds(item: dict, decision_action: str) -> dict:
    """Returns expansion signals from a quality listing.
    Only triggered for 'pursue' or 'escalate' listings with plausible margins."""
    seeds: dict[str, str | list[str] | None] = {"seller_profile": None, "keywords": []}

    seller = item.get("seller") or {}
    seller_name = seller.get("name")
    if seller_name and str(seller_name).isalnum():
        seeds["seller_profile"] = f"https://www.marktplaats.nl/u/{seller_name}/"

    title = (item.get("title") or "").lower()
    words = re.findall(r"[a-z0-9]+", title)
    keywords = [w for w in words if len(w) > 2 and w not in STOP_WORDS]
    seeds["keywords"] = keywords[:5]

    return seeds


def build_expansion_queries(seed_buffer: list[dict], max_queries: int = 3) -> list[str]:
    """Builds prioritized novel search terms from accumulated seeds."""
    kw_counts: Counter[str] = Counter()
    for seed in seed_buffer:
        for kw in seed.get("keywords", []):
            kw_counts[kw] += 1

    novel = [(kw, c) for kw, c in kw_counts.most_common(20) if kw not in BASE_TERMS]
    return [kw for kw, _ in novel[:max_queries]]


def seller_profiles_to_scrape(seed_buffer: list[dict], max_profiles: int = 5) -> list[str]:
    """Returns deduplicated seller profile URLs for catalog scraping."""
    seen = set()
    urls = []
    for seed in seed_buffer:
        url = seed.get("seller_profile")
        if url and url not in seen:
            seen.add(url)
            urls.append(url)
            if len(urls) >= max_profiles:
                break
    return urls
