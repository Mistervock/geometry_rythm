
#-- Импорт
import sys

import pygame

import achievements
import achievements_view as V
import config as C
import display
import events as EV
import screen_setting as SS
import style as S
from i18n import t

VISIBLE = 5
ROW = 76
FIELDS = ("name", "description", "image")
TEXT_LIMITS = {"name": achievements.NAME_MAX, "description": achievements.DESC_MAX}
# Расчётные прямоугольники (x, y, w, h); в пиксели переводит SS.UR при использовании
SAVE_RECT = (SS.REF_W // 2 - 190, 500, 180, 44)
CANCEL_RECT = (SS.REF_W // 2 + 10, 500, 180, 44)
FIELD_RECT = {
    "name": (250, 172, 560, 40),
    "description": (250, 250, 560, 84),
    "image": (250, 372, 560, 40),
}
THUMB_RECT = (860, 172, 160, 160)


def _commit(form):
    if form["edit"] in TEXT_LIMITS:
        form[form["edit"]] = form["buf"].strip()[:TEXT_LIMITS[form["edit"]]]
    form["edit"] = None


def _cycle_image(form, step, options):
    i = options.index(form["image"]) if form["image"] in options else 0
    form["image"] = options[(i + step) % len(options)]


def run(clock):
    items = achievements.list_all()
    sel, top, n = 0, 0, 0
    mode, form, confirm = "list", None, False
    toast, toast_left = "", 0.0
    btn_new = S.Btn(SS.UR(160, 628, 170, 44), t("НОВОЕ"), C.GREEN, S.font(16, True))
    btn_edit = S.Btn(SS.UR(350, 628, 170, 44), t("ИЗМЕНИТЬ"), C.CYAN, S.font(16, True))
    btn_del = S.Btn(SS.UR(540, 628, 170, 44), t("УДАЛИТЬ"), C.RED_LIGHT, S.font(16, True))
    btn_back = S.Btn(SS.UR(930, 628, 170, 44), t("НАЗАД"), C.PURPLE_LIGHT, S.font(16, True))
    save_btn = S.Btn(SS.UR(*SAVE_RECT), t("СОХРАНИТЬ"), C.GREEN, S.font(16, True))
    cancel_btn = S.Btn(SS.UR(*CANCEL_RECT), t("ОТМЕНА"), C.PURPLE_LIGHT, S.font(16, True))

    def reload(keep_path=None):
        nonlocal items, sel
        items = achievements.list_all()
        sel = next((i for i, (p, _) in enumerate(items) if p == keep_path), min(sel, max(0, len(items) - 1)))

    def open_form(path, data):
        nonlocal mode, form
        mode = "form"
        form = {"path": path, "name": data["name"], "description": data["description"],
                "image": data["image"], "field": 0, "edit": None, "buf": ""}

    def start_edit(field):
        form["field"] = FIELDS.index(field)
        form["edit"] = field
        form["buf"] = form[field]

    def save_form():
        nonlocal toast, toast_left
        path = achievements.save({"name": form["name"], "description": form["description"],
                                  "image": form["image"]}, form["path"])
        toast, toast_left = t("Достижение сохранено"), 2.0
        reload(keep_path=path)

    options = [""] + EV.list_images()

    while True:
        display.tick(clock)
        dt = 1 / 60
        if toast_left > 0:
            toast_left -= dt
        mouse = pygame.mouse.get_pos()
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if mode == "form":
                result = _form_event(ev, form, start_edit, save_form, options, cancel_btn, save_btn)
                if result == "leave":
                    mode, form = "list", None
                    reload()
                continue
            if ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE:
                    return
                if ev.key in (pygame.K_UP, pygame.K_w):
                    sel = max(0, sel - 1)
                    confirm = False
                elif ev.key in (pygame.K_DOWN, pygame.K_s):
                    sel = min(max(0, len(items) - 1), sel + 1)
                    confirm = False
                elif ev.key == pygame.K_n:
                    open_form(None, achievements.normalize({}))
                elif ev.key == pygame.K_e and items:
                    open_form(items[sel][0], items[sel][1])
            elif ev.type == pygame.MOUSEWHEEL:
                top = max(0, min(max(0, len(items) - VISIBLE), top - ev.y))
            elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                if btn_back.hovered(ev.pos):
                    return
                if btn_new.hovered(ev.pos):
                    open_form(None, achievements.normalize({}))
                elif btn_edit.hovered(ev.pos) and items:
                    open_form(items[sel][0], items[sel][1])
                elif btn_del.hovered(ev.pos) and items:
                    if not confirm:
                        confirm = True
                        toast, toast_left = t("Нажмите ещё раз, чтобы удалить"), 3.0
                    else:
                        achievements.delete(items[sel][0])
                        confirm = False
                        toast, toast_left = t("Достижение удалено"), 2.0
                        reload()
                else:
                    for i in range(VISIBLE):
                        idx = top + i
                        rect = pygame.Rect(SS.U(140), SS.U(110 + i * ROW), C.WIDTH - SS.U(280), SS.U(ROW - 8))
                        if idx < len(items) and rect.collidepoint(ev.pos):
                            sel = idx
                            confirm = False
        if mode == "list":
            sel = max(0, min(sel, len(items) - 1)) if items else 0
            if sel < top:
                top = sel
            if sel >= top + VISIBLE:
                top = sel - VISIBLE + 1
        if mode == "form":
            _draw_form(form, options, save_btn, cancel_btn, mouse, n)
        else:
            _draw_list(items, sel, top, btn_new, btn_edit, btn_del, btn_back, mouse, n,
                       toast if toast_left > 0 else "")
        pygame.display.flip()
        n += 1


def _form_event(ev, form, start_edit, save_form, options, cancel_btn, save_btn):
    if ev.type == pygame.KEYDOWN:
        if form["edit"] is not None:
            if ev.key == pygame.K_ESCAPE:
                form["edit"] = None
            elif ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_TAB, pygame.K_UP, pygame.K_DOWN):
                _commit(form)
                if ev.key == pygame.K_TAB or ev.key == pygame.K_DOWN:
                    form["field"] = (form["field"] + 1) % len(FIELDS)
                elif ev.key == pygame.K_UP:
                    form["field"] = (form["field"] - 1) % len(FIELDS)
            elif ev.key == pygame.K_BACKSPACE:
                form["buf"] = form["buf"][:-1]
            elif ev.unicode and ev.unicode.isprintable() and len(form["buf"]) < TEXT_LIMITS[form["edit"]]:
                form["buf"] += ev.unicode
            return None
        if ev.key == pygame.K_ESCAPE:
            return "leave"
        if ev.key in (pygame.K_UP, pygame.K_w):
            form["field"] = (form["field"] - 1) % len(FIELDS)
        elif ev.key in (pygame.K_DOWN, pygame.K_s, pygame.K_TAB):
            form["field"] = (form["field"] + 1) % len(FIELDS)
        elif FIELDS[form["field"]] == "image":
            if ev.key in (pygame.K_LEFT, pygame.K_a, pygame.K_RIGHT, pygame.K_d):
                _cycle_image(form, -1 if ev.key in (pygame.K_LEFT, pygame.K_a) else 1, options)
            elif ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                _cycle_image(form, 1, options)
        elif ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            start_edit(FIELDS[form["field"]])
        elif ev.unicode and ev.unicode.isprintable():
            start_edit(FIELDS[form["field"]])
            form["buf"] = ev.unicode
    elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
        if form["edit"] is not None:
            _commit(form)
        if save_btn.hovered(ev.pos):
            save_form()
            return "leave"
        if cancel_btn.hovered(ev.pos):
            return "leave"
        for field, rect in FIELD_RECT.items():
            if SS.UR(*rect).collidepoint(ev.pos):
                form["field"] = FIELDS.index(field)
                if field == "image":
                    _cycle_image(form, 1, options)
                else:
                    start_edit(field)
                break
    return None


def _draw_list(items, sel, top, btn_new, btn_edit, btn_del, btn_back, mouse, n, toast):
    scr = pygame.display.get_surface()
    scr.fill((0, 0, 0))
    S.draw_grid(scr, n * 0.3, 0.0)
    S.glitch_title(scr, S.font(36, True), t("ДОСТИЖЕНИЯ"), C.GOLD, C.WIDTH // 2, SS.U(60), n)
    S.panel(scr, pygame.Rect(SS.U(120), SS.U(100), C.WIDTH - SS.U(240), SS.U(VISIBLE * ROW + 20)), C.GOLD, alpha=215)
    if not items:
        S.blit_text(scr, S.font(18), t("Достижений пока нет — нажмите НОВОЕ"), C.GREY, C.WIDTH // 2, SS.U(200))
    for i in range(VISIBLE):
        idx = top + i
        if idx >= len(items):
            break
        V.draw_row(scr, pygame.Rect(SS.U(140), SS.U(110 + i * ROW), C.WIDTH - SS.U(280), SS.U(ROW - 8)),
                   items[idx][1], idx == sel)
    V.draw_detail(scr, pygame.Rect(SS.U(120), SS.U(500), C.WIDTH - SS.U(240), SS.U(110)),
                  items[sel][1] if items else None)
    for btn in (btn_new, btn_edit, btn_del, btn_back):
        btn.draw(scr, mouse)
    if toast:
        S.blit_text(scr, S.font(16, True), toast, C.GOLD, C.WIDTH // 2, SS.U(690))
    S.post_fx(scr, n, grain=40)


def _draw_form(form, options, save_btn, cancel_btn, mouse, n):
    scr = pygame.display.get_surface()
    scr.fill((0, 0, 0))
    S.draw_grid(scr, n * 0.3, 0.0)
    S.glitch_title(scr, S.font(32, True), t("ДОСТИЖЕНИЕ"), C.GOLD, C.WIDTH // 2, SS.U(60), n)
    S.panel(scr, SS.UR(200, 110, 880, 440), C.GOLD, alpha=215)
    caret = "|" if (n // 30) % 2 == 0 else " "
    labels = {"name": t("Название"), "description": t("Описание"), "image": t("Картинка (images/)")}
    for field in FIELDS:
        rect = SS.UR(*FIELD_RECT[field])
        active = FIELDS[form["field"]] == field
        scr.blit(S.font(15, True).render(labels[field], True, C.WHITE if active else C.GREY),
                 (rect.x, rect.y - SS.U(22)))
        pygame.draw.rect(scr, (34, 34, 68) if active else (14, 14, 30), rect, border_radius=SS.U(6))
        pygame.draw.rect(scr, C.CYAN if active else C.DIM, rect, SS.U(2), border_radius=SS.U(6))
        if field == "image":
            text = form["image"] or t("— нет, пустая картинка —")
            col = C.WHITE if form["image"] else C.DIM
            if active:
                text += "   ← →"
            scr.blit(S.font(16, True).render(text, True, col), (rect.x + SS.U(12), rect.y + SS.U(11)))
            continue
        if form["edit"] == field:
            shown = form["buf"] + caret
            lines = V.wrap(S.font(16, True), shown, rect.w - SS.U(24))
        else:
            lines = V.wrap(S.font(16, True), form[field] or " ", rect.w - SS.U(24))
        y = rect.y + SS.U(10) if field == "name" else rect.y + SS.U(8)
        for line in lines[:3 if field == "description" else 1]:
            scr.blit(S.font(16, True).render(line, True, C.WHITE), (rect.x + SS.U(12), y))
            y += SS.U(22)
    V.draw_thumb(scr, SS.UR(*THUMB_RECT), form["image"])
    save_btn.draw(scr, mouse)
    cancel_btn.draw(scr, mouse)
    S.blit_text(scr, S.font(13), t("Enter — ввести текст или сменить картинку · Tab — поле · ESC — назад"),
                C.GREY, C.WIDTH // 2, SS.U(600))
    S.post_fx(scr, n, grain=40)
