"""MusiAI Test Runner - Grafische Oberfläche für alle Testcases."""

import sys
import os
import unittest
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QTreeWidget, QTreeWidgetItem,
    QVBoxLayout, QHBoxLayout, QWidget, QPushButton, QLabel,
    QTextEdit, QSplitter, QProgressBar, QGroupBox, QHeaderView,
)
from PySide6.QtGui import QColor, QFont, QIcon, QPixmap, QPainter, QBrush, QPen
from PySide6.QtCore import Qt, QThread, Signal, QSettings


def make_circle_icon(color: QColor, size: int = 16) -> QIcon:
    """Erstellt ein rundes Ampel-Icon in der gegebenen Farbe."""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    darker = color.darker(130)
    painter.setPen(QPen(darker, 1.5))
    painter.setBrush(QBrush(color))
    painter.drawEllipse(1, 1, size - 2, size - 2)
    highlight = QColor(255, 255, 255, 90)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QBrush(highlight))
    painter.drawEllipse(4, 3, size // 3, size // 3)
    painter.end()
    return QIcon(pixmap)


def _format_duration(ms: float) -> str:
    """Dauer formatieren: ms mit Trennzeichen, oder Sekunden wenn > 1s."""
    if ms >= 1000:
        return f"{ms / 1000:,.1f}s".replace(",", ".")
    return f"{ms:,.0f}ms".replace(",", ".")


COLORS = {
    "pending": QColor(180, 180, 190),
    "running": QColor(255, 200, 0),
    "passed":  QColor(50, 180, 80),
    "failed":  QColor(220, 50, 50),
    "error":   QColor(200, 60, 200),
}

_ICON_CACHE: dict[str, QIcon] = {}


def get_status_icon(status: str) -> QIcon:
    if status not in _ICON_CACHE:
        _ICON_CACHE[status] = make_circle_icon(COLORS[status], 16)
    return _ICON_CACHE[status]


# ============================================================
#  Test Result & Worker
# ============================================================

class TestResult:
    """Ergebnis eines einzelnen Tests."""
    def __init__(self, test_id: str, test_name: str,
                 folder: str, module: str, class_name: str):
        self.test_id = test_id
        self.test_name = test_name
        self.folder = folder
        self.module = module
        self.class_name = class_name
        self.status = "pending"
        self.duration_ms = 0.0
        self.message = ""
        self.traceback_str = ""


class TestRunnerWorker(QThread):
    """Führt Tests in einem separaten Thread aus."""

    test_started = Signal(str)
    test_finished = Signal(str, str, float, str, str)
    all_finished = Signal(int, int, int, float)

    def __init__(self, suite: unittest.TestSuite):
        super().__init__()
        self.suite = suite
        self._stop_requested = False

    def request_stop(self):
        self._stop_requested = True

    def run(self):
        passed = failed = errors = 0
        start_all = time.time()

        for single in self._flatten(self.suite):
            if self._stop_requested:
                break
            test_id = str(single)
            self.test_started.emit(test_id)
            start = time.time()

            result = unittest.TestResult()
            single.run(result)
            duration = (time.time() - start) * 1000

            if result.errors:
                errors += 1
                self.test_finished.emit(
                    test_id, "error", duration,
                    "ERROR", result.errors[0][1])
            elif result.failures:
                failed += 1
                self.test_finished.emit(
                    test_id, "failed", duration,
                    "FAIL", result.failures[0][1])
            else:
                passed += 1
                self.test_finished.emit(
                    test_id, "passed", duration, "", "")

        total = (time.time() - start_all) * 1000
        self.all_finished.emit(passed, failed, errors, total)

    @staticmethod
    def _flatten(suite):
        """TestSuite rekursiv in einzelne Tests auflösen."""
        for item in suite:
            if hasattr(item, '__iter__'):
                yield from TestRunnerWorker._flatten(item)
            else:
                yield item


# ============================================================
#  UI
# ============================================================

class TestRunnerWindow(QMainWindow):
    """Hauptfenster des Test-Runners mit Ordner-Hierarchie."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("MusiAI Test Runner")
        self.resize(1100, 700)
        self.setMinimumSize(800, 500)

        self._test_results: dict[str, TestResult] = {}
        self._tree_items: dict[str, QTreeWidgetItem] = {}
        self._worker: TestRunnerWorker | None = None

        self._settings = QSettings("MusiAI", "TestRunner")
        self._setup_ui()
        self._restore_layout()
        self._discover_tests()

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(10, 10, 10, 10)

        # Toolbar
        toolbar_widget = QWidget()
        toolbar = QHBoxLayout(toolbar_widget)
        toolbar.setContentsMargins(0, 0, 0, 0)

        self._run_all_btn = QPushButton("▶  Alle Tests")
        self._run_all_btn.setMinimumHeight(36)
        self._run_all_btn.setStyleSheet(
            "QPushButton { background: #2d5aa0; color: white; "
            "font-weight: bold; border-radius: 6px; padding: 0 20px; } "
            "QPushButton:hover { background: #3a6cb8; }"
        )
        self._run_all_btn.clicked.connect(self._run_all)
        toolbar.addWidget(self._run_all_btn)

        self._run_selected_btn = QPushButton("▶  Auswahl ausführen")
        self._run_selected_btn.setMinimumHeight(36)
        self._run_selected_btn.setStyleSheet(
            "QPushButton { background: #3a6a3a; color: white; "
            "font-weight: bold; border-radius: 6px; padding: 0 20px; } "
            "QPushButton:hover { background: #4a8a4a; }"
        )
        self._run_selected_btn.clicked.connect(self._run_selected)
        toolbar.addWidget(self._run_selected_btn)

        self._stop_btn = QPushButton("■  Stopp")
        self._stop_btn.setMinimumHeight(36)
        self._stop_btn.setEnabled(False)
        self._stop_btn.setStyleSheet(
            "QPushButton { background: #a03030; color: white; "
            "font-weight: bold; border-radius: 6px; padding: 0 20px; } "
            "QPushButton:hover { background: #c04040; } "
            "QPushButton:disabled { background: #888; }"
        )
        self._stop_btn.clicked.connect(self._stop_tests)
        toolbar.addWidget(self._stop_btn)

        self._refresh_btn = QPushButton("⟳  Neu entdecken")
        self._refresh_btn.setMinimumHeight(36)
        self._refresh_btn.clicked.connect(self._discover_tests)
        toolbar.addWidget(self._refresh_btn)

        toolbar.addStretch()

        self._summary_label = QLabel("Bereit")
        self._summary_label.setStyleSheet("font-size: 14px; color: #666;")
        toolbar.addWidget(self._summary_label)

        # Progress
        self._progress = QProgressBar()
        self._progress.setMaximumHeight(8)
        self._progress.setTextVisible(False)
        self._progress.setStyleSheet(
            "QProgressBar { background: #e8e8e8; border: none; "
            "border-radius: 4px; }"
            "QProgressBar::chunk { background: #5bb974; "
            "border-radius: 4px; }"
        )

        # Vertikaler Splitter: Toolbar+Progress oben, Content unten
        self._v_splitter = QSplitter(Qt.Orientation.Vertical)

        # Oberer Bereich (Toolbar + Progress)
        top_widget = QWidget()
        top_layout = QVBoxLayout(top_widget)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(4)
        top_layout.addWidget(toolbar_widget)
        top_layout.addWidget(self._progress)
        self._v_splitter.addWidget(top_widget)

        # Horizontaler Splitter: Tree links, Details rechts
        self._splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter = self._splitter

        # Tree
        self._tree = QTreeWidget()
        self._tree.setHeaderLabels(["Status", "Test", "Dauer", "Pfad"])
        self._tree.setColumnWidth(0, 55)
        self._tree.setColumnWidth(1, 380)
        self._tree.setColumnWidth(2, 80)
        self._tree.setColumnWidth(3, 200)
        self._tree.setAlternatingRowColors(True)
        self._tree.setRootIsDecorated(True)
        self._tree.setIndentation(30)  # ~1cm Einrückung pro Ebene
        self._tree.itemClicked.connect(self._on_test_clicked)
        self._tree.setStyleSheet(
            "QTreeWidget { background: #fff; color: #333; "
            "border: 1px solid #ddd; alternate-background-color: #f8f8fc; "
            "font-size: 13px; }"
            "QTreeWidget::item:selected { background: #d0e0f8; }"
            "QHeaderView::section { background: #f0f0f5; color: #555; "
            "border: 1px solid #ddd; padding: 4px; }"
        )
        splitter.addWidget(self._tree)

        # Detail panel
        detail = QWidget()
        dl = QVBoxLayout(detail)

        self._stats_group = QGroupBox("Ergebnis")
        self._stats_group.setStyleSheet(
            "QGroupBox { color: #555; border: 1px solid #ddd; "
            "border-radius: 6px; margin-top: 8px; padding-top: 16px; "
            "background: #fafafa; }"
        )
        sl = QHBoxLayout(self._stats_group)
        self._passed_label = self._make_stat("0", "Bestanden", "#5bb974")
        self._failed_label = self._make_stat("0", "Fehlgeschlagen", "#e84040")
        self._error_label = self._make_stat("0", "Fehler", "#c850c8")
        self._time_label = self._make_stat("0ms", "Dauer", "#8ab4f8")
        sl.addWidget(self._passed_label)
        sl.addWidget(self._failed_label)
        sl.addWidget(self._error_label)
        sl.addWidget(self._time_label)
        dl.addWidget(self._stats_group)

        dl.addWidget(QLabel("Details:"))
        self._detail_text = QTextEdit()
        self._detail_text.setReadOnly(True)
        self._detail_text.setFont(QFont("Consolas", 11))
        self._detail_text.setStyleSheet(
            "QTextEdit { background: #fafafa; color: #333; "
            "border: 1px solid #ddd; border-radius: 6px; padding: 8px; }"
        )
        dl.addWidget(self._detail_text)

        splitter.addWidget(detail)
        splitter.setSizes([550, 450])

        self._v_splitter.addWidget(splitter)
        self._v_splitter.setSizes([50, 650])
        self._v_splitter.setStretchFactor(0, 0)  # Toolbar bleibt kompakt
        self._v_splitter.setStretchFactor(1, 1)  # Content dehnt sich
        layout.addWidget(self._v_splitter)

        self.setStyleSheet(
            "QMainWindow { background: #fff; } QWidget { color: #333; } "
            "QLabel { color: #444; } "
            "QPushButton { background: #f0f0f0; color: #333; "
            "border: 1px solid #ccc; border-radius: 6px; "
            "padding: 6px 16px; font-size: 13px; }"
            "QPushButton:hover { background: #e0e0e0; }"
        )

    def _make_stat(self, value: str, label: str, color: str) -> QWidget:
        w = QWidget()
        lo = QVBoxLayout(w)
        lo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v = QLabel(value)
        v.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v.setStyleSheet(f"font-size: 28px; font-weight: bold; color: {color};")
        v.setObjectName(f"stat_{label}")
        lb = QLabel(label)
        lb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lb.setStyleSheet("font-size: 11px; color: #777;")
        lo.addWidget(v)
        lo.addWidget(lb)
        return w

    def _update_stat(self, name: str, value: str):
        for w in [self._passed_label, self._failed_label,
                  self._error_label, self._time_label]:
            lbl = w.findChild(QLabel, f"stat_{name}")
            if lbl:
                lbl.setText(value)

    # ---- Layout speichern/laden ----

    def _restore_layout(self):
        """Gespeicherte Fenster- und Splitter-Positionen laden."""
        geom = self._settings.value("geometry")
        if geom:
            self.restoreGeometry(geom)
        splitter_state = self._settings.value("splitter")
        if splitter_state:
            self._splitter.restoreState(splitter_state)

    def closeEvent(self, event):
        """Fenster- und Splitter-Positionen speichern."""
        self._settings.setValue("geometry", self.saveGeometry())
        self._settings.setValue("splitter", self._splitter.saveState())
        super().closeEvent(event)

    # ---- Discovery (4-stufig: Folder → Module → Class → Method) ----

    def _discover_tests(self):
        self._tree.clear()
        self._test_results.clear()
        self._tree_items.clear()

        loader = unittest.TestLoader()
        test_dir = os.path.dirname(__file__)
        top_dir = os.path.join(test_dir, "..")
        suite = loader.discover(
            test_dir, pattern="test_*.py", top_level_dir=top_dir)

        folder_nodes: dict[str, QTreeWidgetItem] = {}
        module_nodes: dict[str, QTreeWidgetItem] = {}
        class_nodes: dict[str, QTreeWidgetItem] = {}
        count = 0

        for test in TestRunnerWorker._flatten(suite):
            test_id = str(test)
            parts = test_id.split()
            test_method = parts[0] if parts else test_id
            class_info = parts[1].strip("()") if len(parts) > 1 else ""

            # Parse: tests.data.test_model.TestNote
            ci_parts = class_info.rsplit(".", 1)
            full_module = ci_parts[0] if len(ci_parts) > 1 else "unknown"
            class_name = ci_parts[1] if len(ci_parts) > 1 else class_info

            # Ordner extrahieren: tests.data.test_model → data
            mod_parts = full_module.split(".")
            if len(mod_parts) >= 3:
                folder = mod_parts[1]
                short_module = mod_parts[-1]
            else:
                folder = "(root)"
                short_module = mod_parts[-1] if mod_parts else "unknown"

            # Folder node
            if folder not in folder_nodes:
                fi = QTreeWidgetItem(self._tree, ["", folder, "", ""])
                fi.setExpanded(True)
                f = fi.font(1)
                f.setBold(True)
                f.setPointSize(f.pointSize() + 1)
                fi.setFont(1, f)
                fi.setIcon(0, get_status_icon("pending"))
                folder_nodes[folder] = fi

            # Module node
            mod_key = f"{folder}.{short_module}"
            if mod_key not in module_nodes:
                mi = QTreeWidgetItem(folder_nodes[folder], [
                    "", short_module, "", ""])
                mi.setExpanded(False)
                f = mi.font(1)
                f.setBold(True)
                mi.setFont(1, f)
                mi.setIcon(0, get_status_icon("pending"))
                module_nodes[mod_key] = mi

            # Class node
            cls_key = f"{mod_key}.{class_name}"
            if cls_key not in class_nodes:
                ci = QTreeWidgetItem(module_nodes[mod_key], [
                    "", class_name, "", ""])
                ci.setExpanded(False)
                f = ci.font(1)
                f.setBold(True)
                ci.setFont(1, f)
                ci.setIcon(0, get_status_icon("pending"))
                class_nodes[cls_key] = ci

            # Test node
            result = TestResult(
                test_id, test_method, folder,
                short_module, class_name)
            self._test_results[test_id] = result

            item = QTreeWidgetItem(class_nodes[cls_key], [
                "", test_method, "", full_module])
            self._set_item_status(item, "pending")
            item.setData(0, Qt.ItemDataRole.UserRole, test_id)
            self._tree_items[test_id] = item
            count += 1

        self._summary_label.setText(
            f"{count} Tests in {len(folder_nodes)} Ordnern")
        self._progress.setMaximum(count)
        self._progress.setValue(0)

    # ---- Execution ----

    def _run_all(self):
        self._reset_results()
        # Suite aus gespeicherten test_ids bauen (gleiche IDs wie Discovery)
        loader = unittest.TestLoader()
        test_dir = os.path.dirname(__file__)
        top_dir = os.path.join(test_dir, "..")
        suite = loader.discover(
            test_dir, pattern="test_*.py", top_level_dir=top_dir)
        # Nur Tests ausführen die in _tree_items registriert sind
        known_ids = set(self._tree_items.keys())
        filtered = unittest.TestSuite()
        for test in TestRunnerWorker._flatten(suite):
            if str(test) in known_ids:
                filtered.addTest(test)
        self._execute_suite(filtered)

    def _run_selected(self):
        selected = self._tree.currentItem()
        if not selected:
            return

        # Sammle alle test_ids unter dem selektierten Knoten
        target_ids = set(self._collect_test_ids(selected))
        if not target_ids:
            return

        self._reset_results()
        loader = unittest.TestLoader()
        test_dir = os.path.dirname(__file__)
        top_dir = os.path.join(test_dir, "..")
        full_suite = loader.discover(
            test_dir, pattern="test_*.py", top_level_dir=top_dir)

        filtered = unittest.TestSuite()
        for test in TestRunnerWorker._flatten(full_suite):
            if str(test) in target_ids:
                filtered.addTest(test)

        self._progress.setMaximum(len(target_ids))
        self._execute_suite(filtered)

    def _collect_test_ids(self, item: QTreeWidgetItem) -> list[str]:
        """Rekursiv alle test_ids unter einem Knoten sammeln."""
        ids = []
        tid = item.data(0, Qt.ItemDataRole.UserRole)
        if tid:
            ids.append(tid)
        for i in range(item.childCount()):
            ids.extend(self._collect_test_ids(item.child(i)))
        return ids

    def _stop_tests(self):
        """Laufende Tests abbrechen."""
        if self._worker and self._worker.isRunning():
            self._worker.request_stop()
            self._summary_label.setText("Abgebrochen")
            self._summary_label.setStyleSheet(
                "font-size: 14px; color: #a03030; font-weight: bold;")
            self._run_all_btn.setEnabled(True)
            self._run_selected_btn.setEnabled(True)
            self._stop_btn.setEnabled(False)

    def _execute_suite(self, suite: unittest.TestSuite):
        self._run_all_btn.setEnabled(False)
        self._run_selected_btn.setEnabled(False)
        self._stop_btn.setEnabled(True)
        self._test_done_count = 0

        self._worker = TestRunnerWorker(suite)
        self._worker.test_started.connect(self._on_test_started)
        self._worker.test_finished.connect(self._on_test_finished)
        self._worker.all_finished.connect(self._on_all_finished)
        self._worker.start()

    def _reset_results(self):
        self._progress.setValue(0)
        for test_id, item in self._tree_items.items():
            self._set_item_status(item, "pending")
            item.setText(2, "")
            r = self._test_results[test_id]
            r.status = "pending"
            r.message = ""
            r.traceback_str = ""

        # Reset parent icons + times
        self._reset_parent_items(self._tree.invisibleRootItem())

        self._update_stat("Bestanden", "0")
        self._update_stat("Fehlgeschlagen", "0")
        self._update_stat("Fehler", "0")
        self._update_stat("Dauer", "0ms")
        self._detail_text.clear()

    def _reset_parent_items(self, parent: QTreeWidgetItem):
        for i in range(parent.childCount()):
            child = parent.child(i)
            if not child.data(0, Qt.ItemDataRole.UserRole):
                self._set_item_status(child, "pending")
                child.setText(2, "")
            self._reset_parent_items(child)

    # ---- Signal Handlers ----

    def _set_item_status(self, item: QTreeWidgetItem, status: str):
        """Status-Farbe für ein Item setzen (Icon + Hintergrund + Text)."""
        item.setIcon(0, get_status_icon(status))
        symbols = {"pending": "", "running": "...", "passed": "OK",
                   "failed": "FAIL", "error": "ERR"}
        item.setText(0, symbols.get(status, ""))
        # Hintergrundfarbe als zuverlässiger visueller Indikator
        bg = {
            "pending": QColor(245, 245, 248),
            "running": QColor(255, 248, 220),
            "passed":  QColor(230, 250, 235),
            "failed":  QColor(255, 230, 230),
            "error":   QColor(250, 230, 250),
        }
        fg = COLORS[status]
        row_bg = bg.get(status, QColor(255, 255, 255))
        for col in range(item.columnCount()):
            item.setBackground(col, QBrush(row_bg))
        item.setForeground(0, QBrush(fg))

    def _on_test_started(self, test_id: str):
        if test_id in self._tree_items:
            self._set_item_status(self._tree_items[test_id], "running")
            self._test_results[test_id].status = "running"

    def _on_test_finished(self, test_id: str, status: str,
                          duration: float, msg: str, tb: str):
        if test_id not in self._tree_items:
            return

        item = self._tree_items[test_id]
        self._set_item_status(item, status)
        item.setText(2, _format_duration(duration))

        r = self._test_results[test_id]
        r.status = status
        r.duration_ms = duration
        r.message = msg
        r.traceback_str = tb

        # Propagiere Status + Zeit nach oben (Klasse → Modul → Ordner)
        parent = item.parent()
        while parent:
            self._update_parent_status(parent)
            parent = parent.parent()

        self._test_done_count = getattr(self, '_test_done_count', 0) + 1
        self._progress.setValue(self._test_done_count)
        total = self._progress.maximum()
        self._summary_label.setText(
            f"Test {self._test_done_count} von {total}...")
        self._summary_label.setStyleSheet("font-size: 14px; color: #666;")

    def _update_parent_status(self, parent_item: QTreeWidgetItem):
        """Status und Gesamtzeit eines Elternknotens aktualisieren."""
        # Rekursiv alle test_ids unter diesem Knoten sammeln
        all_ids = self._collect_test_ids(parent_item)
        statuses = set()
        total_ms = 0.0

        for tid in all_ids:
            if tid in self._test_results:
                r = self._test_results[tid]
                statuses.add(r.status)
                total_ms += r.duration_ms

        # Status setzen
        if "error" in statuses or "failed" in statuses:
            self._set_item_status(parent_item, "failed")
        elif "running" in statuses:
            self._set_item_status(parent_item, "running")
        elif statuses and statuses <= {"passed"}:
            self._set_item_status(parent_item, "passed")

        # Zeit setzen
        if total_ms > 0:
            parent_item.setText(2, _format_duration(total_ms))

    def _on_all_finished(self, passed: int, failed: int,
                         errors: int, total_time: float):
        self._run_all_btn.setEnabled(True)
        self._run_selected_btn.setEnabled(True)
        self._stop_btn.setEnabled(False)

        self._update_stat("Bestanden", str(passed))
        self._update_stat("Fehlgeschlagen", str(failed))
        self._update_stat("Fehler", str(errors))
        self._update_stat("Dauer", _format_duration(total_time))

        total = passed + failed + errors
        if failed == 0 and errors == 0:
            self._summary_label.setText(
                f"✓ {passed}/{total} bestanden in {_format_duration(total_time)}")
            self._summary_label.setStyleSheet(
                "font-size: 14px; color: #5bb974; font-weight: bold;")
            self._progress.setStyleSheet(
                "QProgressBar { background: #e8e8e8; border: none; "
                "border-radius: 4px; } QProgressBar::chunk { "
                "background: #5bb974; border-radius: 4px; }")
        else:
            self._summary_label.setText(
                f"✗ {failed+errors} fehlgeschlagen, "
                f"{passed} bestanden in {_format_duration(total_time)}")
            self._summary_label.setStyleSheet(
                "font-size: 14px; color: #e84040; font-weight: bold;")
            self._progress.setStyleSheet(
                "QProgressBar { background: #e8e8e8; border: none; "
                "border-radius: 4px; } QProgressBar::chunk { "
                "background: #e84040; border-radius: 4px; }")

    def _on_test_clicked(self, item: QTreeWidgetItem, column: int):
        test_id = item.data(0, Qt.ItemDataRole.UserRole)
        if not test_id or test_id not in self._test_results:
            # Ordner/Modul/Klasse: Zusammenfassung zeigen
            ids = self._collect_test_ids(item)
            if not ids:
                self._detail_text.clear()
                return
            p = sum(1 for i in ids
                    if i in self._test_results
                    and self._test_results[i].status == "passed")
            f = sum(1 for i in ids
                    if i in self._test_results
                    and self._test_results[i].status == "failed")
            e = sum(1 for i in ids
                    if i in self._test_results
                    and self._test_results[i].status == "error")
            t = sum(self._test_results[i].duration_ms
                    for i in ids if i in self._test_results)
            html = f"<h3>{item.text(1)}</h3>"
            html += f"<p><b>{len(ids)}</b> Tests: "
            html += f"<span style='color:#5bb974'>{p} bestanden</span>"
            if f:
                html += f", <span style='color:#e84040'>{f} fehlgeschlagen</span>"
            if e:
                html += f", <span style='color:#c850c8'>{e} Fehler</span>"
            html += f"<br><b>Gesamtdauer:</b> {_format_duration(t)}</p>"
            self._detail_text.setHtml(html)
            return

        r = self._test_results[test_id]
        icons = {"pending": "⏳", "running": "🔄", "passed": "🟢",
                 "failed": "🔴", "error": "🟣"}
        html = f"<h3 style='color: {COLORS[r.status].name()}'>"
        html += f"{icons.get(r.status, '')} {r.test_name}</h3>"
        html += f"<p><b>Ordner:</b> {r.folder}<br>"
        html += f"<b>Modul:</b> {r.module}<br>"
        html += f"<b>Klasse:</b> {r.class_name}<br>"
        html += f"<b>Status:</b> {r.status}<br>"
        html += f"<b>Dauer:</b> {_format_duration(r.duration_ms)}</p>"

        if r.traceback_str:
            html += (f"<hr><pre style='color: #e84040; font-size: 12px;'>"
                     f"{r.traceback_str}</pre>")
        elif r.status == "passed":
            html += "<p style='color: #5bb974;'>Test erfolgreich bestanden.</p>"
        elif r.status == "pending":
            html += "<p style='color: #888;'>Test noch nicht ausgeführt.</p>"

        self._detail_text.setHtml(html)


def main():
    app = QApplication.instance() or QApplication(sys.argv)
    window = TestRunnerWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
