
#-- Импорт
import math
import random
import sys

import pygame

import audio
import config as C
import display
import style as S
from i18n import t

DEVELOPER = "Mistervock"
BETA = "Devorer"

FADE_IN_END = 30
ROLE_LEN = 170
ROLE1_START = 30
ROLE2_START = ROLE1_START + ROLE_LEN + 10
TITLE_START = ROLE2_START + ROLE_LEN + 10
VERSION_START = TITLE_START + 90
PROMPT_START = VERSION_START + 150
FADE_OUT_LEN = 30

TARGET_Y = C.HEIGHT // 2 - 120


def _screen():
    return pygame.display.get_surface()


def _pump():
    pygame.display.flip()
    skip = False
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            skip = True
    return skip


def _wait(clock, frames):
    for _ in range(frames):
        display.tick(clock)
        if _pump():
            return True
    return False


def _scanline_noise(surf):
    surf.blit(S._scanlines(), (0, 0))
    for _ in range(70):
        c = random.randint(15, 55)
        surf.set_at((random.randrange(C.WIDTH), random.randrange(C.HEIGHT)), (c, c, c))


def _cassette(angle, side="A"):
    w, h = 320, 200
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.rect(s, (46, 46, 58), (0, 0, w, h), border_radius=14)
    pygame.draw.rect(s, (110, 110, 130), (0, 0, w, h), 2, border_radius=14)
    paper = (236, 230, 214) if side == "A" else (200, 220, 245)
    pygame.draw.rect(s, paper, (26, 18, w - 52, 58), border_radius=6)
    lbl = S.font(18, True).render("GEOMETRY RHYTHM", True, (30, 30, 50))
    s.blit(lbl, (w // 2 - lbl.get_width() // 2, 30))
    side_txt = S.font(14).render("SIDE " + side, True, (60, 60, 90))
    s.blit(side_txt, (w - 40 - side_txt.get_width(), 52))
    pygame.draw.rect(s, (22, 22, 30), (50, 96, w - 100, 80), border_radius=12)
    pygame.draw.rect(s, (80, 44, 30), (92, 118, w - 184, 36))
    for cx in (100, w - 100):
        cy = 136
        pygame.draw.circle(s, (210, 210, 220), (cx, cy), 24, 3)
        for k in range(3):
            a = math.radians(angle + k * 120)
            pygame.draw.line(s, (210, 210, 220), (cx, cy),
                             (cx + math.cos(a) * 20, cy + math.sin(a) * 20), 3)
    return s


def _alpha_text(fnt, text, color, cx, cy, alpha, shown=None, dx=0, dy=0):
    S.blit_text(_screen(), fnt, text, color, cx, cy, alpha, shown=shown, dx=dx, dy=dy)


def _role_line(text, start, n, cy):
    k = n - start
    if k < 0 or k >= ROLE_LEN:
        return
    shown = max(1, int(len(text) * min(1.0, k / 50)))
    alpha = 255 if k < ROLE_LEN - FADE_OUT_LEN else 255 * (ROLE_LEN - k) / FADE_OUT_LEN
    _alpha_text(S.font(22, True), text, (235, 235, 245), C.WIDTH // 2, cy, alpha, shown=shown)


def _credit_frame(n, fade_out_start):
    scr = _screen()
    scr.fill((0, 0, 0))
    cy_mid = C.HEIGHT // 2
    _role_line(f"Developer: {DEVELOPER}", ROLE1_START, n, cy_mid)
    _role_line(f"Beta-tester: {BETA}", ROLE2_START, n, cy_mid)

    k = n - TITLE_START
    if k >= 0:
        title = "GEOMETRY RHYTHM"
        big = S.font(44, True)
        if k < 40:
            glitching = random.random() < 0.4
            dx = random.randint(-5, 5) if glitching else 0
            dy = random.randint(-2, 2) if glitching else 0
            alpha = random.randint(90, 255) if glitching else 255
            _alpha_text(big, title, C.WHITE, C.WIDTH // 2, cy_mid - 30, alpha, dx=dx, dy=dy)
            if glitching:
                _alpha_text(big, title, C.CYAN, C.WIDTH // 2, cy_mid - 30, 110, dx=dx + 3, dy=dy)
        else:
            _alpha_text(big, title, C.WHITE, C.WIDTH // 2, cy_mid - 30, 255)

    kv = n - VERSION_START
    if kv >= 0:
        ramp = min(1.0, kv / 90)
        ease = ramp * ramp * (3 - 2 * ramp)
        _alpha_text(S.font(22, True), f"V{C.VERSION}", C.CYAN, C.WIDTH // 2, cy_mid + 30, 255 * ease)

    kp = n - PROMPT_START
    if kp >= 0:
        pulse = 0.6 + 0.4 * (0.5 + 0.5 * math.sin(kp * 0.12))
        _alpha_text(S.font(18), t("Нажми ПРОБЕЛ, чтобы продолжить"), C.GOLD,
                    C.WIDTH // 2, C.HEIGHT - 110, 255 * pulse)

    if n >= FADE_IN_END:
        _alpha_text(S.font(14), t("ESC — пропустить"), (120, 120, 150), C.WIDTH // 2, C.HEIGHT - 40, 170)

    _scanline_noise(scr)
    dark = 0
    if n < FADE_IN_END:
        dark = 255 * (FADE_IN_END - n) / FADE_IN_END
    if fade_out_start is not None:
        dark = max(dark, 255 * min(1.0, (n - fade_out_start) / FADE_OUT_LEN))
    if dark > 0:
        ov = pygame.Surface((C.WIDTH, C.HEIGHT))
        ov.fill((0, 0, 0))
        ov.set_alpha(int(dark))
        scr.blit(ov, (0, 0))


def play_credits(clock):
    random.seed()
    n = 0
    while True:
        display.tick(clock)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return None
                if event.key == pygame.K_SPACE and n >= PROMPT_START:
                    return _screen().copy()
        if n == TITLE_START:
            audio.play("shield", 0.5)
        _credit_frame(n, None)
        pygame.display.flip()
        n += 1


def _tv_off(clock, snap):
    scr = _screen()
    audio.play("split", 0.5)
    for f in range(46):
        scr.fill((0, 0, 0))
        if f < 22:
            p = f / 21
            h = max(2, int(C.HEIGHT * (1 - p ** 1.6 * 0.985)))
            scr.blit(pygame.transform.smoothscale(snap, (C.WIDTH, h)), (0, (C.HEIGHT - h) // 2))
        elif f < 32:
            p = (f - 22) / 9
            w = max(4, int(C.WIDTH * (1 - p)))
            pygame.draw.rect(scr, (235, 240, 255), (C.WIDTH // 2 - w // 2, C.HEIGHT // 2 - 1, w, 3))
        else:
            r = max(1, 7 - (f - 32) // 2)
            pygame.draw.circle(scr, (235, 240, 255), (C.WIDTH // 2, C.HEIGHT // 2), r)
        if _wait(clock, 1):
            return True
    return False


def _tv_on(clock, bg):
    scr = _screen()
    for f in range(26):
        scr.fill((0, 0, 0))
        p = f / 25
        h = max(2, int(C.HEIGHT * (1 - (1 - p) ** 3)))
        scr.blit(pygame.transform.smoothscale(bg, (C.WIDTH, h)), (0, (C.HEIGHT - h) // 2))
        if _wait(clock, 1):
            return True
    return False


def _cassette_flip(clock, frames):
    audio.play("tick", 0.4)
    scr = _screen()
    for f in range(frames):
        scr.fill((0, 0, 0))
        p = f / (frames - 1)
        if p < 0.5:
            surf, k = _cassette(0, "A"), 1 - p * 2
        else:
            surf, k = _cassette(0, "B"), (p - 0.5) * 2
        w = max(2, int(320 * k))
        scr.blit(pygame.transform.smoothscale(surf, (w, 200)), (C.WIDTH // 2 - w // 2, TARGET_Y))
        if _wait(clock, 1):
            return True
    return False


def _load_screen(clock, insert, frames):
    scr = _screen()
    if insert:
        audio.play("shield", 0.5)
        for f in range(50):
            scr.fill((0, 0, 0))
            p = f / 49
            ease = p * p * (3 - 2 * p)
            y = int(-230 + (TARGET_Y + 230) * ease)
            scr.blit(_cassette(f * 10), (C.WIDTH // 2 - 160, y))
            if _wait(clock, 1):
                return True
    steps = (t("Перемотка"), t("Чтение дорожек"), t("Синхронизация"), t("Готово"))
    bar_w = 360
    for lf in range(frames):
        scr.fill((0, 0, 0))
        scr.blit(_cassette(lf * 8, "B" if not insert else "A"), (C.WIDTH // 2 - 160, TARGET_Y))
        p = lf / (frames - 1)
        pulse = 0 if lf % 40 < 30 else 1
        title = t("ЗАГРУЗКА") + "." * (1 + (lf // 12) % 3) + " " * pulse
        _alpha_text(S.font(22, True), title, (235, 235, 245), C.WIDTH // 2, TARGET_Y + 230, 255)
        _alpha_text(S.font(14), steps[min(3, int(p * 4))], (120, 220, 255),
                    C.WIDTH // 2, TARGET_Y + 262, 255)
        bx, by = C.WIDTH // 2 - bar_w // 2, C.HEIGHT - 100
        pygame.draw.rect(scr, (30, 30, 50), (bx, by, bar_w, 14), border_radius=6)
        pygame.draw.rect(scr, (120, 220, 255), (bx, by, int(bar_w * p), 14), border_radius=6)
        pygame.draw.rect(scr, (120, 220, 255), (bx, by, bar_w, 14), 1, border_radius=6)
        pct = S.font(14).render(f"{int(p * 100)}%", True, (160, 160, 180))
        scr.blit(pct, (C.WIDTH // 2 - pct.get_width() // 2, by + 18))
        play = S.font(14).render("▶ PLAY", True, (235, 235, 245))
        scr.blit(play, (30, 26))
        tc = S.font(14).render("00:00:%02d" % (lf // 30), True, (235, 235, 245))
        scr.blit(tc, (C.WIDTH - tc.get_width() - 30, 26))
        if random.random() < 0.3:
            shot = scr.copy()
            for _ in range(random.randint(1, 3)):
                y0 = random.randrange(0, C.HEIGHT - 12)
                scr.blit(shot, (random.randint(-16, 16), y0),
                         pygame.Rect(0, y0, C.WIDTH, random.randint(2, 10)))
        if _wait(clock, 1):
            return True
    audio.play("upgrade", 0.5)
    return False


def to_menu(clock, snap, menu_bg):
    if _tv_off(clock, snap):
        return
    if _load_screen(clock, insert=True, frames=200):
        return
    _tv_on(clock, menu_bg)


def to_game(clock, first_time, menu_bg):
    if _cassette_flip(clock, 40 if first_time else 20):
        return
    if _load_screen(clock, insert=False, frames=120 if first_time else 30):
        return
    _tv_on(clock, menu_bg)
