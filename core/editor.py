
#-- Импорт
import sys
import time

import pygame

import audio
import autochart
import cache
import config as C
import events
import events_screen
import settings
import songs
import style as S
from chart import Note

SNAPS = (10, 25, 50, 100, 200)
ZOOMS = (0.25, 0.35, 0.5, 0.7, 1.0)
UNDO_LIMIT = 80
MAX_HOLD = 10000
REC_HOLD_MS = 300
HIT_Y = C.HIT_Y


def fmt_time(ms):
    ms = max(0, int(ms))
    return f"{ms // 60000}:{(ms // 1000) % 60:02d}.{ms % 1000:03d}"


class Editor:
    def __init__(self, clock, chart):
        self.clock = clock
        self.chart = chart
        self.song_path = songs.song_path(chart.song)
        info = songs.info(chart.song)
        self.duration = int(info.get("duration_ms") or (chart.notes[-1].t + 5000 if chart.notes else 60000))
        self.energy = info.get("energy") or []
        self.energy_fps = float(info.get("energy_fps") or 21.5)
        self.keys = settings.lane_keys()
        self.key_names = settings.get("lane_keys")

        self.sclk = audio.SongClock()
        self.cursor = 0.0
        self.playing = False
        self.snap_i = 2
        self.zoom_i = 2
        self.dirty = chart.path is None
        self.undo = []
        self.rec = [None] * 4
        self._wheel_last = 0.0
        self.flash = [0.0] * 4
        self.toast_text = ""
        self.toast_left = 0.0
        self.confirm_exit = False
        self.name_edit = False
        self.name_buf = chart.name
        self.menu_open = False
        self.menu_sel = 0
        self.frame = 0
        self.veil = pygame.Surface((C.WIDTH, C.HEIGHT), pygame.SRCALPHA)
        self.veil.fill((0, 0, 0, 185))
        self._build_menu()

    #-- Состояние и вспомогательные функции

    @property
    def zoom(self):
        return ZOOMS[self.zoom_i]

    @property
    def snap(self):
        return SNAPS[self.snap_i]

    def time_to_y(self, t):
        return HIT_Y - (t - self.cursor) * self.zoom

    def y_to_time(self, y):
        return self.cursor + (HIT_Y - y) / self.zoom

    def snapped(self, t):
        return round(t / self.snap) * self.snap

    def _toast(self, text, sec=2.5):
        self.toast_text = text
        self.toast_left = sec

    def _push_undo(self):
        self.undo.append([(n.t, n.lane, n.dur) for n in self.chart.notes])
        if len(self.undo) > UNDO_LIMIT:
            self.undo.pop(0)
        self.dirty = True

    def _set_notes(self, items):
        self.chart.notes = [Note(*item) for item in items]
        self.chart.sort()

    def add_note(self, t, lane, dur=0):
        t = max(0, int(round(t)))
        for n in self.chart.notes:
            if n.lane == lane and abs(n.t - t) < 40:
                return None
        self._push_undo()
        note = Note(t, lane, dur)
        self.chart.notes.append(note)
        self.chart.sort()
        self.flash[lane] = 1.0
        return note

    def nearest(self, t, lane=None, limit=250):
        best = None
        for n in self.chart.notes:
            if lane is not None and n.lane != lane:
                continue
            d = abs(n.t - t)
            if d <= limit and (best is None or d < abs(best.t - t)):
                best = n
        return best

    def delete_note(self, n):
        self._push_undo()
        self.chart.notes.remove(n)

    def _seek(self, ms):
        self.cursor = max(0.0, min(float(self.duration), ms))
        if self.playing:
            audio.play_song(self.song_path, self.cursor)
            self.sclk.start(self.cursor)

    def _toggle_play(self):
        if self.playing:
            self._stop_play()
        else:
            audio.play_song(self.song_path, self.cursor)
            self.sclk.start(self.cursor)
            self.playing = True

    def _stop_play(self):
        if self.playing:
            self.cursor = max(0.0, min(float(self.duration), self.sclk.now()))
            audio.stop_song()
            self.playing = False
        self.rec = [None] * 4

    def _record_release(self, lane):
        n = self.rec[lane]
        self.rec[lane] = None
        if n is None or not self.playing:
            return
        length = int(round(self.sclk.now() - n.t))
        if length >= REC_HOLD_MS and n in self.chart.notes:
            n.dur = length

    def _save(self):
        if not self.chart.name.strip():
            self.chart.name = "Чарт"
        songs.save_chart(self.chart)
        self.dirty = False
        self.confirm_exit = False
        self._toast("Сохранено")

    def _auto(self):
        if not autochart.AVAILABLE:
            self._toast("Авто-разметка недоступна: установите numpy")
            return
        self._toast("Анализ песни…", 60)
        self._draw((0, 0))
        pygame.display.flip()
        res = autochart.build(self.song_path)
        if res is None:
            self._toast("Не удалось проанализировать песню")
            return
        self._push_undo()
        self._set_notes(res["notes"])
        self._toast(f"Авто-разметка: нот {len(res['notes'])}")

    def _shift(self, ms):
        self._push_undo()
        for n in self.chart.notes:
            n.t = max(0, n.t + ms)
        self.chart.sort()
        self._toast(f"Сдвиг всех нот: {ms:+d} мс")

    def _undo(self):
        if not self.undo:
            self._toast("Нечего отменять")
            return
        self._set_notes(self.undo.pop())
        self._toast("Отмена")

    #-- Меню

    def _build_menu(self):
        labels = [("continue", "ПРОДОЛЖИТЬ"), ("save", "СОХРАНИТЬ"),
                  ("save_exit", "СОХРАНИТЬ И ВЫЙТИ"), ("events", "СОБЫТИЯ (ГЛЮК, ВСПЫШКА, КАРТИНКИ)"),
                  ("auto", "АВТО-РАЗМЕТКА (ЗАМЕНИТ НОТЫ)"),
                  ("exit", "ВЫЙТИ БЕЗ СОХРАНЕНИЯ")]
        self.menu_items = labels
        self.menu_btns = [S.Btn((C.WIDTH // 2 - 170, 176 + i * 52, 340, 42), text, C.CYAN,
                                S.font(16, True)) for i, (_, text) in enumerate(labels)]

    def _menu_action(self, action):
        if action == "continue":
            self.menu_open = False
        elif action == "save":
            self._save()
        elif action == "save_exit":
            self._save()
            return "back"
        elif action == "events":
            self.menu_open = False
            events_screen.run(self.clock, self.chart, self.cursor, self.duration)
            self.dirty = True
        elif action == "auto":
            self.menu_open = False
            self._auto()
        elif action == "exit":
            if self.dirty and not self.confirm_exit:
                self.confirm_exit = True
                self._toast("Есть несохранённые изменения. Нажмите ещё раз, чтобы выйти.", 4)
            else:
                return "back"
        return None

    #-- Цикл

    def run(self):
        while True:
            dt = min(0.05, self.clock.tick(C.FPS) / 1000.0)
            mouse = pygame.mouse.get_pos()
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    self._stop_play()
                    pygame.quit()
                    sys.exit()
                res = self._event(ev, mouse)
                if res is not None:
                    self._stop_play()
                    return res
            self._tick(dt)
            self._draw(mouse)
            pygame.display.flip()
            self.frame += 1

    def _tick(self, dt):
        if self.playing:
            self.cursor = self.sclk.now()
            if self.cursor >= self.duration:
                self._stop_play()
        for i in range(4):
            self.flash[i] = max(0.0, self.flash[i] - dt * 5)
        if self.toast_left > 0:
            self.toast_left -= dt

    #-- События

    def _event(self, ev, mouse):
        if ev.type == pygame.KEYDOWN:
            return self._key(ev)
        if ev.type == pygame.KEYUP and not self.menu_open and not self.name_edit:
            if ev.key in self.keys:
                self._record_release(self.keys.index(ev.key))
            return None
        if ev.type == pygame.MOUSEBUTTONDOWN:
            if self.menu_open:
                if ev.button == 1:
                    for (action, _), btn in zip(self.menu_items, self.menu_btns):
                        if btn.rect.collidepoint(ev.pos):
                            return self._menu_action(action)
                return None
            return self._click(ev)
        if ev.type == pygame.MOUSEWHEEL and not self.menu_open:
            if self._wheel_note(ev.y):
                return None
            self._seek(self.cursor - ev.y * self.snap * (3 if pygame.key.get_mods() & pygame.KMOD_SHIFT else 1))
        return None

    def _note_under_mouse(self):
        mx, my = pygame.mouse.get_pos()
        rel = mx - C.FIELD_X
        if rel < 0 or rel >= C.FIELD_W:
            return None
        lane = rel // (C.LANE_W + C.LANE_GAP)
        if rel - lane * (C.LANE_W + C.LANE_GAP) >= C.LANE_W:
            return None
        best = None
        for n in self.chart.notes:
            if n.lane != lane:
                continue
            y_head, y_tail = self.time_to_y(n.t), self.time_to_y(n.end)
            if min(y_head, y_tail) - 12 <= my <= max(y_head, y_tail) + 12:
                d = abs(y_head - my)
                if best is None or d < best[0]:
                    best = (d, n)
        return best[1] if best else None

    def _wheel_note(self, direction):
        n = self._note_under_mouse()
        if n is None:
            return False
        now = time.perf_counter()
        if now - self._wheel_last > 0.6:
            self._push_undo()
        self._wheel_last = now
        if n.dur == 0 and direction > 0:
            new = REC_HOLD_MS
        else:
            new = n.dur + direction * max(50, self.snap)
            if new < REC_HOLD_MS:
                new = 0
        n.dur = int(max(0, min(MAX_HOLD, new)))
        self._toast(f"Удержание: {n.dur} мс" if n.dur else "Обычная нота", 1.0)
        return True

    def _key(self, ev):
        k = ev.key
        mods = pygame.key.get_mods()
        ctrl = mods & pygame.KMOD_CTRL

        if self.name_edit:
            if k in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_ESCAPE, pygame.K_F2):
                self.chart.name = (self.name_buf.strip() or "Чарт")[:24]
                self.name_edit = False
                self.dirty = True
            elif k == pygame.K_BACKSPACE:
                self.name_buf = self.name_buf[:-1]
            elif ev.unicode and ev.unicode.isprintable() and len(self.name_buf) < 24:
                self.name_buf += ev.unicode
            return None

        if self.menu_open:
            if k == pygame.K_ESCAPE:
                self.menu_open = False
            elif k in (pygame.K_UP, pygame.K_w):
                self.menu_sel = (self.menu_sel - 1) % len(self.menu_items)
            elif k in (pygame.K_DOWN, pygame.K_s):
                self.menu_sel = (self.menu_sel + 1) % len(self.menu_items)
            elif k in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                return self._menu_action(self.menu_items[self.menu_sel][0])
            return None

        if k == pygame.K_ESCAPE:
            self.menu_open = True
            self.menu_sel = 0
            self.confirm_exit = False
            return None
        if ctrl and k == pygame.K_s:
            self._save()
            return None
        if ctrl and k == pygame.K_z:
            self._undo()
            return None
        if k == pygame.K_SPACE:
            self._toggle_play()
            return None
        if k == pygame.K_LEFT:
            self._seek(self.cursor - (1000 if mods & pygame.KMOD_SHIFT else self.snap))
        elif k == pygame.K_RIGHT:
            self._seek(self.cursor + (1000 if mods & pygame.KMOD_SHIFT else self.snap))
        elif k == pygame.K_UP:
            self.zoom_i = min(len(ZOOMS) - 1, self.zoom_i + 1)
        elif k == pygame.K_DOWN:
            self.zoom_i = max(0, self.zoom_i - 1)
        elif k == pygame.K_g:
            self.snap_i = (self.snap_i + 1) % len(SNAPS)
            self._toast(f"Сетка: {self.snap} мс")
        elif k == pygame.K_LEFTBRACKET:
            self._shift(-10)
        elif k == pygame.K_RIGHTBRACKET:
            self._shift(10)
        elif k == pygame.K_F2:
            self.name_edit = True
            self.name_buf = self.chart.name
        elif k in (pygame.K_DELETE, pygame.K_BACKSPACE):
            ref = self.sclk.now() if self.playing else self.cursor
            n = self.nearest(ref, limit=200)
            if n is not None:
                self.delete_note(n)
                self._toast("Нота удалена")
        elif k in self.keys:
            lane = self.keys.index(k)
            if self.playing:
                self.rec[lane] = self.add_note(self.sclk.now(), lane)
            else:
                self.add_note(self.snapped(self.cursor), lane)
        return None

    def _click(self, ev):
        x, y = ev.pos
        if y < 8:
            self._seek(x / C.WIDTH * self.duration)
            return None
        if not (C.FIELD_X <= x < C.FIELD_X + C.FIELD_W) or y < 0 or y > C.HEIGHT - 60:
            return None
        lane = (x - C.FIELD_X) // (C.LANE_W + C.LANE_GAP)
        if lane < 0 or lane > 3:
            return None
        t = self.y_to_time(y)
        if ev.button == 1:
            self.add_note(t if self.playing else self.snapped(t), lane)
        elif ev.button == 3:
            n = self.nearest(t, lane=lane, limit=max(120, 2 * self.snap))
            if n is not None:
                self.delete_note(n)
                self._toast("Нота удалена")
        return None

    #-- Отрисовка

    def _lane_x(self, lane):
        return C.FIELD_X + lane * (C.LANE_W + C.LANE_GAP) + C.LANE_W // 2

    def _draw(self, mouse):
        scr = pygame.display.get_surface()
        scr.fill(events.bg_at(self.chart.events, self.cursor))
        S.draw_grid(scr, (self.cursor * 0.04) % 60, 0.0)

        for i in range(4):
            x = C.FIELD_X + i * (C.LANE_W + C.LANE_GAP)
            col = C.LANE_COLORS[i]
            band = cache.band(i)
            band.set_alpha(int(12 + 50 * self.flash[i]))
            scr.blit(band, (x, 0))
            pygame.draw.line(scr, S_mix(C.GRID_COL, col, 0.35), (x, 0), (x, C.HEIGHT), 1)
            pygame.draw.line(scr, S_mix(C.GRID_COL, col, 0.35), (x + C.LANE_W, 0),
                             (x + C.LANE_W, C.HEIGHT), 1)

        t_top = self.y_to_time(0)
        t_bot = self.y_to_time(C.HEIGHT)
        for sec in range(max(0, int(t_bot // 1000)), int(t_top // 1000) + 2):
            y = self.time_to_y(sec * 1000)
            pygame.draw.line(scr, (38, 38, 70), (C.FIELD_X - 30, y), (C.FIELD_X + C.FIELD_W + 30, y), 1)
            S.blit_text(scr, S.font(14), fmt_time(sec * 1000)[:-4], (90, 90, 130), 24, y, 255)

        pygame.draw.line(scr, C.WHITE, (C.FIELD_X, HIT_Y), (C.FIELD_X + C.FIELD_W, HIT_Y), 2)
        for i in range(4):
            x = C.FIELD_X + i * (C.LANE_W + C.LANE_GAP)
            pad = pygame.Rect(x + 4, HIT_Y - 22, C.LANE_W - 8, 44)
            pygame.draw.rect(scr, S_mix(C.BG_DARK, C.LANE_COLORS[i], 0.2 + 0.5 * self.flash[i]),
                             pad, border_radius=8)
            pygame.draw.rect(scr, S_mix(C.DIM, C.LANE_COLORS[i], 0.6), pad, 2, border_radius=8)
            label = cache.text(16, True, settings.key_label(self.key_names[i]), C.LANE_COLORS[i])
            scr.blit(label, (self._lane_x(i) - label.get_width() // 2, HIT_Y + 34))

        for n in self.chart.notes:
            y = self.time_to_y(n.t)
            if n.dur > 0:
                tail = self.time_to_y(n.end)
                if tail < C.HEIGHT + 40 and y > -40:
                    self._draw_body(scr, n.lane, y, tail)
            if y < -40 or y > C.HEIGHT + 40:
                continue
            sprite = cache.note(n.lane, 1.0)
            scr.blit(sprite, (self._lane_x(n.lane) - sprite.get_width() // 2,
                              y - sprite.get_height() // 2))

        self._draw_events(scr)
        self._draw_overview(scr)
        self._draw_hud(scr)
        if self.toast_left > 0 and self.toast_text:
            alpha = 255 * min(1.0, self.toast_left / 0.6)
            S.blit_text(scr, S.font(16, True), self.toast_text, C.GOLD, C.WIDTH // 2, 78, alpha)

        if self.name_edit:
            box = pygame.Rect(C.WIDTH // 2 - 170, 300, 340, 56)
            S.panel(scr, box, C.CYAN, alpha=230)
            S.blit_text(scr, S.font(14, True), "НАЗВАНИЕ ЧАРТА — ENTER", C.CYAN, C.WIDTH // 2, 290)
            shown = self.name_buf + ("|" if (self.frame // 30) % 2 == 0 else " ")
            S.blit_text(scr, S.font(20, True), shown, C.WHITE, C.WIDTH // 2, 328)

        if self.menu_open:
            scr.blit(self.veil, (0, 0))
            S.glitch_title(scr, S.font(36, True), "РЕДАКТОР", C.CYAN, C.WIDTH // 2, 110, 60)
            for i, btn in enumerate(self.menu_btns):
                disabled = self.menu_items[i][0] == "auto" and not autochart.AVAILABLE
                btn.color = C.DIM if disabled else C.CYAN
                btn.draw(scr, mouse, active=(i == self.menu_sel))
            S.blit_text(scr, S.font(14), "ESC — закрыть меню", C.GREY, C.WIDTH // 2, 500)

        S.post_fx(scr, self.frame, grain=20)

    def _draw_body(self, scr, lane, y_head, y_tail):
        top, bot = max(-10, min(y_head, y_tail)), min(C.HEIGHT + 10, max(y_head, y_tail))
        if bot - top <= 0:
            return
        w = int(C.LANE_W * 0.42)
        x = self._lane_x(lane) - w // 2
        col = C.LANE_COLORS[lane]
        pygame.draw.rect(scr, S_mix(C.BG_DARK, col, 0.45), (x, top, w, bot - top), border_radius=6)
        pygame.draw.rect(scr, S_mix(C.BG_DARK, col, 0.7), (x, top, w, bot - top), 2, border_radius=6)

    def _draw_events(self, scr):
        if self.playing:
            return
        grey, line_col, edge = (150, 150, 165), (80, 80, 92), (220, 220, 230)
        x = C.FIELD_X + C.FIELD_W + 36
        for ev in self.chart.events:
            y = self.time_to_y(ev["t"])
            y_end = self.time_to_y(ev["t"] + events.total_ms(ev))
            lo, hi = min(y, y_end), max(y, y_end)
            if hi < -20 or lo > C.HEIGHT + 20:
                continue
            top, bot = max(0, lo), min(C.HEIGHT, hi)
            if bot > top:
                pygame.draw.line(scr, line_col, (x, top), (x, bot), 3)
            if 0 <= y <= C.HEIGHT:
                pts = [(x, y - 8), (x + 8, y), (x, y + 8), (x - 8, y)]
                pygame.draw.polygon(scr, grey, pts)
                pygame.draw.polygon(scr, edge, pts, 1)
                label = cache.text(12, True, events.TYPE_NAMES[ev["type"]], grey)
                scr.blit(label, (x + 14, y - label.get_height() // 2))

    def _draw_overview(self, scr):
        pygame.draw.rect(scr, (30, 30, 50), (0, 0, C.WIDTH, 6))
        prog = self.cursor / max(1, self.duration)
        pygame.draw.rect(scr, C.CYAN, (0, 0, int(C.WIDTH * prog), 6))
        for n in self.chart.notes:
            x = int(n.t / max(1, self.duration) * C.WIDTH)
            pygame.draw.line(scr, C.LANE_COLORS[n.lane], (x, 0), (x, 6), 1)
        if not self.playing:
            for ev in self.chart.events:
                x = int(ev["t"] / max(1, self.duration) * C.WIDTH)
                pygame.draw.rect(scr, events.TYPE_COLORS[ev["type"]], (x - 1, 7, 3, 6))

    def _draw_hud(self, scr):
        status = "▶" if self.playing else "❚❚"
        left = f"{status}  {fmt_time(self.cursor)} / {fmt_time(self.duration)}"
        scr.blit(S.font(16, True).render(left, True, C.WHITE), (14, 16))
        name = f"{songs.title(self.chart.song)} — {self.chart.name}" + ("  *" if self.dirty else "")
        scr.blit(S.font(14).render(name, True, C.GREY), (14, 40))
        info = f"нот: {len(self.chart.notes)}   сетка: {self.snap} мс   масштаб: {self.zoom:.2f}"
        t = S.font(14).render(info, True, C.GREY)
        scr.blit(t, (C.WIDTH - t.get_width() - 14, 16))
        hint = "SPACE играть · ←→ курсор · G сетка · [ ] сдвиг · Del удалить · Ctrl+S сохранить · ESC меню"
        h = S.font(14).render(hint, True, (110, 110, 150))
        scr.blit(h, (C.WIDTH // 2 - h.get_width() // 2, C.HEIGHT - 22))


def S_mix(a, b, k):
    return tuple(int(a[i] + (b[i] - a[i]) * k) for i in range(3))
