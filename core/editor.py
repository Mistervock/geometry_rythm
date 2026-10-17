
#-- Импорт
import sys
import time

import pygame

import audio
import autochart
import cache
import config as C
import display
import events
import events_screen
import settings
import song_settings
import songs
import stretch
import style as S
from chart import Note
from i18n import t

SNAPS = (10, 25, 50, 100, 200)
ZOOMS = (0.25, 0.35, 0.5, 0.7, 1.0)
SPEEDS = (0.5, 0.75, 1.0, 1.25)
BAR_H = 12
PANEL_X = 940
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
        self.white = pygame.Surface((C.WIDTH, C.HEIGHT))
        self.white.fill(C.WHITE)
        self.fx_on = True
        self.veil.fill((0, 0, 0, 185))
        self.speed_i = SPEEDS.index(1.0)
        self.drag = False
        self.events_btn = S.Btn((PANEL_X, 110, 150, 40), t("СОБЫТИЯ"), C.CYAN, S.font(14, True))
        self.speed_btns = [S.Btn((PANEL_X, 186 + i * 40, 150, 34), f"{v:g}×", C.GOLD, S.font(14, True))
                           for i, v in enumerate(SPEEDS)]
        self._build_menu()

    #-- Состояние и вспомогательные функции

    @property
    def zoom(self):
        return ZOOMS[self.zoom_i]

    @property
    def snap(self):
        return SNAPS[self.snap_i]

    @property
    def speed(self):
        return SPEEDS[self.speed_i]

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

    def _now(self):
        return self.sclk.now() * self.speed

    def _audio_path(self):
        path = stretch.ensure(self.song_path, self.speed)
        if path is None:
            self.speed_i = SPEEDS.index(1.0)
            self._toast(t("Замедление недоступно: установите numpy"))
            return self.song_path
        return path

    def _start_audio(self, ms):
        at = ms / self.speed
        audio.play_song(self._audio_path(), at)
        self.sclk.start(at)

    def _seek(self, ms):
        self.cursor = max(0.0, min(float(self.duration), ms))
        if self.playing:
            self._start_audio(self.cursor)

    def _set_speed(self, i):
        if i == self.speed_i:
            return
        self.speed_i = i
        if self.speed != 1.0:
            self._toast(t("Готовлю замедление…") if self.speed < 1 else t("Готовлю ускорение…"), 60)
            self._draw((0, 0))
            pygame.display.flip()
        self._audio_path()
        if self.playing:
            self._start_audio(self.cursor)
        self._toast(f"{t('Скорость')}: {self.speed:g}×")

    def _toggle_play(self):
        if self.playing:
            self._stop_play()
        else:
            self._start_audio(self.cursor)
            self.playing = True

    def _stop_play(self):
        if self.playing:
            self.cursor = max(0.0, min(float(self.duration), self._now()))
            audio.stop_song()
            self.playing = False
        self.rec = [None] * 4

    def _record_release(self, lane):
        n = self.rec[lane]
        self.rec[lane] = None
        if n is None or not self.playing:
            return
        length = int(round(self._now() - n.t))
        if length >= REC_HOLD_MS and n in self.chart.notes:
            n.dur = length

    def _save(self):
        if not self.chart.name.strip():
            self.chart.name = "Чарт"
        songs.save_chart(self.chart)
        self.dirty = False
        self.confirm_exit = False
        self._toast(t("Сохранено"))

    def _auto(self):
        if not autochart.AVAILABLE:
            self._toast(t("Авто-разметка недоступна: установите numpy"))
            return
        self._toast(t("Анализ песни…"), 60)
        self._draw((0, 0))
        pygame.display.flip()
        res = autochart.build(self.song_path)
        if res is None:
            self._toast(t("Не удалось проанализировать песню"))
            return
        self._push_undo()
        self._set_notes(res["notes"])
        self._toast(f"{t('Авто-разметка')}: {t('нот')} {len(res['notes'])}")

    def _shift(self, ms):
        self._push_undo()
        for n in self.chart.notes:
            n.t = max(0, n.t + ms)
        self.chart.sort()
        self._toast(f"{t('Сдвиг всех нот')}: {ms:+d} {t('мс')}")

    def _undo(self):
        if not self.undo:
            self._toast(t("Нечего отменять"))
            return
        self._set_notes(self.undo.pop())
        self._toast(t("Отмена"))

    #-- Меню

    def _build_menu(self):
        labels = [("continue", t("ПРОДОЛЖИТЬ")), ("save", t("СОХРАНИТЬ")),
                  ("save_exit", t("СОХРАНИТЬ И ВЫЙТИ")),
                  ("song", t("НАСТРОЙКИ ПЕСНИ")),
                  ("auto", t("АВТО-РАЗМЕТКА (ЗАМЕНИТ НОТЫ)")),
                  ("exit", t("ВЫЙТИ БЕЗ СОХРАНЕНИЯ"))]
        self.menu_items = labels
        self.menu_btns = [S.Btn((C.WIDTH // 2 - 210, 176 + i * 62, 420, 50), text, C.CYAN,
                                S.font(16, True)) for i, (_, text) in enumerate(labels)]

    def _menu_action(self, action):
        if action == "continue":
            self.menu_open = False
        elif action == "save":
            self._save()
        elif action == "save_exit":
            self._save()
            return "back"
        elif action == "song":
            self.menu_open = False
            if song_settings.run(self.clock, self.chart):
                self.dirty = True
                self._toast(t("Настройки песни изменены — не забудьте сохранить"), 3)
        elif action == "auto":
            self.menu_open = False
            self._auto()
        elif action == "exit":
            if self.dirty and not self.confirm_exit:
                self.confirm_exit = True
                self._toast(t("Есть несохранённые изменения. Нажмите ещё раз, чтобы выйти."), 4)
            else:
                return "back"
        return None

    #-- Цикл

    def run(self):
        while True:
            dt = min(0.05, display.tick(self.clock) / 1000.0)
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
            self.cursor = self._now()
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
        if ev.type == pygame.MOUSEBUTTONUP and ev.button == 1:
            self.drag = False
            return None
        if ev.type == pygame.MOUSEMOTION and self.drag and not self.menu_open:
            self._seek(ev.pos[0] / C.WIDTH * self.duration)
            return None
        if ev.type == pygame.MOUSEWHEEL and not self.menu_open:
            if pygame.key.get_mods() & pygame.KMOD_CTRL:
                self.zoom_i = max(0, min(len(ZOOMS) - 1, self.zoom_i + ev.y))
                return None
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
        self._toast(f"{t('Удержание')}: {n.dur} {t('мс')}" if n.dur else t("Обычная нота"), 1.0)
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
        elif k == pygame.K_HOME:
            self._seek(0)
        elif k == pygame.K_END:
            self._seek(self.duration)
        elif k == pygame.K_PAGEUP:
            self._seek(self.cursor - (30000 if mods & pygame.KMOD_SHIFT else 5000))
        elif k == pygame.K_PAGEDOWN:
            self._seek(self.cursor + (30000 if mods & pygame.KMOD_SHIFT else 5000))
        elif k in (pygame.K_MINUS, pygame.K_KP_MINUS):
            self._set_speed(max(0, self.speed_i - 1))
        elif k in (pygame.K_EQUALS, pygame.K_KP_PLUS):
            self._set_speed(min(len(SPEEDS) - 1, self.speed_i + 1))
        elif k == pygame.K_v:
            self.fx_on = not self.fx_on
            self._toast(t("Эффекты событий в редакторе: ") + (t("ВКЛ") if self.fx_on else t("ВЫКЛ")))
        elif k == pygame.K_g:
            self.snap_i = (self.snap_i + 1) % len(SNAPS)
            self._toast(f"{t('Сетка')}: {self.snap} {t('мс')}")
        elif k == pygame.K_LEFTBRACKET:
            self._shift(-10)
        elif k == pygame.K_RIGHTBRACKET:
            self._shift(10)
        elif k == pygame.K_F2:
            self.name_edit = True
            self.name_buf = self.chart.name
        elif k in (pygame.K_DELETE, pygame.K_BACKSPACE):
            ref = self._now() if self.playing else self.cursor
            n = self.nearest(ref, limit=200)
            if n is not None:
                self.delete_note(n)
                self._toast(t("Нота удалена"))
        elif k in self.keys:
            lane = self.keys.index(k)
            if self.playing:
                self.rec[lane] = self.add_note(self._now(), lane)
            else:
                self.add_note(self.snapped(self.cursor), lane)
        return None

    def _click(self, ev):
        x, y = ev.pos
        if y < BAR_H + 2:
            self.drag = True
            self._seek(x / C.WIDTH * self.duration)
            return None
        if x >= PANEL_X:
            if self.events_btn.rect.collidepoint(ev.pos):
                events_screen.run(self.clock, self.chart, self.cursor, self.duration)
                self.dirty = True
                return None
            for i, btn in enumerate(self.speed_btns):
                if btn.rect.collidepoint(ev.pos):
                    self._set_speed(i)
                    return None
            return None
        if not (C.FIELD_X <= x < C.FIELD_X + C.FIELD_W) or y < 0 or y > C.HEIGHT - 60:
            return None
        lane = (x - C.FIELD_X) // (C.LANE_W + C.LANE_GAP)
        if lane < 0 or lane > 3:
            return None
        tm = self.y_to_time(y)
        if ev.button == 1:
            self.add_note(tm if self.playing else self.snapped(tm), lane)
        elif ev.button == 3:
            n = self.nearest(tm, lane=lane, limit=max(120, 2 * self.snap))
            if n is not None:
                self.delete_note(n)
                self._toast(t("Нота удалена"))
        return None

    #-- Отрисовка

    def _lane_x(self, lane):
        return C.FIELD_X + lane * (C.LANE_W + C.LANE_GAP) + C.LANE_W // 2

    def _draw(self, mouse):
        scr = pygame.display.get_surface()
        scr.fill(events.bg_at(self.chart.events, self.cursor))
        S.draw_grid(scr, (self.cursor * 0.04) % 60, 0.0)
        glitch_lvl, flash_lvl, images = events.active_fx(self.chart.events, self.cursor) \
            if self.fx_on else (0.0, 0.0, [])
        events.draw_images(scr, images)

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

        self._draw_heals(scr)
        self._draw_events(scr)
        self._draw_overview(scr)
        self._draw_panel(scr, mouse)
        self._draw_hud(scr)
        if self.toast_left > 0 and self.toast_text:
            alpha = 255 * min(1.0, self.toast_left / 0.6)
            S.blit_text(scr, S.font(16, True), self.toast_text, C.GOLD, C.WIDTH // 2, 78, alpha)

        if glitch_lvl > 0:
            S.glitch(scr, strength=glitch_lvl)
        if flash_lvl > 0:
            self.white.set_alpha(int(255 * 0.85 * flash_lvl))
            scr.blit(self.white, (0, 0))

        if self.name_edit:
            box = pygame.Rect(C.WIDTH // 2 - 210, 300, 420, 60)
            S.panel(scr, box, C.CYAN, alpha=230)
            S.blit_text(scr, S.font(14, True), t("НАЗВАНИЕ ЧАРТА — ENTER"), C.CYAN, C.WIDTH // 2, 290)
            shown = self.name_buf + ("|" if (self.frame // 30) % 2 == 0 else " ")
            S.blit_text(scr, S.font(20, True), shown, C.WHITE, C.WIDTH // 2, 328)

        if self.menu_open:
            scr.blit(self.veil, (0, 0))
            S.glitch_title(scr, S.font(36, True), t("РЕДАКТОР"), C.CYAN, C.WIDTH // 2, 110, 60)
            for i, btn in enumerate(self.menu_btns):
                disabled = self.menu_items[i][0] == "auto" and not autochart.AVAILABLE
                btn.color = C.DIM if disabled else C.CYAN
                btn.draw(scr, mouse, active=(i == self.menu_sel))
            S.blit_text(scr, S.font(14), t("ESC — закрыть меню"), C.GREY, C.WIDTH // 2, 566)

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

    def _draw_heals(self, scr):
        for ev in self.chart.events:
            if ev["type"] != "heal":
                continue
            lane = ev["lane"] - 1
            x = self._lane_x(lane)
            y = self.time_to_y(ev["t"])
            if -40 <= y <= C.HEIGHT + 40:
                pygame.draw.circle(scr, C.LANE_COLORS[lane], (x, int(y)), 19, 2)
                pygame.draw.circle(scr, C.WHITE, (x, int(y)), 15)

    def _draw_panel(self, scr, mouse):
        if self.menu_open:
            return
        self.events_btn.draw(scr, mouse)
        scr.blit(S.font(12, True).render(t("СКОРОСТЬ"), True, (120, 160, 190)), (PANEL_X, 168))
        for i, btn in enumerate(self.speed_btns):
            btn.color = C.GOLD if i == self.speed_i else C.DIM
            btn.draw(scr, mouse, active=(i == self.speed_i))

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
                label = cache.text(12, True, t(events.TYPE_NAMES[ev["type"]]), grey)
                scr.blit(label, (x + 14, y - label.get_height() // 2))

    def _draw_overview(self, scr):
        pygame.draw.rect(scr, (30, 30, 50), (0, 0, C.WIDTH, BAR_H))
        prog = self.cursor / max(1, self.duration)
        pygame.draw.rect(scr, C.CYAN, (0, 0, int(C.WIDTH * prog), BAR_H))
        for n in self.chart.notes:
            x = int(n.t / max(1, self.duration) * C.WIDTH)
            pygame.draw.line(scr, C.LANE_COLORS[n.lane], (x, 0), (x, BAR_H), 1)
        if not self.playing:
            for ev in self.chart.events:
                x = int(ev["t"] / max(1, self.duration) * C.WIDTH)
                pygame.draw.rect(scr, events.TYPE_COLORS[ev["type"]], (x - 1, BAR_H + 2, 3, 6))

    def _draw_hud(self, scr):
        status = "▶" if self.playing else "❚❚"
        left = f"{status}  {fmt_time(self.cursor)} / {fmt_time(self.duration)}"
        scr.blit(S.font(16, True).render(left, True, C.WHITE), (14, 16))
        name = f"{songs.display_title(self.chart.song)} — {self.chart.name}" + ("  *" if self.dirty else "")
        scr.blit(S.font(14).render(name, True, C.GREY), (14, 40))
        info = f"{t('нот')}: {len(self.chart.notes)}   {t('сетка')}: {self.snap} {t('мс')}   {t('масштаб')}: {self.zoom:.2f}   V {t('эффекты')}: {t('ВКЛ') if self.fx_on else t('ВЫКЛ')}"
        info_surf = S.font(14).render(info, True, C.GREY)
        scr.blit(info_surf, (C.WIDTH - info_surf.get_width() - 14, 16))
        hint = t("SPACE играть · ←→ курсор · PgUp/PgDn ±5 с · -/= скорость · G сетка · Del удалить · ESC меню")
        h = S.font(14).render(hint, True, (110, 110, 150))
        scr.blit(h, (C.WIDTH // 2 - h.get_width() // 2, C.HEIGHT - 22))


def S_mix(a, b, k):
    return tuple(int(a[i] + (b[i] - a[i]) * k) for i in range(3))
