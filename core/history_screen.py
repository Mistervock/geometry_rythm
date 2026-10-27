"""Экран «ИСТОРИЯ»: последние запуски чартов (завершённые и нет).

Запуск без результата — это не успех: он показан серым с пометкой «не завершён». Запись можно удалить,
песню открыть из истории (если файлы ещё на месте)."""
import sys
import time

import pygame

import config as C
import display
import keymap
import library
import screen_setting as SS
import songs
import style as S
from i18n import t

VISIBLE = 8
ROW = 50


def _when(ts):
    return time.strftime("%d.%m %H:%M", time.localtime(ts)) if ts else "—"


def _row_text(e):
    res = e["result"]
    if res is None:
        status, col = t("не завершён"), (110, 110, 140)
    elif res["failed"]:
        status, col = t("ПРОВАЛ"), C.RED_LIGHT
    else:
        status, col = f"{res['grade']}  {res['acc']:.1f}%  {res['score']:06d}", C.GOLD if res["grade"] == "S" else C.CYAN
    return status, col


def run(clock):
    """Возвращает (песня, чарт, режим) для запуска или None."""
    lib = library.get()
    entries = lib.history()
    sel, top, frame = 0, 0, 0
    toast, toast_left = "", 0.0
    confirm_clear = False
    specs = (("play", t("ИГРАТЬ"), C.GREEN, 150), ("practice", t("ПРАКТИКА"), C.GOLD, 160),
             ("del", t("УДАЛИТЬ"), C.RED_LIGHT, 150), ("clear", t("ОЧИСТИТЬ"), C.RED_LIGHT, 150),
             ("back", t("НАЗАД"), C.PURPLE_LIGHT, 140))
    x = (C.WIDTH - (sum(SS.U(w) for *_, w in specs) + SS.U(14) * (len(specs) - 1))) // 2
    btns = []
    for action, label, color, w in specs:
        btns.append((action, S.Btn((x, SS.U(612), SS.U(w), SS.U(42)), label, color, S.font(16, True))))
        x += SS.U(w) + SS.U(14)
    names = set(songs.list_songs())

    def current():
        return entries[sel] if entries and 0 <= sel < len(entries) else None

    def act(action):
        nonlocal entries, sel, toast, toast_left, confirm_clear
        e = current()
        if action == "back":
            return "back"
        if action in ("play", "practice") and e is not None:
            found = lib.resolve(e)
            if found is None:
                toast, toast_left = t("Песня или чарт больше не найдены"), 2.5
                return None
            return (found[0], found[1], action)
        if action == "del" and e is not None:
            lib.delete_entry(e["id"])
            entries = lib.history()
            sel = max(0, min(sel, len(entries) - 1))
            toast, toast_left = t("Запись удалена"), 1.5
        elif action == "clear" and entries:
            if not confirm_clear:
                confirm_clear = True
                toast, toast_left = t("Нажмите ещё раз, чтобы очистить всю историю"), 3.0
            else:
                lib.clear_history()
                entries = []
                confirm_clear = False
                toast, toast_left = t("История очищена"), 2.0
        return None

    while True:
        dt = min(0.05, display.tick(clock) / 1000.0)
        frame += 1
        toast_left = max(0.0, toast_left - dt)
        mouse = pygame.mouse.get_pos()
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            res = None
            if ev.type == pygame.KEYDOWN:
                if keymap.hit("back", ev.key):
                    return None
                if keymap.hit("up", ev.key):
                    sel = max(0, sel - 1)
                    confirm_clear = False
                elif keymap.hit("down", ev.key):
                    sel = min(max(0, len(entries) - 1), sel + 1)
                    confirm_clear = False
                elif keymap.hit("confirm", ev.key):
                    res = act("play")
                elif ev.key == pygame.K_DELETE:
                    res = act("del")
            elif ev.type == pygame.MOUSEWHEEL:
                top = max(0, min(max(0, len(entries) - VISIBLE), top - ev.y))
            elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                for action, b in btns:
                    if b.rect.collidepoint(ev.pos):
                        res = act(action)
                        break
                else:
                    for i in range(VISIBLE):
                        rect = pygame.Rect(SS.U(140), SS.U(106 + i * ROW), C.WIDTH - SS.U(280), SS.U(ROW - 6))
                        if top + i < len(entries) and rect.collidepoint(ev.pos):
                            sel = top + i
                            confirm_clear = False
            if res == "back":
                return None
            if isinstance(res, tuple):
                return res
        if sel < top:
            top = sel
        if sel >= top + VISIBLE:
            top = sel - VISIBLE + 1

        scr = pygame.display.get_surface()
        scr.fill((0, 0, 0))
        S.draw_grid(scr, frame * 0.3, 0.0)
        S.glitch_title(scr, S.font(36, True), t("ИСТОРИЯ"), C.CYAN, C.WIDTH // 2, SS.U(56), frame)
        S.panel(scr, pygame.Rect(SS.U(120), SS.U(96), C.WIDTH - SS.U(240), SS.U(VISIBLE * ROW + 18)), C.CYAN, alpha=215)
        if not entries:
            S.blit_text(scr, S.font(18), t("История пуста — сыграйте первый чарт"), C.GREY, C.WIDTH // 2, SS.U(300))
        for i in range(VISIBLE):
            idx = top + i
            if idx >= len(entries):
                break
            e = entries[idx]
            rect = pygame.Rect(SS.U(140), SS.U(106 + i * ROW), C.WIDTH - SS.U(280), SS.U(ROW - 6))
            if idx == sel:
                pygame.draw.rect(scr, (34, 34, 68), rect, border_radius=SS.U(6))
                pygame.draw.rect(scr, C.CYAN, rect, SS.U(2), border_radius=SS.U(6))
            status, col = _row_text(e)
            missing = e["song"] not in names
            title = f"{e['song_title']} — {e['chart_name']}"
            tcol = C.WHITE if idx == sel else (190, 190, 210)
            if missing:
                tcol = (110, 110, 130)
            scr.blit(S.fit(S.font(16, True), title, SS.U(520)).render(title, True, tcol), (rect.x + SS.U(14), rect.y + SS.U(5)))
            sub = f"{_when(e['started'])}   {t('ПРАКТИКА') if e['kind'] == 'practice' else t('ИГРА')}"
            if missing:
                sub += f"   {t('нет файла')}"
            scr.blit(S.font(12).render(sub, True, C.GREY), (rect.x + SS.U(14), rect.y + SS.U(26)))
            st = S.font(15, True).render(status, True, col)
            scr.blit(st, (rect.right - st.get_width() - SS.U(14), rect.centery - st.get_height() // 2))
        for action, b in btns:
            b.draw(scr, mouse)
        if toast_left > 0:
            S.blit_text(scr, S.font(15), toast, C.GOLD, C.WIDTH // 2, SS.U(590))
        S.post_fx(scr, frame, grain=40)
        display.flip()
