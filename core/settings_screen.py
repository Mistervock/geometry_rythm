
#-- Импорт
import sys

import pygame

import audio
import config as C
import settings
import style as S

ROW_H = 40
TOP = 110

ROWS = (
    ("latency_ms", "Задержка звука, мс", "num"),
    ("scroll_ms", "Скорость нот, мс", "num"),
    ("music_volume", "Громкость музыки", "num"),
    ("sfx_volume", "Громкость эффектов", "num"),
    ("key0", "Клавиша дорожки 1", "key"),
    ("key1", "Клавиша дорожки 2", "key"),
    ("key2", "Клавиша дорожки 3", "key"),
    ("key3", "Клавиша дорожки 4", "key"),
    ("reset", "Сбросить настройки", "action"),
    ("back", "НАЗАД", "action"),
)


def _value_text(kind_key, idx):
    if kind_key.startswith("key"):
        return settings.key_label(settings.get("lane_keys")[int(kind_key[3])]).upper()
    if kind_key == "latency_ms":
        v = settings.get(kind_key)
        return f"{v:+d} мс"
    if kind_key == "scroll_ms":
        return f"{settings.get(kind_key)} мс"
    return f"{settings.get(kind_key)} %"


def _set_lane_key(lane, key_name):
    keys = list(settings.get("lane_keys"))
    if key_name in keys:
        other = keys.index(key_name)
        keys[other] = keys[lane]
    keys[lane] = key_name
    settings.set("lane_keys", keys)


def settings_screen(clock):
    sel = 0
    waiting = None
    toast, toast_left = "", 0.0
    frame = 0
    while True:
        dt = min(0.05, clock.tick(C.FPS) / 1000.0)
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
                    toast, toast_left = "Отменено", 1.5
                else:
                    name = pygame.key.name(ev.key).lower()
                    if name and name not in ("unknown key",):
                        _set_lane_key(waiting, name)
                        toast, toast_left = f"Дорожка {waiting + 1}: {settings.key_label(name)}", 2.0
                    else:
                        toast, toast_left = "Эта клавиша не подходит", 2.0
                waiting = None
                continue
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE:
                    return
                if ev.key in (pygame.K_UP, pygame.K_w):
                    sel = (sel - 1) % len(ROWS)
                elif ev.key in (pygame.K_DOWN, pygame.K_s):
                    sel = (sel + 1) % len(ROWS)
                elif ev.key in (pygame.K_LEFT, pygame.K_a):
                    toast = _adjust(sel, -1)
                    toast_left = 1.2 if toast else 0.0
                elif ev.key in (pygame.K_RIGHT, pygame.K_d):
                    toast = _adjust(sel, 1)
                    toast_left = 1.2 if toast else 0.0
                elif ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                    act = _activate(sel)
                    if act == "back":
                        return
                    if act == "wait":
                        waiting = int(ROWS[sel][0][3])
                        toast, toast_left = "Нажмите новую клавишу (ESC — отмена)", 99
                    elif act:
                        toast, toast_left = act, 1.5
            elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                idx = _row_index(ev.pos)
                if idx is not None:
                    sel = idx
                    key, _, kind = ROWS[idx]
                    if kind == "num":
                        direction = -1 if ev.pos[0] < C.WIDTH // 2 else 1
                        toast = _adjust(idx, direction)
                        toast_left = 1.2 if toast else 0.0
                    else:
                        act = _activate(idx)
                        if act == "back":
                            return
                        if act == "wait":
                            waiting = int(key[3])
                            toast, toast_left = "Нажмите новую клавишу (ESC — отмена)", 99
                        elif act:
                            toast, toast_left = act, 1.5
        _draw(sel, waiting, toast if toast_left > 0 else "", mouse, frame)
        pygame.display.flip()


def _row_index(pos):
    x, y = pos
    if y < TOP or not (140 <= x <= C.WIDTH - 140):
        return None
    i = (y - TOP) // ROW_H
    return i if 0 <= i < len(ROWS) else None


def _adjust(idx, direction):
    key, _, kind = ROWS[idx]
    if kind != "num":
        return ""
    settings.step(key, direction)
    if key == "music_volume":
        audio.set_music_volume()
    return ""


def _activate(idx):
    key, _, kind = ROWS[idx]
    if key.startswith("key"):
        return "wait"
    if key == "reset":
        settings.reset()
        audio.set_music_volume()
        return "Настройки сброшены"
    if key == "back":
        return "back"
    return ""


def _draw(sel, waiting, toast, mouse, frame):
    scr = pygame.display.get_surface()
    scr.fill((0, 0, 0))
    S.draw_grid(scr, frame * 0.3, 0.0)
    S.glitch_title(scr, S.font(36, True), "НАСТРОЙКИ", C.CYAN, C.WIDTH // 2, 56, frame)
    area = pygame.Rect(120, TOP - 10, C.WIDTH - 240, len(ROWS) * ROW_H + 10)
    S.panel(scr, area, C.CYAN, alpha=215)
    for i, (key, label, kind) in enumerate(ROWS):
        y = TOP + i * ROW_H
        row = pygame.Rect(140, y, C.WIDTH - 280, ROW_H - 6)
        active = i == sel
        if active:
            pygame.draw.rect(scr, (34, 34, 68), row, border_radius=6)
            pygame.draw.rect(scr, C.CYAN, row, 2, border_radius=6)
        col = C.WHITE if active else (190, 190, 210)
        if kind == "action":
            S.blit_text(scr, S.font(18, True), label, col, C.WIDTH // 2, y + (ROW_H - 6) // 2)
            continue
        scr.blit(S.font(18, True).render(label, True, col), (row.x + 16, row.y + 12))
        if kind == "num":
            val = _value_text(key, i)
            vt = S.font(18, True).render(f"<  {val}  >", True, C.GOLD if active else C.GREY)
            scr.blit(vt, (row.right - vt.get_width() - 16, row.y + 12))
        else:
            if waiting is not None and int(key[3]) == waiting:
                val, vcol = "...", C.RED_LIGHT
            else:
                val, vcol = _value_text(key, i), C.GOLD
            vt = S.font(18, True).render(val, True, vcol)
            scr.blit(vt, (row.right - vt.get_width() - 16, row.y + 12))
    S.blit_text(scr, S.font(14), "← → изменить · ENTER выбрать · ESC назад", C.GREY,
                C.WIDTH // 2, C.HEIGHT - 26)
    if toast:
        S.blit_text(scr, S.font(16, True), toast, C.GOLD, C.WIDTH // 2, C.HEIGHT - 58)
    S.post_fx(scr, frame, grain=40)
