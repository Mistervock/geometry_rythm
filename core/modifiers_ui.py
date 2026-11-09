"""Окно выбора модификаторов для чарта: кнопка «МОДИФ.» на экране песен.

Выбор сохраняется для каждого чарта отдельно (modifiers.save_choice). «ПО УМОЛЧАНИЮ» возвращает
рекомендацию автора из чарта. Esc — выйти без сохранения. В цикле скорости None означает «модификатор выключен».
"""
#-- Импорт
import sys

import pygame

import config as C
import display
import dialogs
import keymap
import modifiers as MD
import screen_setting as SS
import style as S
from i18n import t

BOX_W = 640
ROW_H = 54
SPEED_CYCLE = (None,) + MD.SPEEDS


#-- Состояние

def _next_speed(current):
    i = SPEED_CYCLE.index(current) if current in SPEED_CYCLE else 0
    return SPEED_CYCLE[(i + 1) % len(SPEED_CYCLE)]


def _toggle(state, row):
    """Меняет один ряд. state — словарь {id: value}; возвращает новый словарь."""
    out = dict(state)
    if row == "speed":
        nxt = _next_speed(out.get("speed"))
        if nxt is None:
            out.pop("speed", None)
        else:
            out["speed"] = nxt
    elif out.get(row):
        out.pop(row, None)
    else:
        out[row] = True
    return out


def _to_list(state):
    return MD.normalize([{"id": k, "value": v} for k, v in state.items()])


def _row_label(state, row):
    if row == "speed":
        v = state.get("speed")
        value = f"{v:g}×" if v else t("ВЫКЛ")
    else:
        value = t("ВКЛ") if state.get(row) else t("ВЫКЛ")
    return f"{t(MD.TITLES[row])}:  {value}"


#-- Окно

def panel(clock, chart):
    """Возвращает новый выбор (список модификаторов) или None, если окно закрыто без сохранения."""
    snap = dialogs._snapshot()
    state = MD.as_dict(MD.effective(chart))
    rows = list(MD.ORDER)
    actions = ("default", "done")
    box = pygame.Rect(0, 0, SS.U(BOX_W), SS.U(132) + len(rows) * SS.U(ROW_H) + SS.U(120))
    box.center = (C.WIDTH // 2, C.HEIGHT // 2)
    row_rects = [pygame.Rect(box.x + SS.U(60), box.y + SS.U(84) + i * SS.U(ROW_H), box.w - SS.U(120), SS.U(42))
                 for i in range(len(rows))]
    foot_y = box.y + SS.U(84) + len(rows) * SS.U(ROW_H) + SS.U(30)
    action_rects = {
        "default": pygame.Rect(box.x + SS.U(60), foot_y, SS.U(220), SS.U(40)),
        "done": pygame.Rect(box.right - SS.U(60) - SS.U(180), foot_y, SS.U(180), SS.U(40)),
    }
    sel = 0
    frame = 0
    total = len(rows) + len(actions)
    hint = t("Рекорды и призраки ведутся отдельно для каждого набора")

    def activate(idx):
        if idx < len(rows):
            return ("toggle", idx)
        return ("action", actions[idx - len(rows)])

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
                    sel = min(total - 1, sel + 1)
                elif keymap.hit("confirm", ev.key) or ev.key == pygame.K_SPACE:
                    kind, val = activate(sel)
                    if kind == "toggle":
                        state = _toggle(state, rows[val])
                    elif val == "default":
                        state = MD.as_dict(MD.normalize(getattr(chart, "modifiers", [])))
                    else:
                        MD.save_choice(chart, _to_list(state))
                        return _to_list(state)
            elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                hit = None
                for i, r in enumerate(row_rects):
                    if r.collidepoint(ev.pos):
                        hit = ("toggle", i)
                for name, r in action_rects.items():
                    if r.collidepoint(ev.pos):
                        hit = ("action", name)
                if hit is not None:
                    if hit[0] == "toggle":
                        state = _toggle(state, rows[hit[1]])
                        sel = hit[1]
                    elif hit[1] == "default":
                        state = MD.as_dict(MD.normalize(getattr(chart, "modifiers", [])))
                    else:
                        MD.save_choice(chart, _to_list(state))
                        return _to_list(state)

        scr = dialogs._begin_frame(snap, frame, box, C.CYAN)
        S.glitch_title(scr, S.font(22, True), t("МОДИФИКАТОРЫ"), C.CYAN, box.centerx, box.y + SS.U(34), frame)
        for i, (row, r) in enumerate(zip(rows, row_rects)):
            on = (row == "speed" and state.get("speed")) or (row != "speed" and state.get(row))
            btn = S.Btn(r, _row_label(state, row), C.CYAN if on else C.GREY, S.font(16, True))
            btn.draw(scr, mouse, active=i == sel)
        desc = t(MD.DESCS[rows[sel]]) if sel < len(rows) else hint
        scr.blit(S.font(13).render(desc, True, C.GREY), (box.centerx - S.font(13).size(desc)[0] // 2,
                                                         box.y + SS.U(84) + len(rows) * SS.U(ROW_H) - SS.U(6)))
        labels = {"default": t("ПО УМОЛЧАНИЮ"), "done": t("ГОТОВО")}
        for j, name in enumerate(actions):
            btn = S.Btn(action_rects[name], labels[name], C.GOLD if name == "done" else C.PURPLE_LIGHT,
                        S.font(16, True))
            btn.draw(scr, mouse, active=len(rows) + j == sel)
        dialogs._end_frame(scr, frame)
