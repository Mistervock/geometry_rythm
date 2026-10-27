"""Автосохранение редактора и восстановление после сбоя.

Один чарт — свой ключ — свои файлы автосохранения, поэтому восстановление одного проекта не может
затронуть другой:

    data/autosave/<ключ>.autosave.json      свежее автосохранение (оболочка + полный чарт)
    data/autosave/<ключ>.autosave.1.json    предыдущее поколение (не чаще раза в 2 минуты)
    data/autosave/<ключ>.autosave.2.json    ещё более старое

Ключ чарта — имя его файла без расширения (так же устроены рекорды и победы); у ещё не сохранённого
чарта — «new-<случайный id>». Исходный файл чарта автосохранение никогда не трогает: он заменяется
только когда автор сам нажмёт «Сохранить» (и перед этим уходит в резервные копии).

Оболочка («envelope») хранит название, песню, время, число нот и хэш исходного файла на момент начала
редактирования (base_hash). По нему видно, менялся ли исходный чарт после автосохранения:
если менялся, восстановление предлагается только как НОВАЯ копия.

Запись идёт в фоновом потоке (данные для неё собираются в основном потоке), поэтому кадр не ждёт диск.
"""
import json
import os
import threading
import time

import jsonio
import validation as V

FORMAT = "gr-autosave"
VERSION = 1
SUFFIX = ".autosave.json"
GENERATIONS = 3
ROTATE_AFTER = 120.0          # секунд: прежнее автосохранение уходит в «.1» не чаще этого
INTERVAL = 20.0               # через сколько секунд после первой несохранённой правки пишем автосохранение
IMPORTANT_DEBOUNCE = 3.0      # после «важной» правки — не чаще раза в 3 секунды
MAX_AGE_DAYS = 30
MAX_FILES = 60

#-- Статусы найденных автосохранений
NEWER, CONFLICT, ORPHAN, DRAFT, LEGACY, IDENTICAL, CORRUPT = (
    "newer", "conflict", "orphan", "draft", "legacy", "identical", "corrupt")


def default_dir():
    import config as C
    return C.root("data", "autosave")


def default_chart_dir():
    import songs
    return songs.CHART_DIR


def chart_key(chart, draft_id=""):
    if chart.path:
        return os.path.splitext(os.path.basename(chart.path))[0]
    return f"new-{draft_id}" if draft_id else "new-draft"


def path_for(directory, key, gen=0):
    return os.path.join(directory, f"{key}{SUFFIX}" if gen == 0 else f"{key}.autosave.{gen}.json")


def source_hash(path):
    return jsonio.file_sha1(path) if path and os.path.isfile(path) else ""


def make_envelope(chart, key, base_hash, reason="timer", saved_ts=None):
    ts = time.time() if saved_ts is None else saved_ts
    return {"format": FORMAT, "version": VERSION, "key": key,
            "chart_file": os.path.basename(chart.path) if chart.path else None,
            "chart_id": chart.id or "", "song": chart.song, "name": chart.name,
            "saved_ts": ts, "saved_at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts)),
            "reason": reason, "notes": len(chart.notes), "events": len(chart.events),
            "base_hash": base_hash, "chart": chart.to_dict()}


#-- Запись

class Autosaver:
    """Умеет решать, когда писать, и писать в фоне. Для тестов threaded=False — запись синхронная."""

    def __init__(self, chart, draft_id="", directory=None, clock=time.time, threaded=True):
        self.chart = chart
        self.directory = directory or default_dir()
        self.clock = clock
        self.threaded = threaded
        self.draft_id = draft_id or os.urandom(4).hex()
        self.key = chart_key(chart, self.draft_id)
        self.base_hash = source_hash(chart.path)
        self.saved_rev = -1            # ревизия, которая уже записана
        self.dirty_since = None        # когда появились первые несохранённые правки
        self.last_save_time = 0.0
        self.last_saved_at = None      # время последней успешной записи (для интерфейса)
        self.state = "idle"            # idle | saving | ok | error
        self.error = ""
        self.writes = 0
        self._lock = threading.Condition()
        self._job = None
        self._worker = None
        self._busy = False

    #-- Когда писать

    def note_change(self, rev):
        if rev != self.saved_rev and self.dirty_since is None:
            self.dirty_since = self.clock()

    def due(self, rev, important=False):
        if rev == self.saved_rev:
            return False
        now = self.clock()
        if self.dirty_since is None:
            self.dirty_since = now
            return False
        if important:
            return now - self.last_save_time >= IMPORTANT_DEBOUNCE
        return now - self.dirty_since >= INTERVAL

    def retarget(self, chart=None):
        """После первого «Сохранить» у нового чарта появляется путь — ключ меняется, старые файлы убираем."""
        old_key = self.key
        self.key = chart_key(self.chart, self.draft_id)
        self.base_hash = source_hash(self.chart.path)
        if old_key != self.key:
            remove_key(self.directory, old_key)

    #-- Запись

    def save(self, rev, reason="timer", wait=False):
        env = make_envelope(self.chart, self.key, self.base_hash, reason, self.clock())
        with self._lock:
            self._job = (env, rev, self.key)
            self.state = "saving"
            self.last_save_time = self.clock()
            self.saved_rev = rev
            self.dirty_since = None
        if not self.threaded:
            self._run_job()
            return
        with self._lock:
            if self._worker is None or not self._worker.is_alive():
                self._worker = threading.Thread(target=self._loop, daemon=True, name="autosave")
                self._worker.start()
            self._lock.notify_all()
        if wait:
            self.flush()

    def _loop(self):
        while True:
            with self._lock:
                if self._job is None:
                    self._lock.wait(1.0)
                    if self._job is None:
                        self._busy = False
                        self._lock.notify_all()
                        return
            self._run_job()

    def _run_job(self):
        with self._lock:
            job, self._job = self._job, None
            self._busy = job is not None
        if job is None:
            return
        env, rev, key = job
        try:
            self._write(env, key)
            with self._lock:
                if self._job is None:
                    self.state = "ok"
                self.error = ""
                self.last_saved_at = env["saved_ts"]
                self.writes += 1
        except jsonio.SaveError as e:
            with self._lock:
                self.state = "error"
                self.error = str(e)
                self.saved_rev = -1            # попробуем снова при следующей проверке
        finally:
            with self._lock:
                self._busy = False
                self._lock.notify_all()

    def _write(self, env, key):
        main = path_for(self.directory, key)
        try:
            os.makedirs(self.directory, exist_ok=True)
        except OSError as e:
            raise jsonio.SaveError(str(e))
        try:
            age = time.time() - os.path.getmtime(main)
        except OSError:
            age = None
        if age is not None and age >= ROTATE_AFTER:
            for g in range(GENERATIONS - 1, 0, -1):
                src = path_for(self.directory, key, g - 1)
                if os.path.exists(src):
                    try:
                        os.replace(src, path_for(self.directory, key, g))
                    except OSError:
                        pass
        jsonio.write_atomic(main, env, indent=None)

    def flush(self, timeout=5.0):
        """Ждёт окончания фоновой записи (при выходе из редактора, закрытии окна, в тестах)."""
        end = time.time() + timeout
        with self._lock:
            while (self._job is not None or self._busy) and time.time() < end:
                self._lock.wait(0.1)

    def clear(self):
        """Чарт сохранён или правки намеренно отброшены — автосохранения больше не нужны."""
        self.flush()
        remove_key(self.directory, self.key)
        self.state = "idle"
        self.saved_rev = -1
        self.dirty_since = None


def remove_key(directory, key):
    n = 0
    for g in range(GENERATIONS):
        p = path_for(directory, key, g)
        try:
            os.remove(p)
            n += 1
        except OSError:
            pass
    return n


#-- Поиск и восстановление

class Recoverable:
    """Найденное автосохранение: что это за чарт, когда сохранено, в каком состоянии, что можно сделать."""

    def __init__(self, key, path, status, env=None, source_path=None, note=""):
        self.key = key
        self.path = path
        self.status = status
        self.env = env or {}
        self.source_path = source_path
        self.note = note
        self.ignored = False

    @property
    def name(self):
        return self.env.get("name") or (self.env.get("chart") or {}).get("name") or self.key

    @property
    def song(self):
        return self.env.get("song") or (self.env.get("chart") or {}).get("song") or ""

    @property
    def saved_ts(self):
        return float(self.env.get("saved_ts") or 0.0)

    @property
    def saved_at(self):
        return self.env.get("saved_at") or ""

    @property
    def can_restore_in_place(self):
        """Можно ли при сохранении заменить исходный файл (только если он не менялся после начала сессии)."""
        return self.status == NEWER and bool(self.source_path)

    def describe(self, lang="ru"):
        notes = self.env.get("notes")
        extra = f"{notes} нот" if lang == "ru" and notes is not None else (f"{notes} notes" if notes is not None else "")
        return f"{self.name} — {self.saved_at} ({extra})" if extra else f"{self.name} — {self.saved_at}"


def _read_envelope(path):
    """Возвращает (env | None, ошибка). Проверяет оболочку и вложенный чарт."""
    res = jsonio.read(path)
    if not res.ok:
        return None, res.message or res.kind
    env = res.data
    if not isinstance(env, dict) or env.get("format") != FORMAT:
        return None, "не файл автосохранения"
    ver = env.get("version")
    if not isinstance(ver, int) or ver > VERSION or ver < 1:
        return None, f"неподдерживаемая версия автосохранения {ver!r}"
    clean, rep = V.check_chart(env.get("chart"))
    if clean is None:
        return None, rep.first_error()
    return env, ""


def generations(directory, key):
    return [path_for(directory, key, g) for g in range(GENERATIONS) if os.path.exists(path_for(directory, key, g))]


def load_best(directory, key):
    """Первое читаемое поколение автосохранения: свежее, а если оно побито — предыдущее."""
    problems = []
    for p in generations(directory, key):
        env, err = _read_envelope(p)
        if env is not None:
            return env, p, problems
        problems.append((p, err))
    return None, None, problems


def _state_path(directory):
    return os.path.join(directory, "state.json")


def _ignored(directory):
    data = jsonio.load(_state_path(directory), {}, expect=dict)
    ig = data.get("ignored")
    return ig if isinstance(ig, dict) else {}


def ignore(directory, rec):
    """Игрок выбрал «открыть обычный чарт»: не напоминать, пока автосохранение не обновится."""
    ig = _ignored(directory)
    ig[rec.key] = rec.saved_ts
    jsonio.try_write(_state_path(directory), {"ignored": ig})


def scan(directory=None, chart_dir=None):
    """Все автосохранения, которые стоит показать игроку. Никогда не бросает исключений."""
    directory = directory or default_dir()
    chart_dir = chart_dir or default_chart_dir()
    out = []
    try:
        names = sorted(os.listdir(directory))
    except OSError:
        return out
    ignored = _ignored(directory)
    keys = []
    for n in names:
        if n.endswith(SUFFIX):
            keys.append(n[:-len(SUFFIX)])
    for key in keys:
        env, path, problems = load_best(directory, key)
        if env is None:
            out.append(Recoverable(key, path_for(directory, key), CORRUPT,
                                   note=problems[0][1] if problems else ""))
            continue
        rec = _classify(key, path, env, chart_dir)
        if rec.status == IDENTICAL:
            remove_key(directory, key)
            continue
        rec.ignored = ignored.get(key, -1) >= rec.saved_ts
        out.append(rec)
    out += _scan_legacy(directory, names)
    out.sort(key=lambda r: -r.saved_ts)
    return out


def _classify(key, path, env, chart_dir):
    chart_file = env.get("chart_file")
    if not chart_file:
        return Recoverable(key, path, DRAFT, env, None, "чарт ещё ни разу не сохранялся")
    source = os.path.join(chart_dir, os.path.basename(chart_file))
    if not os.path.isfile(source):
        return Recoverable(key, path, ORPHAN, env, None, "исходного файла чарта больше нет")
    res = jsonio.read(source)
    if res.ok and isinstance(res.data, dict):
        same_song = res.data.get("song") == (env.get("chart") or {}).get("song")
        same_id = (not env.get("chart_id")) or (not res.data.get("id")) or res.data.get("id") == env.get("chart_id")
        if not (same_song and same_id):
            return Recoverable(key, path, ORPHAN, env, None, "файл с этим именем теперь содержит другой чарт")
        if _same_content(res.data, env["chart"]):
            return Recoverable(key, path, IDENTICAL, env, source)
    base = env.get("base_hash") or ""
    if base and source_hash(source) != base:
        return Recoverable(key, path, CONFLICT, env, source, "исходный чарт изменился после начала редактирования")
    return Recoverable(key, path, NEWER, env, source)


def _same_content(a, b):
    ca, _ = V.check_chart(a)
    cb, _ = V.check_chart(b)
    if ca is None or cb is None:
        return False
    keys = ("song", "name", "charter", "difficulty", "achievement", "notes", "events", "folders", "grid")
    return all(ca.get(k) == cb.get(k) for k in keys)


def _scan_legacy(directory, names):
    out = []
    for n in names:
        if not n.endswith("-autosave.json"):
            continue
        path = os.path.join(directory, n)
        res = jsonio.read(path)
        if not res.ok or not isinstance(res.data, dict):
            out.append(Recoverable(n[:-5], path, CORRUPT, note=res.message))
            continue
        clean, rep = V.check_chart(res.data)
        if clean is None:
            out.append(Recoverable(n[:-5], path, CORRUPT, note=rep.first_error()))
            continue
        try:
            ts = os.path.getmtime(path)
        except OSError:
            ts = 0.0
        env = {"name": clean["name"], "song": clean["song"], "saved_ts": ts, "chart": res.data,
               "saved_at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts)), "notes": len(clean["notes"]),
               "chart_file": None}
        out.append(Recoverable(n[:-5], path, LEGACY, env, None, "автосохранение старого формата"))
    return out


def restore_chart(rec):
    """Строит Chart из автосохранения.

    Если исходный файл можно заменить (NEWER) — путь сохраняется, иначе chart.path = None и «Сохранить»
    создаст новый файл рядом (имя получает пометку), исходный чарт останется нетронутым."""
    import chart as chartmod
    data = rec.env.get("chart")
    ch = chartmod.Chart.from_dict(data)
    if rec.can_restore_in_place:
        ch.path = rec.source_path
    else:
        ch.path = None
        ch.id = ""
        suffix = " (восстан.)"
        ch.name = (ch.name[:V.NAME_MAX - len(suffix)] + suffix)
    return ch


def discard(rec):
    """Удаляет автосохранение (все поколения; для legacy и повреждённых — сам файл)."""
    n = remove_key(os.path.dirname(rec.path), rec.key)
    if n == 0:
        try:
            os.remove(rec.path)
            n = 1
        except OSError:
            pass
    return n


def find_for(chart, directory=None, chart_dir=None):
    """Автосохранение именно этого чарта (по ключу) — для проверки при открытии редактора."""
    directory = directory or default_dir()
    if not chart.path:
        return None
    key = chart_key(chart)
    for rec in scan(directory, chart_dir):
        if rec.key == key and rec.status != CORRUPT:
            return rec
    return None


def cleanup(directory=None, now=None, max_age_days=MAX_AGE_DAYS, max_files=MAX_FILES):
    """Удаляет устаревшие автосохранения и лишние старые файлы. Возвращает число удалённых."""
    directory = directory or default_dir()
    now = time.time() if now is None else now
    removed = 0
    try:
        entries = []
        for n in os.listdir(directory):
            p = os.path.join(directory, n)
            if os.path.isfile(p) and (n.endswith(".json") or ".corrupt-" in n) and n != "state.json":
                entries.append((os.path.getmtime(p), p))
    except OSError:
        return 0
    entries.sort()
    limit = now - max_age_days * 86400
    for ts, p in list(entries):
        if ts < limit:
            try:
                os.remove(p)
                removed += 1
                entries.remove((ts, p))
            except OSError:
                pass
    while len(entries) > max_files:
        _, p = entries.pop(0)
        try:
            os.remove(p)
            removed += 1
        except OSError:
            pass
    return removed
