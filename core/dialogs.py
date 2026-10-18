#-- Окна подтверждения, ввода и выбора в стиле VHS
import sys

import pygame

import config as C
import display
import style as S
from i18n import t

BOX_W = 620


def _snapshot():
    return pygame.display.get_surface().copy()


def _begin_frame(snap, frame, box, accent):
    scr = pygame.display.get_surface()
    scr.blit(snap, (0, 0))
    shade = pygame.Surface((C.WIDTH, C.HEIGHT), pygame.SRCALPHA)
    shade.fill((0, 0, 0, 175))
    scr.blit(shade, (0, 0))
    if frame % 120 < 3:
        S.glitch(scr, 0.4)
    back = pygame.Surface((box.w, box.h), pygame.SRCALPHA)
    back.fill((10, 10, 25, 240))
    scr.blit(back, box.topleft)
    S.panel(scr, box, accent, alpha=240)
    return scr


def _end_frame(scr, frame):
    S.post_fx(scr, frame, grain=30)
    pygame.display.flip()


def _wrap(fnt, text, width):
    lines, line = [], ""
    for word in text.split(" "):
        cand = word if not line else line + " " + word
        if fnt.size(cand)[0] <= width:
            line = cand
        else:
            if line:
                lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines


def confirm(clock, message, title=None, yes=None, no=None):
    """Окно «Вы точно желаете?». Возвращает True, если игрок подтвердил."""
    title = title or t("Вы точно желаете?")
    snap = _snapshot()
    lines = _wrap(S.font(16), message, BOX_W - 60)
    box = pygame.Rect(0, 0, BOX_W, 130 + len(lines) * 22 + 60)
    box.center = (C.WIDTH // 2, C.HEIGHT // 2)
    yes_btn = S.Btn((box.centerx - 150, box.bottom - 62, 130, 42), yes or t("ДА"),
                    C.RED_LIGHT, S.font(16, True))
    no_btn = S.Btn((box.centerx + 20, box.bottom - 62, 130, 42), no or t("НЕТ"),
                   C.CYAN, S.font(16, True))
    frame = 0
    while True:
        display.tick(clock)
        frame += 1
        mouse = pygame.mouse.get_pos()
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if ev.type == pygame.KEYDOWN:
                if ev.key in (pygame.K_y, pygame.K_RETURN, pygame.K_KP_ENTER):
                    return True
                if ev.key in (pygame.K_n, pygame.K_ESCAPE):
                    return False
            elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                if yes_btn.hovered(ev.pos):
                    return True
                if no_btn.hovered(ev.pos):
                    return False
        scr = _begin_frame(snap, frame, box, C.RED_LIGHT)
        S.glitch_title(scr, S.font(26, True), title, C.RED_LIGHT, box.centerx, box.y + 34, frame)
        for i, line in enumerate(lines):
            S.blit_text(scr, S.font(16), line, (200, 200, 220), box.centerx,
                        box.y + 84 + i * 22)
        yes_btn.draw(scr, mouse)
        no_btn.draw(scr, mouse)
        _end_frame(scr, frame)


def ask_text(clock, title, initial="", maxlen=24):
    """Окно ввода строки. Возвращает текст или None при отмене."""
    snap = _snapshot()
    box = pygame.Rect(0, 0, BOX_W, 230)
    box.center = (C.WIDTH // 2, C.HEIGHT // 2)
    field = pygame.Rect(box.x + 40, box.y + 92, box.w - 80, 44)
    buf = str(initial)[:maxlen]
    fresh = True
    ok_btn = S.Btn((box.centerx - 150, box.bottom - 62, 130, 42), t("ОК"), C.GREEN,
                   S.font(16, True))
    cancel_btn = S.Btn((box.centerx + 20, box.bottom - 62, 130, 42), t("ОТМЕНА"), C.CYAN,
                       S.font(16, True))
    frame = 0
    while True:
        display.tick(clock)
        frame += 1
        mouse = pygame.mouse.get_pos()
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE:
                    return None
                if ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    value = buf.strip()
                    return value or None
                if ev.key == pygame.K_BACKSPACE:
                    buf = "" if fresh else buf[:-1]
                    fresh = False
                elif ev.unicode and ev.unicode.isprintable():
                    base = "" if fresh else buf
                    if len(base) < maxlen:
                        buf = base + ev.unicode
                    fresh = False
            elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                if ok_btn.hovered(ev.pos):
                    value = buf.strip()
                    return value or None
                if cancel_btn.hovered(ev.pos):
                    return None
        scr = _begin_frame(snap, frame, box, C.CYAN)
        S.glitch_title(scr, S.font(22, True), title, C.CYAN, box.centerx, box.y + 36, frame)
        pygame.draw.rect(scr, (14, 14, 34), field, border_radius=6)
        pygame.draw.rect(scr, C.CYAN, field, 2, border_radius=6)
        caret = "|" if (frame // 30) % 2 == 0 else " "
        shown = S.fit(S.font(20, True), buf + caret, field.w - 20).render(buf + caret, True, C.WHITE)
        scr.blit(shown, (field.x + 10, field.centery - shown.get_height() // 2))
        ok_btn.draw(scr, mouse)
        cancel_btn.draw(scr, mouse)
        _end_frame(scr, frame)


def choose(clock, title, options):
    """Окно выбора из списка. Возвращает индекс варианта или None."""
    snap = _snapshot()
    row_h = 46
    box = pygame.Rect(0, 0, BOX_W, 110 + len(options) * row_h + 24)
    box.center = (C.WIDTH // 2, C.HEIGHT // 2)
    buttons = []
    for i, label in enumerate(options):
        rect = pygame.Rect(box.x + 60, box.y + 84 + i * row_h, box.w - 120, 40)
        buttons.append(S.Btn(rect, label, C.CYAN, S.font(16, True)))
    sel = 0
    frame = 0
    while True:
        display.tick(clock)
        frame += 1
        mouse = pygame.mouse.get_pos()
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE:
                    return None
                if ev.key in (pygame.K_UP, pygame.K_w):
                    sel = max(0, sel - 1)
                elif ev.key in (pygame.K_DOWN, pygame.K_s):
                    sel = min(len(options) - 1, sel + 1)
                elif ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    return sel
            elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                for i, btn in enumerate(buttons):
                    if btn.hovered(ev.pos):
                        return i
        scr = _begin_frame(snap, frame, box, C.CYAN)
        S.glitch_title(scr, S.font(22, True), title, C.CYAN, box.centerx, box.y + 34, frame)
        for i, btn in enumerate(buttons):
            btn.draw(scr, mouse, active=i == sel)
        _end_frame(scr, frame)
