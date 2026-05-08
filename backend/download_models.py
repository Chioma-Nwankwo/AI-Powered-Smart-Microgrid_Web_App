#!/usr/bin/env python3
"""Download pre-trained ML models from GitHub Releases on Render build.

Usage (Render build command):
  pip install -r requirements.txt && python backend/download_models.py

Required env var:
  MODELS_RELEASE_URL  Base URL of the GitHub Release, e.g.:
    https://github.com/ChiomaNwankwo/AI-Powered-Smart-Microgrid_Web_App/releases/download/v1.0-models
"""
import os
import sys
from pathlib import Path

try:
    import requests as _requests
except ImportError:
    _requests = None

import urllib.request as _urllib

RELEASE_URL = os.environ.get('MODELS_RELEASE_URL', '').rstrip('/')

REPO_ROOT   = Path(__file__).parent.parent
MODELS_DIR  = REPO_ROOT / 'models' / 'trained'
SCALERS_DIR = REPO_ROOT / 'models' / 'scalers'

COUNTRIES = ['nigeria', 'australia', 'canada', 'germany']
TARGETS   = ['solar_radiation_wm2', 'wind_speed', 'demand_mw']


def _files():
    # Legacy (no-type-suffix) model files — used as XGB fallback by model_loader.py
    for c in COUNTRIES:
        for t in TARGETS:
            yield MODELS_DIR, f"{c}_{t}_model.pkl"
    # Scaler and feature-list files (tiny, ~1–2 KB each)
    for c in COUNTRIES:
        for t in TARGETS:
            yield SCALERS_DIR, f"{c}_{t}_scaler.pkl"
            yield SCALERS_DIR, f"{c}_{t}_features.pkl"


def _fetch(url: str, dest: Path) -> None:
    if _requests is not None:
        r = _requests.get(url, stream=True, timeout=120)
        r.raise_for_status()
        with open(dest, 'wb') as f:
            for chunk in r.iter_content(65536):
                f.write(chunk)
    else:
        _urllib.urlretrieve(url, dest)


def main() -> None:
    if not RELEASE_URL:
        print("MODELS_RELEASE_URL not set — skipping model download")
        return

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    SCALERS_DIR.mkdir(parents=True, exist_ok=True)

    total = sum(1 for _ in _files())
    done  = 0
    failed: list[str] = []

    for dest_dir, fname in _files():
        dest = dest_dir / fname
        if dest.exists():
            print(f"  [ok] {fname}")
            done += 1
            continue

        url = f"{RELEASE_URL}/{fname}"
        print(f"  [dl] {fname} ...", flush=True)
        try:
            _fetch(url, dest)
            kb = dest.stat().st_size // 1024
            print(f"       {kb} KB")
            done += 1
        except Exception as exc:
            print(f"  [!!] {fname}: {exc}", file=sys.stderr)
            failed.append(fname)

    print(f"\nModels ready: {done}/{total}")
    if failed:
        print(f"Failed ({len(failed)}):", file=sys.stderr)
        for f in failed:
            print(f"  - {f}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
