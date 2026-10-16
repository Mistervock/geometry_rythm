
#-- Импорт
import sys

import pygame

import audio
import config as C
import records
import style as S
from i18n import t

ROW_H = 26


def results_screen(clock, res):
    score = res["score"]
    failed = res["failed"]
    grade = res["grade"]
    counts = res["counts"]
    can_record = records.qualifies(score)

    name = ""
    saved = None
    entries = records.load()
    blink = 0
    n = 0

    again_btn = S.Btn((C.WIDTH // 2 - 270, 512, 260, 44), t("ЕЩЁ РАЗ"), C.CYAN, S.font(18, True))
    menu_btn = S.Btn((C.WIDTH // 2 + 10, 512, 260, 44), t("В МЕНЮ"), C.PURPLE_LIGHT, S.font(18, True))
    if failed:
        audio.play("split", 0.5)
    else:
        audio.play("achieve", 0.5)

    while True:
        clock.tick(C.FPS)
        blink = (blink + 1) % 60
        mouse = pygame.mouse.get_pos()
        ready = n >= 40
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if ev.type == pygame.KEYDOWN and ready:
                if saved is None and can_record:
                    if ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                        entries, entry = records.add(name, score, res["acc"], grade,
                                                     res.get("song", ""), res.get("chart", ""))
                        saved = (entries, entry)
                    elif ev.key == pygame.K_BACKSPACE:
                        name = name[:-1]
                    elif ev.key == pygame.K_ESCAPE:
                        saved = (entries, None)
                    elif ev.unicode and ev.unicode.isprintable() and len(name) < 12:
                        name += ev.unicode
                    continue
                if ev.key in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_KP_ENTER):
                    return "again"
                if ev.key in (pygame.K_m, pygame.K_ESCAPE):
                    return "menu"
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1 and ready:
                buttons_open = saved is not None or not can_record
                if buttons_open and again_btn.rect.collidepoint(ev.pos):
                    return "again"
                if buttons_open and menu_btn.rect.collidepoint(ev.pos):
                    return "menu"

        scr = pygame.display.get_surface()
        scr.fill((0, 0, 0))

        k = n - 10
        if k >= 0:
            title = t("ПРОВАЛ") if failed else t("ФИНИШ")
            col = C.RED_LIGHT if failed else C.GOLD
            S.glitch_title(scr, S.font(44, True), title, col, C.WIDTH // 2, 92, k)

        if n >= 20 and res.get("song"):
            S.blit_text(scr, S.font(14), f"{res['song']} — {res.get('chart', '')}", C.GREY,
                        C.WIDTH // 2, 124, 255 * S.smoothstep((n - 20) / 30))
        if n >= 30:
            S.blit_text(scr, S.font(22, True), f"{t('ОЧКИ')}  {score:06d}", C.GOLD,
                        C.WIDTH // 2, 150, S.smoothstep((n - 30) / 30) * 255)

        if n >= 60:
            g_col = C.RED_LIGHT if grade == "F" else C.CYAN
            S.blit_text(scr, S.font(52, True), grade, g_col, C.WIDTH // 2 - 90, 232,
                        255 * S.smoothstep((n - 60) / 30))
            S.blit_text(scr, S.font(18), f"{t('ТОЧНОСТЬ')} {res['acc']:.1f}%", C.WHITE,
                        C.WIDTH // 2 + 60, 226, 255 * S.smoothstep((n - 60) / 30))
            S.blit_text(scr, S.font(14), f"MAX COMBO {res['max_combo']}", C.GREY,
                        C.WIDTH // 2 + 60, 252, 255 * S.smoothstep((n - 70) / 30))

        if n >= 100:
            line = (f"PERFECT {counts['perfect']}   GREAT {counts['great']}   "
                    f"GOOD {counts['good']}   MISS {counts['miss']}")
            S.blit_text(scr, S.font(14), line, C.GREY, C.WIDTH // 2, 296,
                        255 * S.smoothstep((n - 100) / 30))

        if n >= 130 and can_record and saved is None:
            box = pygame.Rect(C.WIDTH // 2 - 170, 340, 340, 48)
            S.panel(scr, box, C.GOLD, alpha=220)
            S.blit_text(scr, S.font(14, True), t("ВВЕДИТЕ ИМЯ ДЛЯ РЕКОРДОВ"), C.GOLD,
                        C.WIDTH // 2, 326)
            shown = name + ("|" if blink < 30 else " ")
            S.blit_text(scr, S.font(22, True), shown, C.WHITE, C.WIDTH // 2, 364)
            S.blit_text(scr, S.font(14), t("ENTER — сохранить, ESC — не сохранять"), C.GREY,
                        C.WIDTH // 2, 404)

        if n >= 130 and (saved is not None or not can_record):
            shown_entries = saved[0] if saved is not None else entries
            highlight = saved[1] if saved is not None else None
            rows = shown_entries[:5]
            px, py, pw = C.WIDTH // 2 - 200, 330, 400
            ph = 36 + max(1, len(rows)) * ROW_H
            S.panel(scr, pygame.Rect(px, py, pw, ph), C.GOLD, alpha=200)
            S.blit_text(scr, S.font(14, True), t("ТАБЛИЦА РЕКОРДОВ"), C.GOLD,
                        C.WIDTH // 2, py + 16)
            for idx, e in enumerate(rows):
                ka = n - (130 + idx * 8)
                if ka < 0:
                    continue
                alpha = min(255, ka * 255 / 14)
                col = (C.GOLD if idx == 0 else (210, 210, 210) if idx == 1
                       else (200, 120, 60) if idx == 2 else C.GREY)
                if e is highlight:
                    col = C.CYAN
                marker = "◄" if e is highlight else " "
                line = f"#{idx + 1:<2} {e['name'][:10]:<10} {e['score']:>6} {e['grade']:<2} {marker}"
                surf = S.font(14).render(line, True, col)
                surf.set_alpha(int(alpha))
                scr.blit(surf, (px + 16, py + 32 + idx * ROW_H))
            if not rows:
                S.blit_text(scr, S.font(14), t("пока пусто"), C.GREY, C.WIDTH // 2, py + 50)

        if n >= 150:
            ready_btns = saved is not None or not can_record
            if ready_btns:
                again_btn.draw(scr, mouse)
                menu_btn.draw(scr, mouse)
            S.blit_text(scr, S.font(14), t("SPACE — ещё раз, M — в меню"), (255, 210, 60),
                        C.WIDTH // 2, 580)

        S.post_fx(scr, n, grain=50)
        if n < 20:
            ov = pygame.Surface((C.WIDTH, C.HEIGHT))
            ov.fill((0, 0, 0))
            ov.set_alpha(int(255 * (20 - n) / 20))
            scr.blit(ov, (0, 0))
        pygame.display.flip()
        n += 1
