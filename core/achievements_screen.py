
#-- Импорт
import os
import sys

import pygame

import achievements
import achievements_view as V
import config as C
import display
import keymap
import progress
import settings
import style as S
import screen_setting as SS
from i18n import t

VISIBLE = 5
ROW = 76


def _builtin_items():
    """Встроенные достижения в том же формате карточек: (ключ, данные, получено, glyph)."""
    lang = settings.get("lang")
    state = progress.load()
    out = []
    for defn in progress.definitions():
        name, desc = progress.display(defn, lang)
        have, need = progress.counter_value(state, defn), defn[3]
        done = progress.is_unlocked(defn[0])
        text = f"{desc}  [{need if done else have}/{need}]"
        out.append((defn[0], {"name": name, "description": text, "image": ""}, done, progress.GLYPH[defn[1]]))
    return out


def run(clock):
    custom = achievements.list_all()
    builtin = _builtin_items()
    tab = 0
    items = custom
    sel, top, n = 0, 0, 0
    tab_btns = [S.Btn((C.WIDTH // 2 - SS.U(210) + i * SS.U(210), SS.U(88), SS.U(200), SS.U(30)), label, C.GOLD, S.font(14, True))
                for i, label in enumerate((t("ЗА ЧАРТЫ"), t("ВСТРОЕННЫЕ")))]
    back = S.Btn((C.WIDTH // 2 - SS.U(80), SS.U(636), SS.U(160), SS.U(40)), t("НАЗАД"), C.PURPLE_LIGHT, S.font(16, True))
    while True:
        display.tick(clock)
        mouse = pygame.mouse.get_pos()
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if ev.type == pygame.KEYDOWN:
                if keymap.hit("back", ev.key) or keymap.hit("confirm", ev.key) or ev.key == pygame.K_BACKSPACE:
                    return
                if ev.key == pygame.K_TAB:
                    tab = 1 - tab
                    items = builtin if tab else custom
                    sel = top = 0
                if keymap.hit("up", ev.key):
                    sel = max(0, sel - 1)
                elif keymap.hit("down", ev.key):
                    sel = min(max(0, len(items) - 1), sel + 1)
            elif ev.type == pygame.MOUSEWHEEL:
                top = max(0, min(max(0, len(items) - VISIBLE), top - ev.y))
            elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                if back.hovered(ev.pos):
                    return
                for i, b in enumerate(tab_btns):
                    if b.hovered(ev.pos) and i != tab:
                        tab = i
                        items = builtin if tab else custom
                        sel = top = 0
                for i in range(VISIBLE):
                    idx = top + i
                    rect = pygame.Rect(SS.U(140), SS.U(134 + i * ROW), C.WIDTH - SS.U(280), SS.U(ROW - 8))
                    if idx < len(items) and rect.collidepoint(ev.pos):
                        sel = idx
        sel = max(0, min(sel, len(items) - 1)) if items else 0
        if sel < top:
            top = sel
        if sel >= top + VISIBLE:
            top = sel - VISIBLE + 1

        scr = pygame.display.get_surface()
        scr.fill((0, 0, 0))
        S.draw_grid(scr, n * 0.3, 0.0)
        S.glitch_title(scr, S.font(36, True), t("ДОСТИЖЕНИЯ"), C.GOLD, C.WIDTH // 2, SS.U(52), n)
        S.panel(scr, pygame.Rect(SS.U(120), SS.U(124), C.WIDTH - SS.U(240), SS.U(VISIBLE * ROW + 20)), C.GOLD, alpha=215)
        for i, b in enumerate(tab_btns):
            b.draw(scr, mouse, active=(i == tab))
        if not items:
            S.blit_text(scr, S.font(18), t("Достижений пока нет. Создайте их в редакторе чартов: ESC → ДОСТИЖЕНИЯ"),
                        C.GREY, C.WIDTH // 2, SS.U(200))
        for i in range(VISIBLE):
            idx = top + i
            if idx >= len(items):
                break
            rect = pygame.Rect(SS.U(140), SS.U(134 + i * ROW), C.WIDTH - SS.U(280), SS.U(ROW - 8))
            if tab:
                V.draw_row(scr, rect, items[idx][1], idx == sel, items[idx][2], glyph=items[idx][3])
            else:
                V.draw_row(scr, rect, items[idx][1], idx == sel,
                           achievements.is_unlocked(os.path.basename(items[idx][0])))
        detail = items[sel][1] if items else None
        V.draw_detail(scr, pygame.Rect(SS.U(120), SS.U(526), C.WIDTH - SS.U(240), SS.U(96)), detail)
        back.draw(scr, mouse)
        S.post_fx(scr, n, grain=40)
        display.flip()
        n += 1
