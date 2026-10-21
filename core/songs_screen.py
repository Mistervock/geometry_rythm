#-- Импорт
import random
import sys

import pygame

import audio
import config as C
import dev_menu
import display
import editor
import keymap
import settings
import screen_setting as SS
import songs
import style as S
from i18n import t

ROW_SONGS = 50
VISIBLE_SONGS = 7
ROW_CHARTS = 46
VISIBLE_CHARTS = 7
PREVIEW_MS = 15000
PREVIEW_DELAY = 0.35
SEARCH_MAX = 30
BLACK = (0, 0, 0)

# Сортировки списка песен: ключ, подпись
SORTS = (
    ("author", "Автор (группы)"),
    ("title", "Название А–Я"),
    ("rank", "Лучший ранг"),
    ("charts", "Число чартов"),
)
RANK_COL = {"S": C.GOLD, "A": C.CYAN, "B": C.GREEN, "C": C.PURPLE_LIGHT, "D": C.RED_LIGHT}


def _loading(scr, text):
    scr.fill((0, 0, 0))
    S.glitch_title(scr, S.font(22, True), text, C.CYAN, C.WIDTH // 2, C.HEIGHT // 2, 60)
    S.post_fx(scr, 0, grain=30)
    display.flip()


def songs_screen(clock):
    try:
        return _songs_loop(clock)
    finally:
        audio.stop_song()


def _play_preview(name):
    dur = songs.info(name).get("duration_ms", 0)
    start = int(dur * 0.3) if dur > 40000 else 0
    audio.play_song(songs.song_path(name), start)


#-- Поиск, сортировка и группы по автору

def _rank_points(stat):
    grade = stat[2] if len(stat) > 2 else None
    return songs.RANK_POINTS.get(grade, 0)


def _matches(query, stat):
    hay = stat[3] if len(stat) > 3 else ""
    return all(word in hay for word in query.lower().split())


def _entries(names, mode="author", stats=None, query=""):
    """Строки списка: ("head", автор) и ("song", файл).

    mode "author" — группы с подзаголовками авторов, остальные режимы — плоский список.
    query оставляет только песни, где все слова запроса встречаются в названии, авторе или чартах."""
    stats = stats or {}
    if query.strip():
        names = [n for n in names if _matches(query, stats.get(n, (0, 0, None, songs.display_title(n).lower())))]
    if mode == "title":
        return [("song", n) for n in sorted(names, key=lambda n: songs.display_title(n).lower())]
    if mode == "rank":
        return [("song", n) for n in sorted(
            names, key=lambda n: (-_rank_points(stats.get(n, (0, 0, None))), songs.display_title(n).lower()))]
    if mode == "charts":
        return [("song", n) for n in sorted(
            names, key=lambda n: (-stats.get(n, (0,))[0], songs.display_title(n).lower()))]
    groups = {}
    for n in names:
        groups.setdefault(songs.author_of(n), []).append(n)
    if list(groups) == [""]:
        return [("song", n) for n in names]
    out = []
    for author in sorted((a for a in groups if a), key=str.lower):
        out.append(("head", author))
        out += [("song", n) for n in groups[author]]
    if "" in groups:
        out.append(("head", ""))
        out += [("song", n) for n in groups[""]]
    return out


def _refresh(names):
    """Для каждой песни: (число чартов, состояние побед, общий ранг, строка для поиска) и цвета авторов."""
    stats = {}
    ranks = songs._ranks()
    for n in names:
        charts = songs.charts_for(n)
        won = [songs.is_won(c) for c in charts]
        state = 2 if charts and all(won) else (1 if any(won) else 0)
        hay = " ".join([songs.display_title(n), songs.author_of(n)]
                       + [f"{c.name} {c.charter}" for c in charts]).lower()
        stats[n] = (len(charts), state, songs.song_rank(n, charts, ranks), hay)
    colors = {}
    for n in names:
        a = songs.author_of(n)
        if a not in colors:
            colors[a] = songs.author_color(a) if a else None
    return stats, colors


def _bg_color(song, colors):
    col = colors.get(songs.author_of(song))
    return tuple(int(c) for c in col) if col else BLACK


def _search_rect():
    return pygame.Rect(SS.UR(120, 34, 360, 34))


def _sort_rect():
    return pygame.Rect(SS.UR(800, 34, 360, 34))


#-- Цикл

def _songs_loop(clock):
    all_names = songs.list_songs()
    if not all_names:
        return _empty_screen(clock)
    query, typing, sort_i = "", False, 0
    stats, colors = _refresh(all_names)
    entries = _entries(all_names, SORTS[sort_i][0], stats, query)
    names = [v for k, v in entries if k == "song"]
    view = "list"
    sel_song = 0
    top_song = 0
    sel_chart = 0
    top_chart = 0
    charts = []
    chart_ranks = []
    song = None
    song_dur = 0
    cover = None
    confirm_del = False
    toast, toast_left = "", 0.0
    frame = 0
    preview_song, pending, pending_left, preview_left = None, None, 0.0, 0.0

    back_btn = S.Btn((C.WIDTH // 2 - SS.U(70), SS.U(528), SS.U(140), SS.U(40)), t("НАЗАД"), C.PURPLE_LIGHT, S.font(16, True))
    random_btn = S.Btn((C.WIDTH // 2 + SS.U(90), SS.U(528), SS.U(200), SS.U(40)), t("СЛУЧАЙНАЯ"), C.GOLD, S.font(16, True))
    chart_specs = (
        ("play", t("ИГРАТЬ"), C.GREEN, 150),
        ("edit", t("РЕДАКТ."), C.CYAN, 150),
        ("new", t("НОВЫЙ"), C.GOLD, 150),
        ("del", t("УДАЛИТЬ"), C.RED_LIGHT, 150),
        ("back", t("НАЗАД"), C.PURPLE_LIGHT, 140),
    )
    chart_btns = []
    x = (C.WIDTH - (sum(SS.U(w) for *_, w in chart_specs) + SS.U(14) * (len(chart_specs) - 1))) // 2
    for action, label, color, w in chart_specs:
        chart_btns.append((action, S.Btn((x, SS.U(458), SS.U(w), SS.U(42)), label, color, S.font(16, True))))
        x += SS.U(w) + SS.U(14)

    def rebuild(reset_top=False):
        """Пересобирает список после смены запроса, сортировки или статистики. Выбор остаётся на той же песне."""
        nonlocal entries, names, sel_song, top_song
        keep = names[sel_song] if names and sel_song < len(names) else None
        entries = _entries(all_names, SORTS[sort_i][0], stats, query)
        names = [v for k, v in entries if k == "song"]
        sel_song = names.index(keep) if keep in names else 0
        if reset_top or keep not in names:
            top_song = 0

    def load_charts():
        nonlocal charts, chart_ranks
        charts = songs.charts_for(song)
        ranks = songs._ranks()
        chart_ranks = [songs.chart_rank(c, ranks) for c in charts]

    def open_song(idx):
        nonlocal view, song, song_dur, sel_chart, top_chart, confirm_del, cover
        song = names[idx]
        _loading(pygame.display.get_surface(), t("ЗАГРУЗКА ПЕСНИ"))
        song_dur = songs.info(song).get("duration_ms", 0)
        load_charts()
        cover = songs.cover_surface(song)
        sel_chart = 0
        top_chart = 0
        confirm_del = False
        view = "charts"

    def reload_charts(keep_name=None):
        nonlocal sel_chart
        load_charts()
        sel_chart = 0
        if keep_name:
            for i, c in enumerate(charts):
                if c.name == keep_name:
                    sel_chart = i

    def do_action(action):
        nonlocal toast, toast_left, confirm_del, view
        if action == "back":
            view = "list"
            confirm_del = False
            return None
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
                toast, toast_left = t("Нажмите ещё раз, чтобы удалить чарт"), 3.0
            else:
                songs.delete_chart(charts[sel_chart])
                confirm_del = False
                reload_charts()
                toast, toast_left = t("Чарт удалён"), 2.0
        return None

    while True:
        dt = min(0.05, display.tick(clock) / 1000.0)
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
                if typing and ev.type == pygame.KEYDOWN:
                    if ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                        typing = False
                        if names:
                            open_song(sel_song)
                    elif ev.key == pygame.K_ESCAPE:
                        typing = False
                    elif ev.key == pygame.K_BACKSPACE:
                        query = query[:-1]
                        rebuild(reset_top=True)
                    elif ev.key == pygame.K_UP and names:
                        sel_song = max(0, sel_song - 1)
                    elif ev.key == pygame.K_DOWN and names:
                        sel_song = min(len(names) - 1, sel_song + 1)
                    elif ev.unicode and ev.unicode.isprintable() and len(query) < SEARCH_MAX:
                        query += ev.unicode
                        rebuild(reset_top=True)
                    continue
                result = _list_event(ev, mouse, entries, names, sel_song, top_song, back_btn, random_btn,
                                     {"search": _search_rect(), "sort": _sort_rect()})
                if result == "random":
                    result = _random_pick(names)
                if result == "search":
                    typing = True
                    result = None
                elif result == "sort":
                    sort_i = (sort_i + 1) % len(SORTS)
                    rebuild(reset_top=False)
                    toast, toast_left = f"{t('Сортировка')}: {t(SORTS[sort_i][1])}", 1.5
                    result = None
                elif result == "dev":
                    dev_menu.run(clock)
                    all_names = songs.list_songs()
                    if not all_names:
                        return None
                    stats, colors = _refresh(all_names)
                    rebuild(reset_top=True)
                    result = None
                elif isinstance(result, tuple) and result[0] == "select":
                    sel_song = result[1]
                    top_song = result[2]
                    if result[3] and names:
                        open_song(sel_song)
                    result = None
                elif result == "back":
                    if query:
                        query = ""
                        rebuild(reset_top=True)
                        result = None
                    else:
                        return None
            else:
                if ev.type == pygame.KEYDOWN:
                    if keymap.hit("back", ev.key):
                        view = "list"
                        confirm_del = False
                        continue
                    if keymap.hit("up", ev.key):
                        sel_chart = max(0, sel_chart - 1)
                        confirm_del = False
                    elif keymap.hit("down", ev.key):
                        sel_chart = min(max(0, len(charts) - 1), sel_chart + 1)
                        confirm_del = False
                    elif keymap.hit("confirm", ev.key):
                        result = do_action("play")
                    elif keymap.hit("edit_chart", ev.key):
                        do_action("edit")
                    elif keymap.hit("new_chart", ev.key):
                        do_action("new")
                    elif keymap.hit("delete_chart", ev.key):
                        do_action("del")
                elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                    for action, btn in chart_btns:
                        if btn.rect.collidepoint(ev.pos):
                            result = do_action(action)
                            break
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

        if view == "list" and settings.get("preview") and names:
            target = names[sel_song]
            if target != preview_song:
                if preview_song is not None:
                    audio.stop_song()
                    preview_song = None
                if pending != target:
                    pending, pending_left = target, PREVIEW_DELAY
                pending_left -= dt
                if pending_left <= 0:
                    preview_song, pending = target, None
                    _play_preview(target)
                    preview_left = PREVIEW_MS / 1000.0
            else:
                preview_left -= dt
                if preview_left <= 0:
                    _play_preview(target)
                    preview_left = PREVIEW_MS / 1000.0
        elif preview_song is not None or pending is not None:
            audio.stop_song()
            preview_song, pending = None, None

        if view == "list":
            if frame % 30 == 1:
                stats, colors = _refresh(all_names)
                rebuild()
            sel_song = max(0, min(sel_song, max(0, len(names) - 1)))
            sel_entry = -1
            if names:
                sel_entry = next(i for i, (k, v) in enumerate(entries) if k == "song" and v == names[sel_song])
                if sel_entry < top_song:
                    top_song = sel_entry
                if sel_entry >= top_song + VISIBLE_SONGS:
                    top_song = sel_entry - VISIBLE_SONGS + 1
            top_song = max(0, min(top_song, max(0, len(entries) - VISIBLE_SONGS)))
            ui = {"query": query, "typing": typing, "sort": t(SORTS[sort_i][1]),
                  "found": len(names), "total": len(all_names), "toast": toast if toast_left > 0 else ""}
            _draw_list(entries, stats, colors, sel_entry, top_song,
                       _bg_color(names[sel_song], colors) if names else BLACK,
                       back_btn, random_btn, mouse, frame, ui)
        else:
            if sel_chart < top_chart:
                top_chart = sel_chart
            if sel_chart >= top_chart + VISIBLE_CHARTS:
                top_chart = sel_chart - VISIBLE_CHARTS + 1
            _draw_charts(song, song_dur, charts, sel_chart, top_chart, chart_btns,
                         mouse, frame, toast if toast_left > 0 else "", cover,
                         chart_ranks, stats.get(song, (0, 0, None))[2] if song else None)
        display.flip()


def _row_at(pos, top_y, row_h, visible, top, total):
    x, y = pos[0] / SS.SCALE, pos[1] / SS.SCALE
    if not (120 <= x <= SS.REF_W - 120) or y < top_y:
        return None
    i = int((y - top_y) // row_h)
    if i < 0 or i >= visible:
        return None
    idx = top + i
    return idx if idx < total else None


def _random_pick(names):
    pool = [ch for name in names for ch in songs.charts_for(name)]
    if not pool:
        return None
    return ("play", random.choice(pool))


def _list_event(ev, mouse, entries, names, sel, top, back_btn, random_btn, rects=None):
    if ev.type == pygame.KEYDOWN:
        k = ev.key
        if keymap.hit("back", k):
            return "back"
        if keymap.hit("random", k) and names:
            return "random"
        if keymap.hit("dev", k):
            return "dev"
        if keymap.hit("search", k):
            return "search"
        if keymap.hit("sort", k):
            return "sort"
        if not names:
            return None
        if keymap.hit("up", k):
            return ("select", max(0, sel - 1), top, False)
        if keymap.hit("down", k):
            return ("select", min(len(names) - 1, sel + 1), top, False)
        if keymap.hit("confirm", k):
            return ("select", sel, top, True)
    elif ev.type == pygame.MOUSEWHEEL:
        new_top = max(0, min(max(0, len(entries) - VISIBLE_SONGS), top - ev.y))
        return ("select", sel, new_top, False)
    elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
        if back_btn.rect.collidepoint(ev.pos):
            return "back"
        if random_btn.rect.collidepoint(ev.pos) and names:
            return "random"
        if rects:
            if rects["search"].collidepoint(ev.pos):
                return "search"
            if rects["sort"].collidepoint(ev.pos):
                return "sort"
        e = _row_at(ev.pos, 120, ROW_SONGS, VISIBLE_SONGS, top, len(entries))
        if e is not None and entries[e][0] == "song":
            return ("select", names.index(entries[e][1]), top, True)
    return None


def _tag(scr, right, y, text, fill, text_col, outline=None):
    """Тег в стиле VHS: плашка с тенью. Возвращает левую границу для следующего тега."""
    label = S.font(12, True).render(text, True, text_col)
    w, h = label.get_width() + SS.U(18), label.get_height() + SS.U(8)
    rect = pygame.Rect(right - w, y, w, h)
    if fill is not None:
        pygame.draw.rect(scr, (20, 16, 0), rect.move(SS.U(2), SS.U(2)), border_radius=SS.U(3))
        pygame.draw.rect(scr, fill, rect, border_radius=SS.U(3))
    if outline is not None:
        pygame.draw.rect(scr, outline, rect, SS.U(2), border_radius=SS.U(3))
    scr.blit(label, (rect.x + SS.U(9), rect.y + SS.U(4)))
    return rect.x - SS.U(8)


def _rank_badge(scr, right, y, grade, size):
    """Квадрат с буквой ранга справа. Возвращает левую границу для следующего тега."""
    if grade not in RANK_COL:
        return right
    col = RANK_COL[grade]
    rect = pygame.Rect(right - size, y, size, size)
    pygame.draw.rect(scr, (14, 14, 30), rect, border_radius=SS.U(5))
    pygame.draw.rect(scr, col, rect, SS.U(2), border_radius=SS.U(5))
    S.blit_text(scr, S.font(int(size / SS.SCALE * 0.62), True), grade, col, rect.centerx, rect.centery)
    return rect.x - SS.U(8)


def _draw_search(scr, ui, mouse):
    box = _search_rect()
    active = ui["typing"]
    pygame.draw.rect(scr, (14, 14, 30), box, border_radius=SS.U(6))
    pygame.draw.rect(scr, C.CYAN if active else C.DIM, box, SS.U(2), border_radius=SS.U(6))
    if ui["query"] or active:
        shown = ui["query"] + ("|" if active and (pygame.time.get_ticks() // 450) % 2 == 0 else "")
        txt = S.font(16, True).render(shown, True, C.WHITE)
        col = C.WHITE
    else:
        shown = f"{t('Поиск')}  [{keymap.label('search')}]"
        txt = S.font(15).render(shown, True, C.GREY)
        col = C.GREY
    clip = pygame.Rect(box.x + SS.U(10), box.y, box.w - SS.U(20), box.h)
    prev = scr.get_clip()
    scr.set_clip(clip)
    scr.blit(txt, (clip.x - max(0, txt.get_width() - clip.w), box.centery - txt.get_height() // 2))
    scr.set_clip(prev)
    box2 = _sort_rect()
    hov = box2.collidepoint(mouse)
    pygame.draw.rect(scr, (34, 34, 68) if hov else (14, 14, 30), box2, border_radius=SS.U(6))
    pygame.draw.rect(scr, C.GOLD if hov else C.DIM, box2, SS.U(2), border_radius=SS.U(6))
    label = f"{t('Сортировка')}: {ui['sort']}  [{keymap.label('sort')}]"
    S.blit_text(scr, S.fit(S.font(15, True), label, box2.w - SS.U(16)), label,
                C.WHITE if hov else (190, 190, 210), box2.centerx, box2.centery)


def _draw_list(entries, stats, colors, sel, top, bg, back_btn, random_btn, mouse, frame, ui=None):
    scr = pygame.display.get_surface()
    scr.fill(bg)
    S.draw_grid(scr, frame * 0.3, 0.0)
    S.glitch_title(scr, S.font(36, True), t("ПЕСНИ"), C.GOLD, C.WIDTH // 2, 60, frame)
    if ui is not None:
        _draw_search(scr, ui, mouse)
    area = pygame.Rect(SS.U(120), SS.U(100), C.WIDTH - SS.U(240), SS.U(VISIBLE_SONGS * ROW_SONGS + 20))
    S.panel(scr, area, C.GOLD, alpha=215)
    if not entries:
        S.blit_text(scr, S.font(18), t("Ничего не найдено"), C.GREY, area.centerx, area.centery)
    for i in range(VISIBLE_SONGS):
        e = top + i
        if e >= len(entries):
            break
        kind, val = entries[e]
        y = SS.U(110 + i * ROW_SONGS)
        row = pygame.Rect(SS.U(130), y, C.WIDTH - SS.U(260), SS.U(ROW_SONGS - 6))
        if kind == "head":
            author_col = C.GOLD
            if colors.get(val):                                 # фон автора тёмный: подпись берём светлее
                author_col = tuple(min(255, 150 + c * 2) for c in colors[val])
            label = val.upper() if val else t("БЕЗ АВТОРА")
            scr.blit(S.font(15, True).render(label, True, author_col), (row.x + SS.U(14), row.y + SS.U(12)))
            pygame.draw.line(scr, author_col, (row.x + SS.U(14), row.bottom - SS.U(4)),
                             (row.right - SS.U(14), row.bottom - SS.U(4)), SS.U(1))
            continue
        active = e == sel
        if active:
            pygame.draw.rect(scr, (34, 34, 68), row, border_radius=6)
            pygame.draw.rect(scr, C.CYAN, row, 2, border_radius=6)
        bar = colors.get(songs.author_of(val))
        if bar:
            pygame.draw.rect(scr, bar, pygame.Rect(row.x, row.y, SS.U(5), row.h), border_radius=3)
        count, state, *rest = stats.get(val, (0, 0, None))
        rank = rest[0] if rest else None
        col = C.WHITE if active else (190, 190, 210)
        scr.blit(S.font(18, True).render(songs.display_title(val), True, col), (row.x + SS.U(14), row.y + SS.U(4)))
        scr.blit(S.font(14).render(f"{t('чартов')}: {count}", True, C.GREY), (row.x + SS.U(14), row.y + SS.U(26)))
        right = row.right - SS.U(12)
        right = _rank_badge(scr, right, row.y + SS.U(5), rank, SS.U(34))
        if state >= 1:
            right = _tag(scr, right, row.y + SS.U(8), t("ПОБЕДА"), None, C.CYAN, outline=C.CYAN)
        if state == 2:
            _tag(scr, right, row.y + SS.U(8), "Beated", C.GOLD, (20, 16, 0))
    if ui is not None and ui["toast"]:
        S.blit_text(scr, S.font(14, True), ui["toast"], C.GOLD, C.WIDTH // 2, SS.U(500))
    elif ui is not None and ui["query"]:
        S.blit_text(scr, S.font(14), f"{t('Найдено')}: {ui['found']} {t('из')} {ui['total']}", C.GREY,
                    C.WIDTH // 2, SS.U(500))
    else:
        S.blit_text(scr, S.font(14), t("Песни — файлы .ogg/.mp3/.wav в папке songs/"), C.GREY,
                    C.WIDTH // 2, SS.U(500))
    back_btn.draw(scr, mouse)
    random_btn.draw(scr, mouse)
    S.post_fx(scr, frame, grain=40)


def _draw_charts(song, dur, charts, sel, top, chart_btns, mouse, frame, toast, cover=None,
                 chart_ranks=None, song_rank=None):
    scr = pygame.display.get_surface()
    scr.fill((0, 0, 0))
    if cover is not None:
        cover.set_alpha(90)
        scr.blit(cover, (0, 0))
    S.draw_grid(scr, frame * 0.3, 0.0)
    S.glitch_title(scr, S.font(30, True), songs.display_title(song), C.GOLD, C.WIDTH // 2, SS.U(46), frame)
    if song_rank in RANK_COL:
        S.blit_text(scr, S.font(14, True), f"{t('РАНГ ПЕСНИ')}: {song_rank}", RANK_COL[song_rank],
                    C.WIDTH // 2, SS.U(80))
    area = pygame.Rect(SS.U(90), SS.U(96), C.WIDTH - SS.U(180), SS.U(VISIBLE_CHARTS * ROW_CHARTS + 20))
    S.panel(scr, area, C.CYAN, alpha=165 if cover is not None else 215)
    if not charts:
        S.blit_text(scr, S.font(18), t("чартов пока нет — нажмите НОВЫЙ"), C.GREY,
                    C.WIDTH // 2, area.centery)
    for i in range(VISIBLE_CHARTS):
        idx = top + i
        if idx >= len(charts):
            break
        ch = charts[idx]
        y = SS.U(106 + i * ROW_CHARTS)
        row = pygame.Rect(SS.U(104), y, C.WIDTH - SS.U(208), SS.U(ROW_CHARTS - 6))
        active = idx == sel
        if active:
            pygame.draw.rect(scr, (34, 34, 68), row, border_radius=6)
            pygame.draw.rect(scr, C.CYAN, row, 2, border_radius=6)
        col = C.WHITE if active else (190, 190, 210)
        name_surf = S.font(16, True).render(ch.name, True, col)
        scr.blit(name_surf, (row.x + SS.U(14), row.y + SS.U(2)))
        sx = row.x + SS.U(14) + name_surf.get_width() + SS.U(14)
        for k in range(5):
            S.draw_star(scr, sx + k * SS.U(16) + SS.U(6), row.y + SS.U(12), SS.U(6), C.GOLD if k < ch.difficulty else C.DIM,
                        filled=k < ch.difficulty)
        right = row.right - SS.U(12)
        grade = chart_ranks[idx] if chart_ranks and idx < len(chart_ranks) else None
        right = _rank_badge(scr, right, row.y + SS.U(4), grade, SS.U(30))
        if songs.is_won(ch):
            _tag(scr, right, row.y + SS.U(8), t("ПОБЕДА"), None, C.CYAN, outline=C.CYAN)
        density = len(ch.notes) / max(1, dur / 1000.0)
        sub = f"{t('нот')}: {len(ch.notes)}   {t('плотность')}: {density:.2f}/{t('с')}"
        if ch.charter:
            sub = f"{t('чарт')}: {ch.charter}   " + sub
        scr.blit(S.font(13).render(sub, True, C.GREY), (row.x + SS.U(14), row.y + SS.U(21)))
    for action, btn in chart_btns:
        btn.draw(scr, mouse, active=False)
    if toast:
        S.blit_text(scr, S.font(14, True), toast, C.GOLD, C.WIDTH // 2, SS.U(520))
    S.post_fx(scr, frame, grain=40)


def _empty_screen(clock):
    back = S.Btn((C.WIDTH // 2 - SS.U(70), SS.U(380), SS.U(140), SS.U(40)), t("НАЗАД"), C.PURPLE_LIGHT, S.font(16, True))
    frame = 0
    while True:
        display.tick(clock)
        frame += 1
        mouse = pygame.mouse.get_pos()
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if ev.type == pygame.KEYDOWN and (keymap.hit("back", ev.key) or keymap.hit("confirm", ev.key)):
                return None
            if ev.type == pygame.MOUSEBUTTONDOWN and back.hovered(ev.pos):
                return None
        scr = pygame.display.get_surface()
        scr.fill((0, 0, 0))
        S.glitch_title(scr, S.font(30, True), t("ПЕСНИ"), C.GOLD, C.WIDTH // 2, SS.U(200), frame)
        S.blit_text(scr, S.font(18), t("Положите .ogg / .mp3 / .wav в папку songs/"), C.GREY,
                    C.WIDTH // 2, SS.U(260))
        back.draw(scr, mouse)
        S.post_fx(scr, frame, grain=40)
        display.flip()
