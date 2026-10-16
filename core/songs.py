
#-- Импорт
import json
import os
import secrets

import pygame

import autochart
import chart as chartmod
import config as C

SONG_DIR = C.root("songs")
CHART_DIR = C.root("data", "charts")
INFO_DIR = C.root("data", "songinfo")
LEGACY_CHART = C.root("data", "chart.json")
EXTS = (".ogg", ".mp3", ".wav")


def list_songs():
    if not os.path.isdir(SONG_DIR):
        return []
    names = [f for f in os.listdir(SONG_DIR) if f.lower().endswith(EXTS)]
    return sorted(names, key=str.lower)


def title(song):
    return os.path.splitext(song)[0].replace("_", " ")


def song_path(song):
    return os.path.join(SONG_DIR, song)


def _safe(text):
    keep = [ch if ch.isalnum() or ch in "-_" else "_" for ch in text]
    return "".join(keep)[:40] or "song"


def charts_for(song):
    result = []
    if not os.path.isdir(CHART_DIR):
        return result
    for fname in os.listdir(CHART_DIR):
        if not fname.endswith(".json"):
            continue
        path = os.path.join(CHART_DIR, fname)
        try:
            ch = chartmod.Chart.load(path)
        except Exception:
            continue
        if ch.song == song:
            result.append(ch)
    result.sort(key=lambda c: c.name.lower())
    return result


def new_chart(song, name=None):
    existing = {c.name for c in charts_for(song)}
    base = name or "Чарт"
    n, final = 1, base
    while final in existing:
        n += 1
        final = f"{base} {n}"
    return chartmod.Chart(song=song, name=final)


def save_chart(ch):
    os.makedirs(CHART_DIR, exist_ok=True)
    if ch.path is None:
        ch.path = os.path.join(CHART_DIR, f"{_safe(ch.song)}__{secrets.token_hex(4)}.json")
    ch.sort()
    tmp = ch.path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(ch.to_dict(), f, ensure_ascii=False, indent=1)
    os.replace(tmp, ch.path)
    return ch.path


def delete_chart(ch):
    if ch.path and os.path.exists(ch.path):
        try:
            os.remove(ch.path)
        except OSError:
            pass


def info(song):
    os.makedirs(INFO_DIR, exist_ok=True)
    cache = os.path.join(INFO_DIR, _safe(song) + ".json")
    if os.path.exists(cache):
        try:
            with open(cache, "r", encoding="utf-8") as f:
                data = json.load(f)
            if data.get("duration_ms"):
                return data
        except Exception:
            pass
    data = None
    if autochart.AVAILABLE:
        data = autochart.energy_only(song_path(song))
    if data is None:
        try:
            length = pygame.mixer.Sound(song_path(song)).get_length()
        except Exception:
            length = 0.0
        data = {"duration_ms": int(length * 1000), "energy": [], "energy_fps": 21.5}
    try:
        with open(cache, "w", encoding="utf-8") as f:
            json.dump(data, f)
    except OSError:
        pass
    return data


def migrate_legacy():
    if not os.path.exists(LEGACY_CHART) or not os.path.exists(os.path.join(SONG_DIR, "game.ogg")):
        return
    if charts_for("game.ogg"):
        return
    try:
        with open(LEGACY_CHART, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return
    ch = chartmod.Chart.from_dict({"song": "game.ogg", "name": "Авто", "notes": data.get("notes", [])})
    save_chart(ch)
