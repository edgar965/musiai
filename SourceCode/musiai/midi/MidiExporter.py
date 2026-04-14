"""MidiExporter - Exportiert das interne Model als MIDI-Datei."""

import logging
from musiai.model.Piece import Piece
from musiai.util.PitchUtils import cents_to_pitch_bend

logger = logging.getLogger("musiai.midi.MidiExporter")


class MidiExporter:
    """Exportiert ein Piece als MIDI-Datei mit Expression-Daten."""

    def export_file(self, piece: Piece, path: str) -> None:
        """Piece als MIDI-Datei schreiben."""
        import mido
        logger.info(f"Exportiere MIDI: {path}")

        mid = mido.MidiFile(ticks_per_beat=480)

        for part in piece.parts:
            track = mido.MidiTrack()
            mid.tracks.append(track)

            # Track-Name
            track.append(mido.MetaMessage("track_name", name=part.name, time=0))

            # Tempo
            tempo_us = int(60_000_000 / piece.initial_tempo)
            track.append(mido.MetaMessage("set_tempo", tempo=tempo_us, time=0))

            # Noten sammeln mit absoluten Ticks
            events = []
            abs_tick = 0

            for measure in part.measures:
                for note in measure.notes:
                    tick_start = abs_tick + int(note.start_beat * 480)
                    tick_duration = int(note.duration_beats * 480)
                    vel = note.expression.velocity
                    cents = note.expression.cent_offset
                    dev = note.expression.duration_deviation

                    # Tempo change before note (deviation != 1.0)
                    if abs(dev - 1.0) >= 0.01:
                        new_tempo = piece.initial_tempo * dev
                        tempo_us = int(60_000_000 / new_tempo)
                        events.append((tick_start, "set_tempo",
                                      {"tempo": tempo_us, "time": 0}))

                    # Pitch Bend vor der Note
                    if abs(cents) > 0.5:
                        bend = cents_to_pitch_bend(cents)
                        events.append((tick_start, "pitchwheel",
                                      {"channel": part.channel, "pitch": bend - 8192, "time": 0}))

                    # Note On
                    events.append((tick_start, "note_on",
                                  {"channel": part.channel, "note": note.pitch,
                                   "velocity": vel, "time": 0}))

                    # Note Off
                    events.append((tick_start + tick_duration, "note_off",
                                  {"channel": part.channel, "note": note.pitch,
                                   "velocity": 0, "time": 0}))

                    # Tempo reset after note
                    if abs(dev - 1.0) >= 0.01:
                        base_us = int(60_000_000 / piece.initial_tempo)
                        events.append((tick_start + tick_duration, "set_tempo",
                                      {"tempo": base_us, "time": 0}))

                    # Pitch Bend Reset
                    if abs(cents) > 0.5:
                        events.append((tick_start + tick_duration, "pitchwheel",
                                      {"channel": part.channel, "pitch": 0, "time": 0}))

                abs_tick += int(measure.duration_beats * 480)

            # Events nach Zeit sortieren und Delta-Times berechnen
            events.sort(key=lambda e: e[0])
            last_tick = 0
            for abs_t, msg_type, kwargs in events:
                delta = abs_t - last_tick
                kwargs["time"] = max(0, delta)
                if msg_type == "set_tempo":
                    track.append(mido.MetaMessage(msg_type, **kwargs))
                else:
                    track.append(mido.Message(msg_type, **kwargs))
                last_tick = abs_t

        mid.save(path)
        logger.info(f"MIDI exportiert: {path}, {len(mid.tracks)} Tracks")
