
#-- Импорт
import os
import sys
import time

import pygame

import audio
import autochart
import autosave as AS
import beatgrid as BG
import cache
import config as C
import dialogs
import display
import events
import events_screen
import history as H
import holdviz
import jsonio
import keymap
import screen_setting as SS
import settings
import song_settings
import songs
import stretch
import style as S
import validation as V
from chart import Note
from i18n import t
from noteindex import NoteIndex

SPEEDS = (0.5, 0.75, 1.0, 1.25)
ZOOM_MIN, ZOOM_MAX, ZOOM_STEP, ZOOM_DEFAULT = 0.05, 2.0, 1.25, 0.5
BAR_H = 12
PANEL_X = 940
MAX_HOLD = V.SOFT_HOLD
REC_HOLD_MS = 300
MIN_HOLD = 150
HIT_Y = C.HIT_Y
DRAG_PX = 4
SAVE_FLASH = 0.35
LINE_PRESETS = ((True, True, True, "ВСЕ"), (True, True, False, "ДОЛИ"), (False, True, False, "ТАКТЫ"),
                (False, False, False, "СКРЫТЬ"))


def help_lines():
    """Строки подсказки F1 по текущим привязкам клавиш."""
    k = keymap.label

    def pair(a, b):
        return f"{k(a)} {k(b)}"

    lane = " ".join(settings.key_label(n).upper() for n in settings.get("lane_keys"))
    return [
        (keymap.labels("play"), "играть / пауза"),
        (lane, "поставить ноту на дорожку"),
        ("ЛКМ · Shift+рамка", "нота / выделить рамкой"),
        ("ЛКМ-тяга", "переместить ноту, хвост — длительность"),
        (pair("seek_left", "seek_right"), "курсор (шаг сетки)"),
        (pair("zoom_in", "zoom_out"), "масштаб (Ctrl+колесо)"),
        (pair("to_start", "to_end"), "начало / конец"),
        (pair("back5", "fwd5"), "±5 с"),
        (pair("speed_down", "speed_up"), "скорость"),
        (pair("shift_left", "shift_right"), "сдвиг всех нот ±10 мс"),
        (k("snap"), "привязка к сетке вкл / выкл (Alt — разово)"),
        (k("grid_div"), "деление сетки"),
        (k("tap"), "тап-темп"),
        (pair("nudge_back", "nudge_fwd"), "двигать выделение"),
        (pair("lane_prev", "lane_next"), "выделение по дорожкам"),
        (k("quantize"), "привязать выделение к сетке"),
        (keymap.labels("delete_note"), "удалить ноту / выделение"),
        ("Ctrl+" + pair("undo", "redo"), "отмена / повтор"),
        ("Ctrl+" + pair("select_all", "copy") + " " + k("paste"), "выделить все / копировать / вставить"),
        ("Ctrl+" + k("save"), "сохранить"),
        (k("fx"), "эффекты вкл / выкл"),
        (k("rename"), "название чарта"),
        (k("menu"), "меню"),
        ("F1 · F3", "подсказка · FPS"),
    ]


def fmt_time(ms):
    ms = max(0, int(ms))
    return f"{ms // 60000}:{(ms // 1000) % 60:02d}.{ms % 1000:03d}"


def S_mix(a, b, k):
    return tuple(int(a[i] + (b[i] - a[i]) * k) for i in range(3))


def _notify(kind, **data):
    """Достижения не должны ронять редактор: ошибка логируется, работа продолжается."""
    try:
        import progress
        return progress.notify(kind, **data) or []
    except Exception as e:                       # noqa: BLE001 — намеренно: побочная функция
        print(f"[progress] {kind}: {e}")
        return []


class Editor:
    def __init__(self, clock, chart, recovery=None, autosave_dir=None):
        self.clock = clock
        self.chart = chart
        self.recovery = recovery
        self.song_path = songs.song_path(chart.song)
        info = songs.info(chart.song)
        self.duration = int(info.get("duration_ms") or (chart.notes[-1].t + 5000 if chart.notes else 60000))
        self.energy = info.get("energy") or []
        self.energy_fps = float(info.get("energy_fps") or 21.5)
        self.keys = settings.lane_keys()
        self.key_names = settings.get("lane_keys")

        self.hist = H.EditHistory(chart)
        self.hist.listeners.append(self._on_hist)
        self.grid = BG.BeatGrid(chart.grid)
        self.rev_local = 0
        self._index = None
        self._index_rev = -1
        self._ov = None
        self._ov_key = None
        self.sel = {}                        # id(нота) -> нота
        self.drag = None
        self.clip = []
        self.taps = []
        self.sclk = audio.SongClock()
        self.cursor = 0.0
        self.playing = False
        self.zoom = ZOOM_DEFAULT
        self.rec = [None] * 4
        self._wheel_last = 0.0
        self.flash = [0.0] * 4
        self.toast_text = ""
        self.toast_left = 0.0
        self.name_edit = False
        self.name_buf = chart.name
        self.menu_open = False
        self.menu_sel = 0
        self.frame = 0
        self.help_open = False
        self.save_error = ""
        self.saving = 0.0
        self.snapped_placed = 0
        self.report_orig_backup = bool(chart.report.lossy or chart.report.has_code("chart.migrated"))
        self.veil = pygame.Surface((C.WIDTH, C.HEIGHT), pygame.SRCALPHA)
        self.white = pygame.Surface((C.WIDTH, C.HEIGHT))
        self.white.fill(C.WHITE)
        self.fx_on = True
        self.veil.fill((0, 0, 0, 185))
        self.speed_i = SPEEDS.index(1.0)
        self.events_btn = S.Btn(SS.UR(PANEL_X, 110, 150, 40), t("СОБЫТИЯ"), C.CYAN, S.font(14, True))
        self.speed_btns = [S.Btn(SS.UR(PANEL_X, 186 + i * 40, 150, 34), f"{v:g}×", C.GOLD, S.font(14, True))
                           for i, v in enumerate(SPEEDS)]
        self.autosaver = AS.Autosaver(chart, directory=autosave_dir) if settings.get("autosave") else None
        self._important = False
        self._ext_rev = 0
        if chart.path is None or recovery is not None:
            self.hist.force_dirty = True
        self._build_menu()
        self._startup_notices()

    #-- Состояние и вспомогательные функции

    @property
    def dirty(self):
        return self.hist.dirty

    def _mark_dirty(self):
        """Правка вне истории (например, настройки песни): чарт считается изменённым."""
        self.hist.force_dirty = True
        self._ext_rev += 1

    @property
    def index(self):
        if self._index is None or self._index_rev != self.rev_local:
            self._index = NoteIndex(self.chart.notes)
            self._index_rev = self.rev_local
        return self._index

    def _touch(self):
        self.rev_local += 1

    def _on_hist(self, kind):
        self._touch()
        if self.sel:
            alive = {id(n) for n in self.chart.notes}
            self.sel = {k: n for k, n in self.sel.items() if k in alive}
        if kind in ("undo", "redo", "cancel", "clear"):
            self._sync_grid()

    def _sync_grid(self):
        flags = (self.grid.snap_on, self.grid.show_beats, self.grid.show_bars, self.grid.show_sub)
        self.grid.set_from(self.chart.grid)
        self.grid.snap_on, self.grid.show_beats, self.grid.show_bars, self.grid.show_sub = flags
        self.chart.grid = self.grid.to_dict()

    def _startup_notices(self):
        rep = self.chart.report
        lang = settings.get("lang")
        if self.recovery is not None:
            self._toast(f"{t('Восстановлено из автосохранения')}: {self.recovery.saved_at}", 6)
        elif rep.lossy:
            self._toast(f"{t('Часть записей чарта пропущена при загрузке')} "
                        f"({rep.dropped_notes} {t('нот')}, {rep.dropped_events} {t('событий')}). "
                        f"{t('Исходный файл сохранится в резервной копии')}", 8)
        elif not rep.ok or rep.sev_counts[V.WARNING]:
            self._toast(f"{t('Чарт загружен с предупреждениями')}: {rep.summary(lang)} — {t('меню → ПРОВЕРКА ЧАРТА')}", 6)

    @property
    def speed(self):
        return SPEEDS[self.speed_i]

    @property
    def zoom_px(self):
        return self.zoom * SS.SCALE

    def time_to_y(self, tm):
        return HIT_Y - (tm - self.cursor) * self.zoom_px

    def y_to_time(self, y):
        return self.cursor + (HIT_Y - y) / self.zoom_px

    def _free_mod(self):
        return bool(pygame.key.get_mods() & pygame.KMOD_ALT)

    def place(self, tm):
        return self.grid.place(tm, free=self._free_mod())

    def _toast(self, text, sec=2.5):
        self.toast_text = text
        self.toast_left = sec

    def _exec(self, cmd, important=False):
        ok = self.hist.execute(cmd)
        if ok and important:
            self._important = True
        return ok

    def nearest(self, tm, lane=None, limit=250):
        return self.index.nearest(tm, lane, limit)

    #-- Операции над нотами

    def add_note(self, tm, lane, dur=0, free=False):
        tm = max(0, int(round(tm)))
        if self.index.nearest(tm, lane, 0) is not None:       # единственный запрет: точная копия на дорожке
            self._toast(t("Здесь уже есть нота"), 1.0)
            return None
        note = Note(tm, lane, dur)
        self._exec(H.AddNotes([note]))
        self.flash[lane] = 1.0
        if self.grid.snap_on and self.grid.mode == "beat" and not free:
            self.snapped_placed += 1
        return note

    def delete_notes(self, notes):
        notes = list(notes)
        if notes:
            self._exec(H.RemoveNotes(notes))
            for n in notes:
                self.sel.pop(id(n), None)

    def _selected(self):
        return list(self.sel.values())

    def _set_selection(self, notes):
        self.sel = {id(n): n for n in notes}

    def _modify(self, notes, fn, label, coalesce=None):
        """Применяет fn(note) -> (t, lane, dur) к нотам как одну запись истории."""
        changes = []
        for n in notes:
            new = fn(n)
            if new is not None and tuple(new) != n.key():
                changes.append((n, n.key(), new))
        if not changes:
            return False
        return self._exec(H.ModifyNotes(changes, label=label, coalesce=coalesce))

    def _shift(self, ms):
        self._modify(self.chart.notes, lambda n: (max(0, n.t + ms), n.lane, n.dur), "Сдвиг всех нот",
                     coalesce="shift")
        self._toast(f"{t('Сдвиг всех нот')}: {ms:+d} {t('мс')}")

    def _nudge(self, direction):
        notes = self._selected()
        if not notes:
            self._toast(t("Нет выделенных нот"), 1.2)
            return
        shift = pygame.key.get_mods() & pygame.KMOD_SHIFT
        if self.grid.snap_on and not self._free_mod():
            fn = lambda n: (max(0, BG.round_ms(self.grid.step_from(n.t, direction))), n.lane, n.dur)
        else:
            step = 1 if shift else 10
            fn = lambda n: (max(0, n.t + direction * step), n.lane, n.dur)
        self._modify(notes, fn, "Сдвиг выделенных нот", coalesce=("nudge", tuple(id(n) for n in notes)))

    def _move_lanes(self, direction):
        notes = self._selected()
        if not notes:
            self._toast(t("Нет выделенных нот"), 1.2)
            return
        lo, hi = min(n.lane for n in notes), max(n.lane for n in notes)
        if (direction < 0 and lo == 0) or (direction > 0 and hi == 3):
            return
        self._modify(notes, lambda n: (n.t, n.lane + direction, n.dur), "Смена дорожки")

    def _quantize(self):
        notes = self._selected() or list(self.chart.notes)
        changes = BG.snap_changes(notes, self.grid)
        if not changes:
            self._toast(t("Все ноты уже на сетке"), 1.5)
            return
        self._exec(H.ModifyNotes(changes, label="Привязка к сетке"), important=True)
        self._toast(f"{t('Привязано нот')}: {len(changes)}")

    def _copy(self):
        notes = sorted(self._selected(), key=lambda n: (n.t, n.lane))
        if not notes:
            self._toast(t("Нет выделенных нот"), 1.2)
            return
        t0 = notes[0].t
        self.clip = [(n.t - t0, n.lane, n.dur) for n in notes]
        self._toast(f"{t('Скопировано нот')}: {len(notes)}", 1.5)

    def _paste(self):
        if not self.clip:
            self._toast(t("Буфер пуст"), 1.2)
            return
        base = self.place(self.cursor)
        fresh, taken = [], set()
        for dt, lane, dur in self.clip:
            tm = base + dt
            if (tm, lane) in taken or self.index.nearest(tm, lane, 0) is not None:
                continue
            taken.add((tm, lane))
            fresh.append(Note(tm, lane, dur))
        if not fresh:
            self._toast(t("Нечего вставлять: ноты уже есть"), 1.5)
            return
        self._exec(H.AddNotes(fresh), important=True)
        self._set_selection(fresh)
        self._toast(f"{t('Вставлено нот')}: {len(fresh)}", 1.5)

    def _tap_tempo(self):
        now = time.perf_counter()
        if self.taps and now - self.taps[-1] > 2.0:
            self.taps = []
        self.taps.append(now)
        self.taps = self.taps[-9:]
        if len(self.taps) >= 3:
            bpm = 60.0 / ((self.taps[-1] - self.taps[0]) / (len(self.taps) - 1))
            self._grid_edit(lambda: self.grid.set_bpm(bpm), "BPM", coalesce="grid")
            self._toast(f"BPM ≈ {self.grid.bpm:.1f}", 1.2)
        else:
            self._toast(t("Тап-темп: нажимайте в такт"), 1.0)

    #-- Сетка

    def _grid_edit(self, fn, label, coalesce=None):
        before = H.SetMeta.snapshot(self.chart)
        fn()
        self.chart.grid = self.grid.to_dict()
        after = H.SetMeta.snapshot(self.chart)
        self.hist.execute(H.SetMeta(before, after, label=label, coalesce=coalesce))
        self._touch()

    def _grid_flag(self, fn):
        """Параметры вида (привязка, линии) не считаются правкой чарта и не делают его «изменённым»."""
        fn()
        self.chart.grid = self.grid.to_dict()

    def _toggle_snap(self):
        self._grid_flag(lambda: setattr(self.grid, "snap_on", not self.grid.snap_on))
        self._toast(f"{t('Привязка к сетке')}: {t('ВКЛ') if self.grid.snap_on else t('ВЫКЛ')}")

    def _ask_number(self, title, current, maxlen=8):
        value = dialogs.ask_text(self.clock, title, str(current), maxlen=maxlen)
        if value is None:
            return None
        try:
            v = float(value.replace(",", "."))
        except ValueError:
            self._toast(t("Нужно число"), 1.5)
            return None
        return v if v == v and abs(v) != float("inf") else None

    def _grid_row_action(self, key, direction, typed=False):
        g = self.grid
        shift = bool(pygame.key.get_mods() & pygame.KMOD_SHIFT)
        if key == "snap":
            self._toggle_snap()
        elif key == "bpm":
            if typed:
                v = self._ask_number("BPM", f"{g.bpm:g}")
                if v is not None:
                    self._grid_edit(lambda: g.set_bpm(v), "BPM", coalesce="grid")
            else:
                step = 0.1 if shift else 1.0
                self._grid_edit(lambda: g.set_bpm(g.bpm + direction * step), "BPM", coalesce="grid")
        elif key == "offset":
            if typed:
                v = self._ask_number(t("Смещение ритма, мс"), f"{g.offset:g}")
                if v is not None:
                    self._grid_edit(lambda: g.set_offset(v), "Смещение сетки", coalesce="grid")
            else:
                step = 1 if shift else 10
                self._grid_edit(lambda: g.set_offset(g.offset + direction * step), "Смещение сетки",
                                coalesce="grid")
        elif key == "div":
            if typed:
                v = self._ask_number(t("Делений на долю (1–192)"), g.div, 4)
                if v is not None:
                    self._grid_edit(lambda: g.set_spec(("beat", int(v))), "Деление сетки")
            else:
                self._grid_edit(lambda: g.cycle(direction), "Деление сетки")
        elif key == "bar":
            self._grid_edit(lambda: setattr(g, "bar", max(1, min(16, g.bar + direction))), "Размер такта",
                            coalesce="grid")
        elif key == "origin":
            self._grid_edit(lambda: g.set_offset(self.cursor), "Начало ритма")
            self._toast(f"{t('Начало ритма')}: {fmt_time(self.cursor)}", 1.5)
        elif key == "lines":
            cur = next((i for i, p in enumerate(LINE_PRESETS)
                        if p[:3] == (g.show_beats, g.show_bars, g.show_sub)), 0)
            p = LINE_PRESETS[(cur + (direction or 1)) % len(LINE_PRESETS)]
            self._grid_flag(lambda: (setattr(g, "show_beats", p[0]), setattr(g, "show_bars", p[1]),
                                     setattr(g, "show_sub", p[2])))

    def _grid_rows(self):
        g = self.grid
        lines = next((p[3] for p in LINE_PRESETS if p[:3] == (g.show_beats, g.show_bars, g.show_sub)), "ВСЕ")
        data = [("snap", "ПРИВЯЗКА", t("ВКЛ") if g.snap_on else t("ВЫКЛ")),
                ("bpm", "BPM", f"{g.bpm:g}"),
                ("offset", "СМЕЩЕНИЕ", f"{g.offset:g} {t('мс')}"),
                ("div", "ДЕЛЕНИЕ", g.label()),
                ("bar", "ДОЛЕЙ В ТАКТЕ", str(g.bar)),
                ("lines", "ЛИНИИ", t(lines)),
                ("origin", "НАЧАЛО ← КУРСОР", "")]
        rows = []
        for i, (key, label, value) in enumerate(data):
            rows.append((key, label, value, SS.UR(PANEL_X, 372 + i * 40, 150, 35)))
        return rows

    #-- Звук и перемотка

    def _now(self):
        return self.sclk.now() * self.speed

    def _audio_path(self):
        path = stretch.playable(self.song_path, self.speed)
        if path is None:
            self.speed_i = SPEEDS.index(1.0)
            self._toast(t("Замедление недоступно: установите numpy"))
            return stretch.playable(self.song_path, 1.0)
        return path

    def _start_audio(self, ms):
        at = ms / self.speed
        audio.play_song(self._audio_path(), at)
        self.sclk.start(at)

    def _seek(self, ms):
        self.cursor = max(0.0, min(float(self.duration), ms))
        if self.playing:
            self._start_audio(self.cursor)

    def _step_cursor(self, direction, big=False):
        if big:
            self._seek(self.cursor + direction * 1000)
        elif self.grid.snap_on:
            self._seek(BG.round_ms(self.grid.step_from(self.cursor, direction)))
        else:
            self._seek(self.cursor + direction * 10)

    def _set_speed(self, i):
        if i == self.speed_i:
            return
        self.speed_i = i
        if self.speed != 1.0:
            self._toast(t("Готовлю замедление…") if self.speed < 1 else t("Готовлю ускорение…"), 60)
            self._draw((0, 0))
            display.flip()
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
            n.dur = min(MAX_HOLD, length)           # нота принадлежит последней записи «добавить», она её же и вернёт
            self._ext_rev += 1
            self._touch()

    #-- Сохранение

    def save_state(self):
        if self.saving > 0:
            return "saving"
        if self.save_error:
            return "error"
        return "dirty" if self.dirty else "saved"

    def _save(self):
        if not self.chart.name.strip():
            self.chart.name = "Чарт"
        self.saving = SAVE_FLASH
        self._draw((0, 0))
        display.flip()
        had_path = self.chart.path is not None
        try:
            if had_path and self.report_orig_backup:
                stem = os.path.splitext(os.path.basename(self.chart.path))[0]
                jsonio.backup_file(self.chart.path, os.path.join(songs.BACKUP_DIR, stem + "_original"),
                                   keep=3, tag=".original")
            self.chart.path = self.chart.path or None
            songs.save_chart(self.chart)
        except jsonio.SaveError as e:
            self.saving = 0.0
            self.save_error = str(e)
            self._toast(f"{t('ОШИБКА СОХРАНЕНИЯ')}: {e}", 6)
            return False
        self.saving = SAVE_FLASH
        self.save_error = ""
        self.report_orig_backup = False
        self.chart.report.lossy = False
        self.hist.mark_saved()
        if self.autosaver is not None:
            self.autosaver.clear()
            self.autosaver.retarget()
        if self.recovery is not None:
            AS.discard(self.recovery)
            self.recovery = None
        self._toast(t("Сохранено"))
        for line in _notify("chart_saved", chart=self.chart, snapped_notes=self.snapped_placed, new=not had_path):
            self._toast(line, 4)
        return True

    def _auto(self):
        if not autochart.AVAILABLE:
            self._toast(t("Авто-разметка недоступна: установите numpy"))
            return
        choice = dialogs.choose(self.clock, t("Плотность авто-разметки"),
                                [t("Лёгкая (мало нот)"), t("Средняя"), t("Сложная (много нот)"), t("Отмена")])
        if choice is None or choice == 3:
            return
        preset = ("easy", "normal", "hard")[choice]
        self._toast(t("Анализ песни…"), 60)
        self._draw((0, 0))
        display.flip()
        res = autochart.build(self.song_path, preset)
        if res is None:
            self._toast(t("Не удалось проанализировать песню"))
            return
        before = list(self.chart.notes)
        after = [Note(*item) for item in res["notes"]]
        self._exec(H.ReplaceNotes(before, after), important=True)
        self.sel.clear()
        self._toast(f"{t('Авто-разметка')}: {t('нот')} {len(res['notes'])}")

    def _undo(self):
        cmd = self.hist.undo()
        self._toast(f"{t('Отмена')}: {t(cmd.label)}" if cmd else t("Нечего отменять"))

    def _redo(self):
        cmd = self.hist.redo()
        self._toast(f"{t('Повтор')}: {t(cmd.label)}" if cmd else t("Нечего повторять"))

    def _emergency_autosave(self):
        if self.autosaver is not None and self.dirty:
            try:
                self.autosaver.save(self.hist.rev + self._ext_rev, "emergency", wait=True)
            except Exception as e:                   # noqa: BLE001
                print(f"[autosave] emergency: {e}")

    def _maybe_autosave(self):
        a = self.autosaver
        if a is None or not self.dirty or self.playing or self.drag is not None:
            return
        rev = self.hist.rev + self._ext_rev
        a.note_change(rev)
        if a.due(rev, important=self._important):
            self._important = False
            a.save(rev, "timer")

    #-- Меню

    def _build_menu(self):
        labels = [("continue", t("ПРОДОЛЖИТЬ")), ("save", t("СОХРАНИТЬ")),
                  ("save_exit", t("СОХРАНИТЬ И ВЫЙТИ")),
                  ("check", t("ПРОВЕРКА ЧАРТА")),
                  ("song", t("НАСТРОЙКИ ПЕСНИ")),
                  ("achievements", t("ДОСТИЖЕНИЯ")),
                  ("export", t("ЭКСПОРТ ЧАРТА")),
                  ("import", t("ИМПОРТ ЧАРТА")),
                  ("auto", t("АВТО-РАЗМЕТКА (ЗАМЕНИТ НОТЫ)")),
                  ("exit", t("ВЫЙТИ БЕЗ СОХРАНЕНИЯ"))]
        self.menu_items = labels
        self.menu_btns = [S.Btn(SS.UR(SS.REF_W // 2 - 210, 140 + i * 50, 420, 42), text, C.CYAN,
                                S.font(16, True)) for i, (_, text) in enumerate(labels)]

    def _menu_action(self, action):
        if action == "continue":
            self.menu_open = False
        elif action == "save":
            self._save()
        elif action == "save_exit":
            if self._save():
                return "back"
        elif action == "check":
            self.menu_open = False
            self._check_report()
        elif action == "achievements":
            self.menu_open = False
            import achievement_editor
            achievement_editor.run(self.clock)
        elif action == "song":
            self.menu_open = False
            before = H.SetMeta.snapshot(self.chart)
            if song_settings.run(self.clock, self.chart):
                after = H.SetMeta.snapshot(self.chart)
                if before != after:
                    self.hist.execute(H.SetMeta(before, after, label="Свойства чарта"))
                self._mark_dirty()
                self._toast(t("Настройки песни изменены — не забудьте сохранить"), 3)
        elif action == "auto":
            self.menu_open = False
            self._auto()
        elif action == "export":
            self.menu_open = False
            try:
                path = songs.export_chart(self.chart)
                self._toast(f"{t('Экспортировано')}: {os.path.relpath(path, C.ROOT_DIR)}", 4)
                for line in _notify("chart_exported", chart=self.chart):
                    self._toast(line, 4)
            except jsonio.SaveError as e:
                self._toast(f"{t('Экспорт не удался')}: {e}", 5)
        elif action == "import":
            self.menu_open = False
            self._import()
        elif action == "exit":
            if self.dirty:
                if not dialogs.confirm(self.clock, t("Есть несохранённые изменения. Выйти без сохранения? "
                                                      "Автосохранение будет удалено."),
                                       yes=t("ВЫЙТИ"), no=t("ОСТАТЬСЯ")):
                    return None
            self._discard_autosave()
            return "back"
        return None

    def _discard_autosave(self):
        if self.autosaver is not None:
            self.autosaver.clear()
        if self.recovery is not None:
            AS.ignore(self.autosaver.directory if self.autosaver else AS.default_dir(), self.recovery)

    def _check_report(self):
        lang = settings.get("lang")
        _, rep = V.check_chart(self.chart.to_dict(for_hash=True), duration_ms=self.duration,
                               image_exists=songs._image_exists)
        lines = [rep.summary(lang), ""] + rep.lines(lang)
        if self.chart.report.lossy:
            lines += ["", t("При загрузке часть записей была пропущена; исходный файл будет сохранён "
                             "в data/backups/charts при первом сохранении.")]
        if rep.clean and len(lines) <= 2:
            lines = [t("Проблем не найдено."), rep.summary(lang)]
        dialogs.info_lines(self.clock, t("ПРОВЕРКА ЧАРТА"), lines, footer="ESC")

    def _import(self):
        files = songs.export_files()
        if not files:
            self._toast(t("В папке exports/ нет файлов для импорта"), 3)
            return
        idx = dialogs.choose(self.clock, t("Импорт чарта из exports/"), files[:8])
        if idx is None:
            return
        try:
            ch = songs.import_chart(files[idx])
        except songs.ImportFailure as e:
            reason = {"no_song": t("песня из чарта не найдена в songs/"),
                      "newer_version": t("чарт создан в более новой версии игры"),
                      "bad_format": t("чарт не проходит проверку")}.get(e.reason, t("файл не читается"))
            self._toast(f"{t('Импорт не удался')}: {reason}", 5)
            if e.report is not None:
                dialogs.info_lines(self.clock, t("ИМПОРТ НЕ УДАЛСЯ"),
                                   e.report.lines(settings.get("lang")) or [reason])
            return
        except jsonio.SaveError as e:
            self._toast(f"{t('Импорт не удался')}: {e}", 5)
            return
        self._toast(f"{t('Импортирован')}: {ch.name} — {t('откройте его из списка песен')}", 4)

    #-- Цикл

    def run(self):
        try:
            return self._loop()
        except Exception:
            self._emergency_autosave()
            raise

    def _loop(self):
        while True:
            dt = min(0.05, display.tick(self.clock) / 1000.0)
            mouse = pygame.mouse.get_pos()
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    self._stop_play()
                    self._emergency_autosave()
                    pygame.quit()
                    sys.exit()
                res = self._event(ev, mouse)
                if res is not None:
                    self._stop_play()
                    if self.autosaver is not None:
                        self.autosaver.flush()
                    return res
            self._tick(dt)
            self._maybe_autosave()
            self._draw(mouse)
            display.flip()
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
        if self.saving > 0:
            self.saving = max(0.0, self.saving - dt)

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
            if self.help_open or self.name_edit:
                return None
            return self._click(ev)
        if ev.type == pygame.MOUSEBUTTONUP and ev.button == 1:
            self._finish_drag()
            return None
        if ev.type == pygame.MOUSEMOTION and not self.menu_open:
            self._motion(ev)
            return None
        if ev.type == pygame.MOUSEWHEEL and not self.menu_open:
            self._wheel(ev)
        return None

    def _wheel(self, ev):
        mods = pygame.key.get_mods()
        mx, my = pygame.mouse.get_pos()
        for key, _, _, rect in self._grid_rows():
            if rect.collidepoint((mx, my)) and key not in ("origin",):
                self._grid_row_action(key, 1 if ev.y > 0 else -1)
                return
        if mods & pygame.KMOD_CTRL:
            self._zoom_by(ZOOM_STEP ** ev.y)
            return
        if self._wheel_note(ev.y, (mx, my)):
            return
        step = max(self.grid.step_ms if self.grid.snap_on else 10.0, 8.0 / self.zoom_px)
        self._seek(self.cursor - ev.y * step * (3 if mods & pygame.KMOD_SHIFT else 1))

    def _zoom_by(self, k):
        self.zoom = max(ZOOM_MIN, min(ZOOM_MAX, self.zoom * k))

    def _lane_at(self, x):
        rel = x - C.FIELD_X
        if rel < 0 or rel >= C.FIELD_W:
            return None
        lane = rel // (C.LANE_W + C.LANE_GAP)
        if rel - lane * (C.LANE_W + C.LANE_GAP) >= C.LANE_W:
            return None
        return int(lane)

    def _hit_test(self, x, y):
        """Нота под курсором: (нота, 'head' | 'tail') или (None, None)."""
        lane = self._lane_at(x)
        if lane is None:
            return None, None
        tm = self.y_to_time(y)
        span = 40 / self.zoom_px
        best = None
        for n in self.index.visible(tm - span, tm + span + 1):
            if n.lane != lane:
                continue
            yh, yt = self.time_to_y(n.t), self.time_to_y(n.end)
            if n.dur and abs(y - yt) <= SS.U(10) and yt < yh - SS.U(16):
                return n, "tail"
            d = abs(y - yh)
            if d <= SS.U(16) or (n.dur and yt - SS.U(4) <= y <= yh + SS.U(4)):
                if best is None or d < best[0]:
                    best = (d, n)
        return (best[1], "head") if best else (None, None)

    def _wheel_note(self, direction, pos=None):
        mx, my = pos or pygame.mouse.get_pos()
        n, _ = self._hit_test(mx, my)
        if n is None:
            return False
        mods = pygame.key.get_mods()
        step = self.grid.step_ms if self.grid.snap_on and not self._free_mod() else 10.0
        step = max(1, BG.round_ms(step * (5 if mods & pygame.KMOD_SHIFT else 1)))
        if n.dur == 0 and direction > 0:
            new = MIN_HOLD
        else:
            new = n.dur + direction * step
            if new < MIN_HOLD:
                new = 0
        new = int(max(0, min(MAX_HOLD, new)))
        self._modify([n], lambda x: (x.t, x.lane, new), "Длительность удержания", coalesce=("hold", id(n)))
        self._toast(f"{t('Удержание')}: {new} {t('мс')}" if new else t("Обычная нота"), 1.0)
        return True

    def _key(self, ev):
        k = ev.key
        mods = pygame.key.get_mods()
        ctrl = mods & pygame.KMOD_CTRL

        if self.name_edit:
            if k in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_ESCAPE) or keymap.hit("rename", k):
                self._commit_name()
            elif k == pygame.K_BACKSPACE:
                self.name_buf = self.name_buf[:-1]
            elif ev.unicode and ev.unicode.isprintable() and len(self.name_buf) < V.NAME_MAX:
                self.name_buf += ev.unicode
            return None

        if self.help_open:
            self.help_open = False
            return None
        if k == pygame.K_F1:
            self.help_open = True
            return None

        if self.menu_open:
            if keymap.hit("back", k):
                self.menu_open = False
            elif keymap.hit("up", k):
                self.menu_sel = (self.menu_sel - 1) % len(self.menu_items)
            elif keymap.hit("down", k):
                self.menu_sel = (self.menu_sel + 1) % len(self.menu_items)
            elif keymap.hit("confirm", k):
                return self._menu_action(self.menu_items[self.menu_sel][0])
            return None

        if keymap.hit("menu", k):
            self.menu_open = True
            self.menu_sel = 0
            return None
        if ctrl:
            return self._ctrl_key(k, mods)
        if keymap.hit("play", k):
            self._toggle_play()
            return None
        shift = bool(mods & pygame.KMOD_SHIFT)
        if keymap.hit("seek_left", k):
            self._step_cursor(-1, shift)
        elif keymap.hit("seek_right", k):
            self._step_cursor(1, shift)
        elif keymap.hit("zoom_in", k):
            self._zoom_by(ZOOM_STEP)
        elif keymap.hit("zoom_out", k):
            self._zoom_by(1 / ZOOM_STEP)
        elif keymap.hit("to_start", k):
            self._seek(0)
        elif keymap.hit("to_end", k):
            self._seek(self.duration)
        elif keymap.hit("back5", k):
            self._seek(self.cursor - (30000 if shift else 5000))
        elif keymap.hit("fwd5", k):
            self._seek(self.cursor + (30000 if shift else 5000))
        elif keymap.hit("speed_down", k):
            self._set_speed(max(0, self.speed_i - 1))
        elif keymap.hit("speed_up", k):
            self._set_speed(min(len(SPEEDS) - 1, self.speed_i + 1))
        elif keymap.hit("fx", k):
            self.fx_on = not self.fx_on
            self._toast(t("Эффекты событий в редакторе: ") + (t("ВКЛ") if self.fx_on else t("ВЫКЛ")))
        elif keymap.hit("snap", k):
            self._toggle_snap()
        elif keymap.hit("grid_div", k):
            self._grid_row_action("div", -1 if shift else 1)
            self._toast(f"{t('Деление')}: {self.grid.label()}", 1.2)
        elif keymap.hit("tap", k):
            self._tap_tempo()
        elif keymap.hit("shift_left", k):
            self._shift(-10)
        elif keymap.hit("shift_right", k):
            self._shift(10)
        elif keymap.hit("nudge_back", k):
            self._nudge(-1)
        elif keymap.hit("nudge_fwd", k):
            self._nudge(1)
        elif keymap.hit("lane_prev", k):
            self._move_lanes(-1)
        elif keymap.hit("lane_next", k):
            self._move_lanes(1)
        elif keymap.hit("quantize", k):
            self._quantize()
        elif keymap.hit("deselect", k):
            self.sel.clear()
        elif keymap.hit("rename", k):
            self.name_edit = True
            self.name_buf = self.chart.name
        elif keymap.hit("delete_note", k):
            if self.sel:
                n = len(self.sel)
                self.delete_notes(self._selected())
                self._toast(f"{t('Удалено нот')}: {n}")
            else:
                ref = self._now() if self.playing else self.cursor
                n = self.nearest(ref, limit=200)
                if n is not None:
                    self.delete_notes([n])
                    self._toast(t("Нота удалена"))
        elif k in self.keys:
            lane = self.keys.index(k)
            if self.playing:
                self.rec[lane] = self.add_note(self._now(), lane, free=True)
            else:
                self.add_note(self.place(self.cursor), lane, free=self._free_mod())
        return None

    def _ctrl_key(self, k, mods):
        if keymap.hit("save", k):
            self._save()
        elif keymap.hit("undo", k):
            if mods & pygame.KMOD_SHIFT:
                self._redo()
            else:
                self._undo()
        elif keymap.hit("redo", k):
            self._redo()
        elif keymap.hit("select_all", k):
            self._set_selection(self.chart.notes)
            self._toast(f"{t('Выделено нот')}: {len(self.sel)}", 1.2)
        elif keymap.hit("copy", k):
            self._copy()
        elif keymap.hit("paste", k):
            self._paste()
        return None

    def _commit_name(self):
        new = (self.name_buf.strip() or "Чарт")[:V.NAME_MAX]
        self.name_edit = False
        if new != self.chart.name:
            before = H.SetMeta.snapshot(self.chart)
            self.chart.name = new
            self.hist.execute(H.SetMeta(before, H.SetMeta.snapshot(self.chart), label="Название чарта"))

    #-- Мышь

    def _click(self, ev):
        x, y = ev.pos
        if y < SS.U(BAR_H) + SS.U(2):
            self.drag = {"mode": "seek"}
            self._seek(x / C.WIDTH * self.duration)
            return None
        if x >= SS.U(PANEL_X):
            return self._panel_click(ev)
        lane = self._lane_at(x)
        if lane is None or y < 0 or y > C.HEIGHT - SS.U(60):
            return None
        tm = self.y_to_time(y)
        mods = pygame.key.get_mods()
        if ev.button == 3:
            n, _ = self._hit_test(x, y)
            if n is None:
                n = self.nearest(tm, lane=lane, limit=max(120, int(2 * self.grid.step_ms)))
            if n is not None:
                self.delete_notes([n])
                self._toast(t("Нота удалена"))
            return None
        if ev.button != 1:
            return None
        n, part = self._hit_test(x, y)
        if n is not None and not self.playing:
            if mods & pygame.KMOD_SHIFT and part == "head":
                if id(n) in self.sel:
                    self.sel.pop(id(n))
                else:
                    self.sel[id(n)] = n
                return None
            if id(n) not in self.sel:
                self._set_selection([n])
            if part == "tail":
                self.drag = {"mode": "tail", "note": n, "orig": n.key(), "moved": False}
            else:
                group = self._selected()
                self.drag = {"mode": "move", "primary": n, "start": (x, y), "moved": False,
                             "orig": {m: m.key() for m in group}, "grab": tm - n.t}
            return None
        if mods & pygame.KMOD_SHIFT and not self.playing:
            self.drag = {"mode": "box", "start": (x, y), "end": (x, y)}
            return None
        self.sel.clear()
        self.add_note(tm if self.playing else self.place(tm), lane, free=self.playing or self._free_mod())
        return None

    def _panel_click(self, ev):
        if ev.button != 1:
            return None
        if self.events_btn.rect.collidepoint(ev.pos):
            self._open_events()
            return None
        for i, btn in enumerate(self.speed_btns):
            if btn.rect.collidepoint(ev.pos):
                self._set_speed(i)
                return None
        for key, _, _, rect in self._grid_rows():
            if rect.collidepoint(ev.pos):
                third = rect.w // 4
                if key in ("snap", "origin"):
                    self._grid_row_action(key, 1)
                elif ev.pos[0] < rect.x + third:
                    self._grid_row_action(key, -1)
                elif ev.pos[0] > rect.right - third:
                    self._grid_row_action(key, 1)
                elif key in ("bpm", "offset", "div"):
                    self._grid_row_action(key, 0, typed=True)
                else:
                    self._grid_row_action(key, 1)
                return None
        return None

    def _open_events(self):
        before = H.SetEvents.snapshot(self.chart)
        events_screen.run(self.clock, self.chart, self.cursor, self.duration)
        after = H.SetEvents.snapshot(self.chart)
        if before != after:
            self.hist.execute(H.SetEvents(before, after))
            self._important = True

    def _motion(self, ev):
        d = self.drag
        if d is None:
            return
        x, y = ev.pos
        if d["mode"] == "seek":
            self._seek(x / C.WIDTH * self.duration)
        elif d["mode"] == "box":
            d["end"] = (x, y)
        elif d["mode"] == "tail":
            n = d["note"]
            end = self.place(self.y_to_time(y))
            dur = max(0, end - n.t)
            if dur < MIN_HOLD:
                dur = 0
            d["moved"] = True
            n.dur = int(min(MAX_HOLD, dur))
            self._touch()
        elif d["mode"] == "move":
            if not d["moved"] and abs(x - d["start"][0]) < SS.U(DRAG_PX) and abs(y - d["start"][1]) < SS.U(DRAG_PX):
                return
            d["moved"] = True
            primary = d["primary"]
            t0, l0, _ = d["orig"][primary]
            lane = self._lane_at(x)
            if lane is None:
                lane = max(0, min(3, int((x - C.FIELD_X) // (C.LANE_W + C.LANE_GAP))))
            new_t = self.place(self.y_to_time(y) - d["grab"])
            dt, dl = new_t - t0, lane - l0
            lanes = [v[1] for v in d["orig"].values()]
            dl = max(-min(lanes), min(3 - max(lanes), dl))
            dt = max(dt, -min(v[0] for v in d["orig"].values()))
            for n, (nt, nl, nd) in d["orig"].items():
                n.t, n.lane = nt + dt, nl + dl
            self.chart.sort()
            self._touch()

    def _finish_drag(self):
        d, self.drag = self.drag, None
        if d is None:
            return
        if d["mode"] == "box":
            self._box_select(d)
        elif d["mode"] == "tail":
            n = d["note"]
            new = n.key()
            n.t, n.lane, n.dur = d["orig"]
            if d["moved"]:
                self._modify([n], lambda x: new, "Длительность удержания")
                self._toast(f"{t('Удержание')}: {new[2]} {t('мс')}" if new[2] else t("Обычная нота"), 1.0)
            self._touch()
        elif d["mode"] == "move" and d["moved"]:
            final = {n: n.key() for n in d["orig"]}
            for n, old in d["orig"].items():
                n.t, n.lane, n.dur = old
            self.chart.sort()
            moving = set(final)
            taken = {(v[0], v[1]) for v in final.values()}
            clash = len(taken) < len(final) or any(
                m not in moving and (m.t, m.lane) in taken for m in self.chart.notes)
            if clash:
                self._toast(t("Нельзя поставить ноту точно поверх другой"), 2)
            else:
                self._modify(list(final), lambda n: final[n], "Перемещение нот")
            self._touch()

    def _box_select(self, d):
        (x0, y0), (x1, y1) = d["start"], d["end"]
        rect = pygame.Rect(min(x0, x1), min(y0, y1), abs(x1 - x0), abs(y1 - y0))
        if rect.w < SS.U(3) and rect.h < SS.U(3):
            return
        lanes = {i for i in range(4)
                 if pygame.Rect(C.FIELD_X + i * (C.LANE_W + C.LANE_GAP), 0, C.LANE_W, C.HEIGHT).colliderect(rect)}
        t_lo, t_hi = self.y_to_time(rect.bottom), self.y_to_time(rect.top)
        picked = self.index.in_range(t_lo, t_hi, lanes)
        if pygame.key.get_mods() & pygame.KMOD_CTRL:
            picked = list(self.sel.values()) + picked
        self._set_selection(picked)
        self._toast(f"{t('Выделено нот')}: {len(self.sel)}", 1.2)

    #-- Отрисовка

    def _lane_x(self, lane):
        return C.FIELD_X + lane * (C.LANE_W + C.LANE_GAP) + C.LANE_W // 2

    def _draw_grid_lines(self, scr, t_bot, t_top):
        g = self.grid
        zp = self.zoom_px
        step_px = g.step_ms * zp
        beat_px = g.beat_ms * zp if g.mode == "beat" else 1e9
        x0, x1 = C.FIELD_X - SS.U(14), C.FIELD_X + C.FIELD_W + SS.U(14)
        for tm, kind in g.lines(t_bot - 20, t_top + 20):
            if kind == BG.SUB and step_px < 5:
                continue
            if kind == BG.BEAT and beat_px < 5:
                continue
            y = int(self.time_to_y(tm))
            if kind == BG.BAR:
                pygame.draw.line(scr, (86, 86, 150), (x0 - SS.U(14), y), (x1 + SS.U(14), y), SS.U(2))
                if beat_px * g.bar > 34:
                    num = int(round(g.beat_number(tm) / g.bar)) + 1
                    scr.blit(cache.text(12, True, str(num), (130, 130, 190)), (x1 + SS.U(18), y - SS.U(8)))
            elif kind == BG.BEAT:
                pygame.draw.line(scr, (66, 66, 124), (x0, y), (x1, y), SS.U(1))
            else:
                pygame.draw.line(scr, (44, 44, 80), (x0 + SS.U(14), y), (x1 - SS.U(14), y), 1)

    def _draw(self, mouse):
        scr = pygame.display.get_surface()
        scr.fill(events.bg_at(self.chart.events, self.cursor))
        S.draw_grid(scr, (self.cursor * 0.04) % 60, 0.0)
        glitch_lvl, flash_lvl, images, cards, invert_lvl = events.active_fx(self.chart.events, self.cursor) \
            if self.fx_on else (0.0, 0.0, [], [], 0.0)
        events.draw_images(scr, images)

        for i in range(4):
            x = C.FIELD_X + i * (C.LANE_W + C.LANE_GAP)
            col = C.LANE_COLORS[i]
            band = cache.band(i)
            band.set_alpha(int(12 + 50 * self.flash[i]))
            scr.blit(band, (x, 0))
            pygame.draw.line(scr, S_mix(C.GRID_COL, col, 0.35), (x, 0), (x, C.HEIGHT), SS.U(1))
            pygame.draw.line(scr, S_mix(C.GRID_COL, col, 0.35), (x + C.LANE_W, 0),
                             (x + C.LANE_W, C.HEIGHT), SS.U(1))

        t_top = self.y_to_time(0)
        t_bot = self.y_to_time(C.HEIGHT)
        self._draw_grid_lines(scr, t_bot, t_top)
        for sec in range(max(0, int(t_bot // 1000)), int(t_top // 1000) + 2):
            y = self.time_to_y(sec * 1000)
            pygame.draw.line(scr, (38, 38, 70), (C.FIELD_X - SS.U(30), y), (C.FIELD_X + C.FIELD_W + SS.U(30), y), SS.U(1))
            S.blit_text(scr, S.font(14), fmt_time(sec * 1000)[:-4], (90, 90, 130), SS.U(24), y, 255)

        pygame.draw.line(scr, C.WHITE, (C.FIELD_X, HIT_Y), (C.FIELD_X + C.FIELD_W, HIT_Y), SS.U(2))
        for i in range(4):
            x = C.FIELD_X + i * (C.LANE_W + C.LANE_GAP)
            pad = pygame.Rect(x + SS.U(4), HIT_Y - SS.U(22), C.LANE_W - SS.U(8), SS.U(44))
            pygame.draw.rect(scr, S_mix(C.BG_DARK, C.LANE_COLORS[i], 0.2 + 0.5 * self.flash[i]),
                             pad, border_radius=SS.U(8))
            pygame.draw.rect(scr, S_mix(C.DIM, C.LANE_COLORS[i], 0.6), pad, SS.U(2), border_radius=SS.U(8))
            label = cache.text(16, True, settings.key_label(self.key_names[i]), C.LANE_COLORS[i])
            scr.blit(label, (self._lane_x(i) - label.get_width() // 2, HIT_Y + SS.U(34)))

        self._draw_notes(scr, t_bot, t_top)
        self._draw_heals(scr)
        events.draw_cards(scr, cards)
        self._draw_events(scr)
        self._draw_hover(scr, mouse)
        self._draw_box(scr)
        self._draw_overview(scr)
        self._draw_panel(scr, mouse)
        self._draw_hud(scr)
        if self.toast_left > 0 and self.toast_text:
            alpha = 255 * min(1.0, self.toast_left / 0.6)
            S.blit_text(scr, S.fit(S.font(16, True), self.toast_text, C.WIDTH - SS.U(40)), self.toast_text,
                        C.GOLD, C.WIDTH // 2, SS.U(78), alpha)

        events.apply_invert(scr, invert_lvl)
        if glitch_lvl > 0:
            S.glitch(scr, strength=glitch_lvl)
        if flash_lvl > 0:
            self.white.set_alpha(int(255 * 0.85 * flash_lvl))
            scr.blit(self.white, (0, 0))

        if self.name_edit:
            box = SS.UR(SS.REF_W // 2 - 210, 300, 420, 60)
            S.panel(scr, box, C.CYAN, alpha=230)
            S.blit_text(scr, S.font(14, True), t("НАЗВАНИЕ ЧАРТА — ENTER"), C.CYAN, C.WIDTH // 2, SS.U(290))
            shown = self.name_buf + ("|" if (self.frame // 30) % 2 == 0 else " ")
            S.blit_text(scr, S.font(20, True), shown, C.WHITE, C.WIDTH // 2, SS.U(328))

        if self.menu_open:
            scr.blit(self.veil, (0, 0))
            S.glitch_title(scr, S.font(36, True), t("РЕДАКТОР"), C.CYAN, C.WIDTH // 2, SS.U(90), 60)
            for i, btn in enumerate(self.menu_btns):
                disabled = self.menu_items[i][0] == "auto" and not autochart.AVAILABLE
                btn.color = C.DIM if disabled else C.CYAN
                btn.draw(scr, mouse, active=(i == self.menu_sel))
            S.blit_text(scr, S.font(14), t("ESC — закрыть меню"), C.GREY, C.WIDTH // 2, SS.U(676))

        if self.help_open:
            self._draw_help(scr)

        S.post_fx(scr, self.frame, grain=20)

    def _draw_notes(self, scr, t_bot, t_top):
        margin = 60 / self.zoom_px
        sprite = cache.note
        for n in self.index.visible(t_bot - margin, t_top + margin):
            y = self.time_to_y(n.t)
            selected = id(n) in self.sel
            if n.dur > 0:
                tail = self.time_to_y(n.end)
                holdviz.draw_body(scr, n.lane, self._lane_x(n.lane), y, tail,
                                  0.45 if not selected else 0.62, 0.7 if not selected else 1.0)
            if y < -SS.U(40) or y > C.HEIGHT + SS.U(40):
                continue
            spr = sprite(n.lane, 1.0)
            yi = holdviz.snap_y(y)
            scr.blit(spr, (self._lane_x(n.lane) - spr.get_width() // 2, yi - spr.get_height() // 2))
            if selected:
                pygame.draw.circle(scr, C.WHITE, (self._lane_x(n.lane), yi), spr.get_width() // 2 - SS.U(2), SS.U(2))

    def _draw_hover(self, scr, mouse):
        if self.menu_open or self.playing or self.drag is not None or self.name_edit or self.help_open:
            return
        lane = self._lane_at(mouse[0])
        if lane is None or mouse[1] > C.HEIGHT - SS.U(60) or mouse[1] < SS.U(BAR_H + 4):
            return
        tm = self.place(self.y_to_time(mouse[1]))
        y = holdviz.snap_y(self.time_to_y(tm))
        x = C.FIELD_X + lane * (C.LANE_W + C.LANE_GAP)
        col = C.LANE_COLORS[lane]
        pygame.draw.line(scr, S_mix(C.BG_DARK, col, 0.8), (x, y), (x + C.LANE_W, y), SS.U(2))
        S.blit_text(scr, S.font(12), f"{fmt_time(tm)}" + ("" if self.grid.snap_on and not self._free_mod()
                                                          else "  ·"), (170, 170, 200),
                    x + C.LANE_W + SS.U(60), y)

    def _draw_box(self, scr):
        d = self.drag
        if d is None or d["mode"] != "box":
            return
        (x0, y0), (x1, y1) = d["start"], d["end"]
        rect = pygame.Rect(min(x0, x1), min(y0, y1), abs(x1 - x0), abs(y1 - y0))
        veil = pygame.Surface(rect.size, pygame.SRCALPHA)
        veil.fill((80, 220, 255, 40))
        scr.blit(veil, rect.topleft)
        pygame.draw.rect(scr, C.CYAN, rect, SS.U(1))

    def _draw_help(self, scr):
        scr.blit(self.veil, (0, 0))
        box = SS.UR(SS.REF_W // 2 - 340, 40, 680, 650)
        S.panel(scr, box, C.CYAN, alpha=235)
        S.blit_text(scr, S.font(22, True), t("ГОРЯЧИЕ КЛАВИШИ"), C.CYAN, C.WIDTH // 2, SS.U(70))
        for i, (keys, what) in enumerate(help_lines()):
            y = SS.U(98 + i * 23)
            scr.blit(S.font(14, True).render(keys, True, C.GOLD), (box.x + SS.U(30), y))
            scr.blit(S.font(14).render(t(what), True, C.WHITE), (box.x + SS.U(270), y))
        S.blit_text(scr, S.font(13), t("Нажмите любую клавишу, чтобы закрыть"), C.GREY,
                    C.WIDTH // 2, SS.U(676))

    def _draw_heals(self, scr):
        for ev in self.chart.events:
            if ev["type"] != "heal":
                continue
            lane = ev["lane"] - 1
            x = self._lane_x(lane)
            y = self.time_to_y(ev["t"])
            if -SS.U(40) <= y <= C.HEIGHT + SS.U(40):
                pygame.draw.circle(scr, C.LANE_COLORS[lane], (x, int(y)), SS.U(19), SS.U(2))
                pygame.draw.circle(scr, C.WHITE, (x, int(y)), SS.U(15))

    def _draw_panel(self, scr, mouse):
        if self.menu_open:
            return
        self.events_btn.draw(scr, mouse)
        scr.blit(S.font(12, True).render(t("СКОРОСТЬ"), True, (120, 160, 190)), SS.UP(PANEL_X, 168))
        for i, btn in enumerate(self.speed_btns):
            btn.color = C.GOLD if i == self.speed_i else C.DIM
            btn.draw(scr, mouse, active=(i == self.speed_i))
        scr.blit(S.font(12, True).render(t("BPM-СЕТКА"), True, (120, 160, 190)), SS.UP(PANEL_X, 352))
        for key, label, value, rect in self._grid_rows():
            hov = rect.collidepoint(mouse)
            on = key == "snap" and self.grid.snap_on
            pygame.draw.rect(scr, (34, 34, 68) if hov else (14, 14, 30), rect, border_radius=SS.U(5))
            pygame.draw.rect(scr, C.GREEN if on else (C.GOLD if hov else C.DIM), rect, SS.U(2),
                             border_radius=SS.U(5))
            lab = S.fit(S.font(11, True), t(label), rect.w - SS.U(14)).render(t(label), True, (150, 170, 200))
            if value:
                scr.blit(lab, (rect.x + SS.U(8), rect.y + SS.U(2)))
                val = S.font(14, True).render(value, True, C.WHITE if hov else (210, 210, 230))
                scr.blit(val, (rect.centerx - val.get_width() // 2, rect.y + SS.U(16)))
                if hov and key not in ("snap", "lines"):
                    scr.blit(S.font(14, True).render("‹", True, C.GOLD), (rect.x + SS.U(4), rect.y + SS.U(13)))
                    scr.blit(S.font(14, True).render("›", True, C.GOLD), (rect.right - SS.U(12), rect.y + SS.U(13)))
            else:
                lab = S.font(12, True).render(t(label), True, C.WHITE if hov else (190, 190, 210))
                scr.blit(lab, (rect.centerx - lab.get_width() // 2, rect.centery - lab.get_height() // 2))

    def _draw_events(self, scr):
        if self.playing:
            return
        grey, line_col, edge = (150, 150, 165), (80, 80, 92), (220, 220, 230)
        x = C.FIELD_X + C.FIELD_W + SS.U(36)
        for ev in self.chart.events:
            y = self.time_to_y(ev["t"])
            y_end = self.time_to_y(ev["t"] + events.total_ms(ev))
            lo, hi = min(y, y_end), max(y, y_end)
            if hi < -SS.U(20) or lo > C.HEIGHT + SS.U(20):
                continue
            top, bot = max(0, lo), min(C.HEIGHT, hi)
            if bot > top:
                pygame.draw.line(scr, line_col, (x, top), (x, bot), SS.U(3))
            if 0 <= y <= C.HEIGHT:
                d = SS.U(8)
                pts = [(x, y - d), (x + d, y), (x, y + d), (x - d, y)]
                pygame.draw.polygon(scr, grey, pts)
                pygame.draw.polygon(scr, edge, pts, SS.U(1))
                label = cache.text(12, True, t(events.TYPE_NAMES[ev["type"]]), grey)
                scr.blit(label, (x + SS.U(14), y - label.get_height() // 2))

    def _overview_surface(self):
        key = (self.rev_local, C.WIDTH, self.duration, len(self.chart.events))
        if self._ov_key != key:
            surf = pygame.Surface((C.WIDTH, SS.U(BAR_H)))
            surf.fill((30, 30, 50))
            dur = max(1, self.duration)
            for n in self.chart.notes:
                x = int(n.t / dur * C.WIDTH)
                pygame.draw.line(surf, C.LANE_COLORS[n.lane], (x, 0), (x, SS.U(BAR_H)), SS.U(1))
            self._ov, self._ov_key = surf, key
        return self._ov

    def _draw_overview(self, scr):
        base = self._overview_surface()
        scr.blit(base, (0, 0))
        prog = self.cursor / max(1, self.duration)
        x = int(C.WIDTH * prog)
        pygame.draw.rect(scr, C.CYAN, (0, 0, x, SS.U(3)))
        pygame.draw.line(scr, C.WHITE, (x, 0), (x, SS.U(BAR_H)), SS.U(2))
        if not self.playing:
            for ev in self.chart.events:
                ex = int(ev["t"] / max(1, self.duration) * C.WIDTH)
                pygame.draw.rect(scr, events.TYPE_COLORS[ev["type"]], (ex - SS.U(1), SS.U(BAR_H + 2), SS.U(3), SS.U(6)))

    def _draw_hud(self, scr):
        status = "▶" if self.playing else "❚❚"
        left = f"{status}  {fmt_time(self.cursor)} / {fmt_time(self.duration)}"
        scr.blit(S.font(16, True).render(left, True, C.WHITE), SS.UP(14, 16))
        name = f"{songs.display_title(self.chart.song)} — {self.chart.name}"
        name_surf = S.font(14).render(name, True, C.GREY)
        scr.blit(name_surf, SS.UP(14, 40))
        self._draw_status(scr, SS.U(14) + name_surf.get_width() + SS.U(12), SS.U(40))
        g = self.grid
        snap_txt = f"{g.label()} {t('ВКЛ') if g.snap_on else t('ВЫКЛ')}"
        info = (f"{t('нот')}: {len(self.chart.notes)}   {t('сетка')}: {snap_txt}   BPM {g.bpm:g}   "
                f"{t('масштаб')}: {self.zoom:.2f}   V {t('эффекты')}: {t('ВКЛ') if self.fx_on else t('ВЫКЛ')}")
        info_surf = S.font(14).render(info, True, C.GREY)
        scr.blit(info_surf, (C.WIDTH - info_surf.get_width() - SS.U(14), SS.U(16)))
        if self.sel:
            sel_txt = S.font(13, True).render(f"{t('выделено')}: {len(self.sel)}", True, C.CYAN)
            scr.blit(sel_txt, (C.WIDTH - sel_txt.get_width() - SS.U(14), SS.U(36)))
        a = self.autosaver
        if a is not None:
            if a.state == "saving":
                txt, col = t("авто: сохранение…"), C.CYAN
            elif a.state == "error":
                txt, col = f"{t('авто: ошибка')} — {a.error}"[:70], C.RED_LIGHT
            elif a.last_saved_at:
                txt, col = f"{t('авто')} {time.strftime('%H:%M:%S', time.localtime(a.last_saved_at))}", (90, 130, 110)
            else:
                txt, col = "", C.GREY
            if txt:
                scr.blit(S.font(12).render(txt, True, col), SS.UP(14, 60))
        hint = t("SPACE играть · ←→ курсор · PgUp/PgDn ±5 с · -/= скорость · G привязка · H деление · Del удалить · F1 помощь")
        h = S.font(14).render(hint, True, (110, 110, 150))
        scr.blit(h, (C.WIDTH // 2 - h.get_width() // 2, C.HEIGHT - SS.U(22)))

    def _draw_status(self, scr, x, y):
        state = self.save_state()
        label, col = {"saved": (t("СОХРАНЕНО"), C.GREEN), "dirty": (t("НЕ СОХРАНЕНО"), C.GOLD),
                      "saving": (t("СОХРАНЕНИЕ…"), C.CYAN), "error": (t("ОШИБКА СОХРАНЕНИЯ"), C.RED_LIGHT)}[state]
        txt = S.font(12, True).render(label, True, col if state != "saved" else (20, 40, 20))
        pad = SS.U(7)
        rect = pygame.Rect(x, y - SS.U(1), txt.get_width() + pad * 2, txt.get_height() + SS.U(4))
        if state == "saved":
            pygame.draw.rect(scr, C.GREEN, rect, border_radius=SS.U(4))
        else:
            pygame.draw.rect(scr, (14, 14, 30), rect, border_radius=SS.U(4))
            pygame.draw.rect(scr, col, rect, SS.U(2), border_radius=SS.U(4))
        scr.blit(txt, (rect.x + pad, rect.y + SS.U(2)))
