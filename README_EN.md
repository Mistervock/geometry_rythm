# Geometry Rhythm

**Geometry Rhythm** is a rhythm game built with Python and Pygame. Press the keys in time with the music and hit notes as they reach the judgment line.

The project is inspired by **Friday Night Funkin' (FNF)**, but it is an independent fan-made project and is not an official FNF release.

## Features

- Four note lanes.
- Timing judgments, score, combo, and health.
- Hold notes.
- A chart editor for creating and editing note charts.
- Automatic chart generation using audio analysis.

## Gameplay

Use the following keys to hit notes in the four lanes:

| Lane | Key |
|---|---|
| 1 | **D** |
| 2 | **F** |
| 3 | **J** |
| 4 | **K** |

Press the corresponding key when a note reaches the judgment line. Try to keep your combo going and avoid missing notes.

## Windows (.exe) — coming soon

A standalone **Windows `.exe` build is in development**. Once it is ready, it will be available in this repository's **Releases** section. No ready-to-download `.exe` has been published yet, so use the setup instructions below for now.

## Installation and launch

### Requirements

- Python 3
- The dependencies listed in `requirements.txt`

### Steps

1. Install Python 3 if it is not already installed.
2. Clone or download this repository.
3. Open a terminal in the project folder.
4. Install the dependencies:

   ```bash
   pip install -r requirements.txt
   ```

5. Start the game:

   **Windows**
   ```bash
   py main.py
   ```

   **Linux / macOS**
   ```bash
   python3 main.py
   ```

If the command does not work on your system, make sure Python is installed and available from your terminal.

## Music and charts

The project supports audio files in formats such as `.ogg`, `.mp3`, and `.wav` (depending on the installed audio support). You can use the chart editor to create charts, or try the automatic chart-generation feature.

Only use music and other assets that you have permission to use. Make sure you follow the relevant copyright and license terms.

## Technology

- **Python**
- **Pygame**
- Audio analysis for automatic chart generation

## Inspiration and copyright

Geometry Rhythm is an independent project inspired by Friday Night Funkin'. It is not affiliated with or endorsed by the creators of Friday Night Funkin'. Any third-party music, graphics, names, or other assets remain the property of their respective owners.

## Project status

The project is under development. Features, controls, and setup instructions may change over time.
