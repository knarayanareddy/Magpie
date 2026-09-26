"""Duplicate-photo signal (T09) — 64-bit difference hash (dHash) of a listing's first photo, so a
re-post under a new listing id doesn't get a second offer. (Module name `phash` is historical: the
algorithm is dHash, not DCT pHash.) A match is a SIGNAL that escalates, never proof of identity.

Deterministic, no model (threat-model §Photos). Art XII.1: image bytes are fetched ONLY from the
pinned marketplace image CDN (host allowlist); redirects are re-validated against the same allowlist
at every hop; seller-supplied URLs in text are never fetched.
Fail-open by design: a photo that can't be hashed yields None and the item continues on its
id-dedupe path — hashing may add suspicion (duplicate_photo), it can never grant a pursue.
Backend: Pillow if installed, else macOS `sips` (zero-dependency fallback). No backend => disabled.
"""
from __future__ import annotations
import io, os, shutil, subprocess, tempfile, time, urllib.error, urllib.parse, urllib.request

ALLOWED_HOSTS = ("images.marktplaats.com", "images.2dehands.com")
DUP_MAX_HAMMING = int(os.environ.get("PHASH_MAX_HAMMING", "6"))   # of 64 bits
FETCH_TIMEOUT_S = 8
MAX_BYTES = 3_000_000
_SIZE = 9  # dHash: 9x8 grayscale -> 64 horizontal-gradient bits

try:
    from PIL import Image  # type: ignore
except Exception:  # pragma: no cover - depends on host
    Image = None


def backend() -> str | None:
    if os.environ.get("PHASH_DISABLE") == "1":
        return None
    if Image is not None:
        return "pillow"
    if shutil.which("sips"):
        return "sips"
    return None


def _allowed(url: str) -> str | None:
    if url.startswith("//"):
        url = "https:" + url
    p = urllib.parse.urlparse(url)
    if p.scheme != "https" or (p.hostname or "") not in ALLOWED_HOSTS:
        return None
    return url


class _AllowlistRedirects(urllib.request.HTTPRedirectHandler):
    """Re-check every redirect hop against the CDN allowlist (a 30x must not escape Art XII.1)."""
    max_redirections = 3

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if _allowed(urllib.parse.urljoin(req.full_url, newurl)) is None:
            raise urllib.error.HTTPError(newurl, code, "redirect off allowlist", headers, fp)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


_OPENER = urllib.request.build_opener(_AllowlistRedirects)


def _fetch(url: str) -> bytes | None:
    req = urllib.request.Request(url, headers={"User-Agent": "Magpie-dhash/1"})
    try:
        with _OPENER.open(req, timeout=FETCH_TIMEOUT_S) as r:
            if _allowed(r.geturl()) is None:      # belt-and-braces: final URL must still be on the CDN
                return None
            data = r.read(MAX_BYTES + 1)
        return data if 0 < len(data) <= MAX_BYTES else None
    except Exception:
        return None


def _gray_pixels(data: bytes) -> list[int] | None:
    """Return _SIZE x 8 grayscale pixels (row-major)."""
    if Image is not None:
        try:
            im = Image.open(io.BytesIO(data)).convert("L").resize((_SIZE, 8), Image.LANCZOS)
            return list(im.getdata())
        except Exception:
            return None
    if shutil.which("sips"):
        with tempfile.TemporaryDirectory() as d:
            src, dst = os.path.join(d, "in"), os.path.join(d, "out.bmp")
            open(src, "wb").write(data)
            r = subprocess.run(["sips", "-s", "format", "bmp", "-z", "8", str(_SIZE), src, "--out", dst],
                               capture_output=True, timeout=15)
            if r.returncode != 0 or not os.path.exists(dst):
                return None
            return _bmp_gray(open(dst, "rb").read())
    return None


def _bmp_gray(b: bytes) -> list[int] | None:
    try:
        off = int.from_bytes(b[10:14], "little")
        w, h = int.from_bytes(b[18:22], "little", signed=True), int.from_bytes(b[22:26], "little", signed=True)
        bpp = int.from_bytes(b[28:30], "little")
        if bpp not in (24, 32):
            return None
        step, row = bpp // 8, ((bpp * w + 31) // 32) * 4
        px = []
        for y in range(abs(h)):
            ry = (abs(h) - 1 - y) if h > 0 else y  # BMP is bottom-up when h > 0
            base = off + ry * row
            for x in range(w):
                bl, g, r = b[base + x * step: base + x * step + 3]
                px.append((r * 299 + g * 587 + bl * 114) // 1000)
        return px
    except Exception:
        return None


def dhash_bytes(data: bytes) -> str | None:
    px = _gray_pixels(data)
    if not px or len(px) != _SIZE * 8:
        return None
    bits = 0
    for y in range(8):
        for x in range(8):
            bits = (bits << 1) | int(px[y * _SIZE + x] > px[y * _SIZE + x + 1])
    return f"{bits:016x}"


def item_hash(item: dict) -> str | None:
    """Hash the first allowlisted image of a listing. None = unhashable (fail-open)."""
    if backend() is None:
        return None
    for u in (item.get("images") or [])[:2]:
        url = _allowed(str(u))
        if url:
            data = _fetch(url)
            if data:
                h = dhash_bytes(data)
                if h:
                    return h
    return None


def hamming(a: str, b: str) -> int:
    return bin(int(a, 16) ^ int(b, 16)).count("1")


def find_duplicate(h: str, index: dict, self_id: str) -> str | None:
    """index: {phash: {"id": listing_id, "ts": ...}}. Returns the prior listing id if near-identical."""
    if h in index and index[h]["id"] != self_id:
        return index[h]["id"]
    for k, v in index.items():
        if v["id"] != self_id and hamming(h, k) <= DUP_MAX_HAMMING:
            return v["id"]
    return None


RETRY_AFTER_S = int(os.environ.get("PHASH_RETRY_S", "7200"))  # failed hash => retry after 2h, not never
MAX_RETRIES = 3


def should_retry(failed: dict, listing_id: str, now: float | None = None) -> bool:
    """failed: {listing_id: {"ts": epoch, "n": attempts}}. Transient CDN errors must not blind the guard."""
    f = failed.get(listing_id)
    if not f:
        return True
    return f["n"] < MAX_RETRIES and ((now or time.time()) - f["ts"]) >= RETRY_AFTER_S


def mark_failed(failed: dict, listing_id: str, now: float | None = None) -> None:
    f = failed.setdefault(listing_id, {"ts": 0, "n": 0})
    f["ts"], f["n"] = (now or time.time()), f["n"] + 1
    if len(failed) > 2000:                       # bound state size: drop oldest
        for k in sorted(failed, key=lambda k: failed[k]["ts"])[: len(failed) - 2000]:
            failed.pop(k)


def remember(h: str, index: dict, listing_id: str) -> None:
    index.setdefault(h, {"id": listing_id, "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())})
