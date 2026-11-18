"""Phase 4 - Data acquisition.

Downloads the official ANP files byte-for-byte into data/raw/ and records a manifest with
SHA-256, size, server Last-Modified and download time, so every later number is traceable
to an exact file version.

CLI:  python -m oilgas.acquisition            (from oil-gas-intelligence/src)
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from oilgas.config import BENCHMARKS, MANIFEST, METADATA, RAW_DIR, SOURCES

USER_AGENT = "industrial-data-analytics/0.1 (portfolio research; python-urllib)"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def download(url: str, dest: Path, timeout: int = 300) -> dict:
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # TLS verification stays on
        last_modified = resp.headers.get("Last-Modified", "")
        dest.write_bytes(resp.read())
    return {
        "file": dest.relative_to(RAW_DIR).as_posix(),
        "url": url,
        "bytes": dest.stat().st_size,
        "sha256": sha256(dest),
        "last_modified": last_modified,
        "downloaded_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def acquire(include_benchmarks: bool = True, include_metadata: bool = True) -> list[dict]:
    jobs = [(url, RAW_DIR / "ppgn" / fname) for url, fname, _, _ in SOURCES.values()]
    if include_benchmarks:
        jobs += [(url, RAW_DIR / "anuario_2026" / url.rsplit("/", 1)[1]) for url in BENCHMARKS.values()]
    if include_metadata:
        jobs += [(url, RAW_DIR / "metadata" / name) for name, url in METADATA.items()]
    rows = []
    for url, dest in jobs:
        print(f"Downloading {url}")
        rows.append(download(url, dest))
    with MANIFEST.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    return rows


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--no-benchmarks", action="store_true")
    ap.add_argument("--no-metadata", action="store_true")
    a = ap.parse_args()
    for r in acquire(not a.no_benchmarks, not a.no_metadata):
        print(f"  {r['file']:<55} {r['bytes']:>10,}  {r['last_modified']}")
    print(f"Manifest: {MANIFEST}")


if __name__ == "__main__":
    main()
