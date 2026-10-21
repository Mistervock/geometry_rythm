
#-- Импорт
import json
import math
import os
import secrets

import pygame

import autochart
import chart as chartmod
import config as C

SONG_DIR = C.root("songs")
CHART_DIR = C.root("data", "charts")
INFO_DIR = C.root("data", "songinfo")
META_DIR = C.root("data", "songmeta")
LEGACY_CHART = C.root("data", "chart.json")
EXTS = (".ogg", ".mp3", ".wav")


def list_songs():
    if not os.path.isdir(SONG_DIR):
        return []
    names = [f for f in os.listdir(SONG_DIR) if f.lower().endswith(EXTS)]
    return sorted(names, key=str.lower)


def title(song):
    return os.path.splitext(song)[0].replace("_", " ")


def meta(song):
    path = os.path.join(META_DIR, _safe(song) + ".json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def save_meta(song, data):
    os.makedirs(META_DIR, exist_ok=True)
    path = os.path.join(META_DIR, _safe(song) + ".json")
    clean = {k: str(v).strip() for k, v in data.items() if str(v).strip()}
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(clean, f, ensure_ascii=False, indent=1)
    os.replace(tmp, path)


def update_meta(song, **fields):
    """Меняет только переданные поля; остальные (например, картинка) сохраняются."""
    data = meta(song)
    data.update(fields)
    save_meta(song, data)


def display_title(song):
    return meta(song).get("title") or title(song)


def song_path(song):
    return os.path.join(SONG_DIR, song)


def _safe(text):
    keep = [ch if ch.isalnum() or ch in "-_" else "_" for ch in text]
    return "".join(keep)[:40] or "song"


def charts_for(song):
    result = []
    if not os.path.isdir(CHART_DIR):
        return result
    for fname in os.listdir(CHART_DIR):
        if not fname.endswith(".json"):
            continue
        path = os.path.join(CHART_DIR, fname)
        try:
            ch = chartmod.Chart.load(path)
        except Exception:
            continue
        if ch.song == song:
            result.append(ch)
    result.sort(key=lambda c: c.name.lower())
    return result


def new_chart(song, name=None):
    existing = {c.name for c in charts_for(song)}
    base = name or "Чарт"
    n, final = 1, base
    while final in existing:
        n += 1
        final = f"{base} {n}"
    return chartmod.Chart(song=song, name=final)


def save_chart(ch):
    os.makedirs(CHART_DIR, exist_ok=True)
    if ch.path is None:
        ch.path = os.path.join(CHART_DIR, f"{_safe(ch.song)}__{secrets.token_hex(4)}.json")
    ch.sort()
    tmp = ch.path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(ch.to_dict(), f, ensure_ascii=False, indent=1)
    os.replace(tmp, ch.path)
    return ch.path


def delete_chart(ch):
    if ch.path and os.path.exists(ch.path):
        try:
            os.remove(ch.path)
        except OSError:
            pass
        forget_rank(ch)


def info(song):
    os.makedirs(INFO_DIR, exist_ok=True)
    cache = os.path.join(INFO_DIR, _safe(song) + ".json")
    if os.path.exists(cache):
        try:
            with open(cache, "r", encoding="utf-8") as f:
                data = json.load(f)
            if data.get("duration_ms"):
                return data
        except Exception:
            pass
    data = None
    if autochart.AVAILABLE:
        data = autochart.energy_only(song_path(song))
    if data is None:
        try:
            length = pygame.mixer.Sound(song_path(song)).get_length()
        except Exception:
            length = 0.0
        data = {"duration_ms": int(length * 1000), "energy": [], "energy_fps": 21.5}
    try:
        with open(cache, "w", encoding="utf-8") as f:
            json.dump(data, f)
    except OSError:
        pass
    return data


def migrate_legacy():
    if not os.path.exists(LEGACY_CHART) or not os.path.exists(os.path.join(SONG_DIR, "game.ogg")):
        return
    if charts_for("game.ogg"):
        return
    try:
        with open(LEGACY_CHART, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return
    ch = chartmod.Chart.from_dict({"song": "game.ogg", "name": "Авто", "notes": data.get("notes", [])})
    save_chart(ch)


#-- Обложки, авторы и цвета

IMAGE_DIR = C.root("images")
AUTHOR_COLORS_PATH = C.root("data", "author_colors.json")
WINS_PATH = C.root("data", "wins.json")
RANKS_PATH = C.root("data", "ranks.json")
AUTOSAVE_DIR = C.root("data", "autosave")
EXPORT_DIR = C.root("exports")
_cover_cache = {}


def cover_path(song):
    """Картинка песни из папки images/ (поле image в songmeta); None, если не задана или файла нет."""
    name = meta(song).get("image", "")
    if not name:
        return None
    path = os.path.join(IMAGE_DIR, name)
    return path if os.path.isfile(path) else None


def cover_surface(song):
    """Обложка на весь экран, с обрезкой по краям (16:9 и любые другие пропорции)."""
    path = cover_path(song)
    if path is None:
        return None
    key = (path, C.WIDTH, C.HEIGHT)
    surf = _cover_cache.get(key)
    if surf is None:
        if len(_cover_cache) > 4:
            _cover_cache.clear()
        try:
            src = pygame.image.load(path).convert()
        except (pygame.error, OSError):
            return None
        sw, sh = src.get_size()
        scale = max(C.WIDTH / sw, C.HEIGHT / sh)
        w, h = max(1, round(sw * scale)), max(1, round(sh * scale))
        big = pygame.transform.smoothscale(src, (w, h))
        surf = pygame.Surface((C.WIDTH, C.HEIGHT))
        surf.blit(big, ((C.WIDTH - w) // 2, (C.HEIGHT - h) // 2))
        _cover_cache[key] = surf
    return surf


def _read_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


_json_cache = {}


def _read_json_cached(path, default):
    """Чтение с кэшем по времени изменения: файлы побед и рангов читаются в каждом кадре списка."""
    try:
        st = os.stat(path)
        sig = (st.st_mtime_ns, st.st_size)
    except OSError:
        return default
    hit = _json_cache.get(path)
    if hit and hit[0] == sig:
        return hit[1]
    data = _read_json(path, default)
    _json_cache[path] = (sig, data)
    return data


def _write_json(path, data):
    _json_cache.pop(path, None)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    os.replace(tmp, path)


def author_of(song):
    return meta(song).get("artist", "")


def all_authors():
    return sorted({author_of(s) for s in list_songs() if author_of(s)}, key=str.lower)


def author_color(author):
    """Цвет фона для автора (RGB) или None."""
    raw = _read_json(AUTHOR_COLORS_PATH, {})
    col = raw.get(author) if isinstance(raw, dict) else None
    if isinstance(col, list) and len(col) == 3:
        return tuple(int(c) for c in col)
    return None


def set_author_color(author, rgb):
    raw = _read_json(AUTHOR_COLORS_PATH, {})
    if not isinstance(raw, dict):
        raw = {}
    if rgb is None:
        raw.pop(author, None)
    else:
        raw[author] = list(rgb)
    _write_json(AUTHOR_COLORS_PATH, raw)


def _won_set():
    raw = _read_json_cached(WINS_PATH, [])
    return set(raw) if isinstance(raw, list) else set()


def is_won(ch):
    return bool(ch.path) and os.path.basename(ch.path) in _won_set()


def mark_win(ch):
    """Чарт пройден (финиш). Возвращает True, если это первая победа на этом чарте."""
    if not ch.path:
        return False
    done = _won_set()
    key = os.path.basename(ch.path)
    if key in done:
        return False
    done.add(key)
    _write_json(WINS_PATH, sorted(done))
    return True


def song_win_state(song):
    """0 — ни один чарт не пройден, 1 — часть, 2 — все чарты песни пройдены."""
    charts = charts_for(song)
    if not charts:
        return 0
    won = [is_won(c) for c in charts]
    if all(won):
        return 2
    return 1 if any(won) else 0


def all_charts():
    out = []
    if not os.path.isdir(CHART_DIR):
        return out
    for fname in sorted(os.listdir(CHART_DIR)):
        if fname.endswith(".json"):
            try:
                out.append(chartmod.Chart.load(os.path.join(CHART_DIR, fname)))
            except Exception:
                continue
    return out


#-- Экспорт, импорт, автосохранение

def _file_stem(text):
    keep = [ch if ch.isalnum() or ch in " -_" else "_" for ch in text]
    return "".join(keep).strip()[:60] or "chart"


def export_chart(ch):
    """Чарт в файл exports/<название>.json. Возвращает путь."""
    os.makedirs(EXPORT_DIR, exist_ok=True)
    path = os.path.join(EXPORT_DIR, _file_stem(ch.name) + ".json")
    _write_json(path, ch.to_dict())
    return path


def export_files():
    if not os.path.isdir(EXPORT_DIR):
        return []
    return sorted(f for f in os.listdir(EXPORT_DIR) if f.lower().endswith(".json"))


def import_chart(file_name):
    """Импорт из exports/ как нового чарта. Возвращает чарт (уже сохранён) или ValueError с причиной."""
    path = os.path.join(EXPORT_DIR, file_name)
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        raise ValueError("bad_file")
    if not isinstance(data, dict) or not data.get("song"):
        raise ValueError("bad_file")
    if not os.path.isfile(song_path(str(data["song"]))):
        raise ValueError("no_song")
    ch = chartmod.Chart.from_dict(data)
    ch.path = None
    ch.name = (ch.name or "Чарт") + " (импорт)"
    save_chart(ch)
    return ch


def autosave_chart(ch):
    """Автосохранение: data/autosave/<название чарта>-autosave.json (в список чартов не попадает)."""
    path = os.path.join(AUTOSAVE_DIR, _file_stem(ch.name) + "-autosave.json")
    _write_json(path, ch.to_dict())
    return path


#-- Ранги: лучший результат на чарт и общий ранг песни

RANKS = ("D", "C", "B", "A", "S")          # от худшего к лучшему; провал ранга не получает
RANK_POINTS = {g: i + 1 for i, g in enumerate(RANKS)}


def _ranks():
    raw = _read_json_cached(RANKS_PATH, {})
    return raw if isinstance(raw, dict) else {}


def _rank_key(ch):
    return os.path.basename(ch.path) if ch.path else None


def chart_best(ch, ranks=None):
    """Лучший результат на чарте: {"grade", "acc", "score"} или None."""
    key = _rank_key(ch)
    entry = (_ranks() if ranks is None else ranks).get(key) if key else None
    if isinstance(entry, dict) and entry.get("grade") in RANK_POINTS:
        return entry
    return None


def chart_rank(ch, ranks=None):
    best = chart_best(ch, ranks)
    return best["grade"] if best else None


def record_rank(ch, grade, acc, score):
    """Записывает результат победы. Возвращает (новый_рекорд, прежний_ранг)."""
    key = _rank_key(ch)
    if key is None or grade not in RANK_POINTS:
        return False, None
    raw = _ranks()
    old = raw.get(key) if isinstance(raw.get(key), dict) else None
    old_grade = old.get("grade") if old else None
    better = (old is None or old_grade not in RANK_POINTS
              or (RANK_POINTS[grade], acc) > (RANK_POINTS[old_grade], float(old.get("acc", 0))))
    if better:
        raw[key] = {"grade": grade, "acc": round(float(acc), 2), "score": int(score)}
        _write_json(RANKS_PATH, raw)
    return better, old_grade if old_grade in RANK_POINTS else None


def forget_rank(ch):
    key = _rank_key(ch)
    raw = _ranks()
    if key in raw:
        del raw[key]
        _write_json(RANKS_PATH, raw)


def combine_ranks(grades):
    """Общий ранг по списку рангов чартов (None — чарт не пройден).

    Ранги переводятся в баллы D=1 … S=5, непройденный чарт даёт 0, берётся среднее
    с округлением вниз при .5 (S и A дают A). Если пройден хотя бы один чарт, ранг не ниже D.
    Песня целиком получает S, только когда все её чарты пройдены на S."""
    grades = list(grades)
    if not grades or all(g is None for g in grades):
        return None
    avg = sum(RANK_POINTS.get(g, 0) for g in grades) / len(grades)
    idx = math.ceil(avg - 0.5)
    return RANKS[max(1, min(len(RANKS), idx)) - 1]


def song_rank(song, charts=None, ranks=None):
    ranks = _ranks() if ranks is None else ranks
    charts = charts_for(song) if charts is None else charts
    return combine_ranks(chart_rank(c, ranks) for c in charts)
