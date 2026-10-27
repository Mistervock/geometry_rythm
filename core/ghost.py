"""Ghost Mode: лучший проход чарта как призрак для сравнения.

Что хранится (data/ghosts/<ключ>.json, запись атомарная):
  * привязка: id чарта, имя файла, отпечаток нот (notes_hash) и версия формата — по ним проверяется,
    что призрак относится именно к этим нотам;
  * итог прохода: очки, точность, ранг, комбо, оценки;
  * timeline — (время, очки, комбо) после каждого решения: по нему считается «сколько очков было у
    призрака к этому моменту»;
  * marks — (время, дорожка, оценка) каждого попадания/промаха призрака для лёгких меток на площадках.

Правила:
  * сохраняется только полный проход обычного режима без проигрыша; практика призрака не пишет;
  * новый проход заменяет старый, только если строго лучше (очки, затем точность); при равенстве остаётся старый;
  * призрак не влияет на очки, комбо и HP — это только отображение;
  * устаревший (чарт изменён), повреждённый или более новый призрак не ломает игру: игра идёт без него,
    повреждённый файл уходит в карантин, а не затирается.
Время везде в мс чарта, поэтому призрак совпадает с нотами при любой скорости практики.
"""
import bisect
import os
import re
import time

import config as C
import jsonio

FORMAT = "gr-ghost"
VERSION = 1
DIR = C.root("data", "ghosts")
MAX_POINTS = 40000

OK, NONE, STALE, CORRUPT, NEWER = "ok", "none", "stale", "corrupt", "newer"
GRADE_CODE = {"perfect": "p", "great": "g", "good": "o", "miss": "m"}


def _safe(key):
    return re.sub(r"[^0-9A-Za-zА-Яа-я_.-]+", "_", str(key))[:80] or "chart"


def keys_for(chart):
    out = []
    for k in (chart.id, chart.key):
        if k and k not in out:
            out.append(k)
    return out


def path_for(key, directory=None):
    return os.path.join(directory or DIR, _safe(key) + ".ghost.json")


class Ghost:
    def __init__(self, data):
        self.data = data
        self.timeline = data["timeline"]
        self._times = [p[0] for p in self.timeline]
        self.marks = data["marks"]
        self._mark_times = [m[0] for m in self.marks]
        self.score = data["score"]
        self.acc = data["acc"]
        self.grade = data["grade"]
        self.max_combo = data["max_combo"]

    def snapshot_at(self, t):
        """(очки, комбо) призрака к моменту t."""
        i = bisect.bisect_right(self._times, t) - 1
        if i < 0:
            return 0, 0
        return self.timeline[i][1], self.timeline[i][2]

    def marks_between(self, t0, t1):
        i0 = bisect.bisect_left(self._mark_times, t0)
        i1 = bisect.bisect_right(self._mark_times, t1)
        return self.marks[i0:i1]


#-- Проверка файла

def _num(v, lo=-1e12, hi=1e12):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and v == v and lo <= v <= hi


def validate(data):
    """Возвращает (ok, причина). Проверяет оболочку и каждую запись; ничего не исправляет молча."""
    if not isinstance(data, dict) or data.get("format") != FORMAT:
        return False, "не файл призрака"
    if not isinstance(data.get("version"), int):
        return False, "нет версии"
    for k in ("chart_id", "chart_key", "notes_hash"):
        if not isinstance(data.get(k, ""), str):
            return False, f"поле {k}"
    if not _num(data.get("score"), 0, 10 ** 9) or not _num(data.get("acc"), 0, 100):
        return False, "очки или точность"
    if not _num(data.get("max_combo"), 0, 10 ** 7) or data.get("grade") not in ("S", "A", "B", "C", "D", "F"):
        return False, "комбо или ранг"
    tl, marks = data.get("timeline"), data.get("marks")
    if not isinstance(tl, list) or not isinstance(marks, list) or len(tl) > MAX_POINTS or len(marks) > MAX_POINTS:
        return False, "timeline / marks"
    last = -1e18
    for p in tl:
        if not (isinstance(p, list) and len(p) == 3 and all(_num(x) for x in p)) or p[0] < last:
            return False, "запись timeline"
        last = p[0]
    last = -1e18
    for m in marks:
        if not (isinstance(m, list) and len(m) == 3 and _num(m[0]) and m[1] in (0, 1, 2, 3)
                and m[2] in GRADE_CODE.values()) or m[0] < last:
            return False, "запись marks"
        last = m[0]
    return True, ""


def load(chart, directory=None):
    """(Ghost | None, статус). Статус: ok / none / stale / corrupt / newer."""
    for key in keys_for(chart):
        path = path_for(key, directory)
        if not os.path.exists(path):
            continue
        res = jsonio.read(path)
        if not res.ok:
            if res.kind != jsonio.ACCESS:
                jsonio.quarantine(path)
            return None, CORRUPT
        ver = res.data.get("version") if isinstance(res.data, dict) else None
        if isinstance(ver, int) and ver > VERSION:
            return None, NEWER
        ok, _ = validate(res.data)
        if not ok:
            jsonio.quarantine(path)
            return None, CORRUPT
        if res.data["notes_hash"] != chart.notes_hash():
            return None, STALE
        return Ghost(res.data), OK
    return None, NONE


#-- Сохранение

def build(chart, outcome):
    stats = outcome["stats"]
    marks = [[round(j[5], 1), j[1], GRADE_CODE[j[3]]] for j in outcome["judgments"]]
    marks.sort(key=lambda m: m[0])
    return {
        "format": FORMAT, "version": VERSION,
        "chart_id": chart.id or "", "chart_key": chart.key or "",
        "notes_hash": chart.notes_hash(), "total": stats["total"],
        "score": int(outcome["score"]), "acc": float(outcome["acc"]), "grade": outcome["grade"],
        "max_combo": int(outcome["max_combo"]), "counts": dict(outcome["counts"]),
        "saved_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "timeline": [[round(a, 1), int(b), int(c)] for a, b, c in outcome["timeline"]][:MAX_POINTS],
        "marks": marks[:MAX_POINTS],
    }


def is_better(new, old):
    """Строго лучше: больше очков, при равенстве — выше точность. Равный результат старый не заменяет."""
    if old is None:
        return True
    return (new["score"], new["acc"]) > (old["score"], old["acc"])


def eligible(outcome):
    return bool(outcome) and not outcome.get("practice") and not outcome.get("failed") \
        and outcome.get("stats", {}).get("judged", 0) >= outcome.get("stats", {}).get("total", 1) > 0 \
        and bool(outcome.get("timeline"))


def maybe_save(chart, outcome, directory=None):
    """'saved' | 'kept' (старый лучше или равен) | 'skipped' (не подходит) | 'error'."""
    if not eligible(outcome):
        return "skipped"
    old, status = load(chart, directory)
    new = build(chart, outcome)
    if status == OK and not is_better(new, old.data):
        return "kept"
    key = chart.id or chart.key
    if not key:
        return "skipped"
    ok, _ = jsonio.try_write(path_for(key, directory), new, indent=None)
    return "saved" if ok else "error"


def delete(chart, directory=None):
    for key in keys_for(chart):
        try:
            os.remove(path_for(key, directory))
        except OSError:
            pass


#-- Показ во время игры

class View:
    """Состояние призрака для текущего момента игры. Только отображение — ничего не меняет в движке."""

    def __init__(self, ghost, section=None):
        self.ghost = ghost
        self.section = section if section and section[0] is not None else None
        self.base = ghost.snapshot_at(self.section[0] - 1)[0] if self.section else 0
        self.score = 0
        self.combo = 0
        self.recent = []

    def update(self, now):
        s, c = self.ghost.snapshot_at(now)
        self.score = max(0, s - self.base)
        self.combo = c
        self.recent = self.ghost.marks_between(now - 260, now)

    def delta(self, player_score):
        return player_score - self.score
