"""Избранное и история запусков.

Хранится в data/library.json (атомарная запись, повреждённый файл уходит в карантин и не затирается):

  favorites.songs   — стабильные id песен (отпечаток содержимого файла, а не имя файла);
  favorites.charts  — ссылки на чарты (id чарта из файла, а для старых чартов — имя файла);
  history           — запуски: начало, окончание, итог. Запуск без завершения — это НЕ успех:
                      у него нет результата, он помечен «не завершён».

Переименование/перенос файла песни не теряет избранное (id берётся из содержимого). Удалённая песня остаётся
в списках как «нет файла»: открыть её нельзя, запись можно удалить. История ограничена HISTORY_LIMIT записями.
"""
import hashlib
import os
import secrets
import time

import config as C
import jsonio

PATH = C.root("data", "library.json")
VERSION = 1
HISTORY_LIMIT = 200
FP_BYTES = 65536

_fp_cache = {}                     # (путь, размер, mtime) → id


def song_id(song):
    """Устойчивый id песни: sha1(начало + конец + размер файла). Без файла — запасной id по имени."""
    import songs
    path = songs.song_path(song)
    try:
        st = os.stat(path)
    except OSError:
        return "name:" + song
    key = (path, st.st_size, int(st.st_mtime))
    if key in _fp_cache:
        return _fp_cache[key]
    try:
        h = hashlib.sha1()
        with open(path, "rb") as f:
            h.update(f.read(FP_BYTES))
            if st.st_size > FP_BYTES * 2:
                f.seek(-FP_BYTES, os.SEEK_END)
                h.update(f.read(FP_BYTES))
        h.update(str(st.st_size).encode())
        sid = "fp:" + h.hexdigest()[:20]
    except OSError:
        sid = "name:" + song
    _fp_cache[key] = sid
    return sid


def chart_ref(chart):
    """Ссылка на чарт: id из файла (переживает переименование файла) либо имя файла."""
    if chart.id:
        return "id:" + chart.id
    return "file:" + (chart.key or chart.name)


def chart_refs(chart):
    out = []
    if chart.id:
        out.append("id:" + chart.id)
    if chart.key:
        out.append("file:" + chart.key)
    return out or ["file:" + chart.name]


#-- Загрузка / проверка

def _str_list(v, limit=5000):
    out, seen = [], set()
    if isinstance(v, list):
        for x in v:
            if isinstance(x, str) and 0 < len(x) <= 200 and x not in seen:
                seen.add(x)
                out.append(x)
    return out[:limit]


def _num(v, default=0.0):
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) and v == v and abs(v) < 1e12 \
        else default


def _entry(raw):
    if not isinstance(raw, dict) or not isinstance(raw.get("id"), str) or not raw["id"]:
        return None
    res = raw.get("result")
    if isinstance(res, dict):
        res = {"score": int(_num(res.get("score"))), "acc": round(_num(res.get("acc")), 2),
               "grade": res.get("grade") if res.get("grade") in ("S", "A", "B", "C", "D", "F") else "D",
               "failed": res.get("failed") is True}
    else:
        res = None
    return {
        "id": raw["id"][:40], "kind": "practice" if raw.get("kind") == "practice" else "play",
        "song": str(raw.get("song", ""))[:200], "song_id": str(raw.get("song_id", ""))[:60],
        "song_title": str(raw.get("song_title", ""))[:80], "chart_ref": str(raw.get("chart_ref", ""))[:200],
        "chart_file": str(raw.get("chart_file", ""))[:200], "chart_name": str(raw.get("chart_name", ""))[:40],
        "started": _num(raw.get("started")), "finished": _num(raw.get("finished")) or None, "result": res,
    }


def sanitize(raw):
    fav = raw.get("favorites") if isinstance(raw, dict) else None
    fav = fav if isinstance(fav, dict) else {}
    hist = []
    seen = set()
    for item in (raw.get("history") if isinstance(raw, dict) and isinstance(raw.get("history"), list) else []):
        e = _entry(item)
        if e and e["id"] not in seen:
            seen.add(e["id"])
            hist.append(e)
    hist.sort(key=lambda e: e["started"])
    return {"v": VERSION, "favorites": {"songs": _str_list(fav.get("songs")), "charts": _str_list(fav.get("charts"))},
            "history": hist[-HISTORY_LIMIT:]}


class Library:
    """Состояние в памяти + сохранение. Один экземпляр на запуск игры (см. get())."""

    def __init__(self, path=None):
        self.path = path or PATH
        self.data = sanitize(jsonio.load(self.path, {}, expect=dict))
        self.error = ""

    def save(self):
        ok, err = jsonio.try_write(self.path, self.data)
        self.error = "" if ok else err
        return ok

    #-- Избранное

    def is_favorite_song(self, song):
        return song_id(song) in self.data["favorites"]["songs"]

    def toggle_favorite_song(self, song):
        sid = song_id(song)
        lst = self.data["favorites"]["songs"]
        if sid in lst:
            lst.remove(sid)
            state = False
        else:
            lst.append(sid)
            state = True
        self.save()
        return state

    def is_favorite_chart(self, chart):
        lst = self.data["favorites"]["charts"]
        return any(r in lst for r in chart_refs(chart))

    def toggle_favorite_chart(self, chart):
        lst = self.data["favorites"]["charts"]
        refs = chart_refs(chart)
        if any(r in lst for r in refs):
            for r in refs:
                while r in lst:
                    lst.remove(r)
            state = False
        else:
            lst.append(refs[0])
            state = True
        self.save()
        return state

    def favorite_song_ids(self):
        return set(self.data["favorites"]["songs"])

    #-- История

    def start_run(self, chart, kind="play"):
        import songs
        e = {"id": secrets.token_hex(6), "kind": "practice" if kind == "practice" else "play",
             "song": chart.song, "song_id": song_id(chart.song), "song_title": songs.display_title(chart.song),
             "chart_ref": chart_ref(chart), "chart_file": chart.key or "", "chart_name": chart.name,
             "started": time.time(), "finished": None, "result": None}
        self.data["history"].append(e)
        del self.data["history"][:-HISTORY_LIMIT]
        self.save()
        return e["id"]

    def finish_run(self, entry_id, outcome):
        for e in reversed(self.data["history"]):
            if e["id"] == entry_id:
                e["finished"] = time.time()
                e["result"] = {"score": int(outcome.get("score", 0)), "acc": round(float(outcome.get("acc", 0.0)), 2),
                               "grade": outcome.get("grade", "D"), "failed": bool(outcome.get("failed"))}
                self.save()
                return True
        return False

    def history(self):
        return list(reversed(self.data["history"]))

    def delete_entry(self, entry_id):
        before = len(self.data["history"])
        self.data["history"] = [e for e in self.data["history"] if e["id"] != entry_id]
        if len(self.data["history"]) != before:
            self.save()
            return True
        return False

    def clear_history(self):
        self.data["history"] = []
        self.save()

    def resolve(self, entry):
        """Находит песню и чарт для записи истории: (песня, чарт) или None, если файлов больше нет."""
        import songs
        names = songs.list_songs()
        song = entry["song"] if entry["song"] in names else None
        if song is None and entry["song_id"].startswith("fp:"):
            song = next((n for n in names if song_id(n) == entry["song_id"]), None)
        if song is None:
            return None
        for ch in songs.charts_for(song):
            if chart_ref(ch) == entry["chart_ref"] or (entry["chart_file"] and ch.key == entry["chart_file"]):
                return song, ch
        return None


_lib = None


def get():
    global _lib
    if _lib is None:
        _lib = Library()
    return _lib


def reset_for_tests(path=None):
    global _lib
    _lib = Library(path) if path else None
    _fp_cache.clear()
