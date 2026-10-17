
#-- Импорт
import json

import events as EV

LANES = 4
MIN_HOLD_MS = 150


class Note:
    __slots__ = ("t", "lane", "dur", "state", "hit_at", "grade", "early",
                 "held", "next_tick", "tail_ok")

    def __init__(self, t, lane, dur=0):
        self.t = int(t)
        self.lane = int(lane)
        self.dur = max(0, int(dur))
        self.state = "wait"
        self.hit_at = 0.0
        self.grade = None
        self.early = False
        self.held = False
        self.next_tick = 0.0
        self.tail_ok = False

    @property
    def end(self):
        return self.t + self.dur


class Chart:
    def __init__(self, song, name="Чарт", notes=None, path=None, events=None,
                 charter="", difficulty=1):
        self.song = song
        self.name = name
        self.charter = charter
        self.difficulty = max(1, min(5, int(difficulty)))
        self.notes = list(notes or [])
        self.events = list(events or [])
        self.path = path

    def sort(self):
        self.notes.sort(key=lambda n: (n.t, n.lane))

    def copy_notes(self):
        return [Note(n.t, n.lane, n.dur) for n in self.notes]

    def to_dict(self):
        out = []
        for n in self.notes:
            item = {"t": n.t, "lane": n.lane}
            if n.dur:
                item["d"] = n.dur
            out.append(item)
        out_data = {"version": 4, "song": self.song, "name": self.name,
                    "charter": self.charter, "difficulty": self.difficulty, "notes": out}
        if self.events:
            out_data["events"] = self.events
        return out_data

    @staticmethod
    def from_dict(data, path=None):
        notes = []
        for n in data.get("notes", []):
            try:
                t, lane = int(n["t"]), int(n["lane"])
                dur = int(n.get("d", 0))
            except (KeyError, TypeError, ValueError):
                continue
            if 0 <= lane < LANES:
                notes.append(Note(t, lane, dur))
        events = [e for e in (EV.normalize(raw) for raw in data.get("events", [])) if e is not None]
        try:
            difficulty = int(data.get("difficulty", 1))
        except (TypeError, ValueError):
            difficulty = 1
        chart = Chart(song=str(data.get("song", "")), name=str(data.get("name", "Чарт"))[:24],
                      notes=notes, path=path, events=events,
                      charter=str(data.get("charter", ""))[:40], difficulty=difficulty)
        chart.sort()
        chart.events.sort(key=lambda e: e["t"])
        return chart

    @staticmethod
    def load(path):
        with open(path, "r", encoding="utf-8") as f:
            return Chart.from_dict(json.load(f), path=path)
