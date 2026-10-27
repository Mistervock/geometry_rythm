"""Единый слой чтения и записи JSON-файлов.

Все данные игры (чарты, настройки, рекорды, автосохранения, повторы) проходят через эти функции:

* запись атомарная: данные пишутся во временный файл рядом с целью, сбрасываются на диск
  и только потом заменяют целевой файл (os.replace) — обрыв посреди записи не портит старую версию;
* повреждённый файл не затирается пустым состоянием: он переименовывается в «*.corrupt-<время>»
  (карантин), чтобы пользователь мог его посмотреть или починить руками;
* ошибки файловой системы (нет файла, нет прав, диск занят) возвращаются как значения, а не
  как исключения, где это возможно.

Модуль не зависит от pygame и от config — он принимает готовые пути, поэтому его легко тестировать.
"""
import hashlib
import json
import math
import os
import time

KEEP_CORRUPT = 5

MISSING, ACCESS, SYNTAX, EMPTY, TYPE = "missing", "access", "syntax", "empty", "type"

# Последние проблемы чтения/записи (для отладки и вывода в интерфейсе). Кольцевой журнал.
_problems = []
MAX_PROBLEMS = 50


def _note_problem(kind, path, message):
    _problems.append({"kind": kind, "path": path, "message": message, "ts": time.time()})
    del _problems[:-MAX_PROBLEMS]


def recent_problems():
    return list(_problems)


def clear_problems():
    _problems.clear()


class ReadResult:
    __slots__ = ("ok", "data", "kind", "message", "path")

    def __init__(self, ok, data=None, kind=None, message="", path=""):
        self.ok = ok
        self.data = data
        self.kind = kind
        self.message = message
        self.path = path

    def __bool__(self):
        return self.ok


#-- Чтение

def read(path):
    """Читает JSON. Никогда не бросает исключений: итог — ReadResult."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
    except FileNotFoundError:
        return ReadResult(False, None, MISSING, "файл не найден", path)
    except UnicodeDecodeError as e:
        return ReadResult(False, None, SYNTAX, f"не UTF-8: {e}", path)
    except OSError as e:
        return ReadResult(False, None, ACCESS, str(e), path)
    if text.startswith("﻿"):
        text = text[1:]
    if not text.strip():
        return ReadResult(False, None, EMPTY, "файл пуст", path)
    try:
        return ReadResult(True, json.loads(text, parse_constant=_reject_constant), None, "", path)
    except ValueError as e:
        return ReadResult(False, None, SYNTAX, f"{e}", path)
    except RecursionError:
        return ReadResult(False, None, SYNTAX, "слишком глубокая вложенность", path)


def _reject_constant(name):
    # NaN / Infinity допускаются питоновским json по умолчанию, но не являются корректным JSON
    raise ValueError(f"недопустимое значение {name}")


def load(path, default=None, expect=None, quarantine_bad=True):
    """Читает JSON; при любой проблеме возвращает default.

    expect — тип (или кортеж типов) корня. Если файл есть, но он испорчен или не того типа,
    он уходит в карантин (если quarantine_bad), чтобы его не затёрла следующая запись."""
    res = read(path)
    if res.ok and (expect is None or isinstance(res.data, expect)):
        return res.data
    if res.kind == MISSING:
        return default
    if res.ok:
        res = ReadResult(False, None, TYPE, "неожиданный тип данных", path)
    _note_problem(res.kind, path, res.message)
    if quarantine_bad and res.kind in (SYNTAX, EMPTY, TYPE):
        quarantine(path)
    return default


#-- Запись

class SaveError(Exception):
    """Не удалось сохранить файл (текст — причина для пользователя)."""


def _dump(data, indent):
    return json.dumps(data, ensure_ascii=False, indent=indent, allow_nan=False)


def write_atomic(path, data, indent=1, retries=3):
    """Атомарная запись JSON. При ошибке бросает SaveError, старая версия файла остаётся нетронутой."""
    try:
        text = _dump(data, indent)
    except (TypeError, ValueError) as e:
        raise SaveError(f"данные нельзя сохранить: {e}")
    directory = os.path.dirname(os.path.abspath(path))
    tmp = os.path.join(directory, f".{os.path.basename(path)}.{os.getpid()}.tmp")
    try:
        os.makedirs(directory, exist_ok=True)
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(text)
            f.flush()
            try:
                os.fsync(f.fileno())
            except OSError:
                pass
        last = None
        for attempt in range(max(1, retries)):
            try:
                os.replace(tmp, path)
                return
            except PermissionError as e:           # Windows: файл на миг занят антивирусом/индексатором
                last = e
                time.sleep(0.05 * (attempt + 1))
        raise last
    except OSError as e:
        _note_problem("write", path, str(e))
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except OSError:
            pass
        raise SaveError(str(e))


def try_write(path, data, indent=1):
    """То же, но без исключения: возвращает (успех, текст_ошибки)."""
    try:
        write_atomic(path, data, indent)
        return True, ""
    except SaveError as e:
        return False, str(e)


#-- Карантин и резервные копии

def _stamp():
    return time.strftime("%Y%m%d-%H%M%S")


def _unique(path):
    if not os.path.exists(path):
        return path
    base, ext = os.path.splitext(path)
    i = 2
    while os.path.exists(f"{base}-{i}{ext}"):
        i += 1
    return f"{base}-{i}{ext}"


def quarantine(path):
    """Убирает повреждённый файл с дороги, не удаляя его. Возвращает новый путь или None."""
    if not os.path.exists(path):
        return None
    target = _unique(f"{path}.corrupt-{_stamp()}")
    try:
        os.replace(path, target)
    except OSError:
        try:
            import shutil
            shutil.copy2(path, target)
        except OSError:
            return None
    _prune(os.path.dirname(path), os.path.basename(path) + ".corrupt-", KEEP_CORRUPT)
    return target


def _prune(directory, prefix, keep):
    try:
        names = sorted(n for n in os.listdir(directory) if n.startswith(prefix))
    except OSError:
        return
    for name in names[:-keep] if keep > 0 else names:
        try:
            os.remove(os.path.join(directory, name))
        except OSError:
            pass


def backup_file(path, backup_dir, keep=5, tag=""):
    """Копирует текущий файл в backup_dir/<имя>.<время>.bak, оставляя последние keep копий.

    Возвращает путь копии или None (если файла нет или копия не удалась)."""
    if not os.path.isfile(path):
        return None
    name = os.path.basename(path)
    try:
        os.makedirs(backup_dir, exist_ok=True)
        import shutil
        target = _unique(os.path.join(backup_dir, f"{name}.{_stamp()}{tag}.bak"))
        shutil.copy2(path, target)
    except OSError as e:
        _note_problem("backup", path, str(e))
        return None
    _prune(backup_dir, name + ".", keep)
    return target


#-- Отпечатки содержимого

def canonical(data):
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def content_hash(data):
    try:
        return hashlib.sha1(canonical(data).encode("utf-8")).hexdigest()
    except (TypeError, ValueError):
        return ""


def file_sha1(path, limit=None):
    h = hashlib.sha1()
    try:
        with open(path, "rb") as f:
            while True:
                chunk = f.read(65536 if limit is None else min(65536, limit))
                if not chunk:
                    break
                h.update(chunk)
                if limit is not None:
                    limit -= len(chunk)
                    if limit <= 0:
                        break
    except OSError:
        return ""
    return h.hexdigest()


def is_finite_number(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)
