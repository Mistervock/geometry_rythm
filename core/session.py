"""Подготовка к игре: всё тяжёлое делается ДО старта песни, а не в игровом цикле.

prepare() читает и проверяет чарт, события и ресурсы, строит структуры для быстрого поиска по времени,
готовит картинки/ролики, замедленную дорожку для практики и музыку. Результат — Session: набор уже
готовых данных для Game. Во время игры Game не читает файлы, не разбирает JSON и не загружает ресурсы.

Фатальные проблемы (нет песни, чарт не проходит проверку, нет нот) → PrepError с понятным текстом.
Необязательное (нет картинки события, не читается ролик) → предупреждение, событие пропускается.
"""
import os
import sys
import time

import pygame

import audio
import config as C
import display
import events as EV
import settings
import songs
import stretch
import style as S
import validation as V
import screen_setting as SS
from i18n import t
from noteindex import NoteIndex


class PrepError(Exception):
    def __init__(self, title, lines=()):
        self.title = title
        self.lines = list(lines)
        super().__init__(title)


class Session:
    def __init__(self, chart):
        self.chart = chart
        self.practice = None            # PracticeConfig или None
        self.speed = 1.0
        self.notes = []
        self.index = None
        self.events = []                # события для игры (без bg и heal), отсортированы по времени
        self.bg_events = []
        self.heals = []
        self.duration = 0
        self.energy = []
        self.energy_fps = 21.5
        self.song_file = ""
        self.play_file = ""             # файл, который реально проигрывается (замедленный в практике)
        self.warnings = []
        self.timings = {}               # шаг → мс
        self.ghost = None
        self.scroll = float(settings.get("scroll_ms"))

    @property
    def total_ms(self):
        return sum(self.timings.values())

    def diagnostics(self):
        parts = ", ".join(f"{k} {v:.0f}" for k, v in self.timings.items())
        return f"prep {self.total_ms:.0f} мс ({parts}); нот {len(self.notes)}, событий {len(self.events)}"


STEP_LABELS = (
    ("chart", "Проверка чарта"),
    ("song", "Проверка песни"),
    ("build", "Построение структур"),
    ("media", "Картинки и ролики событий"),
    ("audio", "Подготовка звука"),
)


class Preparer:
    """Выполняет шаги подготовки по одному — экран между шагами успевает перерисоваться."""

    def __init__(self, chart, practice=None, ghost=None, notes=()):
        self.session = Session(chart)
        self.session.warnings.extend(notes)
        self.session.practice = practice
        self.session.speed = practice.speed if practice else 1.0
        self.session.ghost = ghost
        self.index = 0
        self.status = {k: "wait" for k, _ in STEP_LABELS}

    @property
    def finished(self):
        return self.index >= len(STEP_LABELS)

    def run_next(self):
        key = STEP_LABELS[self.index][0]
        self.status[key] = "run"
        t0 = time.perf_counter()
        try:
            getattr(self, "_" + key)(self.session)
        except PrepError:
            self.status[key] = "fail"
            raise
        self.session.timings[key] = (time.perf_counter() - t0) * 1000.0
        self.status[key] = "ok"
        self.index += 1

    def run_all(self):
        while not self.finished:
            self.run_next()
        return self.session

    #-- Шаги

    def _chart(self, s):
        ch = s.chart
        if not ch.notes:
            raise PrepError(t("В чарте нет нот"), [t("Откройте чарт в редакторе и добавьте ноты.")])
        _, rep = V.check_chart(ch.to_dict(for_hash=True), duration_ms=None, image_exists=songs._image_exists)
        lang = settings.get("lang")
        if not rep.ok:
            raise PrepError(t("Чарт не проходит проверку"), rep.lines(lang)[:12])
        for line in rep.lines(lang):
            if line:
                s.warnings.append(line)
        del s.warnings[12:]

    def _song(self, s):
        path = songs.song_path(s.chart.song)
        if not os.path.isfile(path):
            raise PrepError(t("Песня не найдена"), [f"songs/{s.chart.song}"])
        info = songs.info(s.chart.song)
        s.song_file = path
        s.duration = int(info.get("duration_ms") or 0)
        if s.duration <= 0:
            raise PrepError(t("Не удалось прочитать песню"), [f"songs/{s.chart.song}"])
        s.energy = info.get("energy") or []
        s.energy_fps = float(info.get("energy_fps") or 21.5)

    def _build(self, s):
        ch = s.chart
        s.notes = ch.copy_notes()
        s.notes.sort(key=lambda n: (n.t, n.lane))
        for i, n in enumerate(s.notes):
            n.idx = i
        s.index = NoteIndex(s.notes)
        s.bg_events = sorted((e for e in ch.events if e["type"] == "bg"), key=lambda e: e["t"])
        s.events = sorted((e for e in ch.events if e["type"] not in ("bg", "heal")), key=lambda e: e["t"])
        s.heals = sorted(({"t": e["t"], "lane": e["lane"] - 1, "fall": s.scroll * 100.0 / e["speed"]}
                          for e in ch.events if e["type"] == "heal"), key=lambda h: h["t"])
        if s.practice is not None:
            s.practice.fit(s.duration)

    def _media(self, s):
        keep = []
        for ev in s.events:
            kind, name = ev["type"], ev.get("file")
            if kind in ("image", "video"):
                if not name or not os.path.isfile(os.path.join(EV.IMAGE_DIR, name)):
                    s.warnings.append(f"{t('Нет файла события')}: {name or '—'} ({t('событие пропущено')})")
                    continue
                if kind == "video" and not EV.video.AVAILABLE:
                    s.warnings.append(f"{t('Ролики недоступны: установите opencv')} ({name})")
                    continue
            keep.append(ev)
        s.events = keep
        EV.prewarm(s.events)
        for ev in s.events:
            if ev["type"] == "image":
                w, h = EV.media_size(ev)
                EV.image_surface(ev["file"], w, EV.media_bright(), h)
            elif ev["type"] == "video":
                EV.natural_size(ev)

    def _audio(self, s):
        # Все скорости (и 1x) играют из одного полного декодирования: единая временная шкала звука
        path = stretch.playable(s.song_file, s.speed)
        if path is None:
            raise PrepError(t("Замедление недоступно"), [t("Установите numpy (pip install numpy).")])
        s.play_file = path
        if not pygame.mixer.get_init():
            s.warnings.append(t("Звук недоступен: игра пойдёт без музыки"))
            return
        audio.preload_song(s.play_file)
        if audio._music_path != s.play_file:
            raise PrepError(t("Не удалось загрузить песню"), [os.path.basename(s.play_file)])


def prepare(chart, practice=None, ghost=None, notes=()):
    """Без экрана (для тестов и скриптов)."""
    return Preparer(chart, practice, ghost, notes).run_all()


#-- Экран подготовки

def prep_screen(clock, chart, practice=None, ghost=None, notes=()):
    """Показывает ход подготовки. Возвращает Session или None (ошибка / отмена)."""
    prep = Preparer(chart, practice, ghost, notes)
    frame = 0
    error = None
    shown_warn_until = None
    while True:
        display.tick(clock)
        frame += 1
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if ev.type == pygame.KEYDOWN:
                if error is not None and ev.key in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_KP_ENTER,
                                                    pygame.K_SPACE):
                    return None
                if error is None and ev.key == pygame.K_ESCAPE:
                    return None
                if shown_warn_until is not None:
                    shown_warn_until = 0
        _draw(prep, frame, error, shown_warn_until)
        display.flip()
        if error is not None:
            continue
        if not prep.finished:
            try:
                prep.run_next()
            except PrepError as e:
                error = e
                _draw(prep, frame, error, None)
                display.flip()
            continue
        s = prep.session
        if s.warnings:
            if shown_warn_until is None:
                shown_warn_until = time.perf_counter() + 2.5
            if time.perf_counter() < shown_warn_until:
                continue
        print(f"[session] {s.diagnostics()}")
        return s


def _draw(prep, frame, error, warn_until):
    scr = pygame.display.get_surface()
    scr.fill((0, 0, 0))
    S.glitch_title(scr, S.font(34, True), t("ПОДГОТОВКА"), C.CYAN, C.WIDTH // 2, SS.U(120), min(60, frame * 3))
    y = SS.U(200)
    icons = {"wait": ("·", C.DIM), "run": ("…", C.CYAN), "ok": ("✓", C.GREEN), "fail": ("✗", C.RED_LIGHT)}
    for key, label in STEP_LABELS:
        st = prep.status[key]
        mark, col = icons[st]
        name = t(label)
        scr.blit(S.font(18, True).render(mark, True, col), (C.WIDTH // 2 - SS.U(220), y))
        scr.blit(S.font(18).render(name, True, C.WHITE if st != "wait" else C.GREY),
                 (C.WIDTH // 2 - SS.U(190), y))
        ms = prep.session.timings.get(key)
        if ms is not None:
            scr.blit(S.font(14).render(f"{ms:.0f} {t('мс')}", True, C.GREY), (C.WIDTH // 2 + SS.U(150), y + SS.U(3)))
        y += SS.U(36)
    done = sum(1 for v in prep.status.values() if v == "ok")
    bar = pygame.Rect(C.WIDTH // 2 - SS.U(220), y + SS.U(10), SS.U(440), SS.U(8))
    pygame.draw.rect(scr, C.GRID_COL, bar, border_radius=SS.U(3))
    pygame.draw.rect(scr, C.CYAN, (bar.x, bar.y, int(bar.w * done / len(STEP_LABELS)), bar.h),
                     border_radius=SS.U(3))
    y = bar.bottom + SS.U(30)
    if error is not None:
        S.blit_text(scr, S.font(20, True), error.title, C.RED_LIGHT, C.WIDTH // 2, y)
        for line in error.lines[:8]:
            y += SS.U(26)
            S.blit_text(scr, S.fit(S.font(14), line, SS.U(900)), line, C.GREY, C.WIDTH // 2, y)
        S.blit_text(scr, S.font(14), t("ESC / ENTER — назад"), C.GOLD, C.WIDTH // 2, SS.U(660))
    elif prep.session.warnings and warn_until is not None:
        S.blit_text(scr, S.font(16, True), t("Предупреждения"), C.GOLD, C.WIDTH // 2, y)
        for line in prep.session.warnings[:6]:
            y += SS.U(24)
            S.blit_text(scr, S.fit(S.font(13), line, SS.U(1000)), line, C.GREY, C.WIDTH // 2, y)
    S.post_fx(scr, frame, grain=30)
