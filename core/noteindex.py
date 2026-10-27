"""Быстрый поиск нот по времени: окно видимости, ближайшая нота.

Индекс строится один раз на изменение списка нот. Для видимого окна [t_lo, t_hi] нужны ноты, которые
НАЧИНАЮТСЯ до t_hi и ЗАКАНЧИВАЮТСЯ после t_lo (удержания могут быть длинными). Для этого рядом с
временами начала хранится «бегущий максимум конца» — он не убывает, значит работает бинарный поиск.
"""
import bisect


class NoteIndex:
    __slots__ = ("notes", "times", "run_end", "lanes")

    def __init__(self, notes):
        self.notes = notes
        self.times = [n.t for n in notes]
        run, best = [], -1
        for n in notes:
            e = n.t + n.dur
            if e > best:
                best = e
            run.append(best)
        self.run_end = run
        self.lanes = None

    def window(self, t_lo, t_hi):
        """Полуоткрытый диапазон индексов [i0, i1): ноты, которые могут быть видны в окне времени."""
        i0 = bisect.bisect_left(self.run_end, t_lo)
        i1 = bisect.bisect_right(self.times, t_hi)
        return i0, max(i0, i1)

    def visible(self, t_lo, t_hi):
        i0, i1 = self.window(t_lo, t_hi)
        for n in self.notes[i0:i1]:
            if n.t + n.dur >= t_lo:
                yield n

    def _lane_lists(self):
        if self.lanes is None:
            self.lanes = [([], []) for _ in range(4)]
            for n in self.notes:
                self.lanes[n.lane][0].append(n.t)
                self.lanes[n.lane][1].append(n)
        return self.lanes

    def nearest(self, t, lane=None, limit=250):
        """Ближайшая по времени начала нота (в пределах limit мс) на дорожке или среди всех."""
        if lane is None:
            times, notes = self.times, self.notes
        else:
            times, notes = self._lane_lists()[lane]
        i = bisect.bisect_left(times, t)
        best = None
        for j in (i - 1, i):
            if 0 <= j < len(times):
                d = abs(times[j] - t)
                if d <= limit and (best is None or d < best[0]):
                    best = (d, notes[j])
        return best[1] if best else None

    def in_range(self, t_lo, t_hi, lanes=None):
        """Ноты, начало которых лежит в [t_lo, t_hi] (для рамки выделения)."""
        i0 = bisect.bisect_left(self.times, t_lo)
        i1 = bisect.bisect_right(self.times, t_hi)
        out = self.notes[i0:i1]
        if lanes is not None:
            out = [n for n in out if n.lane in lanes]
        return out
