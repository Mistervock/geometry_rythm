#-- Окна подтверждения, ввода и выбора в стиле VHS
import sys

import pygame

import config as C
import display
import keymap
import screen_setting as SS
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
    display.flip()


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
    lines = _wrap(S.font(16), message, SS.U(BOX_W - 60))
    box = pygame.Rect(0, 0, SS.U(BOX_W), SS.U(130 + len(lines) * 22 + 60))
    box.center = (C.WIDTH // 2, C.HEIGHT // 2)
    yes_btn = S.Btn((box.centerx - SS.U(150), box.bottom - SS.U(62), SS.U(130), SS.U(42)), yes or t("ДА"),
                    C.RED_LIGHT, S.font(16, True))
    no_btn = S.Btn((box.centerx + SS.U(20), box.bottom - SS.U(62), SS.U(130), SS.U(42)), no or t("НЕТ"),
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
        S.glitch_title(scr, S.font(26, True), title, C.RED_LIGHT, box.centerx, box.y + SS.U(34), frame)
        for i, line in enumerate(lines):
            S.blit_text(scr, S.font(16), line, (200, 200, 220), box.centerx,
                        box.y + SS.U(84) + i * SS.U(22))
        yes_btn.draw(scr, mouse)
        no_btn.draw(scr, mouse)
        _end_frame(scr, frame)


def ask_text(clock, title, initial="", maxlen=24):
    """Окно ввода строки. Возвращает текст или None при отмене."""
    snap = _snapshot()
    box = pygame.Rect(0, 0, SS.U(BOX_W), SS.U(230))
    box.center = (C.WIDTH // 2, C.HEIGHT // 2)
    field = pygame.Rect(box.x + SS.U(40), box.y + SS.U(92), box.w - SS.U(80), SS.U(44))
    buf = str(initial)[:maxlen]
    fresh = True
    ok_btn = S.Btn((box.centerx - SS.U(150), box.bottom - SS.U(62), SS.U(130), SS.U(42)), t("ОК"), C.GREEN,
                   S.font(16, True))
    cancel_btn = S.Btn((box.centerx + SS.U(20), box.bottom - SS.U(62), SS.U(130), SS.U(42)), t("ОТМЕНА"), C.CYAN,
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
        S.glitch_title(scr, S.font(22, True), title, C.CYAN, box.centerx, box.y + SS.U(36), frame)
        pygame.draw.rect(scr, (14, 14, 34), field, border_radius=SS.U(6))
        pygame.draw.rect(scr, C.CYAN, field, SS.U(2), border_radius=SS.U(6))
        caret = "|" if (frame // 30) % 2 == 0 else " "
        shown = S.fit(S.font(20, True), buf + caret, field.w - SS.U(20)).render(buf + caret, True, C.WHITE)
        scr.blit(shown, (field.x + SS.U(10), field.centery - shown.get_height() // 2))
        ok_btn.draw(scr, mouse)
        cancel_btn.draw(scr, mouse)
        _end_frame(scr, frame)


def choose(clock, title, options):
    """Окно выбора из списка. Возвращает индекс варианта или None."""
    snap = _snapshot()
    row_h = SS.U(46)
    box = pygame.Rect(0, 0, SS.U(BOX_W), SS.U(110) + len(options) * row_h + SS.U(24))
    box.center = (C.WIDTH // 2, C.HEIGHT // 2)
    buttons = []
    for i, label in enumerate(options):
        rect = pygame.Rect(box.x + SS.U(60), box.y + SS.U(84) + i * row_h, box.w - SS.U(120), SS.U(40))
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
                if keymap.hit("back", ev.key):
                    return None
                if keymap.hit("up", ev.key):
                    sel = max(0, sel - 1)
                elif keymap.hit("down", ev.key):
                    sel = min(len(options) - 1, sel + 1)
                elif keymap.hit("confirm", ev.key) and ev.key != pygame.K_SPACE:
                    return sel
            elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                for i, btn in enumerate(buttons):
                    if btn.hovered(ev.pos):
                        return i
        scr = _begin_frame(snap, frame, box, C.CYAN)
        S.glitch_title(scr, S.font(22, True), title, C.CYAN, box.centerx, box.y + SS.U(34), frame)
        for i, btn in enumerate(buttons):
            btn.draw(scr, mouse, active=i == sel)
        _end_frame(scr, frame)


def info_lines(clock, title, lines, accent=None, buttons=None, footer=""):
    """Окно со списком строк (с прокруткой) и кнопками. Возвращает индекс нажатой кнопки или None (ESC).

    Используется для отчётов проверки чарта, окна восстановления и подобных сообщений."""
    accent = accent or C.CYAN
    buttons = buttons or [t("ОК")]
    snap = _snapshot()
    box = pygame.Rect(0, 0, SS.U(820), SS.U(520))
    box.center = (C.WIDTH // 2, C.HEIGHT // 2)
    text_area = pygame.Rect(box.x + SS.U(30), box.y + SS.U(70), box.w - SS.U(60), box.h - SS.U(160))
    fnt = S.font(15)
    wrapped = []
    for line in lines:
        wrapped += _wrap(fnt, line, text_area.w) or [""]
    row_h = fnt.get_linesize() + SS.U(2)
    visible = max(1, text_area.h // row_h)
    top = 0
    bw = min(SS.U(210), (box.w - SS.U(60)) // max(1, len(buttons)) - SS.U(10))
    total = len(buttons) * bw + (len(buttons) - 1) * SS.U(10)
    x0 = box.centerx - total // 2
    btns = [S.Btn((x0 + i * (bw + SS.U(10)), box.bottom - SS.U(62), bw, SS.U(42)), label,
                  accent if i == 0 else C.PURPLE_LIGHT, S.font(14, True)) for i, label in enumerate(buttons)]
    sel, frame = 0, 0
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
                    return sel
                if ev.key in (pygame.K_LEFT, pygame.K_a):
                    sel = max(0, sel - 1)
                elif ev.key in (pygame.K_RIGHT, pygame.K_d, pygame.K_TAB):
                    sel = min(len(btns) - 1, sel + 1)
                elif ev.key == pygame.K_UP:
                    top = max(0, top - 1)
                elif ev.key == pygame.K_DOWN:
                    top = min(max(0, len(wrapped) - visible), top + 1)
            elif ev.type == pygame.MOUSEWHEEL:
                top = max(0, min(max(0, len(wrapped) - visible), top - ev.y * 2))
            elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                for i, b in enumerate(btns):
                    if b.hovered(ev.pos):
                        return i
        scr = _begin_frame(snap, frame, box, accent)
        S.glitch_title(scr, S.font(22, True), title, accent, box.centerx, box.y + SS.U(36), frame)
        for i, line in enumerate(wrapped[top:top + visible]):
            scr.blit(fnt.render(line, True, (200, 200, 220)), (text_area.x, text_area.y + i * row_h))
        if len(wrapped) > visible:
            S.blit_text(scr, S.font(12), f"{top + 1}–{min(len(wrapped), top + visible)} / {len(wrapped)}  ↑↓",
                        C.GREY, box.right - SS.U(80), box.bottom - SS.U(86))
        if footer:
            S.blit_text(scr, S.font(12), footer, C.GREY, box.centerx, box.bottom - SS.U(88))
        for i, b in enumerate(btns):
            b.draw(scr, mouse, active=(i == sel))
        _end_frame(scr, frame)
