# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Run the app
pythonENV/Scripts/python.exe main.py

# Run all tests (unittest discovery, 145 tests)
pythonENV/Scripts/python.exe tests/run_tests.py

# Run test runner GUI
pythonENV/Scripts/python.exe tests/test_runner_ui.py

# Run a single test file
pythonENV/Scripts/python.exe -m pytest tests/test_model.py

# Run a single test case
pythonENV/Scripts/python.exe -m unittest tests.test_model.TestNote.test_name

# Install dependencies (Python 3.14 venv)
pythonENV/Scripts/pip.exe install -r requirements.txt
```

## Architecture

MVC with a central **SignalBus** (Qt Signals) that decouples all components. No component imports another component directly - all cross-component communication goes through SignalBus.

**Control flow:** UI action → Controller → modifies Model → emits Signal → UI/Notation refreshes.

**AppController** (`controller/AppController.py`) is the single wiring point that creates all components and connects their signals.

### Key layers

- **model/** - Pure Python data classes (no Qt dependency). All implement `to_dict()`/`from_dict()` for JSON serialization. Project saves as `.musiai` JSON files.
- **musicXML/** - Custom XML parser (NOT music21) using `xml.etree.ElementTree`. Handles microtones (decimal `<alter>` values), per-note dynamics, glissando. music21 crashes on microtones - that's why we have our own parser.
- **midi/** - MIDI I/O. `MidiImporter` uses music21 (MIDI has no microtones so it's fine). `MidiExporter` uses mido directly.
- **notation/** - `QGraphicsScene`/`QGraphicsItem` based rendering. Each note is a `NoteItem` (colored ellipse). Expression shown via `ZigzagItem` (instant cent shift), `CurveItem` (glide), `DurationItem` (length deviation color).
- **audio/** - `PlaybackEngine` orchestrates `Transport` (timing) + `FluidSynthPlayer` (pygame.midi output to Windows GS Wavetable Synth). Pitch bends applied per-note for cent offsets.
- **ui/** - PySide6 widgets. `NotationView` wraps the QGraphicsScene. `PropertiesPanel` edits selected note expression.
- **controller/** - `EditController` handles note selection/editing (references Model Note objects, finds corresponding NoteItems after scene refresh). `RecordingController` captures MIDI CC/pitch bend during playback and writes to current note's Expression.

### Color scheme

Velocity: yellow(0) → red(80/default) → blue(127). Duration deviation: red-yellow(shorter) → gray(standard) → blue(longer). Cent offsets: orange zigzags/curves.

## Conventions

- **One class per file, file named after class** (PascalCase): `Expression.py` contains `class Expression`.
- **Max ~200 lines per file.** Split into multiple classes if longer.
- **Model classes** always have `to_dict()` and `@classmethod from_dict(cls, data)`.
- **Logging**: `logger = logging.getLogger("musiai.module.ClassName")` at module level.
- **SignalBus** for all cross-component events - never call another component's methods directly from a different layer.
- **QGraphicsScene items** get invalidated on `scene.refresh()`. The `EditController` stores a reference to the Model `Note` (survives refresh), not the `NoteItem` (gets deleted). Use `_find_item_for_note()` to re-locate after refresh.
- PySide6 (LGPL), not PyQt6 (GPL). Import from `PySide6`, use `Signal`/`Slot` not `pyqtSignal`/`pyqtSlot`.
