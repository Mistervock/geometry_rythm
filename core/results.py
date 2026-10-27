
#-- Импорт
import sys

import pygame

import audio
import config as C
import display
import records
import results_stats
import screen_setting as SS
import style as S
from i18n import t

ROW_H = 30


def results_screen(clock, res):
    score = res["score"]
    failed = res["failed"]
    grade = res["grade"]
    counts = res["counts"]
    practice = bool(res.get("practice"))
    can_record = (not practice) and records.qualifies(score)
    tab = 0
    unlocked = list(res.get("unlocked") or [])

    name = ""
    saved = None
    entries = records.load()
    blink = 0
    n = 0

    if practice:
        again_btn = S.Btn((C.WIDTH // 2 - SS.U(430), SS.U(614), SS.U(270), SS.U(52)), t("ЕЩЁ РАЗ"), C.CYAN, S.font(18, True))
        setup_btn = S.Btn((C.WIDTH // 2 - SS.U(135), SS.U(614), SS.U(270), SS.U(52)), t("ИЗМЕНИТЬ УЧАСТОК"), C.GOLD, S.font(17, True))
        menu_btn = S.Btn((C.WIDTH // 2 + SS.U(160), SS.U(614), SS.U(270), SS.U(52)), t("В МЕНЮ"), C.PURPLE_LIGHT, S.font(18, True))
    else:
        again_btn = S.Btn((C.WIDTH // 2 - SS.U(290), SS.U(614), SS.U(280), SS.U(52)), t("ЕЩЁ РАЗ"), C.CYAN, S.font(18, True))
        setup_btn = None
        menu_btn = S.Btn((C.WIDTH // 2 + SS.U(10), SS.U(614), SS.U(280), SS.U(52)), t("В МЕНЮ"), C.PURPLE_LIGHT, S.font(18, True))
    tab_btns = [S.Btn((SS.U(20 + i * 150), SS.U(10), SS.U(140), SS.U(30)), label, C.CYAN, S.font(13, True))
                for i, label in enumerate((t("ОБЗОР"), t("ПОДРОБНО")))]
    if failed:
        audio.play("split", 0.5)
    else:
        audio.play("achieve", 0.5)

    while True:
        display.tick(clock)
        blink = (blink + 1) % 60
        mouse = pygame.mouse.get_pos()
        ready = n >= 40
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if ev.type == pygame.KEYDOWN and ready and ev.key == pygame.K_TAB and (saved is not None or not can_record):
                tab = 1 - tab
                continue
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
                if ev.key == pygame.K_s and practice:
                    return "setup"
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1 and ready:
                buttons_open = saved is not None or not can_record
                for i, b in enumerate(tab_btns):
                    if buttons_open and b.rect.collidepoint(ev.pos):
                        tab = i
                if buttons_open and again_btn.rect.collidepoint(ev.pos):
                    return "again"
                if buttons_open and setup_btn is not None and setup_btn.rect.collidepoint(ev.pos):
                    return "setup"
                if buttons_open and menu_btn.rect.collidepoint(ev.pos):
                    return "menu"

        scr = pygame.display.get_surface()
        scr.fill((0, 0, 0))

        if tab == 1 and n >= 150:
            results_stats.draw(scr, res, n)
            for i, b in enumerate(tab_btns):
                b.draw(scr, mouse, active=(i == tab))
            again_btn.draw(scr, mouse)
            if setup_btn is not None:
                setup_btn.draw(scr, mouse)
            menu_btn.draw(scr, mouse)
            S.post_fx(scr, n, grain=50)
            display.flip()
            n += 1
            continue

        k = n - 10
        if k >= 0:
            title = t("ПРОВАЛ") if failed else (t("ПРАКТИКА") if practice else t("ФИНИШ"))
            col = C.RED_LIGHT if failed else C.GOLD
            S.glitch_title(scr, S.font(44, True), title, col, C.WIDTH // 2, SS.U(110), k)

        if n >= 20 and res.get("song"):
            S.blit_text(scr, S.font(14), f"{res['song']} — {res.get('chart', '')}", C.GREY,
                        C.WIDTH // 2, SS.U(149), 255 * S.smoothstep((n - 20) / 30))
        if n >= 30:
            S.blit_text(scr, S.font(22, True), f"{t('ОЧКИ')}  {score:06d}", C.GOLD,
                        C.WIDTH // 2, SS.U(180), S.smoothstep((n - 30) / 30) * 255)

        if n >= 60:
            g_col = C.RED_LIGHT if grade == "F" else C.CYAN
            S.blit_text(scr, S.font(52, True), grade, g_col, C.WIDTH // 2 - SS.U(90), SS.U(278),
                        255 * S.smoothstep((n - 60) / 30))
            S.blit_text(scr, S.font(18), f"{t('ТОЧНОСТЬ')} {res['acc']:.1f}%", C.WHITE,
                        C.WIDTH // 2 + SS.U(60), SS.U(271), 255 * S.smoothstep((n - 60) / 30))
            S.blit_text(scr, S.font(14), f"MAX COMBO {res['max_combo']}", C.GREY,
                        C.WIDTH // 2 + SS.U(60), SS.U(302), 255 * S.smoothstep((n - 70) / 30))

        if n >= 40 and practice:
            line = f"{int(res.get('speed', 1) * 100)}%   {res['section'][0] // 1000}–{res['section'][1] // 1000} {t('с')}   " \
                   f"{t('попыток')}: {len(res.get('attempts', []))}"
            best = max((a["acc"] for a in res.get("attempts", [])), default=None)
            if best is not None:
                line += f"   {t('лучшая точность')}: {best:.1f}%"
            S.blit_text(scr, S.fit(S.font(14, True), line, SS.U(760)), line, C.GOLD, C.WIDTH // 2, SS.U(208),
                        255 * S.smoothstep((n - 40) / 30))
        elif n >= 45 and res.get("pb_compare") and res["pb_compare"]["better"]:
            S.blit_text(scr, S.font(15, True), t("★ НОВЫЙ ЛИЧНЫЙ РЕКОРД"), C.GOLD, C.WIDTH // 2, SS.U(208),
                        255 * S.smoothstep((n - 45) / 30))

        if n >= 110 and res.get("rank") and not practice:
            rk = res["rank"]
            if rk["new"]:
                head = t("НОВЫЙ ЛУЧШИЙ РАНГ") if rk["prev"] else t("РАНГ ЧАРТА ПОЛУЧЕН")
                tail = f"{rk['prev']} → {rk['best']}" if rk["prev"] else rk["best"]
            else:
                head, tail = t("ЛУЧШИЙ РАНГ ЧАРТА"), rk["best"]
            line = f"{head}: {tail}"
            if rk.get("song"):
                line += f"   ·   {t('РАНГ ПЕСНИ')}: {rk['song']}"
            S.blit_text(scr, S.fit(S.font(14, True), line, SS.U(620)), line,
                        C.GOLD if rk["new"] else C.GREY, C.WIDTH // 2, SS.U(332),
                        255 * S.smoothstep((n - 110) / 30))

        if n >= 100:
            st = res.get("stats") or {}
            line = (f"PERFECT {counts['perfect']}   GREAT {counts['great']}   "
                    f"GOOD {counts['good']}   MISS {counts['miss']}")
            if st.get("holds_total"):
                line += f"   HOLD {st['holds_ok']}/{st['holds_total']}"
            S.blit_text(scr, S.font(14), line, C.GREY, C.WIDTH // 2, SS.U(355),
                        255 * S.smoothstep((n - 100) / 30))

        if n >= 120 and unlocked:
            name = unlocked[((n - 120) // 110) % len(unlocked)]
            line = f"{t('ДОСТИЖЕНИЕ ПОЛУЧЕНО')}: {name}"
            S.blit_text(scr, S.fit(S.font(14, True), line, SS.U(560)), line, C.GOLD,
                        C.WIDTH // 2, SS.U(372), 255 * S.smoothstep((n - 120) / 30))
        elif n >= 120 and res.get("achievement"):
            ach = res["achievement"]
            head = t("ДОСТИЖЕНИЕ ПОЛУЧЕНО") if ach["new"] else t("ДОСТИЖЕНИЕ")
            line = f"{head}: {ach['name']}"
            S.blit_text(scr, S.fit(S.font(14, True), line, SS.U(560)), line, C.GOLD,
                        C.WIDTH // 2, SS.U(372), 255 * S.smoothstep((n - 120) / 30))

        if n >= 130 and can_record and saved is None:
            box = pygame.Rect(C.WIDTH // 2 - SS.U(260), SS.U(398), SS.U(520), SS.U(100))
            S.panel(scr, box, C.GOLD, alpha=220)
            head = t("ВВЕДИТЕ ИМЯ ДЛЯ РЕКОРДОВ")
            S.blit_text(scr, S.fit(S.font(14, True), head, SS.U(480)), head, C.GOLD,
                        C.WIDTH // 2, SS.U(424))
            shown = name + ("|" if blink < 30 else " ")
            S.blit_text(scr, S.font(22, True), shown, C.WHITE, C.WIDTH // 2, SS.U(456))
            hint = t("ENTER — сохранить, ESC — не сохранять")
            S.blit_text(scr, S.fit(S.font(14), hint, SS.U(480)), hint, C.GREY,
                        C.WIDTH // 2, SS.U(484))

        if n >= 130 and (saved is not None or not can_record):
            shown_entries = saved[0] if saved is not None else entries
            highlight = saved[1] if saved is not None else None
            rows = shown_entries[:5]
            px, py, pw = C.WIDTH // 2 - SS.U(240), SS.U(396), SS.U(480)
            ph = SS.U(36) + max(1, len(rows)) * SS.U(ROW_H)
            S.panel(scr, pygame.Rect(px, py, pw, ph), C.GOLD, alpha=200)
            S.blit_text(scr, S.font(14, True), t("ТАБЛИЦА РЕКОРДОВ"), C.GOLD,
                        C.WIDTH // 2, py + SS.U(19))
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
                scr.blit(surf, (px + SS.U(16), py + SS.U(32) + idx * SS.U(ROW_H)))
            if not rows:
                S.blit_text(scr, S.font(14), t("пока пусто"), C.GREY, C.WIDTH // 2, py + SS.U(60))

        if n >= 150:
            ready_btns = saved is not None or not can_record
            if ready_btns:
                again_btn.draw(scr, mouse)
                if setup_btn is not None:
                    setup_btn.draw(scr, mouse)
                menu_btn.draw(scr, mouse)
                for i, b in enumerate(tab_btns):
                    b.draw(scr, mouse, active=(i == tab))
            hint = t("SPACE — ещё раз, S — участок, M — в меню, TAB — подробно") if practice \
                else t("SPACE — ещё раз, M — в меню, TAB — подробно")
            S.blit_text(scr, S.font(14), hint, (255, 210, 60), C.WIDTH // 2, SS.U(696))

        S.post_fx(scr, n, grain=50)
        if n < 20:
            ov = pygame.Surface((C.WIDTH, C.HEIGHT))
            ov.fill((0, 0, 0))
            ov.set_alpha(int(255 * (20 - n) / 20))
            scr.blit(ov, (0, 0))
        display.flip()
        n += 1
