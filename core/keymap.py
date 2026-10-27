#-- Привязка клавиш меню и редактора
# Действие -> список клавиш (по именам pygame). Первая клавиша главная: именно её меняют в настройках,
# остальные остаются запасными. Стрелки, Enter и Esc в меню работают всегда, чтобы нельзя было
# заблокировать себя неудачной привязкой. Дорожки игры настраиваются отдельно (settings.lane_keys).
import pygame

import settings

MENU, SONGS, EDITOR = "menu", "songs", "editor"
SECTIONS = (MENU, SONGS, EDITOR)
# Вкладки экрана: вкладка -> разделы. Меню и список песен делят одно пространство клавиш.
TABS = (("menu", (MENU, SONGS)), ("editor", (EDITOR,)))
GROUP = {MENU: "ui", SONGS: "ui", EDITOR: "editor"}

# (id, раздел, подпись, клавиши по умолчанию, запасные клавиши, нужен Ctrl)
_RAW = (
    ("up", MENU, "Вверх", ("up", "w"), ("up",), False),
    ("down", MENU, "Вниз", ("down", "s"), ("down",), False),
    ("left", MENU, "Влево (уменьшить)", ("left", "a"), ("left",), False),
    ("right", MENU, "Вправо (увеличить)", ("right", "d"), ("right",), False),
    ("confirm", MENU, "Выбрать", ("return", "space"), ("return", "enter"), False),
    ("back", MENU, "Назад", ("escape",), ("escape",), False),
    ("random", SONGS, "Случайная песня", ("r",), (), False),
    ("dev", SONGS, "Режим разработчика", ("7", "[7]"), (), False),
    ("search", SONGS, "Поиск по песням", ("/", "f"), (), False),
    ("sort", SONGS, "Сменить сортировку", ("tab",), (), False),
    ("favorite", SONGS, "Избранное: песня / чарт", ("b",), (), False),
    ("fav_filter", SONGS, "Только избранное", ("l",), (), False),
    ("practice_chart", SONGS, "Практика", ("p",), (), False),
    ("edit_chart", SONGS, "Редактировать чарт", ("e",), (), False),
    ("new_chart", SONGS, "Новый чарт", ("n",), (), False),
    ("delete_chart", SONGS, "Удалить чарт", ("delete",), (), False),
    ("play", EDITOR, "Играть / пауза", ("space",), (), False),
    ("save", EDITOR, "Сохранить (с Ctrl)", ("s",), (), True),
    ("undo", EDITOR, "Отмена (с Ctrl)", ("z",), (), True),
    ("seek_left", EDITOR, "Курсор назад", ("left",), (), False),
    ("seek_right", EDITOR, "Курсор вперёд", ("right",), (), False),
    ("zoom_in", EDITOR, "Масштаб крупнее", ("up",), (), False),
    ("zoom_out", EDITOR, "Масштаб мельче", ("down",), (), False),
    ("to_start", EDITOR, "В начало", ("home",), (), False),
    ("to_end", EDITOR, "В конец", ("end",), (), False),
    ("back5", EDITOR, "Назад на 5 с", ("page up",), (), False),
    ("fwd5", EDITOR, "Вперёд на 5 с", ("page down",), (), False),
    ("speed_down", EDITOR, "Медленнее", ("-", "[-]"), (), False),
    ("speed_up", EDITOR, "Быстрее", ("=", "[+]"), (), False),
    ("fx", EDITOR, "Эффекты вкл / выкл", ("v",), (), False),
    ("snap", EDITOR, "Привязка к сетке вкл / выкл", ("g",), (), False),
    ("shift_left", EDITOR, "Сдвиг нот −10 мс", ("[",), (), False),
    ("shift_right", EDITOR, "Сдвиг нот +10 мс", ("]",), (), False),
    ("rename", EDITOR, "Название чарта", ("f2",), (), False),
    ("delete_note", EDITOR, "Удалить ноту", ("delete", "backspace"), (), False),
    ("redo", EDITOR, "Повтор (с Ctrl)", ("y",), (), True),
    ("select_all", EDITOR, "Выделить все ноты (с Ctrl)", ("a",), (), True),
    ("copy", EDITOR, "Копировать выделение (с Ctrl)", ("c",), (), True),
    ("paste", EDITOR, "Вставить в курсор (с Ctrl)", ("v",), (), True),
    ("deselect", EDITOR, "Снять выделение", ("u",), (), False),
    ("nudge_back", EDITOR, "Сдвинуть выделенное раньше", (",",), (), False),
    ("nudge_fwd", EDITOR, "Сдвинуть выделенное позже", (".",), (), False),
    ("lane_prev", EDITOR, "Выделенное на дорожку левее", ("o",), (), False),
    ("lane_next", EDITOR, "Выделенное на дорожку правее", ("p",), (), False),
    ("quantize", EDITOR, "Привязать выделенное к сетке", ("q",), (), False),
    ("grid_div", EDITOR, "Следующее деление сетки", ("h",), (), False),
    ("tap", EDITOR, "Тап-темп (BPM)", ("t",), (), False),
    ("menu", EDITOR, "Меню редактора", ("escape",), ("escape",), False),
)

ACTIONS = {a[0]: {"id": a[0], "section": a[1], "label": a[2], "default": tuple(a[3]),
                  "fallback": tuple(a[4]), "ctrl": a[5]} for a in _RAW}
ORDER = [a[0] for a in _RAW]

RESERVED = {"escape", "f1", "f3"}      # Esc отменяет ввод, F1 и F3 — общие клавиши окна
_MODIFIERS = {"left shift", "right shift", "left ctrl", "right ctrl", "left alt", "right alt",
              "left meta", "right meta", "caps lock", "left super", "right super", "numlock"}

_PRETTY = {"up": "↑", "down": "↓", "left": "←", "right": "→", "return": "Enter", "enter": "Num Enter",
           "space": "Space", "escape": "Esc", "backspace": "Backspace", "delete": "Del", "tab": "Tab",
           "page up": "PgUp", "page down": "PgDn", "home": "Home", "end": "End"}

_codes = {}


def _overrides():
    raw = settings.get("keys")
    return raw if isinstance(raw, dict) else {}


def _valid(name):
    try:
        pygame.key.key_code(name)
        return True
    except Exception:
        return False


def names(action):
    """Текущие клавиши действия (по именам); неверные записи в настройках игнорируются."""
    got = _overrides().get(action)
    if isinstance(got, list) and got and all(isinstance(n, str) and _valid(n) for n in got):
        return tuple(got)
    return ACTIONS[action]["default"]


def codes(action):
    names_now = names(action)
    key = (action, names_now)
    cached = _codes.get(key)
    if cached is None:
        out = [pygame.key.key_code(n) for n in names_now]
        out += [pygame.key.key_code(n) for n in ACTIONS[action]["fallback"] if _valid(n)]
        cached = _codes[key] = tuple(dict.fromkeys(out))
    return cached


def hit(action, key):
    return key in codes(action)


def pretty(name):
    if name in _PRETTY:
        return _PRETTY[name]
    if name.startswith("[") and name.endswith("]") and len(name) > 2:
        return "Num " + name[1:-1].upper()
    return name.upper() if len(name) == 1 else name.title()


def label(action):
    return pretty(names(action)[0])


def labels(action):
    return "  ·  ".join(pretty(n) for n in names(action))


def is_custom(action):
    return names(action) != ACTIONS[action]["default"]


def section_actions(section):
    return [a for a in ORDER if ACTIONS[a]["section"] == section]


def _group_peers(action):
    info = ACTIONS[action]
    return [a for a in ORDER if a != action and GROUP[ACTIONS[a]["section"]] == GROUP[info["section"]]
            and ACTIONS[a]["ctrl"] == info["ctrl"]]


def _store(action, new_names):
    data = dict(_overrides())
    if tuple(new_names) == ACTIONS[action]["default"]:
        data.pop(action, None)
    else:
        data[action] = list(new_names)
    settings.set("keys", data)


def rebind(action, name):
    """Назначает главную клавишу действия. Возвращает (успех, сообщение/None, действие_с_которым_поменялись)."""
    name = (name or "").lower()
    if not name or not _valid(name):
        return False, "bad", None
    if name in RESERVED or name in _MODIFIERS:
        return False, "reserved", None
    info = ACTIONS[action]
    if info["section"] == EDITOR and not info["ctrl"]:
        if name in [n.lower() for n in settings.get("lane_keys")]:
            return False, "lane", None
    cur = list(names(action))
    if cur[0] == name:
        return True, None, None
    old_primary = cur[0]
    new = [name] + [n for n in cur[1:] if n != name]
    swapped = None
    for other in _group_peers(action):
        on = list(names(other))
        if name not in on:
            continue
        if on[0] == name:
            on[0] = old_primary if old_primary not in on else on[0]
            if on[0] == name:            # старая клавиша уже есть у соседа — берём его запасную
                on = [n for n in on if n != name] or list(ACTIONS[other]["default"])
        else:
            on.remove(name)
        _store(other, on)
        swapped = other
    _store(action, new)
    return True, None, swapped


def reset_action(action):
    data = dict(_overrides())
    if action in data:
        del data[action]
        settings.set("keys", data)


def reset_tab(tab):
    """Сбрасывает привязки вкладки (меню+песни или редактор) к значениям по умолчанию."""
    sections = dict(TABS)[tab]
    data = {a: v for a, v in _overrides().items() if a in ACTIONS and ACTIONS[a]["section"] not in sections}
    settings.set("keys", data)


def editor_conflict(name):
    """Название действия редактора, которое уже занимает эту клавишу (для проверки клавиш дорожек)."""
    name = (name or "").lower()
    for a in section_actions(EDITOR):
        if not ACTIONS[a]["ctrl"] and name in names(a):
            return ACTIONS[a]["label"]
    return None
