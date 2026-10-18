
#-- Импорт
import math
import sys

import pygame

import config as C
import display
import records
import style as S
from i18n import t

ITEMS = (("songs", "ПЕСНИ"), ("records", "РЕКОРДЫ"), ("achievements", "ДОСТИЖЕНИЯ"),
         ("settings", "НАСТРОЙКИ"), ("quit", "ВЫХОД"))
BEAT_MS = 500
BETA_ANGLE = 8
_beta_img = None


def _beta_surface():
    global _beta_img
    if _beta_img is None:
        label = S.font(14, True).render("BETA", True, C.GOLD)
        w, h = label.get_width() + 12, label.get_height() + 6
        _beta_img = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.rect(_beta_img, (10, 10, 25, 230), (0, 0, w, h), border_radius=5)
        pygame.draw.rect(_beta_img, C.GOLD, (0, 0, w, h), 2, border_radius=5)
        _beta_img.blit(label, (6, 3))
    return _beta_img


def _draw_beta(scr, n):
    title_w, title_h = S.font(44, True).size("GEOMETRY RHYTHM")
    phase = (pygame.time.get_ticks() % BEAT_MS) / BEAT_MS
    pulse = (1.0 - phase) ** 3
    img = pygame.transform.rotozoom(_beta_surface(), BETA_ANGLE, 1.0 + 0.22 * pulse)
    img.set_alpha(int(255 * S.smoothstep(min(1.0, (n - 12) / 20))))
    cx = C.WIDTH // 2 + title_w // 2 - 4
    cy = 170 + title_h // 2 + 4
    scr.blit(img, img.get_rect(center=(cx, cy)))


def background_surface():
    surf = pygame.Surface((C.WIDTH, C.HEIGHT))
    surf.fill((0, 0, 0))
    S.draw_grid(surf, 0)
    S.post_fx(surf, 0, grain=0)
    return surf


def _draw_background(scr, n):
    scr.fill((0, 0, 0))
    S.draw_grid(scr, n * 0.5, 0.15 + 0.1 * math.sin(n * 0.05))


def main_menu(clock):
    buttons = []
    for i, (action, label) in enumerate(ITEMS):
        rect = pygame.Rect(C.WIDTH // 2 - 130, 296 + i * 58, 260, 44)
        buttons.append((action, S.Btn(rect, t(label), C.CYAN, S.font(18, True))))
    selected = 0
    n = 0
    while True:
        display.tick(clock)
        mouse = pygame.mouse.get_pos()
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if ev.type == pygame.KEYDOWN:
                if ev.key in (pygame.K_UP, pygame.K_w):
                    selected = (selected - 1) % len(buttons)
                elif ev.key in (pygame.K_DOWN, pygame.K_s):
                    selected = (selected + 1) % len(buttons)
                elif ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                    return buttons[selected][0]
                elif ev.key == pygame.K_ESCAPE:
                    return "quit"
            if ev.type == pygame.MOUSEMOTION:
                for i, (_, btn) in enumerate(buttons):
                    if btn.hovered(ev.pos):
                        selected = i
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                for action, btn in buttons:
                    if btn.hovered(ev.pos):
                        return action

        scr = pygame.display.get_surface()
        _draw_background(scr, n)

        for i in range(4):
            cx = C.FIELD_X + C.FIELD_W // 2 + (i - 1.5) * 70
            cy = 92 + math.sin(n * 0.04 + i * 1.3) * 6
            rot = n * 0.6 + i * 25
            S.draw_shape(scr, C.LANE_SHAPES[i], cx, cy, 16, C.LANE_COLORS[i], 255, rot=rot)

        glitch_k = n - 10
        S.glitch_title(scr, S.font(44, True), "GEOMETRY RHYTHM", C.WHITE,
                       C.WIDTH // 2, 170, glitch_k)
        if n >= 12:
            _draw_beta(scr, n)
        if n >= 40:
            S.blit_text(scr, S.font(14), f"D  F  J  K  —  {t('дорожки')}   ·   V{C.VERSION}",
                        C.GREY, C.WIDTH // 2, 214, 255 * S.smoothstep((n - 40) / 30))

        for i, (action, btn) in enumerate(buttons):
            if n >= 60 + i * 10:
                btn.draw(scr, mouse, active=(i == selected))

        if n >= 120:
            S.blit_text(scr, S.font(14), t("Developer: Mistervock · ПЕСНИ: свои .ogg/.mp3 в папке songs/"),
                        (90, 90, 120),
                        C.WIDTH // 2, C.HEIGHT - 24)

        S.post_fx(scr, n, grain=45)
        pygame.display.flip()
        n += 1


def records_screen(clock):
    back = S.Btn((C.WIDTH // 2 - 130, 520, 260, 44), t("НАЗАД"), C.PURPLE_LIGHT, S.font(18, True))
    entries = records.load()
    n = 0
    while True:
        display.tick(clock)
        mouse = pygame.mouse.get_pos()
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if ev.type == pygame.KEYDOWN and ev.key in (pygame.K_ESCAPE, pygame.K_RETURN,
                                                         pygame.K_SPACE, pygame.K_BACKSPACE):
                return
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1 and back.hovered(ev.pos):
                return

        scr = pygame.display.get_surface()
        _draw_background(scr, n)
        S.glitch_title(scr, S.font(36, True), t("РЕКОРДЫ"), C.GOLD, C.WIDTH // 2, 60, n - 5)

        area = pygame.Rect(C.WIDTH // 2 - 280, 110, 560, 390)
        S.panel(scr, area, C.GOLD, alpha=215)
        head = S.font(14, True).render(
            f"{'#':<4}{t('ИМЯ'):<14}{t('ОЧКИ'):>8}{t('ТОЧН.'):>9}{t('ОЦЕНКА'):>9}{t('ДАТА'):>13}",
            True, C.GOLD)
        scr.blit(head, (area.x + 22, area.y + 18))
        if not entries:
            S.blit_text(scr, S.font(18), t("пока пусто — сыграй первый забег"), C.GREY,
                        C.WIDTH // 2, area.centery)
        for idx, e in enumerate(entries):
            ka = n - (10 + idx * 4)
            if ka < 0:
                continue
            col = (C.GOLD if idx == 0 else (210, 210, 210) if idx == 1
                   else (200, 120, 60) if idx == 2 else C.GREY)
            line = (f"{idx + 1:<4}{e['name'][:12]:<14}{e['score']:>8}"
                    f"{e['acc']:>8.1f}%{e['grade']:>9}{e['date']:>13}")
            surf = S.font(14).render(line, True, col)
            surf.set_alpha(int(min(255, ka * 255 / 12)))
            scr.blit(surf, (area.x + 22, area.y + 50 + idx * 32))

        back.draw(scr, mouse)
        S.post_fx(scr, n, grain=45)
        pygame.display.flip()
        n += 1
