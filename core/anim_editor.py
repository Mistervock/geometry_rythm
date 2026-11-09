"""Редактор анимаций (Geometry Rhythm 7.0, пункт 4): список, таймлайн с ключами, поля ключа и предпросмотр.

Анимации хранятся в чарте (chart.animations) и подключаются к картинке или ролику в экране событий
(строка «АНИМАЦИЯ»). Редактор меняет список на месте. Откат и повтор идут через историю редактора:
экран событий записывает весь снимок (события, папки, анимации) при выходе.
Ключ — это значения свойств в момент времени; переход «до следующего ключа» задаёт, как плавно
идёт интерполяция от этого ключа к следующему. Первый ключ всегда стоит в 0 мс.
"""
#-- Импорт
import copy
import sys

import pygame

import anim as AN
import config as C
import dialogs
import display
import screen_setting as SS
import style as S
from i18n import t

#-- Раскладка (расчётные единицы, как в экране событий)
LIST_X, LIST_Y, LIST_W, LIST_ROW, LIST_ROWS = 16, 64, 284, 24, 14
TL_X0, TL_X1, TL_Y0, TL_Y1 = 340, 1260, 96, 192
PANEL_X, PANEL_Y = 340, 252
PREV_X, PREV_Y, PREV_W, PREV_H = 740, 252, 520, 264
PREVIEW_SCALE = 0.4
KEY_BLOCK_Y = 322
KEY_ROW = 20
NUM_CURVE = ("x", "y", "scale", "rot", "alpha", "r", "g", "b")
TINT_INDEX = {"r": 0, "g": 1, "b": 2}
STEP = {"t": 10, "dur": 100, "x": 10, "y": 10, "scale": 10, "rot": 15, "alpha": 5, "r": 8, "g": 8, "b": 8}
ANIM_ROWS = (("dur", "Длительность, мс"), ("loop", "Повтор с начала"))
KEY_ROWS = (("t", "Время ключа, мс"), ("ease", "Переход до следующего ключа"), ("x", "Смещение X, px"),
            ("y", "Смещение Y, px"), ("scale", "Масштаб, %"), ("rot", "Поворот, °"),
            ("alpha", "Прозрачность, %"), ("r", "Цвет: красный"), ("g", "Цвет: зелёный"), ("b", "Цвет: синий"))
ROWS = tuple(("anim", n, l) for n, l in ANIM_ROWS) + tuple(("key", n, l) for n, l in KEY_ROWS)
HINT_LINES = (
    "Пробел — ▶ / пауза · , и . — сдвиг времени (Shift ×10) · [ и ] — соседний ключ · K — ключ здесь · Del — удалить ключ",
    "↑↓ — поле · ←→ — изменить (Shift ×5) · Enter — ввести число · L — повтор · Tab — другая анимация · N — новая",
    "Клик по таймлайну ставит время, перетаскивание ключа двигает его · R — переименовать · ESC — назад",
)


#-- Помощники

def _design(pos):
    return int(pos[0] / SS.SCALE), int(pos[1] / SS.SCALE)


def _clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v


def _row_y(i):
    return PANEL_Y + i * 22 if i < len(ANIM_ROWS) else KEY_BLOCK_Y + (i - len(ANIM_ROWS)) * KEY_ROW


def _field_at(dx, dy):
    for i in range(len(ROWS)):
        y = _row_y(i)
        if PANEL_X <= dx <= PANEL_X + 360 and y <= dy < y + KEY_ROW:
            return i
    return None


def _range(name):
    if name in TINT_INDEX:
        return 0, 255
    return AN.LIMITS[name]


class AnimEditor:
    def __init__(self, clock, chart, anim_id=""):
        self.clock = clock
        self.chart = chart
        self.sel = 0
        self.top = 0
        self.field = 0
        self.sel_key = 0
        self.head = 0.0
        self.playing = False
        self.drag = None
        self.frame = 0
        self.status = ""
        if anim_id:
            self.sel = next((i for i, a in enumerate(chart.animations) if a["id"] == anim_id), 0)
        self.buttons = {}
        for name, label, rect in (
            ("new", "+ НОВАЯ", SS.UR(LIST_X, 420, LIST_W, 30)),
            ("rename", "ПЕРЕИМЕНОВАТЬ", SS.UR(LIST_X, 456, LIST_W, 30)),
            ("dup", "ДУБЛИРОВАТЬ", SS.UR(LIST_X, 492, LIST_W, 30)),
            ("delete", "УДАЛИТЬ", SS.UR(LIST_X, 528, LIST_W, 30)),
            ("play", "▶ ИГРАТЬ", SS.UR(PANEL_X, 572, 150, 32)),
            ("addkey", "+ КЛЮЧ", SS.UR(PANEL_X + 160, 572, 150, 32)),
            ("delkey", "УДАЛИТЬ КЛЮЧ", SS.UR(PANEL_X + 320, 572, 170, 32)),
            ("back", "НАЗАД", SS.UR(PANEL_X + 500, 572, 150, 32)),
        ):
            self.buttons[name] = (S.Btn(rect, t(label), C.CYAN, S.font(12, True)), label)

    #-- Данные

    def _anim(self):
        anims = self.chart.animations
        if not anims:
            return None
        self.sel = _clamp(self.sel, 0, len(anims) - 1)
        return anims[self.sel]

    def _cur(self):
        anim = self._anim()
        if anim is None or not anim["keys"]:
            return None
        self.sel_key = _clamp(self.sel_key, 0, len(anim["keys"]) - 1)
        return anim["keys"][self.sel_key]

    def _name(self, i):
        return ROWS[i][1]

    def _raw(self, name):
        anim = self._anim()
        if anim is None:
            return None
        if name == "dur":
            return anim["dur"]
        key = self._cur()
        if key is None:
            return None
        if name in TINT_INDEX:
            return key["tint"][TINT_INDEX[name]]
        return key[name]

    def _value_text(self, name):
        anim = self._anim()
        if anim is None:
            return ""
        if name == "dur":
            return str(anim["dur"])
        if name == "loop":
            return t("ДА") if anim["loop"] else t("НЕТ")
        key = self._cur()
        if key is None:
            return ""
        if name == "ease":
            return t(AN.EASE_NAMES[key["ease"]])
        return str(int(round(self._raw(name))))

    def _select_anim(self, i):
        self.sel = i
        self.sel_key = 0
        self.drag = None
        self.playing = False
        anim = self._anim()
        if anim is not None:
            self.head = min(self.head, anim["dur"])
            if i < self.top:
                self.top = i
            elif i >= self.top + LIST_ROWS:
                self.top = i - LIST_ROWS + 1

    def _resort(self, key):
        keys = self._anim()["keys"]
        keys.sort(key=lambda k: k["t"])
        self.sel_key = next(i for i, k in enumerate(keys) if k is key)

    def _set(self, name, value):
        anim = self._anim()
        if anim is None:
            return
        if name == "dur":
            AN.set_dur(anim, int(round(value)))
            self.head = min(self.head, anim["dur"])
            return
        if name == "loop":
            anim["loop"] = bool(value)
            return
        key = self._cur()
        if key is None:
            return
        if name == "t":
            if self.sel_key == 0:
                self.status = t("Первый ключ всегда стоит в начале анимации")
                return
            new_t = int(_clamp(round(value), 1, anim["dur"]))
            if any(k is not key and k["t"] == new_t for k in anim["keys"]):
                self.status = t("В этой точке времени уже есть ключ")
                return
            key["t"] = new_t
            self._resort(key)
            return
        if name == "ease":
            if value in AN.EASES:
                key["ease"] = value
            return
        if name in TINT_INDEX:
            key["tint"][TINT_INDEX[name]] = int(_clamp(round(value), 0, 255))
            return
        lo, hi = AN.LIMITS[name]
        key[name] = _clamp(round(value), lo, hi)

    def _adjust(self, name, direction, mult=1):
        anim = self._anim()
        if anim is None:
            return
        if name == "loop":
            self._set("loop", not anim["loop"])
            return
        if name == "ease":
            key = self._cur()
            if key is not None:
                idx = AN.EASES.index(key["ease"])
                self._set("ease", AN.EASES[(idx + direction) % len(AN.EASES)])
            return
        cur = self._raw(name)
        if cur is None:
            return
        step = STEP[name] * mult
        if name == "dur":
            self._set("dur", _clamp(cur + direction * step, AN.DUR_LIMITS[0], AN.DUR_LIMITS[1]))
            return
        self._set(name, cur + direction * step)

    def _edit(self, i):
        name, label = self._name(i), ROWS[i][2]
        if name in ("loop", "ease"):
            self._adjust(name, 1)
            return
        cur = self._raw(name)
        if cur is None:
            return
        res = dialogs.ask_text(self.clock, t(label), str(int(round(cur))), 7)
        if res is None:
            return
        try:
            value = float(res.replace(",", "."))
        except ValueError:
            self.status = t("Нужно число")
            return
        self._set(name, value)

    #-- Список и действия

    def _new(self):
        anims = self.chart.animations
        if len(anims) >= AN.MAX_ANIMS:
            self.status = t("Анимаций уже максимум") + f": {AN.MAX_ANIMS}"
            return
        anim = AN.new_animation(f"{t('Анимация')} {len(anims) + 1}", [a["id"] for a in anims])
        anims.append(anim)
        self._select_anim(len(anims) - 1)
        self.status = t("Новая анимация создана")

    def _dup(self):
        anims = self.chart.animations
        src = self._anim()
        if src is None:
            return
        if len(anims) >= AN.MAX_ANIMS:
            self.status = t("Анимаций уже максимум") + f": {AN.MAX_ANIMS}"
            return
        copied = copy.deepcopy(src)
        copied["id"] = AN.new_id([a["id"] for a in anims])
        copied["name"] = (src["name"] + " ·")[:AN.NAME_MAX]
        anims.insert(self.sel + 1, copied)
        self._select_anim(self.sel + 1)
        self.status = t("Анимация скопирована")

    def _rename(self):
        anim = self._anim()
        if anim is None:
            return
        res = dialogs.ask_text(self.clock, t("Название анимации"), anim["name"], AN.NAME_MAX)
        if res:
            anim["name"] = res[:AN.NAME_MAX]

    def _delete(self):
        anim = self._anim()
        if anim is None:
            return
        if not dialogs.confirm(self.clock, f"{t('Удалить анимацию')} «{anim['name']}»?"):
            return
        anims = self.chart.animations
        anims.remove(anim)
        for ev in self.chart.events:
            if ev.get("anim_id") == anim["id"]:
                ev["anim_id"] = ""
        self._select_anim(min(self.sel, len(anims) - 1) if anims else 0)
        self.status = t("Анимация удалена")

    def _toggle_play(self):
        anim = self._anim()
        if anim is None:
            return
        if not self.playing and self.head >= anim["dur"]:
            self.head = 0.0
        self.playing = not self.playing

    def _move_head(self, delta):
        anim = self._anim()
        if anim is None:
            return
        self.playing = False
        self.head = _clamp(self.head + delta, 0, anim["dur"])

    def _add_key(self):
        anim = self._anim()
        if anim is None:
            self.status = t("Сначала создайте анимацию")
            return
        if len(anim["keys"]) >= AN.MAX_KEYS:
            self.status = t("Ключей уже максимум") + f": {AN.MAX_KEYS}"
            return
        self.sel_key = AN.add_key(anim, self.head)
        self.status = f"{t('Ключ')} {_fmt_ms(anim['keys'][self.sel_key]['t'])}"

    def _del_key(self):
        anim = self._anim()
        if anim is None:
            return
        if AN.remove_key(anim, self.sel_key):
            self.sel_key = min(self.sel_key, len(anim["keys"]) - 1)
            self.status = t("Ключ удалён")
        else:
            self.status = t("Нельзя удалить первый ключ и единственный оставшийся")

    def _step_key(self, direction):
        anim = self._anim()
        if anim is None:
            return
        self.sel_key = _clamp(self.sel_key + direction, 0, len(anim["keys"]) - 1)
        self.head = anim["keys"][self.sel_key]["t"]
        self.playing = False

    def _advance(self, dt_ms):
        anim = self._anim()
        if not self.playing or anim is None:
            return
        self.head += min(dt_ms, 100)
        if self.head >= anim["dur"]:
            if anim["loop"]:
                self.head = self.head % anim["dur"]
            else:
                self.head = anim["dur"]
                self.playing = False

    #-- Таймлайн

    def _t_to_x(self, ms, dur):
        return TL_X0 + (TL_X1 - TL_X0) * ms / dur

    def _x_to_t(self, x, dur):
        return _clamp((x - TL_X0) / (TL_X1 - TL_X0) * dur, 0, dur)

    def _key_at(self, dx, dy, anim):
        mid = (TL_Y0 + TL_Y1) // 2
        for i, k in enumerate(anim["keys"]):
            if abs(dx - self._t_to_x(k["t"], anim["dur"])) <= 9 and abs(dy - mid) <= 12:
                return i
        return None

    def _sample(self, anim, ms, name):
        vals = AN.sample(anim, ms)
        if name in TINT_INDEX:
            return vals["tint"][TINT_INDEX[name]]
        return vals[name]

    #-- Ввод

    def _button(self, name):
        if name == "back":
            return "back"
        handlers = {"new": self._new, "rename": self._rename, "dup": self._dup, "delete": self._delete,
                    "play": self._toggle_play, "addkey": self._add_key, "delkey": self._del_key}
        handlers[name]()
        return None

    def _on_key(self, ev):
        mods = pygame.key.get_mods()
        mul = 5 if mods & pygame.KMOD_SHIFT else 1
        anims = self.chart.animations
        k = ev.key
        if k == pygame.K_ESCAPE:
            return "back"
        if k == pygame.K_SPACE:
            self._toggle_play()
        elif k == pygame.K_UP:
            self.field = (self.field - 1) % len(ROWS)
        elif k == pygame.K_DOWN:
            self.field = (self.field + 1) % len(ROWS)
        elif k in (pygame.K_LEFT, pygame.K_RIGHT):
            self._adjust(self._name(self.field), -1 if k == pygame.K_LEFT else 1, mul)
        elif k in (pygame.K_RETURN, pygame.K_KP_ENTER):
            self._edit(self.field)
        elif k in (pygame.K_COMMA, pygame.K_PERIOD):
            step = 100 if mul > 1 else 10
            self._move_head(-step if k == pygame.K_COMMA else step)
        elif k == pygame.K_LEFTBRACKET:
            self._step_key(-1)
        elif k == pygame.K_RIGHTBRACKET:
            self._step_key(1)
        elif k == pygame.K_k:
            self._add_key()
        elif k in (pygame.K_DELETE, pygame.K_BACKSPACE):
            self._del_key()
        elif k == pygame.K_l:
            self._adjust("loop", 1)
        elif k == pygame.K_n:
            self._new()
        elif k == pygame.K_r:
            self._rename()
        elif k == pygame.K_TAB and anims:
            step = -1 if mods & pygame.KMOD_SHIFT else 1
            self._select_anim((self.sel + step) % len(anims))
        return None

    def _event(self, ev):
        anim = self._anim()
        if ev.type == pygame.KEYDOWN:
            return self._on_key(ev)
        if ev.type == pygame.MOUSEBUTTONUP and ev.button == 1:
            self.drag = None
            return None
        if ev.type == pygame.MOUSEMOTION and self.drag is not None and anim is not None:
            dx, _ = _design(ev.pos)
            new_t = round(self._x_to_t(dx, anim["dur"]))
            if self._cur() is self.drag:
                self._set("t", new_t)
            return None
        if ev.type == pygame.MOUSEWHEEL:
            dx, dy = _design(pygame.mouse.get_pos())
            if LIST_X <= dx < LIST_X + LIST_W and LIST_Y <= dy < LIST_Y + LIST_ROWS * LIST_ROW:
                total = len(self.chart.animations)
                self.top = _clamp(self.top - ev.y, 0, max(0, total - LIST_ROWS))
                return None
            i = _field_at(dx, dy)
            if i is not None:
                self._adjust(self._name(i), ev.y, 5 if pygame.key.get_mods() & pygame.KMOD_SHIFT else 1)
            return None
        if ev.type != pygame.MOUSEBUTTONDOWN or ev.button != 1:
            return None
        for name, (btn, _) in self.buttons.items():
            if btn.rect.collidepoint(ev.pos):
                return self._button(name)
        dx, dy = _design(ev.pos)
        if LIST_X <= dx < LIST_X + LIST_W and LIST_Y <= dy < LIST_Y + LIST_ROWS * LIST_ROW:
            i = self.top + (dy - LIST_Y) // LIST_ROW
            if i < len(self.chart.animations):
                self._select_anim(i)
            return None
        if anim is not None and TL_X0 <= dx <= TL_X1 and TL_Y0 <= dy <= TL_Y1:
            idx = self._key_at(dx, dy, anim)
            if idx is not None:
                self.sel_key = idx
                self.drag = anim["keys"][idx]
            else:
                self.head = self._x_to_t(dx, anim["dur"])
                self.playing = False
            return None
        i = _field_at(dx, dy)
        if i is not None:
            self.field = i
            if dx >= PANEL_X + 250:
                self._edit(i)
        return None

    def run(self):
        while True:
            dt = display.tick(self.clock)
            self._advance(dt)
            mouse = pygame.mouse.get_pos()
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if self._event(ev) == "back":
                    return
            self._draw(mouse)
            display.flip()
            self.frame += 1

    #-- Отрисовка

    def _draw(self, mouse):
        u = SS.U
        scr = pygame.display.get_surface()
        scr.fill(C.BG_DARK)
        S.draw_grid(scr, self.frame * 0.2, 0.0)
        S.glitch_title(scr, S.font(24, True), t("АНИМАЦИИ"), C.CYAN, C.WIDTH // 2, u(24), self.frame)
        self._draw_list(scr)
        self._draw_timeline(scr)
        self._draw_fields(scr)
        self._draw_preview(scr)
        self._draw_buttons(scr, mouse)
        if self.status:
            S.blit_text(scr, S.font(13, True), self.status, C.GOLD, C.WIDTH // 2, u(540))
        for i, line in enumerate(HINT_LINES):
            S.blit_text(scr, S.font(12), t(line), (110, 110, 150), C.WIDTH // 2, u(624 + i * 22))
        S.post_fx(scr, self.frame, grain=20)

    def _draw_list(self, scr):
        u = SS.U
        anims = self.chart.animations
        scr.blit(S.font(12, True).render(t("СПИСОК АНИМАЦИЙ"), True, (120, 160, 190)), SS.UP(LIST_X, LIST_Y - 18))
        if not anims:
            S.blit_text(scr, S.font(13), t("Анимаций пока нет"), C.GREY, u(LIST_X + LIST_W // 2), u(LIST_Y + 20))
        for i in range(self.top, min(len(anims), self.top + LIST_ROWS)):
            a = anims[i]
            y = LIST_Y + (i - self.top) * LIST_ROW
            selected = i == self.sel
            if selected:
                pygame.draw.rect(scr, (40, 40, 70), SS.UR(LIST_X, y, LIST_W, LIST_ROW - 3), border_radius=u(6))
            label = f"{a['name']} · {a['dur']} {t('мс')}"
            color = C.GOLD if selected else C.GREY
            scr.blit(S.font(13, selected).render(label[:34], True, color), SS.UP(LIST_X + 8, y + 3))

    def _draw_timeline(self, scr):
        u = SS.U
        rect = SS.UR(TL_X0, TL_Y0, TL_X1 - TL_X0, TL_Y1 - TL_Y0)
        pygame.draw.rect(scr, (14, 14, 34), rect, border_radius=u(6))
        pygame.draw.rect(scr, C.CYAN, rect, u(1), border_radius=u(6))
        anim = self._anim()
        if anim is None:
            S.blit_text(scr, S.font(14), t("Создайте анимацию слева"), C.GREY, u(800), u(144))
            return
        dur = anim["dur"]
        for i in range(5):
            ms = dur * i / 4
            x = self._t_to_x(ms, dur)
            pygame.draw.line(scr, (50, 50, 90), (u(x), u(TL_Y0)), (u(x), u(TL_Y1)), u(1))
            S.blit_text(scr, S.font(11), f"{ms / 1000:.2f} {t('с')}", C.GREY, u(min(x, TL_X1 - 24)), u(TL_Y1 + 10))
        name = self._name(self.field) if self.field < len(ROWS) and ROWS[self.field][0] == "key" else None
        if name in NUM_CURVE:
            lo, hi = _range(name)
            pts = []
            for i in range(161):
                ms = dur * i / 160
                v = self._sample(anim, ms, name)
                y = TL_Y1 - 6 - (v - lo) / (hi - lo) * (TL_Y1 - TL_Y0 - 12)
                pts.append((u(self._t_to_x(ms, dur)), u(y)))
            pygame.draw.lines(scr, (110, 200, 255), False, pts, u(2))
        mid = (TL_Y0 + TL_Y1) // 2
        for i, k in enumerate(anim["keys"]):
            x = self._t_to_x(k["t"], dur)
            color = C.GOLD if i == self.sel_key else C.CYAN
            pygame.draw.polygon(scr, color, [(u(x), u(mid - 8)), (u(x + 7), u(mid)),
                                             (u(x), u(mid + 8)), (u(x - 7), u(mid))])
        hx = self._t_to_x(self.head, dur)
        pygame.draw.line(scr, C.GOLD, (u(hx), u(TL_Y0)), (u(hx), u(TL_Y1)), u(2))

    def _draw_fields(self, scr):
        anim = self._anim()
        if anim is None:
            return
        u = SS.U
        key = self._cur()
        if key is not None:
            head = f"{t('КЛЮЧ')} {self.sel_key + 1} / {len(anim['keys'])} · {t('Время')} {_fmt_ms(key['t'])}"
            scr.blit(S.font(12, True).render(head, True, C.GOLD), SS.UP(PANEL_X, KEY_BLOCK_Y - 22))
        for i, (kind, name, label) in enumerate(ROWS):
            y = _row_y(i)
            active = i == self.field
            if active:
                pygame.draw.rect(scr, (40, 40, 70), SS.UR(PANEL_X - 8, y - 1, 380, KEY_ROW + 2), border_radius=u(5))
            scr.blit(S.font(12, active).render(t(label), True, C.WHITE if active else C.GREY),
                     SS.UP(PANEL_X, y + 3))
            value = self._value_text(name)
            if value:
                vs = S.font(12, True).render(value, True, C.CYAN)
                scr.blit(vs, (u(PANEL_X + 352) - vs.get_width(), u(y + 3)))

    def _draw_preview(self, scr):
        u = SS.U
        rect = SS.UR(PREV_X, PREV_Y, PREV_W, PREV_H)
        pygame.draw.rect(scr, (12, 12, 28), rect, border_radius=u(6))
        pygame.draw.rect(scr, C.DIM, rect, u(1), border_radius=u(6))
        S.blit_text(scr, S.font(12, True), t("ПРЕДПРОСМОТР"), C.CYAN, u(PREV_X + PREV_W // 2), u(PREV_Y + 14))
        anim = self._anim()
        if anim is None:
            return
        vals = AN.sample(anim, self.head)
        size = u(110)
        img = pygame.Surface((size, size), pygame.SRCALPHA)
        img.fill((0, 200, 255, 255))
        img = pygame.transform.rotozoom(img, vals["rot"], vals["scale"] / 100.0)
        r, g, b = vals["tint"]
        img.fill((r, g, b, 255), special_flags=pygame.BLEND_RGBA_MULT)
        img.set_alpha(int(255 * vals["alpha"] / 100))
        cx = u(PREV_X + PREV_W // 2) + u(vals["x"] * PREVIEW_SCALE)
        cy = u(PREV_Y + PREV_H // 2 + 10) + u(vals["y"] * PREVIEW_SCALE)
        scr.blit(img, (cx - img.get_width() // 2, cy - img.get_height() // 2))
        S.blit_text(scr, S.font(12), f"{self.head / 1000:.2f} с / {anim['dur'] / 1000:.2f} с",
                    C.GREY, u(PREV_X + PREV_W // 2), u(PREV_Y + PREV_H - 14))

    def _draw_buttons(self, scr, mouse):
        for name, (btn, label) in self.buttons.items():
            if name == "play":
                label = "‖ ПАУЗА" if self.playing else "▶ ИГРАТЬ"
            btn.set_label(t(label))
            btn.draw(scr, mouse, active=False)


def _fmt_ms(ms):
    ms = max(0, int(round(ms)))
    return f"{ms // 60000}:{(ms // 1000) % 60:02d}.{ms % 1000:03d}"


def run(clock, chart, anim_id=""):
    AnimEditor(clock, chart, anim_id).run()
