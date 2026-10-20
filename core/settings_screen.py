
#-- Импорт
import sys

import pygame

import audio
import config as C
import dialogs
import display
import cache
import screen_setting as SS
import settings
import style as S
from i18n import t

ROW_H = 31
ACTION_H = 40
ACTION_GAP = 14
TOP = 96

ROWS = (
    ("latency_ms", "Задержка звука, мс", "num"),
    ("scroll_ms", "Скорость нот, мс", "num"),
    ("music_volume", "Громкость музыки", "num"),
    ("sfx_volume", "Громкость эффектов", "num"),
    ("key0", "Клавиша дорожки 1", "key"),
    ("key1", "Клавиша дорожки 2", "key"),
    ("key2", "Клавиша дорожки 3", "key"),
    ("key3", "Клавиша дорожки 4", "key"),
    ("fullscreen", "Экран", "switch"),
    ("resolution", "Разрешение", "res"),
    ("preview", "Предпрослушивание песен", "switch"),
    ("media_dim", "Затемнение картинок и роликов", "num"),
    ("lang", "Язык", "lang"),
    ("reset", "Сбросить настройки", "action"),
    ("back", "НАЗАД", "action"),
)


def _value_text(kind_key, idx):
    if kind_key == "lang":
        return "Русский" if settings.get("lang") == "ru" else "English"
    if kind_key == "fullscreen":
        return t("На весь экран") if settings.get("fullscreen") else t("Оконно")
    if kind_key == "resolution":
        w, h = SS.size(SS.current())
        return f"{w} × {h}"
    if kind_key == "preview":
        return t("Вкл") if settings.get("preview") else t("Выкл")
    if kind_key.startswith("key"):
        return settings.key_label(settings.get("lane_keys")[int(kind_key[3])]).upper()
    if kind_key == "latency_ms":
        v = settings.get(kind_key)
        return f"{v:+d} {t('мс')}"
    if kind_key == "scroll_ms":
        return f"{settings.get(kind_key)} {t('мс')}"
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
                    name = pygame.key.name(ev.key).lower()
                    if name and name not in ("unknown key",):
                        _set_lane_key(waiting, name)
                        toast, toast_left = f"{t('Дорожка')} {waiting + 1}: {settings.key_label(name)}", 2.0
                    else:
                        toast, toast_left = t("Эта клавиша не подходит"), 2.0
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
                    if act == "reset":
                        act = _reset(clock)
                    if act == "back":
                        return
                    if act == "wait":
                        waiting = int(ROWS[sel][0][3])
                        toast, toast_left = t("Нажмите новую клавишу (ESC — отмена)"), 99
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
                        if act == "reset":
                            act = _reset(clock)
                        if act == "back":
                            return
                        if act == "wait":
                            waiting = int(key[3])
                            toast, toast_left = t("Нажмите новую клавишу (ESC — отмена)"), 99
                        elif act:
                            toast, toast_left = act, 1.5
        _draw(sel, waiting, toast if toast_left > 0 else "", mouse, frame)
        pygame.display.flip()


def _gap_before(i):
    return ACTION_GAP if ROWS[i][2] == "action" and i > 0 and ROWS[i - 1][2] != "action" else 0


def _row_h(i):
    return ACTION_H if ROWS[i][2] == "action" else ROW_H


def _row_y(i):
    return TOP + sum(_row_h(j) + _gap_before(j) for j in range(i)) + _gap_before(i)


def _panel_h():
    last = len(ROWS) - 1
    return _row_y(last) + _row_h(last) - TOP + 20


def _row_index(pos):
    x, y = pos[0] / SS.SCALE, pos[1] / SS.SCALE
    if y < TOP or not (140 <= x <= SS.REF_W - 140):
        return None
    for i in range(len(ROWS)):
        top = _row_y(i)
        if top <= y < top + _row_h(i):
            return i
    return None


def _cycle_resolution(direction):
    names = SS.names()
    i = names.index(SS.current()) if SS.current() in names else 0
    name = names[(i + direction) % len(names)]
    settings.set("resolution", name)
    SS.set_mode(name)
    display.apply()
    cache.warm()
    w, h = SS.size(name)
    return f"{w} × {h}"


def _toggle(key):
    if key == "fullscreen":
        display.toggle()
    elif key == "preview":
        settings.set("preview", 0 if settings.get("preview") else 1)


def _adjust(idx, direction):
    key, _, kind = ROWS[idx]
    if kind == "switch":
        _toggle(key)
        return ""
    if kind == "res":
        return _cycle_resolution(direction)
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
    if kind == "res":
        return _cycle_resolution(1)
    if kind == "switch":
        _toggle(key)
        return ""
    if key == "lang":
        settings.set("lang", "en" if settings.get("lang") == "ru" else "ru")
        return ""
    if key == "reset":
        return "reset"
    if key == "back":
        return "back"
    return ""


def _reset(clock):
    if not dialogs.confirm(clock, t("Все настройки вернутся к значениям по умолчанию. Это нельзя отменить.")):
        return ""
    settings.reset()
    SS.set_mode(settings.get("resolution"))
    display.apply()
    cache.warm()
    audio.set_music_volume()
    return t("Настройки сброшены")


def _draw(sel, waiting, toast, mouse, frame):
    scr = pygame.display.get_surface()
    scr.fill((0, 0, 0))
    S.draw_grid(scr, frame * 0.3, 0.0)
    S.glitch_title(scr, S.font(36, True), t("НАСТРОЙКИ"), C.CYAN, C.WIDTH // 2, SS.U(56), frame)
    area = pygame.Rect(SS.U(120), SS.U(TOP - 10), C.WIDTH - SS.U(240), SS.U(_panel_h()))
    S.panel(scr, area, C.CYAN, alpha=215)
    for i, (key, label, kind) in enumerate(ROWS):
        y = SS.U(_row_y(i))
        h = SS.U(_row_h(i))
        row = pygame.Rect(SS.U(140), y, C.WIDTH - SS.U(280), h - SS.U(4))
        active = i == sel
        if active:
            pygame.draw.rect(scr, (34, 34, 68), row, border_radius=SS.U(6))
            pygame.draw.rect(scr, C.CYAN, row, SS.U(2), border_radius=SS.U(6))
        col = C.WHITE if active else (190, 190, 210)
        if kind == "action":
            S.blit_text(scr, S.font(18, True), t(label), col, C.WIDTH // 2, y + (h - SS.U(4)) // 2)
            continue
        scr.blit(S.font(18, True).render(t(label), True, col), (row.x + SS.U(16), row.y + SS.U(5)))
        if kind == "num":
            val = _value_text(key, i)
            vt = S.font(18, True).render(f"<  {val}  >", True, C.GOLD if active else C.GREY)
            scr.blit(vt, (row.right - vt.get_width() - SS.U(16), row.y + SS.U(5)))
        else:
            if kind == "key" and waiting is not None and int(key[3]) == waiting:
                val, vcol = "...", C.RED_LIGHT
            else:
                val, vcol = _value_text(key, i), C.GOLD
            vt = S.font(18, True).render(val, True, vcol)
            scr.blit(vt, (row.right - vt.get_width() - SS.U(16), row.y + SS.U(5)))
    S.blit_text(scr, S.font(14), t("← → изменить · ENTER выбрать · ESC назад"), C.GREY,
                C.WIDTH // 2, C.HEIGHT - SS.U(16))
    if toast:
        S.blit_text(scr, S.font(16, True), toast, C.GOLD, C.WIDTH // 2, C.HEIGHT - SS.U(40))
    S.post_fx(scr, frame, grain=40)
