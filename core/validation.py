"""Общий слой проверки данных: чарты, события, настройки, рекорды и прочие файлы пользователя.

Редактор, игровой режим, импорт и загрузчик песен вызывают одни и те же функции, поэтому правила
у всех одинаковые. Проверка отделена от чтения файла: сюда приходят уже разобранные данные.

Серьёзность проблем:
  error   — критично: данные нельзя безопасно загрузить (нет списка нот, версия новее поддерживаемой …);
  warning — данные загрузятся, но что-то подозрительно или часть записей пришлось пропустить;
  fix     — проблема исправлена автоматически В ПАМЯТИ (обрезано значение, нота отсортирована …);
            файл на диске при этом не меняется, пока автор сам не сохранит чарт;
  info    — справочная пометка (например, чарт старой версии, миграция при сохранении).

Модуль не рисует интерфейс и не пишет на диск.
"""
import math
import secrets
import re

CHART_VERSION = 5          # текущая версия формата чарта
MIN_VERSION = 1            # самая старая версия, которую умеем мигрировать
LANES = 4
MAX_NOTE_T = 6 * 3600 * 1000
MAX_HOLD = 600_000          # жёсткий предел длительности удержания
SOFT_HOLD = 10_000          # длиннее — только предупреждение (редактор ограничивает так же)
NAME_MAX, CHARTER_MAX, ACH_MAX, FOLDER_MAX = 24, 40, 80, 24
MAX_FOLDERS = 64

ERROR, WARNING, FIX, INFO = "error", "warning", "fix", "info"
_ORDER = {ERROR: 0, WARNING: 1, FIX: 2, INFO: 3}
PER_CODE_KEEP = 12          # подробно храним первые N проблем каждого вида, остальное — счётчиком

#-- Тексты: код -> (по-русски, по-английски)
MESSAGES = {
    "json.syntax": ("файл повреждён: {detail}", "file is corrupted: {detail}"),
    "json.missing": ("файл не найден", "file not found"),
    "json.access": ("нет доступа к файлу: {detail}", "cannot access the file: {detail}"),
    "json.type": ("неожиданная структура данных", "unexpected data structure"),
    "chart.not_object": ("корень чарта должен быть объектом {…}", "chart root must be an object {…}"),
    "chart.version_new": ("чарт создан в более новой версии формата ({version}); эта игра понимает до {max}",
                          "chart uses a newer format version ({version}); this game supports up to {max}"),
    "chart.version_bad": ("версия формата указана неверно ({value!r})", "invalid format version ({value!r})"),
    "chart.version_missing": ("версия формата не указана — считаю старым чартом",
                              "format version is missing — treating as an old chart"),
    "chart.migrated": ("чарт версии {version} будет обновлён до {max} при сохранении",
                       "chart version {version} will be upgraded to {max} on save"),
    "chart.no_notes": ("нет списка нот «notes»", "no «notes» list"),
    "chart.notes_type": ("«notes» должен быть списком", "«notes» must be a list"),
    "chart.no_song": ("не указана песня «song»", "song name «song» is missing"),
    "chart.empty": ("в чарте нет ни одной ноты", "the chart has no notes"),
    "chart.field_type": ("поле «{field}» имеет неверный тип — взято значение по умолчанию",
                         "field «{field}» has a wrong type — default used"),
    "chart.field_range": ("поле «{field}» вне допустимых пределов — приведено к {value}",
                          "field «{field}» out of range — clamped to {value}"),
    "chart.field_trim": ("поле «{field}» слишком длинное — обрезано", "field «{field}» too long — trimmed"),
    "chart.id_new": ("у чарта нет идентификатора — будет назначен при сохранении",
                     "chart has no id — one will be assigned on save"),
    "chart.id_bad": ("идентификатор чарта некорректен — будет заменён", "invalid chart id — will be replaced"),
    "chart.notes_sorted": ("ноты были не по порядку — отсортированы", "notes were out of order — sorted"),
    "chart.events_sorted": ("события были не по порядку — отсортированы", "events were out of order — sorted"),
    "chart.extra_keys": ("неизвестные поля сохранены без изменений: {keys}",
                         "unknown fields kept unchanged: {keys}"),
    "note.not_object": ("запись ноты не является объектом — пропущена", "note entry is not an object — skipped"),
    "note.missing": ("у ноты нет поля «{field}» — пропущена", "note has no «{field}» — skipped"),
    "note.type": ("поле «{field}» не число ({value!r}) — нота пропущена",
                  "field «{field}» is not a number ({value!r}) — note skipped"),
    "note.not_finite": ("поле «{field}» бесконечно или не число — нота пропущена",
                        "field «{field}» is infinite or NaN — note skipped"),
    "note.negative_time": ("время ноты отрицательное ({value}) — нота пропущена",
                           "negative note time ({value}) — note skipped"),
    "note.time_big": ("время ноты слишком велико ({value}) — нота пропущена",
                      "note time is too large ({value}) — note skipped"),
    "note.lane": ("дорожка {value!r} вне 0…3 — нота пропущена", "lane {value!r} outside 0..3 — note skipped"),
    "note.rounded": ("нецелое время/длительность округлено до миллисекунд", "fractional time rounded to ms"),
    "note.str_number": ("число записано строкой — исправлено", "number stored as a string — fixed"),
    "note.dur_negative": ("отрицательная длительность удержания сброшена в 0", "negative hold length reset to 0"),
    "note.dur_big": ("длительность удержания {value} мс уменьшена до {limit}",
                     "hold length {value} ms reduced to {limit}"),
    "note.dur_long": ("очень длинное удержание ({value} мс)", "very long hold ({value} ms)"),
    "note.duplicate": ("две ноты на одной дорожке в одно и то же время ({lane}, {t} мс)",
                       "two notes on the same lane at the same time ({lane}, {t} ms)"),
    "note.in_hold": ("нота на дорожке {lane} в {t} мс попадает внутрь удержания, начатого в {start} мс",
                     "note on lane {lane} at {t} ms falls inside a hold started at {start} ms"),
    "note.after_end": ("нот после конца песни: {count} (первая в {t} мс) — до них не дойти",
                       "notes after the end of the song: {count} (first at {t} ms) — unreachable"),
    "note.skipped_total": ("пропущено некорректных нот: {count}", "invalid notes skipped: {count}"),
    "event.not_object": ("запись события не является объектом — пропущена", "event entry is not an object — skipped"),
    "event.unknown_type": ("неизвестный тип события {type} — пропущено", "unknown event type {type} — skipped"),
    "event.bad_time": ("время события некорректно — взято 0", "invalid event time — 0 used"),
    "event.field_type": ("поле «{field}» не число — взято значение по умолчанию",
                         "field «{field}» is not a number — default used"),
    "event.field_range": ("поле «{field}» вне пределов — приведено к допустимому",
                          "field «{field}» out of range — clamped"),
    "event.field_default": ("нет поля «{field}» — взято значение по умолчанию",
                            "field «{field}» missing — default used"),
    "event.text_trim": ("текст карточки обрезан", "card text trimmed"),
    "event.resource_missing": ("файл «{file}» не найден в папке images/", "file «{file}» not found in images/"),
    "event.resource_empty": ("событие без выбранного файла", "event has no file selected"),
    "event.after_end": ("событий после конца песни: {count}", "events after the end of the song: {count}"),
    "event.folder_unknown": ("событие ссылается на несуществующую папку «{folder}» — вынуто из папки",
                             "event refers to an unknown folder «{folder}» — taken out"),
    "event.skipped_total": ("пропущено некорректных событий: {count}", "invalid events skipped: {count}"),
    "folder.bad": ("запись папки некорректна — пропущена", "invalid folder entry — skipped"),
    "folder.duplicate": ("папка «{name}» повторяется — лишняя пропущена", "folder «{name}» repeated — skipped"),
    "grid.type": ("настройки сетки некорректны — взяты по умолчанию", "invalid grid settings — defaults used"),
    "grid.range": ("параметр сетки «{field}» вне пределов — исправлен", "grid parameter «{field}» out of range — fixed"),
    "file.corrupt_moved": ("повреждённый файл сохранён как {path}", "corrupted file kept as {path}"),
    "settings.type": ("настройка «{field}» некорректна — взято значение по умолчанию",
                      "setting «{field}» is invalid — default used"),
    "settings.range": ("настройка «{field}» вне пределов — исправлена", "setting «{field}» out of range — fixed"),
    "settings.unknown": ("неизвестная настройка «{field}» игнорируется",
                         "unknown setting «{field}» is ignored"),
    "records.entry": ("запись рекордов #{index} некорректна — пропущена", "record #{index} is invalid — skipped"),
    "list.entry": ("запись #{index} не строка — пропущена", "entry #{index} is not a string — skipped"),
    "dict.entry": ("запись «{key}» некорректна — пропущена", "entry «{key}» is invalid — skipped"),
}


class Issue:
    __slots__ = ("severity", "code", "where", "args")

    def __init__(self, severity, code, where="", args=None):
        self.severity = severity
        self.code = code
        self.where = where
        self.args = args or {}

    def text(self, lang="ru"):
        ru, en = MESSAGES.get(self.code, (self.code, self.code))
        template = ru if lang == "ru" else en
        try:
            msg = template.format(**self.args)
        except (KeyError, IndexError, ValueError):
            msg = template
        return f"{self.where}: {msg}" if self.where else msg

    def __repr__(self):
        return f"Issue({self.severity}, {self.code}, {self.where!r})"


class Report:
    """Набор проблем одной проверки. Подробно хранит первые PER_CODE_KEEP каждого вида."""

    def __init__(self, subject=""):
        self.subject = subject
        self.issues = []
        self.counts = {}            # code -> сколько всего
        self.sev_counts = {ERROR: 0, WARNING: 0, FIX: 0, INFO: 0}
        self.lossy = False          # часть записей отброшена: сохранение перезапишет их потерю
        self.dropped_notes = 0
        self.dropped_events = 0

    def add(self, severity, code, where="", **args):
        n = self.counts.get(code, 0) + 1
        self.counts[code] = n
        self.sev_counts[severity] += 1
        if n <= PER_CODE_KEEP:
            self.issues.append(Issue(severity, code, where, args))
        return self

    def error(self, code, where="", **a):
        return self.add(ERROR, code, where, **a)

    def warn(self, code, where="", **a):
        return self.add(WARNING, code, where, **a)

    def fix(self, code, where="", **a):
        return self.add(FIX, code, where, **a)

    def info(self, code, where="", **a):
        return self.add(INFO, code, where, **a)

    def merge(self, other):
        for it in other.issues:
            self.issues.append(it)
        for k, v in other.counts.items():
            self.counts[k] = self.counts.get(k, 0) + v
        for k, v in other.sev_counts.items():
            self.sev_counts[k] += v
        self.lossy = self.lossy or other.lossy
        self.dropped_notes += other.dropped_notes
        self.dropped_events += other.dropped_events

    @property
    def errors(self):
        return [i for i in self.issues if i.severity == ERROR]

    @property
    def warnings(self):
        return [i for i in self.issues if i.severity == WARNING]

    @property
    def fixes(self):
        return [i for i in self.issues if i.severity == FIX]

    @property
    def ok(self):
        return self.sev_counts[ERROR] == 0

    @property
    def clean(self):
        return self.sev_counts[ERROR] == 0 and self.sev_counts[WARNING] == 0 and self.sev_counts[FIX] == 0

    def has_code(self, code):
        return self.counts.get(code, 0) > 0

    def lines(self, lang="ru", limit=None, min_severity=INFO):
        keep = [i for i in sorted(self.issues, key=lambda i: _ORDER[i.severity])
                if _ORDER[i.severity] <= _ORDER[min_severity]]
        out = [f"[{i.severity}] {i.text(lang)}" for i in keep]
        return out if limit is None else out[:limit]

    def summary(self, lang="ru"):
        e, w, f = self.sev_counts[ERROR], self.sev_counts[WARNING], self.sev_counts[FIX]
        if lang == "ru":
            return f"ошибок: {e}, предупреждений: {w}, исправлено в памяти: {f}"
        return f"errors: {e}, warnings: {w}, auto-fixed in memory: {f}"

    def first_error(self, lang="ru"):
        errs = self.errors
        return errs[0].text(lang) if errs else ""


#-- Числа

def is_num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def finite(v):
    return is_num(v) and math.isfinite(v)


_NUM_STR = re.compile(r"^\s*-?\d+(\.\d+)?\s*$")


def _coerce_ms(raw, field, where, rep, required=True, default=0):
    """Число из файла → (значение_float | None, пропустить_ли_запись)."""
    if raw is None:
        if required:
            rep.warn("note.missing", where, field=field)
            return None, True
        return float(default), False
    if isinstance(raw, str) and _NUM_STR.match(raw):
        rep.fix("note.str_number", where)
        raw = float(raw)
    if not is_num(raw):
        rep.warn("note.type", where, field=field, value=raw if not isinstance(raw, (list, dict)) else type(raw).__name__)
        return None, True
    if not math.isfinite(raw):
        rep.warn("note.not_finite", where, field=field)
        return None, True
    return float(raw), False


def clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v


#-- Сетка редактора

GRID_DEFAULT = {"mode": "ms", "ms_step": 50, "bpm": 120.0, "offset": 0.0, "div": 4, "bar": 4,
                "snap": True, "show_beats": True, "show_bars": True, "show_sub": True}
GRID_LIMITS = {"bpm": (20.0, 400.0), "offset": (-60000.0, 60000.0), "div": (1, 192), "bar": (1, 16),
               "ms_step": (1, 2000)}


def check_grid(raw, rep, where="grid"):
    out = dict(GRID_DEFAULT)
    if raw is None:
        return out
    if not isinstance(raw, dict):
        rep.warn("grid.type", where)
        return out
    if raw.get("mode") in ("ms", "beat"):
        out["mode"] = raw["mode"]
    for key in ("snap", "show_beats", "show_bars", "show_sub"):
        if key in raw:
            out[key] = bool(raw[key])
    for key, (lo, hi) in GRID_LIMITS.items():
        if key not in raw:
            continue
        v = raw[key]
        if not finite(v):
            rep.warn("grid.type", where)
            continue
        v2 = clamp(v, lo, hi)
        if v2 != v:
            rep.fix("grid.range", where, field=key)
        out[key] = round(float(v2), 3) if key in ("bpm", "offset") else int(round(v2))
    return out


#-- Чарт

KNOWN_KEYS = {"version", "id", "song", "name", "charter", "difficulty", "notes", "events", "folders",
              "achievement", "grid"}


def new_chart_id():
    return secrets.token_hex(8)


_ID_RE = re.compile(r"^[0-9A-Za-z_-]{6,64}$")


def check_chart(data, duration_ms=None, image_exists=None):
    """Проверяет разобранный JSON чарта.

    Возвращает (clean, report). clean — нормализованный словарь (ноты — кортежи (t, lane, d),
    отсортированные) либо None, если есть критические ошибки (report.ok == False)."""
    rep = Report("chart")
    if not isinstance(data, dict):
        rep.error("chart.not_object")
        return None, rep

    version = data.get("version")
    if version is None:
        rep.info("chart.version_missing")
        version = 1
    elif not is_num(version) or not math.isfinite(version) or int(version) != version or version < 1:
        rep.error("chart.version_bad", "version", value=version)
        return None, rep
    version = int(version)
    if version > CHART_VERSION:
        rep.error("chart.version_new", "version", version=version, max=CHART_VERSION)
        return None, rep
    if version < CHART_VERSION:
        rep.info("chart.migrated", "version", version=version, max=CHART_VERSION)

    song = data.get("song")
    if not isinstance(song, str) or not song.strip():
        rep.error("chart.no_song", "song")
        return None, rep

    raw_notes = data.get("notes")
    if raw_notes is None:
        rep.error("chart.no_notes", "notes")
        return None, rep
    if not isinstance(raw_notes, list):
        rep.error("chart.notes_type", "notes")
        return None, rep

    clean = {"version": CHART_VERSION, "song": song}

    # идентификатор
    cid = data.get("id")
    if cid is None:
        rep.info("chart.id_new")
        clean["id"] = ""
    elif isinstance(cid, str) and _ID_RE.match(cid):
        clean["id"] = cid
    else:
        rep.warn("chart.id_bad", "id")
        clean["id"] = ""

    clean["name"] = _text_field(data, "name", "Чарт", NAME_MAX, rep)
    clean["charter"] = _text_field(data, "charter", "", CHARTER_MAX, rep)
    clean["achievement"] = _text_field(data, "achievement", "", ACH_MAX, rep)
    diff = data.get("difficulty", 1)
    if not is_num(diff) or not math.isfinite(diff):
        rep.fix("chart.field_type", "difficulty", field="difficulty")
        diff = 1
    d2 = int(clamp(int(diff), 1, 5))
    if d2 != int(diff):
        rep.fix("chart.field_range", "difficulty", field="difficulty", value=d2)
    clean["difficulty"] = d2

    clean["grid"] = check_grid(data.get("grid"), rep)
    clean["notes"] = _check_notes(raw_notes, rep, duration_ms)
    clean["events"], clean["folders"] = _check_events_and_folders(
        data.get("events"), data.get("folders"), rep, duration_ms, image_exists)

    extra = {k: v for k, v in data.items() if k not in KNOWN_KEYS}
    if extra:
        clean["extra"] = extra
        rep.info("chart.extra_keys", keys=", ".join(sorted(map(str, extra)))[:80])
    if not clean["notes"]:
        rep.warn("chart.empty")
    return clean, rep


def _text_field(data, key, default, limit, rep):
    raw = data.get(key, default)
    if raw is None:
        return default
    if not isinstance(raw, str):
        rep.fix("chart.field_type", key, field=key)
        raw = str(raw)
    if len(raw) > limit:
        rep.fix("chart.field_trim", key, field=key)
        raw = raw[:limit]
    return raw


def _check_notes(raw_notes, rep, duration_ms):
    notes = []
    skipped = 0
    rounded = False
    for i, n in enumerate(raw_notes):
        where = f"notes[{i}]"
        if not isinstance(n, dict):
            rep.warn("note.not_object", where)
            skipped += 1
            continue
        t, bad = _coerce_ms(n.get("t"), "t", where, rep)
        if bad:
            skipped += 1
            continue
        lane_raw = n.get("lane")
        lane, bad = _coerce_ms(lane_raw, "lane", where, rep)
        if bad:
            skipped += 1
            continue
        if lane != int(lane) or not 0 <= lane < LANES:
            rep.warn("note.lane", where, value=lane_raw)
            skipped += 1
            continue
        if t < 0:
            rep.warn("note.negative_time", where, value=n.get("t"))
            skipped += 1
            continue
        if t > MAX_NOTE_T:
            rep.warn("note.time_big", where, value=n.get("t"))
            skipped += 1
            continue
        d, bad = _coerce_ms(n.get("d"), "d", where, rep, required=False)
        if bad:
            skipped += 1
            continue
        if t != int(t) or d != int(d):
            rounded = True
        ti, di = int(math.floor(t + 0.5)), int(math.floor(d + 0.5))
        if di < 0:
            rep.fix("note.dur_negative", where)
            di = 0
        if di > MAX_HOLD:
            rep.fix("note.dur_big", where, value=di, limit=MAX_HOLD)
            di = MAX_HOLD
        elif di > SOFT_HOLD:
            rep.warn("note.dur_long", where, value=di)
        notes.append((ti, int(lane), di))
    if rounded:
        rep.fix("note.rounded")
    if skipped:
        rep.dropped_notes = skipped
        rep.lossy = True
        rep.warn("note.skipped_total", count=skipped)
    if any(a[:2] > b[:2] for a, b in zip(notes, notes[1:])):
        rep.fix("chart.notes_sorted")
        notes.sort(key=lambda n: (n[0], n[1]))
    _check_note_conflicts(notes, rep)
    if duration_ms:
        late = [n for n in notes if n[0] > duration_ms]
        if late:
            rep.warn("note.after_end", count=len(late), t=late[0][0])
    return notes


def _check_note_conflicts(notes, rep):
    last_start = [-1] * LANES
    run_end = [-1] * LANES                  # самый поздний конец удержания на дорожке
    for t, lane, d in notes:
        if last_start[lane] == t:
            rep.warn("note.duplicate", lane=lane, t=t)
        elif t < run_end[lane]:
            rep.warn("note.in_hold", lane=lane, t=t, start=last_start[lane])
        last_start[lane] = t
        run_end[lane] = max(run_end[lane], t + d)


def _check_events_and_folders(raw_events, raw_folders, rep, duration_ms, image_exists):
    folders, seen = [], set()
    if raw_folders is not None and not isinstance(raw_folders, list):
        rep.warn("folder.bad", "folders")
        raw_folders = []
    for i, f in enumerate(raw_folders or []):
        if not isinstance(f, dict) or not isinstance(f.get("name"), str) or not f["name"]:
            rep.warn("folder.bad", f"folders[{i}]")
            continue
        name = f["name"][:FOLDER_MAX]
        if name in seen:
            rep.warn("folder.duplicate", f"folders[{i}]", name=name)
            continue
        if len(folders) >= MAX_FOLDERS:
            continue
        seen.add(name)
        folders.append({"name": name, "locked": bool(f.get("locked", False))})

    events = []
    skipped = 0
    if raw_events is not None and not isinstance(raw_events, list):
        rep.warn("event.not_object", "events")
        raw_events = []
    for i, raw in enumerate(raw_events or []):
        ev = check_event(raw, f"events[{i}]", rep, image_exists)
        if ev is None:
            skipped += 1
            continue
        if ev["folder"] and ev["folder"] not in seen:
            rep.fix("event.folder_unknown", f"events[{i}]", folder=ev["folder"])
            ev["folder"] = ""
        events.append(ev)
    if skipped:
        rep.dropped_events = skipped
        rep.lossy = True
        rep.warn("event.skipped_total", count=skipped)
    if any(events[i]["t"] > events[i + 1]["t"] for i in range(len(events) - 1)):
        rep.fix("chart.events_sorted")
    events.sort(key=lambda e: e["t"])
    if duration_ms:
        late = [e for e in events if e["t"] > duration_ms]
        if late:
            rep.warn("event.after_end", count=len(late))
    return events, folders


def check_event(raw, where, rep, image_exists=None):
    """Проверяет одно событие. Возвращает нормализованный словарь события или None (пропущено)."""
    import events as EV
    if not isinstance(raw, dict):
        rep.warn("event.not_object", where)
        return None
    kind = raw.get("type")
    if kind not in EV.TYPES:
        rep.warn("event.unknown_type", where, type=repr(kind)[:30])
        return None
    t_raw = raw.get("t")
    if not finite(t_raw):
        rep.warn("event.bad_time", where)
    elif t_raw < 0 or t_raw > EV.MAX_T:
        rep.fix("event.field_range", where + ".t", field="t")
    for key, _label, lo, hi, _step, _default in EV.FIELDS[kind]:
        if key not in raw:
            rep.info("event.field_default", where, field=key)
            continue
        v = raw[key]
        if not finite(v):
            rep.warn("event.field_type", where, field=key)
        elif v < lo or v > hi:
            rep.fix("event.field_range", where, field=key)
    ev = EV.normalize(raw)
    if ev is None:
        rep.warn("event.unknown_type", where, type=repr(kind)[:30])
        return None
    if kind == "card" and isinstance(raw.get("text"), str) and len(raw["text"]) > EV.CARD_TEXT_MAX:
        rep.fix("event.text_trim", where)
    if kind in ("image", "video") and image_exists is not None:
        if not ev["file"]:
            rep.warn("event.resource_empty", where)
        elif not image_exists(ev["file"]):
            rep.warn("event.resource_missing", where, file=ev["file"])
    return ev


#-- Другие файлы пользователя

def check_settings(raw, defaults, limits, extra_rules=None):
    """Проверка настроек. Неизвестные ключи сохраняются (моды), известные приводятся к допустимым."""
    rep = Report("settings")
    out = dict(defaults)
    if raw is None:                       # файла нет — первый запуск, это не проблема
        return out, rep
    if not isinstance(raw, dict):
        rep.warn("json.type")
        return out, rep
    for key in defaults:
        if key not in raw:
            continue
        v = raw[key]
        if key in limits:
            lo, hi, _ = limits[key]
            if not finite(v):
                rep.warn("settings.type", field=key)
                continue
            iv = int(clamp(int(round(v)), lo, hi))
            if iv != v:
                rep.fix("settings.range", field=key)
            out[key] = iv
        else:
            out[key] = v
    for key in raw:
        if key not in defaults:
            rep.info("settings.unknown", field=key)
    if extra_rules:
        extra_rules(out, rep)
    return out, rep


def check_records(raw, max_entries=10):
    rep = Report("records")
    entries = []
    if not isinstance(raw, list):
        rep.warn("json.type")
        return entries, rep
    for i, e in enumerate(raw):
        if not (isinstance(e, dict) and isinstance(e.get("score"), int) and not isinstance(e.get("score"), bool)
                and isinstance(e.get("name"), str)):
            rep.warn("records.entry", index=i)
            continue
        try:
            acc = float(e.get("acc", 0.0))
        except (TypeError, ValueError):
            acc = 0.0
        if not math.isfinite(acc):
            acc = 0.0
        entries.append({"name": e["name"][:12], "score": e["score"], "acc": acc,
                        "grade": str(e.get("grade", "?"))[:2], "date": str(e.get("date", ""))[:10],
                        "song": str(e.get("song", ""))[:40], "chart": str(e.get("chart", ""))[:24]})
    entries.sort(key=lambda e: (-e["score"], -e["acc"]))
    return entries[:max_entries], rep


def check_str_list(raw):
    rep = Report("list")
    out = []
    if not isinstance(raw, list):
        rep.warn("json.type")
        return out, rep
    for i, v in enumerate(raw):
        if isinstance(v, str):
            out.append(v)
        else:
            rep.warn("list.entry", index=i)
    return out, rep


def check_ranks(raw, valid_grades):
    rep = Report("ranks")
    out = {}
    if not isinstance(raw, dict):
        rep.warn("json.type")
        return out, rep
    for key, e in raw.items():
        if (isinstance(key, str) and isinstance(e, dict) and e.get("grade") in valid_grades
                and finite(e.get("acc", 0)) and finite(e.get("score", 0))):
            kept = dict(e)
            kept["acc"] = float(e.get("acc", 0))
            kept["score"] = int(e.get("score", 0))
            out[key] = kept
        else:
            rep.warn("dict.entry", key=str(key)[:40])
    return out, rep
