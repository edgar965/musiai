"""MusiAI Test Runner - Grafische Oberfläche für alle Testcases."""

import sys
import os
import unittest
import time
import traceback
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QTreeWidget, QTreeWidgetItem,
    QVBoxLayout, QHBoxLayout, QWidget, QPushButton, QLabel,
    QTextEdit, QSplitter, QProgressBar, QGroupBox, QHeaderView,
)
from PySide6.QtGui import QColor, QFont, QIcon, QPixmap, QPainter, QBrush, QPen
from PySide6.QtCore import Qt, QThread, Signal, QTimer


def make_circle_icon(color: QColor, size: int = 16) -> QIcon:
    """Erstellt ein rundes Ampel-Icon in der gegebenen Farbe."""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    # Äußerer Ring (dunkler)
    darker = color.darker(130)
    painter.setPen(QPen(darker, 1.5))
    painter.setBrush(QBrush(color))
    painter.drawEllipse(1, 1, size - 2, size - 2)
    # Glanz-Effekt (heller Punkt oben links)
    highlight = QColor(255, 255, 255, 90)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QBrush(highlight))
    painter.drawEllipse(4, 3, size // 3, size // 3)
    painter.end()
    return QIcon(pixmap)


# ============================================================
#  Test Discovery & Execution
# ============================================================

class TestResult:
    """Ergebnis eines einzelnen Tests."""
    def __init__(self, test_id: str, test_name: str, module: str, class_name: str):
        self.test_id = test_id
        self.test_name = test_name
        self.module = module
        self.class_name = class_name
        self.status = "pending"   # pending, running, passed, failed, error
        self.duration_ms = 0.0
        self.message = ""
        self.traceback_str = ""


class TestRunnerWorker(QThread):
    """Führt Tests in einem separaten Thread aus."""

    test_started = Signal(str)         # test_id
    test_finished = Signal(str, str, float, str, str)  # test_id, status, duration_ms, message, traceback
    all_finished = Signal(int, int, int, float)  # passed, failed, errors, total_time

    def __init__(self, suite: unittest.TestSuite):
        super().__init__()
        self.suite = suite

    def run(self):
        passed = 0
        failed = 0
        errors = 0
        start_all = time.time()

        for test_group in self.suite:
            for test in (test_group if hasattr(test_group, '__iter__') else [test_group]):
                for single_test in (test if hasattr(test, '__iter__') else [test]):
                    test_id = str(single_test)
                    self.test_started.emit(test_id)
                    start = time.time()

                    result = unittest.TestResult()
                    single_test.run(result)
                    duration = (time.time() - start) * 1000

                    if result.errors:
                        errors += 1
                        msg = result.errors[0][1]
                        self.test_finished.emit(test_id, "error", duration, "ERROR", msg)
                    elif result.failures:
                        failed += 1
                        msg = result.failures[0][1]
                        self.test_finished.emit(test_id, "failed", duration, "FAIL", msg)
                    else:
                        passed += 1
                        self.test_finished.emit(test_id, "passed", duration, "", "")

        total_time = (time.time() - start_all) * 1000
        self.all_finished.emit(passed, failed, errors, total_time)


# ============================================================
#  UI
# ============================================================

COLORS = {
    "pending":  QColor(180, 180, 190),   # Grau
    "running":  QColor(255, 200, 0),     # Gelb
    "passed":   QColor(50, 180, 80),     # Grün
    "failed":   QColor(220, 50, 50),     # Rot
    "error":    QColor(200, 60, 200),    # Lila
}

# Icons werden beim ersten Zugriff erzeugt (braucht QApplication)
_ICON_CACHE: dict[str, QIcon] = {}

def get_status_icon(status: str) -> QIcon:
    """Gibt das Ampel-Icon für einen Status zurück (cached)."""
    if status not in _ICON_CACHE:
        _ICON_CACHE[status] = make_circle_icon(COLORS[status], 16)
    return _ICON_CACHE[status]


class TestRunnerWindow(QMainWindow):
    """Hauptfenster des Test-Runners."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("MusiAI Test Runner")
        self.resize(1100, 700)
        self.setMinimumSize(800, 500)

        self._test_results: dict[str, TestResult] = {}
        self._tree_items: dict[str, QTreeWidgetItem] = {}
        self._worker: TestRunnerWorker | None = None

        self._setup_ui()
        self._discover_tests()

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(10, 10, 10, 10)

        # Toolbar
        toolbar = QHBoxLayout()

        self._run_all_btn = QPushButton("▶  Alle Tests ausführen")
        self._run_all_btn.setMinimumHeight(36)
        self._run_all_btn.setStyleSheet(
            "QPushButton { background: #2d5aa0; color: white; font-weight: bold; "
            "border-radius: 6px; padding: 0 20px; } "
            "QPushButton:hover { background: #3a6cb8; }"
        )
        self._run_all_btn.clicked.connect(self._run_all)
        toolbar.addWidget(self._run_all_btn)

        self._run_selected_btn = QPushButton("▶  Auswahl ausführen")
        self._run_selected_btn.setMinimumHeight(36)
        self._run_selected_btn.setStyleSheet(
            "QPushButton { background: #3a6a3a; color: white; font-weight: bold; "
            "border-radius: 6px; padding: 0 20px; } "
            "QPushButton:hover { background: #4a8a4a; }"
        )
        self._run_selected_btn.clicked.connect(self._run_selected)
        toolbar.addWidget(self._run_selected_btn)

        self._refresh_btn = QPushButton("⟳  Neu entdecken")
        self._refresh_btn.setMinimumHeight(36)
        self._refresh_btn.clicked.connect(self._discover_tests)
        toolbar.addWidget(self._refresh_btn)

        toolbar.addStretch()

        # Zusammenfassung
        self._summary_label = QLabel("Bereit")
        self._summary_label.setStyleSheet("font-size: 14px; color: #666;")
        toolbar.addWidget(self._summary_label)

        layout.addLayout(toolbar)

        # Progress Bar
        self._progress = QProgressBar()
        self._progress.setMaximumHeight(8)
        self._progress.setTextVisible(False)
        self._progress.setStyleSheet(
            "QProgressBar { background: #e8e8e8; border: none; border-radius: 4px; }"
            "QProgressBar::chunk { background: #5bb974; border-radius: 4px; }"
        )
        layout.addWidget(self._progress)

        # Splitter: Tree links, Details rechts
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Test Tree
        self._tree = QTreeWidget()
        self._tree.setHeaderLabels(["Status", "Test", "Dauer", "Modul"])
        self._tree.setColumnWidth(0, 60)
        self._tree.setColumnWidth(1, 350)
        self._tree.setColumnWidth(2, 80)
        self._tree.setColumnWidth(3, 200)
        self._tree.setAlternatingRowColors(True)
        self._tree.setRootIsDecorated(True)
        self._tree.itemClicked.connect(self._on_test_clicked)
        self._tree.setStyleSheet(
            "QTreeWidget { background: #ffffff; color: #333; border: 1px solid #ddd; "
            "alternate-background-color: #f8f8fc; font-size: 13px; }"
            "QTreeWidget::item:selected { background: #d0e0f8; }"
            "QHeaderView::section { background: #f0f0f5; color: #555; "
            "border: 1px solid #ddd; padding: 4px; }"
        )
        splitter.addWidget(self._tree)

        # Detail Panel
        detail_widget = QWidget()
        detail_layout = QVBoxLayout(detail_widget)

        # Stats
        self._stats_group = QGroupBox("Ergebnis")
        self._stats_group.setStyleSheet(
            "QGroupBox { color: #555; border: 1px solid #ddd; border-radius: 6px; "
            "margin-top: 8px; padding-top: 16px; background: #fafafa; }"
        )
        stats_layout = QHBoxLayout(self._stats_group)

        self._passed_label = self._make_stat_label("0", "Bestanden", "#5bb974")
        self._failed_label = self._make_stat_label("0", "Fehlgeschlagen", "#e84040")
        self._error_label = self._make_stat_label("0", "Fehler", "#c850c8")
        self._time_label = self._make_stat_label("0ms", "Dauer", "#8ab4f8")
        stats_layout.addWidget(self._passed_label)
        stats_layout.addWidget(self._failed_label)
        stats_layout.addWidget(self._error_label)
        stats_layout.addWidget(self._time_label)
        detail_layout.addWidget(self._stats_group)

        # Test Detail
        detail_layout.addWidget(QLabel("Details:"))
        self._detail_text = QTextEdit()
        self._detail_text.setReadOnly(True)
        self._detail_text.setFont(QFont("Consolas", 11))
        self._detail_text.setStyleSheet(
            "QTextEdit { background: #fafafa; color: #333; border: 1px solid #ddd; "
            "border-radius: 6px; padding: 8px; }"
        )
        detail_layout.addWidget(self._detail_text)

        splitter.addWidget(detail_widget)
        splitter.setSizes([550, 450])
        layout.addWidget(splitter)

        # Light theme
        self.setStyleSheet(
            "QMainWindow { background: #ffffff; }"
            "QWidget { color: #333; }"
            "QGroupBox { color: #555; }"
            "QLabel { color: #444; }"
            "QPushButton { background: #f0f0f0; color: #333; border: 1px solid #ccc; "
            "border-radius: 6px; padding: 6px 16px; font-size: 13px; }"
            "QPushButton:hover { background: #e0e0e0; }"
        )

    def _make_stat_label(self, value: str, label: str, color: str) -> QWidget:
        w = QWidget()
        l = QVBoxLayout(w)
        l.setAlignment(Qt.AlignmentFlag.AlignCenter)
        val = QLabel(value)
        val.setAlignment(Qt.AlignmentFlag.AlignCenter)
        val.setStyleSheet(f"font-size: 28px; font-weight: bold; color: {color};")
        val.setObjectName(f"stat_{label}")
        lbl = QLabel(label)
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setStyleSheet("font-size: 11px; color: #777;")
        l.addWidget(val)
        l.addWidget(lbl)
        return w

    def _update_stat(self, label_name: str, value: str):
        for w in [self._passed_label, self._failed_label, self._error_label, self._time_label]:
            lbl = w.findChild(QLabel, f"stat_{label_name}")
            if lbl:
                lbl.setText(value)

    # ---- Test Discovery ----

    def _discover_tests(self):
        self._tree.clear()
        self._test_results.clear()
        self._tree_items.clear()

        loader = unittest.TestLoader()
        test_dir = os.path.dirname(__file__)
        top_dir = os.path.join(test_dir, "..")
        suite = loader.discover(test_dir, pattern="test_*.py", top_level_dir=top_dir)

        module_nodes: dict[str, QTreeWidgetItem] = {}
        class_nodes: dict[str, QTreeWidgetItem] = {}

        self._suite = suite
        count = 0

        for test_group in suite:
            for test_class_group in test_group:
                for test in (test_class_group if hasattr(test_class_group, '__iter__') else [test_class_group]):
                    test_id = str(test)
                    parts = test_id.split()
                    test_method = parts[0] if parts else test_id
                    class_info = parts[1].strip("()") if len(parts) > 1 else ""

                    # Parse module.class
                    class_parts = class_info.rsplit(".", 1)
                    module_name = class_parts[0] if len(class_parts) > 1 else "unknown"
                    class_name = class_parts[1] if len(class_parts) > 1 else class_info

                    # Module node
                    if module_name not in module_nodes:
                        mod_item = QTreeWidgetItem(self._tree, [
                            "", module_name.replace("tests.", ""), "", ""
                        ])
                        mod_item.setExpanded(True)
                        font = mod_item.font(1)
                        font.setBold(True)
                        mod_item.setFont(1, font)
                        module_nodes[module_name] = mod_item

                    # Class node
                    class_key = f"{module_name}.{class_name}"
                    if class_key not in class_nodes:
                        cls_item = QTreeWidgetItem(module_nodes[module_name], [
                            "", class_name, "", ""
                        ])
                        cls_item.setExpanded(False)
                        font = cls_item.font(1)
                        font.setBold(True)
                        cls_item.setFont(1, font)
                        class_nodes[class_key] = cls_item

                    # Test node
                    result = TestResult(test_id, test_method, module_name, class_name)
                    self._test_results[test_id] = result

                    item = QTreeWidgetItem(class_nodes[class_key], [
                        "", test_method, "", module_name
                    ])
                    item.setIcon(0, get_status_icon("pending"))
                    item.setData(0, Qt.ItemDataRole.UserRole, test_id)
                    self._tree_items[test_id] = item
                    count += 1

        self._summary_label.setText(f"{count} Tests entdeckt")
        self._progress.setMaximum(count)
        self._progress.setValue(0)

    # ---- Test Execution ----

    def _run_all(self):
        self._reset_results()
        loader = unittest.TestLoader()
        test_dir = os.path.dirname(__file__)
        top_dir = os.path.join(test_dir, "..")
        suite = loader.discover(test_dir, pattern="test_*.py", top_level_dir=top_dir)
        self._execute_suite(suite)

    def _run_selected(self):
        selected = self._tree.currentItem()
        if not selected:
            return

        test_id = selected.data(0, Qt.ItemDataRole.UserRole)
        if test_id:
            # Einzelner Test
            self._reset_results()
            loader = unittest.TestLoader()
            test_dir = os.path.dirname(__file__)
            top_dir = os.path.join(test_dir, "..")
            full_suite = loader.discover(test_dir, pattern="test_*.py", top_level_dir=top_dir)

            filtered = unittest.TestSuite()
            for group in full_suite:
                for cls_group in group:
                    for test in (cls_group if hasattr(cls_group, '__iter__') else [cls_group]):
                        if str(test) == test_id:
                            filtered.addTest(test)
            self._execute_suite(filtered)
        else:
            # Ganzes Modul/Klasse - alle Kinder
            self._run_all()

    def _execute_suite(self, suite: unittest.TestSuite):
        self._run_all_btn.setEnabled(False)
        self._run_selected_btn.setEnabled(False)

        self._worker = TestRunnerWorker(suite)
        self._worker.test_started.connect(self._on_test_started)
        self._worker.test_finished.connect(self._on_test_finished)
        self._worker.all_finished.connect(self._on_all_finished)
        self._worker.start()

    def _reset_results(self):
        self._progress.setValue(0)
        for test_id, item in self._tree_items.items():
            item.setIcon(0, get_status_icon("pending"))
            item.setText(0, "")
            item.setText(2, "")
            self._test_results[test_id].status = "pending"
            self._test_results[test_id].message = ""
            self._test_results[test_id].traceback_str = ""

        self._update_stat("Bestanden", "0")
        self._update_stat("Fehlgeschlagen", "0")
        self._update_stat("Fehler", "0")
        self._update_stat("Dauer", "0ms")
        self._detail_text.clear()

    def _on_test_started(self, test_id: str):
        if test_id in self._tree_items:
            item = self._tree_items[test_id]
            item.setIcon(0, get_status_icon("running"))
            item.setText(0, "")
            self._test_results[test_id].status = "running"

    def _on_test_finished(self, test_id: str, status: str, duration: float, msg: str, tb: str):
        if test_id in self._tree_items:
            item = self._tree_items[test_id]
            item.setIcon(0, get_status_icon(status))
            item.setText(0, "")
            item.setText(2, f"{duration:.0f}ms")

            result = self._test_results[test_id]
            result.status = status
            result.duration_ms = duration
            result.message = msg
            result.traceback_str = tb

            # Parent-Farbe updaten
            parent = item.parent()
            if parent:
                self._update_parent_status(parent)

        self._progress.setValue(self._progress.value() + 1)

    def _update_parent_status(self, parent_item: QTreeWidgetItem):
        """Elternknoten-Status basierend auf Kindern setzen."""
        statuses = set()
        for i in range(parent_item.childCount()):
            child = parent_item.child(i)
            tid = child.data(0, Qt.ItemDataRole.UserRole)
            if tid and tid in self._test_results:
                statuses.add(self._test_results[tid].status)
            # Auch Enkel prüfen (Klassen-Knoten)
            for j in range(child.childCount()):
                grandchild = child.child(j)
                tid2 = grandchild.data(0, Qt.ItemDataRole.UserRole)
                if tid2 and tid2 in self._test_results:
                    statuses.add(self._test_results[tid2].status)

        if "error" in statuses or "failed" in statuses:
            parent_item.setIcon(0, get_status_icon("failed"))
        elif statuses == {"passed"}:
            parent_item.setIcon(0, get_status_icon("passed"))
        elif "running" in statuses:
            parent_item.setIcon(0, get_status_icon("running"))

    def _on_all_finished(self, passed: int, failed: int, errors: int, total_time: float):
        self._run_all_btn.setEnabled(True)
        self._run_selected_btn.setEnabled(True)

        self._update_stat("Bestanden", str(passed))
        self._update_stat("Fehlgeschlagen", str(failed))
        self._update_stat("Fehler", str(errors))
        self._update_stat("Dauer", f"{total_time:.0f}ms")

        total = passed + failed + errors
        if failed == 0 and errors == 0:
            self._summary_label.setText(f"✓ {passed}/{total} Tests bestanden in {total_time:.0f}ms")
            self._summary_label.setStyleSheet("font-size: 14px; color: #5bb974; font-weight: bold;")
            self._progress.setStyleSheet(
                "QProgressBar { background: #e8e8e8; border: none; border-radius: 4px; }"
                "QProgressBar::chunk { background: #5bb974; border-radius: 4px; }"
            )
        else:
            self._summary_label.setText(
                f"✗ {failed + errors} fehlgeschlagen, {passed} bestanden in {total_time:.0f}ms"
            )
            self._summary_label.setStyleSheet("font-size: 14px; color: #e84040; font-weight: bold;")
            self._progress.setStyleSheet(
                "QProgressBar { background: #e8e8e8; border: none; border-radius: 4px; }"
                "QProgressBar::chunk { background: #e84040; border-radius: 4px; }"
            )

    def _on_test_clicked(self, item: QTreeWidgetItem, column: int):
        test_id = item.data(0, Qt.ItemDataRole.UserRole)
        if not test_id or test_id not in self._test_results:
            self._detail_text.clear()
            return

        result = self._test_results[test_id]
        status_labels = {"pending": "⏳", "running": "🔄", "passed": "🟢", "failed": "🔴", "error": "🟣"}
        html = f"<h3 style='color: {COLORS[result.status].name()}'>"
        html += f"{status_labels.get(result.status, '')} {result.test_name}</h3>"
        html += f"<p><b>Modul:</b> {result.module}<br>"
        html += f"<b>Klasse:</b> {result.class_name}<br>"
        html += f"<b>Status:</b> {result.status}<br>"
        html += f"<b>Dauer:</b> {result.duration_ms:.1f}ms</p>"

        if result.traceback_str:
            html += f"<hr><pre style='color: #e84040; font-size: 12px;'>{result.traceback_str}</pre>"
        elif result.status == "passed":
            html += "<p style='color: #5bb974;'>Test erfolgreich bestanden.</p>"
        elif result.status == "pending":
            html += "<p style='color: #888;'>Test noch nicht ausgeführt.</p>"

        self._detail_text.setHtml(html)


# ============================================================
#  Main
# ============================================================

def main():
    app = QApplication.instance() or QApplication(sys.argv)
    window = TestRunnerWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
