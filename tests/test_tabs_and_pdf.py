"""Tests für Tabs, PDF-Engine-Infrastruktur und SettingsDialog."""

import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# =============================================================================
# DocumentTab
# =============================================================================

class TestDocumentTab(unittest.TestCase):

    def test_title_from_piece(self):
        from musiai.ui.DocumentTab import DocumentTab
        piece = _make_piece("Mein Stück")
        tab = DocumentTab(piece, None, None, None)
        self.assertEqual(tab.title, "Mein Stück")

    def test_title_from_file_path(self):
        from musiai.ui.DocumentTab import DocumentTab
        tab = DocumentTab(None, None, None, None, file_path="/tmp/song.mid")
        self.assertEqual(tab.title, "song.mid")

    def test_title_default(self):
        from musiai.ui.DocumentTab import DocumentTab
        tab = DocumentTab(None, None, None, None)
        self.assertEqual(tab.title, "Unbenannt")

    def test_title_piece_priority(self):
        from musiai.ui.DocumentTab import DocumentTab
        piece = _make_piece("Piece Title")
        tab = DocumentTab(piece, None, None, None, file_path="/tmp/other.mid")
        self.assertEqual(tab.title, "Piece Title")

    def test_attributes(self):
        from musiai.ui.DocumentTab import DocumentTab
        tab = DocumentTab("p", "s", "v", "e", "/path", "midi")
        self.assertEqual(tab.piece, "p")
        self.assertEqual(tab.notation_scene, "s")
        self.assertEqual(tab.notation_view, "v")
        self.assertEqual(tab.edit_controller, "e")
        self.assertEqual(tab.file_path, "/path")
        self.assertEqual(tab.file_type, "midi")


# =============================================================================
# TabWidget (benötigt QApplication)
# =============================================================================

class TestTabWidget(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        _ensure_qapp()

    def test_add_and_current(self):
        from musiai.ui.TabWidget import TabWidget
        from musiai.ui.DocumentTab import DocumentTab
        tw = TabWidget()

        tab1 = DocumentTab(_make_piece("A"), None, _make_widget(), None)
        tab2 = DocumentTab(_make_piece("B"), None, _make_widget(), None)

        idx1 = tw.add_document_tab(tab1)
        idx2 = tw.add_document_tab(tab2)

        self.assertEqual(idx1, 0)
        self.assertEqual(idx2, 1)
        self.assertEqual(tw.tab_count(), 2)
        self.assertIs(tw.current_document_tab(), tab2)  # Letzter Tab aktiv

    def test_close_tab(self):
        from musiai.ui.TabWidget import TabWidget
        from musiai.ui.DocumentTab import DocumentTab
        tw = TabWidget()

        tab = DocumentTab(_make_piece("X"), None, _make_widget(), None)
        tw.add_document_tab(tab)
        self.assertEqual(tw.tab_count(), 1)

        tw.close_tab(0)
        self.assertEqual(tw.tab_count(), 0)
        self.assertIsNone(tw.current_document_tab())

    def test_document_tab_at(self):
        from musiai.ui.TabWidget import TabWidget
        from musiai.ui.DocumentTab import DocumentTab
        tw = TabWidget()

        tab = DocumentTab(_make_piece("Y"), None, _make_widget(), None)
        tw.add_document_tab(tab)

        self.assertIs(tw.document_tab_at(0), tab)
        self.assertIsNone(tw.document_tab_at(5))
        self.assertIsNone(tw.document_tab_at(-1))

    def test_update_title(self):
        from musiai.ui.TabWidget import TabWidget
        from musiai.ui.DocumentTab import DocumentTab
        tw = TabWidget()

        tab = DocumentTab(_make_piece("Alt"), None, _make_widget(), None)
        tw.add_document_tab(tab)
        tw.update_tab_title(0, "Neu")
        self.assertEqual(tw.tabText(0), "Neu")


# =============================================================================
# PdfEngineConfig
# =============================================================================

class TestPdfEngineConfig(unittest.TestCase):

    def test_import_engines_returns_dict(self):
        from musiai.pdf.PdfEngineConfig import PdfEngineConfig
        result = PdfEngineConfig.detect_import_engines()
        self.assertIsInstance(result, dict)
        self.assertIn("audiveris", result)
        self.assertIn("oemer", result)
        self.assertIn("pdf2musicxml", result)
        for v in result.values():
            self.assertIsInstance(v, bool)

    def test_export_engines_returns_dict(self):
        from musiai.pdf.PdfEngineConfig import PdfEngineConfig
        result = PdfEngineConfig.detect_export_engines()
        self.assertIsInstance(result, dict)
        self.assertIn("lilypond", result)
        self.assertIn("musescore", result)
        self.assertIn("reportlab", result)
        for v in result.values():
            self.assertIsInstance(v, bool)

    def test_engine_info_keys(self):
        from musiai.pdf.PdfEngineConfig import PdfEngineConfig
        for key, info in PdfEngineConfig.IMPORT_ENGINES.items():
            self.assertIn("name", info)
            self.assertIn("desc", info)
        for key, info in PdfEngineConfig.EXPORT_ENGINES.items():
            self.assertIn("name", info)
            self.assertIn("desc", info)

    def test_check_command_nonexistent(self):
        from musiai.pdf.PdfEngineConfig import PdfEngineConfig
        result = PdfEngineConfig._check_command(["nonexistent_command_xyz"])
        self.assertFalse(result)


# =============================================================================
# PdfImportWorker
# =============================================================================

class TestPdfImportWorker(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        _ensure_qapp()

    def test_init(self):
        from musiai.pdf.PdfImportWorker import PdfImportWorker
        worker = PdfImportWorker("audiveris", "/tmp/test.pdf", "/tmp/out")
        self.assertEqual(worker._engine, "audiveris")
        self.assertEqual(worker._pdf_path, "/tmp/test.pdf")
        self.assertEqual(worker._output_dir, "/tmp/out")

    def test_unknown_engine_emits_error(self):
        from musiai.pdf.PdfImportWorker import PdfImportWorker
        worker = PdfImportWorker("unknown_engine", "/tmp/test.pdf", "/tmp/out")
        errors = []
        worker.error.connect(errors.append)
        worker.run()
        self.assertTrue(len(errors) > 0)
        self.assertIn("Unbekannte Engine", errors[0])

    def test_pdf2musicxml_not_implemented(self):
        from musiai.pdf.PdfImportWorker import PdfImportWorker
        worker = PdfImportWorker("pdf2musicxml", "/tmp/test.pdf", "/tmp/out")
        errors = []
        worker.error.connect(errors.append)
        worker.run()
        self.assertTrue(len(errors) > 0)


# =============================================================================
# PdfExportWorker
# =============================================================================

class TestPdfExportWorker(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        _ensure_qapp()

    def test_init(self):
        from musiai.pdf.PdfExportWorker import PdfExportWorker
        worker = PdfExportWorker("lilypond", "/tmp/in.musicxml", "/tmp/out.pdf")
        self.assertEqual(worker._engine, "lilypond")
        self.assertEqual(worker._musicxml_path, "/tmp/in.musicxml")
        self.assertEqual(worker._output_path, "/tmp/out.pdf")

    def test_unknown_engine_emits_error(self):
        from musiai.pdf.PdfExportWorker import PdfExportWorker
        worker = PdfExportWorker("unknown", "/tmp/in.musicxml", "/tmp/out.pdf")
        errors = []
        worker.error.connect(errors.append)
        worker.run()
        self.assertTrue(len(errors) > 0)
        self.assertIn("Unbekannte Engine", errors[0])


# =============================================================================
# SettingsDialog PDF Tab
# =============================================================================

class TestSettingsDialogPdfTab(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        _ensure_qapp()

    def test_has_pdf_tab(self):
        from musiai.ui.SettingsDialog import SettingsDialog
        dialog = SettingsDialog()
        tab_titles = [dialog._tabs.tabText(i) for i in range(dialog._tabs.count())]
        self.assertIn("PDF", tab_titles)

    def test_has_three_tabs(self):
        from musiai.ui.SettingsDialog import SettingsDialog
        dialog = SettingsDialog()
        self.assertEqual(dialog._tabs.count(), 3)

    def test_pdf_import_engines_exist(self):
        from musiai.ui.SettingsDialog import SettingsDialog
        dialog = SettingsDialog()
        self.assertIn("audiveris", dialog._pdf_import_engines)
        self.assertIn("oemer", dialog._pdf_import_engines)
        self.assertIn("pdf2musicxml", dialog._pdf_import_engines)

    def test_pdf_export_engines_exist(self):
        from musiai.ui.SettingsDialog import SettingsDialog
        dialog = SettingsDialog()
        self.assertIn("lilypond", dialog._pdf_export_engines)
        self.assertIn("musescore", dialog._pdf_export_engines)
        self.assertIn("reportlab", dialog._pdf_export_engines)

    def test_selected_pdf_import_engine_property(self):
        from musiai.ui.SettingsDialog import SettingsDialog
        dialog = SettingsDialog()
        result = dialog.selected_pdf_import_engine
        self.assertIsInstance(result, str)

    def test_selected_pdf_export_engine_property(self):
        from musiai.ui.SettingsDialog import SettingsDialog
        dialog = SettingsDialog()
        result = dialog.selected_pdf_export_engine
        self.assertIsInstance(result, str)


# =============================================================================
# Constants
# =============================================================================

class TestConstants(unittest.TestCase):

    def test_pdf_extensions(self):
        from musiai.util.Constants import PDF_EXTENSIONS
        self.assertIn(".pdf", PDF_EXTENSIONS)

    def test_existing_extensions_unchanged(self):
        from musiai.util.Constants import MIDI_EXTENSIONS, MUSICXML_EXTENSIONS
        self.assertIn(".mid", MIDI_EXTENSIONS)
        self.assertIn(".musicxml", MUSICXML_EXTENSIONS)


# =============================================================================
# SignalBus Tab Signals
# =============================================================================

class TestSignalBusTabSignals(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        _ensure_qapp()

    def test_tab_activated_signal(self):
        from musiai.util.SignalBus import SignalBus
        bus = SignalBus()
        received = []
        bus.tab_activated.connect(received.append)
        bus.tab_activated.emit("test_tab")
        self.assertEqual(received, ["test_tab"])

    def test_tab_closed_signal(self):
        from musiai.util.SignalBus import SignalBus
        bus = SignalBus()
        received = []
        bus.tab_closed.connect(received.append)
        bus.tab_closed.emit(42)
        self.assertEqual(received, [42])


# =============================================================================
# Toolbar PDF Signals
# =============================================================================

class TestToolbarPdfSignals(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        _ensure_qapp()

    def test_import_pdf_signal(self):
        from musiai.ui.Toolbar import Toolbar
        tb = Toolbar()
        self.assertTrue(hasattr(tb, "import_pdf_clicked"))
        received = []
        tb.import_pdf_clicked.connect(lambda: received.append(True))
        tb.import_pdf_clicked.emit()
        self.assertEqual(len(received), 1)

    def test_export_pdf_signal(self):
        from musiai.ui.Toolbar import Toolbar
        tb = Toolbar()
        self.assertTrue(hasattr(tb, "export_pdf_clicked"))
        received = []
        tb.export_pdf_clicked.connect(lambda: received.append(True))
        tb.export_pdf_clicked.emit()
        self.assertEqual(len(received), 1)


# =============================================================================
# Helpers
# =============================================================================

_qapp = None

def _ensure_qapp():
    global _qapp
    if _qapp is None:
        from PySide6.QtWidgets import QApplication
        _qapp = QApplication.instance() or QApplication(sys.argv)

def _make_piece(title="Test"):
    from musiai.model.Piece import Piece
    return Piece(title)

def _make_widget():
    from PySide6.QtWidgets import QWidget
    return QWidget()


if __name__ == "__main__":
    unittest.main()
