#-- Экран привязки клавиш меню и редактора (из настроек)
import sys

import pygame

import config as C
import display
import keymap
import screen_setting as SS
import style as S
from i18n import t

ROW_H = 31
TOP = 112
VISIBLE = 15
HEADS = {keymap.MENU: "НАВИГАЦИЯ ПО МЕНЮ", keymap.SONGS: "СПИСОК ПЕСЕН", keymap.EDITOR: ""}


def _rows(tab):
    """Строки вкладки: ("head", текст) и ("act", действие)."""
    out = []
    for section in dict(keymap.TABS)[tab]:
        if HEADS[section]:
            out.append(("head", HEADS[section]))
        out += [("act", a) for a in keymap.section_actions(section)]
    return out


def _first_act(rows, start=0, step=1):
    i = start
    while 0 <= i < len(rows):
        if rows[i][0] == "act":
            return i
        i += step
    return None


def _message(reason, other):
    if reason == "reserved":
        return t("Эту клавишу нельзя назначить")
    if reason == "lane":
        return t("Клавиша занята дорожкой игры")
    if reason == "bad":
        return t("Эта клавиша не подходит")
    if other:
        return f"{t('Поменялись местами с')}: {t(keymap.ACTIONS[other]['label'])}"
    return ""


def keys_screen(clock, tab="menu"):
    tabs = [name for name, _ in keymap.TABS]
    tab_i = tabs.index(tab) if tab in tabs else 0
    rows = _rows(tabs[tab_i])
    sel = _first_act(rows)
    top = 0
    waiting = None
    toast, toast_left = "", 0.0
    frame = 0
    tab_w = SS.U(260)
    tab_rects = [pygame.Rect(C.WIDTH // 2 - tab_w - SS.U(8) + i * (tab_w + SS.U(16)), SS.U(68), tab_w, SS.U(30))
                 for i in range(len(tabs))]
    reset_btn = S.Btn(SS.UR(SS.REF_W // 2 - 300, 664, 290, 40), t("СБРОСИТЬ ВКЛАДКУ"), C.RED_LIGHT, S.font(16, True))
    back_btn = S.Btn(SS.UR(SS.REF_W // 2 + 10, 664, 290, 40), t("НАЗАД"), C.PURPLE_LIGHT, S.font(16, True))

    def switch(i):
        nonlocal tab_i, rows, sel, top, waiting
        tab_i = i % len(tabs)
        rows = _rows(tabs[tab_i])
        sel = _first_act(rows)
        top = 0
        waiting = None

    def move(step):
        nonlocal sel
        j = _first_act(rows, sel + step, step)
        if j is not None:
            sel = j

    def row_at(pos):
        x, y = pos[0] / SS.SCALE, pos[1] / SS.SCALE
        if not (140 <= x <= SS.REF_W - 140) or y < TOP:
            return None
        i = int((y - TOP) // ROW_H)
        if 0 <= i < VISIBLE and top + i < len(rows):
            return top + i
        return None

    while True:
        dt = min(0.05, display.tick(clock) / 1000.0)
        frame += 1
        if toast_left > 0:
            toast_left -= dt
        mouse = pygame.mouse.get_pos()
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if waiting is not None and ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE:
                    toast, toast_left = t("Отменено"), 1.5
                else:
                    ok, reason, other = keymap.rebind(waiting, pygame.key.name(ev.key))
                    if ok:
                        msg = _message(None, other)
                        toast, toast_left = (msg or f"{t(keymap.ACTIONS[waiting]['label'])}: {keymap.label(waiting)}"), 2.5
                    else:
                        toast, toast_left = _message(reason, None), 2.5
                waiting = None
                continue
            if waiting is not None:
                continue
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE:
                    return
                if ev.key == pygame.K_UP:
                    move(-1)
                elif ev.key == pygame.K_DOWN:
                    move(1)
                elif ev.key in (pygame.K_LEFT, pygame.K_RIGHT, pygame.K_TAB):
                    switch(tab_i + (-1 if ev.key == pygame.K_LEFT else 1))
                elif ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE) and sel is not None:
                    waiting = rows[sel][1]
                    toast, toast_left = t("Нажмите новую клавишу (ESC — отмена)"), 99
                elif ev.key == pygame.K_DELETE and sel is not None:
                    keymap.reset_action(rows[sel][1])
                    toast, toast_left = t("Клавиша сброшена"), 1.5
            elif ev.type == pygame.MOUSEWHEEL:
                top = max(0, min(max(0, len(rows) - VISIBLE), top - ev.y))
            elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                for i, r in enumerate(tab_rects):
                    if r.collidepoint(ev.pos):
                        switch(i)
                        break
                else:
                    if back_btn.hovered(ev.pos):
                        return
                    if reset_btn.hovered(ev.pos):
                        keymap.reset_tab(tabs[tab_i])
                        toast, toast_left = t("Клавиши вкладки сброшены"), 2.0
                        continue
                    idx = row_at(ev.pos)
                    if idx is not None and rows[idx][0] == "act":
                        sel = idx
                        waiting = rows[idx][1]
                        toast, toast_left = t("Нажмите новую клавишу (ESC — отмена)"), 99

        if sel is not None:
            if sel < top:
                top = sel
            if sel >= top + VISIBLE:
                top = sel - VISIBLE + 1
        _draw(rows, tabs, tab_i, tab_rects, sel, top, waiting, toast if toast_left > 0 else "",
              mouse, frame, reset_btn, back_btn)
        display.flip()


def _draw(rows, tabs, tab_i, tab_rects, sel, top, waiting, toast, mouse, frame, reset_btn, back_btn):
    scr = pygame.display.get_surface()
    scr.fill((0, 0, 0))
    S.draw_grid(scr, frame * 0.3, 0.0)
    S.glitch_title(scr, S.font(30, True), t("КЛАВИШИ"), C.CYAN, C.WIDTH // 2, SS.U(36), frame)
    names = {"menu": t("МЕНЮ И ПЕСНИ"), "editor": t("РЕДАКТОР")}
    for i, r in enumerate(tab_rects):
        active = i == tab_i
        pygame.draw.rect(scr, (34, 34, 68) if active else (14, 14, 30), r, border_radius=SS.U(6))
        pygame.draw.rect(scr, C.CYAN if active else C.DIM, r, SS.U(2), border_radius=SS.U(6))
        S.blit_text(scr, S.font(15, True), names[tabs[i]], C.WHITE if active else C.GREY, r.centerx, r.centery)
    area = pygame.Rect(SS.U(120), SS.U(TOP - 8), C.WIDTH - SS.U(240), SS.U(VISIBLE * ROW_H + 16))
    S.panel(scr, area, C.CYAN, alpha=215)
    for i in range(VISIBLE):
        idx = top + i
        if idx >= len(rows):
            break
        kind, val = rows[idx]
        y = SS.U(TOP + i * ROW_H)
        row = pygame.Rect(SS.U(140), y, C.WIDTH - SS.U(280), SS.U(ROW_H - 4))
        if kind == "head":
            S.blit_text(scr, S.font(13, True), t(val), C.GOLD, C.WIDTH // 2, row.centery)
            continue
        active = idx == sel
        if active:
            pygame.draw.rect(scr, (34, 34, 68), row, border_radius=SS.U(6))
            pygame.draw.rect(scr, C.CYAN, row, SS.U(2), border_radius=SS.U(6))
        col = C.WHITE if active else (190, 190, 210)
        scr.blit(S.font(17, True).render(t(keymap.ACTIONS[val]["label"]), True, col),
                 (row.x + SS.U(16), row.y + SS.U(4)))
        if waiting == val:
            text, vcol = "...", C.RED_LIGHT
        else:
            text = keymap.labels(val)
            vcol = C.CYAN if keymap.is_custom(val) else C.GOLD
        vt = S.font(17, True).render(text, True, vcol)
        scr.blit(vt, (row.right - vt.get_width() - SS.U(16), row.y + SS.U(4)))
    if len(rows) > VISIBLE:
        track = pygame.Rect(area.right - SS.U(10), area.y + SS.U(6), SS.U(4), area.h - SS.U(12))
        pygame.draw.rect(scr, C.DIM, track, border_radius=2)
        h = max(SS.U(20), int(track.h * VISIBLE / len(rows)))
        y = track.y + int((track.h - h) * top / max(1, len(rows) - VISIBLE))
        pygame.draw.rect(scr, C.CYAN, (track.x, y, track.w, h), border_radius=2)
    S.blit_text(scr, S.font(13), t("ENTER — назначить · DEL — сбросить клавишу · ←/→ — вкладка · ESC — назад"),
                C.GREY, C.WIDTH // 2, SS.U(TOP + VISIBLE * ROW_H + 22))
    S.blit_text(scr, S.font(13), t("Стрелки, Enter и Esc в меню работают всегда. Первая клавиша — главная, остальные запасные."),
                C.GREY, C.WIDTH // 2, SS.U(TOP + VISIBLE * ROW_H + 42))
    reset_btn.draw(scr, mouse)
    back_btn.draw(scr, mouse)
    if toast:
        S.blit_text(scr, S.font(16, True), toast, C.GOLD, C.WIDTH // 2, SS.U(648))
    S.post_fx(scr, frame, grain=40)
