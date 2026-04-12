# Open-Source Bausteine für MusiAI

## Notation Rendering (im Browser)

### OpenSheetMusicDisplay (OSMD)
- **Was**: Rendert MusicXML als SVG im Browser
- **Repo**: https://github.com/opensheetmusicdisplay/opensheetmusicdisplay
- **Lizenz**: BSD-3
- **Vorteil**: Liest direkt MusicXML, SVG-Output = jedes Element per CSS/JS anpassbar (Farben!)
- **Nachteil**: Kein eingebauter Player, kein MIDI
- **Anpassbar**: Ja - man kann die SVG-Noten per JavaScript einfärben basierend auf Velocity
- **Beispiel**: OSMD rendert die Note → du liest `<sound dynamics>` aus → färbst das SVG-Element

### VexFlow
- **Was**: Low-level Noten-Rendering-Engine (Canvas/SVG)
- **Repo**: https://github.com/0xfe/vexflow
- **Lizenz**: MIT
- **Vorteil**: Volle Kontrolle über jeden Pixel, sehr flexibel
- **Nachteil**: Kein MusicXML-Import (braucht Konverter), mehr Programmieraufwand
- **Gut für**: Eigene Visualisierung von Grund auf

### abc.js
- **Was**: Rendert ABC-Notation (einfacheres Textformat)
- **Repo**: https://github.com/paulrosen/abcjs
- **Lizenz**: MIT
- **Vorteil**: Einfachstes Format, Player eingebaut
- **Nachteil**: ABC-Format kennt keine Micro-Expression

## MIDI im Browser

### WebMidi.js
- **Was**: Wrapper für die Web MIDI API
- **Repo**: https://github.com/djipco/webmidi
- **Lizenz**: Apache-2.0
- **Kann**: MIDI-Keyboard Input, Controller (Fader, Knobs, Pitch Wheel) lesen
- **Beispiel**: `WebMidi.inputs[0].addListener("controlchange", e => { ... })`

### Tone.js
- **Was**: Audio-Framework für den Browser (Web Audio API)
- **Repo**: https://github.com/Tonejs/Tone.js
- **Lizenz**: MIT
- **Kann**: Synthesizer, Sampler, Timing, Transport, Effekte
- **Gut für**: Abspielen der Noten mit korrektem Timing und Velocity

### JZZ.js
- **Was**: MIDI-Library (Input/Output/Files)
- **Repo**: https://github.com/nicedoc/jzz
- **Kann**: MIDI-Dateien lesen/schreiben, MIDI-Keyboard, auch Node.js

## Audio-Erkennung (Pitch Detection)

### basic-pitch (Spotify)
- **Was**: ML-basierte Polyphonic Pitch Detection
- **Repo**: https://github.com/spotify/basic-pitch
- **Lizenz**: Apache-2.0
- **Kann**: Audio → MIDI-Noten (auch Akkorde!)
- **Läuft**: Python oder als ONNX-Modell im Browser (basic-pitch-ts)

### Pitchy / Autocorrelation
- **Was**: Echtzeit Monophone Pitch Detection
- **Repo**: https://github.com/ianprime0509/pitchy
- **Kann**: Mikrofon-Input → Frequenz in Hz (auch Cent-genau)

## Desktop-Wrapper (löst Web-App Probleme)

### Tauri
- **Was**: Rust-basierter Desktop-Wrapper für Web-Apps
- **Repo**: https://github.com/nicedoc/tauri
- **Lizenz**: MIT/Apache-2.0
- **Löst**: Kein Cache-Problem, native Kontextmenüs, Dateisystem-Zugriff, Copy/Paste nativ
- **Vorteil**: App-Größe ~5MB (vs Electron ~150MB)
- **MIDI**: Über Rust-Backend direkt Zugriff auf System-MIDI

### Electron
- **Was**: Chromium + Node.js als Desktop-App
- **Repo**: https://github.com/nicedoc/electron
- **Löst**: Gleiche Probleme wie Tauri
- **Nachteil**: Groß (~150MB), RAM-hungrig
- **Vorteil**: Größeres Ökosystem, einfacher wenn man nur JS kann

## Empfohlener Stack

```
┌─────────────────────────────────────────┐
│  Tauri (Desktop Shell)                  │  ← Löst Cache, Kontextmenü, Copy/Paste
│  ┌───────────────────────────────────┐  │
│  │  OSMD (Notation Rendering)        │  │  ← MusicXML → farbige SVG-Noten
│  │  + eigene Farb-/Expression-Layer  │  │  ← Velocity→Farbe, Cents→Pfeile
│  ├───────────────────────────────────┤  │
│  │  Tone.js (Audio Playback)         │  │  ← Spielt Noten mit Expression ab
│  ├───────────────────────────────────┤  │
│  │  WebMidi.js (MIDI Input)          │  │  ← Keyboard, Fader, Pitch Wheel
│  ├───────────────────────────────────┤  │
│  │  basic-pitch (Audio→MIDI)         │  │  ← Audio-Erkennung
│  └───────────────────────────────────┘  │
│  Rust Backend: Dateisystem, MIDI I/O    │
└─────────────────────────────────────────┘

Datenformat: MusicXML (Standard, kein eigenes Format)
```
