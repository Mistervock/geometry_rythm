#-- Импорт
import sys
import time

import pygame

import config as C
import events as EV
import style as S
import video
from i18n import t

#-- Раскладка
ROW1_Y, ROW2_Y, ROW3_Y, BTN_H = 54, 96, 138, 32
LIST_X, LIST_Y, ROW, LIST_W = 16, 182, 26, 290
PANEL_X = 320
FIELD_Y, FIELD_STEP = 184, 26
MAX_T_SHOWN = 10
PREVIEW_BG_MS = 1500
PREVIEW_PAUSE_MS = 500
HOLD_DELAY = 0.35
HOLD_RATE = 0.06
NO_EDIT = ("file", "anim", "orig")

#-- Разделы кнопок
SECTIONS = (
    ("ДОБАВИТЬ", ROW1_Y, (("glitch", "+ ГЛЮК"), ("flash", "+ ВСПЫШКА"),
                         ("image", "+ КАРТИНКА"), ("video", "+ ВИДЕО"), ("bg", "+ ФОН"))),
    ("ПРАВКА", ROW2_Y, (("copy", "КОПИРОВАТЬ"), ("paste", "ВСТАВИТЬ"), ("paste_all", "ВСЕМ ТАКИМ"),
                       ("dup", "ДУБЛИРОВАТЬ"), ("delete", "УДАЛИТЬ"))),
    ("ВИД", ROW3_Y, (("preview", "▶ ПРОСМОТР"), ("cursor", "В КУРСОР"), ("fit", "ПОДОГНАТЬ"), ("back", "НАЗАД"))),
)

#-- Подсказки полей
HINTS = {
    "t": "Когда начинается событие, мс от начала песни (стрелки — шаг 10 мс, Shift — 50 мс)",
    "dur": "Сколько длится эффект, мс. Клик по числу — ввести, колесо мыши — изменить, держите +/− — быстрее",
    "strength": "Сила глюка: 10% слабый, 100% сильный",
    "attack": "За сколько мс вспышка доходит до полной яркости",
    "fade": "За сколько мс картинка или фон появляются и исчезают",
    "w": "Ширина в пикселях (у картинки высота считается по пропорциям)",
    "h": "Высота ролика в пикселях, ширина и высота меняются независимо",
    "x": "Сдвиг картинки от центра экрана по горизонтали",
    "y": "Сдвиг картинки от центра экрана по вертикали",
    "dx": "На сколько картинка сместится за время показа (для ДВИЖЕНИЯ)",
    "dy": "На сколько картинка сместится по вертикали (для ДВИЖЕНИЯ)",
    "file": "Файл из папки images/, стрелки перебирают список",
    "anim": "РЕЗКО — появилась и пропала; ПЛАВНО — с затуханием; ДВИЖЕНИЕ — плывёт",
    "r": "Красная составляющая фона, 0–255",
    "g": "Зелёная составляющая фона, 0–255",
    "b": "Синяя составляющая фона, 0–255",
    "orig": "ДА — вернуть исходный цвет фона; ручное изменение цвета выключает это",
}


#-- Форматирование времени
def _fmt(ms):
    ms = max(0, int(ms))
    return f"{ms // 60000}:{(ms // 1000) % 60:02d}.{ms % 1000:03d}"


#-- Экран событий
class EventsScreen:
    def __init__(self, clock, chart, cursor_ms, duration):
        self.clock = clock
        self.chart = chart
        self.cursor = int(cursor_ms)
        self.duration = int(duration)
        self.cur = chart.events[0] if chart.events else None
        self.field = 0
        self.top = 0
        self.frame = 0
        self.status = ""
        self.edit_key = None
        self.edit_buf = ""
        self.edit_fresh = False
        self.hold = None
        self.clip = None
        self.preview_ev = None
        self.preview_t0 = None
        self.white = pygame.Surface((C.WIDTH, C.HEIGHT))
        self.white.fill(C.WHITE)
        self.buttons = []
        self.section_labels = []
        for label, row_y, items in SECTIONS:
            self.section_labels.append((label, row_y))
            for i, (name, text) in enumerate(items):
                rect = (100 + i * 124, row_y, 118, BTN_H)
                self.buttons.append((name, S.Btn(rect, t(text), C.CYAN, S.font(12, True))))

    #-- Данные

    def _sort(self):
        self.chart.events.sort(key=lambda e: e["t"])

    def _fields(self):
        ev = self.cur
        if ev is None:
            return []
        rows = [("t", t("Время, мс"), 0, self.duration, 10)]
        rows += [(k, lbl, lo, hi, st) for k, lbl, lo, hi, st, _ in EV.FIELDS[ev["type"]]]
        if ev["type"] in ("image", "video"):
            rows += [("file", t("Ролик (images/)") if ev["type"] == "video" else t("Картинка (images/)"), None, None, None),
                     ("anim", t("Анимация"), None, None, None)]
        if ev["type"] == "bg":
            rows += [("orig", t("Исходный цвет фона"), None, None, None)]
        return rows

    def _value_text(self, key):
        ev = self.cur
        if key == "file":
            return ev["file"] or t("нет файлов в images/")
        if key == "anim":
            return t(EV.ANIM_NAMES[ev["anim"]])
        if key == "orig":
            return t("ДА") if ev["orig"] else t("НЕТ")
        if key == "t":
            return _fmt(ev["t"])
        return str(ev[key])

    def _adjust(self, key, lo, hi, step, direction):
        ev = self.cur
        if ev is None:
            return
        if key == "file":
            ev["file"] = EV.cycle(EV.list_media(ev["type"]), ev["file"], direction)
        elif key == "anim":
            ev["anim"] = EV.cycle(EV.ANIMS, ev["anim"], direction)
        elif key == "orig":
            ev["orig"] = not ev["orig"]
        else:
            self._set_value(key, ev[key] + direction * step, lo, hi)

    def _set_value(self, key, value, lo, hi):
        ev = self.cur
        ev[key] = max(lo, min(hi, int(value)))
        if key == "t":
            self._sort()
        elif key in ("r", "g", "b"):
            ev["orig"] = False

    def _row_at(self, pos):
        if not (PANEL_X <= pos[0] <= PANEL_X + 380):
            return None
        for i in range(len(self._fields())):
            y = FIELD_Y + i * FIELD_STEP
            if y <= pos[1] < y + 24:
                return i
        return None

    def _start_edit(self, i):
        key, label, _, _, _ = self._fields()[i]
        if key in NO_EDIT or self.cur is None:
            return
        self.field = i
        self.edit_key = key
        self.edit_buf = str(self.cur[key])
        self.edit_fresh = True
        self.status = t("Введите число, ENTER — применить, ESC — отмена")

    def _finish_edit(self, apply):
        key = self.edit_key
        buf = self.edit_buf
        self.edit_key = None
        self.edit_buf = ""
        if not apply or self.cur is None or key is None:
            return
        try:
            value = int(buf)
        except ValueError:
            self.status = t("Нужно целое число")
            return
        row = next((r for r in self._fields() if r[0] == key), None)
        if row is None:
            return
        _, label, lo, hi, _ = row
        self._set_value(key, value, lo, hi)
        self.status = f"{t(label)}: {self.cur[key]}"

    def _tick_hold(self):
        if self.hold is None or self.cur is None:
            return
        key, lo, hi, step, direction, t0, last = self.hold
        now = time.perf_counter()
        held = now - t0
        if held < HOLD_DELAY or now - last < HOLD_RATE:
            return
        mult = 1 if held < 1.0 else 5 if held < 2.5 else 20
        self._adjust(key, lo, hi, step * mult, direction)
        self.hold = (key, lo, hi, step, direction, t0, now)

    def _fit(self):
        ev = self.cur
        if ev is None or ev["type"] not in ("image", "video"):
            self.status = t("Выберите картинку или ролик")
            return
        size = EV.natural_size(ev)
        if size is None:
            self.status = t("Ролик не открылся") if ev["type"] == "video" else t("Картинка не найдена в images/")
            return
        w, h = EV.fit_box(size[0], size[1], C.WIDTH, C.HEIGHT)
        ev["w"] = w
        if ev["type"] == "video":
            ev["h"] = h
        self.status = f"{t('Подогнано')}: {w} × {h}"

    def _reset_color(self):
        if self.cur is not None and self.cur["type"] == "bg":
            self.cur["orig"] = True
            self.status = t("Фон: вернули исходный цвет")

    def _add(self, kind):
        ev = EV.make(kind, self.cursor)
        self.chart.events.append(ev)
        self._sort()
        self.cur = ev
        self.field = 0
        if kind == "image" and not ev["file"]:
            self.status = t("В папке images/ нет картинок (.png, .jpg). Положите файл и добавьте снова.")
        elif kind == "video" and not ev["file"]:
            self.status = t("В папке images/ нет роликов (.mp4, .webm, .mov, .avi, .mkv)")
        elif kind == "video" and not video.AVAILABLE:
            self.status = t("Для роликов нужен opencv-python: pip install opencv-python")
        else:
            self.status = f"{t('Добавлено')}: {t(EV.TYPE_NAMES[kind])} {t('в')} {_fmt(ev['t'])}"

    def _delete(self):
        if self.cur is None:
            return
        idx = self.chart.events.index(self.cur)
        self.chart.events.remove(self.cur)
        self.cur = None
        if self.chart.events:
            self.cur = self.chart.events[min(idx, len(self.chart.events) - 1)]
        self.field = 0
        self.status = t("Удалено")

    def _copy(self):
        if self.cur is None:
            self.status = t("Сначала выберите событие")
            return
        self.clip = {k: v for k, v in self.cur.items() if k != "t"}
        self.status = f"{t('Скопировано')}: {t(EV.TYPE_NAMES[self.cur['type']])}"

    def _paste(self, to_all):
        if self.clip is None:
            self.status = t("Буфер пуст: сначала КОПИРОВАТЬ")
            return
        kind = self.clip["type"]
        if to_all:
            targets = [e for e in self.chart.events if e["type"] == kind]
        elif self.cur is not None and self.cur["type"] == kind:
            targets = [self.cur]
        else:
            self.status = f"{t('Вставить можно только в событие типа')} «{t(EV.TYPE_NAMES[kind])}»"
            return
        if not targets:
            self.status = f"{t('Нет событий типа')} «{t(EV.TYPE_NAMES[kind])}»"
            return
        for e in targets:
            e.update({k: v for k, v in self.clip.items() if k not in ("type", "t")})
        self.status = f"{t('Свойства вставлены')}: {len(targets)} {t('шт.')}"

    def _duplicate(self):
        if self.cur is None:
            return
        copy = dict(self.cur)
        copy["t"] = max(0, min(self.duration, self.cursor))
        self.chart.events.append(copy)
        self._sort()
        self.cur = copy
        self.field = 0
        self.status = f"{t('Копия в')} {_fmt(copy['t'])}"

    def _action(self, name):
        if name in ("glitch", "flash", "image", "video", "bg"):
            self._add(name)
        elif name == "copy":
            self._copy()
        elif name == "paste":
            self._paste(False)
        elif name == "paste_all":
            self._paste(True)
        elif name == "dup":
            self._duplicate()
        elif name == "delete":
            self._delete()
        elif name == "preview":
            self._start_preview()
        elif name == "fit":
            self._fit()
        elif name == "cursor" and self.cur is not None:
            self.cur["t"] = max(0, min(self.duration, self.cursor))
            self._sort()
            self.status = f"{t('Время события')}: {_fmt(self.cur['t'])}"
        elif name == "back":
            return "back"
        return None

    def _select_index(self, delta):
        if not self.chart.events:
            return
        i = self.chart.events.index(self.cur) if self.cur in self.chart.events else 0
        i = max(0, min(len(self.chart.events) - 1, i + delta))
        self.cur = self.chart.events[i]
        self.field = 0
        if i < self.top:
            self.top = i
        elif i >= self.top + MAX_T_SHOWN:
            self.top = i - MAX_T_SHOWN + 1

    def _reset_rect(self):
        y = FIELD_Y + len(self._fields()) * FIELD_STEP + 6
        return pygame.Rect(PANEL_X, y, 200, 30)

    #-- Просмотр

    def _start_preview(self):
        if self.cur is None:
            self.status = t("Выберите событие для просмотра")
            return
        self.preview_ev = self.cur
        self.preview_t0 = time.perf_counter()

    def _preview_span(self, ev):
        if ev["type"] == "bg":
            return max(PREVIEW_BG_MS, ev["fade"] + 800)
        return max(1, EV.total_ms(ev))

    def _draw_preview(self, scr):
        ev = self.preview_ev
        span = self._preview_span(ev) + PREVIEW_PAUSE_MS
        e = ((time.perf_counter() - self.preview_t0) * 1000.0) % span
        if ev["type"] == "bg":
            scr.fill(EV.bg_at([ev], ev["t"] + e))
        else:
            scr.fill(C.BG_DARK)
        S.draw_grid(scr, e * 0.04, 0.0)
        if ev["type"] in ("image", "video"):
            if EV.natural_size(ev) is None:
                self.status = t("Картинка не найдена в images/") if ev["type"] == "image" else t("Ролик не открылся")
            else:
                EV.draw_media(scr, ev, e)
        if ev["type"] == "glitch":
            lvl = EV.glitch_level(ev, e)
            if lvl > 0:
                S.glitch(scr, strength=lvl)
        if ev["type"] == "flash":
            a = EV.flash_alpha(ev, e)
            if a > 0:
                self.white.set_alpha(int(255 * 0.85 * a))
                scr.blit(self.white, (0, 0))
        progress = min(1.0, e / span)
        pygame.draw.rect(scr, C.CYAN, (0, 0, int(C.WIDTH * progress), 4))
        title = f"{t('ПРОСМОТР')}: {t(EV.TYPE_NAMES[ev['type']])}   {e / 1000:.2f} {t('с')}"
        S.blit_text(scr, S.font(18, True), title, C.WHITE, C.WIDTH // 2, 28)
        S.blit_text(scr, S.font(13), t("P или ESC — вернуться к редактору"), C.GREY, C.WIDTH // 2, C.HEIGHT - 26)
        S.post_fx(scr, self.frame, grain=20)

    #-- Цикл

    def run(self):
        while True:
            self.clock.tick(C.FPS)
            mouse = pygame.mouse.get_pos()
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if self._event(ev) == "back":
                    return
            self._tick_hold()
            self._draw(mouse)
            pygame.display.flip()
            self.frame += 1

    def _event(self, ev):
        if self.preview_t0 is not None:
            if ev.type == pygame.KEYDOWN and ev.key in (pygame.K_ESCAPE, pygame.K_p):
                self.preview_t0 = None
            elif ev.type == pygame.MOUSEBUTTONDOWN:
                self.preview_t0 = None
            return None
        if self.edit_key is not None and ev.type == pygame.KEYDOWN:
            if ev.key == pygame.K_ESCAPE:
                self._finish_edit(False)
            elif ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self._finish_edit(True)
            elif ev.key == pygame.K_BACKSPACE:
                self.edit_buf = "" if self.edit_fresh else self.edit_buf[:-1]
                self.edit_fresh = False
            elif ev.unicode in ("0", "1", "2", "3", "4", "5", "6", "7", "8", "9"):
                base = "" if self.edit_fresh else self.edit_buf
                if len(base) < 7:
                    self.edit_buf = base + ev.unicode
                self.edit_fresh = False
            elif ev.unicode == "-" and (self.edit_fresh or not self.edit_buf):
                self.edit_buf = "-"
                self.edit_fresh = False
            return None
        if ev.type == pygame.KEYDOWN:
            return self._key(ev)
        if ev.type == pygame.MOUSEBUTTONUP:
            self.hold = None
        if ev.type == pygame.MOUSEWHEEL:
            i = self._row_at(pygame.mouse.get_pos())
            if i is not None and self.cur is not None:
                key, _, lo, hi, step = self._fields()[i]
                if key not in NO_EDIT:
                    mult = 5 if pygame.key.get_mods() & pygame.KMOD_SHIFT else 1
                    self._adjust(key, lo, hi, step * mult, ev.y)
                    return None
            self.top = max(0, min(max(0, len(self.chart.events) - MAX_T_SHOWN), self.top - ev.y))
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            if self.edit_key is not None:
                self._finish_edit(False)
            return self._click(ev.pos)
        return None

    def _key(self, ev):
        k = ev.key
        mods = pygame.key.get_mods()
        mul = 5 if mods & pygame.KMOD_SHIFT else 1
        if mods & pygame.KMOD_CTRL:
            if k == pygame.K_c:
                self._copy()
            elif k == pygame.K_v:
                self._paste(bool(mods & pygame.KMOD_SHIFT))
            elif k == pygame.K_d:
                self._duplicate()
            return None
        if k == pygame.K_ESCAPE:
            return "back"
        if k == pygame.K_UP:
            self._select_index(-1)
        elif k == pygame.K_DOWN:
            self._select_index(1)
        elif k == pygame.K_TAB:
            rows = self._fields()
            if rows:
                self.field = (self.field + 1) % len(rows)
        elif k in (pygame.K_LEFT, pygame.K_RIGHT):
            rows = self._fields()
            if rows:
                key, _, lo, hi, step = rows[min(self.field, len(rows) - 1)]
                self._adjust(key, lo, hi, step * mul if step else step, -1 if k == pygame.K_LEFT else 1)
        elif k == pygame.K_1:
            self._add("glitch")
        elif k == pygame.K_2:
            self._add("flash")
        elif k == pygame.K_3:
            self._add("image")
        elif k == pygame.K_4:
            self._add("bg")
        elif k == pygame.K_5:
            self._add("video")
        elif k == pygame.K_f:
            self._fit()
        elif k == pygame.K_p:
            self._start_preview()
        elif k == pygame.K_r:
            self._reset_color()
        elif k == pygame.K_c:
            return self._action("cursor")
        elif k in (pygame.K_DELETE, pygame.K_BACKSPACE):
            self._delete()
        return None

    def _click(self, pos):
        for name, btn in self.buttons:
            if btn.rect.collidepoint(pos):
                return self._action(name)
        if self.cur is not None and self.cur["type"] == "bg" and self._reset_rect().collidepoint(pos):
            self._reset_color()
            return None
        for i in range(min(MAX_T_SHOWN, max(0, len(self.chart.events) - self.top))):
            row = pygame.Rect(LIST_X, LIST_Y + i * ROW, LIST_W, ROW - 4)
            if row.collidepoint(pos):
                self.cur = self.chart.events[self.top + i]
                self.field = 0
                return None
        for i, (key, _, lo, hi, step) in enumerate(self._fields()):
            y = FIELD_Y + i * FIELD_STEP
            if pygame.Rect(PANEL_X, y, 200, 24).collidepoint(pos):
                self.field = i
            elif pygame.Rect(PANEL_X + 204, y, 22, 24).collidepoint(pos):
                self._adjust(key, lo, hi, step, -1)
                self.hold = (key, lo, hi, step, -1, time.perf_counter(), time.perf_counter())
            elif pygame.Rect(PANEL_X + 360, y, 22, 24).collidepoint(pos):
                self._adjust(key, lo, hi, step, 1)
                self.hold = (key, lo, hi, step, 1, time.perf_counter(), time.perf_counter())
            elif pygame.Rect(PANEL_X + 226, y, 126, 24).collidepoint(pos):
                self._start_edit(i)
        return None

    #-- Отрисовка

    def _draw(self, mouse):
        scr = pygame.display.get_surface()
        if self.preview_t0 is not None:
            self._draw_preview(scr)
            return
        scr.fill(C.BG_DARK)
        S.draw_grid(scr, self.frame * 0.2, 0.0)
        S.blit_text(scr, S.font(24, True), t("СОБЫТИЯ ПЕСНИ"), C.CYAN, C.WIDTH // 2, 24)

        for label, row_y in self.section_labels:
            scr.blit(S.font(12, True).render(t(label), True, (120, 160, 190)), (16, row_y + 9))
        for name, btn in self.buttons:
            btn.draw(scr, mouse)

        evs = self.chart.events
        if not evs:
            S.blit_text(scr, S.font(13), t("Событий пока нет"), C.GREY, LIST_X + LIST_W // 2, LIST_Y + 20)
        for i in range(min(MAX_T_SHOWN, max(0, len(evs) - self.top))):
            ev = evs[self.top + i]
            y = LIST_Y + i * ROW
            selected = ev is self.cur
            if selected:
                pygame.draw.rect(scr, (40, 40, 70), (LIST_X, y, LIST_W, ROW - 4), border_radius=6)
            color = EV.TYPE_COLORS[ev["type"]]
            label = f"{_fmt(ev['t'])}  {t(EV.TYPE_NAMES[ev['type']])}"
            if ev["type"] in ("image", "video") and ev["file"]:
                label += f"  {ev['file']}"
            scr.blit(S.font(13, selected).render(label[:36], True, color), (LIST_X + 8, y + 4))

        rows = self._fields()
        if self.cur is None:
            S.blit_text(scr, S.font(16), t("Выберите событие слева или добавьте новое"),
                        C.GREY, PANEL_X + 240, FIELD_Y + 20)
        for i, (key, label, _, _, _) in enumerate(rows):
            y = FIELD_Y + i * FIELD_STEP
            active = i == self.field
            if active:
                pygame.draw.rect(scr, (40, 40, 70), (PANEL_X - 8, y - 1, 470, 24), border_radius=6)
            scr.blit(S.font(13, active).render(t(label), True, C.WHITE if active else C.GREY), (PANEL_X, y + 5))
            if self.edit_key == key:
                caret = "_" if (self.frame // 30) % 2 == 0 else " "
                value = S.font(13, True).render(self.edit_buf + caret, True, C.GOLD)
            else:
                value = S.font(13, True).render(self._value_text(key)[:18], True, C.CYAN)
            scr.blit(value, (PANEL_X + 292 - value.get_width() // 2, y + 5))
            pygame.draw.rect(scr, C.DIM, (PANEL_X + 204, y, 22, 24), 1, border_radius=5)
            pygame.draw.rect(scr, C.DIM, (PANEL_X + 360, y, 22, 24), 1, border_radius=5)
            S.blit_text(scr, S.font(14, True), "−", C.WHITE, PANEL_X + 215, y + 12)
            S.blit_text(scr, S.font(14, True), "+", C.WHITE, PANEL_X + 371, y + 12)

        if self.cur is not None and self.cur["type"] == "bg":
            rect = self._reset_rect()
            pygame.draw.rect(scr, C.GOLD if rect.collidepoint(mouse) else C.DIM, rect, 2, border_radius=6)
            S.blit_text(scr, S.font(13, True), t("ВЕРНУТЬ ИСХОДНЫЙ"), C.GOLD, rect.centerx, rect.centery)
            swatch = pygame.Rect(rect.right + 12, rect.y, 60, rect.h)
            pygame.draw.rect(scr, EV.bg_target(self.cur), swatch, border_radius=6)
            pygame.draw.rect(scr, C.DIM, swatch, 1, border_radius=6)

        if self.cur is not None and self.field < len(rows):
            hint = t(HINTS.get(rows[self.field][0], ""))
            S.blit_text(scr, S.font(13), hint, (170, 170, 200), C.WIDTH // 2, 492)

        beta = t("Картинки и ролики: кладите .png / .jpg / .mp4 / .webm в папку images/ рядом с main.py (БЕТА)")
        S.blit_text(scr, S.font(13), beta, (150, 150, 190), C.WIDTH // 2, 516)
        if self.status:
            S.blit_text(scr, S.font(13, True), self.status, C.GOLD, C.WIDTH // 2, 540)
        S.blit_text(scr, S.font(12),
                    t("↑↓ событие · Tab поле · ←→ изменить (Shift ×5) · 1–5 добавить · P просмотр · R исходный фон"),
                    (110, 110, 150), C.WIDTH // 2, 566)
        S.blit_text(scr, S.font(12),
                    t("Ctrl+C копировать · Ctrl+V вставить · Ctrl+Shift+V всем таким · Ctrl+D копия · Del удалить · ESC назад"),
                    (110, 110, 150), C.WIDTH // 2, 584)
        S.post_fx(scr, self.frame, grain=20)


def run(clock, chart, cursor_ms, duration):
    EventsScreen(clock, chart, cursor_ms, duration).run()
