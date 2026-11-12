"""Download the Olist public dataset into data/raw/ (raw files are never modified).

Usage:
    python -m olist_ba.ingest              # download from Kaggle (public, no login needed at time of writing)
    python -m olist_ba.ingest --zip PATH   # use a manually downloaded archive.zip
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import ssl
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import certifi

from .config import DATA_RAW, DATASET_PAGE, KAGGLE_URL, RAW_FILES


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def raw_files_present() -> bool:
    return all((DATA_RAW / f).exists() for f in RAW_FILES.values())


def extract(zip_bytes: bytes, dest: Path = DATA_RAW) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        names = set(zf.namelist())
        missing = [f for f in RAW_FILES.values() if f not in names]
        if missing:
            raise RuntimeError(f"Archive is missing expected files: {missing}")
        for f in RAW_FILES.values():
            # Extract by explicit name only (no path traversal from archive members).
            (dest / f).write_bytes(zf.read(f))


def write_manifest(dest: Path = DATA_RAW, source: str = KAGGLE_URL) -> dict:
    manifest = {
        "source": source,
        "dataset_page": DATASET_PAGE,
        "license": "CC BY-NC-SA 4.0",
        "retrieved_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "files": {f: {"bytes": (dest / f).stat().st_size, "sha256": _sha256(dest / f)} for f in RAW_FILES.values()},
    }
    (dest / "MANIFEST.json").write_text(json.dumps(manifest, indent=2))
    return manifest


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--zip", type=Path, help="Path to a manually downloaded Kaggle archive")
    p.add_argument("--force", action="store_true", help="Re-download even if files exist")
    a = p.parse_args(argv)

    if raw_files_present() and not a.force and a.zip is None:
        print(f"Raw files already present in {DATA_RAW}; skipping download (use --force to refresh).")
        return
    if a.zip:
        data, source = a.zip.read_bytes(), f"local:{a.zip.name}"
    else:
        print(f"Downloading {KAGGLE_URL} ...")
        req = urllib.request.Request(KAGGLE_URL, headers={"User-Agent": "olist-ba-portfolio/1.0"})
        # Use certifi's CA bundle: python.org builds on macOS ship without system CA certificates.
        ctx = ssl.create_default_context(cafile=certifi.where())
        with urllib.request.urlopen(req, timeout=300, context=ctx) as r:
            data, source = r.read(), KAGGLE_URL
    extract(data)
    m = write_manifest(source=source)
    print(f"Extracted {len(m['files'])} files to {DATA_RAW}")


if __name__ == "__main__":
    main()
