"""
Brand config loader.

Reads `brand/brand.yaml` and exposes the values that the proposal and quote
templates consume. Also base64-inlines the logo so the rendered HTML is
self-contained (no broken images in a PDF).
"""
from __future__ import annotations

import base64
import mimetypes
from functools import lru_cache
from pathlib import Path

import yaml

BRAND_DIR = Path("brand")


@lru_cache(maxsize=1)
def load() -> dict:
    cfg = yaml.safe_load((BRAND_DIR / "brand.yaml").read_text(encoding="utf-8")) or {}
    logo_path = BRAND_DIR / (cfg.get("logo_file") or "logo.svg")
    if logo_path.exists():
        mime = mimetypes.guess_type(str(logo_path))[0] or "image/svg+xml"
        b64 = base64.b64encode(logo_path.read_bytes()).decode("ascii")
        cfg["logo_data_url"] = f"data:{mime};base64,{b64}"
    else:
        cfg["logo_data_url"] = ""
    return cfg


def reload() -> dict:
    """Bust the cache — useful if you tweak brand.yaml while uvicorn is running."""
    load.cache_clear()
    return load()
