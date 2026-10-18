
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


def delete(path):
    try:
        os.remove(path)
    except OSError:
        pass
