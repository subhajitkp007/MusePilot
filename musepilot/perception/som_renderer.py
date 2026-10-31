# Copyright 2026 MusePilot Authors
# Licensed under the Apache License, Version 2.0
"""Set-of-Mark (SoM) visual badge compositor for SAM 3.1 masks."""

from __future__ import annotations

from PIL import Image, ImageDraw

from musepilot.contracts.schemas import MaskSet


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

            # Centroid crosshair
            cx, cy = mask.centroid_px
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

        composited = Image.alpha_composite(canvas, overlay)
        return composited.convert("RGB")
