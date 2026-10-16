
#-- Импорт
import sys

import pygame

import config as C
import events as EV
import style as S

LIST_X, LIST_Y, ROW, LIST_W = 16, 170, 26, 290
PANEL_X = 320
FIELD_Y, FIELD_STEP = 180, 30
MAX_T_SHOWN = 12


def _fmt(ms):
    ms = max(0, int(ms))
    return f"{ms // 60000}:{(ms // 1000) % 60:02d}.{ms % 1000:03d}"


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
        self.buttons = []
        actions = (("glitch", "+ ГЛЮК"), ("flash", "+ ВСПЫШКА"), ("image", "+ КАРТИНКА"),
                   ("bg", "+ ФОН"), ("delete", "УДАЛИТЬ"), ("cursor", "КУРСОР"), ("back", "НАЗАД"))
        for i, (name, text) in enumerate(actions):
            rect = (16 + i * 112, 70, 104, 40)
            self.buttons.append((name, S.Btn(rect, text, C.CYAN, S.font(12, True))))

    #-- Данные

    def _sort(self):
        self.chart.events.sort(key=lambda e: e["t"])

    def _fields(self):
        ev = self.cur
        if ev is None:
            return []
        rows = [("t", "Время, мс", 0, self.duration, 10)]
        rows += [(k, lbl, lo, hi, st) for k, lbl, lo, hi, st, _ in EV.FIELDS[ev["type"]]]
        if ev["type"] == "image":
            rows += [("file", "Картинка (images/)", None, None, None),
                     ("anim", "Анимация", None, None, None)]
        if ev["type"] == "bg":
            rows += [("orig", "Исходный цвет фона", None, None, None)]
        return rows

    def _value_text(self, key):
        ev = self.cur
        if key == "file":
            return ev["file"] or "нет файлов в images/"
        if key == "anim":
            return EV.ANIM_NAMES[ev["anim"]]
        if key == "orig":
            return "ДА" if ev["orig"] else "НЕТ"
        if key == "t":
            return _fmt(ev["t"])
        return str(ev[key])

    def _adjust(self, key, lo, hi, step, direction):
        ev = self.cur
        if ev is None:
            return
        if key == "file":
            ev["file"] = EV.cycle(EV.list_images(), ev["file"], direction)
        elif key == "anim":
            ev["anim"] = EV.cycle(EV.ANIMS, ev["anim"], direction)
        elif key == "orig":
            ev["orig"] = not ev["orig"]
        else:
            ev[key] = max(lo, min(hi, ev[key] + direction * step))
            if key == "t":
                self._sort()
            elif key in ("r", "g", "b"):
                ev["orig"] = False

    def _reset_color(self):
        if self.cur is not None and self.cur["type"] == "bg":
            self.cur["orig"] = True
            self.status = "Фон: вернули исходный цвет"

    def _add(self, kind):
        ev = EV.make(kind, self.cursor)
        self.chart.events.append(ev)
        self._sort()
        self.cur = ev
        self.field = 0
        if kind == "image" and not ev["file"]:
            self.status = "В папке images/ нет картинок (.png, .jpg). Положите файл и добавьте снова."
        else:
            self.status = f"Добавлено: {EV.TYPE_NAMES[kind]} в {_fmt(ev['t'])}"

    def _delete(self):
        if self.cur is None:
            return
        idx = self.chart.events.index(self.cur)
        self.chart.events.remove(self.cur)
        self.cur = None
        if self.chart.events:
            self.cur = self.chart.events[min(idx, len(self.chart.events) - 1)]
        self.field = 0
        self.status = "Удалено"

    def _action(self, name):
        if name in ("glitch", "flash", "image", "bg"):
            self._add(name)
        elif name == "delete":
            self._delete()
        elif name == "cursor" and self.cur is not None:
            self.cur["t"] = max(0, min(self.duration, self.cursor))
            self._sort()
            self.status = f"Время события: {_fmt(self.cur['t'])}"
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
            self._draw(mouse)
            pygame.display.flip()
            self.frame += 1

    def _event(self, ev):
        if ev.type == pygame.KEYDOWN:
            return self._key(ev)
        if ev.type == pygame.MOUSEWHEEL:
            self.top = max(0, min(max(0, len(self.chart.events) - MAX_T_SHOWN), self.top - ev.y))
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            return self._click(ev.pos)
        return None

    def _key(self, ev):
        k = ev.key
        mul = 5 if pygame.key.get_mods() & pygame.KMOD_SHIFT else 1
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
            elif pygame.Rect(PANEL_X + 360, y, 22, 24).collidepoint(pos):
                self._adjust(key, lo, hi, step, 1)
        return None

    #-- Отрисовка

    def _draw(self, mouse):
        scr = pygame.display.get_surface()
        scr.fill(C.BG_DARK)
        S.draw_grid(scr, self.frame * 0.2, 0.0)
        S.blit_text(scr, S.font(26, True), "СОБЫТИЯ ПЕСНИ", C.CYAN, C.WIDTH // 2, 26)

        for name, btn in self.buttons:
            btn.draw(scr, mouse)

        evs = self.chart.events
        if not evs:
            S.blit_text(scr, S.font(13), "Событий пока нет", C.GREY, LIST_X + LIST_W // 2, LIST_Y + 20)
        for i in range(min(MAX_T_SHOWN, max(0, len(evs) - self.top))):
            ev = evs[self.top + i]
            y = LIST_Y + i * ROW
            selected = ev is self.cur
            if selected:
                pygame.draw.rect(scr, (40, 40, 70), (LIST_X, y, LIST_W, ROW - 4), border_radius=6)
            color = EV.TYPE_COLORS[ev["type"]]
            label = f"{_fmt(ev['t'])}  {EV.TYPE_NAMES[ev['type']]}"
            if ev["type"] == "image" and ev["file"]:
                label += f"  {ev['file']}"
            scr.blit(S.font(13, selected).render(label[:36], True, color), (LIST_X + 8, y + 4))

        rows = self._fields()
        if self.cur is None:
            S.blit_text(scr, S.font(16), "Выберите событие слева или добавьте новое",
                        C.GREY, PANEL_X + 240, FIELD_Y + 20)
        for i, (key, label, _, _, _) in enumerate(rows):
            y = FIELD_Y + i * FIELD_STEP
            active = i == self.field
            if active:
                pygame.draw.rect(scr, (40, 40, 70), (PANEL_X - 8, y - 2, 470, 28), border_radius=6)
            scr.blit(S.font(13, active).render(label, True, C.WHITE if active else C.GREY), (PANEL_X, y + 5))
            value = S.font(13, True).render(self._value_text(key)[:18], True, C.CYAN)
            scr.blit(value, (PANEL_X + 292 - value.get_width() // 2, y + 5))
            pygame.draw.rect(scr, C.DIM, (PANEL_X + 204, y, 22, 24), 1, border_radius=5)
            pygame.draw.rect(scr, C.DIM, (PANEL_X + 360, y, 22, 24), 1, border_radius=5)
            S.blit_text(scr, S.font(14, True), "−", C.WHITE, PANEL_X + 215, y + 12)
            S.blit_text(scr, S.font(14, True), "+", C.WHITE, PANEL_X + 371, y + 12)

        if self.cur is not None and self.cur["type"] == "bg":
            rect = self._reset_rect()
            btn_color = (C.GOLD if rect.collidepoint(mouse) else C.DIM)
            pygame.draw.rect(scr, btn_color, rect, 2, border_radius=6)
            S.blit_text(scr, S.font(13, True), "ВЕРНУТЬ ИСХОДНЫЙ", C.GOLD,
                        rect.centerx, rect.centery)
            swatch = pygame.Rect(rect.right + 12, rect.y, 60, rect.h)
            pygame.draw.rect(scr, EV.bg_target(self.cur), swatch, border_radius=6)
            pygame.draw.rect(scr, C.DIM, swatch, 1, border_radius=6)

        beta = "Картинки: кладите .png / .jpg в папку images/ рядом с main.py (БЕТА)"
        S.blit_text(scr, S.font(13), beta, (150, 150, 190), C.WIDTH // 2, C.HEIGHT - 80)
        if self.status:
            S.blit_text(scr, S.font(13, True), self.status, C.GOLD, C.WIDTH // 2, C.HEIGHT - 56)
        hint = ("↑↓ событие · Tab поле · ←→ изменить (Shift ×5) · 1/2/3/4 добавить · "
                "R исходный фон · Del удалить · ESC назад")
        S.blit_text(scr, S.font(12), hint, (110, 110, 150), C.WIDTH // 2, C.HEIGHT - 26)
        S.post_fx(scr, self.frame, grain=20)


def run(clock, chart, cursor_ms, duration):
    EventsScreen(clock, chart, cursor_ms, duration).run()
