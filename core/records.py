
#-- Импорт
import datetime
import json
import os

import config as C

PATH = C.root("data", "records.json")
MAX_ENTRIES = 10


def load():
    try:
        with open(PATH, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except Exception:
        return []
    entries = []
    if isinstance(raw, list):
        for e in raw:
            if isinstance(e, dict) and isinstance(e.get("score"), int) and isinstance(e.get("name"), str):
                entries.append({
                    "name": e["name"][:12],
                    "score": e["score"],
                    "acc": float(e.get("acc", 0.0)),
                    "grade": str(e.get("grade", "?"))[:2],
                    "date": str(e.get("date", ""))[:10],
                })
    entries.sort(key=lambda e: (-e["score"], -e["acc"]))
    return entries[:MAX_ENTRIES]


def qualifies(score, entries=None):
    if score <= 0:
        return False
    entries = load() if entries is None else entries
    return len(entries) < MAX_ENTRIES or score > entries[-1]["score"]


def add(name, score, acc, grade, song="", chart=""):
    entries = load()
    entry = {
        "name": (name.strip() or "PLAYER")[:12],
        "score": int(score),
        "acc": round(float(acc), 2),
        "grade": grade,
        "date": datetime.date.today().isoformat(),
        "song": str(song)[:40],
        "chart": str(chart)[:24],
    }
    entries.append(entry)
    entries.sort(key=lambda e: (-e["score"], -e["acc"]))
    entries = entries[:MAX_ENTRIES]
    try:
        os.makedirs(os.path.dirname(PATH), exist_ok=True)
        with open(PATH, "w", encoding="utf-8") as f:
            json.dump(entries, f, ensure_ascii=False, indent=2)
    except OSError:
        pass
    return entries, entry
