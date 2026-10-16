
#-- Импорт
import math
import random
import sys
from collections import deque

import pygame

import audio
import cache
import config as C
import events as EV
import settings
import songs
import style as S

COUNTDOWN_MS = 3000
COUNTDOWN_WORDS = (("3", -3000, -2000), ("2", -2000, -1000), ("1", -1000, -400),
                   ("RYTHM!", -400, 0))
HOLD_TICK_MS = 200
HOLD_TICK_POINTS = 10
HOLD_BONUS = 150

GRADE_POINTS = {"perfect": 300, "great": 200, "good": 100}
GRADE_TEXT = {"perfect": "PERFECT", "great": "GREAT", "good": "GOOD", "miss": "MISS"}
GRADE_COL = {"perfect": C.GOLD, "great": C.CYAN, "good": C.GREEN, "miss": C.RED_LIGHT}
ACC_WEIGHT = {"perfect": 1.0, "great": 0.75, "good": 0.5, "miss": 0.0}


def _lighten(col, k):
    return tuple(int(c + (255 - c) * k) for c in col)


def _mix(a, b, k):
    return tuple(int(a[i] + (b[i] - a[i]) * k) for i in range(3))


class Game:
    def __init__(self, clock, chart):
        self.clock = clock
        self.chart = chart
        self.notes = chart.copy_notes()
        self.total = len(self.notes)
        self.last_note_t = max((n.end for n in self.notes), default=0)
        self.pending = [deque(n for n in self.notes if n.lane == i) for i in range(4)]
        self.holds = []
        self.held = [False] * 4
        info = songs.info(chart.song)
        self.duration = int(info.get("duration_ms") or self.last_note_t + 5000)
        self.energy = info.get("energy") or []
        self.energy_fps = float(info.get("energy_fps") or 21.5)
        self.keys = settings.lane_keys()
        self.key_names = settings.get("lane_keys")
        self.scroll = float(settings.get("scroll_ms"))

        self.song = audio.SongClock()
        self.canvas = pygame.Surface((C.WIDTH, C.HEIGHT))
        self.veil = pygame.Surface((C.WIDTH, C.HEIGHT), pygame.SRCALPHA)
        self.veil.fill((0, 0, 0, 185))
        self.now = float(-COUNTDOWN_MS)
        self.frame = 0
        self.music_started = False
        self.words_played = set()
        self.bg_events = sorted((e for e in chart.events if e["type"] == "bg"), key=lambda e: e["t"])
        self.ev_queue = deque(sorted((e for e in chart.events if e["type"] != "bg"),
                                     key=lambda e: e["t"]))
        self.ev_active = []
        self.white = pygame.Surface((C.WIDTH, C.HEIGHT))
        self.white.fill(C.WHITE)
        for ev in chart.events:
            if ev["type"] == "image":
                EV.image_surface(ev["file"], ev["w"])

        self.hp = C.MAX_HP
        self.hp_show = float(C.MAX_HP)
        self.combo = 0
        self.max_combo = 0
        self.score = 0
        self.score_show = 0.0
        self.counts = {"perfect": 0, "great": 0, "good": 0, "miss": 0}
        self.glow = [0.0] * 4
        self.rings = []
        self.parts = []
        self.popups = []
        self.combo_pop = 0.0
        self.energy_val = 0.0
        self.shake_t = 0.0

        self.paused = False
        self.finished = False
        self.failed = False
        self.to_menu = False
        self.resume_btn = S.Btn((C.WIDTH // 2 - 150, 236, 300, 50), "ПРОДОЛЖИТЬ", C.CYAN,
                                S.font(18, True))
        self.menu_btn = S.Btn((C.WIDTH // 2 - 150, 302, 300, 50), "В МЕНЮ", (255, 160, 90),
                              S.font(18, True))


    def run(self):
        self.song.start(-COUNTDOWN_MS)
        while True:
            dt = min(0.05, self.clock.tick(C.FPS) / 1000.0)
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
            pygame.display.flip()
            self.frame += 1

    def result(self):
        judged = sum(self.counts.values())
        acc = 100.0 * sum(self.counts[g] * ACC_WEIGHT[g] for g in self.counts) / max(1, judged)
        if self.failed:
            grade = "F"
        elif acc >= 95:
            grade = "S"
        elif acc >= 85:
            grade = "A"
        elif acc >= 70:
            grade = "B"
        elif acc >= 50:
            grade = "C"
        else:
            grade = "D"
        return {
            "score": self.score,
            "acc": round(acc, 2),
            "grade": grade,
            "counts": dict(self.counts),
            "max_combo": self.max_combo,
            "failed": self.failed,
            "total": self.total,
            "song": songs.title(self.chart.song),
            "chart": self.chart.name,
            "action": "menu" if self.to_menu else "results",
        }


    def _play_event(self, ev):
        if ev.type == pygame.KEYDOWN:
            if ev.key in (pygame.K_ESCAPE, pygame.K_p):
                self._set_pause(True)
            elif ev.key in self.keys:
                lane = self.keys.index(ev.key)
                self.held[lane] = True
                self._press(lane)
        elif ev.type == pygame.KEYUP and ev.key in self.keys:
            lane = self.keys.index(ev.key)
            self.held[lane] = False
            self._release(lane)

    def _pause_event(self, ev, mouse):
        if ev.type == pygame.KEYDOWN:
            if ev.key in (pygame.K_ESCAPE, pygame.K_p):
                self._set_pause(False)
            elif ev.key == pygame.K_m:
                self._go_menu()
        elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            if self.resume_btn.rect.collidepoint(ev.pos):
                self._set_pause(False)
            elif self.menu_btn.rect.collidepoint(ev.pos):
                self._go_menu()

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
            for lane, key in enumerate(self.keys):
                now_down = bool(pressed[key])
                if self.held[lane] and not now_down:
                    self.held[lane] = False
                    self._release(lane)
                else:
                    self.held[lane] = now_down

    def _go_menu(self):
        self.to_menu = True
        self.finished = True
        audio.stop_song()

    def _press(self, lane):
        now = self.now
        self.glow[lane] = 1.0
        q = self.pending[lane]
        best = None
        for n in list(q)[:3]:
            d = now - n.t
            if abs(d) <= C.WIN_GOOD and (best is None or abs(d) < abs(best)):
                best = d
                best_note = n
        if best is None:
            return
        q.remove(best_note)
        a = abs(best)
        grade = "perfect" if a <= C.WIN_PERFECT else "great" if a <= C.WIN_GREAT else "good"
        best_note.early = best < 0
        self._hit(best_note, grade, best)

    def _release(self, lane):
        for n in list(self.holds):
            if n.lane == lane and n.state == "hold" and n.held:
                n.held = False
                if self.now >= n.end - C.WIN_GOOD:
                    self._hold_success(n)
                else:
                    self._hold_break(n)


    def _update(self, dt):
        now = self.song.now()
        self.now = now

        if not self.music_started and now >= 0:
            audio.play_song(songs.song_path(self.chart.song), 0.0)
            self.music_started = True
        for word, start, _ in COUNTDOWN_WORDS:
            if now >= start and word not in self.words_played:
                self.words_played.add(word)
                audio.play("upgrade" if word == "RYTHM!" else "tick", 0.5)

        for lane in range(4):
            q = self.pending[lane]
            while q and now - q[0].t > C.WIN_GOOD:
                self._miss(q.popleft())
                if self.finished:
                    return

        for n in list(self.holds):
            if n.state != "hold":
                self.holds.remove(n)
                continue
            if not n.held:
                self._hold_break(n)
                continue
            if now >= n.next_tick and now < n.end:
                n.next_tick += HOLD_TICK_MS
                self.score += HOLD_TICK_POINTS * self._mult()
            if n.held and now >= n.end:
                self._hold_success(n)

        if (now > self.last_note_t + 1200 and not any(self.pending) and not self.holds) or \
                now >= self.duration:
            self._finish()
            return

        while self.ev_queue and now >= self.ev_queue[0]["t"]:
            ev = self.ev_queue.popleft()
            surf = EV.image_surface(ev["file"], ev["w"]) if ev["type"] == "image" else None
            if ev["type"] != "image" or surf is not None:
                self.ev_active.append((ev, surf))
        self.ev_active = [(ev, s) for ev, s in self.ev_active if now - ev["t"] < EV.total_ms(ev)]

        for i in range(4):
            self.glow[i] = S.approach(self.glow[i], 0.0, dt, 9)
        self.hp_show = S.approach(self.hp_show, self.hp, dt, 9)
        self.score_show = S.approach(self.score_show, self.score, dt, 14)
        self.combo_pop = S.approach(self.combo_pop, 0.0, dt, 7)
        self.shake_t = max(0.0, self.shake_t - dt)
        self.energy_val = S.approach(self.energy_val, self._energy_at(now), dt, 16)

        for rg in self.rings:
            rg["age"] += dt
        self.rings = [rg for rg in self.rings if rg["age"] < rg["life"]]
        for p in self.parts:
            p["x"] += p["vx"] * dt
            p["y"] += p["vy"] * dt
            p["vy"] += 260 * dt
            p["life"] -= dt
        self.parts = [p for p in self.parts if p["life"] > 0]
        for p in self.popups:
            p["age"] += dt
        self.popups = [p for p in self.popups if p["age"] < 0.7]

    def _mult(self):
        return 1 + min(self.combo // 10, 3)

    def _hit(self, n, grade, offset_ms):
        self.score += GRADE_POINTS[grade] * self._mult()
        self.combo += 1
        self.max_combo = max(self.max_combo, self.combo)
        self.combo_pop = 1.0
        self.counts[grade] += 1
        n.grade = grade
        n.hit_at = self.now
        if n.dur > 0:
            n.state = "hold"
            n.held = self.held[n.lane]
            n.next_tick = self.now + HOLD_TICK_MS
            self.holds.append(n)
        else:
            n.state = "hit"

        cx, cy = self._lane_x(n.lane), C.HIT_Y
        col = C.LANE_COLORS[n.lane]
        self.rings.append({"x": cx, "y": cy, "col": col, "age": 0.0,
                           "life": 0.5 if grade == "perfect" else 0.35,
                           "big": grade == "perfect"})
        count = 16 if grade == "perfect" else 9
        for _ in range(count):
            ang = random.uniform(0, math.tau)
            sp = random.uniform(120, 320)
            life = random.uniform(0.3, 0.6)
            self.parts.append({"x": cx, "y": cy, "vx": math.cos(ang) * sp,
                               "vy": math.sin(ang) * sp - 60, "life": life, "max": life,
                               "col": col})
        sub = f"{offset_ms:+.0f} ms" if grade != "perfect" else ""
        self.popups.append({"text": GRADE_TEXT[grade], "sub": sub, "x": cx,
                            "y": C.HIT_Y - 70, "col": GRADE_COL[grade], "age": 0.0})
        audio.play("catch" if grade == "perfect" else "tick", 0.45)
        if self.combo > 0 and self.combo % 10 == 0:
            audio.play("combo", 0.5)

    def _hold_success(self, n):
        n.held = False
        n.state = "hit"
        n.tail_ok = True
        n.hit_at = self.now
        self.score += HOLD_BONUS * self._mult()
        self.popups.append({"text": "HOLD", "sub": "", "x": self._lane_x(n.lane),
                            "y": C.HIT_Y - 70, "col": C.GREEN, "age": 0.0})
        if n in self.holds:
            self.holds.remove(n)
        audio.play("shield", 0.35)

    def _hold_break(self, n):
        n.held = False
        n.state = "broken"
        n.hit_at = self.now
        self.combo = 0
        self.popups.append({"text": "BREAK", "sub": "", "x": self._lane_x(n.lane),
                            "y": C.HIT_Y - 70, "col": C.RED_LIGHT, "age": 0.0})
        if n in self.holds:
            self.holds.remove(n)
        audio.play("hurt", 0.3)

    def _miss(self, n):
        n.state = "miss"
        n.grade = "miss"
        n.hit_at = self.now
        self.counts["miss"] += 1
        self.combo = 0
        self.hp -= 1
        self.popups.append({"text": GRADE_TEXT["miss"], "sub": "", "x": self._lane_x(n.lane),
                            "y": C.HIT_Y - 70, "col": C.RED_LIGHT, "age": 0.0})
        self.shake_t = 0.25
        audio.play("hurt", 0.5)
        if self.hp <= 0:
            self.failed = True
            self._finish()

    def _finish(self):
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

    def _draw(self, mouse):
        c = self.canvas
        now = self.now
        c.fill(EV.bg_at(self.bg_events, now))
        S.draw_grid(c, now * 0.04, self.energy_val * 0.8)

        self._draw_images(c, now)
        self._draw_lanes(c)
        self._draw_notes(c, now)
        self._draw_fx(c)
        self._draw_hud(c, now)
        if now < 0:
            self._draw_countdown(c, now)

        dx = random.randint(-4, 4) if self.shake_t > 0 else 0
        dy = random.randint(-2, 2) if self.shake_t > 0 else 0
        scr = self._screen()
        scr.blit(c, (dx, dy))
        glitch = max(self.shake_t / 0.25 if self.shake_t > 0 else 0.0, self._event_glitch(now))
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

    def _draw_images(self, c, now):
        for ev, surf in self.ev_active:
            if ev["type"] != "image":
                continue
            alpha, ox, oy = EV.image_state(ev, now - ev["t"])
            if alpha <= 0:
                continue
            surf.set_alpha(int(255 * alpha))
            c.blit(surf, (C.WIDTH // 2 + ox - surf.get_width() // 2,
                          C.HEIGHT // 2 + oy - surf.get_height() // 2))

    def _draw_lanes(self, c):
        for i in range(4):
            x = C.FIELD_X + i * (C.LANE_W + C.LANE_GAP)
            col = C.LANE_COLORS[i]
            band = cache.band(i)
            band.set_alpha(int(12 + 55 * self.glow[i]))
            c.blit(band, (x, 0))
            pygame.draw.line(c, _mix(C.GRID_COL, col, 0.35), (x, 0), (x, C.HEIGHT), 1)
            pygame.draw.line(c, _mix(C.GRID_COL, col, 0.35), (x + C.LANE_W, 0),
                             (x + C.LANE_W, C.HEIGHT), 1)

        pygame.draw.line(c, C.WHITE, (C.FIELD_X, C.HIT_Y), (C.FIELD_X + C.FIELD_W, C.HIT_Y), 2)
        for i in range(4):
            x = C.FIELD_X + i * (C.LANE_W + C.LANE_GAP)
            col = C.LANE_COLORS[i]
            k = self.glow[i]
            pad = pygame.Rect(x + 4, C.HIT_Y - 22, C.LANE_W - 8, 44)
            pygame.draw.rect(c, _lighten(_mix(C.BG_DARK, col, 0.25 + 0.5 * k), 0.2 * k),
                             pad, border_radius=8)
            pygame.draw.rect(c, _lighten(_mix(C.DIM, col, 0.6), 0.6 * k), pad, 2, border_radius=8)
            label = cache.text(18, True, settings.key_label(self.key_names[i]), col)
            c.blit(label, (x + C.LANE_W // 2 - label.get_width() // 2, C.HIT_Y + 40))

    def _draw_body(self, c, lane, y_head, y_tail, factor):
        top, bot = min(y_head, y_tail), max(y_head, y_tail)
        top, bot = max(-10, top), min(C.HEIGHT + 10, bot)
        if bot - top <= 0 or factor <= 0:
            return
        w = int(C.LANE_W * 0.42)
        x = self._lane_x(lane) - w // 2
        col = _mix(C.BG_DARK, C.LANE_COLORS[lane], 0.25 + 0.4 * factor)
        pygame.draw.rect(c, col, (x, top, w, bot - top), border_radius=6)
        pygame.draw.rect(c, _mix(C.BG_DARK, C.LANE_COLORS[lane], 0.7 * factor), (x, top, w, bot - top),
                         2, border_radius=6)

    def _draw_notes(self, c, now):
        speed = C.TRAVEL_PX / self.scroll
        for n in self.notes:
            lane = n.lane
            cx = self._lane_x(lane)
            if n.state == "wait":
                dt = n.t - now
                if dt > self.scroll + 120:
                    break
                y = C.HIT_Y - dt * speed
                if y < -40:
                    continue
                if n.dur > 0:
                    tail = C.HIT_Y - (n.end - now) * speed
                    self._draw_body(c, lane, y, tail, 0.8)
                alpha = int(255 * S.clamp((y + 40) / 110))
                self._blit_note(c, lane, cx, y, 1.0, alpha)
            elif n.state == "hold":
                tail = C.HIT_Y - (n.end - now) * speed
                self._draw_body(c, lane, C.HIT_Y, tail, 1.0 if n.held else 0.5)
                pulse = 1.0 + 0.04 * math.sin(now * 0.02) if n.held else 1.0
                self._blit_note(c, lane, cx, C.HIT_Y, pulse, 255)
            elif n.state == "hit":
                age = (now - n.hit_at) / 0.2
                if age >= 1:
                    continue
                e = S.ease_out_cubic(age)
                self._blit_note(c, lane, cx, C.HIT_Y, 1.0 + 0.7 * e, int(255 * (1 - age)))
            elif n.state == "broken":
                age = (now - n.hit_at) / 0.4
                if age >= 1:
                    continue
                self._draw_body(c, lane, C.HIT_Y, C.HIT_Y - 60 * age, 0.6 * (1 - age))
            else:
                age = (now - n.hit_at) / 0.35
                if age >= 1:
                    continue
                y = C.HIT_Y - (n.t - now) * speed + age * 40
                pygame.draw.rect(c, _mix(C.BG_DARK, C.DIM, 1 - age), (cx - 12, y - 12, 24, 24),
                                 border_radius=5)

    def _blit_note(self, c, lane, cx, y, scale, alpha):
        if alpha <= 0:
            return
        sprite = cache.note(lane, scale)
        sprite.set_alpha(alpha)
        c.blit(sprite, (cx - sprite.get_width() // 2, y - sprite.get_height() // 2))

    def _draw_fx(self, c):
        for rg in self.rings:
            e = S.ease_out_cubic(rg["age"] / rg["life"])
            rad = int((18 + 60 * e) * (1.35 if rg["big"] else 1.0))
            a = int(255 * (1 - e))
            if rad <= 0 or a <= 0:
                continue
            ring = cache.ring(rg["col"], rad)
            ring.set_alpha(a)
            c.blit(ring, (rg["x"] - ring.get_width() // 2, rg["y"] - ring.get_height() // 2))
        for p in self.parts:
            k = max(0.0, p["life"] / p["max"])
            col = _mix(C.BG_DARK, p["col"], k)
            pygame.draw.rect(c, col, (int(p["x"]) - 2, int(p["y"]) - 2, 4, 4))
        for p in self.popups:
            t = p["age"] / 0.7
            y = p["y"] - 40 * S.ease_out_cubic(t)
            a = int(255 * (1 - S.smoothstep(max(0.0, (t - 0.5) / 0.5))))
            if a <= 0:
                continue
            label = cache.text(22, True, p["text"], p["col"])
            label.set_alpha(a)
            c.blit(label, (p["x"] - label.get_width() // 2, y - label.get_height() // 2))
            if p["sub"]:
                sub = cache.text(14, False, p["sub"], C.GREY)
                sub.set_alpha(int(a * 0.8))
                c.blit(sub, (p["x"] - sub.get_width() // 2, y + 12))

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
        cx, cy = C.WIDTH // 2, C.HEIGHT // 2 - 40

        if gold:
            ring_r = int(30 + 260 * S.ease_out_cubic(k / 500.0))
            ring_a = 1 - S.clamp(k / 500.0)
            if ring_r > 0 and ring_a > 0:
                pygame.draw.circle(c, _mix(C.BG_DARK, C.GOLD, ring_a), (cx, cy), ring_r, 3)

        surf = cache.text(cache.COUNTDOWN_SIZE, True, word, col)
        dx = dy = 0
        if k < 350 and random.random() < 0.4:
            dx = random.randint(-6, 6)
            dy = random.randint(-2, 2)
            ghost = cache.text(cache.COUNTDOWN_SIZE, True, word, C.CYAN)
            ghost.set_alpha(110)
            c.blit(ghost, (cx - ghost.get_width() // 2 + dx + 4, cy - ghost.get_height() // 2 + dy))
        surf.set_alpha(alpha)
        c.blit(surf, (cx - surf.get_width() // 2 + dx, cy - surf.get_height() // 2 + dy))

    def _draw_hud(self, c, now):
        prog = S.clamp(now / max(1, self.duration))
        pygame.draw.rect(c, C.GRID_COL, (0, 0, C.WIDTH, 3))
        if prog > 0:
            pygame.draw.rect(c, C.CYAN, (0, 0, int(C.WIDTH * prog), 3))

        c.blit(S.font(14, True).render("HP", True, C.GREY), (20, 14))
        for i in range(C.MAX_HP):
            x = 60 + i * 26
            fill = S.clamp(self.hp_show - i)
            pygame.draw.rect(c, (40, 40, 60), (x, 14, 20, 14), border_radius=3)
            if fill > 0:
                col = C.GREEN if self.hp > 2 else C.RED
                pygame.draw.rect(c, col, (x, 14, int(20 * fill), 14), border_radius=3)
            pygame.draw.rect(c, (60, 60, 80), (x, 14, 20, 14), 1, border_radius=3)

        score_txt = S.font(22, True).render(f"{int(self.score_show):06d}", True, C.GOLD)
        c.blit(score_txt, (C.WIDTH - score_txt.get_width() - 20, 10))

        judged = sum(self.counts.values())
        acc = 100.0 * sum(self.counts[g] * ACC_WEIGHT[g] for g in self.counts) / max(1, judged)
        acc_txt = S.font(14).render(f"ТОЧНОСТЬ {acc:5.1f}%", True, C.GREY)
        c.blit(acc_txt, (C.WIDTH - acc_txt.get_width() - 20, 42))

        if self.combo >= 2:
            size = 22 + int(6 * self.combo_pop)
            combo_txt = S.font(size, True).render(f"COMBO x{self.combo}", True,
                                                  _lighten(C.PURPLE_LIGHT, 0.3 * self.combo_pop))
            c.blit(combo_txt, (C.WIDTH // 2 - combo_txt.get_width() // 2, 60))

        hint = cache.text(14, False, "ESC — пауза", (90, 90, 120))
        c.blit(hint, (C.WIDTH // 2 - hint.get_width() // 2, C.HEIGHT - 26))

    def _draw_pause(self, mouse):
        scr = self._screen()
        scr.blit(self.veil, (0, 0))
        S.glitch_title(scr, S.font(44, True), "ПАУЗА", C.CYAN, C.WIDTH // 2, 150,
                       self.frame % 200, length=40)
        self.resume_btn.draw(scr, mouse)
        self.menu_btn.draw(scr, mouse)
        S.blit_text(scr, S.font(14), "P / ESC — продолжить, M — в меню", C.GREY,
                    C.WIDTH // 2, 470)
