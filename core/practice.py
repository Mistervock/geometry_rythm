"""Режим практики: настройки участка и экран выбора границ на таймлайне.

PracticeConfig хранит границы участка (мс чарта), скорость, повтор и опцию потери HP.
Результаты практики никогда не попадают в рекорды, ранги, победы и достижения за прохождение:
флаг practice в итогах проверяют все, кто их записывает (см. main.finish_run).
"""
import bisect
import sys

import pygame

import config as C
import display
import jsonio
import screen_setting as SS
import songs
import style as S
from i18n import t

SPEEDS = (0.5, 0.75, 0.9, 1.0)
MIN_LEN = 1000
PREROLL = 2000
PATH = C.root("data", "practice.json")
MAX_REMEMBERED = 200


class PracticeConfig:
    def __init__(self, a=0, b=0, speed=1.0, loop=True, hp_loss=False):
        self.a = int(a)
        self.b = int(b)
        self.speed = speed if speed in SPEEDS else 1.0
        self.loop = bool(loop)
        self.hp_loss = bool(hp_loss)

    def fit(self, duration):
        """Приводит границы к допустимым: 0 ≤ a < b ≤ duration, длина не меньше MIN_LEN."""
        duration = max(MIN_LEN, int(duration))
        self.a = max(0, min(self.a, duration - MIN_LEN))
        self.b = max(self.a + MIN_LEN, min(self.b if self.b > 0 else duration, duration))
        if self.b - self.a < MIN_LEN:
            self.a = max(0, self.b - MIN_LEN)
        return self

    @property
    def length(self):
        return self.b - self.a

    @property
    def start_time(self):
        """Куда ставить часы в начале каждого повтора (с разбегом перед участком)."""
        return self.a - PREROLL

    def to_dict(self):
        return {"a": self.a, "b": self.b, "speed": self.speed, "loop": self.loop, "hp_loss": self.hp_loss}

    @staticmethod
    def from_dict(d, duration):
        if not isinstance(d, dict):
            d = {}

        def num(key, default):
            v = d.get(key, default)
            return int(v) if isinstance(v, (int, float)) and not isinstance(v, bool) and v == v \
                and abs(v) < 1e12 else default
        speed = d.get("speed", 1.0)
        speed = float(speed) if isinstance(speed, (int, float)) and not isinstance(speed, bool) else 1.0
        return PracticeConfig(num("a", 0), num("b", duration), speed, d.get("loop", True) is not False,
                              d.get("hp_loss") is True).fit(duration)

    @staticmethod
    def default(duration):
        return PracticeConfig(0, duration).fit(duration)


def load_saved(chart, duration):
    key = chart.key or chart.id or chart.name
    data = jsonio.load(PATH, {}, expect=dict)
    return PracticeConfig.from_dict(data.get(key), duration) if key in data else PracticeConfig.default(duration)


def save_config(chart, cfg):
    key = chart.key or chart.id or chart.name
    data = jsonio.load(PATH, {}, expect=dict)
    data[key] = cfg.to_dict()
    while len(data) > MAX_REMEMBERED:
        data.pop(next(iter(data)))
    jsonio.try_write(PATH, data)


def fmt(ms):
    ms = max(0, int(ms))
    return f"{ms // 60000}:{(ms // 1000) % 60:02d}.{ms % 1000:03d}"


#-- Экран выбора участка

def setup_screen(clock, chart, duration, cfg=None, energy=None, energy_fps=21.5):
    """Возвращает PracticeConfig (старт) или None (назад)."""
    duration = max(MIN_LEN, int(duration))
    cfg = (cfg or load_saved(chart, duration)).fit(duration)
    notes_t = [n.t for n in chart.notes]
    sel = "a"
    drag = None
    frame = 0
    toast = ""
    tl = pygame.Rect(SS.UR(80, 220, 1120, 120))
    cols = max(1, tl.w // SS.U(3))
    dens = [0] * cols
    for n in chart.notes:
        dens[min(cols - 1, int(n.t / duration * cols))] += 1
    dmax = max(dens) or 1
    en = energy or []

    speed_btns = [S.Btn(SS.UR(380 + i * 130, 390, 120, 42), f"{int(v * 100)}%", C.GOLD, S.font(16, True))
                  for i, v in enumerate(SPEEDS)]
    loop_btn = S.Btn(SS.UR(380, 450, 250, 42), "", C.CYAN, S.font(15, True))
    hp_btn = S.Btn(SS.UR(650, 450, 250, 42), "", C.CYAN, S.font(15, True))
    start_btn = S.Btn(SS.UR(430, 560, 200, 52), t("СТАРТ"), C.GREEN, S.font(18, True))
    back_btn = S.Btn(SS.UR(650, 560, 200, 52), t("НАЗАД"), C.PURPLE_LIGHT, S.font(18, True))

    def x_of(ms):
        return tl.x + int(ms / duration * tl.w)

    def ms_of(x):
        return int(max(0, min(duration, (x - tl.x) / tl.w * duration)))

    def move(which, ms):
        ms = max(0, min(duration, int(ms)))
        if which == "a":
            cfg.a = max(0, min(ms, cfg.b - MIN_LEN))
        else:
            cfg.b = min(duration, max(ms, cfg.a + MIN_LEN))

    def nearest_marker(x):
        return "a" if abs(x - x_of(cfg.a)) <= abs(x - x_of(cfg.b)) else "b"

    def snap_note(ms, which):
        """Прилипание к ближайшей ноте (в пределах 150 мс): удобно начинать ровно с фразы."""
        if not notes_t:
            return ms
        i = bisect.bisect_left(notes_t, ms)
        best = min((notes_t[j] for j in (i - 1, i) if 0 <= j < len(notes_t)), key=lambda v: abs(v - ms))
        return best if abs(best - ms) <= 150 else ms

    while True:
        display.tick(clock)
        frame += 1
        mouse = pygame.mouse.get_pos()
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if ev.type == pygame.KEYDOWN:
                mods = pygame.key.get_mods()
                step = 1000 if mods & pygame.KMOD_SHIFT else 10 if mods & pygame.KMOD_CTRL else 250
                if ev.key == pygame.K_ESCAPE:
                    return None
                if ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                    save_config(chart, cfg)
                    return cfg
                if ev.key == pygame.K_a:
                    sel = "a"
                elif ev.key == pygame.K_b:
                    sel = "b"
                elif ev.key == pygame.K_TAB:
                    sel = "b" if sel == "a" else "a"
                elif ev.key == pygame.K_LEFT:
                    move(sel, (cfg.a if sel == "a" else cfg.b) - step)
                elif ev.key == pygame.K_RIGHT:
                    move(sel, (cfg.a if sel == "a" else cfg.b) + step)
                elif ev.key == pygame.K_HOME:
                    move("a", 0)
                elif ev.key == pygame.K_END:
                    move("b", duration)
                elif ev.key == pygame.K_l:
                    cfg.loop = not cfg.loop
                elif ev.key == pygame.K_h:
                    cfg.hp_loss = not cfg.hp_loss
                elif ev.key in (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4):
                    cfg.speed = SPEEDS[ev.key - pygame.K_1]
            elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                if tl.inflate(SS.U(20), SS.U(30)).collidepoint(ev.pos):
                    sel = nearest_marker(ev.pos[0])
                    drag = sel
                    move(sel, snap_note(ms_of(ev.pos[0]), sel))
                elif start_btn.rect.collidepoint(ev.pos):
                    save_config(chart, cfg)
                    return cfg
                elif back_btn.rect.collidepoint(ev.pos):
                    return None
                elif loop_btn.rect.collidepoint(ev.pos):
                    cfg.loop = not cfg.loop
                elif hp_btn.rect.collidepoint(ev.pos):
                    cfg.hp_loss = not cfg.hp_loss
                else:
                    for v, b in zip(SPEEDS, speed_btns):
                        if b.rect.collidepoint(ev.pos):
                            cfg.speed = v
            elif ev.type == pygame.MOUSEBUTTONUP and ev.button == 1:
                drag = None
            elif ev.type == pygame.MOUSEMOTION and drag:
                move(drag, snap_note(ms_of(ev.pos[0]), drag))
            elif ev.type == pygame.MOUSEWHEEL and tl.collidepoint(mouse):
                cur = cfg.a if sel == "a" else cfg.b
                move(sel, cur + ev.y * 250)

        scr = pygame.display.get_surface()
        scr.fill((0, 0, 0))
        S.glitch_title(scr, S.font(40, True), t("ПРАКТИКА"), C.CYAN, C.WIDTH // 2, SS.U(70), 60)
        name = f"{songs.display_title(chart.song)} — {chart.name}"
        S.blit_text(scr, S.fit(S.font(15), name, SS.U(900)), name, C.GREY, C.WIDTH // 2, SS.U(120))
        S.blit_text(scr, S.font(14), t("Результаты практики не попадают в рекорды и достижения"), C.GOLD,
                    C.WIDTH // 2, SS.U(150))

        S.panel(scr, tl.inflate(SS.U(20), SS.U(20)), C.CYAN, alpha=200)
        for i in range(cols):
            x = tl.x + i * tl.w // cols
            if en:
                ei = min(len(en) - 1, int((i + 0.5) / cols * duration / 1000.0 * energy_fps))
                h = max(1, int(tl.h * 0.55 * en[ei] / 100.0))
                pygame.draw.line(scr, (28, 40, 70), (x, tl.bottom), (x, tl.bottom - h), SS.U(2))
            if dens[i]:
                k = dens[i] / dmax
                col = tuple(int(C.GRID_COL[c] + (C.PURPLE_LIGHT[c] - C.GRID_COL[c]) * (0.3 + 0.7 * k))
                            for c in range(3))
                pygame.draw.line(scr, col, (x, tl.y + SS.U(6)), (x, tl.y + SS.U(6) + int(tl.h * 0.35 * k)),
                                 SS.U(2))
        ax, bx = x_of(cfg.a), x_of(cfg.b)
        shade = pygame.Surface((max(1, bx - ax), tl.h), pygame.SRCALPHA)
        shade.fill((80, 255, 160, 40))
        scr.blit(shade, (ax, tl.y))
        for which, x, col in (("a", ax, C.GREEN), ("b", bx, C.RED_LIGHT)):
            w = SS.U(3) if sel == which else SS.U(2)
            pygame.draw.line(scr, col, (x, tl.y - SS.U(12)), (x, tl.bottom + SS.U(12)), w)
            S.blit_text(scr, S.font(14, True), which.upper(), col, x, tl.y - SS.U(20))
        S.blit_text(scr, S.font(12), "0:00", C.GREY, tl.x, tl.bottom + SS.U(26))
        S.blit_text(scr, S.font(12), fmt(duration)[:-4], C.GREY, tl.right, tl.bottom + SS.U(26))

        in_sec = bisect.bisect_right(notes_t, cfg.b) - bisect.bisect_left(notes_t, cfg.a)
        line = (f"A  {fmt(cfg.a)}     B  {fmt(cfg.b)}     {t('длина')} {fmt(cfg.length)}     "
                f"{t('нот')}: {in_sec}")
        S.blit_text(scr, S.font(18, True), line, C.WHITE, C.WIDTH // 2, SS.U(372))

        S.blit_text(scr, S.font(13, True), t("СКОРОСТЬ"), (120, 160, 190), SS.U(330), SS.U(411))
        for v, b in zip(SPEEDS, speed_btns):
            b.color = C.GOLD if v == cfg.speed else C.DIM
            b.draw(scr, mouse, active=(v == cfg.speed))
        loop_btn.set_label(f"{t('ЦИКЛ')}: {t('ВКЛ') if cfg.loop else t('ВЫКЛ')}  (L)")
        hp_btn.set_label(f"{t('ПОТЕРЯ HP')}: {t('ВКЛ') if cfg.hp_loss else t('ВЫКЛ')}  (H)")
        loop_btn.color = C.GREEN if cfg.loop else C.DIM
        hp_btn.color = C.GREEN if cfg.hp_loss else C.DIM
        loop_btn.draw(scr, mouse)
        hp_btn.draw(scr, mouse)
        start_btn.draw(scr, mouse)
        back_btn.draw(scr, mouse)
        hint = t("A / B / Tab — маркер · ←→ ±0.25 с (Shift ±1 с, Ctrl ±10 мс) · мышь — тянуть · 1–4 скорость · ENTER старт")
        S.blit_text(scr, S.fit(S.font(13), hint, SS.U(1180)), hint, (110, 110, 150), C.WIDTH // 2, SS.U(660))
        if toast:
            S.blit_text(scr, S.font(14), toast, C.GOLD, C.WIDTH // 2, SS.U(520))
        S.post_fx(scr, frame, grain=30)
        display.flip()
