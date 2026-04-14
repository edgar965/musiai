"""SheetMusicRecognizer - Erkennt Noten aus Bildern/PDFs."""

import logging
import os

logger = logging.getLogger("musiai.omr.SheetMusicRecognizer")


class OMRResult:
    """Ergebnis einer Notenerkennung aus Bild/PDF."""

    def __init__(self):
        self.musicxml: str = ""      # MusicXML String
        self.midi_path: str = ""     # Pfad zur erzeugten MIDI-Datei
        self.engine: str = ""
        self.success: bool = False
        self.error: str = ""


class SheetMusicRecognizer:
    """Erkennt Noten aus Bildern (PNG/JPG) und PDFs."""

    ENGINES = {
        "oemer": {
            "name": "oemer (Deep Learning)",
            "desc": "PyTorch-basierte Notenerkennung.\n"
                    "Erkennt Noten, Takte, Schlüssel aus Bildern.",
            "module": "oemer",
        },
        "audiveris": {
            "name": "Audiveris (Java)",
            "desc": "Java-basierte OMR Engine.\n"
                    "Sehr genau, braucht Java Runtime.",
            "module": None,  # External process
        },
    }

    @staticmethod
    def detect_available() -> dict[str, bool]:
        """Prüft welche Engines installiert sind."""
        result = {}
        for key, info in SheetMusicRecognizer.ENGINES.items():
            if key == "audiveris":
                result[key] = SheetMusicRecognizer._find_audiveris_dir() is not None
            elif info["module"]:
                try:
                    __import__(info["module"])
                    result[key] = True
                except ImportError:
                    result[key] = False
            else:
                result[key] = False
        return result

    @staticmethod
    def _find_audiveris() -> str | None:
        """Find Audiveris installation."""
        # Project-local install (A:\MusiAI\tools\audiveris\Audiveris\)
        project_root = os.path.normpath(
            os.path.join(os.path.dirname(__file__), "..", "..", ".."))
        paths = [
            os.path.join(project_root, "tools", "audiveris",
                         "Audiveris", "Audiveris.exe"),
            os.path.join(project_root, "tools", "audiveris",
                         "Audiveris", "bin", "Audiveris.bat"),
            os.path.join(os.environ.get("PROGRAMFILES", ""),
                         "Audiveris", "bin", "Audiveris.bat"),
            os.path.join(os.environ.get("PROGRAMFILES", ""),
                         "Audiveris", "Audiveris.exe"),
            os.path.join(os.environ.get("LOCALAPPDATA", ""),
                         "Audiveris", "Audiveris.bat"),
            os.path.join(os.environ.get("LOCALAPPDATA", ""),
                         "Audiveris", "Audiveris.exe"),
        ]
        for p in paths:
            if os.path.exists(p):
                return p
        return None

    @staticmethod
    def _find_audiveris_dir() -> str | None:
        """Find Audiveris installation directory (with app/ and runtime/)."""
        project_root = os.path.normpath(
            os.path.join(os.path.dirname(__file__), "..", "..", ".."))
        candidates = [
            os.path.join(project_root, "tools", "audiveris", "Audiveris"),
            os.path.join(os.environ.get("PROGRAMFILES", ""), "Audiveris"),
        ]
        for d in candidates:
            if os.path.isdir(os.path.join(d, "app")):
                return d
        return None

    @staticmethod
    def recognize(image_path: str, engine: str = "oemer") -> OMRResult:
        """Noten aus Bild/PDF erkennen."""
        if engine == "oemer":
            return SheetMusicRecognizer._recognize_oemer(image_path)
        elif engine == "audiveris":
            return SheetMusicRecognizer._recognize_audiveris(image_path)
        else:
            r = OMRResult()
            r.error = f"Unbekannte Engine: {engine}"
            return r

    @staticmethod
    def _recognize_oemer(image_path: str) -> OMRResult:
        """oemer: Bild → MusicXML via Deep Learning (end-to-end)."""
        result = OMRResult()
        result.engine = "oemer"
        try:
            import argparse
            import tempfile
            from oemer.ete import extract

            logger.info(f"oemer: Erkenne Noten in {image_path}")

            output_dir = tempfile.mkdtemp(prefix="musiai_oemer_")
            args = argparse.Namespace(
                img_path=image_path,
                output_path=output_dir,
                use_tf=False,
                save_cache=False,
                without_deskew=False,
            )
            output = extract(args)

            # extract() may return XML string, file path, or None
            xml_str = None
            if output and isinstance(output, str):
                if output.strip().startswith("<?xml") or "<score" in output:
                    xml_str = output
                elif os.path.isfile(output):
                    with open(output, "r", encoding="utf-8") as fh:
                        xml_str = fh.read()

            # Also check output dir for generated files
            if not xml_str:
                for f in os.listdir(output_dir):
                    if f.endswith((".musicxml", ".xml", ".mxl")):
                        fpath = os.path.join(output_dir, f)
                        with open(fpath, "r", encoding="utf-8") as fh:
                            xml_str = fh.read()
                        break

            if xml_str and ("<score" in xml_str or "<?xml" in xml_str):
                result.musicxml = xml_str
                result.success = True
                logger.info("oemer: Erkennung erfolgreich")
            else:
                result.error = (f"oemer: Kein gültiges MusicXML erzeugt"
                                f" (output={repr(output)[:100]})")
                logger.warning(result.error)
        except ImportError as e:
            result.error = f"oemer nicht installiert: {e}"
            logger.error(result.error)
        except Exception as e:
            result.error = str(e)
            logger.error(f"oemer Fehler: {e}", exc_info=True)
        return result

    @staticmethod
    def _recognize_audiveris(image_path: str) -> OMRResult:
        """Audiveris: Bild/PDF → MusicXML via Java-Prozess."""
        import subprocess
        import tempfile
        result = OMRResult()
        result.engine = "audiveris"

        audiveris_dir = SheetMusicRecognizer._find_audiveris_dir()
        if not audiveris_dir:
            result.error = "Audiveris nicht gefunden"
            return result

        try:
            output_dir = tempfile.mkdtemp(prefix="musiai_omr_")
            logger.info(f"Audiveris: {image_path} → {output_dir}")

            # Upscale image if needed (Audiveris needs ~300 DPI)
            from PIL import Image
            img = Image.open(image_path)
            w, h = img.size
            if w < 2000 or h < 2000:
                scale = max(2, 3000 // max(w, h))
                img = img.resize((w * scale, h * scale),
                                 Image.Resampling.LANCZOS)
                upscaled = os.path.join(output_dir, "upscaled.png")
                img.save(upscaled)
                actual_input = upscaled
                logger.info(f"Audiveris: Bild hochskaliert "
                            f"{w}x{h} → {w*scale}x{h*scale}")
            else:
                actual_input = image_path

            # Use bundled JRE + classpath
            java = os.path.join(audiveris_dir, "runtime", "bin", "java.exe")
            app_dir = os.path.join(audiveris_dir, "app", "*")
            if not os.path.exists(java):
                java = "java"

            proc = subprocess.run(
                [java, "-cp", app_dir, "Audiveris",
                 "-batch", "-export",
                 "-output", output_dir, actual_input],
                capture_output=True, text=True, timeout=300)

            # Audiveris may exit non-zero even with warnings
            # Check if MusicXML was actually generated before failing
            has_output = False
            for f in os.listdir(output_dir):
                if f.endswith((".xml", ".musicxml", ".mxl")):
                    has_output = True
                    break
            if proc.returncode != 0 and not has_output:
                err_msg = proc.stdout or proc.stderr or ""
                result.error = f"Audiveris: {err_msg[-300:]}"
                logger.warning(f"Audiveris exit {proc.returncode}")
                return result

            # Find generated MusicXML (may be .mxl ZIP or .xml)
            for f in os.listdir(output_dir):
                if f.endswith(".mxl"):
                    # MXL is a ZIP — extract XML from it
                    import zipfile
                    mxl_path = os.path.join(output_dir, f)
                    with zipfile.ZipFile(mxl_path) as z:
                        for n in z.namelist():
                            if n.endswith(".xml") and "META" not in n:
                                result.musicxml = z.read(n).decode("utf-8")
                                result.success = True
                                break
                    if result.success:
                        break
                elif f.endswith((".xml", ".musicxml")):
                    xml_path = os.path.join(output_dir, f)
                    try:
                        with open(xml_path, "r", encoding="utf-8") as fh:
                            result.musicxml = fh.read()
                    except UnicodeDecodeError:
                        with open(xml_path, "rb") as fh:
                            result.musicxml = fh.read().decode(
                                "latin-1", errors="replace")
                    result.success = True
                    break

            if not result.success:
                result.error = "Keine MusicXML-Ausgabe erzeugt"

        except subprocess.TimeoutExpired:
            result.error = "Audiveris Timeout (120s)"
        except Exception as e:
            result.error = str(e)
            logger.error(f"Audiveris Fehler: {e}", exc_info=True)

        return result
