"""Подсчёт точности, ранга и подробной статистики попаданий.

Все числа считаются по журналу реальных судейских решений движка (engine.Judgment),
а не по счётчикам интерфейса. Модуль не зависит от pygame: его можно проверять обычными тестами.

Точность: каждая нота-«голова» даёт вес по оценке (PERFECT 1, GREAT 0.75, GOOD 0.5, MISS 0).
Удержание добавляет ещё одно решение — «хвост»: удержано до конца = 1, сорвано = 0.
Если голова пропущена, хвост отдельно не считается (это один MISS).
"""
import math

import config as C

ACC_WEIGHT = {"perfect": 1.0, "great": 0.75, "good": 0.5, "miss": 0.0}
TAIL_WEIGHT = {"ok": 1.0, "broken": 0.0}
GRADE_ORDER = ("D", "C", "B", "A", "S")
HIST_BIN_MS = 10
SERIES_BUCKETS = 24
SCATTER_MAX = 600


def grade_for(acc, failed=False):
    if failed:
        return "F"
    if acc >= 95:
        return "S"
    if acc >= 85:
        return "A"
    if acc >= 70:
        return "B"
    if acc >= 50:
        return "C"
    return "D"


def decisions(judgments):
    """Список (вес, время ноты, ошибка?) для каждого решения: голова и (если есть) хвост."""
    out = []
    for j in judgments:
        out.append((ACC_WEIGHT[j.grade], j.t, j.grade == "miss"))
        if j.tail is not None:
            out.append((TAIL_WEIGHT[j.tail], j.t, j.tail == "broken"))
    return out


def accuracy(judgments):
    dec = decisions(judgments)
    if not dec:
        return 0.0
    return 100.0 * sum(w for w, _, _ in dec) / len(dec)


def _mean(xs):
    return sum(xs) / len(xs) if xs else 0.0


def _std(xs, mean):
    if len(xs) < 2:
        return 0.0
    return math.sqrt(sum((x - mean) ** 2 for x in xs) / len(xs))


def histogram(offsets, win=C.WIN_GOOD, bin_ms=HIST_BIN_MS):
    n = int(math.ceil(win / bin_ms))
    bins = [0] * (2 * n)
    for o in offsets:
        i = int(math.floor(o / bin_ms)) + n
        bins[max(0, min(2 * n - 1, i))] += 1
    return {"bin_ms": bin_ms, "start": -n * bin_ms, "bins": bins}


def _downsample(points, limit):
    if len(points) <= limit:
        return list(points)
    step = len(points) / limit
    return [points[int(i * step)] for i in range(limit)]


def series(judgments, t_lo, t_hi, buckets=SERIES_BUCKETS):
    """Точность и число ошибок по отрезкам песни: [{t, acc, errors, n}]."""
    span = max(1.0, float(t_hi - t_lo))
    acc = [[0.0, 0] for _ in range(buckets)]
    err = [0] * buckets
    for w, tm, bad in decisions(judgments):
        b = int(min(buckets - 1, max(0, (tm - t_lo) / span * buckets)))
        acc[b][0] += w
        acc[b][1] += 1
        err[b] += 1 if bad else 0
    out = []
    for i in range(buckets):
        n = acc[i][1]
        out.append({"t": int(t_lo + span * (i + 0.5) / buckets), "n": n,
                    "acc": round(100.0 * acc[i][0] / n, 2) if n else None, "errors": err[i]})
    return out


def running(judgments, steps=60):
    """Накопленная точность по ходу игры (для сравнения с рекордом): [(время, точность%)]."""
    dec = sorted(decisions(judgments), key=lambda d: d[1])
    if not dec:
        return []
    out, total, n = [], 0.0, 0
    stride = max(1, len(dec) // steps)
    for i, (w, tm, _) in enumerate(dec):
        total += w
        n += 1
        if i % stride == 0 or i == len(dec) - 1:
            out.append((int(tm), round(100.0 * total / n, 2)))
    return out


def summarize(judgments, *, total, score, max_combo, failed, counts, holds_ok, holds_broken,
              t_lo=0, t_hi=None):
    """Итоговая статистика прохода. Результат — обычный словарь (его можно сохранять в JSON)."""
    hits = [j for j in judgments if j.grade != "miss"]
    offsets = [j.offset for j in hits]
    mean = _mean(offsets)
    std = _std(offsets, mean)
    judged = len(judgments)
    acc = accuracy(judgments)
    misses = counts.get("miss", 0)
    if t_hi is None:
        t_hi = max((j.t for j in judgments), default=t_lo + 1)
    scatter = _downsample([(j.t, round(j.offset, 1)) for j in hits], SCATTER_MAX)
    return {
        "total": total,
        "judged": judged,
        "counts": dict(counts),
        "holds_ok": holds_ok,
        "holds_broken": holds_broken,
        "holds_total": holds_ok + holds_broken,
        "score": int(score),
        "acc": round(acc, 2),
        "grade": grade_for(acc, failed),
        "max_combo": max_combo,
        "failed": failed,
        "full_combo": (not failed and total > 0 and judged >= total and misses == 0 and holds_broken == 0),
        "mean_offset": round(mean, 2),
        "mean_abs_offset": round(_mean([abs(o) for o in offsets]), 2),
        "std_offset": round(std, 2),
        "early": sum(1 for o in offsets if o < 0),
        "late": sum(1 for o in offsets if o > 0),
        "hist": histogram(offsets),
        "scatter": scatter,
        "series": series(judgments, t_lo, t_hi),
        "running": running(judgments),
    }


def compare(cur, best):
    """Сравнение прохода с личным рекордом (словари из summarize / сохранённые рекорды). None, если рекорда нет."""
    if not best:
        return None
    return {
        "score": cur["score"] - int(best.get("score", 0)),
        "acc": round(cur["acc"] - float(best.get("acc", 0.0)), 2),
        "max_combo": cur["max_combo"] - int(best.get("max_combo", 0)),
        "misses": cur["counts"].get("miss", 0) - int(best.get("counts", {}).get("miss", 0)),
        "better": (cur["score"], cur["acc"]) > (int(best.get("score", 0)), float(best.get("acc", 0.0))),
    }
