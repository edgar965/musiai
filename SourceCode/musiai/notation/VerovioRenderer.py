"""VerovioRenderer - Rendert MusicXML via Verovio als SVG in QWebEngineView."""

import logging
from PySide6.QtWidgets import QGraphicsScene
from musiai.model.Piece import Piece

logger = logging.getLogger("musiai.notation.VerovioRenderer")


class VerovioRenderer:
    """Rendert ein Piece via Verovio → SVG → QWebEngineView in Scene."""

    def __init__(self):
        self._toolkit = None
        self._web_view = None  # Strong reference

    def _ensure_toolkit(self):
        if self._toolkit is not None:
            return True
        try:
            import verovio
            self._toolkit = verovio.toolkit()
            logger.info("Verovio Toolkit initialisiert")
            return True
        except ImportError:
            logger.error("Verovio nicht installiert: pip install verovio")
            return False
        except Exception as e:
            logger.error(f"Verovio Fehler: {e}")
            return False

    def render_piece(self, piece: Piece, scene: QGraphicsScene,
                     system_width: float) -> bool:
        if not self._ensure_toolkit():
            self._render_error(scene, "Verovio nicht verfügbar.")
            return False

        try:
            from musiai.musicXML.MusicXmlExporter import MusicXmlExporter
            xml_str = MusicXmlExporter().export_string(piece)

            self._toolkit.setOptions({
                "pageWidth": int(system_width * 2.5),
                "scale": 40,
                "adjustPageHeight": True,
                "breaks": "auto",
                "header": "none",
                "footer": "none",
                "svgRemoveXlink": True,
            })
            if not self._toolkit.loadData(xml_str):
                self._render_error(scene, "Verovio: MusicXML laden fehlgeschlagen.")
                return False

            page_count = self._toolkit.getPageCount()

            # Alle SVG-Seiten in ein HTML-Dokument
            svgs = []
            for page in range(1, page_count + 1):
                svgs.append(self._toolkit.renderToSVG(page))

            html = self._build_html(svgs, system_width)

            # QWebEngineView als Proxy-Widget in Scene
            from PySide6.QtWebEngineWidgets import QWebEngineView
            from PySide6.QtCore import QUrl

            view = QWebEngineView()
            view.setHtml(html, QUrl("about:blank"))

            # Höhe schätzen (jede Seite ~1000px bei scale=40)
            total_height = page_count * 1000
            view.setFixedSize(int(system_width), total_height)

            proxy = scene.addWidget(view)
            proxy.setPos(10, 10)
            self._web_view = view  # Reference halten

            scene.setSceneRect(0, 0, system_width + 40, total_height + 40)
            logger.info(f"Verovio: {page_count} Seiten gerendert (WebEngine)")
            return True

        except Exception as e:
            logger.error(f"Verovio Rendering Fehler: {e}", exc_info=True)
            self._render_error(scene, f"Verovio Fehler: {e}")
            return False

    @staticmethod
    def _build_html(svgs: list[str], width: float) -> str:
        """SVG-Seiten in HTML-Dokument verpacken."""
        parts = [
            "<!DOCTYPE html><html><head><style>",
            "body { margin: 0; padding: 10px; background: white; }",
            "svg { display: block; margin-bottom: 20px; ",
            f"max-width: {int(width - 20)}px; height: auto; }}",
            "</style></head><body>",
        ]
        for svg in svgs:
            parts.append(svg)
        parts.append("</body></html>")
        return "\n".join(parts)

    @staticmethod
    def _render_error(scene: QGraphicsScene, message: str) -> None:
        from PySide6.QtWidgets import QGraphicsSimpleTextItem
        from PySide6.QtGui import QFont, QBrush, QColor
        text = QGraphicsSimpleTextItem(message)
        text.setFont(QFont("Arial", 14))
        text.setBrush(QBrush(QColor(200, 50, 50)))
        text.setPos(50, 50)
        scene.addItem(text)
        scene.setSceneRect(0, 0, 800, 200)
