
#-- Импорт
import json
import os
import secrets

import config as C

DIR = C.root("achievements")
EXT = ".vcld"
NAME_MAX = 40
DESC_MAX = 200
IMAGE_MAX = 120
DEFAULT_NAME = "Достижение"


def _safe(text):
    keep = [ch if ch.isalnum() or ch in "-_" else "_" for ch in text]
    return "".join(keep)[:30] or "achievement"


def normalize(raw):
    if not isinstance(raw, dict):
        raw = {}
    name = str(raw.get("name", "")).strip()[:NAME_MAX] or DEFAULT_NAME
    desc = str(raw.get("description", "")).strip()[:DESC_MAX]
    image = str(raw.get("image", "")).strip()[:IMAGE_MAX]
    return {"name": name, "description": desc, "image": image}


def load(path):
    with open(path, "r", encoding="utf-8") as f:
        return normalize(json.load(f))


def list_all():
    out = []
    if not os.path.isdir(DIR):
        return out
    for fname in os.listdir(DIR):
        if not fname.lower().endswith(EXT):
            continue
        path = os.path.join(DIR, fname)
        try:
            out.append((path, load(path)))
        except (OSError, ValueError):
            continue
    out.sort(key=lambda item: item[1]["name"].lower())
    return out


def save(data, path=None):
    os.makedirs(DIR, exist_ok=True)
    data = normalize(data)
    if path is None:
        path = os.path.join(DIR, f"{_safe(data['name'])}__{secrets.token_hex(4)}{EXT}")
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    os.replace(tmp, path)
    return path


UNLOCKED_PATH = C.root("data", "achievements_unlocked.json")


def find(file_name):
    """Ачивка по имени файла (как хранится в чарте). None, если файла уже нет."""
    if not file_name:
        return None
    path = os.path.join(DIR, file_name)
    if not os.path.isfile(path):
        return None
    try:
        return load(path)
    except (OSError, ValueError):
        return None


_unlocked_cache = (None, set())


def _read_unlocked():
    try:
        with open(UNLOCKED_PATH, "r", encoding="utf-8") as f:
            raw = json.load(f)
        return set(str(x) for x in raw) if isinstance(raw, list) else set()
    except (OSError, ValueError):
        return set()


def unlocked_names():
    """Множество полученных ачивок. Файл перечитывается только когда он изменился (вызывается из кадра)."""
    global _unlocked_cache
    try:
        stamp = os.path.getmtime(UNLOCKED_PATH)
    except OSError:
        stamp = None
    if _unlocked_cache[0] != stamp:
        _unlocked_cache = (stamp, _read_unlocked() if stamp is not None else set())
    return _unlocked_cache[1]


def is_unlocked(file_name):
    return file_name in unlocked_names()


def unlock(file_name):
    """Отмечает ачивку полученной. Возвращает True, если она получена впервые."""
    done = _read_unlocked()
    if file_name in done:
        return False
    done.add(file_name)
    try:
        os.makedirs(os.path.dirname(UNLOCKED_PATH), exist_ok=True)
        tmp = UNLOCKED_PATH + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(sorted(done), f, ensure_ascii=False, indent=1)
        os.replace(tmp, UNLOCKED_PATH)
    except OSError:
        return False
    return True


def delete(path):
    try:
        os.remove(path)
    except OSError:
        pass
