# Copyright 2026 MusePilot Authors
# Licensed under the Apache License, Version 2.0
"""Set-of-Mark (SoM) visual badge compositor and PPT-style laser pointer for SAM 3.1 masks."""

from __future__ import annotations

from PIL import Image, ImageDraw, ImageFont

from musepilot.contracts.schemas import MaskSet


def _get_font(size: int = 12, bold: bool = False) -> ImageFont.ImageFont:
    """Return a clean truetype font if available on macOS, falling back to PIL default."""
    try:
        font_path = "/System/Library/Fonts/HelveticaNeue.ttc"
        return ImageFont.truetype(font_path, size, index=1 if bold else 0)
    except Exception:
        try:
            return ImageFont.load_default(size=size)
        except Exception:
            return ImageFont.load_default()


def draw_ppt_laser_pointer(
    draw: ImageDraw.ImageDraw,
    cx: int,
    cy: int,
    action_label: str,
    target_detail: str,
    laser_color: tuple[int, int, int] = (255, 45, 85),  # Electric Keynote Red
    font_bold: ImageFont.ImageFont | None = None,
    font_mono: ImageFont.ImageFont | None = None,
    max_w: int = 1280,
) -> None:
    """Draw an authentic PowerPoint-style laser pointer with concentric glow rings and annotation callout."""
    font_b = font_bold or _get_font(11, bold=True)
    font_m = font_mono or _get_font(10, bold=False)

    r, g, b = laser_color

    # Concentric glowing laser ripple rings
    draw.ellipse([cx - 28, cy - 28, cx + 28, cy + 28], outline=(r, g, b, 75), width=1)
    draw.ellipse([cx - 18, cy - 18, cx + 18, cy + 18], outline=(r, g, b, 150), width=2)
    draw.ellipse([cx - 10, cy - 10, cx + 10, cy + 10], fill=(r, g, b, 210))
    draw.ellipse([cx - 4, cy - 4, cx + 4, cy + 4], fill=(255, 255, 255, 255))

    # Crosshair precision ticks
    draw.line([(cx - 26, cy), (cx - 12, cy)], fill=(r, g, b, 220), width=2)
    draw.line([(cx + 12, cy), (cx + 26, cy)], fill=(r, g, b, 220), width=2)
    draw.line([(cx, cy - 26), (cx, cy - 12)], fill=(r, g, b, 220), width=2)
    draw.line([(cx, cy + 12), (cx, cy + 26)], fill=(r, g, b, 220), width=2)

    # Calculate callout pill anchor position (flip if close to right edge)
    flip_x = (cx + 270) > max_w
    pill_w = 246
    pill_h = 36
    pill_x = cx - pill_w - 24 if flip_x else cx + 34
    pill_y = max(12, cy - 24)

    # Leader line from laser to callout pill
    line_start = (cx - 10, cy - 10) if flip_x else (cx + 10, cy - 10)
    line_end = (pill_x + pill_w, pill_y + pill_h // 2) if flip_x else (pill_x, pill_y + pill_h // 2)
    draw.line([line_start, line_end], fill=(r, g, b, 220), width=2)

    # Annotation Callout Pill with subtle drop shadow
    draw.rounded_rectangle(
        [pill_x + 2, pill_y + 2, pill_x + pill_w + 2, pill_y + pill_h + 2],
        radius=8,
        fill=(5, 10, 18, 160),
    )
    draw.rounded_rectangle(
        [pill_x, pill_y, pill_x + pill_w, pill_y + pill_h],
        radius=8,
        fill=(15, 23, 42, 245),
        outline=(r, g, b, 240),
        width=2,
    )
    # Title / Action line
    draw.text((pill_x + 10, pill_y + 4), action_label, fill=(255, 255, 255, 255), font=font_b)
    # Subtitle / Coordinate line
    draw.text((pill_x + 10, pill_y + 19), target_detail, fill=(167, 243, 208, 255), font=font_m)


class SetOfMarkRenderer:
    """Composites neon SAM 3.1 polygons, centroids, and numbered ID badges onto frames."""

    PALETTE: tuple[tuple[int, int, int], ...] = (
        (56, 189, 248),  # Cyan
        (168, 85, 247),  # Purple
        (251, 146, 60),  # Orange
        (52, 211, 153),  # Emerald
        (244, 63, 94),  # Rose
    )

    def render_som_overlay(
        self,
        base_image: Image.Image,
        mask_set: MaskSet,
        active_target_mask_id: int | None = None,
        verified_mask_ids: set[int] | None = None,
    ) -> Image.Image:
        """Return a new RGB image with Set-of-Mark badges and target highlights."""
        verified_ids = verified_mask_ids or set()
        canvas = base_image.convert("RGBA")
        overlay = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        # Detect whether target is Android (portrait phone display)
        is_android = mask_set.height_px > mask_set.width_px

        target_laser_data: tuple[int, int, str, str, tuple[int, int, int]] | None = None

        for mask in mask_set.masks:
            is_target = mask.mask_id == active_target_mask_id
            is_verified = mask.mask_id in verified_ids
            base_rgb = (
                (16, 235, 145)
                if is_target
                else (
                    (34, 197, 94)
                    if is_verified
                    else self.PALETTE[(mask.mask_id - 1) % len(self.PALETTE)]
                )
            )

            x1, y1, x2, y2 = mask.bbox
            fill_alpha = 70 if is_target else 32
            border_width = 4 if is_target else 2

            # Semi-transparent mask fill + neon border
            draw.rectangle(
                [x1, y1, x2, y2],
                fill=(*base_rgb, fill_alpha),
                outline=(*base_rgb, 245),
                width=border_width,
            )

            cx, cy = mask.centroid_px

            if is_target and not is_android:
                # Prepare PPT laser pointer on active simulation target
                tag = mask.semantic_tag.lower()
                if "slider" in tag:
                    act_txt = f"✦ ACTUATION: DRAG [MASK #{mask.mask_id:02d}]"
                    detail = f"Centroid: ({cx}, {cy}) • Zero-Coord Slider Tune"
                    color = (255, 45, 85)
                elif "toggle" in tag or "switch" in tag:
                    act_txt = f"✦ ACTUATION: CLICK [MASK #{mask.mask_id:02d}]"
                    detail = f"Centroid: ({cx}, {cy}) • Zero-Coord Toggle"
                    color = (16, 235, 145)
                elif "input" in tag or "summary" in tag:
                    act_txt = f"✦ ACTUATION: TYPE [MASK #{mask.mask_id:02d}]"
                    detail = f"Centroid: ({cx}, {cy}) • Keystroke Ingest"
                    color = (6, 182, 212)
                elif "dismiss" in tag or "modal" in tag:
                    act_txt = f"✦ AUTONOMOUS REPLAN [MASK #{mask.mask_id:02d}]"
                    detail = f"Centroid: ({cx}, {cy}) • Self-Healing Dismiss"
                    color = (255, 45, 85)
                else:
                    act_txt = f"✦ ACTUATION: CLICK [MASK #{mask.mask_id:02d}]"
                    detail = f"Centroid: ({cx}, {cy}) • Zero-Coord Centroid"
                    color = (255, 45, 85)
                target_laser_data = (cx, cy, act_txt, detail, color)
            else:
                # Standard centroid crosshair
                draw.ellipse(
                    [cx - 5, cy - 5, cx + 5, cy + 5],
                    fill=(255, 255, 255, 255),
                    outline=(*base_rgb, 255),
                )

            # High-contrast Set-of-Mark badge pill at top-left of mask
            badge_label = f"[{mask.mask_id:02d}]"
            if is_verified:
                badge_label += " OK"
            badge_w = 58 if is_verified else 38
            badge_h = 22
            bx1 = max(4, x1)
            by1 = max(4, y1 - badge_h - 2)
            draw.rectangle(
                [bx1, by1, bx1 + badge_w, by1 + badge_h],
                fill=(*base_rgb, 245),
                outline=(10, 15, 25, 255),
                width=1,
            )
            draw.text((bx1 + 5, by1 + 4), badge_label, fill=(10, 15, 25, 255))

        # Render laser pointer on top of all masks so it is never occluded
        if target_laser_data is not None:
            lcx, lcy, lact, ldet, lcol = target_laser_data
            draw_ppt_laser_pointer(
                draw=draw,
                cx=lcx,
                cy=lcy,
                action_label=lact,
                target_detail=ldet,
                laser_color=lcol,
                max_w=canvas.size[0],
            )

        composited = Image.alpha_composite(canvas, overlay)
        return composited.convert("RGB")
