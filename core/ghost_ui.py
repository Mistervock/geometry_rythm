"""Окно выбора призрака для чарта: кнопка «ПРИЗРАК» на экране песен.

Варианты: свой лучший проход (для набора модификаторов, с которым чарт сейчас запускается), без призрака
и файлы из папки data/ghosts/import/. Импортированный призрак помечен «НЕ ПРОВЕРЕНО»: игра не может
подтвердить, что проход был настоящим. Файлы, которые не подходят к чарту или к набору модификаторов,
видны, но выбрать их нельзя. «ЭКСПОРТ» копирует свой призрак в data/ghosts/export/.
"""
#-- Импорт
import sys

import pygame

import config as C
import dialogs
import display
import ghost as GH
import keymap
import modifiers as MD
import screen_setting as SS
import style as S
from i18n import t

BOX_W = 660
ROW_H = 44
MAX_IMPORTS = 5
REASONS = {
    GH.STALE: "другие ноты — не подходит",
    GH.OTHER_MODS: "другие модификаторы — не подходит",
    GH.CORRUPT: "файл повреждён",
    GH.NEWER: "записан новой версией игры",
}


#-- Строки окна

def _own_label(own):
    if own is None:
        return f"{t('Свой лучший проход')}: {t('пока нет')}"
    return f"{t('Свой лучший проход')}: {own.grade} · {own.score:06d} · {own.acc:.2f}%"


def _entries(chart, mods):
    """Строки окна: dict(value, label, ok, tag). value — то, что запишется в выбор; ok — можно ли выбрать."""
    own, _ = GH.load(chart, None, mods)
    rows = [
        {"value": GH.CHOICE_OWN, "label": _own_label(own), "ok": True, "tag": ""},
        {"value": GH.CHOICE_NONE, "label": t("Без призрака"), "ok": True, "tag": ""},
    ]
    for name, status, g in GH.inspect_imports(chart, mods)[:MAX_IMPORTS]:
        short = name[:-len(".ghost.json")][:28]
        if status == GH.OK:
            label = f"{short}: {g.grade} · {g.score:06d} · {g.acc:.2f}%"
            rows.append({"value": GH.IMPORT_PREFIX + name, "label": label, "ok": True,
                         "tag": t("НЕ ПРОВЕРЕНО")})
        else:
            rows.append({"value": GH.IMPORT_PREFIX + name, "label": f"{short}: {t(REASONS.get(status, 'не подходит'))}",
                         "ok": False, "tag": ""})
    rows.append({"value": "export", "label": t("ЭКСПОРТ СВОЕГО ПРИЗРАКА"), "ok": True, "tag": ""})
    rows.append({"value": "refresh", "label": t("ОБНОВИТЬ ПАПКУ ИМПОРТА"), "ok": True, "tag": ""})
    return rows


#-- Окно

def panel(clock, chart):
    """Возвращает значение выбора (CHOICE_OWN / CHOICE_NONE / «import:имя») или None, если окно закрыто без выбора."""
    snap = dialogs._snapshot()
    mods = MD.effective(chart)
    rows = _entries(chart, mods)
    sel = 0
    frame = 0
    status = ""
    box = pygame.Rect(0, 0, SS.U(BOX_W), SS.U(96) + SS.U(ROW_H) * (4 + MAX_IMPORTS) + SS.U(76))
    box.center = (C.WIDTH // 2, C.HEIGHT // 2)

    def row_rect(i):
        return pygame.Rect(box.x + SS.U(40), box.y + SS.U(78) + i * SS.U(ROW_H), box.w - SS.U(80), SS.U(36))

    def activate(i):
        nonlocal rows, status
        row = rows[i]
        if row["value"] == "export":
            path = GH.export_own(chart, mods)
            status = f"{t('Экспорт')}: {path}" if path else t("Своего призрака для этого набора пока нет")
            return None
        if row["value"] == "refresh":
            rows = _entries(chart, mods)
            status = t("Папка импорта обновлена")
            return None
        if not row["ok"]:
            status = t("Этот призрак не подходит к чарту или набору модификаторов")
            return None
        GH.save_choice(chart, row["value"])
        return row["value"]

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
                    sel = min(len(rows) - 1, sel + 1)
                elif keymap.hit("confirm", ev.key) or ev.key == pygame.K_SPACE:
                    result = activate(sel)
                    if result is not None:
                        return result
            elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                for i in range(len(rows)):
                    if row_rect(i).collidepoint(ev.pos):
                        sel = i
                        result = activate(i)
                        if result is not None:
                            return result
                        break

        scr = dialogs._begin_frame(snap, frame, box, C.CYAN)
        S.glitch_title(scr, S.font(22, True), t("ПРИЗРАК"), C.CYAN, box.centerx, box.y + SS.U(34), frame)
        current = GH.choice_of(chart)
        for i, row in enumerate(rows):
            on = row["value"] == current
            label = ("● " if on else "  ") + row["label"]
            if row["tag"]:
                label += f"   [{row['tag']}]"
            color = C.CYAN if row["ok"] and on else C.GREY if row["ok"] else C.DIM
            btn = S.Btn(row_rect(i), label, color, S.font(14, True))
            btn.draw(scr, mouse, active=i == sel)
        hint_y = box.bottom - SS.U(54)
        if status:
            S.blit_text(scr, S.font(13, True), status, C.GOLD, box.centerx, hint_y)
        S.blit_text(scr, S.font(12), t("Файлы призраков кладите в data/ghosts/import/ · Enter — выбрать · Esc — отмена"),
                    C.GREY, box.centerx, box.bottom - SS.U(24))
        dialogs._end_frame(scr, frame)
