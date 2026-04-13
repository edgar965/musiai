"""SMuFLMetadata - Glyph metrics from Bravura metadata for precise positioning."""

import json
import logging
import os

logger = logging.getLogger("musiai.ui.midi.SMuFLMetadata")


class SMuFLMetadata:
    """SMuFL glyph metrics for precise positioning.

    All coordinates are in "staff spaces" (1 staff space = distance between
    two adjacent staff lines = LineSpace in pixels).
    """

    _data = None

    @classmethod
    def load(cls):
        """Load bravura_metadata.json (once)."""
        if cls._data is not None:
            return
        path = os.path.join(
            os.path.dirname(__file__),
            '..', '..', '..', '..',
            'media', 'fonts', 'bravura_metadata.json')
        path = os.path.abspath(path)
        if not os.path.exists(path):
            logger.warning("bravura_metadata.json not found at %s", path)
            cls._data = {}
            return
        with open(path, encoding='utf-8') as f:
            cls._data = json.load(f)
        logger.debug("Loaded SMuFL metadata (%d glyphs with bboxes)",
                     len(cls._data.get('glyphBBoxes', {})))

    @classmethod
    def get_bbox(cls, glyph_name: str) -> dict:
        """Get glyph bounding box {bBoxNE, bBoxSW} in staff spaces."""
        cls.load()
        return cls._data.get('glyphBBoxes', {}).get(glyph_name, {})

    @classmethod
    def get_anchor(cls, glyph_name: str, anchor_name: str) -> tuple:
        """Get anchor point (x, y) in staff spaces."""
        cls.load()
        anchors = cls._data.get('glyphsWithAnchors', {})
        glyph_anchors = anchors.get(glyph_name, {})
        point = glyph_anchors.get(anchor_name)
        if point is None:
            return (0.0, 0.0)
        return (point[0], point[1])

    @classmethod
    def get_advance_width(cls, glyph_name: str) -> float:
        """Get glyph advance width in staff spaces."""
        cls.load()
        return cls._data.get('glyphAdvanceWidths', {}).get(glyph_name, 0.0)

    @classmethod
    def get_engraving_default(cls, key: str, fallback=None):
        """Get an engraving default value (e.g. stemThickness)."""
        cls.load()
        return cls._data.get('engravingDefaults', {}).get(key, fallback)

    # ------------------------------------------------------------------
    # Convenience shortcuts for common anchors
    # ------------------------------------------------------------------
    @classmethod
    def stem_up_se(cls) -> tuple:
        """Stem-up attachment on filled notehead (south-east corner)."""
        return cls.get_anchor('noteheadBlack', 'stemUpSE')

    @classmethod
    def stem_down_nw(cls) -> tuple:
        """Stem-down attachment on filled notehead (north-west corner)."""
        return cls.get_anchor('noteheadBlack', 'stemDownNW')

    @classmethod
    def stem_up_se_half(cls) -> tuple:
        """Stem-up attachment on half notehead."""
        return cls.get_anchor('noteheadHalf', 'stemUpSE')

    @classmethod
    def stem_down_nw_half(cls) -> tuple:
        """Stem-down attachment on half notehead."""
        return cls.get_anchor('noteheadHalf', 'stemDownNW')

    @classmethod
    def flag_stem_up_nw(cls, flag_glyph: str) -> tuple:
        """Where a flag attaches to the stem (top of stem for up-flags)."""
        return cls.get_anchor(flag_glyph, 'stemUpNW')

    @classmethod
    def notehead_bbox(cls, glyph_name: str = 'noteheadBlack') -> tuple:
        """Return (width, height) in staff spaces for a notehead."""
        bbox = cls.get_bbox(glyph_name)
        ne = bbox.get('bBoxNE', [0, 0])
        sw = bbox.get('bBoxSW', [0, 0])
        return (ne[0] - sw[0], ne[1] - sw[1])

    # ------------------------------------------------------------------
    # Font scale: convert SMuFL staff-space coordinates to pixels
    # ------------------------------------------------------------------
    _font_scale_cache: dict = {}

    @classmethod
    def font_scale(cls, font_size_pt: int) -> float:
        """Pixels per staff space for a given Bravura font point size.

        SMuFL defines 1 staff space relative to the font em-square.
        The actual pixel size depends on the point size used for
        rendering.  We measure the noteheadBlack glyph once and cache
        the ratio: actual_pixel_width / smufl_width.
        """
        if font_size_pt in cls._font_scale_cache:
            return cls._font_scale_cache[font_size_pt]
        try:
            from PySide6.QtGui import QFont, QFontMetricsF
            font = QFont("Bravura", font_size_pt)
            fm = QFontMetricsF(font)
            br = fm.tightBoundingRect("\uE0A4")  # noteheadBlack
            smufl_w = 1.18  # noteheadBlack bbox width in staff spaces
            if br.width() > 0:
                scale = br.width() / smufl_w
            else:
                scale = float(font_size_pt) / 4.0
        except Exception:
            scale = float(font_size_pt) / 4.0
        cls._font_scale_cache[font_size_pt] = scale
        return scale

    @classmethod
    def notehead_font_size(cls, ls: int) -> int:
        """Standard Bravura font size for noteheads at a given line space."""
        return max(14, int(ls * 3.5))
