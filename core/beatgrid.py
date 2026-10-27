"""BPM-сетка редактора: помощник при расстановке нот, а не ограничение.

Сетка — это только способ редактирования. Она не хранится в нотах и не двигает их: смена BPM,
смещения или деления никогда не меняет время существующих нот. Привязка (snap) выключается целиком,
и тогда нота ставится в любое миллисекундное время; кроме того, клавиша-модификатор в редакторе
временно отключает привязку на одну операцию.

Время линий считается как offset + i * шаг от целого индекса i, поэтому ошибка float не накапливается
на длинных композициях: i-я линия получается одним умножением, а не i сложениями.
"""
import math

import validation as V

BEAT_DIVISIONS = (1, 2, 3, 4, 6, 8, 12, 16, 24, 32)
MS_STEPS = (10, 25, 50, 100, 200)
MAX_DRAW_LINES = 1500           # если линий больше, мелкие уровни не рисуем (иначе экран — сплошная заливка)

BAR, BEAT, SUB = "bar", "beat", "sub"


def round_ms(x):
    """Округление до целых миллисекунд «от половины вверх», одинаковое для любых знаков."""
    return int(math.floor(x + 0.5))


class BeatGrid:
    def __init__(self, data=None):
        self.set_from(data)

    #-- Данные

    def set_from(self, data):
        d = dict(V.GRID_DEFAULT)
        if isinstance(data, dict):
            d.update(data)
        self.mode = d["mode"] if d["mode"] in ("ms", "beat") else "ms"
        self.ms_step = int(V.clamp(int(d["ms_step"]), *V.GRID_LIMITS["ms_step"]))
        self.bpm = float(V.clamp(float(d["bpm"]), *V.GRID_LIMITS["bpm"]))
        self.offset = float(V.clamp(float(d["offset"]), *V.GRID_LIMITS["offset"]))
        self.div = int(V.clamp(int(d["div"]), *V.GRID_LIMITS["div"]))
        self.bar = int(V.clamp(int(d["bar"]), *V.GRID_LIMITS["bar"]))
        self.snap_on = bool(d["snap"])
        self.show_beats = bool(d["show_beats"])
        self.show_bars = bool(d["show_bars"])
        self.show_sub = bool(d["show_sub"])

    def to_dict(self):
        return {"mode": self.mode, "ms_step": self.ms_step, "bpm": round(self.bpm, 3),
                "offset": round(self.offset, 3), "div": self.div, "bar": self.bar, "snap": self.snap_on,
                "show_beats": self.show_beats, "show_bars": self.show_bars, "show_sub": self.show_sub}

    #-- Шаги

    @property
    def beat_ms(self):
        return 60000.0 / self.bpm

    @property
    def step_ms(self):
        if self.mode == "beat":
            return self.beat_ms / self.div
        return float(self.ms_step)

    def label(self):
        return f"1/{self.div}" if self.mode == "beat" else f"{self.ms_step} мс"

    def spec(self):
        return (self.mode, self.div if self.mode == "beat" else self.ms_step)

    def specs(self):
        out = [("beat", n) for n in BEAT_DIVISIONS]
        if self.mode == "beat" and self.div not in BEAT_DIVISIONS:
            out.append(("beat", self.div))       # пользовательское деление остаётся в цикле
            out.sort(key=lambda s: (s[0] != "beat", s[1]))
        out += [("ms", n) for n in MS_STEPS]
        if self.mode == "ms" and self.ms_step not in MS_STEPS:
            out.append(("ms", self.ms_step))
        return out

    def set_spec(self, spec):
        mode, value = spec
        if mode == "beat":
            self.mode, self.div = "beat", int(V.clamp(int(value), *V.GRID_LIMITS["div"]))
        else:
            self.mode, self.ms_step = "ms", int(V.clamp(int(value), *V.GRID_LIMITS["ms_step"]))

    def cycle(self, direction=1):
        specs = self.specs()
        cur = self.spec()
        i = specs.index(cur) if cur in specs else 0
        self.set_spec(specs[(i + direction) % len(specs)])

    def set_bpm(self, bpm):
        self.bpm = round(float(V.clamp(float(bpm), *V.GRID_LIMITS["bpm"])), 3)

    def set_offset(self, ms):
        self.offset = round(float(V.clamp(float(ms), *V.GRID_LIMITS["offset"])), 3)

    #-- Время и индексы

    def time_at(self, i):
        return self.offset + i * self.step_ms

    def index_near(self, t):
        return int(math.floor((t - self.offset) / self.step_ms + 0.5))

    def snap(self, t):
        """Ближайшая точка сетки (целые мс), даже если привязка выключена. Не ниже 0."""
        return max(0, round_ms(self.time_at(self.index_near(t))))

    def place(self, t, free=False):
        """Время новой ноты: точка сетки, если привязка включена и не отключена на эту операцию."""
        if self.snap_on and not free:
            return self.snap(t)
        return max(0, round_ms(t))

    def step_from(self, t, direction):
        """Следующая (direction=+1) или предыдущая (-1) точка сетки строго по другую сторону от t."""
        i = self.index_near(t)
        eps = 0.5
        if direction > 0:
            while self.time_at(i) <= t + eps:
                i += 1
        else:
            while self.time_at(i) >= t - eps:
                i -= 1
        return max(0.0, self.time_at(i))

    def beat_number(self, t):
        return (t - self.offset) / self.beat_ms

    def classify(self, i):
        if self.mode == "beat":
            if i % (self.div * self.bar) == 0:
                return BAR
            if i % self.div == 0:
                return BEAT
        return SUB

    def lines(self, t_lo, t_hi):
        """Линии сетки в окне [t_lo, t_hi]: [(время, вид)]. Пустой список, если окно слишком велико."""
        if t_hi < t_lo:
            return []
        step = self.step_ms
        out = []
        if self.mode == "beat":
            beat = self.beat_ms
            n_sub = (t_hi - t_lo) / step
            n_beat = (t_hi - t_lo) / beat
            draw_sub = self.show_sub and self.div > 1 and n_sub <= MAX_DRAW_LINES
            draw_beat = self.show_beats and n_beat <= MAX_DRAW_LINES
            draw_bar = self.show_bars and n_beat / self.bar <= MAX_DRAW_LINES
            i0 = int(math.floor((t_lo - self.offset) / step))
            i1 = int(math.ceil((t_hi - self.offset) / step))
            for i in range(i0, i1 + 1):
                kind = self.classify(i)
                if kind == BAR:
                    if not draw_bar:
                        kind = BEAT if draw_beat else None
                elif kind == BEAT:
                    kind = BEAT if draw_beat else None
                else:
                    kind = SUB if draw_sub else None
                if kind is not None:
                    out.append((self.time_at(i), kind))
            return out
        # режим «миллисекунды»: только мелкие линии, если их не слишком много
        if self.show_sub and (t_hi - t_lo) / step <= MAX_DRAW_LINES:
            i0 = int(math.floor((t_lo - self.offset) / step))
            i1 = int(math.ceil((t_hi - self.offset) / step))
            out = [(self.time_at(i), SUB) for i in range(i0, i1 + 1)]
        return out


def snap_changes(notes, grid):
    """Что изменится, если привязать ноты к сетке: [(нота, старое, новое)] только для сдвигаемых."""
    out = []
    for n in notes:
        new_t = grid.snap(n.t)
        if new_t != n.t:
            out.append((n, (n.t, n.lane, n.dur), (new_t, n.lane, n.dur)))
    return out
