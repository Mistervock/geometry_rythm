
#-- Импорт
import sys

import pygame

import achievements
import achievements_view as V
import config as C
import display
import style as S
import screen_setting as SS
from i18n import t

VISIBLE = 5
ROW = 76


def run(clock):
    items = achievements.list_all()
    sel, top, n = 0, 0, 0
    back = S.Btn((C.WIDTH // 2 - SS.U(80), SS.U(628), SS.U(160), SS.U(44)), t("НАЗАД"), C.PURPLE_LIGHT, S.font(16, True))
    while True:
        display.tick(clock)
        mouse = pygame.mouse.get_pos()
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if ev.type == pygame.KEYDOWN:
                if ev.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE, pygame.K_RETURN, pygame.K_SPACE):
                    return
                if ev.key in (pygame.K_UP, pygame.K_w):
                    sel = max(0, sel - 1)
                elif ev.key in (pygame.K_DOWN, pygame.K_s):
                    sel = min(max(0, len(items) - 1), sel + 1)
            elif ev.type == pygame.MOUSEWHEEL:
                top = max(0, min(max(0, len(items) - VISIBLE), top - ev.y))
            elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                if back.hovered(ev.pos):
                    return
                for i in range(VISIBLE):
                    idx = top + i
                    rect = pygame.Rect(SS.U(140), SS.U(110 + i * ROW), C.WIDTH - SS.U(280), SS.U(ROW - 8))
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
        S.glitch_title(scr, S.font(36, True), t("ДОСТИЖЕНИЯ"), C.GOLD, C.WIDTH // 2, SS.U(60), n)
        S.panel(scr, pygame.Rect(SS.U(120), SS.U(100), C.WIDTH - SS.U(240), SS.U(VISIBLE * ROW + 20)), C.GOLD, alpha=215)
        if not items:
            S.blit_text(scr, S.font(18), t("Достижений пока нет. Создайте их в редакторе чартов: ESC → ДОСТИЖЕНИЯ"),
                        C.GREY, C.WIDTH // 2, SS.U(200))
        for i in range(VISIBLE):
            idx = top + i
            if idx >= len(items):
                break
            V.draw_row(scr, pygame.Rect(SS.U(140), SS.U(110 + i * ROW), C.WIDTH - SS.U(280), SS.U(ROW - 8)),
                       items[idx][1], idx == sel)
        detail = items[sel][1] if items else None
        V.draw_detail(scr, pygame.Rect(SS.U(120), SS.U(500), C.WIDTH - SS.U(240), SS.U(110)), detail)
        back.draw(scr, mouse)
        S.post_fx(scr, n, grain=40)
        pygame.display.flip()
        n += 1
