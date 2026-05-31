"""Generate rounded-corner card overlays for word blocks using PIL.

These PNGs are composited behind text in FFmpeg for a glassmorphism effect.
"""

from __future__ import annotations

from pathlib import Path


try:
    from PIL import Image, ImageDraw, ImageFilter

    HAS_PIL = True
except ImportError:
    HAS_PIL = False

if HAS_PIL:
    _RESAMPLE_BILINEAR = getattr(getattr(Image, "Resampling", Image), "BILINEAR", 2)
else:
    _RESAMPLE_BILINEAR = 2


def _round_rect_mask(size: tuple[int, int], radius: int) -> Image.Image:
    """Create an RGBA image with a white rounded rectangle on black background."""
    w, h = size
    mask = Image.new("L", (w, h), 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle((0, 0, w - 1, h - 1), radius=radius, fill=255)
    return mask


def _parse_color(c: str | tuple[int, int, int, int], default_alpha: int = 255) -> tuple[int, int, int, int]:
    if isinstance(c, tuple):
        return c
    from PIL import ImageColor
    rgb = ImageColor.getrgb(c)
    if len(rgb) == 4:
        return rgb
    return (rgb[0], rgb[1], rgb[2], default_alpha)


def _create_linear_gradient(
    size: tuple[int, int],
    color_start: tuple[int, int, int, int],
    color_end: tuple[int, int, int, int]
) -> Image.Image:
    """Create a smooth 2D linear gradient from top-left to bottom-right using bilinear interpolation."""
    small = Image.new("RGBA", (2, 2))
    # Top-left and bottom-right pixels get the start and end colors
    small.putpixel((0, 0), color_start)
    small.putpixel((1, 1), color_end)

    # Off-diagonal pixels get the average color
    half = tuple((color_start[c] + color_end[c]) // 2 for c in range(4))
    small.putpixel((1, 0), half)
    small.putpixel((0, 1), half)

    # Scale up using bilinear interpolation for a perfect smooth gradient
    return small.resize(size, _RESAMPLE_BILINEAR)


def generate_card_overlay(
    width: int,
    height: int,
    output_path: str,
    fill_color: tuple[int, int, int, int] = (20, 20, 30, 180),
    border_color: tuple[int, int, int, int] = (255, 255, 255, 60),
    border_width: int = 2,
    corner_radius: int = 40,
    shadow_offset: tuple[int, int] = (0, 8),
    shadow_blur: int = 24,
    shadow_color: tuple[int, int, int, int] = (10, 10, 25, 90),
    padding: int = 30,
    divider: bool = False,
    progress_dots: bool = False,
    dot_count: int = 5,
    active_dot: int = 0,
    dot_color_active: str | tuple[int, int, int, int] = (255, 255, 255, 220),
    dot_color_inactive: str | tuple[int, int, int, int] = (255, 255, 255, 70),
) -> str:
    """Generate a PNG card with rounded corners, semi-transparent fill, drop-shadow, and subtle border.

    Args:
        width: Canvas width in pixels.
        height: Canvas height in pixels.
        output_path: Where to save the PNG.
        fill_color: RGBA tuple for the card fill (default: dark semi-transparent).
        border_color: RGBA tuple for the border (default: subtle white).
        border_width: Border thickness in pixels.
        corner_radius: Corner roundness in pixels.
        shadow_offset: Offset of the drop shadow in pixels (x, y).
        shadow_blur: Gaussian blur radius of the drop shadow.
        shadow_color: RGBA tuple for the drop shadow (default: deep ambient indigo/navy).
        padding: Inset padding to leave space for the shadow to diffuse.
        divider: If True, draw a subtle horizontal divider line in the card's middle.
        progress_dots: If True, draw carousel progress dots near the bottom of the card.
        dot_count: Total number of progress dots.
        active_dot: Index of the active dot.
        dot_color_active: Color for the active dot.
        dot_color_inactive: Color for inactive dots.

    Returns:
        Absolute path to the generated PNG.
    """
    if not HAS_PIL:
        raise RuntimeError("PIL (Pillow) is required for card overlay generation.")

    # Create transparent base canvas
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))

    # The actual card dimensions are inset by padding
    card_w = width - 2 * padding
    card_h = height - 2 * padding

    # Top-left corner of the card shape within the canvas
    card_x = padding
    card_y = padding

    # 1. Draw the drop shadow
    if shadow_blur > 0 and shadow_color[3] > 0:
        shadow_img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        shadow_draw = ImageDraw.Draw(shadow_img)
        shadow_box = (
            card_x + shadow_offset[0],
            card_y + shadow_offset[1],
            card_x + card_w - 1 + shadow_offset[0],
            card_y + card_h - 1 + shadow_offset[1],
        )
        shadow_draw.rounded_rectangle(
            shadow_box,
            radius=corner_radius,
            fill=shadow_color,
        )
        shadow_img = shadow_img.filter(ImageFilter.GaussianBlur(radius=shadow_blur))
        img = Image.alpha_composite(img, shadow_img)

    # 2. Draw card fill
    fill_img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    fill_draw = ImageDraw.Draw(fill_img)
    fill_draw.rounded_rectangle(
        (card_x, card_y, card_x + card_w - 1, card_y + card_h - 1),
        radius=corner_radius,
        fill=fill_color,
    )
    img = Image.alpha_composite(img, fill_img)

    # 3. Draw refractive gradient border
    if border_width > 0:
        # Create border outline mask
        border_mask = Image.new("L", (width, height), 0)
        border_draw = ImageDraw.Draw(border_mask)
        border_draw.rounded_rectangle(
            (card_x, card_y, card_x + card_w - 1, card_y + card_h - 1),
            radius=corner_radius,
            outline=255,
            width=border_width,
        )

        # Top-left gets bright refraction; bottom-right gets soft translucent occlusion
        color_start = (border_color[0], border_color[1], border_color[2], min(255, int(border_color[3] * 1.8)))
        color_end = (border_color[0], border_color[1], border_color[2], max(0, int(border_color[3] * 0.4)))
        grad = _create_linear_gradient((width, height), color_start, color_end)

        # Paste gradient onto the border outline
        img.paste(grad, (0, 0), border_mask)

    # 4. Draw horizontal divider line (gradient fade-out at edges)
    if divider:
        div_rgba = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        div_draw = ImageDraw.Draw(div_rgba)
        # Place divider at 44% of card height
        div_y = card_y + int(card_h * 0.44)
        div_x_start = card_x + int(card_w * 0.08)
        div_x_end = card_x + int(card_w * 0.92)
        div_w = div_x_end - div_x_start

        # Draw solid divider line first
        div_draw.line(
            [(div_x_start, div_y), (div_x_end, div_y)],
            fill=border_color,
            width=2,
        )

        # Create horizontal fade-out mask (Transparent -> Opaque -> Transparent)
        div_mask_small = Image.new("L", (3, 1))
        div_mask_small.putpixel((0, 0), 0)
        div_mask_small.putpixel((1, 0), 255)
        div_mask_small.putpixel((2, 0), 0)

        div_mask = div_mask_small.resize((div_w, 2), _RESAMPLE_BILINEAR)

        # Paste the divider line with the fade mask to blend edges gracefully
        img.paste(div_rgba.crop((div_x_start, div_y, div_x_end, div_y + 2)), (div_x_start, div_y), div_mask)

    # 5. Draw progress dots at the bottom of the card shape
    if progress_dots and dot_count > 1:
        dots_rgba = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        dots_draw = ImageDraw.Draw(dots_rgba)

        dot_radius = 8
        dot_gap = 20

        # Center of the card horizontally
        center_x = width // 2

        # Bottom of the card shape
        card_bottom_y = card_y + card_h
        # Draw dots 42px above the bottom border
        dots_y = card_bottom_y - 42

        # Total width of all dots and gaps
        total_dots_width = (dot_count * 2 * dot_radius) + ((dot_count - 1) * dot_gap)
        start_x = center_x - total_dots_width // 2

        active_color = _parse_color(dot_color_active, default_alpha=230)
        inactive_color = _parse_color(dot_color_inactive, default_alpha=70)

        for idx in range(dot_count):
            cx = start_x + idx * (2 * dot_radius + dot_gap) + dot_radius
            cy = dots_y

            fill = active_color if idx == active_dot else inactive_color
            dots_draw.ellipse(
                (cx - dot_radius, cy - dot_radius, cx + dot_radius, cy + dot_radius),
                fill=fill,
            )
        img = Image.alpha_composite(img, dots_rgba)

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path, "PNG")
    return output_path


def generate_card_mask(
    width: int,
    height: int,
    output_path: str,
    corner_radius: int = 36,
) -> str:
    """Generate a grayscale mask PNG of a rounded rectangle.

    Used by FFmpeg to apply backdrop blur inside the exact card boundaries.
    """
    if not HAS_PIL:
        raise RuntimeError("PIL (Pillow) is required for card mask generation.")

    mask = _round_rect_mask((width, height), corner_radius)
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    mask.save(output_path, "PNG")
    return output_path


