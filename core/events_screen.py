#-- Импорт
import math
import sys
import time

import pygame

import anim as AN
import anim_editor
import cine as CN
import config as C
import dialogs
import display
import events as EV
import fx as FX
import packs as PK
import screen_setting as SS
import style as S
import tracks
import video
from i18n import t

#-- Раскладка
ROW1_Y, ROW2_Y, ROW3_Y, ROW4_Y, BTN_H = 54, 96, 138, 180, 32
BTN_W, BTN_STEP, ROW_SPAN = 124, 132, 1160
BTN_GAP = 8
PARAM_PREFIX = "p:"
LIST_X, LIST_Y, ROW, LIST_W = 16, 226, 22, 380
PANEL_X = 440
FIELD_Y, FIELD_STEP = 226, 30
FIELD_STEP_MID, FIELD_STEP_DENSE = 27, 23
MAX_T_SHOWN = 10
MAX_FOLDERS = 8
PREVIEW_BG_MS = 1500
PREVIEW_PAUSE_MS = 500
HOLD_DELAY = 0.35
HOLD_RATE = 0.06
NO_EDIT = ("file", "anim", "anim_id", "look", "kind", "beat", "orig", "full", "mode", "ease", "skip", "pack")
FULL_IGNORED = ("w", "h", "x", "y", "dx", "dy")
LOCKED_MSG = "Событие заблокировано: нажмите РАЗМКНУТЬ, чтобы изменить"
FOLDER_LOCKED_MSG = "Папка заблокирована: сначала разблокируйте её"

#-- Разделы кнопок
SECTIONS = (
    ("ДОБАВИТЬ", ROW1_Y, (("glitch", "+ ГЛЮК"), ("flash", "+ ВСПЫШКА"),
                         ("image", "+ КАРТИНКА"), ("video", "+ ВИДЕО"), ("bg", "+ ФОН"), ("heal", "+ ХИЛЛ"), ("card", "+ КАРТОЧКА"), ("invert", "+ ИНВЕРСИЯ"), ("fx", "+ ЭФФЕКТ"),
                         ("camera", "+ КАМЕРА"), ("transition", "+ ПЕРЕХОД"), ("pack", "+ ПАКЕТ"))),
    ("ПРАВКА", ROW2_Y, (("copy", "КОПИРОВАТЬ"), ("paste", "ВСТАВИТЬ"), ("paste_all", "ВСЕМ ТАКИМ"),
                       ("dup", "ДУБЛИРОВАТЬ"), ("delete", "УДАЛИТЬ"))),
    ("ВИД", ROW3_Y, (("preview", "▶ ПРОСМОТР"), ("cursor", "В КУРСОР"), ("fit", "ПОДОГНАТЬ"), ("anims", "АНИМАЦИИ"), ("back", "НАЗАД"))),
    ("ПАПКИ", ROW4_Y, (("sort", "СОРТ: ВРЕМЯ"), ("newfolder", "+ ПАПКА"), ("tofolder", "В ПАПКУ"),
                      ("unfolder", "ИЗ ПАПКИ"), ("lock", "ЗАМКНУТЬ"), ("rename", "ПЕРЕИМЕНОВАТЬ"), ("visible", "СКРЫТЬ"), ("kind", "ТИП"))),
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
    "full": "ДА — картинка или ролик растягиваются на весь экран (пропорции не сохраняются, размер и смещение не используются)",
    "file": "Файл из папки images/, стрелки перебирают список",
    "anim": "РЕЗКО — появилась и пропала; ПЛАВНО — с затуханием; ДВИЖЕНИЕ — плывёт. Не действует, если выбрана анимация из чарта",
    "anim_id": "Анимация из чарта: движение, масштаб, поворот, цвет по ключам. НЕТ — работают пресеты выше. M — открыть редактор анимаций",
    "look": "Эффект самой картинки или ролика: размытие, свечение, хроматика, волна, тёплый, холодный, чёрно-белый",
    "look_amt": "Сила эффекта «ОБЪЕКТ» в процентах",
    "amount": "Сила эффекта на весь экран в процентах",
    "attack": "За сколько мс эффект нарастает и спадает",
    "kind": "Вид эффекта на весь экран: размытие, свечение, хроматика, волна, тёплый, холодный, чёрно-белый",
    "beat": "ДА — сила пульсирует по сетке: сильнее на ударе, слабее между ударами (нужен темп в сетке)",
    "r": "Красная составляющая фона, 0–255",
    "g": "Зелёная составляющая фона, 0–255",
    "b": "Синяя составляющая фона, 0–255",
    "orig": "ДА — вернуть исходный цвет фона; ручное изменение цвета выключает это",
    "lane": "Дорожка, в которой упадёт белый круг: 1 — D, 2 — F, 3 — J, 4 — K",
    "speed": "Во сколько раз круг падает быстрее обычных нот: 170% — в 1.7 раза",
    "text": "Текст, который появится на экране. Клик по полю или ENTER — ввести, ESC — отмена",
    "camera.dur": "За сколько мс камера переходит к новому положению. Новое событие камеры обрывает предыдущее и начинается с текущего положения",
    "camera.zoom": "Масштаб кадра: 100% — без изменений, больше — приближение, меньше — отдаление с чёрными полями",
    "camera.x": "Сдвиг кадра по горизонтали, пиксели",
    "camera.y": "Сдвиг кадра по вертикали, пиксели",
    "camera.ease": "Кривая движения: РАЗГОН — медленный старт, ТОРМОЖЕНИЕ — медленное окончание, МЯГКО — по обоим краям",
    "transition.kind": "ЗАТЕМНЕНИЕ — плавная заливка, ДИАФРАГМА — круг из центра, ШТОРКА — полоса слева направо",
    "transition.mode": "ЗАКРЫТЬ — экран закрыт и остаётся закрытым, ОТКРЫТЬ — экран открывается, АКЦЕНТ — закрывается и открывается",
    "transition.dur": "Сколько мс длится переход",
    "transition.ease": "Кривая перехода: как быстро закрывается или открывается экран",
    "transition.colour": "Цвет закрытого экрана: 0 — чёрный, 1 — белый, 2 — красный, 3 — голубой",
    "transition.skip": "ДА — Enter пропускает переход «ОТКРЫТЬ» и «АКЦЕНТ». Счёт не меняется",
    "pack.pack": "Пакет из библиотеки packs/. Стрелки перебирают пакеты, B — открыть список с предпросмотром",
    "pack.dur": "Сколько мс пакет живёт на экране",
    "pack.lane": "Дорожка, от которой идёт пакет: 0 — центр экрана, 1 — D … 4 — K",
    "pack.x": "Смещение точки появления по горизонтали, пиксели",
    "pack.y": "Смещение точки появления по вертикали, пиксели",
    "pack.power": "Сила пакета: число частиц и размер колец, в пределах лимитов",
    "pack.colour": "Цвет пакета из палитры: 0 — белый, 1 — красный, 2 — голубой и так далее до 5",
}


#-- Форматирование времени
def _wrap(text, fnt, width):
    lines, line = [], ""
    for word in text.split(" "):
        cand = word if not line else line + " " + word
        if fnt.size(cand)[0] <= width:
            line = cand
        else:
            if line:
                lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines


def _fmt(ms):
    ms = max(0, int(ms))
    return f"{ms // 60000}:{(ms // 1000) % 60:02d}.{ms % 1000:03d}"


def _ev_get(ev, key):
    """Значение поля события. Для параметров пакета («p:<id>») — с учётом значений по умолчанию пакета."""
    if key.startswith(PARAM_PREFIX):
        pack = PK.get(ev.get("pack", ""))
        if pack is None:
            return 0.0
        return PK.resolve_params(pack, ev.get("params"))[key[len(PARAM_PREFIX):]]
    return ev[key]


def _num_text(v):
    """Число для поля ввода и подписи: 50 вместо 50.0, без лишних нулей у дробных. Строка (текст карточки) — как есть."""
    if isinstance(v, str):
        return v
    if isinstance(v, float) and not v.is_integer():
        return f"{v:.3f}".rstrip("0").rstrip(".")
    return str(int(v))


def _hint_text(ev, key):
    """Подсказка поля. У камеры, перехода и пакета свои тексты для одинаковых имён полей (x, y, lane, kind)."""
    if ev is not None and f"{ev['type']}.{key}" in HINTS:
        return HINTS[f"{ev['type']}.{key}"]
    return HINTS.get(key, "")


def _design(pos):
    """Экранные координаты мыши → расчётные (те, в которых написана раскладка)."""
    return int(pos[0] / SS.SCALE), int(pos[1] / SS.SCALE)


def _draw_lock(scr, x, y, color):
    u = SS.U
    pygame.draw.rect(scr, color, (x, y + u(6), u(10), u(9)), border_radius=u(2))
    pygame.draw.arc(scr, color, pygame.Rect(x + u(2), y, u(6), u(11)), 0, math.pi, u(2))


#-- Экран событий
class EventsScreen:
    def __init__(self, clock, chart, cursor_ms, duration):
        self.clock = clock
        self.chart = chart
        self.cursor = int(cursor_ms)
        self.duration = int(duration)
        self.cur = min(chart.events, key=lambda e: abs(e["t"] - self.cursor)) if chart.events else None
        self.kind_filter = None
        self.stat_rects = {}
        self.sel_folder = None
        self.open_folders = {f["name"] for f in chart.folders}
        self.sort_mode = "time"
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
        self.marks = {}
        self.white = pygame.Surface((C.WIDTH, C.HEIGHT))
        self.white.fill(C.WHITE)
        self.buttons = []
        self.btns = {}
        self.section_labels = []
        for label, row_y, items in SECTIONS:
            self.section_labels.append((label, row_y))
            pitch = min(BTN_STEP, (ROW_SPAN + BTN_GAP) // max(1, len(items)))
            width = min(BTN_W, pitch - BTN_GAP)
            for i, (name, text) in enumerate(items):
                btn = S.Btn(SS.UR(100 + i * pitch, row_y, width, BTN_H), t(text), C.CYAN, S.font(12, True))
                self.buttons.append((name, btn))
                self.btns[name] = btn

    #-- Данные

    def _sort(self):
        self.chart.events.sort(key=lambda e: e["t"])

    def _fold_names(self):
        return [f["name"] for f in self.chart.folders]

    def _folder(self, name):
        return next((f for f in self.chart.folders if f["name"] == name), None)

    def _members(self, name):
        return [e for e in self.chart.events if e.get("folder") == name]

    def _hidden(self):
        return tracks.hidden_names(self.chart.folders)

    def _visible(self, ev):
        return ev.get("folder", "") not in self._hidden()

    def _folder_locked(self, ev):
        f = self._folder(ev.get("folder", ""))
        return bool(f and f["locked"])

    def _is_marked(self, ev):
        return self.marks.get(id(ev)) is ev

    def _marked(self):
        live = {id(e): e for e in self.chart.events}
        self.marks = {k: v for k, v in self.marks.items() if live.get(k) is v}
        return [e for e in self.chart.events if self._is_marked(e) and self._visible(e)]

    def _batch_targets(self):
        marked = self._marked()
        return marked if len(marked) >= 2 else []

    def _targets(self):
        batch = self._batch_targets()
        if batch:
            return batch
        return [self.cur] if self.cur is not None else []

    def _mark(self, ev, on):
        if on:
            self.marks[id(ev)] = ev
        else:
            self.marks.pop(id(ev), None)

    def _clear_marks(self):
        self.marks = {}

    def _extend(self, row, toggle):
        if row[0] != "event":
            return
        ev = row[1]
        if not self._marked() and self.cur is not None and self.cur is not ev:
            self._mark(self.cur, True)
        self._mark(ev, not (toggle and self._is_marked(ev)))
        self.cur = ev
        self.sel_folder = None
        self.field = 0
        self.status = f"{t('Выбрано')}: {len(self._marked())}"

    def _mark_all(self):
        events = [p for kind, p in self._view() if kind == "event"]
        if not events:
            return
        for e in events:
            self._mark(e, True)
        if self.cur is None:
            self.cur = events[0]
        self.status = f"{t('Выбрано')}: {len(self._marked())}"

    def _block_edit(self):
        if self.cur is not None and self.cur.get("locked"):
            self.status = t(LOCKED_MSG)
            return True
        return False

    def _sort_key(self):
        if self.sort_mode == "type":
            return lambda e: (EV.TYPES.index(e["type"]), e["t"])
        return lambda e: e["t"]

    def _view(self):
        """Строки списка: ('folder', имя) и ('event', событие). Порядок: папки, затем события без папки.
        События скрытых дорожек не показываются, сама дорожка остаётся в списке."""
        key = self._sort_key()
        hidden = self._hidden()
        if self.kind_filter is not None:
            return [("event", e) for e in sorted(self.chart.events, key=key)
                    if e["type"] == self.kind_filter and e.get("folder", "") not in hidden]
        names = set(self._fold_names())
        rows = []
        for f in self.chart.folders:
            rows.append(("folder", f["name"]))
            if f["name"] in self.open_folders and f["name"] not in hidden:
                rows += [("event", e) for e in sorted(self._members(f["name"]), key=key)]
        root = [e for e in self.chart.events if e.get("folder", "") not in names]
        rows += [("event", e) for e in sorted(root, key=key)]
        return rows

    def _sel_index(self, rows):
        for i, (kind, payload) in enumerate(rows):
            if kind == "event" and self.cur is not None and payload is self.cur:
                return i
            if kind == "folder" and self.sel_folder is not None and payload == self.sel_folder:
                return i
        return -1

    def _ensure_visible(self, i, total):
        if i < 0:
            return
        if i < self.top:
            self.top = i
        elif i >= self.top + MAX_T_SHOWN:
            self.top = i - MAX_T_SHOWN + 1
        self.top = max(0, min(self.top, max(0, total - MAX_T_SHOWN)))

    def _select_row(self, row):
        self.field = 0
        if row is None:
            self.cur = None
            self.sel_folder = None
        elif row[0] == "folder":
            self.cur = None
            self.sel_folder = row[1]
        else:
            self.cur = row[1]
            self.sel_folder = None

    def _select_index(self, delta, extend=False):
        rows = self._view()
        if not rows:
            return
        if not extend:
            self._clear_marks()
        i = max(0, min(len(rows) - 1, self._sel_index(rows) + delta))
        if extend and rows[i][0] == "event":
            self._extend(rows[i], toggle=False)
        else:
            self._select_row(rows[i])

    def _toggle_folder(self, name):
        if name in self.open_folders:
            self.open_folders.discard(name)
        else:
            self.open_folders.add(name)

    def _fields(self):
        batch = self._batch_targets()
        if batch:
            return self._batch_fields(batch)
        ev = self.cur
        if ev is None:
            return []
        rows = [("t", t("Время, мс"), 0, self.duration, 10)]
        rows += [(k, lbl, lo, hi, st) for k, lbl, lo, hi, st, _ in EV.FIELDS[ev["type"]]]
        if ev["type"] in ("image", "video"):
            rows += [("file", t("Ролик (images/)") if ev["type"] == "video" else t("Картинка (images/)"), None, None, None),
                     ("anim", t("Анимация"), None, None, None),
                     ("anim_id", t("Анимация из чарта"), None, None, None),
                     ("look", t("Эффект объекта"), None, None, None),
                     ("full", t("Растянуть на весь экран"), None, None, None)]
        if ev["type"] == "camera":
            rows += [("ease", t("Кривая движения"), None, None, None)]
        if ev["type"] == "transition":
            rows += [("kind", t("Вид перехода"), None, None, None),
                     ("mode", t("Режим"), None, None, None),
                     ("ease", t("Кривая движения"), None, None, None),
                     ("skip", t("Пропуск клавишей Enter"), None, None, None)]
        if ev["type"] == "pack":
            rows += [("pack", t("Пакет"), None, None, None)]
            pack = PK.get(ev.get("pack", ""))
            if pack is not None:
                rows += [(PARAM_PREFIX + p["id"], p["name"], p["min"], p["max"], p["step"]) for p in pack["params"]]
        if ev["type"] == "fx":
            rows += [("kind", t("Вид эффекта"), None, None, None),
                     ("beat", t("В такт (пульс по сетке)"), None, None, None)]
        if ev["type"] == "bg":
            rows += [("orig", t("Исходный цвет фона"), None, None, None)]
        if ev["type"] == "card":
            rows += [("text", t("Текст карточки"), None, None, None)]
        return rows

    def _value_text(self, key):
        batch = self._batch_targets()
        if batch:
            return self._batch_text(key, batch)
        ev = self.cur
        if key == "file":
            return ev["file"] or t("нет файлов в images/")
        if key == "anim":
            return t(EV.ANIM_NAMES[ev["anim"]])
        if key == "anim_id":
            anim = next((a for a in self.chart.animations if a["id"] == ev.get("anim_id")), None)
            return anim["name"] if anim else t("НЕТ")
        if key == "look":
            return t(FX.NAMES[ev.get("look", "")])
        if key == "kind" and ev["type"] == "transition":
            return t(CN.KIND_NAMES[ev["kind"]])
        if key == "kind":
            return t(FX.NAMES[ev["kind"]])
        if key == "mode":
            return t(CN.MODE_NAMES[ev["mode"]])
        if key == "ease":
            return t(AN.EASE_NAMES[ev["ease"]])
        if key == "skip":
            return t("ДА") if ev["skip"] else t("НЕТ")
        if key == "pack":
            return self._pack_name(ev.get("pack", ""))
        if key == "colour" and ev["type"] == "transition":
            return t(CN.COLOUR_NAMES[ev["colour"]])
        if key == "beat":
            return t("ДА") if ev.get("beat") else t("НЕТ")
        if key == "orig":
            return t("ДА") if ev["orig"] else t("НЕТ")
        if key == "full":
            return t("ДА") if ev.get("full") else t("НЕТ")
        if key == "text":
            return ev["text"]
        if key.startswith(PARAM_PREFIX):
            return _num_text(_ev_get(ev, key))
        if key == "t":
            return _fmt(ev["t"])
        return str(ev[key])

    def _adjust(self, key, lo, hi, step, direction):
        batch = self._batch_targets()
        if batch:
            self._adjust_batch(key, lo, hi, step, direction, batch)
            return
        ev = self.cur
        if ev is None or self._block_edit():
            return
        if key == "file":
            ev["file"] = EV.cycle(EV.list_media(ev["type"]), ev["file"], direction)
        elif key == "anim":
            ev["anim"] = EV.cycle(EV.ANIMS, ev["anim"], direction)
        elif key == "anim_id":
            ids = [""] + [a["id"] for a in self.chart.animations]
            ev["anim_id"] = EV.cycle(ids, ev.get("anim_id", ""), direction)
        elif key == "look":
            ev["look"] = EV.cycle(FX.LOOKS, ev.get("look", ""), direction)
        elif key == "kind":
            ev["kind"] = EV.cycle(CN.KINDS if ev["type"] == "transition" else FX.KINDS, ev["kind"], direction)
        elif key == "mode":
            ev["mode"] = EV.cycle(CN.MODES, ev["mode"], direction)
        elif key == "ease":
            ev["ease"] = EV.cycle(AN.EASES, ev["ease"], direction)
        elif key == "skip":
            ev["skip"] = not ev["skip"]
        elif key == "pack":
            ev["pack"] = EV.cycle(self._pack_ids(), ev.get("pack", ""), direction)
            ev["params"] = {}
            self.status = f"{t('Пакет')}: {self._pack_name(ev['pack'])}"
        elif key == "beat":
            ev["beat"] = not ev.get("beat", False)
        elif key == "orig":
            ev["orig"] = not ev["orig"]
        elif key == "full":
            ev["full"] = not ev.get("full", False)
            self.status = t("На весь экран: ДА") if ev["full"] else t("На весь экран: НЕТ")
        elif lo is not None and step is not None:
            self._set_value(key, _ev_get(ev, key) + direction * step, lo, hi)

    def _set_value(self, key, value, lo, hi):
        ev = self.cur
        if key.startswith(PARAM_PREFIX):
            ev.setdefault("params", {})[key[len(PARAM_PREFIX):]] = round(max(lo, min(hi, float(value))), 3)
            return
        ev[key] = max(lo, min(hi, int(value)))
        if key == "t":
            self._sort()
        elif key in ("r", "g", "b"):
            ev["orig"] = False

    def _fstep(self):
        n = len(self._fields())
        if n <= 11:
            return FIELD_STEP
        return FIELD_STEP_MID if n <= 13 else FIELD_STEP_DENSE

    def _row_at(self, pos):
        dx, dy = _design(pos)
        if not (PANEL_X <= dx <= PANEL_X + 380):
            return None
        for i in range(len(self._fields())):
            y = FIELD_Y + i * self._fstep()
            if y <= dy < y + 24:
                return i
        return None

    def _start_edit(self, i):
        key, label, _, _, _ = self._fields()[i]
        batch = self._batch_targets()
        if key in NO_EDIT or not self._targets() or (not batch and self._block_edit()):
            return
        self.field = i
        self.edit_key = key
        if batch:
            value = tracks.common_value(batch, key)
            self.edit_buf = "" if value is tracks.MIXED else str(value)
        else:
            self.edit_buf = _num_text(_ev_get(self.cur, key))
        self.edit_fresh = True
        if key == "text":
            self.status = t("Введите текст, ENTER — применить, ESC — отмена")
        else:
            self.status = t("Введите число, ENTER — применить, ESC — отмена")

    def _finish_edit(self, apply):
        key = self.edit_key
        buf = self.edit_buf
        self.edit_key = None
        self.edit_buf = ""
        batch = self._batch_targets()
        if batch and apply and key is not None and key != "text":
            self._finish_batch_edit(key, buf, batch)
            return
        if not apply or self.cur is None or key is None or self._block_edit():
            return
        if key == "text":
            self.cur["text"] = buf.strip()[:EV.CARD_TEXT_MAX] or "Текст"
            self.status = f"{t('Текст карточки')}: {self.cur['text']}"
            return
        try:
            value = float(buf) if key.startswith(PARAM_PREFIX) else int(buf)
        except ValueError:
            self.status = t("Нужно целое число")
            return
        row = next((r for r in self._fields() if r[0] == key), None)
        if row is None:
            return
        _, label, lo, hi, _ = row
        self._set_value(key, value, lo, hi)
        self.status = f"{t(label)}: {_num_text(_ev_get(self.cur, key))}"

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
        if self._block_edit():
            return
        size = EV.natural_size(ev)
        if size is None:
            self.status = t("Ролик не открылся") if ev["type"] == "video" else t("Картинка не найдена в images/")
            return
        w, h = EV.fit_box(size[0], size[1], SS.REF_W, SS.REF_H)
        ev["w"] = w
        if ev["type"] == "video":
            ev["h"] = h
        self.status = f"{t('Подогнано')}: {w} × {h}"

    def _reset_color(self):
        if self.cur is not None and self.cur["type"] == "bg" and not self._block_edit():
            self.cur["orig"] = True
            self.status = t("Фон: вернули исходный цвет")

    def _add(self, kind):
        ev = EV.make(kind, self.cursor)
        if kind == "pack":
            ids = sorted(PK.known_ids())
            ev["pack"] = ids[0] if ids else ""
        if self.kind_filter not in (None, kind):
            self.kind_filter = None
        self.chart.events.append(ev)
        self._sort()
        self.cur = ev
        self.sel_folder = None
        self.field = 0
        if kind == "image" and not ev["file"]:
            self.status = t("В папке images/ нет картинок (.png, .jpg). Положите файл и добавьте снова.")
        elif kind == "video" and not ev["file"]:
            self.status = t("В папке images/ нет роликов (.mp4, .webm, .mov, .avi, .mkv)")
        elif kind == "video" and not video.AVAILABLE:
            self.status = t("Для роликов нужен opencv-python: pip install opencv-python")
        elif kind == "pack" and not ev["pack"]:
            self.status = t("Пакетов нет: положите .json в папку packs/ и нажмите R в списке пакетов")
        else:
            self.status = f"{t('Добавлено')}: {t(EV.TYPE_NAMES[kind])} {t('в')} {_fmt(ev['t'])}"

    def _delete(self):
        if self.sel_folder is not None:
            self._delete_folder()
            return
        batch = self._batch_targets()
        if batch:
            self._delete_batch(batch)
            return
        if self.cur is None or self._block_edit():
            return
        idx = self._sel_index(self._view())
        self.chart.events.remove(self.cur)
        self.cur = None
        rows = self._view()
        if rows:
            self._select_row(rows[max(0, min(idx, len(rows) - 1))])
        self.field = 0
        self.status = t("Удалено")

    def _batch_fields(self, events):
        rows = [("t", t("Время, мс"), 0, self.duration, 10)]
        kinds = {e["type"] for e in events}
        rows += tracks.common_fields(kinds, lambda kind: [(k, lbl, lo, hi, st) for k, lbl, lo, hi, st, _ in EV.FIELDS[kind]])
        if kinds <= {"image", "video"}:
            rows.append(("full", t("Растянуть на весь экран"), None, None, None))
        if kinds == {"bg"}:
            rows.append(("orig", t("Исходный цвет фона"), None, None, None))
        return rows

    def _batch_text(self, key, events):
        if key in ("full", "orig"):
            values = {bool(e.get(key)) for e in events}
            if len(values) > 1:
                return "—"
            return t("ДА") if values.pop() else t("НЕТ")
        value = tracks.common_value(events, key)
        if value is tracks.MIXED:
            return "—"
        return _fmt(value) if key == "t" else str(value)

    def _adjust_batch(self, key, lo, hi, step, direction, events):
        if not tracks.unlocked(events):
            self.status = t(LOCKED_MSG)
            return
        if key in ("full", "orig"):
            changed = tracks.toggle_flag(events, key)
        elif lo is not None and step is not None:
            changed = tracks.shift_values(events, key, lo, hi, direction * step)
        else:
            return
        if key == "t":
            self._sort()
        self.status = f"{t('Изменено')}: {changed} {t('шт.')}"

    def _finish_batch_edit(self, key, buf, events):
        try:
            value = int(buf)
        except ValueError:
            self.status = t("Нужно целое число")
            return
        row = next((r for r in self._fields() if r[0] == key), None)
        if row is None or row[2] is None:
            return
        _, _, lo, hi, _ = row
        changed = tracks.set_values(events, key, value, lo, hi)
        if key == "t":
            self._sort()
        self.status = f"{t('Изменено')}: {changed} {t('шт.')}" if changed else t(LOCKED_MSG)

    def _delete_batch(self, events):
        free = tracks.unlocked(events)
        if not free:
            self.status = t(LOCKED_MSG)
            return
        if not dialogs.confirm(self.clock, t("Удалить выбранные события: {n}?").format(n=len(free))):
            self.status = t("Отменено")
            return
        idx = self._sel_index(self._view())
        removed, skipped = tracks.remove_events(self.chart.events, events)
        self._clear_marks()
        self.cur = None
        rows = self._view()
        if rows:
            self._select_row(rows[max(0, min(idx, len(rows) - 1))])
        self.field = 0
        self.status = f"{t('Удалено')}: {removed}" + (f" ({t('заблокировано')}: {skipped})" if skipped else "")

    def _copy(self):
        if self.cur is None:
            self.status = t("Сначала выберите событие")
            return
        self.clip = {k: v for k, v in self.cur.items() if k not in ("t", "folder", "locked")}
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
        free = [e for e in targets if not e.get("locked")]
        if not free:
            self.status = t(LOCKED_MSG)
            return
        for e in free:
            e.update({k: v for k, v in self.clip.items() if k not in ("type", "t")})
        skipped = len(targets) - len(free)
        self.status = f"{t('Свойства вставлены')}: {len(free)} {t('шт.')}"
        if skipped:
            self.status += f" ({t('заблокировано')}: {skipped})"

    def _duplicate(self):
        batch = self._batch_targets()
        if batch:
            copies = tracks.duplicate_at(batch, max(0, min(self.duration, self.cursor)), self.duration)
            self.chart.events.extend(copies)
            self._sort()
            self._clear_marks()
            for c in copies:
                self._mark(c, True)
            self.cur = copies[0]
            self.sel_folder = None
            self.field = 0
            self.status = f"{t('Копий')}: {len(copies)}"
            return
        if self.cur is None:
            return
        copy = dict(self.cur)
        copy["t"] = max(0, min(self.duration, self.cursor))
        copy["locked"] = False
        self.chart.events.append(copy)
        self._sort()
        self.cur = copy
        self.sel_folder = None
        self.field = 0
        self.status = f"{t('Копия в')} {_fmt(copy['t'])}"

    #-- Папки и блокировка

    def _toggle_sort(self):
        self.sort_mode = "type" if self.sort_mode == "time" else "time"
        self.status = f"{t('Сортировка')}: {t('по типу' if self.sort_mode == 'type' else 'по времени')}"

    def _new_folder(self):
        if len(self.chart.folders) >= MAX_FOLDERS:
            self.status = f"{t('Не больше')} {MAX_FOLDERS} {t('папок')}"
            return
        names = set(self._fold_names())
        n = len(names) + 1
        while f"{t('Папка')} {n}" in names:
            n += 1
        name = dialogs.ask_text(self.clock, t("Название новой папки"), f"{t('Папка')} {n}", 24)
        if name is None:
            self.status = t("Отменено")
            return
        if name in names:
            self.status = t("Папка с таким именем уже есть")
            return
        self.chart.folders.append(tracks.new_folder(name))
        self.open_folders.add(name)
        self._select_row(("folder", name))
        self.status = f"{t('Создана папка')}: {name}"

    def _to_folder(self):
        targets = self._targets()
        if not targets:
            self.status = t("Сначала выберите событие")
            return
        if not tracks.unlocked(targets):
            self.status = t(LOCKED_MSG)
            return
        if not self.chart.folders:
            self.status = t("Сначала создайте папку: + ПАПКА")
            return
        names = self._fold_names()
        options = [f"{n} ({t('заблокирована')})" if self._folder(n)["locked"] else n for n in names]
        options.append(t("Без папки"))
        idx = dialogs.choose(self.clock, t("Положить в папку"), options)
        if idx is None:
            self.status = t("Отменено")
            return
        target = names[idx] if idx < len(names) else ""
        if target and self._folder(target)["locked"]:
            self.status = t(FOLDER_LOCKED_MSG)
            return
        moved = tracks.assign_folder(targets, target)
        if target:
            self.open_folders.add(target)
        if len(targets) == 1:
            self.status = f"{t('Событие перемещено')}: {target or t('без папки')}"
        else:
            self.status = f"{t('Перемещено')}: {moved} · {target or t('без папки')}"

    def _from_folder(self):
        targets = self._targets()
        if not targets:
            self.status = t("Сначала выберите событие")
            return
        inside = [e for e in targets if e.get("folder")]
        if not inside:
            self.status = t("Событие уже без папки")
            return
        free = tracks.unlocked(inside)
        if not free:
            self.status = t(LOCKED_MSG)
            return
        free = [e for e in free if not self._folder_locked(e)]
        if not free:
            self.status = t(FOLDER_LOCKED_MSG)
            return
        tracks.assign_folder(free, "")
        if len(targets) == 1:
            self.status = t("Событие вынуто из папки")
        else:
            self.status = f"{t('Вынуто из папок')}: {len(free)}"

    def _rename_folder(self):
        if self.sel_folder is None:
            self.status = t("Выберите папку в списке")
            return
        f = self._folder(self.sel_folder)
        if f is None:
            return
        if f["locked"]:
            self.status = t(FOLDER_LOCKED_MSG)
            return
        old = f["name"]
        name = dialogs.ask_text(self.clock, t("Новое имя папки"), old, 24)
        if name is None or name == old:
            self.status = t("Отменено")
            return
        if name in self._fold_names():
            self.status = t("Папка с таким именем уже есть")
            return
        for e in self.chart.events:
            if e.get("folder") == old:
                e["folder"] = name
        f["name"] = name
        if old in self.open_folders:
            self.open_folders.discard(old)
            self.open_folders.add(name)
        self.sel_folder = name
        self.status = f"{t('Папка переименована')}: {name}"

    def _delete_folder(self):
        f = self._folder(self.sel_folder)
        if f is None:
            return
        if f["locked"]:
            self.status = t(FOLDER_LOCKED_MSG)
            return
        message = t("Папка «{n}» будет удалена, события останутся в списке.").format(n=f["name"])
        if not dialogs.confirm(self.clock, message):
            self.status = t("Отменено")
            return
        for e in self.chart.events:
            if e.get("folder") == f["name"]:
                e["folder"] = ""
        self.chart.folders.remove(f)
        self.open_folders.discard(f["name"])
        self.sel_folder = None
        self.status = t("Папка удалена")

    def _toggle_lock(self):
        if self.sel_folder is not None:
            f = self._folder(self.sel_folder)
            if f is None:
                return
            new = not f["locked"]
            f["locked"] = new
            for e in self._members(f["name"]):
                e["locked"] = new
            self.status = t("Папка заблокирована") if new else t("Папка разблокирована")
            return
        targets = self._targets()
        if not targets:
            self.status = t("Выберите событие или папку")
            return
        new = not all(e.get("locked") for e in targets)
        free = [e for e in targets if not self._folder_locked(e)]
        if not free:
            self.status = t(FOLDER_LOCKED_MSG)
            return
        tracks.set_flag(free, "locked", new)
        if len(targets) == 1:
            self.status = t("Событие заблокировано") if new else t("Событие разблокировано")
        else:
            self.status = f"{t('Заблокировано') if new else t('Разблокировано')}: {len(free)}"

    def _toggle_visible(self):
        if self.sel_folder is None:
            self.status = t("Выберите папку в списке")
            return
        f = self._folder(self.sel_folder)
        if f is None:
            return
        f["visible"] = not f.get("visible", True)
        if not f["visible"]:
            self._clear_marks()
            if self.cur is not None and self.cur.get("folder") == f["name"]:
                self.cur = None
        self.status = t("Дорожка показана") if f["visible"] else \
            t("Дорожка скрыта: её события не видны в списке, но играются")

    def _cycle_kind(self):
        if self.sel_folder is None:
            self.status = t("Выберите папку в списке")
            return
        f = self._folder(self.sel_folder)
        if f is None:
            return
        if f["locked"]:
            self.status = t(FOLDER_LOCKED_MSG)
            return
        f["kind"] = tracks.next_kind(f.get("kind", tracks.DEFAULT_KIND))
        self.status = f"{t('Тип дорожки')}: {t(tracks.KIND_NAMES[f['kind']])}"

    def _action(self, name):
        if name in ("glitch", "flash", "image", "video", "bg", "heal", "card", "invert", "fx",
                    "camera", "transition", "pack"):
            self._add(name)
        elif name == "anims":
            self._open_anims()
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
        elif name == "cursor" and self._batch_targets():
            moved = tracks.move_to(self._batch_targets(), max(0, min(self.duration, self.cursor)), self.duration)
            self._sort()
            self.status = f"{t('Перемещено')}: {moved} {t('шт.')}" if moved else t(LOCKED_MSG)
        elif name == "cursor" and self.cur is not None:
            if self._block_edit():
                return None
            self.cur["t"] = max(0, min(self.duration, self.cursor))
            self._sort()
            self.status = f"{t('Время события')}: {_fmt(self.cur['t'])}"
        elif name == "sort":
            self._toggle_sort()
        elif name == "newfolder":
            self._new_folder()
        elif name == "tofolder":
            self._to_folder()
        elif name == "unfolder":
            self._from_folder()
        elif name == "lock":
            self._toggle_lock()
        elif name == "rename":
            self._rename_folder()
        elif name == "visible":
            self._toggle_visible()
        elif name == "kind":
            self._cycle_kind()
        elif name == "back":
            return "back"
        return None

    def _pack_ids(self):
        return [""] + sorted(PK.known_ids())

    def _pack_name(self, pid):
        pack = PK.get(pid) if pid else None
        return pack.get("name", pid) if pack else t("НЕТ")

    def _browse_pack(self):
        """B: список пакетов с предпросмотром. Выбранный пакет записывается в выбранное событие «ПАКЕТ»."""
        if self.cur is None or self.cur["type"] != "pack":
            self.status = t("Выберите событие «ПАКЕТ»")
            return
        if self._block_edit():
            return
        import pack_browser
        chosen = pack_browser.run(self.clock, self.cur.get("pack", ""))
        if chosen is not None and chosen != self.cur.get("pack"):
            self.cur["pack"] = chosen
            self.cur["params"] = {}
            self.status = f"{t('Пакет')}: {self._pack_name(chosen)}"

    def _reset_rect(self):
        y = FIELD_Y + len(self._fields()) * self._fstep() + 6
        return pygame.Rect(PANEL_X, y, 200, 30)

    #-- Просмотр

    def _open_anims(self):
        aid = ""
        if self.cur is not None and self.cur["type"] in ("image", "video"):
            aid = self.cur.get("anim_id", "")
        anim_editor.run(self.clock, self.chart, aid)
        self.status = t("Вернулись из редактора анимаций")

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
        if ev["type"] == "card":
            EV.draw_card(scr, ev, e)
        if ev["type"] == "invert":
            EV.apply_invert(scr, EV.invert_level(ev, e))
        S.draw_grid(scr, e * 0.04, 0.0)
        if ev["type"] == "fx":
            self._draw_fx_sample(scr, ev, e)
        if ev["type"] in ("camera", "transition", "pack"):
            self._draw_cine_sample(scr, ev, e)
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
        pygame.draw.rect(scr, C.CYAN, (0, 0, int(C.WIDTH * progress), SS.U(4)))
        title = f"{t('ПРОСМОТР')}: {t(EV.TYPE_NAMES[ev['type']])}   {e / 1000:.2f} {t('с')}"
        S.blit_text(scr, S.font(18, True), title, C.WHITE, C.WIDTH // 2, SS.U(28))
        S.blit_text(scr, S.font(13), t("P или ESC — вернуться к редактору"), C.GREY, C.WIDTH // 2, C.HEIGHT - SS.U(26))
        S.post_fx(scr, self.frame, grain=20)

    def _draw_cine_sample(self, scr, ev, e):
        """Предпросмотр камеры, перехода и пакета: сэмпл из цветных дорожек, а поверх — сам эффект."""
        u = SS.U
        for i, col in enumerate(C.LANE_COLORS):
            pygame.draw.rect(scr, col, SS.UR(330 + i * 170, 220, 130, 280), border_radius=u(10))
        if ev["type"] == "camera":
            CN.apply_camera(scr, CN.build([dict(ev, t=0)]).camera_at(e), smooth=True)
        elif ev["type"] == "transition":
            CN.apply_overlay(scr, CN.build([dict(ev, t=0)]).overlay_at(e))
        else:
            pack = PK.get(ev.get("pack", ""))
            if pack is None:
                S.blit_text(scr, S.font(14, True), t("Пакет не выбран: нажмите B"), C.GOLD, C.WIDTH // 2, u(120))
                return
            inst = PK.make_instance(pack, ev.get("params"), ev.get("power", 100), ev.get("colour", 0), 1, ev["dur"])
            inst.draw(scr, e, C.WIDTH // 2, C.HEIGHT // 2)

    def _draw_fx_sample(self, scr, ev, e):
        u = SS.U
        for i, col in enumerate(C.LANE_COLORS):
            pygame.draw.rect(scr, col, SS.UR(330 + i * 170, 220, 130, 280), border_radius=u(10))
        if FX.budget().mode() == "off":
            S.blit_text(scr, S.font(14, True), t("Эффекты выключены в настройках"), C.GOLD, C.WIDTH // 2, u(120))
        FX.frame(scr, [(ev["kind"], FX.level(ev, ev["t"] + e))], e)

    #-- Цикл

    def run(self):
        while True:
            display.tick(self.clock)
            mouse = pygame.mouse.get_pos()
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if self._event(ev) == "back":
                    return
            self._tick_hold()
            self._draw(mouse)
            display.flip()
            self.frame += 1

    def _event(self, ev):
        if self.preview_t0 is not None:
            if ev.type == pygame.KEYDOWN and ev.key in (pygame.K_ESCAPE, pygame.K_p):
                self.preview_t0 = None
            elif ev.type == pygame.MOUSEBUTTONDOWN:
                self.preview_t0 = None
            return None
        if self.edit_key is not None and ev.type == pygame.KEYDOWN and self.edit_key == "text":
            if ev.key == pygame.K_ESCAPE:
                self._finish_edit(False)
            elif ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self._finish_edit(True)
            elif ev.key == pygame.K_BACKSPACE:
                self.edit_buf = "" if self.edit_fresh else self.edit_buf[:-1]
                self.edit_fresh = False
            elif ev.unicode and ev.unicode.isprintable():
                base = "" if self.edit_fresh else self.edit_buf
                if len(base) < EV.CARD_TEXT_MAX:
                    self.edit_buf = base + ev.unicode
                self.edit_fresh = False
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
            total = len(self._view())
            self.top = max(0, min(max(0, total - MAX_T_SHOWN), self.top - ev.y))
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
            elif k == pygame.K_a:
                self._mark_all()
            return None
        if k == pygame.K_ESCAPE:
            if self._marked():
                self._clear_marks()
                self.status = t("Выбор снят")
                return None
            return "back"
        extend = bool(mods & pygame.KMOD_SHIFT)
        if k == pygame.K_UP:
            self._select_index(-1, extend)
        elif k == pygame.K_DOWN:
            self._select_index(1, extend)
        elif k in (pygame.K_PAGEUP, pygame.K_PAGEDOWN):
            self._select_index((-1 if k == pygame.K_PAGEUP else 1) * MAX_T_SHOWN, extend)
        elif k in (pygame.K_HOME, pygame.K_END):
            rows = self._view()
            if rows:
                if not extend:
                    self._clear_marks()
                self._select_row(rows[0 if k == pygame.K_HOME else -1])
        elif k == pygame.K_v:
            self._toggle_visible()
        elif k == pygame.K_t:
            self._cycle_kind()
        elif k in (pygame.K_RETURN, pygame.K_KP_ENTER) and self.sel_folder is not None:
            self._toggle_folder(self.sel_folder)
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
        elif k == pygame.K_6:
            self._add("heal")
        elif k == pygame.K_7:
            self._add("card")
        elif k == pygame.K_8:
            self._add("invert")
        elif k == pygame.K_9:
            self._add("fx")
        elif k == pygame.K_b:
            self._browse_pack()
        elif k == pygame.K_m:
            self._open_anims()
        elif k == pygame.K_f:
            self._fit()
        elif k == pygame.K_p:
            self._start_preview()
        elif k == pygame.K_r:
            self._reset_color()
        elif k == pygame.K_l:
            self._toggle_lock()
        elif k == pygame.K_c:
            return self._action("cursor")
        elif k in (pygame.K_DELETE, pygame.K_BACKSPACE):
            self._delete()
        return None

    def _click(self, pos):
        for name, btn in self.buttons:
            if btn.rect.collidepoint(pos):
                return self._action(name)
        pos = _design(pos)
        for kind, rect in self.stat_rects.items():
            if rect.collidepoint(pos):
                self.kind_filter = None if self.kind_filter == kind else kind
                self.top = 0
                self.status = (f"{t('Показаны только')}: {t(EV.TYPE_NAMES[kind])}" if self.kind_filter
                               else t("Фильтр снят"))
                return None
        if self.cur is not None and self.cur["type"] == "bg" and not self._batch_targets() \
                and self._reset_rect().collidepoint(pos):
            self._reset_color()
            return None
        rows = self._view()
        for i in range(min(MAX_T_SHOWN, max(0, len(rows) - self.top))):
            row_rect = pygame.Rect(LIST_X, LIST_Y + i * ROW, LIST_W, ROW - 4)
            if row_rect.collidepoint(pos):
                kind, payload = rows[self.top + i]
                if kind == "folder" and pos[0] < LIST_X + 26:
                    self._toggle_folder(payload)
                if pygame.key.get_mods() & pygame.KMOD_SHIFT and kind == "event":
                    self._extend(rows[self.top + i], toggle=True)
                    return None
                self._clear_marks()
                self._select_row(rows[self.top + i])
                return None
        for i, (key, _, lo, hi, step) in enumerate(self._fields()):
            y = FIELD_Y + i * self._fstep()
            if pygame.Rect(PANEL_X, y, 200, 24).collidepoint(pos):
                self.field = i
            elif pygame.Rect(PANEL_X + 340, y, 22, 24).collidepoint(pos):
                self._adjust(key, lo, hi, step, -1)
                self.hold = (key, lo, hi, step, -1, time.perf_counter(), time.perf_counter())
            elif pygame.Rect(PANEL_X + 500, y, 22, 24).collidepoint(pos):
                self._adjust(key, lo, hi, step, 1)
                self.hold = (key, lo, hi, step, 1, time.perf_counter(), time.perf_counter())
            elif pygame.Rect(PANEL_X + 370, y, 120, 24).collidepoint(pos):
                self._start_edit(i)
        return None

    #-- Отрисовка

    def _draw_info(self, scr):
        u = SS.U
        counts, media_ms = EV.stats(self.chart.events)
        top = LIST_Y + MAX_T_SHOWN * ROW + 12
        title = t("СТАТИСТИКА")
        if self.kind_filter is not None:
            title = f"{t('ФИЛЬТР')}: {t(EV.TYPE_NAMES[self.kind_filter])}  ×"
        scr.blit(S.font(13, True).render(title, True, C.GOLD if self.kind_filter else (120, 160, 190)),
                 SS.UP(LIST_X, top))
        self.stat_rects = {}
        media = f"{t('медиа')}: {media_ms / 1000:.1f} {t('с')}"
        scr.blit(S.font(12).render(media, True, C.GREY),
                 (u(LIST_X + LIST_W) - S.font(12).size(media)[0], u(top + 2)))
        for i, kind in enumerate(EV.TYPES):
            col, row = i % 2, i // 2
            text = f"{t(EV.TYPE_NAMES[kind])}: {counts[kind]}"
            x, y = LIST_X + col * 150, top + 18 + row * 16
            self.stat_rects[kind] = pygame.Rect(u(x) - 2, u(y) - 1, u(140), u(16))
            active = self.kind_filter == kind
            if active:
                pygame.draw.rect(scr, (40, 40, 70), self.stat_rects[kind], border_radius=u(4))
            scr.blit(S.font(12, active).render(text, True, EV.TYPE_COLORS[kind]), SS.UP(x, y))

    def _draw_tooltip(self, scr, mouse, rows):
        u = SS.U
        kind = None
        for name, btn in self.buttons:
            if name in EV.TYPES and btn.hovered(mouse):
                kind = name
        x, y = mouse
        dx, dy = _design(mouse)
        if kind is None and LIST_X <= dx < LIST_X + LIST_W and LIST_Y <= dy < LIST_Y + MAX_T_SHOWN * ROW:
            idx = self.top + (dy - LIST_Y) // ROW
            if idx < len(rows) and rows[idx][0] == "event":
                kind = rows[idx][1]["type"]
        if kind is None:
            return
        fnt = S.font(13)
        lines = _wrap(t(EV.DESCRIPTIONS[kind]), fnt, u(300))
        w = max(fnt.size(line)[0] for line in lines) + u(20)
        h = len(lines) * u(17) + u(14)
        bx = min(max(u(8), x + u(16)), C.WIDTH - w - u(8))
        by = min(max(u(8), y + u(18)), C.HEIGHT - h - u(8))
        box = pygame.Rect(bx, by, w, h)
        pygame.draw.rect(scr, (14, 14, 34), box, border_radius=u(6))
        pygame.draw.rect(scr, EV.TYPE_COLORS[kind], box, u(1), border_radius=u(6))
        for i, line in enumerate(lines):
            scr.blit(fnt.render(line, True, (210, 210, 230)), (bx + u(10), by + u(7) + i * u(17)))

    def _draw_list(self, scr, rows):
        u = SS.U
        if not rows:
            S.blit_text(scr, S.font(13), t("Событий пока нет"), C.GREY,
                        u(LIST_X + LIST_W // 2), u(LIST_Y + 20))
        for i in range(min(MAX_T_SHOWN, max(0, len(rows) - self.top))):
            kind, payload = rows[self.top + i]
            y = LIST_Y + i * ROW
            if kind == "folder":
                selected = payload == self.sel_folder
                folder = self._folder(payload)
                pygame.draw.rect(scr, (40, 40, 70) if selected else (24, 34, 50),
                                 SS.UR(LIST_X, y, LIST_W, ROW - 4), border_radius=u(6))
                arrow = "▼" if payload in self.open_folders else "▶"
                count = len(self._members(payload))
                label = f"{arrow} {payload} ({count})"
                shown = folder is None or folder.get("visible", True)
                if folder and folder.get("kind", tracks.DEFAULT_KIND) != tracks.DEFAULT_KIND:
                    label += f" · {t(tracks.KIND_NAMES[folder['kind']])}"
                if not shown:
                    label += f" · {t('СКРЫТА')}"
                base = (150, 190, 215) if shown else (105, 110, 135)
                col = C.GOLD if selected else base
                scr.blit(S.font(13, True).render(label[:34], True, col), SS.UP(LIST_X + 8, y + 4))
                if folder and folder["locked"]:
                    _draw_lock(scr, u(LIST_X + LIST_W - 20), u(y + 5), C.GOLD)
                continue
            ev = payload
            selected = ev is self.cur
            indent = 16 if ev.get("folder") else 0
            if selected:
                pygame.draw.rect(scr, (40, 40, 70), SS.UR(LIST_X, y, LIST_W, ROW - 4), border_radius=u(6))
            if self._is_marked(ev):
                pygame.draw.rect(scr, C.GOLD, SS.UR(LIST_X, y, LIST_W, ROW - 4), u(1), border_radius=u(6))
            color = EV.TYPE_COLORS[ev["type"]]
            label = f"{_fmt(ev['t'])}  {t(EV.TYPE_NAMES[ev['type']])}"
            if ev["type"] in ("image", "video") and ev["file"]:
                label += f"  {ev['file']}"
            scr.blit(S.font(13, selected).render(label[:34 - indent // 2], True, color),
                     SS.UP(LIST_X + 8 + indent, y + 4))
            if ev.get("locked"):
                _draw_lock(scr, u(LIST_X + LIST_W - 20), u(y + 5), C.GOLD)

    def _draw_folder_info(self, scr):
        f = self._folder(self.sel_folder)
        if f is None:
            return
        lines = [
            (f"{t('Папка')}: {f['name']}", C.WHITE, True),
            (f"{t('Событий')}: {len(self._members(f['name']))}", C.GREY, False),
            (f"{t('Заблокирована')}: {t('ДА') if f['locked'] else t('НЕТ')}", C.GREY, False),
            (f"{t('Тип дорожки')}: {t(tracks.KIND_NAMES[f.get('kind', tracks.DEFAULT_KIND)])}", C.GREY, False),
            (f"{t('Показана в списке')}: {t('ДА') if f.get('visible', True) else t('НЕТ')}", C.GREY, False),
            (t("V — показать или скрыть · T — сменить тип · Enter — свернуть"), (170, 170, 200), False),
            (t("Выберите событие слева, чтобы положить его в папку или вынуть из неё."), (170, 170, 200), False),
        ]
        for i, (text, col, bold) in enumerate(lines):
            scr.blit(S.font(15, bold).render(text, True, col), SS.UP(PANEL_X, FIELD_Y + 4 + i * 26))

    def _draw(self, mouse):
        u = SS.U
        scr = pygame.display.get_surface()
        if self.preview_t0 is not None:
            self._draw_preview(scr)
            return
        scr.fill(C.BG_DARK)
        S.draw_grid(scr, self.frame * 0.2, 0.0)
        S.blit_text(scr, S.font(24, True), t("СОБЫТИЯ ПЕСНИ"), C.CYAN, C.WIDTH // 2, u(24))

        target_locked = (self._folder(self.sel_folder) or {}).get("locked") if self.sel_folder is not None \
            else bool(self.cur and self.cur.get("locked"))
        self.btns["sort"].set_label(t(f"СОРТ: {'ТИП' if self.sort_mode == 'type' else 'ВРЕМЯ'}"))
        batch = self._batch_targets()
        if batch:
            target_locked = all(e.get("locked") for e in batch)
        self.btns["lock"].set_label(t("РАЗМКНУТЬ" if target_locked else "ЗАМКНУТЬ"))
        folder_now = self._folder(self.sel_folder) if self.sel_folder is not None else None
        self.btns["visible"].set_label(t("ПОКАЗАТЬ" if folder_now and not folder_now.get("visible", True) else "СКРЫТЬ"))
        self.btns["kind"].set_label(f"{t('ТИП')}: {t(tracks.KIND_NAMES[(folder_now or {}).get('kind', tracks.DEFAULT_KIND)])}")

        for label, row_y in self.section_labels:
            scr.blit(S.font(12, True).render(t(label), True, (120, 160, 190)), SS.UP(16, row_y + 9))
        for name, btn in self.buttons:
            btn.draw(scr, mouse)

        rows = self._view()
        self._ensure_visible(self._sel_index(rows), len(rows))
        self._draw_list(scr, rows)

        fields = self._fields()
        if self.sel_folder is not None:
            self._draw_folder_info(scr)
        elif self.cur is None:
            S.blit_text(scr, S.font(16), t("Выберите событие слева или добавьте новое"),
                        C.GREY, u(PANEL_X + 240), u(FIELD_Y + 20))
        for i, (key, label, row_lo, _, _) in enumerate(fields):
            y = FIELD_Y + i * self._fstep()
            active = i == self.field
            if active:
                pygame.draw.rect(scr, (40, 40, 70), SS.UR(PANEL_X - 8, y - 1, 720, 26), border_radius=u(6))
            unused = bool(not self._batch_targets() and self.cur is not None and self.cur.get("full")
                          and key in FULL_IGNORED)
            scr.blit(S.font(13, active).render(t(label), True, C.WHITE if active and not unused else
                                               C.DIM if unused else C.GREY), SS.UP(PANEL_X, y + 5))
            if self.edit_key == key:
                caret = "_" if (self.frame // 30) % 2 == 0 else " "
                value = S.font(13, True).render(self.edit_buf + caret, True, C.GOLD)
            else:
                value = S.font(13, True).render(self._value_text(key)[:18], True, C.DIM if unused else C.CYAN)
            scr.blit(value, (u(PANEL_X + 432) - value.get_width() // 2, u(y + 5)))
            if row_lo is not None:
                S.draw_disc(scr, u(PANEL_X + 351), u(y + 12), u(16))
                S.draw_disc(scr, u(PANEL_X + 511), u(y + 12), u(16))
                pygame.draw.rect(scr, C.DIM, SS.UR(PANEL_X + 340, y, 22, 24), u(1), border_radius=u(5))
                pygame.draw.rect(scr, C.DIM, SS.UR(PANEL_X + 500, y, 22, 24), u(1), border_radius=u(5))
                S.blit_text(scr, S.font(14, True), "−", C.WHITE, u(PANEL_X + 351), u(y + 12))
                S.blit_text(scr, S.font(14, True), "+", C.WHITE, u(PANEL_X + 511), u(y + 12))

        if self.cur is not None and self.cur["type"] == "bg" and not self._batch_targets():
            rect = self._reset_rect()
            prect = SS.UR(rect.x, rect.y, rect.w, rect.h)
            pygame.draw.rect(scr, C.GOLD if prect.collidepoint(mouse) else C.DIM, prect, u(2), border_radius=u(6))
            S.blit_text(scr, S.font(13, True), t("ВЕРНУТЬ ИСХОДНЫЙ"), C.GOLD, prect.centerx, prect.centery)
            swatch = pygame.Rect(prect.right + u(12), prect.y, u(60), prect.h)
            pygame.draw.rect(scr, EV.bg_target(self.cur), swatch, border_radius=u(6))
            pygame.draw.rect(scr, C.DIM, swatch, u(1), border_radius=u(6))

        if self.cur is not None and self.field < len(fields):
            hint = t(_hint_text(self.cur, fields[self.field][0]))
            S.blit_text(scr, S.font(13), hint, (170, 170, 200), C.WIDTH // 2, u(592))

        beta = t("Картинки и ролики: кладите .png / .jpg / .mp4 / .webm в папку images/ рядом с main.py (БЕТА)")
        S.blit_text(scr, S.font(13), beta, (150, 150, 190), C.WIDTH // 2, u(634))
        self._draw_info(scr)
        self._draw_tooltip(scr, mouse, rows)
        if self.status:
            S.blit_text(scr, S.font(13, True), self.status, C.GOLD, C.WIDTH // 2, u(614))
        S.blit_text(scr, S.font(12),
                    t("↑↓ PgUp PgDn Home End · Enter папка · Tab поле · ←→ изменить (Shift ×5) · 1–9 добавить · M анимации · клик по счётчику — фильтр · P просмотр"),
                    (110, 110, 150), C.WIDTH // 2, u(652))
        S.blit_text(scr, S.font(12),
                    t("Ctrl+C копировать · Ctrl+V вставить · Ctrl+Shift+V всем таким · Ctrl+D копия · L замок · Del удалить · ESC назад"),
                    (110, 110, 150), C.WIDTH // 2, u(674))
        S.blit_text(scr, S.font(12),
                    t("Shift+клик или Shift+↑↓ — выбрать несколько · Ctrl+A — все видимые · V — скрыть дорожку · T — тип"),
                    (110, 110, 150), C.WIDTH // 2, u(696))
        S.post_fx(scr, self.frame, grain=20)


def run(clock, chart, cursor_ms, duration):
    EventsScreen(clock, chart, cursor_ms, duration).run()
