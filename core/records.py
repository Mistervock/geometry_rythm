
#-- Импорт
import datetime

import config as C
import jsonio
import validation as V

PATH = C.root("data", "records.json")
MAX_ENTRIES = 10


def load():
    raw = jsonio.load(PATH, [], expect=list)
    entries, _ = V.check_records(raw, MAX_ENTRIES)
    return entries


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
    jsonio.try_write(PATH, entries, indent=2)
    return entries, entry
