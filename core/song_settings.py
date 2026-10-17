
#-- Импорт
import sys

import pygame

import config as C
import display
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
)
TEXT_LIMITS = {"title": 60, "artist": 60, "charter": 40}
DIFF_ROW = 3
STAR_R = 16
STAR_GAP = 46


def _box(i):
    return pygame.Rect((C.WIDTH - 560) // 2, ROW_Y + i * ROW_STEP + 22, 560, 38)


def _stars():
    return S.star_centers(C.WIDTH // 2, _box(DIFF_ROW).centery, 5, STAR_GAP)


#-- Ввод

def _commit(vals, edit, buf):
    if edit is not None:
        vals[edit] = buf.strip()[:TEXT_LIMITS[edit]]


def _set_diff(vals, value):
    vals["difficulty"] = max(1, min(5, value))


#-- Цикл

def run(clock, chart):
    """Окно настроек песни. Возвращает True, если что-то изменилось."""
    meta = songs.meta(chart.song)
    orig = {"title": meta.get("title", ""), "artist": meta.get("artist", ""),
            "charter": chart.charter, "difficulty": chart.difficulty}
    vals = dict(orig)
    sel, edit, buf, frame = 0, None, "", 0
    done = S.Btn((C.WIDTH // 2 - 90, 470, 180, 40), t("ГОТОВО"), C.CYAN, S.font(16, True))

    def finish():
        _commit(vals, edit, buf)
        chart.charter = vals["charter"]
        chart.difficulty = vals["difficulty"]
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
                for i in range(DIFF_ROW):
                    if _box(i).collidepoint(ev.pos):
                        sel = i
                        edit = LABELS[i][0]
                        buf = vals[edit]
                        break
                else:
                    for k, (cx, cy) in enumerate(_stars()):
                        if (ev.pos[0] - cx) ** 2 + (ev.pos[1] - cy) ** 2 <= (STAR_R + 6) ** 2:
                            sel = DIFF_ROW
                            _set_diff(vals, k + 1)
                            break
                    else:
                        if _box(DIFF_ROW).collidepoint(ev.pos):
                            sel = DIFF_ROW
        _draw(chart, sel, edit, buf, vals, done, mouse, frame)
        pygame.display.flip()


#-- Отрисовка

def _draw(chart, sel, edit, buf, vals, done, mouse, frame):
    scr = pygame.display.get_surface()
    scr.fill((0, 0, 0))
    S.draw_grid(scr, frame * 0.3, 0.0)
    S.glitch_title(scr, S.font(36, True), t("НАСТРОЙКИ ПЕСНИ"), C.CYAN, C.WIDTH // 2, 56, frame)
    S.blit_text(scr, S.font(14), f"{t('файл')}: {chart.song}", C.GREY, C.WIDTH // 2, 92)
    S.panel(scr, pygame.Rect(130, 116, C.WIDTH - 260, 350), C.CYAN, alpha=215)

    for i, (key, label) in enumerate(LABELS):
        active = i == sel
        box = _box(i)
        scr.blit(S.font(16, True).render(t(label), True, C.WHITE if active else C.GREY),
                 (box.x, box.y - 22))
        pygame.draw.rect(scr, (34, 34, 68) if active else (14, 14, 30), box, border_radius=6)
        pygame.draw.rect(scr, C.CYAN if active else C.DIM, box, 2, border_radius=6)
        if key == "difficulty":
            for k, (cx, cy) in enumerate(_stars()):
                S.draw_star(scr, cx, cy, STAR_R, C.GOLD if k < vals["difficulty"] else C.DIM,
                            filled=k < vals["difficulty"])
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
        while fnt.size(text)[0] > box.w - 24 and len(text) > 1:
            text = text[1:]
        scr.blit(fnt.render(text, True, col), (box.x + 12, box.centery - fnt.get_height() // 2))

    done.draw(scr, mouse)
    S.blit_text(scr, S.font(13),
                t("↑↓ переход · Enter — ввод · 1–5 или ← → — сложность · ESC — готово"),
                C.GREY, C.WIDTH // 2, C.HEIGHT - 30)
    S.post_fx(scr, frame, grain=40)
