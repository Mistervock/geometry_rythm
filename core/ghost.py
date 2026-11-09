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
import modifiers as MD


_busy = False


def _t(text):
    """Перевод сообщения. Импорт локальный (i18n тянет settings, а settings читает файлы через этот модуль).
    Повторный вход возвращает русский текст — так цикл settings → jsonio → _t не образуется."""
    global _busy
    if _busy:
        return text
    _busy = True
    try:
        from i18n import t
        return t(text)
    except Exception:
        return text
    finally:
        _busy = False

FORMAT = "gr-ghost"
VERSION = 1
DIR = C.root("data", "ghosts")
IMPORT_DIR = C.root("data", "ghosts", "import")
EXPORT_DIR = C.root("data", "ghosts", "export")
CHOICE_PATH = C.root("data", "ghost_choice.json")
CHOICE_OWN, CHOICE_NONE = "own", "none"
IMPORT_PREFIX = "import:"
MAX_POINTS = 40000

OK, NONE, STALE, CORRUPT, NEWER, OTHER_MODS = "ok", "none", "stale", "corrupt", "newer", "other_mods"
GRADE_CODE = {"perfect": "p", "great": "g", "good": "o", "miss": "m"}


def _safe(key):
    return re.sub(r"[^0-9A-Za-zА-Яа-я_.-]+", "_", str(key))[:80] or "chart"


def keys_for(chart, mods=()):
    sfx = MD.suffix(mods)
    out = []
    for k in (chart.id, chart.key):
        if k and k + sfx not in out:
            out.append(k + sfx)
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
        return False, _t("не файл призрака")
    if not isinstance(data.get("version"), int):
        return False, _t("нет версии")
    for k in ("chart_id", "chart_key", "notes_hash", "mods", "chart_name"):
        if not isinstance(data.get(k, ""), str):
            return False, f"{_t('поле')} {k}"
    if not _num(data.get("score"), 0, 10 ** 9) or not _num(data.get("acc"), 0, 100):
        return False, _t("очки или точность")
    if not _num(data.get("max_combo"), 0, 10 ** 7) or data.get("grade") not in ("S", "A", "B", "C", "D", "F"):
        return False, _t("комбо или ранг")
    tl, marks = data.get("timeline"), data.get("marks")
    if not isinstance(tl, list) or not isinstance(marks, list) or len(tl) > MAX_POINTS or len(marks) > MAX_POINTS:
        return False, "timeline / marks"
    last = -1e18
    for p in tl:
        if not (isinstance(p, list) and len(p) == 3 and all(_num(x) for x in p)) or p[0] < last:
            return False, _t("запись timeline")
        last = p[0]
    last = -1e18
    for m in marks:
        if not (isinstance(m, list) and len(m) == 3 and _num(m[0]) and m[1] in (0, 1, 2, 3)
                and m[2] in GRADE_CODE.values()) or m[0] < last:
            return False, _t("запись marks")
        last = m[0]
    return True, ""


def load_file(path, chart, mods=(), quarantine=False):
    """(Ghost | None, статус) для одного файла призрака.

    quarantine — убирать ли испорченный файл в карантин (так поступаем только со своими призраками;
    файлы из папки импорта принадлежат игроку и не трогаются)."""
    if not os.path.exists(path):
        return None, NONE
    res = jsonio.read(path)
    if not res.ok:
        if quarantine and res.kind != jsonio.ACCESS:
            jsonio.quarantine(path)
        return None, CORRUPT
    ver = res.data.get("version") if isinstance(res.data, dict) else None
    if isinstance(ver, int) and ver > VERSION:
        return None, NEWER
    ok, _ = validate(res.data)
    if not ok:
        if quarantine:
            jsonio.quarantine(path)
        return None, CORRUPT
    if res.data.get("notes_hash") != chart.notes_hash():
        return None, STALE
    if res.data.get("mods", "") != MD.suffix(mods):
        return None, OTHER_MODS
    return Ghost(res.data), OK


def load(chart, directory=None, mods=()):
    """(Ghost | None, статус) свой призрак чарта для набора модификаторов."""
    for key in keys_for(chart, mods):
        path = path_for(key, directory)
        if os.path.exists(path):
            return load_file(path, chart, mods, quarantine=True)
    return None, NONE


#-- Сохранение

def build(chart, outcome):
    stats = outcome["stats"]
    marks = [[round(j[5], 1), j[1], GRADE_CODE[j[3]]] for j in outcome["judgments"]]
    marks.sort(key=lambda m: m[0])
    return {
        "format": FORMAT, "version": VERSION,
        "chart_id": chart.id or "", "chart_key": chart.key or "",
        "notes_hash": chart.notes_hash(), "total": stats["total"], "mods": MD.suffix(outcome.get("mods", [])),
        "chart_name": str(chart.name or "")[:80],
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
    mods = outcome.get("mods", [])
    old, status = load(chart, directory, mods)
    new = build(chart, outcome)
    if status == OK and not is_better(new, old.data):
        return "kept"
    key = chart.id or chart.key
    if not key:
        return "skipped"
    ok, _ = jsonio.try_write(path_for(key + MD.suffix(mods), directory), new, indent=None)
    return "saved" if ok else "error"


def _plain(name):
    return bool(name) and os.path.basename(name) == name and name.endswith(".ghost.json")


def import_names(directory=None):
    try:
        return sorted(n for n in os.listdir(directory or IMPORT_DIR) if _plain(n))
    except OSError:
        return []


def inspect_imports(chart, mods=(), directory=None):
    """[(имя файла, статус, Ghost | None)] для файлов папки импорта. Файлы не меняются и не переносятся."""
    folder = directory or IMPORT_DIR
    out = []
    for name in import_names(folder):
        g, status = load_file(os.path.join(folder, name), chart, mods)
        out.append((name, status, g))
    return out


def export_own(chart, mods=(), directory=None, out_dir=None):
    """Копирует свой призрак набора в папку экспорта. Возвращает путь к файлу или None."""
    keys = keys_for(chart, mods)
    src = next((p for p in (path_for(k, directory) for k in keys) if os.path.exists(p)), None)
    if src is None:
        return None
    res = jsonio.read(src)
    if not res.ok:
        return None
    dest = os.path.join(out_dir or EXPORT_DIR, os.path.basename(path_for(keys[0])))
    ok, _ = jsonio.try_write(dest, res.data, indent=2)
    return dest if ok else None


def choice_of(chart):
    """Какой призрак выбрал игрок для чарта: CHOICE_OWN (по умолчанию), CHOICE_NONE или «import:имя файла»."""
    key = chart.id or chart.key
    raw = jsonio.load(CHOICE_PATH, {}, expect=dict)
    value = raw.get(key) if key and isinstance(raw, dict) else None
    return value if isinstance(value, str) else CHOICE_OWN


def save_choice(chart, value):
    key = chart.id or chart.key
    if not key:
        return False
    raw = jsonio.load(CHOICE_PATH, {}, expect=dict)
    if not isinstance(raw, dict):
        raw = {}
    raw[key] = value
    ok, _ = jsonio.try_write(CHOICE_PATH, raw, indent=2)
    return ok


def for_play(chart, mods=(), directory=None, import_dir=None):
    """(Ghost | None, статус) призрака для показа в игре с учётом выбора игрока."""
    choice = choice_of(chart)
    if choice == CHOICE_NONE:
        return None, NONE
    if choice.startswith(IMPORT_PREFIX):
        name = choice[len(IMPORT_PREFIX):]
        if not _plain(name):
            return None, NONE
        return load_file(os.path.join(import_dir or IMPORT_DIR, name), chart, mods)
    return load(chart, directory, mods)


def delete(chart, directory=None):
    """Удаляет призраки чарта для всех наборов модификаторов (базовый и «__…»-варианты)."""
    folder = directory or DIR
    bases = [_safe(k) for k in (chart.id, chart.key) if k]
    try:
        names = os.listdir(folder)
    except OSError:
        return
    for name in names:
        if not name.endswith(".ghost.json"):
            continue
        stem = name[:-len(".ghost.json")]
        if any(stem == b or stem.startswith(b + "__") for b in bases):
            try:
                os.remove(os.path.join(folder, name))
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
