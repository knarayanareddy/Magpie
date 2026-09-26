"""pHash dedupe (T09) — perceptual photo hash so re-posts under a new listing id don't double-offer.

Deterministic, no model (threat-model §Photos). Art XII.1: image bytes are fetched ONLY from the
pinned marketplace image CDN (host allowlist); seller-supplied URLs in text are never fetched.
Fail-open by design: a photo that can't be hashed yields None and the item continues on its
id-dedupe path — hashing may add suspicion (duplicate_photo), it can never grant a pursue.
Backend: Pillow if installed, else macOS `sips` (zero-dependency fallback). No backend => disabled.
"""
from __future__ import annotations
import io, os, shutil, subprocess, tempfile, time, urllib.parse, urllib.request

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


def _fetch(url: str) -> bytes | None:
    req = urllib.request.Request(url, headers={"User-Agent": "Magpie-phash/1"})
    try:
        with urllib.request.urlopen(req, timeout=FETCH_TIMEOUT_S) as r:
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


def remember(h: str, index: dict, listing_id: str) -> None:
    index.setdefault(h, {"id": listing_id, "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())})
