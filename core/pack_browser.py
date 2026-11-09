"""Список пакетов визуальных эффектов с предпросмотром (клавиша B в экране событий).

run(clock, current_id) возвращает id выбранного пакета или None, если выход по Esc или «ОТМЕНА».
Предпросмотр повторяет выбранный пакет в правой части экрана. R перечитывает папки packs/
и показывает файлы, которые не прошли проверку, с текстами из validation.MESSAGES.
"""
import sys
import time

import pygame

import config as C
import display
import packs as PK
import screen_setting as SS
import settings
import style as S
import validation as V
from i18n import t

LIST_X, LIST_Y, LIST_W, ROW_H = 60, 150, 420, 30
PREVIEW = (520, 150, 700, 320)
PREVIEW_PAUSE_MS = 500
MAX_ROWS = 12
SEED = 7
ISSUE_LINES = 4


def _ids():
    return sorted(PK.known_ids(), key=lambda pid: (PK.get(pid).get("name", pid), pid))


def _row_rect(i):
    return SS.UR(LIST_X, LIST_Y + i * ROW_H, LIST_W, ROW_H - 4)


def _clip(font, text, maxw):
    """Обрезает текст под ширину maxw пикселей, в конце многоточие."""
    if font.size(text)[0] <= maxw:
        return text
    while text and font.size(text + "…")[0] > maxw:
        text = text[:-1]
    return text + "…"


def _issue_lines():
    """Проблемы файлов пакетов текстом на языке интерфейса, не больше ISSUE_LINES строк."""
    rep = V.Report("packs")
    for name, code, where in PK.issues():
        rep.warn(code, where=f"{name}: {where}")
    return rep.lines(settings.get("lang"))[:ISSUE_LINES]


def run(clock, current_id=""):
    """Экран выбора пакета. Возвращает id или None."""
    scr = pygame.display.get_surface()
    ids = _ids()
    sel = ids.index(current_id) if current_id in ids else 0
    ok_btn = S.Btn(SS.UR(60, 600, 180, 40), t("ВЫБРАТЬ"), C.GREEN, S.font(16, True))
    cancel_btn = S.Btn(SS.UR(260, 600, 180, 40), t("ОТМЕНА"), C.DIM, S.font(16, True))
    notice = ""
    preview = None
    t0 = time.perf_counter()
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
                if ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER) and ids:
                    return ids[sel]
                if ev.key == pygame.K_UP and ids:
                    sel = (sel - 1) % len(ids)
                elif ev.key == pygame.K_DOWN and ids:
                    sel = (sel + 1) % len(ids)
                elif ev.key == pygame.K_r:
                    PK.reload()
                    ids = _ids()
                    sel = min(sel, max(0, len(ids) - 1))
                    preview = None
                    t0 = time.perf_counter()
                    notice = f"{t('Перечитано')}: {len(ids)}"
            elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                if ok_btn.rect.collidepoint(ev.pos) and ids:
                    return ids[sel]
                if cancel_btn.rect.collidepoint(ev.pos):
                    return None
                for i in range(min(MAX_ROWS, len(ids))):
                    if _row_rect(i).collidepoint(ev.pos):
                        sel = i
        scr.fill(C.BG_DARK)
        S.blit_text(scr, S.font(30, True), t("ПАКЕТЫ"), C.CYAN, C.WIDTH // 2, SS.U(70))
        S.blit_text(scr, S.font(13), t("↑↓ — выбор · Enter — выбрать · R — перечитать папку · Esc — отмена"),
                    C.GREY, C.WIDTH // 2, SS.U(106))
        if not ids:
            S.blit_text(scr, S.font(16, True), t("Пакетов нет. Положите .json в папку packs/ и нажмите R"),
                        C.GOLD, C.WIDTH // 2, SS.U(300))
        for i, pid in enumerate(ids[:MAX_ROWS]):
            pack = PK.get(pid)
            rect = _row_rect(i)
            active = i == sel
            if active:
                pygame.draw.rect(scr, (40, 40, 70), rect, border_radius=SS.U(6))
            info = S.font(12).render(f"{pid} · {PK.total_ms(pack) / 1000:.1f} {t('с')}", True, C.GREY)
            scr.blit(info, (rect.right - info.get_width() - SS.U(10), rect.y + SS.U(8)))
            name_font = S.font(15, active)
            name = _clip(name_font, pack.get("name", pid), rect.w - info.get_width() - SS.U(30))
            scr.blit(name_font.render(name, True, C.WHITE if active else C.GREY), (rect.x + SS.U(12), rect.y + SS.U(5)))
        if ids:
            pack = PK.get(ids[sel])
            if preview is None or preview[0] != ids[sel]:
                total = PK.total_ms(pack)
                preview = (ids[sel], PK.make_instance(pack, {}, 100, 0, SEED, total), total)
            _, inst, total = preview
            area = SS.UR(*PREVIEW)
            pygame.draw.rect(scr, C.GRID_COL, area, SS.U(2))
            elapsed = ((time.perf_counter() - t0) * 1000.0) % (total + PREVIEW_PAUSE_MS)
            scr.set_clip(area)
            if elapsed < total:
                inst.draw(scr, elapsed, SS.U(PREVIEW[0] + PREVIEW[2] // 2), SS.U(PREVIEW[1] + PREVIEW[3] // 2))
            scr.set_clip(None)
        y = SS.U(486)
        for line in _issue_lines():
            S.blit_text(scr, S.fit(S.font(13), line, SS.U(1100)), line, C.RED_LIGHT, C.WIDTH // 2, y)
            y += SS.U(20)
        ok_btn.draw(scr, mouse)
        cancel_btn.draw(scr, mouse)
        if notice:
            S.blit_text(scr, S.font(13), notice, C.GOLD, C.WIDTH // 2, SS.U(680))
        S.post_fx(scr, frame, grain=20)
        display.flip()
