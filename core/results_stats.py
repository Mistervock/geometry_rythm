"""Вкладка «ПОДРОБНО» экрана результатов: числа и графики по статистике прохода (scoring.summarize).

Только отрисовка: данные приходят готовыми, ничего не пересчитывается и не читается с диска.
"""
import pygame

import config as C
import scoring
import screen_setting as SS
import style as S
from i18n import t

AXIS = (70, 70, 110)
TEXT = (150, 150, 185)
EARLY_COL = C.CYAN
LATE_COL = (255, 150, 90)


def _box(scr, rect, title):
    S.panel(scr, rect, C.DIM, alpha=190)
    scr.blit(S.font(12, True).render(title, True, (120, 160, 190)), (rect.x + SS.U(10), rect.y + SS.U(6)))
    return pygame.Rect(rect.x + SS.U(12), rect.y + SS.U(28), rect.w - SS.U(24), rect.h - SS.U(40))


def _grade_col(a):
    a = abs(a)
    return C.GOLD if a <= C.WIN_PERFECT else C.CYAN if a <= C.WIN_GREAT else C.GREEN


def scatter(scr, rect, points, t_lo, t_hi):
    inner = _box(scr, rect, t("ОТКЛОНЕНИЕ ПО ВРЕМЕНИ (мс)"))
    mid = inner.centery
    pygame.draw.line(scr, AXIS, (inner.x, mid), (inner.right, mid), 1)
    for off, lab in ((-C.WIN_PERFECT, ""), (C.WIN_PERFECT, "")):
        y = mid + int(off / C.WIN_GOOD * inner.h / 2)
        pygame.draw.line(scr, (40, 40, 70), (inner.x, y), (inner.right, y), 1)
    scr.blit(S.font(11).render(f"+{C.WIN_GOOD}", True, TEXT), (inner.x, inner.y - SS.U(2)))
    scr.blit(S.font(11).render(f"-{C.WIN_GOOD}", True, TEXT), (inner.x, inner.bottom - SS.U(12)))
    span = max(1.0, t_hi - t_lo)
    for tm, off in points:
        x = inner.x + int((tm - t_lo) / span * inner.w)
        y = mid + int(max(-C.WIN_GOOD, min(C.WIN_GOOD, off)) / C.WIN_GOOD * (inner.h / 2 - 2))
        pygame.draw.rect(scr, _grade_col(off), (x, y, SS.U(3), SS.U(3)))
    if not points:
        scr.blit(S.font(13).render(t("нет попаданий"), True, TEXT), (inner.centerx - SS.U(40), mid - SS.U(8)))


def histogram(scr, rect, hist):
    inner = _box(scr, rect, t("РАСПРЕДЕЛЕНИЕ ОТКЛОНЕНИЙ"))
    bins = hist["bins"]
    top = max(bins) or 1
    n = len(bins)
    w = inner.w / n
    for i, v in enumerate(bins):
        off = hist["start"] + (i + 0.5) * hist["bin_ms"]
        h = int((inner.h - SS.U(14)) * v / top)
        pygame.draw.rect(scr, _grade_col(off), (inner.x + int(i * w) + 1, inner.bottom - SS.U(14) - h,
                                                max(1, int(w) - 1), h))
    mid = inner.centerx
    pygame.draw.line(scr, (200, 200, 220), (mid, inner.y), (mid, inner.bottom - SS.U(14)), 1)
    scr.blit(S.font(11).render(t("рано"), True, EARLY_COL), (inner.x, inner.bottom - SS.U(12)))
    late = S.font(11).render(t("поздно"), True, LATE_COL)
    scr.blit(late, (inner.right - late.get_width(), inner.bottom - SS.U(12)))


def dynamics(scr, rect, series):
    inner = _box(scr, rect, t("ТОЧНОСТЬ И ОШИБКИ ПО ПЕСНЕ"))
    n = len(series)
    if not n:
        return
    w = inner.w / n
    emax = max([b["errors"] for b in series] + [1])
    base = inner.bottom - SS.U(4)
    for i, b in enumerate(series):
        if b["errors"]:
            h = int((inner.h * 0.45) * b["errors"] / emax)
            pygame.draw.rect(scr, (140, 50, 60), (inner.x + int(i * w) + 1, base - h, max(1, int(w) - 2), h))
    pts = []
    for i, b in enumerate(series):
        if b["acc"] is None:
            continue
        pts.append((inner.x + int((i + 0.5) * w), inner.y + int((1 - b["acc"] / 100.0) * (inner.h - SS.U(6)))))
    if len(pts) > 1:
        pygame.draw.lines(scr, C.GOLD, False, pts, SS.U(2))
    for p in pts:
        pygame.draw.circle(scr, C.GOLD, p, SS.U(2))
    scr.blit(S.font(11).render("100%", True, TEXT), (inner.x, inner.y - SS.U(2)))
    legend = S.font(11).render(t("золото — точность, красное — ошибки"), True, TEXT)
    scr.blit(legend, (inner.right - legend.get_width(), inner.y - SS.U(2)))


def compare_lines(scr, rect, cur, pb):
    """Очки по ходу песни: текущий проход и личный рекорд (Ghost)."""
    inner = _box(scr, rect, t("ТЕКУЩИЙ ПРОХОД И РЕКОРД"))
    if not cur:
        return
    hi = max([p[1] for p in cur] + [p[1] for p in (pb or [])] + [1])
    t_hi = max([p[0] for p in cur] + [p[0] for p in (pb or [])] + [1])
    t_lo = min([p[0] for p in cur] + [p[0] for p in (pb or [])] + [0])
    span = max(1.0, t_hi - t_lo)

    def line(points, col):
        pts = [(inner.x + int((tm - t_lo) / span * inner.w), inner.bottom - int(sc / hi * (inner.h - SS.U(14))) - SS.U(4))
               for tm, sc, *_ in points]
        if len(pts) > 1:
            pygame.draw.lines(scr, col, False, pts, SS.U(2))
    if pb:
        line(pb, (150, 150, 190))
    line(cur, C.CYAN)
    scr.blit(S.font(11).render(t("сейчас"), True, C.CYAN), (inner.x, inner.y - SS.U(2)))
    if pb:
        scr.blit(S.font(11).render(t("рекорд"), True, (150, 150, 190)), (inner.x + SS.U(60), inner.y - SS.U(2)))
    else:
        s = S.font(12).render(t("рекорда ещё нет"), True, TEXT)
        scr.blit(s, (inner.right - s.get_width(), inner.y - SS.U(2)))


def early_late(scr, rect, early, late):
    inner = _box(scr, rect, t("РАНО / ПОЗДНО"))
    total = early + late
    if total == 0:
        return
    w = inner.w
    ew = int(w * early / total)
    bar = pygame.Rect(inner.x, inner.y + SS.U(2), w, SS.U(16))
    pygame.draw.rect(scr, LATE_COL, bar)
    pygame.draw.rect(scr, EARLY_COL, (bar.x, bar.y, ew, bar.h))
    scr.blit(S.font(12, True).render(f"{t('рано')} {early}", True, (10, 10, 30)), (bar.x + SS.U(6), bar.y + SS.U(1)))
    s = S.font(12, True).render(f"{late} {t('поздно')}", True, (10, 10, 30))
    scr.blit(s, (bar.right - s.get_width() - SS.U(6), bar.y + SS.U(1)))


def stats_lines(res):
    st = res["stats"]
    c = st["counts"]
    rows = [
        (t("Нот всего"), f"{st['total']}"),
        ("PERFECT / GREAT", f"{c['perfect']} / {c['great']}"),
        ("GOOD / MISS", f"{c['good']} / {c['miss']}"),
        (t("Удержания ок / сорвано"), f"{st['holds_ok']} / {st['holds_broken']}"),
        (t("Фулл-комбо"), t("ДА") if st["full_combo"] else t("нет")),
        (t("Макс. комбо"), f"{st['max_combo']}"),
        (t("Очки"), f"{st['score']:06d}"),
        (t("Точность"), f"{st['acc']:.2f}%"),
        (t("Ранг"), st["grade"]),
        (t("Среднее отклонение"), f"{st['mean_offset']:+.1f} {t('мс')}"),
        (t("Среднее |откл.|"), f"{st['mean_abs_offset']:.1f} {t('мс')}"),
        (t("Разброс (σ)"), f"{st['std_offset']:.1f} {t('мс')}"),
        (t("Рано / поздно"), f"{st['early']} / {st['late']}"),
    ]
    return rows


def draw(scr, res, frame):
    st = res["stats"]
    S.blit_text(scr, S.font(26, True), t("СТАТИСТИКА"), C.CYAN, C.WIDTH // 2, SS.U(38))
    sub = f"{res.get('song', '')} — {res.get('chart', '')}"
    if res.get("practice"):
        a, b = res["section"]
        sub += f"   [{t('ПРАКТИКА')} {int(res.get('speed', 1) * 100)}%  {a // 1000}–{b // 1000} {t('с')}]"
    S.blit_text(scr, S.fit(S.font(13), sub, SS.U(900)), sub, C.GREY, C.WIDTH // 2, SS.U(64))

    panel = pygame.Rect(SS.UR(40, 90, 380, 470))
    S.panel(scr, panel, C.CYAN, alpha=190)
    y = panel.y + SS.U(14)
    for label, value in stats_lines(res):
        scr.blit(S.font(14).render(label, True, (160, 160, 190)), (panel.x + SS.U(14), y))
        v = S.font(15, True).render(value, True, C.WHITE)
        scr.blit(v, (panel.right - v.get_width() - SS.U(14), y - SS.U(1)))
        y += SS.U(28)
    cmp = res.get("pb_compare")
    y += SS.U(6)
    if cmp:
        head = t("ЛУЧШЕ РЕКОРДА") if cmp["better"] else t("РЕКОРД НЕ ПОБИТ")
        scr.blit(S.font(13, True).render(head, True, C.GREEN if cmp["better"] else C.GREY), (panel.x + SS.U(14), y))
        line = f"{t('очки')} {cmp['score']:+d}   {t('точность')} {cmp['acc']:+.2f}%   {t('промахи')} {cmp['misses']:+d}"
        scr.blit(S.font(12).render(line, True, TEXT), (panel.x + SS.U(14), y + SS.U(20)))
    elif not res.get("practice"):
        scr.blit(S.font(13).render(t("Личного рекорда для сравнения ещё нет"), True, TEXT), (panel.x + SS.U(14), y))

    t_lo, t_hi = (res["section"] if res.get("practice") else (0, max([p[0] for p in st["scatter"]] + [1])))
    scatter(scr, pygame.Rect(SS.UR(440, 90, 400, 215)), st["scatter"], t_lo, t_hi)
    histogram(scr, pygame.Rect(SS.UR(860, 90, 380, 215)), st["hist"])
    dynamics(scr, pygame.Rect(SS.UR(440, 320, 400, 190)), st["series"])
    compare_lines(scr, pygame.Rect(SS.UR(860, 320, 380, 190)), res.get("timeline"), res.get("pb_timeline"))
    early_late(scr, pygame.Rect(SS.UR(440, 525, 800, 54)), st["early"], st["late"])
