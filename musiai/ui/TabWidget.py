"""TabWidget - QTabWidget für mehrere Dokumente."""

import logging
from PySide6.QtWidgets import QTabWidget

logger = logging.getLogger("musiai.ui.TabWidget")


class TabWidget(QTabWidget):
    """Tab-Container für mehrere Notation-Dokumente."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTabsClosable(True)
        self.setMovable(True)
        self._tabs: list = []  # list[DocumentTab]
        logger.debug("TabWidget erstellt")

    def add_document_tab(self, doc_tab) -> int:
        """DocumentTab hinzufügen. Gibt den Tab-Index zurück."""
        self._tabs.append(doc_tab)
        index = self.addTab(doc_tab.notation_view, doc_tab.title)
        self.setCurrentIndex(index)
        logger.info(f"Tab hinzugefügt: '{doc_tab.title}' (Index {index})")
        return index

    def current_document_tab(self):
        """Aktuellen DocumentTab zurückgeben oder None."""
        index = self.currentIndex()
        if 0 <= index < len(self._tabs):
            return self._tabs[index]
        return None

    def document_tab_at(self, index: int):
        """DocumentTab am gegebenen Index."""
        if 0 <= index < len(self._tabs):
            return self._tabs[index]
        return None

    def close_tab(self, index: int) -> None:
        """Tab entfernen und aufräumen."""
        if 0 <= index < len(self._tabs):
            doc_tab = self._tabs.pop(index)
            self.removeTab(index)
            logger.info(f"Tab geschlossen: '{doc_tab.title}'")

    def update_tab_title(self, index: int, title: str) -> None:
        """Tab-Titel aktualisieren."""
        if 0 <= index < self.count():
            self.setTabText(index, title)

    def tab_count(self) -> int:
        return len(self._tabs)
