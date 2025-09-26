#!/usr/bin/env python3
"""
Fetch one or more Kaggle datasets into sources/ using the Kaggle CLI,
then (optionally) unzip them in place.

Requirements:
  - kaggle CLI installed and on PATH (kaggle)
  - ~/.kaggle/kaggle.json present with {"username":"...","key":"..."}

Usage examples:
  python3 scripts/fetch_kaggle_datasets.py --slug alicelabs/new-plant-diseases-dataset --unzip
  python3 scripts/fetch_kaggle_datasets.py --slug muhammadardiputra/plantvillage-dataset --unzip

Notes:
  - This script only downloads into sources/<slug_last_part>/.
  - Use other scripts to normalize, rename, and merge into datasets/.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
from pathlib import Path


def check_kaggle_cli() -> None:
    from shutil import which
    if which("kaggle") is None:
        raise SystemExit(
            "kaggle CLI not found. Install via `pip install kaggle` and place ~/.kaggle/kaggle.json."
        )
    cfg = Path.home() / ".kaggle" / "kaggle.json"
    if not cfg.exists():
        raise SystemExit(
            "~/.kaggle/kaggle.json not found. Download API token from Kaggle account and place it there (chmod 600)."
        )


def run(cmd: list[str], cwd: str | None = None) -> None:
    print("$", " ".join(cmd))
    subprocess.run(cmd, check=True, cwd=cwd)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug", action="append", help="owner/dataset slug on Kaggle", required=True)
    ap.add_argument("--unzip", action="store_true", help="Unzip downloaded file(s) into sources/<name>/")
    args = ap.parse_args()

    check_kaggle_cli()

    sources = Path("sources")
    sources.mkdir(parents=True, exist_ok=True)

    for slug in args.slug:
        name = slug.split("/")[-1]
        out_dir = sources / name
        out_dir.mkdir(parents=True, exist_ok=True)
        # Download into sources/name/
        run(["kaggle", "datasets", "download", "-d", slug, "-p", str(out_dir)])
        if args.unzip:
            # Unzip all zips within out_dir
            for z in out_dir.glob("*.zip"):
                run(["unzip", "-o", "-q", str(z)], cwd=str(out_dir))
    print("Done.")


if __name__ == "__main__":
    main()

