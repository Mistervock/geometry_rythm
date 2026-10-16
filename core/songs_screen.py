
#-- Импорт
import sys

import pygame

import config as C
import editor
import songs
import style as S

ROW_SONGS = 44
VISIBLE_SONGS = 7
ROW_CHARTS = 40
VISIBLE_CHARTS = 8


def _loading(scr, text):
    scr.fill((0, 0, 0))
    S.glitch_title(scr, S.font(22, True), text, C.CYAN, C.WIDTH // 2, C.HEIGHT // 2, 60)
    S.post_fx(scr, 0, grain=30)
    pygame.display.flip()


def songs_screen(clock):
    names = songs.list_songs()
    if not names:
        return _empty_screen(clock)
    view = "list"
    sel_song = 0
    top_song = 0
    sel_chart = 0
    top_chart = 0
    charts = []
    song = None
    song_dur = 0
    counts = {}
    confirm_del = False
    toast, toast_left = "", 0.0
    frame = 0

    back_btn = S.Btn((C.WIDTH // 2 - 70, 528, 140, 40), "НАЗАД", C.PURPLE_LIGHT, S.font(16, True))
    chart_btns = [
        ("play", S.Btn((80, 470, 150, 42), "ИГРАТЬ", C.GREEN, S.font(16, True))),
        ("edit", S.Btn((240, 470, 150, 42), "РЕДАКТ.", C.CYAN, S.font(16, True))),
        ("new", S.Btn((400, 470, 150, 42), "НОВЫЙ", C.GOLD, S.font(16, True))),
        ("del", S.Btn((560, 470, 150, 42), "УДАЛИТЬ", C.RED_LIGHT, S.font(16, True))),
    ]

    def open_song(idx):
        nonlocal view, song, song_dur, charts, sel_chart, top_chart, confirm_del
        song = names[idx]
        _loading(pygame.display.get_surface(), "ЗАГРУЗКА ПЕСНИ")
        song_dur = songs.info(song).get("duration_ms", 0)
        charts = songs.charts_for(song)
        sel_chart = 0
        top_chart = 0
        confirm_del = False
        view = "charts"

    def reload_charts(keep_name=None):
        nonlocal charts, sel_chart
        charts = songs.charts_for(song)
        sel_chart = 0
        if keep_name:
            for i, c in enumerate(charts):
                if c.name == keep_name:
                    sel_chart = i

    def do_action(action):
        nonlocal toast, toast_left, confirm_del
        if action == "play" and charts:
            return ("play", charts[sel_chart])
        if action == "edit" and charts:
            ch = charts[sel_chart]
            editor.Editor(clock, ch).run()
            reload_charts(keep_name=ch.name)
            return None
        if action == "new":
            ch = songs.new_chart(song)
            editor.Editor(clock, ch).run()
            if ch.path is not None:
                reload_charts(keep_name=ch.name)
            return None
        if action == "del" and charts:
            if not confirm_del:
                confirm_del = True
                toast, toast_left = "Нажмите ещё раз, чтобы удалить чарт", 3.0
            else:
                songs.delete_chart(charts[sel_chart])
                confirm_del = False
                reload_charts()
                toast, toast_left = "Чарт удалён", 2.0
        return None

    while True:
        dt = min(0.05, clock.tick(C.FPS) / 1000.0)
        frame += 1
        if toast_left > 0:
            toast_left -= dt
        mouse = pygame.mouse.get_pos()
        result = None
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if view == "list":
                result = _list_event(ev, mouse, names, sel_song, top_song, back_btn)
                if isinstance(result, tuple) and result[0] == "select":
                    sel_song = result[1]
                    top_song = result[2]
                    if result[3]:
                        open_song(sel_song)
                    result = None
                elif result == "back":
                    return None
            else:
                if ev.type == pygame.KEYDOWN:
                    if ev.key == pygame.K_ESCAPE:
                        view = "list"
                        confirm_del = False
                        continue
                    if ev.key in (pygame.K_UP, pygame.K_w):
                        sel_chart = max(0, sel_chart - 1)
                        confirm_del = False
                    elif ev.key in (pygame.K_DOWN, pygame.K_s):
                        sel_chart = min(max(0, len(charts) - 1), sel_chart + 1)
                        confirm_del = False
                    elif ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                        result = do_action("play")
                    elif ev.key == pygame.K_e:
                        do_action("edit")
                    elif ev.key == pygame.K_n:
                        do_action("new")
                    elif ev.key == pygame.K_DELETE:
                        do_action("del")
                elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                    for action, btn in chart_btns:
                        if btn.rect.collidepoint(ev.pos):
                            result = do_action(action)
                            break
                    else:
                        if back_btn.rect.collidepoint(ev.pos):
                            view = "list"
                            confirm_del = False
                        else:
                            idx = _row_at(ev.pos, 106, ROW_CHARTS, VISIBLE_CHARTS, top_chart,
                                          len(charts))
                            if idx is not None:
                                sel_chart = idx
                                confirm_del = False
                elif ev.type == pygame.MOUSEWHEEL:
                    top_chart = max(0, min(max(0, len(charts) - VISIBLE_CHARTS), top_chart - ev.y))
            if isinstance(result, tuple) and result[0] == "play":
                return result
            result = None

        if view == "list":
            if frame % 30 == 1:
                counts = {n: len(songs.charts_for(n)) for n in names}
            sel_song = max(0, min(sel_song, len(names) - 1))
            if sel_song < top_song:
                top_song = sel_song
            if sel_song >= top_song + VISIBLE_SONGS:
                top_song = sel_song - VISIBLE_SONGS + 1
            _draw_list(names, counts, sel_song, top_song, back_btn, mouse, frame)
        else:
            if sel_chart < top_chart:
                top_chart = sel_chart
            if sel_chart >= top_chart + VISIBLE_CHARTS:
                top_chart = sel_chart - VISIBLE_CHARTS + 1
            _draw_charts(song, song_dur, charts, sel_chart, top_chart, chart_btns, back_btn,
                         mouse, frame, toast if toast_left > 0 else "")
        pygame.display.flip()


def _row_at(pos, top_y, row_h, visible, top, total):
    x, y = pos
    if not (120 <= x <= C.WIDTH - 120) or y < top_y:
        return None
    i = (y - top_y) // row_h
    if i < 0 or i >= visible:
        return None
    idx = top + i
    return idx if idx < total else None


def _list_event(ev, mouse, names, sel, top, back_btn):
    if ev.type == pygame.KEYDOWN:
        if ev.key == pygame.K_ESCAPE:
            return "back"
        if ev.key in (pygame.K_UP, pygame.K_w):
            return ("select", max(0, sel - 1), top, False)
        if ev.key in (pygame.K_DOWN, pygame.K_s):
            return ("select", min(len(names) - 1, sel + 1), top, False)
        if ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
            return ("select", sel, top, True)
    elif ev.type == pygame.MOUSEWHEEL:
        new_top = max(0, min(max(0, len(names) - VISIBLE_SONGS), top - ev.y))
        return ("select", sel, new_top, False)
    elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
        if back_btn.rect.collidepoint(ev.pos):
            return "back"
        idx = _row_at(ev.pos, 120, ROW_SONGS, VISIBLE_SONGS, top, len(names))
        if idx is not None:
            return ("select", idx, top, True)
    return None


def _draw_list(names, counts, sel, top, back_btn, mouse, frame):
    scr = pygame.display.get_surface()
    scr.fill((0, 0, 0))
    S.draw_grid(scr, frame * 0.3, 0.0)
    S.glitch_title(scr, S.font(36, True), "ПЕСНИ", C.GOLD, C.WIDTH // 2, 60, frame)
    area = pygame.Rect(120, 100, C.WIDTH - 240, VISIBLE_SONGS * ROW_SONGS + 20)
    S.panel(scr, area, C.GOLD, alpha=215)
    for i in range(VISIBLE_SONGS):
        idx = top + i
        if idx >= len(names):
            break
        y = 110 + i * ROW_SONGS
        row = pygame.Rect(130, y, C.WIDTH - 260, ROW_SONGS - 6)
        active = idx == sel
        if active:
            pygame.draw.rect(scr, (34, 34, 68), row, border_radius=6)
            pygame.draw.rect(scr, C.CYAN, row, 2, border_radius=6)
        count = counts.get(names[idx], 0)
        col = C.WHITE if active else (190, 190, 210)
        scr.blit(S.font(18, True).render(songs.title(names[idx]), True, col), (row.x + 14, row.y + 6))
        sub = f"чартов: {count}"
        scr.blit(S.font(14).render(sub, True, C.GREY), (row.x + 14, row.y + 24))
    S.blit_text(scr, S.font(14), "Песни — файлы .ogg/.mp3/.wav в папке songs/", C.GREY,
                C.WIDTH // 2, 500)
    back_btn.draw(scr, mouse)
    S.post_fx(scr, frame, grain=40)


def _draw_charts(song, dur, charts, sel, top, chart_btns, back_btn, mouse, frame, toast):
    scr = pygame.display.get_surface()
    scr.fill((0, 0, 0))
    S.draw_grid(scr, frame * 0.3, 0.0)
    S.glitch_title(scr, S.font(30, True), songs.title(song), C.GOLD, C.WIDTH // 2, 50, frame)
    area = pygame.Rect(90, 96, C.WIDTH - 180, VISIBLE_CHARTS * ROW_CHARTS + 20)
    S.panel(scr, area, C.CYAN, alpha=215)
    if not charts:
        S.blit_text(scr, S.font(18), "чартов пока нет — нажмите НОВЫЙ", C.GREY,
                    C.WIDTH // 2, area.centery)
    for i in range(VISIBLE_CHARTS):
        idx = top + i
        if idx >= len(charts):
            break
        ch = charts[idx]
        y = 106 + i * ROW_CHARTS
        row = pygame.Rect(104, y, C.WIDTH - 208, ROW_CHARTS - 6)
        active = idx == sel
        if active:
            pygame.draw.rect(scr, (34, 34, 68), row, border_radius=6)
            pygame.draw.rect(scr, C.CYAN, row, 2, border_radius=6)
        col = C.WHITE if active else (190, 190, 210)
        scr.blit(S.font(16, True).render(ch.name, True, col), (row.x + 14, row.y + 9))
        density = len(ch.notes) / max(1, dur / 1000.0)
        sub = f"нот: {len(ch.notes)}   плотность: {density:.2f}/с"
        scr.blit(S.font(14).render(sub, True, C.GREY), (row.x + 260, row.y + 11))
    for action, btn in chart_btns:
        btn.draw(scr, mouse, active=False)
    back_btn.draw(scr, mouse)
    if toast:
        S.blit_text(scr, S.font(14, True), toast, C.GOLD, C.WIDTH // 2, 452)
    S.post_fx(scr, frame, grain=40)


def _empty_screen(clock):
    back = S.Btn((C.WIDTH // 2 - 70, 380, 140, 40), "НАЗАД", C.PURPLE_LIGHT, S.font(16, True))
    frame = 0
    while True:
        clock.tick(C.FPS)
        frame += 1
        mouse = pygame.mouse.get_pos()
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if ev.type == pygame.KEYDOWN and ev.key in (pygame.K_ESCAPE, pygame.K_RETURN):
                return None
            if ev.type == pygame.MOUSEBUTTONDOWN and back.hovered(ev.pos):
                return None
        scr = pygame.display.get_surface()
        scr.fill((0, 0, 0))
        S.glitch_title(scr, S.font(30, True), "ПЕСНИ", C.GOLD, C.WIDTH // 2, 200, frame)
        S.blit_text(scr, S.font(18), "Положите .ogg / .mp3 / .wav в папку songs/", C.GREY,
                    C.WIDTH // 2, 260)
        back.draw(scr, mouse)
        S.post_fx(scr, frame, grain=40)
        pygame.display.flip()
