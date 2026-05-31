"""Background asset fetching and fallback generation."""

from __future__ import annotations

import random
from pathlib import Path

import httpx
from PIL import Image, ImageDraw, ImageFilter

from flux_lang.config import AppConfig
from flux_lang.utils import get_logger

logger = get_logger(__name__)

_PEXELS_BASE = "https://api.pexels.com/v1"
_UNSPLASH_BASE = "https://api.unsplash.com"


async def fetch_backgrounds(config: AppConfig) -> list[str]:
    """Fetch or generate background image paths.

    Returns a list of file paths ready for the renderer.
    """
    paths: list[str] = []

    # 1. Try local folder first
    if config.bg.local_folder:
        local = Path(config.bg.local_folder)
        if local.exists():
            for ext in ("*.jpg", "*.jpeg", "*.png", "*.mp4", "*.mov", "*.webm"):
                paths.extend(str(p) for p in local.glob(ext))
            if paths:
                logger.info("Using %d backgrounds from local folder", len(paths))
                return paths

    # 2. Try Pexels
    if config.pexels_api_key:
        pexels = await _fetch_pexels(config)
        paths.extend(pexels)

    # 3. Try Unsplash if we still need more
    if len(paths) < 3 and config.unsplash_access_key:
        unsplash = await _fetch_unsplash(config)
        paths.extend(unsplash)

    if paths:
        return paths

    # 4. Fallback: generate a gradient background with FFmpeg
    logger.info("No API keys or local folder — generating gradient background")
    gradient = await _generate_gradient(config)
    return [gradient]


async def _fetch_pexels(config: AppConfig) -> list[str]:
    paths: list[str] = []
    headers = {"Authorization": config.pexels_api_key}
    keywords = config.bg.pexels_keywords or ["gradient", "abstract"]

    async with httpx.AsyncClient(timeout=30.0) as client:
        for keyword in keywords:
            if len(paths) >= 5:
                break
            try:
                resp = await client.get(
                    f"{_PEXELS_BASE}/search",
                    headers=headers,
                    params={"query": keyword, "orientation": "portrait", "per_page": 3},
                )
                resp.raise_for_status()
                data = resp.json()
            except httpx.HTTPError as e:
                logger.warning("Pexels search failed: %s", e)
                continue

            for photo in data.get("photos", []):
                if len(paths) >= 5:
                    break
                src_url = photo.get("src", {}).get("large") or photo.get("src", {}).get("original")
                if not src_url:
                    continue
                try:
                    img_resp = await client.get(src_url, timeout=30.0)
                    img_resp.raise_for_status()
                except httpx.HTTPError:
                    continue

                photo_id = photo.get("id", random.randint(1000, 9999))
                dest = Path(config.output_dir) / ".bg_cache" / f"pexels_{photo_id}.jpg"
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(img_resp.content)
                paths.append(str(dest))

    logger.info("Pexels: fetched %d backgrounds", len(paths))
    return paths


async def _fetch_unsplash(config: AppConfig) -> list[str]:
    paths: list[str] = []
    headers = {"Authorization": f"Client-ID {config.unsplash_access_key}"}
    keywords = config.bg.unsplash_keywords or ["texture", "pattern"]

    async with httpx.AsyncClient(timeout=30.0) as client:
        for keyword in keywords:
            if len(paths) >= 3:
                break
            try:
                resp = await client.get(
                    f"{_UNSPLASH_BASE}/search/photos",
                    headers=headers,
                    params={"query": keyword, "orientation": "portrait", "per_page": 3},
                )
                resp.raise_for_status()
                data = resp.json()
            except httpx.HTTPError as e:
                logger.warning("Unsplash search failed: %s", e)
                continue

            for result in data.get("results", []):
                if len(paths) >= 3:
                    break
                img_url = result.get("urls", {}).get("regular")
                if not img_url:
                    continue
                try:
                    img_resp = await client.get(img_url, timeout=30.0)
                    img_resp.raise_for_status()
                except httpx.HTTPError:
                    continue

                img_id = result.get("id", random.randint(1000, 9999))
                dest = Path(config.output_dir) / ".bg_cache" / f"unsplash_{img_id}.jpg"
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(img_resp.content)
                paths.append(str(dest))

    logger.info("Unsplash: fetched %d backgrounds", len(paths))
    return paths


async def _generate_gradient(config: AppConfig) -> str:
    """Generate a vibrant glassmorphic mesh background."""
    dest = Path(config.output_dir) / ".bg_cache" / "gradient_fallback.jpg"
    dest.parent.mkdir(parents=True, exist_ok=True)

    w, h = config.canvas.width, config.canvas.height

    # Deep navy base backdrop
    base = Image.new("RGBA", (w, h), (15, 15, 30, 255))

    # 1. Overlay Magenta glowing circle (top-right area)
    overlay_mag = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw_mag = ImageDraw.Draw(overlay_mag)
    r_mag = int(w * 0.6)
    cx_mag, cy_mag = int(w * 0.8), int(h * 0.2)
    draw_mag.ellipse(
        [cx_mag - r_mag, cy_mag - r_mag, cx_mag + r_mag, cy_mag + r_mag],
        fill=(255, 30, 150, 100),
    )
    base = Image.alpha_composite(base, overlay_mag)

    # 2. Overlay Cyan glowing circle (middle-left area)
    overlay_cyan = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw_cyan = ImageDraw.Draw(overlay_cyan)
    r_cyan = int(w * 0.7)
    cx_cyan, cy_cyan = int(w * 0.2), int(h * 0.5)
    draw_cyan.ellipse(
        [cx_cyan - r_cyan, cy_cyan - r_cyan, cx_cyan + r_cyan, cy_cyan + r_cyan],
        fill=(0, 220, 255, 100),
    )
    base = Image.alpha_composite(base, overlay_cyan)

    # 3. Overlay Purple glowing circle (bottom-right area)
    overlay_pur = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw_pur = ImageDraw.Draw(overlay_pur)
    r_pur = int(w * 0.8)
    cx_pur, cy_pur = int(w * 0.7), int(h * 0.8)
    draw_pur.ellipse(
        [cx_pur - r_pur, cy_pur - r_pur, cx_pur + r_pur, cy_pur + r_pur],
        fill=(130, 50, 255, 120),
    )
    base = Image.alpha_composite(base, overlay_pur)

    # Blur base heavily to melt the circles together
    img = base.convert("RGB")
    img = img.filter(ImageFilter.GaussianBlur(radius=150))
    img_rgba = img.convert("RGBA")

    # 4. Generate smaller, more defined glowing orbs for color bleed behind card
    detail_base = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    detail_draw = ImageDraw.Draw(detail_base)

    # Orb 1: Orange/Gold glow near center-right
    r_d1 = int(w * 0.22)
    cx_d1, cy_d1 = int(w * 0.75), int(h * 0.45)
    detail_draw.ellipse(
        [cx_d1 - r_d1, cy_d1 - r_d1, cx_d1 + r_d1, cy_d1 + r_d1],
        fill=(255, 150, 20, 80),
    )

    # Orb 2: Pink/Magenta glow near center-left
    r_d2 = int(w * 0.20)
    cx_d2, cy_d2 = int(w * 0.25), int(h * 0.65)
    detail_draw.ellipse(
        [cx_d2 - r_d2, cy_d2 - r_d2, cx_d2 + r_d2, cy_d2 + r_d2],
        fill=(255, 30, 180, 80),
    )

    # Orb 3: Cyan/Electric Blue glow near upper-middle
    r_d3 = int(w * 0.15)
    cx_d3, cy_d3 = int(w * 0.45), int(h * 0.30)
    detail_draw.ellipse(
        [cx_d3 - r_d3, cy_d3 - r_d3, cx_d3 + r_d3, cy_d3 + r_d3],
        fill=(0, 200, 255, 70),
    )

    # Blur details with a smaller radius (65) to keep them distinct but soft
    detail_base = detail_base.filter(ImageFilter.GaussianBlur(radius=65))
    final_rgba = Image.alpha_composite(img_rgba, detail_base)

    final_rgba.convert("RGB").save(dest, "JPEG", quality=92)
    logger.info("Generated vibrant mesh gradient background: %s", dest)
    return str(dest)

