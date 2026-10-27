"""Игровая логика без графики и звука: нажатия, оценки, удержания, HP, очки, повтор участка.

Время — «время чарта» в миллисекундах (при замедлении практики песня идёт медленнее, а окна оценок
остаются в миллисекундах чарта). Движок ничего не знает о pygame, часах и файлах: ему передают
текущее время, поэтому его можно проверять без игры и использовать для проигрывания повторов.

События для оформления (частицы, звуки, всплывающие надписи) уходят в sink(kind, **data).
"""
from collections import deque

import config as C
import scoring

HOLD_TICK_MS = 200
HOLD_TICK_POINTS = 10
HOLD_BONUS = 150
GRADE_POINTS = {"perfect": 300, "great": 200, "good": 100}
END_MARGIN_MS = 1200
SECTION_MARGIN_MS = 400
MAX_INPUT_LOG = 40000


class Judgment:
    """Решение по одной ноте: оценка головы, отклонение (мс, «+» — поздно) и итог хвоста удержания."""
    __slots__ = ("idx", "lane", "t", "grade", "offset", "at", "tail")

    def __init__(self, idx, lane, t, grade, offset, at):
        self.idx = idx
        self.lane = lane
        self.t = t
        self.grade = grade
        self.offset = offset
        self.at = at
        self.tail = None

    def to_list(self):
        return [self.idx, self.lane, self.t, self.grade, round(self.offset, 2), round(self.at, 1), self.tail]

    @staticmethod
    def from_list(row):
        j = Judgment(row[0], row[1], row[2], row[3], row[4], row[5])
        j.tail = row[6]
        return j


def _noop(kind, **data):
    return None


class Engine:
    def __init__(self, notes, heals=(), duration=0, max_hp=C.MAX_HP, practice=False, hp_loss=True,
                 sink=_noop, section=None):
        self.notes = notes
        self.heals_src = [dict(h) for h in heals]
        self.duration = int(duration)
        self.max_hp = max_hp
        self.practice = practice
        self.hp_loss = hp_loss          # только для практики: терять ли HP (но проиграть там нельзя)
        self.sink = sink
        self.sect_a, self.sect_b = (None, None) if section is None else (int(section[0]), int(section[1]))
        self.attempt = 0
        self.start_attempt()

    #-- Подготовка прохода

    def set_section(self, a, b):
        """Участок для практики [a, b] в мс чарта. None — вся песня."""
        self.sect_a, self.sect_b = (None, None) if a is None else (int(a), int(b))

    def _in_section(self, t):
        return self.sect_a is None or self.sect_a <= t <= self.sect_b

    def start_attempt(self):
        """Чистое состояние: ничего не переносится из прошлого повтора (очки, комбо, HP, удержания, события)."""
        self.attempt += 1
        for n in self.notes:
            n.reset()
            if not self._in_section(n.t):
                n.state = "skip"
        self.active = [n for n in self.notes if n.state != "skip"]
        self.total = len(self.active)
        self.pending = [deque(n for n in self.active if n.lane == i) for i in range(4)]
        self.holds = []
        self.held = [False] * 4
        self.heals = [dict(h, state="wait", hit_at=0.0) for h in self.heals_src if self._in_section(h["t"])]
        self.heals.sort(key=lambda h: h["t"])
        self.hp = self.max_hp
        self.combo = 0
        self.max_combo = 0
        self.score = 0
        self.counts = {"perfect": 0, "great": 0, "good": 0, "miss": 0}
        self.holds_ok = 0
        self.holds_broken = 0
        self.judgments = []
        self.timeline = []              # (время, очки, комбо) после каждого решения — для Ghost
        self._by_note = {}
        self.inputs = []
        self.now = 0.0
        self.done = False
        self.failed = False
        last = max((n.end for n in self.active), default=0)
        if self.sect_a is None:
            self.end_time = last + END_MARGIN_MS
        else:
            self.end_time = max(self.sect_b, last) + SECTION_MARGIN_MS

    @property
    def section(self):
        return (self.sect_a, self.sect_b)

    @property
    def last_note_end(self):
        return max((n.end for n in self.active), default=0)

    def _emit(self, kind, **data):
        self.sink(kind, **data)

    def _snap(self):
        if len(self.timeline) < MAX_INPUT_LOG:
            self.timeline.append((round(self.now, 1), self.score, self.combo))

    def _mult(self):
        return 1 + min(self.combo // 10, 3)

    #-- Ввод

    def press(self, lane, now):
        if self.done:
            return None
        self.now = now
        self.held[lane] = True
        if len(self.inputs) < MAX_INPUT_LOG:
            self.inputs.append((round(now, 1), lane, 1))
        self._emit("press", lane=lane)
        for h in self.heals:
            if h["state"] == "wait" and h["lane"] == lane and abs(now - h["t"]) <= C.WIN_GOOD:
                h["state"] = "hit"
                h["hit_at"] = now
                self.hp = min(self.max_hp, self.hp + 1)
                self._emit("heal_hit", heal=h)
                break
        q = self.pending[lane]
        best = None
        best_note = None
        for i, n in enumerate(q):
            if i >= 3:
                break
            d = now - n.t
            if abs(d) <= C.WIN_GOOD and (best is None or abs(d) < abs(best)):
                best, best_note = d, n
        if best is None:
            return None
        q.remove(best_note)
        a = abs(best)
        grade = "perfect" if a <= C.WIN_PERFECT else "great" if a <= C.WIN_GREAT else "good"
        best_note.early = best < 0
        self._hit(best_note, grade, best)
        return best_note

    def release(self, lane, now):
        if self.done:
            return
        self.now = now
        self.held[lane] = False
        if len(self.inputs) < MAX_INPUT_LOG:
            self.inputs.append((round(now, 1), lane, 0))
        for n in list(self.holds):
            if n.lane == lane and n.state == "hold" and n.held:
                n.held = False
                if now >= n.end - C.WIN_GOOD:
                    self._hold_success(n)
                else:
                    self._hold_break(n)

    def sync_held(self, pressed):
        """После паузы: клавиши, отпущенные пока шла пауза, считаются отпущенными в момент возобновления."""
        for lane in range(4):
            now_down = bool(pressed[lane])
            if self.held[lane] and not now_down:
                self.release(lane, self.now)
            else:
                self.held[lane] = now_down

    #-- Время

    def update(self, now):
        if self.done:
            return
        self.now = now
        for h in self.heals:
            if h["state"] == "wait" and now - h["t"] > C.WIN_GOOD:
                h["state"] = "miss"
                h["hit_at"] = now
                self._emit("heal_miss", heal=h)
        self.heals = [h for h in self.heals if h["state"] == "wait" or now - h["hit_at"] < 0.4 * 1000]

        for lane in range(4):
            q = self.pending[lane]
            while q and now - q[0].t > C.WIN_GOOD:
                self._miss(q.popleft())
                if self.done:
                    return

        for n in list(self.holds):
            if n.state != "hold":
                self.holds.remove(n)
                continue
            if not n.held:
                self._hold_break(n)
                continue
            # тики по расписанию от момента попадания: результат не зависит от частоты кадров
            limit = min(now, n.end)
            while n.next_tick <= limit and n.next_tick < n.end:
                self.score += HOLD_TICK_POINTS * self._mult()
                n.next_tick += HOLD_TICK_MS
            if now >= n.end:
                self._hold_success(n)

        if now > self.end_time and not any(self.pending) and not self.holds:
            self._finish()
        elif self.sect_a is None and now >= self.duration > 0 and now > self.last_note_end:
            self._finish()

    #-- Решения

    def _hit(self, n, grade, offset):
        self.score += GRADE_POINTS[grade] * self._mult()
        self.combo += 1
        self.max_combo = max(self.max_combo, self.combo)
        self.counts[grade] += 1
        n.grade = grade
        n.hit_at = self.now
        j = Judgment(n.idx, n.lane, n.t, grade, offset, self.now)
        self.judgments.append(j)
        self._by_note[id(n)] = j
        if n.dur > 0:
            n.state = "hold"
            n.held = self.held[n.lane]
            n.next_tick = self.now + HOLD_TICK_MS
            self.holds.append(n)
        else:
            n.state = "hit"
        self._snap()
        self._emit("hit", note=n, grade=grade, offset=offset)

    def _hold_success(self, n):
        n.held = False
        n.state = "hit"
        n.tail_ok = True
        n.hit_at = self.now
        self.score += HOLD_BONUS * self._mult()
        self.holds_ok += 1
        j = self._by_note.get(id(n))
        if j is not None:
            j.tail = "ok"
        if n in self.holds:
            self.holds.remove(n)
        self._snap()
        self._emit("hold_ok", note=n)

    def _hold_break(self, n):
        n.held = False
        n.state = "broken"
        n.hit_at = self.now
        self.combo = 0
        self.holds_broken += 1
        j = self._by_note.get(id(n))
        if j is not None:
            j.tail = "broken"
        if n in self.holds:
            self.holds.remove(n)
        self._snap()
        self._emit("hold_break", note=n)

    def _miss(self, n):
        n.state = "miss"
        n.grade = "miss"
        n.hit_at = self.now
        self.counts["miss"] += 1
        self.combo = 0
        j = Judgment(n.idx, n.lane, n.t, "miss", float(C.WIN_GOOD), self.now)
        self.judgments.append(j)
        if not self.practice or self.hp_loss:
            self.hp -= 1
            if self.practice:
                self.hp = max(1, self.hp)           # в практике проиграть нельзя
        self._snap()
        self._emit("miss", note=n)
        if self.hp <= 0 and not self.practice:
            self.failed = True
            self._finish()

    def _finish(self):
        if self.done:
            return
        self.done = True
        self._emit("done", failed=self.failed)

    def abort(self):
        """Принудительное завершение (выход из практики, сброс участка)."""
        self.done = True

    #-- Итоги

    def accuracy(self):
        return scoring.accuracy(self.judgments)

    def summary(self):
        a, b = self.section
        return scoring.summarize(
            self.judgments, total=self.total, score=self.score, max_combo=self.max_combo,
            failed=self.failed, counts=self.counts, holds_ok=self.holds_ok,
            holds_broken=self.holds_broken, t_lo=a if a is not None else 0,
            t_hi=b if b is not None else max(self.last_note_end, 1))
