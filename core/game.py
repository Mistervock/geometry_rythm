
#-- Импорт
import math
import random
import sys
from collections import deque

import pygame

import audio
import cache
import config as C
import display
import engine as EN
import events as EV
import ghost as GH
import holdviz
import practice as PR
import scoring
import settings
import songs
import stretch
import screen_setting as SS
import style as S
from i18n import t

COUNTDOWN_MS = 3000
COUNTDOWN_WORDS = (("3", -3000, -2000), ("2", -2000, -1000), ("1", -1000, -400),
                   ("RYTHM!", -400, 0))
HOLD_TICK_MS = EN.HOLD_TICK_MS
HOLD_TICK_POINTS = EN.HOLD_TICK_POINTS
HOLD_BONUS = EN.HOLD_BONUS

GRADE_POINTS = EN.GRADE_POINTS
GRADE_TEXT = {"perfect": "PERFECT", "great": "GREAT", "good": "GOOD", "miss": "MISS"}
GRADE_COL = {"perfect": C.GOLD, "great": C.CYAN, "good": C.GREEN, "miss": C.RED_LIGHT}
ACC_WEIGHT = scoring.ACC_WEIGHT


def _lighten(col, k):
    return tuple(int(c + (255 - c) * k) for c in col)


def _mix(a, b, k):
    return tuple(int(a[i] + (b[i] - a[i]) * k) for i in range(3))


class Game:
    """Экран игры. Вся логика оценок — в Engine; здесь ввод, часы, звук и отрисовка.

    session — готовые данные (session.Session): файлы не читаются и ресурсы не грузятся в игровом цикле."""

    def __init__(self, clock, session):
        self.clock = clock
        self.s = session
        self.chart = session.chart
        self.practice = session.practice
        self.speed = session.speed
        self.notes = session.notes
        self.index = session.index
        self.duration = session.duration
        self.energy = session.energy
        self.energy_fps = session.energy_fps
        self.keys = settings.lane_keys()
        self.key_names = settings.get("lane_keys")
        self.scroll = session.scroll

        sect = (self.practice.a, self.practice.b) if self.practice else None
        self.engine = EN.Engine(self.notes, session.heals, duration=self.duration,
                                practice=self.practice is not None,
                                hp_loss=bool(self.practice and self.practice.hp_loss),
                                sink=self._sink, section=sect)
        self.song = audio.SongClock(self.speed)
        self.canvas = pygame.Surface((C.WIDTH, C.HEIGHT))
        self.veil = pygame.Surface((C.WIDTH, C.HEIGHT), pygame.SRCALPHA)
        self.veil.fill((0, 0, 0, 185))
        self.white = pygame.Surface((C.WIDTH, C.HEIGHT))
        self.white.fill(C.WHITE)
        self.frame = 0
        self.dt = 0.016
        self.bg_events = session.bg_events
        self.gview = None
        if session.ghost is not None and settings.get("ghost"):
            self.gview = GH.View(session.ghost, sect)

        self.attempts = []
        self.attempt_no = 0
        self.paused = False
        self.finished = False
        self.to_menu = False
        self.restart_toast = 0.0
        self._build_buttons()
        self._begin()

    #-- Совместимость: состояние движка в привычных именах

    @property
    def counts(self):
        return self.engine.counts

    @property
    def combo(self):
        return self.engine.combo

    @property
    def score(self):
        return self.engine.score

    @property
    def hp(self):
        return self.engine.hp

    @property
    def failed(self):
        return self.engine.failed

    @property
    def total(self):
        return self.engine.total

    def _build_buttons(self):
        font = S.font(18, True)
        if self.practice is None:
            self.pause_btns = [("resume", S.Btn(SS.UR(640 - 150, 236, 300, 50), t("ПРОДОЛЖИТЬ"), C.CYAN, font)),
                               ("menu", S.Btn(SS.UR(640 - 150, 302, 300, 50), t("В МЕНЮ"), (255, 160, 90), font))]
        else:
            specs = (("resume", t("ПРОДОЛЖИТЬ"), C.CYAN), ("restart", t("ЗАНОВО (R)"), C.GREEN),
                     ("setup", t("УЧАСТОК И СКОРОСТЬ"), C.GOLD), ("results", t("ЗАВЕРШИТЬ"), C.PURPLE_LIGHT),
                     ("menu", t("В МЕНЮ"), (255, 160, 90)))
            self.pause_btns = [(a, S.Btn(SS.UR(640 - 150, 220 + i * 60, 300, 48), label, col, font))
                               for i, (a, label, col) in enumerate(specs)]

    #-- Начало прохода (и повторы практики)

    def _begin(self):
        """Чистое состояние: движок, события, эффекты и звук начинаются заново. Ничего не копится между повторами."""
        e = self.engine
        e.start_attempt()
        self.attempt_no += 1
        start = -COUNTDOWN_MS if self.practice is None else self.practice.start_time
        self.start_time = start
        self.seg0 = max(0, start)
        self.song.start(start)
        audio.stop_song()
        self.music_started = False
        self.words_played = set()
        self.now = float(start)
        self.ev_queue = deque(ev for ev in self.s.events if ev["t"] > start)
        self.ev_active = [(ev, None) for ev in self.s.events if ev["t"] <= start < ev["t"] + EV.total_ms(ev)]
        self.heal_glitch = 0.0
        self.hp_show = float(e.hp)
        self.score_show = 0.0
        self.glow = [0.0] * 4
        self.rings = []
        self.parts = []
        self.popups = []
        self.combo_pop = 0.0
        self.energy_val = 0.0
        self.shake_t = 0.0
        if self.gview is not None:
            self.gview.update(start)

    def run(self):
        while True:
            dt = min(0.05, display.tick(self.clock) / 1000.0)
            self.dt = dt
            mouse = pygame.mouse.get_pos()
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if self.paused:
                    self._pause_event(ev, mouse)
                else:
                    self._play_event(ev)
            if self.finished:
                return self.result()
            if not self.paused:
                self._update(dt)
            self._draw(mouse)
            if self.finished:
                return self.result()
            display.flip()
            self.frame += 1

    #-- Итог

    def _final_summary(self):
        if self.practice is not None and self.attempts:
            return self.attempts[-1]
        return self.engine.summary()

    def result(self):
        e = self.engine
        st = self._final_summary()
        out = {
            "score": st["score"],
            "acc": st["acc"],
            "grade": st["grade"],
            "counts": dict(st["counts"]),
            "max_combo": st["max_combo"],
            "failed": st["failed"],
            "total": st["total"],
            "song": songs.display_title(self.chart.song),
            "chart": self.chart.name,
            "action": "menu" if self.to_menu else "results",
            "stats": st,
            "practice": self.practice is not None,
            "notes_hash": self.chart.notes_hash(),
        }
        if self.practice is None:
            out["judgments"] = [j.to_list() for j in e.judgments]
            out["timeline"] = list(e.timeline)
        else:
            out["section"] = (self.practice.a, self.practice.b)
            out["speed"] = self.practice.speed
            out["attempts"] = [{"acc": a["acc"], "score": a["score"], "grade": a["grade"]} for a in self.attempts]
            out["practice_cfg"] = self.practice.to_dict()
            if not self.attempts:
                out["action"] = "menu"          # ни одного завершённого прохода — показывать нечего
        return out

    #-- Ввод

    def _play_event(self, ev):
        if ev.type == pygame.KEYDOWN:
            if ev.key in (pygame.K_ESCAPE, pygame.K_p):
                self._set_pause(True)
            elif ev.key == pygame.K_r and self.practice is not None:
                self._restart()
            elif ev.key in self.keys:
                lane = self.keys.index(ev.key)
                self.engine.press(lane, self.song.now())
        elif ev.type == pygame.KEYUP and ev.key in self.keys:
            lane = self.keys.index(ev.key)
            self.engine.release(lane, self.song.now())

    def _pause_event(self, ev, mouse):
        if ev.type == pygame.KEYDOWN:
            if ev.key in (pygame.K_ESCAPE, pygame.K_p):
                self._set_pause(False)
            elif ev.key == pygame.K_m:
                self._go_menu()
            elif ev.key == pygame.K_r and self.practice is not None:
                self._set_pause(False)
                self._restart()
        elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            for action, btn in self.pause_btns:
                if btn.rect.collidepoint(ev.pos):
                    self._pause_action(action)
                    break

    def _pause_action(self, action):
        if action == "resume":
            self._set_pause(False)
        elif action == "menu":
            self._go_menu()
        elif action == "restart":
            self._set_pause(False)
            self._restart()
        elif action == "results":
            self._finish_practice()
        elif action == "setup":
            self._edit_section()

    def _set_pause(self, on):
        if on and not self.paused:
            self.paused = True
            self.song.pause()
            audio.pause_song()
        elif not on and self.paused:
            self.paused = False
            self.song.resume()
            audio.resume_song()
            pressed = pygame.key.get_pressed()
            self.engine.now = self.song.now()
            self.engine.sync_held([bool(pressed[k]) for k in self.keys])

    def _go_menu(self):
        self.to_menu = True
        self.finished = True
        audio.stop_song()

    def _finish_practice(self):
        if not self.attempts and self.engine.judgments:
            self.engine.abort()
            self.attempts.append(self.engine.summary())
        audio.stop_song()
        self.finished = True

    def _restart(self):
        self._begin()                               # незавершённый проход в статистику не попадает

    def _edit_section(self):
        """Пауза → экран выбора участка: можно изменить границы, скорость, цикл и потерю HP."""
        cfg = PR.setup_screen(self.clock, self.chart, self.duration, self.practice, self.energy,
                              self.energy_fps)
        if cfg is None:
            return
        if cfg.speed != self.speed:
            path = stretch.playable(self.s.song_file, cfg.speed)
            if path is None:
                cfg.speed = self.speed
            else:
                self.s.play_file = path
                self.speed = cfg.speed
                self.s.speed = cfg.speed
                self.song.speed = cfg.speed
                audio.preload_song(path)
        self.practice = self.s.practice = cfg
        e = self.engine
        e.hp_loss = cfg.hp_loss
        e.set_section(cfg.a, cfg.b)
        if self.gview is not None:
            self.gview = GH.View(self.s.ghost, (cfg.a, cfg.b))
        self.attempts = []
        self.attempt_no = 0
        self.paused = False
        self._begin()

    #-- Звуки и эффекты по событиям движка

    def _sink(self, kind, **d):
        if kind == "press":
            self.glow[d["lane"]] = 1.0
        elif kind == "heal_hit":
            lane = d["heal"]["lane"]
            self.popups.append({"text": "+HP", "sub": "", "x": self._lane_x(lane),
                                "y": C.HIT_Y - SS.U(70), "col": C.GREEN, "age": 0.0})
            audio.play("upgrade", 0.45)
        elif kind == "heal_miss":
            self.heal_glitch = 0.35
        elif kind == "hit":
            self._fx_hit(d["note"], d["grade"], d["offset"])
        elif kind == "hold_ok":
            n = d["note"]
            self.popups.append({"text": "HOLD", "sub": "", "x": self._lane_x(n.lane),
                                "y": C.HIT_Y - SS.U(70), "col": C.GREEN, "age": 0.0})
            audio.play("shield", 0.35)
        elif kind == "hold_break":
            n = d["note"]
            self.popups.append({"text": "BREAK", "sub": "", "x": self._lane_x(n.lane),
                                "y": C.HIT_Y - SS.U(70), "col": C.RED_LIGHT, "age": 0.0})
            audio.play("hurt", 0.3)
        elif kind == "miss":
            n = d["note"]
            self.popups.append({"text": GRADE_TEXT["miss"], "sub": "", "x": self._lane_x(n.lane),
                                "y": C.HIT_Y - SS.U(70), "col": C.RED_LIGHT, "age": 0.0})
            self.shake_t = 0.25
            audio.play("hurt", 0.5)

    def _fx_hit(self, n, grade, offset_ms):
        self.combo_pop = 1.0
        cx, cy = self._lane_x(n.lane), C.HIT_Y
        col = C.LANE_COLORS[n.lane]
        self.rings.append({"x": cx, "y": cy, "col": col, "age": 0.0,
                           "life": 0.5 if grade == "perfect" else 0.35,
                           "big": grade == "perfect"})
        count = 16 if grade == "perfect" else 9
        for _ in range(count):
            ang = random.uniform(0, math.tau)
            sp = random.uniform(120, 320) * SS.SCALE
            life = random.uniform(0.3, 0.6)
            self.parts.append({"x": cx, "y": cy, "vx": math.cos(ang) * sp,
                               "vy": math.sin(ang) * sp - 60 * SS.SCALE, "life": life, "max": life,
                               "col": col})
        sub = f"{offset_ms:+.0f} ms" if grade != "perfect" else ""
        self.popups.append({"text": GRADE_TEXT[grade], "sub": sub, "x": cx,
                            "y": C.HIT_Y - SS.U(70), "col": GRADE_COL[grade], "age": 0.0})
        audio.play("catch" if grade == "perfect" else "tick", 0.45)
        if self.engine.combo > 0 and self.engine.combo % 10 == 0:
            audio.play("combo", 0.5)

    #-- Обновление

    def _update(self, dt):
        e = self.engine
        now = self.song.now()
        self.now = now

        if not self.music_started and now >= self.seg0:
            audio.play_song(self.s.play_file, max(self.seg0, now) / self.speed)    # догоняем кадр запаздывания: звук точно по часам
            self.music_started = True
        if self.practice is None:
            for word, start, _ in COUNTDOWN_WORDS:
                if now >= start and word not in self.words_played:
                    self.words_played.add(word)
                    audio.play("upgrade" if word == "RYTHM!" else "tick", 0.5)

        e.update(now)
        if e.done:
            self._on_done()
            if self.finished:
                return
            now = self.now

        while self.ev_queue and now >= self.ev_queue[0]["t"]:
            ev = self.ev_queue.popleft()
            # картинки и ролики подготовлены заранее (session); рисуются через EV.draw_media
            self.ev_active.append((ev, None))
        self.ev_active = [(ev, s) for ev, s in self.ev_active if now - ev["t"] < EV.total_ms(ev)]

        self.heal_glitch = max(0.0, self.heal_glitch - dt)
        for i in range(4):
            self.glow[i] = S.approach(self.glow[i], 0.0, dt, 9)
        self.hp_show = S.approach(self.hp_show, e.hp, dt, 9)
        self.score_show = S.approach(self.score_show, e.score, dt, 14)
        self.combo_pop = S.approach(self.combo_pop, 0.0, dt, 7)
        self.shake_t = max(0.0, self.shake_t - dt)
        self.energy_val = S.approach(self.energy_val, self._energy_at(now), dt, 16)
        if self.gview is not None:
            self.gview.update(now)

        for rg in self.rings:
            rg["age"] += dt
        self.rings = [rg for rg in self.rings if rg["age"] < rg["life"]]
        for p in self.parts:
            p["x"] += p["vx"] * dt
            p["y"] += p["vy"] * dt
            p["vy"] += 260 * SS.SCALE * dt
            p["life"] -= dt
        self.parts = [p for p in self.parts if p["life"] > 0]
        for p in self.popups:
            p["age"] += dt
        self.popups = [p for p in self.popups if p["age"] < 0.7]
        if self.restart_toast > 0:
            self.restart_toast -= dt

    def _on_done(self):
        e = self.engine
        if self.practice is None:
            self.finished = True
            audio.stop_song()
            return
        if e.judgments:
            self.attempts.append(e.summary())
            del self.attempts[:-50]
        if self.practice.loop:
            self.restart_toast = 1.0
            self._begin()
        else:
            self.finished = True
            audio.stop_song()

    def _energy_at(self, ms):
        if not self.energy:
            return 0.0
        i = int(ms / 1000.0 * self.energy_fps)
        i = max(0, min(len(self.energy) - 1, i))
        return self.energy[i] / 100.0

    def _lane_x(self, lane):
        return C.FIELD_X + lane * (C.LANE_W + C.LANE_GAP) + C.LANE_W // 2

    def _screen(self):
        return pygame.display.get_surface()

    #-- Отрисовка

    def _draw(self, mouse):
        c = self.canvas
        now = self.now
        c.fill(EV.bg_at(self.bg_events, now))
        S.draw_grid(c, now * 0.04, self.energy_val * 0.8)

        self._draw_images(c, now)
        self._draw_lanes(c)
        self._draw_notes(c, now)
        self._draw_heals(c, now)
        self._draw_fx(c)
        self._draw_ghost(c, now)
        self._draw_cards(c, now)
        self._draw_hud(c, now)
        if now < 0 and self.practice is None:
            self._draw_countdown(c, now)

        dx = random.randint(-SS.U(4), SS.U(4)) if self.shake_t > 0 else 0
        dy = random.randint(-SS.U(2), SS.U(2)) if self.shake_t > 0 else 0
        scr = self._screen()
        scr.blit(c, (dx, dy))
        EV.apply_invert(scr, self._event_invert(now))
        glitch = max(self.shake_t / 0.25 if self.shake_t > 0 else 0.0, self._event_glitch(now),
                     self.heal_glitch / 0.35 * 0.7)
        if glitch > 0:
            S.glitch(scr, strength=glitch)
        flash = self._event_flash(now)
        if flash > 0:
            self.white.set_alpha(int(255 * 0.85 * flash))
            scr.blit(self.white, (0, 0))
        S.post_fx(scr, self.frame, grain=40)

        if self.paused:
            self._draw_pause(mouse)

    def _event_glitch(self, now):
        return max((EV.glitch_level(ev, now - ev["t"]) for ev, _ in self.ev_active
                    if ev["type"] == "glitch"), default=0.0)

    def _event_flash(self, now):
        return max((EV.flash_alpha(ev, now - ev["t"]) for ev, _ in self.ev_active
                    if ev["type"] == "flash"), default=0.0)

    def _event_invert(self, now):
        return max((EV.invert_level(ev, now - ev["t"]) for ev, _ in self.ev_active
                    if ev["type"] == "invert"), default=0.0)

    def _draw_cards(self, c, now):
        for ev, _ in self.ev_active:
            if ev["type"] == "card":
                EV.draw_card(c, ev, now - ev["t"])

    def _draw_images(self, c, now):
        for ev, _ in self.ev_active:
            if ev["type"] in ("image", "video"):
                EV.draw_media(c, ev, now - ev["t"])

    def _draw_lanes(self, c):
        for i in range(4):
            x = C.FIELD_X + i * (C.LANE_W + C.LANE_GAP)
            col = C.LANE_COLORS[i]
            band = cache.band(i)
            band.set_alpha(int(12 + 55 * self.glow[i]))
            c.blit(band, (x, 0))
            pygame.draw.line(c, _mix(C.GRID_COL, col, 0.35), (x, 0), (x, C.HEIGHT), SS.U(1))
            pygame.draw.line(c, _mix(C.GRID_COL, col, 0.35), (x + C.LANE_W, 0),
                             (x + C.LANE_W, C.HEIGHT), SS.U(1))

        pygame.draw.line(c, C.WHITE, (C.FIELD_X, C.HIT_Y), (C.FIELD_X + C.FIELD_W, C.HIT_Y), SS.U(2))
        for i in range(4):
            x = C.FIELD_X + i * (C.LANE_W + C.LANE_GAP)
            col = C.LANE_COLORS[i]
            k = self.glow[i]
            pad = pygame.Rect(x + SS.U(4), C.HIT_Y - SS.U(22), C.LANE_W - SS.U(8), SS.U(44))
            pygame.draw.rect(c, _lighten(_mix(C.BG_DARK, col, 0.25 + 0.5 * k), 0.2 * k),
                             pad, border_radius=SS.U(8))
            pygame.draw.rect(c, _lighten(_mix(C.DIM, col, 0.6), 0.6 * k), pad, SS.U(2), border_radius=SS.U(8))
            label = cache.text(18, True, settings.key_label(self.key_names[i]), col)
            c.blit(label, (x + C.LANE_W // 2 - label.get_width() // 2, C.HIT_Y + SS.U(40)))

    def _draw_body(self, c, n, lane, y_head, y_tail, target):
        """Тело удержания через общую геометрию (holdviz): без щелей, мерцания и срезов у края экрана."""
        n.vis = holdviz.smooth_factor(n.vis, target, self.dt)
        f = n.vis
        if f <= 0.01:
            return
        holdviz.draw_body(c, lane, self._lane_x(lane), y_head, y_tail, 0.25 + 0.4 * f, 0.7 * f)

    def _draw_notes(self, c, now):
        speed = C.TRAVEL_PX / self.scroll
        for n in self.index.visible(now - 700, now + self.scroll + 120):
            lane = n.lane
            cx = self._lane_x(lane)
            st = n.state
            if st == "wait":
                dt = n.t - now
                if dt > self.scroll + 120:
                    continue
                y = C.HIT_Y - dt * speed
                if n.dur > 0:
                    tail = C.HIT_Y - (n.end - now) * speed
                    if y >= -SS.U(40):
                        self._draw_body(c, n, lane, y, tail, 0.8)
                if y < -SS.U(40):
                    continue
                alpha = int(255 * S.clamp((y + SS.U(40)) / SS.U(110)))
                self._blit_note(c, lane, cx, y, 1.0, alpha)
            elif st == "hold":
                tail = C.HIT_Y - (n.end - now) * speed
                self._draw_body(c, n, lane, C.HIT_Y, tail, 1.0 if n.held else 0.5)
                pulse = 1.0 + 0.04 * math.sin(now * 0.02) if n.held else 1.0
                self._blit_note(c, lane, cx, C.HIT_Y, pulse, 255)
            elif st == "hit":
                age = (now - n.hit_at) / 0.2
                if age >= 1:
                    continue
                e = S.ease_out_cubic(age)
                self._blit_note(c, lane, cx, C.HIT_Y, 1.0 + 0.7 * e, int(255 * (1 - age)))
            elif st == "broken":
                age = (now - n.hit_at) / 0.4
                if age >= 1:
                    continue
                n.vis = 0.6 * (1 - age)
                holdviz.draw_body(c, lane, cx, C.HIT_Y, C.HIT_Y - SS.U(60) * age, 0.25 + 0.4 * n.vis, 0.7 * n.vis)
            elif st == "miss":
                age = (now - n.hit_at) / 0.35
                if age >= 1:
                    continue
                y = C.HIT_Y - (n.t - now) * speed + age * SS.U(40)
                pygame.draw.rect(c, _mix(C.BG_DARK, C.DIM, 1 - age), (cx - SS.U(12), y - SS.U(12), SS.U(24), SS.U(24)),
                                 border_radius=SS.U(5))

    def _draw_heals(self, c, now):
        for h in self.engine.heals:
            cx = self._lane_x(h["lane"])
            if h["state"] == "wait":
                dt = h["t"] - now
                if dt > h["fall"]:
                    continue
                y = C.HIT_Y - dt * C.TRAVEL_PX / h["fall"]
                if y < -SS.U(40):
                    continue
                pygame.draw.circle(c, C.LANE_COLORS[h["lane"]], (cx, int(y)), SS.U(19), SS.U(2))
                pygame.draw.circle(c, C.WHITE, (cx, int(y)), SS.U(15))
            elif h["state"] == "hit":
                age = (now - h["hit_at"]) / 0.35
                if age >= 1:
                    continue
                r = int(SS.U(16) + SS.U(36) * S.ease_out_cubic(age))
                pygame.draw.circle(c, _mix(C.BG_DARK, C.WHITE, 1 - age), (cx, C.HIT_Y), r, SS.U(3))

    def _blit_note(self, c, lane, cx, y, scale, alpha):
        if alpha <= 0:
            return
        sprite = cache.note(lane, scale)
        sprite.set_alpha(alpha)
        c.blit(sprite, (cx - sprite.get_width() // 2, holdviz.snap_y(y) - sprite.get_height() // 2))

    def _draw_fx(self, c):
        for rg in self.rings:
            e = S.ease_out_cubic(rg["age"] / rg["life"])
            rad = int((SS.U(18) + SS.U(60) * e) * (1.35 if rg["big"] else 1.0))
            a = int(255 * (1 - e))
            if rad <= 0 or a <= 0:
                continue
            ring = cache.ring(rg["col"], rad)
            ring.set_alpha(a)
            c.blit(ring, (rg["x"] - ring.get_width() // 2, rg["y"] - ring.get_height() // 2))
        for p in self.parts:
            k = max(0.0, p["life"] / p["max"])
            col = _mix(C.BG_DARK, p["col"], k)
            pygame.draw.rect(c, col, (int(p["x"]) - SS.U(2), int(p["y"]) - SS.U(2), SS.U(4), SS.U(4)))
        for p in self.popups:
            t = p["age"] / 0.7
            y = p["y"] - SS.U(40) * S.ease_out_cubic(t)
            a = int(255 * (1 - S.smoothstep(max(0.0, (t - 0.5) / 0.5))))
            if a <= 0:
                continue
            label = cache.text(22, True, p["text"], p["col"])
            label.set_alpha(a)
            c.blit(label, (p["x"] - label.get_width() // 2, y - label.get_height() // 2))
            if p["sub"]:
                sub = cache.text(14, False, p["sub"], C.GREY)
                sub.set_alpha(int(a * 0.8))
                c.blit(sub, (p["x"] - sub.get_width() // 2, y + SS.U(12)))

    def _draw_ghost(self, c, now):
        """Призрак: тонкие контуры на площадках в моменты его попаданий. Не закрывает ноты и ничего не считает."""
        g = self.gview
        if g is None:
            return
        for tm, lane, code in g.recent:
            age = (now - tm) / 260.0
            if not 0 <= age < 1:
                continue
            col = C.RED_LIGHT if code == "m" else (200, 200, 220)
            a = int(150 * (1 - age))
            rad = SS.U(26) + int(SS.U(10) * age)
            ring = cache.ring(col, rad)
            ring.set_alpha(a)
            c.blit(ring, (self._lane_x(lane) - ring.get_width() // 2, C.HIT_Y - ring.get_height() // 2))

    def _draw_countdown(self, c, now):
        current = None
        for word, start, end in COUNTDOWN_WORDS:
            if start <= now < end:
                current = (word, start, end)
        if current is None:
            return
        word, start, end = current
        k = now - start
        fade_in = S.clamp(k / 150.0)
        fade_out = S.clamp((end - now) / 120.0)
        alpha = int(255 * min(fade_in, fade_out))
        gold = word == "RYTHM!"
        col = C.GOLD if gold else C.CYAN
        cx, cy = C.WIDTH // 2, C.HEIGHT // 2 - SS.U(40)

        if gold:
            ring_r = int(SS.U(30) + SS.U(260) * S.ease_out_cubic(k / 500.0))
            ring_a = 1 - S.clamp(k / 500.0)
            if ring_r > 0 and ring_a > 0:
                pygame.draw.circle(c, _mix(C.BG_DARK, C.GOLD, ring_a), (cx, cy), ring_r, SS.U(3))

        surf = cache.text(cache.COUNTDOWN_SIZE, True, word, col)
        dx = dy = 0
        if k < 350 and random.random() < 0.4:
            dx = random.randint(-SS.U(6), SS.U(6))
            dy = random.randint(-SS.U(2), SS.U(2))
            ghost = cache.text(cache.COUNTDOWN_SIZE, True, word, C.CYAN)
            ghost.set_alpha(110)
            c.blit(ghost, (cx - ghost.get_width() // 2 + dx + SS.U(4), cy - ghost.get_height() // 2 + dy))
        surf.set_alpha(alpha)
        c.blit(surf, (cx - surf.get_width() // 2 + dx, cy - surf.get_height() // 2 + dy))

    def _draw_hud(self, c, now):
        u = SS.U
        e = self.engine
        prog = S.clamp(now / max(1, self.duration))
        pygame.draw.rect(c, C.GRID_COL, (0, 0, C.WIDTH, u(3)))
        if prog > 0:
            pygame.draw.rect(c, C.CYAN, (0, 0, int(C.WIDTH * prog), u(3)))
        if self.practice is not None:
            for ms, col in ((self.practice.a, C.GREEN), (self.practice.b, C.RED_LIGHT)):
                x = int(C.WIDTH * ms / max(1, self.duration))
                pygame.draw.rect(c, col, (x - u(1), 0, u(3), u(8)))

        show_hp = self.practice is None or self.practice.hp_loss
        if show_hp:
            c.blit(S.font(14, True).render("HP", True, C.GREY), SS.UP(20, 14))
            for i in range(C.MAX_HP):
                x = u(60) + i * u(26)
                fill = S.clamp(self.hp_show - i)
                pygame.draw.rect(c, (40, 40, 60), (x, u(14), u(20), u(14)), border_radius=u(3))
                if fill > 0:
                    col = C.GREEN if e.hp > 2 else C.RED
                    pygame.draw.rect(c, col, (x, u(14), int(u(20) * fill), u(14)), border_radius=u(3))
                pygame.draw.rect(c, (60, 60, 80), (x, u(14), u(20), u(14)), 1, border_radius=u(3))
        if self.practice is not None:
            badge = pygame.Rect(u(20), u(12) if not show_hp else u(36), u(200), u(22))
            pygame.draw.rect(c, (30, 24, 0), badge, border_radius=u(4))
            pygame.draw.rect(c, C.GOLD, badge, u(2), border_radius=u(4))
            txt = S.font(13, True).render(f"{t('ПРАКТИКА')} {int(self.speed * 100)}%", True, C.GOLD)
            c.blit(txt, (badge.centerx - txt.get_width() // 2, badge.centery - txt.get_height() // 2))
            sec = f"{PR.fmt(self.practice.a)[:-4]}–{PR.fmt(self.practice.b)[:-4]}  #{self.attempt_no}"
            c.blit(S.font(12).render(sec, True, C.GREY), (u(20), badge.bottom + u(4)))

        score_txt = S.font(22, True).render(f"{int(self.score_show):06d}", True, C.GOLD)
        c.blit(score_txt, (C.WIDTH - score_txt.get_width() - u(20), u(10)))

        acc_txt = S.font(14).render(f"{t('ТОЧНОСТЬ')} {e.accuracy():5.1f}%" if e.judgments
                                    else f"{t('ТОЧНОСТЬ')}   0.0%", True, C.GREY)
        c.blit(acc_txt, (C.WIDTH - acc_txt.get_width() - u(20), u(42)))

        if self.gview is not None:
            self._draw_ghost_panel(c)

        if e.combo >= 2:
            size = u(22) + int(u(6) * self.combo_pop)
            combo_txt = S.font(size, True).render(f"COMBO x{e.combo}", True,
                                                  _lighten(C.PURPLE_LIGHT, 0.3 * self.combo_pop))
            c.blit(combo_txt, (C.WIDTH // 2 - combo_txt.get_width() // 2, u(60)))

        if self.restart_toast > 0:
            S.blit_text(c, S.font(16, True), t("ПОВТОР"), C.GOLD, C.WIDTH // 2, u(110),
                        255 * min(1.0, self.restart_toast))

        hint = cache.text(14, False, t("ESC — пауза") if self.practice is None
                          else t("ESC — пауза · R — заново"), (90, 90, 120))
        c.blit(hint, (C.WIDTH // 2 - hint.get_width() // 2, C.HEIGHT - u(26)))

    def _draw_ghost_panel(self, c):
        u = SS.U
        g = self.gview
        diff = g.delta(self.engine.score)
        col = C.GREEN if diff >= 0 else C.RED_LIGHT
        box = pygame.Rect(C.WIDTH - u(190), u(66), u(170), u(40))
        veil = pygame.Surface(box.size, pygame.SRCALPHA)
        veil.fill((10, 10, 25, 120))
        c.blit(veil, box.topleft)
        c.blit(S.font(12, True).render("GHOST", True, (150, 150, 180)), (box.x + u(8), box.y + u(4)))
        c.blit(S.font(13).render(f"{g.score:06d}", True, (190, 190, 210)), (box.x + u(8), box.y + u(20)))
        d = S.font(15, True).render(f"{diff:+d}", True, col)
        c.blit(d, (box.right - d.get_width() - u(8), box.y + u(12)))

    def _draw_pause(self, mouse):
        scr = self._screen()
        scr.blit(self.veil, (0, 0))
        S.glitch_title(scr, S.font(44, True), t("ПАУЗА"), C.CYAN, C.WIDTH // 2, SS.U(150),
                       self.frame % 200, length=40)
        for _, btn in self.pause_btns:
            btn.draw(scr, mouse)
        hint = t("P / ESC — продолжить, M — в меню") if self.practice is None \
            else t("P / ESC — продолжить, R — заново, M — в меню")
        S.blit_text(scr, S.font(14), hint, C.GREY, C.WIDTH // 2,
                    SS.U(446) if self.practice is None else SS.U(540))
