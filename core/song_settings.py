
#-- Импорт
import os
import sys

import pygame

import achievements
import config as C
import display
import screen_setting as SS
import songs
import style as S
from i18n import t

#-- Раскладка

ROW_Y = 160
ROW_STEP = 72
LABELS = (
    ("title", "Название песни"),
    ("artist", "Автор песни"),
    ("charter", "Кто делал чарт"),
    ("difficulty", "Сложность (звёзды)"),
    ("achievement", "Ачивка за победу"),
)
TEXT_LIMITS = {"title": 60, "artist": 60, "charter": 40}
DIFF_ROW = 3
ACH_ROW = 4
PANEL_H = 422
STAR_R = 16
STAR_GAP = 46


def _box(i):
    return pygame.Rect((C.WIDTH - SS.U(560)) // 2, SS.U(ROW_Y + i * ROW_STEP + 22), SS.U(560), SS.U(38))


def _stars():
    return S.star_centers(C.WIDTH // 2, _box(DIFF_ROW).centery, 5, SS.U(STAR_GAP))


#-- Ввод

def _commit(vals, edit, buf):
    if edit is not None:
        vals[edit] = buf.strip()[:TEXT_LIMITS[edit]]


def _set_diff(vals, value):
    vals["difficulty"] = max(1, min(5, value))


def _ach_choices():
    """Варианты ачивки: сначала «без ачивки», затем файлы из achievements/."""
    out = [("", None)]
    for path, data in achievements.list_all():
        out.append((os.path.basename(path), data))
    return out


def _cycle_ach(vals, choices, step):
    names = [name for name, _ in choices]
    cur = names.index(vals["achievement"]) if vals["achievement"] in names else 0
    vals["achievement"] = names[(cur + step) % len(names)]


#-- Цикл

def run(clock, chart):
    """Окно настроек песни. Возвращает True, если что-то изменилось."""
    meta = songs.meta(chart.song)
    orig = {"title": meta.get("title", ""), "artist": meta.get("artist", ""),
            "charter": chart.charter, "difficulty": chart.difficulty}
    choices = _ach_choices()
    names = [name for name, _ in choices]
    # ачивка, которой уже нет в папке, показывается как «нет»
    orig["achievement"] = chart.achievement if chart.achievement in names else ""
    vals = dict(orig)
    sel, edit, buf, frame = 0, None, "", 0
    done = S.Btn((C.WIDTH // 2 - SS.U(90), SS.U(556), SS.U(180), SS.U(40)), t("ГОТОВО"), C.CYAN, S.font(16, True))

    def finish():
        _commit(vals, edit, buf)
        chart.charter = vals["charter"]
        chart.difficulty = vals["difficulty"]
        chart.achievement = vals["achievement"]
        if vals != orig:
            songs.save_meta(chart.song, {"title": vals["title"], "artist": vals["artist"]})
        return vals != orig

    while True:
        display.tick(clock)
        frame += 1
        mouse = pygame.mouse.get_pos()
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                finish()
                pygame.quit()
                sys.exit()
            if ev.type == pygame.KEYDOWN:
                if edit is not None:
                    key = LABELS[sel][0]
                    if ev.key == pygame.K_ESCAPE:
                        edit = None
                    elif ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_TAB, pygame.K_UP, pygame.K_DOWN):
                        _commit(vals, edit, buf)
                        edit = None
                        if ev.key == pygame.K_UP:
                            sel = (sel - 1) % len(LABELS)
                        elif ev.key in (pygame.K_DOWN, pygame.K_TAB):
                            sel = (sel + 1) % len(LABELS)
                    elif ev.key == pygame.K_BACKSPACE:
                        buf = buf[:-1]
                    elif ev.unicode and ev.unicode.isprintable() and len(buf) < TEXT_LIMITS[edit]:
                        buf += ev.unicode
                    continue
                if ev.key == pygame.K_ESCAPE:
                    return finish()
                if ev.key == pygame.K_UP:
                    sel = (sel - 1) % len(LABELS)
                elif ev.key in (pygame.K_DOWN, pygame.K_TAB):
                    sel = (sel + 1) % len(LABELS)
                elif sel == ACH_ROW:
                    if ev.key in (pygame.K_LEFT, pygame.K_a):
                        _cycle_ach(vals, choices, -1)
                    elif ev.key in (pygame.K_RIGHT, pygame.K_d, pygame.K_RETURN, pygame.K_KP_ENTER):
                        _cycle_ach(vals, choices, 1)
                elif sel == DIFF_ROW:
                    if ev.key in (pygame.K_LEFT, pygame.K_a):
                        _set_diff(vals, vals["difficulty"] - 1)
                    elif ev.key in (pygame.K_RIGHT, pygame.K_d):
                        _set_diff(vals, vals["difficulty"] + 1)
                    elif ev.unicode in ("1", "2", "3", "4", "5"):
                        _set_diff(vals, int(ev.unicode))
                elif ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    edit = LABELS[sel][0]
                    buf = vals[edit]
                elif ev.unicode and ev.unicode.isprintable():
                    edit = LABELS[sel][0]
                    buf = ev.unicode
            elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                if done.hovered(ev.pos):
                    return finish()
                _commit(vals, edit, buf)
                edit = None
                if _box(ACH_ROW).collidepoint(ev.pos):
                    sel = ACH_ROW
                    _cycle_ach(vals, choices, 1)
                    continue
                for i in range(DIFF_ROW):
                    if _box(i).collidepoint(ev.pos):
                        sel = i
                        edit = LABELS[i][0]
                        buf = vals[edit]
                        break
                else:
                    for k, (cx, cy) in enumerate(_stars()):
                        if (ev.pos[0] - cx) ** 2 + (ev.pos[1] - cy) ** 2 <= (SS.U(STAR_R) + SS.U(6)) ** 2:
                            sel = DIFF_ROW
                            _set_diff(vals, k + 1)
                            break
                    else:
                        if _box(DIFF_ROW).collidepoint(ev.pos):
                            sel = DIFF_ROW
        _draw(chart, sel, edit, buf, vals, done, mouse, frame, choices)
        pygame.display.flip()


#-- Отрисовка

def _draw(chart, sel, edit, buf, vals, done, mouse, frame, choices):
    scr = pygame.display.get_surface()
    scr.fill((0, 0, 0))
    S.draw_grid(scr, frame * 0.3, 0.0)
    S.glitch_title(scr, S.font(36, True), t("НАСТРОЙКИ ПЕСНИ"), C.CYAN, C.WIDTH // 2, SS.U(56), frame)
    S.blit_text(scr, S.font(14), f"{t('файл')}: {chart.song}", C.GREY, C.WIDTH // 2, SS.U(92))
    S.panel(scr, pygame.Rect(SS.U(130), SS.U(116), C.WIDTH - SS.U(260), SS.U(PANEL_H)), C.CYAN, alpha=215)

    for i, (key, label) in enumerate(LABELS):
        active = i == sel
        box = _box(i)
        scr.blit(S.font(16, True).render(t(label), True, C.WHITE if active else C.GREY),
                 (box.x, box.y - SS.U(22)))
        pygame.draw.rect(scr, (34, 34, 68) if active else (14, 14, 30), box, border_radius=SS.U(6))
        pygame.draw.rect(scr, C.CYAN if active else C.DIM, box, SS.U(2), border_radius=SS.U(6))
        if key == "difficulty":
            for k, (cx, cy) in enumerate(_stars()):
                S.draw_star(scr, cx, cy, SS.U(STAR_R), C.GOLD if k < vals["difficulty"] else C.DIM,
                            filled=k < vals["difficulty"])
            continue
        if key == "achievement":
            title = dict(choices).get(vals[key])
            text = title["name"] if title else t("нет")
            col = C.WHITE if title else C.DIM
            fnt = S.font(18, True)
            scr.blit(fnt.render(text, True, col), (box.x + SS.U(12), box.centery - fnt.get_height() // 2))
            continue
        editing = edit == key
        if editing:
            text = buf + ("|" if (frame // 30) % 2 == 0 else " ")
            col = C.WHITE
        elif vals[key]:
            text, col = vals[key], C.WHITE
        else:
            text = songs.title(chart.song) if key == "title" else t("не указано")
            col = C.DIM
        fnt = S.font(18, True)
        while fnt.size(text)[0] > box.w - SS.U(24) and len(text) > 1:
            text = text[1:]
        scr.blit(fnt.render(text, True, col), (box.x + SS.U(12), box.centery - fnt.get_height() // 2))

    done.draw(scr, mouse)
    S.blit_text(scr, S.font(13),
                t("↑↓ переход · Enter — ввод · 1–5 или ← → — сложность · ESC — готово"),
                C.GREY, C.WIDTH // 2, C.HEIGHT - SS.U(30))
    S.post_fx(scr, frame, grain=40)
