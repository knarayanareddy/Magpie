"""INTAKE — sanitize a photo dump and group photos into items (US-9 AC-1, AC-5).

Privacy first: every photo is decoded and RE-ENCODED from pixels only (EXIF/GPS/XMP/ICC/maker notes
dropped); originals are never copied into out/. Orientation is baked in before stripping so photos
don't come out sideways. HEIC (iPhone default) is converted via macOS `sips` when Pillow lacks a plugin.
Grouping is deterministic: consecutive photos (capture time, then filename) join the current item when
their dHash is near-identical OR they were taken within GROUP_WINDOW_S. A model never groups.
"""
from __future__ import annotations
import hashlib, io, os, shutil, subprocess, tempfile
from datetime import datetime
from pathlib import Path

from .. import phash

try:
    from PIL import Image, ImageOps
except Exception:  # pragma: no cover
    Image = ImageOps = None

EXTS = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif"}
MAX_EDGE = 1600            # listing photos: Marktplaats downsizes anyway; keeps vision payload small
GROUP_WINDOW_S = int(os.environ.get("SELL_GROUP_WINDOW_S", "20"))
SAME_ITEM_HAMMING = int(os.environ.get("SELL_SAME_ITEM_HAMMING", "12"))
MAX_PHOTOS = 200


def _open(path: Path):
    """Return a PIL image; HEIC via sips fallback. None if unreadable."""
    if Image is None:
        raise RuntimeError("Pillow is required for sell intake (pip install --user Pillow)")
    try:
        return Image.open(path)
    except Exception:
        pass
    if path.suffix.lower() in (".heic", ".heif") and shutil.which("sips"):
        with tempfile.TemporaryDirectory() as td:
            dst = Path(td) / "c.jpg"
            r = subprocess.run(["sips", "-s", "format", "jpeg", str(path), "--out", str(dst)],
                               capture_output=True, timeout=30)
            if r.returncode == 0 and dst.exists():
                im = Image.open(dst)
                im.load()
                return im
    return None


def _taken_at(im, path: Path) -> float:
    """Capture time from EXIF DateTimeOriginal (read BEFORE stripping), else file mtime."""
    try:
        ex = im.getexif()
        raw = ex.get_ifd(0x8769).get(36867) or ex.get(306)  # DateTimeOriginal, else DateTime
        if raw:
            return datetime.strptime(str(raw), "%Y:%m:%d %H:%M:%S").timestamp()
    except Exception:
        pass
    return path.stat().st_mtime


def sanitize(src: Path, dst_dir: Path) -> dict | None:
    """Re-encode pixels only. Returns {file, sha, dhash, taken_at, w, h} or None if unreadable."""
    im = _open(src)
    if im is None:
        return None
    taken = _taken_at(im, src)
    im = ImageOps.exif_transpose(im)                 # bake orientation, then drop all metadata
    im = im.convert("RGB")
    im.thumbnail((MAX_EDGE, MAX_EDGE))
    clean = Image.new("RGB", im.size)
    clean.putdata(list(im.getdata()))                # fresh image object: no info/exif/icc carried over
    buf = io.BytesIO()
    clean.save(buf, "JPEG", quality=88, optimize=True)   # no exif= / icc_profile= passed => none written
    data = buf.getvalue()
    sha = hashlib.sha256(data).hexdigest()[:16]
    out = dst_dir / f"{sha}.jpg"
    out.write_bytes(data)
    return {"file": out.name, "sha": sha, "dhash": phash.dhash_bytes(data), "taken_at": taken,
            "w": clean.size[0], "h": clean.size[1], "src_name": src.name}


def has_metadata(path: Path) -> bool:
    """Verification helper: True if any EXIF/GPS/ICC survives in a written file."""
    im = Image.open(path)
    return bool(im.getexif()) or bool(im.info.get("exif")) or bool(im.info.get("icc_profile"))


def collect(folder: Path) -> list[Path]:
    files = sorted(p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in EXTS
                   and not p.name.startswith("."))
    if len(files) > MAX_PHOTOS:
        raise ValueError(f"{len(files)} photos > MAX_PHOTOS={MAX_PHOTOS}; split the dump")
    return files


def group(photos: list[dict]) -> list[list[dict]]:
    """Deterministic grouping: sort by capture time; join current group if near-dup or within window."""
    ps = sorted(photos, key=lambda p: (p["taken_at"], p["src_name"]))
    groups: list[list[dict]] = []
    for p in ps:
        if groups:
            last = groups[-1][-1]
            near = bool(p["dhash"] and last["dhash"] and phash.hamming(p["dhash"], last["dhash"]) <= SAME_ITEM_HAMMING)
            close = abs(p["taken_at"] - last["taken_at"]) <= GROUP_WINDOW_S
            if near or close:
                groups[-1].append(p)
                continue
        groups.append([p])
    return groups
