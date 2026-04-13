"""MusicXML Importer - Hauptklasse für den Import."""

import logging
import os
import xml.etree.ElementTree as ET
from pathlib import Path
from musiai.model.Piece import Piece
from musiai.model.Part import Part
from musiai.model.Tempo import Tempo
from musiai.musicXML.MeasureParser import MeasureParser, MeasureParseState

logger = logging.getLogger("musiai.musicXML.importer")


class MusicXmlImporter:
    """Importiert MusicXML-Dateien mit voller Mikrotöne-/Expression-Unterstützung.

    Eigener Parser basierend auf xml.etree.ElementTree.
    Unterstützt alles was MusicXML bietet:
    - Mikrotöne (dezimale <alter>)
    - Dynamik pro Note und global
    - Tempo-Änderungen
    - Taktart-Wechsel
    - Akkorde
    - Triolen
    - Glissando/Slide
    """

    def import_file(self, path: str) -> Piece:
        """MusicXML-Datei laden und als Piece zurückgeben."""
        path = os.path.abspath(path)
        logger.info(f"Importiere MusicXML: {path}")
        if not os.path.exists(path):
            raise FileNotFoundError(f"Datei nicht gefunden: {path}")

        if path.endswith(".mxl"):
            tree = self._parse_mxl(path)
        else:
            tree = ET.parse(path)
        root = tree.getroot()

        # Namespace handling
        ns = self._detect_namespace(root)

        # Titel
        title = self._parse_title(root, ns, path)
        piece = Piece(title=title)

        # Part-Namen aus <part-list>
        part_names = self._parse_part_names(root, ns)

        # Parts parsen
        for i, part_elem in enumerate(root.findall(f"{ns}part")):
            pid = part_elem.get("id", f"P{i+1}")
            part_name = part_names.get(pid, f"Part {i+1}")
            part = self._parse_part(part_elem, part_name, i, ns, piece)
            piece.add_part(part)
            logger.info(f"  Part '{part.name}': {len(part.measures)} Takte, "
                       f"{len(part.get_all_notes())} Noten")

        # Doppelte Tempos bereinigen
        self._cleanup_tempos(piece)

        logger.info(f"Import fertig: '{piece.title}', {piece.total_measures} Takte")
        return piece

    def _parse_mxl(self, path: str) -> ET.ElementTree:
        """Komprimierte MusicXML (.mxl) entpacken und parsen."""
        import zipfile
        with zipfile.ZipFile(path) as z:
            # Versuche META-INF/container.xml für rootfile-Pfad
            try:
                with z.open("META-INF/container.xml") as cf:
                    container = ET.parse(cf).getroot()
                    ns = ""
                    if container.tag.startswith("{"):
                        ns = container.tag.split("}")[0] + "}"
                    for rf in container.iter(f"{ns}rootfile"):
                        full_path = rf.get("full-path", "")
                        if full_path and full_path in z.namelist():
                            with z.open(full_path) as f:
                                return ET.parse(f)
            except (KeyError, ET.ParseError):
                pass
            # Fallback: erste .xml Datei (nicht META-INF)
            for name in z.namelist():
                if name.endswith(".xml") and not name.startswith("META-INF"):
                    with z.open(name) as f:
                        return ET.parse(f)
        raise ValueError(f"Keine MusicXML-Datei im MXL-Archiv: {path}")

    def _detect_namespace(self, root: ET.Element) -> str:
        if root.tag.startswith("{"):
            return root.tag.split("}")[0] + "}"
        return ""

    def _parse_title(self, root: ET.Element, ns: str, path: str) -> str:
        title_elem = root.find(f".//{ns}work-title")
        if title_elem is not None and title_elem.text:
            return title_elem.text
        return Path(path).stem

    def _parse_part_names(self, root: ET.Element, ns: str) -> dict[str, str]:
        names = {}
        part_list = root.find(f"{ns}part-list")
        if part_list is not None:
            for sp in part_list.findall(f"{ns}score-part"):
                pid = sp.get("id", "")
                name_elem = sp.find(f"{ns}part-name")
                names[pid] = name_elem.text if name_elem is not None and name_elem.text else pid
        return names

    def _parse_part(self, part_elem: ET.Element, name: str, channel: int,
                    ns: str, piece: Piece) -> Part:
        part = Part(name=name, channel=channel)
        state = MeasureParseState()

        for measure_elem in part_elem.findall(f"{ns}measure"):
            measure = MeasureParser.parse(measure_elem, ns, state, piece.tempos)
            part.add_measure(measure)
            state.abs_beat += measure.duration_beats

        return part

    def _cleanup_tempos(self, piece: Piece) -> None:
        if len(piece.tempos) > 1:
            # Doppelte am Anfang entfernen
            while (len(piece.tempos) > 1
                   and piece.tempos[0].beat_position == 0
                   and piece.tempos[1].beat_position == 0):
                piece.tempos.pop(0)
