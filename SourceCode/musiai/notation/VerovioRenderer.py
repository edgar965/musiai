"""VerovioRenderer - Rendert MusicXML via Verovio zu SVG in der QGraphicsScene."""

import logging
from PySide6.QtWidgets import QGraphicsScene
from PySide6.QtCore import QByteArray
from PySide6.QtGui import QTransform
from musiai.model.Piece import Piece

logger = logging.getLogger("musiai.notation.VerovioRenderer")


class VerovioRenderer:
    """Rendert ein Piece als professionell gestochenes SVG via Verovio."""

    def __init__(self):
        self._toolkit = None
        self._renderers: list = []  # Strong refs to QSvgRenderers

    def _ensure_toolkit(self):
        """Verovio Toolkit lazy initialisieren."""
        if self._toolkit is not None:
            return True
        try:
            import verovio
            self._toolkit = verovio.toolkit()
            self._toolkit.setOptions({
                "pageWidth": 2100,
                "pageHeight": 2970,
                "scale": 40,
                "adjustPageHeight": True,
                "breaks": "auto",
                "header": "none",
                "footer": "none",
            })
            logger.info("Verovio Toolkit initialisiert")
            return True
        except ImportError:
            logger.error("Verovio nicht installiert. "
                         "Bitte: pip install verovio")
            return False
        except Exception as e:
            logger.error(f"Verovio Fehler: {e}")
            return False

    def render_piece(self, piece: Piece, scene: QGraphicsScene,
                     system_width: float) -> bool:
        """Piece via Verovio als SVG rendern und in die Scene einfuegen.

        Returns True bei Erfolg, False bei Fehler.
        """
        self._renderers.clear()

        if not self._ensure_toolkit():
            self._render_error(scene, "Verovio nicht verfuegbar. "
                               "Bitte installieren: pip install verovio")
            return False

        try:
            from musiai.musicXML.MusicXmlExporter import MusicXmlExporter
            exporter = MusicXmlExporter()
            xml_str = exporter.export_string(piece)

            self._toolkit.setOptions({
                "pageWidth": int(system_width * 2.5),
                "scale": 40,
            })
            success = self._toolkit.loadData(xml_str)
            if not success:
                self._render_error(scene, "Verovio: MusicXML konnte nicht "
                                   "geladen werden.")
                return False

            page_count = self._toolkit.getPageCount()
            y_offset = 0.0
            target_width = system_width

            from PySide6.QtSvgWidgets import QGraphicsSvgItem
            from PySide6.QtSvg import QSvgRenderer

            for page in range(1, page_count + 1):
                svg_str = self._toolkit.renderToSVG(page)
                svg_bytes = QByteArray(svg_str.encode("utf-8"))

                renderer = QSvgRenderer(svg_bytes)
                if not renderer.isValid():
                    logger.warning(f"SVG Renderer Seite {page} ungueltig")
                    continue

                # Store strong reference so GC cannot collect it
                self._renderers.append(renderer)

                item = QGraphicsSvgItem()
                item.setSharedRenderer(renderer)

                # Scale SVG to fit target width
                vb = renderer.viewBoxF()
                if vb.width() > 0:
                    scale = target_width / vb.width()
                    item.setTransform(QTransform.fromScale(scale, scale))
                    page_height = vb.height() * scale
                else:
                    page_height = vb.height()

                item.setPos(10, y_offset)
                item.setVisible(True)
                item.setZValue(0)
                scene.addItem(item)

                y_offset += page_height + 20

            total_width = target_width + 40
            total_height = y_offset + 40
            scene.setSceneRect(0, 0, total_width, total_height)
            scene.update()
            logger.info(f"Verovio: {page_count} Seiten gerendert, "
                        f"scene {total_width:.0f}x{total_height:.0f}")
            return True

        except Exception as e:
            logger.error(f"Verovio Rendering Fehler: {e}")
            self._render_error(scene, f"Verovio Fehler: {e}")
            return False

    @staticmethod
    def _render_error(scene: QGraphicsScene, message: str) -> None:
        """Fehlermeldung in die Scene schreiben."""
        from PySide6.QtWidgets import QGraphicsSimpleTextItem
        from PySide6.QtGui import QFont, QBrush, QColor
        text = QGraphicsSimpleTextItem(message)
        text.setFont(QFont("Arial", 14))
        text.setBrush(QBrush(QColor(200, 50, 50)))
        text.setPos(50, 50)
        scene.addItem(text)
        scene.setSceneRect(0, 0, 800, 200)
