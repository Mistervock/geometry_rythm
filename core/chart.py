
#-- Импорт
import copy
import hashlib

import jsonio
import validation as V

LANES = V.LANES
MIN_HOLD_MS = 150
FORMAT_VERSION = V.CHART_VERSION


class ChartFormatError(ValueError):
    """Чарт нельзя загрузить: критические ошибки в report."""

    def __init__(self, report, message=""):
        self.report = report
        super().__init__(message or report.first_error() or "bad chart")


class Note:
    __slots__ = ("t", "lane", "dur", "state", "hit_at", "grade", "early",
                 "held", "next_tick", "tail_ok", "vis", "idx")

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
        self.vis = 0.8          # сглаженная яркость тела удержания (только для отрисовки)
        self.idx = -1           # номер ноты в отсортированном чарте (для повторов и статистики)

    @property
    def end(self):
        return self.t + self.dur

    def key(self):
        return (self.t, self.lane, self.dur)

    def reset(self):
        self.state = "wait"
        self.hit_at = 0.0
        self.grade = None
        self.early = False
        self.held = False
        self.next_tick = 0.0
        self.tail_ok = False
        self.vis = 0.8


class Chart:
    def __init__(self, song, name="Чарт", notes=None, path=None, events=None,
                 charter="", difficulty=1, folders=None, achievement="", grid=None, chart_id="",
                 extra=None):
        self.song = song
        self.name = name
        self.charter = charter
        self.difficulty = max(1, min(5, int(difficulty)))
        self.notes = list(notes or [])
        self.events = list(events or [])
        self.folders = [dict(f) for f in (folders or [])]
        self.achievement = str(achievement or "")
        self.grid = dict(V.GRID_DEFAULT)
        if grid:
            self.grid.update(grid)
        self.id = chart_id or ""
        self.extra = dict(extra or {})
        self.path = path
        self.report = V.Report("chart")     # результат проверки при загрузке (для редактора и подготовки)
        self.source_version = FORMAT_VERSION

    #-- Идентичность

    @property
    def key(self):
        """Устойчивый ключ чарта для рекордов, побед, истории: имя файла (как в прежних версиях)."""
        import os
        return os.path.basename(self.path) if self.path else None

    def ensure_id(self):
        if not self.id:
            self.id = V.new_chart_id()
        return self.id

    def sort(self):
        self.notes.sort(key=lambda n: (n.t, n.lane))

    def copy_notes(self):
        out = [Note(n.t, n.lane, n.dur) for n in self.notes]
        for i, n in enumerate(out):
            n.idx = i
        return out

    def notes_hash(self):
        """Отпечаток нот: по нему Ghost узнаёт, что чарт изменился."""
        h = hashlib.sha1()
        for n in self.notes:
            h.update(f"{n.t},{n.lane},{n.dur};".encode("ascii"))
        return h.hexdigest()

    def content_hash(self):
        return jsonio.content_hash(self.to_dict(for_hash=True))

    #-- Сериализация

    def to_dict(self, for_hash=False):
        out = []
        for n in self.notes:
            item = {"t": n.t, "lane": n.lane}
            if n.dur:
                item["d"] = n.dur
            out.append(item)
        data = dict(self.extra)
        data.update({"version": FORMAT_VERSION, "id": self.id if (self.id or for_hash) else V.new_chart_id(),
                     "song": self.song, "name": self.name, "charter": self.charter,
                     "difficulty": self.difficulty, "grid": dict(self.grid), "notes": out})
        if not for_hash and not self.id:
            self.id = data["id"]
        if self.events:
            data["events"] = self.events
        if self.folders:
            data["folders"] = self.folders
        if self.achievement:
            data["achievement"] = self.achievement
        return data

    @staticmethod
    def from_clean(clean, path=None, report=None):
        notes = [Note(t, lane, d) for t, lane, d in clean["notes"]]
        chart = Chart(song=clean["song"], name=clean["name"], notes=notes, path=path,
                      events=copy.deepcopy(clean["events"]), charter=clean["charter"],
                      difficulty=clean["difficulty"], folders=clean["folders"],
                      achievement=clean["achievement"], grid=clean["grid"], chart_id=clean["id"],
                      extra=copy.deepcopy(clean.get("extra")))
        for i, n in enumerate(chart.notes):
            n.idx = i
        if report is not None:
            chart.report = report
        return chart

    @staticmethod
    def from_dict(data, path=None, duration_ms=None, image_exists=None):
        """Строгая проверка + мягкая загрузка. Критические ошибки → ChartFormatError."""
        clean, rep = V.check_chart(data, duration_ms=duration_ms, image_exists=image_exists)
        if clean is None:
            raise ChartFormatError(rep)
        return Chart.from_clean(clean, path=path, report=rep)

    @staticmethod
    def load_checked(path, duration_ms=None, image_exists=None):
        """Читает файл чарта. Никогда не бросает исключений: (chart | None, report)."""
        res = jsonio.read(path)
        if not res.ok:
            rep = V.Report("chart")
            code = {jsonio.MISSING: "json.missing", jsonio.ACCESS: "json.access"}.get(res.kind, "json.syntax")
            rep.error(code, detail=res.message)
            return None, rep
        clean, rep = V.check_chart(res.data, duration_ms=duration_ms, image_exists=image_exists)
        if clean is None:
            return None, rep
        return Chart.from_clean(clean, path=path, report=rep), rep

    @staticmethod
    def load(path):
        chart, rep = Chart.load_checked(path)
        if chart is None:
            raise ChartFormatError(rep)
        return chart
