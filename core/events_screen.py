#-- Импорт
import math
import sys
import time

import pygame

import config as C
import dialogs
import display
import events as EV
import screen_setting as SS
import style as S
import video
from i18n import t

#-- Раскладка
ROW1_Y, ROW2_Y, ROW3_Y, ROW4_Y, BTN_H = 54, 96, 138, 180, 32
LIST_X, LIST_Y, ROW, LIST_W = 16, 226, 28, 380
PANEL_X = 440
FIELD_Y, FIELD_STEP = 226, 30
FIELD_STEP_TIGHT = 27          # строк больше 11 (ролик с «на весь экран»): чуть теснее, чтобы влезли над подсказкой
MAX_T_SHOWN = 8
MAX_FOLDERS = 8
PREVIEW_BG_MS = 1500
PREVIEW_PAUSE_MS = 500
HOLD_DELAY = 0.35
HOLD_RATE = 0.06
NO_EDIT = ("file", "anim", "orig", "full")
FULL_IGNORED = ("w", "h", "x", "y", "dx", "dy")     # при «на весь экран» размер и смещение не используются
LOCKED_MSG = "Событие заблокировано: нажмите РАЗМКНУТЬ, чтобы изменить"
FOLDER_LOCKED_MSG = "Папка заблокирована: сначала разблокируйте её"

#-- Разделы кнопок
SECTIONS = (
    ("ДОБАВИТЬ", ROW1_Y, (("glitch", "+ ГЛЮК"), ("flash", "+ ВСПЫШКА"),
                         ("image", "+ КАРТИНКА"), ("video", "+ ВИДЕО"), ("bg", "+ ФОН"), ("heal", "+ ХИЛЛ"), ("card", "+ КАРТОЧКА"), ("invert", "+ ИНВЕРСИЯ"))),
    ("ПРАВКА", ROW2_Y, (("copy", "КОПИРОВАТЬ"), ("paste", "ВСТАВИТЬ"), ("paste_all", "ВСЕМ ТАКИМ"),
                       ("dup", "ДУБЛИРОВАТЬ"), ("delete", "УДАЛИТЬ"))),
    ("ВИД", ROW3_Y, (("preview", "▶ ПРОСМОТР"), ("cursor", "В КУРСОР"), ("fit", "ПОДОГНАТЬ"), ("back", "НАЗАД"))),
    ("ПАПКИ", ROW4_Y, (("sort", "СОРТ: ВРЕМЯ"), ("newfolder", "+ ПАПКА"), ("tofolder", "В ПАПКУ"),
                      ("unfolder", "ИЗ ПАПКИ"), ("lock", "ЗАМКНУТЬ"), ("rename", "ПЕРЕИМЕНОВАТЬ"))),
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
    "anim": "РЕЗКО — появилась и пропала; ПЛАВНО — с затуханием; ДВИЖЕНИЕ — плывёт",
    "r": "Красная составляющая фона, 0–255",
    "g": "Зелёная составляющая фона, 0–255",
    "b": "Синяя составляющая фона, 0–255",
    "orig": "ДА — вернуть исходный цвет фона; ручное изменение цвета выключает это",
    "lane": "Дорожка, в которой упадёт белый круг: 1 — D, 2 — F, 3 — J, 4 — K",
    "speed": "Во сколько раз круг падает быстрее обычных нот: 170% — в 1.7 раза",
    "text": "Текст, который появится на экране. Клик по полю или ENTER — ввести, ESC — отмена",
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
        self.cur = chart.events[0] if chart.events else None
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
        self.white = pygame.Surface((C.WIDTH, C.HEIGHT))
        self.white.fill(C.WHITE)
        self.buttons = []
        self.btns = {}
        self.section_labels = []
        for label, row_y, items in SECTIONS:
            self.section_labels.append((label, row_y))
            for i, (name, text) in enumerate(items):
                btn = S.Btn(SS.UR(100 + i * 132, row_y, 124, BTN_H), t(text), C.CYAN, S.font(12, True))
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
        """Строки списка: ('folder', имя) и ('event', событие). Порядок: папки, затем события без папки."""
        key = self._sort_key()
        names = set(self._fold_names())
        rows = []
        for f in self.chart.folders:
            rows.append(("folder", f["name"]))
            if f["name"] in self.open_folders:
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

    def _select_index(self, delta):
        rows = self._view()
        if not rows:
            return
        i = max(0, min(len(rows) - 1, self._sel_index(rows) + delta))
        self._select_row(rows[i])

    def _toggle_folder(self, name):
        if name in self.open_folders:
            self.open_folders.discard(name)
        else:
            self.open_folders.add(name)

    def _fields(self):
        ev = self.cur
        if ev is None:
            return []
        rows = [("t", t("Время, мс"), 0, self.duration, 10)]
        rows += [(k, lbl, lo, hi, st) for k, lbl, lo, hi, st, _ in EV.FIELDS[ev["type"]]]
        if ev["type"] in ("image", "video"):
            rows += [("file", t("Ролик (images/)") if ev["type"] == "video" else t("Картинка (images/)"), None, None, None),
                     ("anim", t("Анимация"), None, None, None),
                     ("full", t("Растянуть на весь экран"), None, None, None)]
        if ev["type"] == "bg":
            rows += [("orig", t("Исходный цвет фона"), None, None, None)]
        if ev["type"] == "card":
            rows += [("text", t("Текст карточки"), None, None, None)]
        return rows

    def _value_text(self, key):
        ev = self.cur
        if key == "file":
            return ev["file"] or t("нет файлов в images/")
        if key == "anim":
            return t(EV.ANIM_NAMES[ev["anim"]])
        if key == "orig":
            return t("ДА") if ev["orig"] else t("НЕТ")
        if key == "full":
            return t("ДА") if ev.get("full") else t("НЕТ")
        if key == "text":
            return ev["text"]
        if key == "t":
            return _fmt(ev["t"])
        return str(ev[key])

    def _adjust(self, key, lo, hi, step, direction):
        ev = self.cur
        if ev is None or self._block_edit():
            return
        if key == "file":
            ev["file"] = EV.cycle(EV.list_media(ev["type"]), ev["file"], direction)
        elif key == "anim":
            ev["anim"] = EV.cycle(EV.ANIMS, ev["anim"], direction)
        elif key == "orig":
            ev["orig"] = not ev["orig"]
        elif key == "full":
            ev["full"] = not ev.get("full", False)
            self.status = t("На весь экран: ДА") if ev["full"] else t("На весь экран: НЕТ")
        elif lo is not None and step is not None:
            self._set_value(key, ev[key] + direction * step, lo, hi)

    def _set_value(self, key, value, lo, hi):
        ev = self.cur
        ev[key] = max(lo, min(hi, int(value)))
        if key == "t":
            self._sort()
        elif key in ("r", "g", "b"):
            ev["orig"] = False

    def _fstep(self):
        return FIELD_STEP_TIGHT if len(self._fields()) > 11 else FIELD_STEP

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
        if key in NO_EDIT or self.cur is None or self._block_edit():
            return
        self.field = i
        self.edit_key = key
        self.edit_buf = str(self.cur[key])
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
        if not apply or self.cur is None or key is None or self._block_edit():
            return
        if key == "text":
            self.cur["text"] = buf.strip()[:EV.CARD_TEXT_MAX] or "Текст"
            self.status = f"{t('Текст карточки')}: {self.cur['text']}"
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
        else:
            self.status = f"{t('Добавлено')}: {t(EV.TYPE_NAMES[kind])} {t('в')} {_fmt(ev['t'])}"

    def _delete(self):
        if self.sel_folder is not None:
            self._delete_folder()
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
        self.chart.folders.append({"name": name, "locked": False})
        self.open_folders.add(name)
        self._select_row(("folder", name))
        self.status = f"{t('Создана папка')}: {name}"

    def _to_folder(self):
        if self.cur is None:
            self.status = t("Сначала выберите событие")
            return
        if self._block_edit():
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
        self.cur["folder"] = target
        if target:
            self.open_folders.add(target)
        self.status = f"{t('Событие перемещено')}: {target or t('без папки')}"

    def _from_folder(self):
        if self.cur is None:
            self.status = t("Сначала выберите событие")
            return
        if not self.cur.get("folder"):
            self.status = t("Событие уже без папки")
            return
        if self._block_edit():
            return
        if self._folder(self.cur["folder"])["locked"]:
            self.status = t(FOLDER_LOCKED_MSG)
            return
        self.cur["folder"] = ""
        self.status = t("Событие вынуто из папки")

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
        ev = self.cur
        if ev is None:
            self.status = t("Выберите событие или папку")
            return
        parent = self._folder(ev.get("folder", ""))
        if parent is not None and parent["locked"]:
            self.status = t(FOLDER_LOCKED_MSG)
            return
        ev["locked"] = not ev.get("locked", False)
        self.status = t("Событие заблокировано") if ev["locked"] else t("Событие разблокировано")

    def _action(self, name):
        if name in ("glitch", "flash", "image", "video", "bg", "heal", "card", "invert"):
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
        elif name == "back":
            return "back"
        return None

    def _reset_rect(self):
        y = FIELD_Y + len(self._fields()) * self._fstep() + 6
        return pygame.Rect(PANEL_X, y, 200, 30)  # расчётные координаты

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
        if ev["type"] == "card":
            EV.draw_card(scr, ev, e)
        if ev["type"] == "invert":
            EV.apply_invert(scr, EV.invert_level(ev, e))
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
        pygame.draw.rect(scr, C.CYAN, (0, 0, int(C.WIDTH * progress), SS.U(4)))
        title = f"{t('ПРОСМОТР')}: {t(EV.TYPE_NAMES[ev['type']])}   {e / 1000:.2f} {t('с')}"
        S.blit_text(scr, S.font(18, True), title, C.WHITE, C.WIDTH // 2, SS.U(28))
        S.blit_text(scr, S.font(13), t("P или ESC — вернуться к редактору"), C.GREY, C.WIDTH // 2, C.HEIGHT - SS.U(26))
        S.post_fx(scr, self.frame, grain=20)

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
            return None
        if k == pygame.K_ESCAPE:
            return "back"
        if k == pygame.K_UP:
            self._select_index(-1)
        elif k == pygame.K_DOWN:
            self._select_index(1)
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
        if self.cur is not None and self.cur["type"] == "bg" and self._reset_rect().collidepoint(pos):
            self._reset_color()
            return None
        rows = self._view()
        for i in range(min(MAX_T_SHOWN, max(0, len(rows) - self.top))):
            row_rect = pygame.Rect(LIST_X, LIST_Y + i * ROW, LIST_W, ROW - 4)
            if row_rect.collidepoint(pos):
                kind, payload = rows[self.top + i]
                if kind == "folder" and pos[0] < LIST_X + 26:
                    self._toggle_folder(payload)
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
        scr.blit(S.font(13, True).render(t("СТАТИСТИКА"), True, (120, 160, 190)), SS.UP(LIST_X, top))
        media = f"{t('медиа')}: {media_ms / 1000:.1f} {t('с')}"
        scr.blit(S.font(12).render(media, True, C.GREY),
                 (u(LIST_X + LIST_W) - S.font(12).size(media)[0], u(top + 2)))
        for i, kind in enumerate(EV.TYPES):
            col, row = i % 2, i // 2
            text = f"{t(EV.TYPE_NAMES[kind])}: {counts[kind]}"
            scr.blit(S.font(12).render(text, True, EV.TYPE_COLORS[kind]),
                     SS.UP(LIST_X + col * 150, top + 18 + row * 16))

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
                col = C.GOLD if selected else (150, 190, 215)
                scr.blit(S.font(13, True).render(label[:34], True, col), SS.UP(LIST_X + 8, y + 4))
                if folder and folder["locked"]:
                    _draw_lock(scr, u(LIST_X + LIST_W - 20), u(y + 5), C.GOLD)
                continue
            ev = payload
            selected = ev is self.cur
            indent = 16 if ev.get("folder") else 0
            if selected:
                pygame.draw.rect(scr, (40, 40, 70), SS.UR(LIST_X, y, LIST_W, ROW - 4), border_radius=u(6))
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
        self.btns["lock"].set_label(t("РАЗМКНУТЬ" if target_locked else "ЗАМКНУТЬ"))

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
            unused = bool(self.cur is not None and self.cur.get("full") and key in FULL_IGNORED)
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

        if self.cur is not None and self.cur["type"] == "bg":
            rect = self._reset_rect()
            prect = SS.UR(rect.x, rect.y, rect.w, rect.h)
            pygame.draw.rect(scr, C.GOLD if prect.collidepoint(mouse) else C.DIM, prect, u(2), border_radius=u(6))
            S.blit_text(scr, S.font(13, True), t("ВЕРНУТЬ ИСХОДНЫЙ"), C.GOLD, prect.centerx, prect.centery)
            swatch = pygame.Rect(prect.right + u(12), prect.y, u(60), prect.h)
            pygame.draw.rect(scr, EV.bg_target(self.cur), swatch, border_radius=u(6))
            pygame.draw.rect(scr, C.DIM, swatch, u(1), border_radius=u(6))

        if self.cur is not None and self.field < len(fields):
            hint = t(HINTS.get(fields[self.field][0], ""))
            S.blit_text(scr, S.font(13), hint, (170, 170, 200), C.WIDTH // 2, u(560))

        beta = t("Картинки и ролики: кладите .png / .jpg / .mp4 / .webm в папку images/ рядом с main.py (БЕТА)")
        S.blit_text(scr, S.font(13), beta, (150, 150, 190), C.WIDTH // 2, u(592))
        self._draw_info(scr)
        self._draw_tooltip(scr, mouse, rows)
        if self.status:
            S.blit_text(scr, S.font(13, True), self.status, C.GOLD, C.WIDTH // 2, u(618))
        S.blit_text(scr, S.font(12),
                    t("↑↓ событие · Enter раскрыть папку · Tab поле · ←→ изменить (Shift ×5) · 1–8 добавить · P просмотр · R исходный фон"),
                    (110, 110, 150), C.WIDTH // 2, u(652))
        S.blit_text(scr, S.font(12),
                    t("Ctrl+C копировать · Ctrl+V вставить · Ctrl+Shift+V всем таким · Ctrl+D копия · L замок · Del удалить · ESC назад"),
                    (110, 110, 150), C.WIDTH // 2, u(674))
        S.post_fx(scr, self.frame, grain=20)


def run(clock, chart, cursor_ms, duration):
    EventsScreen(clock, chart, cursor_ms, duration).run()
