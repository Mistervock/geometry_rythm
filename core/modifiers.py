"""Модификаторы сложности (Geometry Rhythm 7.0): переключаемые правила для любого чарта.

Набор — список {"id", "value"} в каноническом порядке ORDER. Хранится в двух местах:
  * в чарте, поле "modifiers" — рекомендуемый набор автора (формат v6);
  * в data/modifiers.json — выбор игрока для каждого чарта; он важнее рекомендации автора.

Модификаторы меняют только игровую картинку и темп (зеркало, скорость, скрытые ноты). Ноты чарта
и правила очков не трогаются, поэтому рекорды, ранги и призраки раскладываются по наборам через suffix().

SPEEDS — множители без 1.0 (1.0 означает «модификатор выключен», поэтому в списке его нет).
HIDDEN_FADE_IN и HIDDEN_FULL — доли пути до линии попадания: скрытая нота начинает появляться на первой,
а полностью видна становится на второй.
"""
#-- Импорт
import config as C
import jsonio

#-- Определения
ORDER = ("mirror", "speed", "hidden")
LANES = 4
SPEEDS = (0.75, 1.25, 1.5)
HIDDEN_FADE_IN = 0.70
HIDDEN_FULL = 0.35
PATH = C.root("data", "modifiers.json")

TITLES = {"mirror": "ЗЕРКАЛО", "speed": "СКОРОСТЬ", "hidden": "СКРЫТЫЕ"}
DESCS = {
    "mirror": "Дорожки отзеркалены: ноты приходят справа налево",
    "speed": "Ноты летят быстрее или медленнее; музыка не меняется",
    "hidden": "Ноты появляются только в последней трети пути до линии попадания",
}


#-- Нормализация

def normalize(raw, warn=None):
    """Приводит сырой список к каноническому виду. Ошибочные записи отбрасываются.

    warn(code, **args) — необязательный приёмник предупреждений (для валидации чарта).
    Возвращает список {"id", "value"} в порядке ORDER без повторов."""
    def note(code, **args):
        if warn is not None:
            warn(code, **args)

    if raw is None:
        return []
    if not isinstance(raw, list):
        note("modifiers.type")
        return []
    found = {}
    for item in raw:
        if not isinstance(item, dict):
            note("modifiers.item_type")
            continue
        mid = item.get("id")
        if mid not in ORDER:
            note("modifiers.unknown", id=str(mid)[:24])
            continue
        value = item.get("value", True)
        if mid == "speed":
            if not isinstance(value, (int, float)) or isinstance(value, bool) or float(value) not in SPEEDS:
                note("modifiers.value", id=mid)
                continue
            value = float(value)
        else:
            if not isinstance(value, bool):
                note("modifiers.value", id=mid)
                continue
            if not value:
                continue
            value = True
        if mid in found:
            note("modifiers.duplicate", id=mid)
            continue
        found[mid] = value
    return [{"id": mid, "value": found[mid]} for mid in ORDER if mid in found]


def as_dict(mods):
    """{id: value} для быстрых проверок. Пустой набор — пустой словарь."""
    return {m["id"]: m["value"] for m in normalize(mods)}


def has(mods, mid):
    return mid in as_dict(mods)


def describe(mods):
    """Короткая строка для HUD и результатов: «ЗЕРКАЛО · СКОРОСТЬ 1.25× · СКРЫТЫЕ» или ''."""
    parts = []
    for m in normalize(mods):
        if m["id"] == "speed":
            parts.append(f"{TITLES['speed']} {m['value']:g}×")
        else:
            parts.append(TITLES[m["id"]])
    return " · ".join(parts)


def tag(mods):
    """Короткая метка для таблицы рекордов: ' [MIR · 1.25× · HID]' или ''."""
    parts = []
    for m in normalize(mods):
        if m["id"] == "mirror":
            parts.append("MIR")
        elif m["id"] == "speed":
            parts.append(f"{m['value']:g}×")
        else:
            parts.append("HID")
    return f" [{' · '.join(parts)}]" if parts else ""


def suffix(mods):
    """Суффикс для ключей рекордов и призраков. Без модификаторов — пустая строка (старые ключи не меняются)."""
    parts = []
    for m in normalize(mods):
        if m["id"] == "mirror":
            parts.append("mir")
        elif m["id"] == "speed":
            parts.append(f"spd{round(m['value'] * 100)}")
        else:
            parts.append("hid")
    return "__" + "-".join(parts) if parts else ""


#-- Влияние на игру

def scroll_for(base_ms, mods):
    """Время пути ноты (мс) с учётом скорости. base_ms — настройка scroll_ms."""
    speed = as_dict(mods).get("speed", 1.0)
    return float(base_ms) / float(speed)


def mirror_lane(lane, lanes=LANES):
    return lanes - 1 - lane


def hidden_alpha(dt, scroll):
    """Видимость скрытой ноты: dt — мс до попадания, scroll — время пути. 0..1."""
    if dt <= HIDDEN_FULL * scroll:
        return 1.0
    if dt >= HIDDEN_FADE_IN * scroll:
        return 0.0
    return (HIDDEN_FADE_IN * scroll - dt) / ((HIDDEN_FADE_IN - HIDDEN_FULL) * scroll)


#-- Выбор игрока

def load_choice(chart):
    """Выбор игрока для чарта или None, если он ещё не сохранён."""
    key = chart.id or chart.key
    if not key:
        return None
    raw = jsonio.load(PATH, {}, expect=dict)
    entry = raw.get(key) if isinstance(raw, dict) else None
    if entry is None:
        return None
    return normalize(entry)


def save_choice(chart, mods):
    key = chart.id or chart.key
    if not key:
        return False
    raw = jsonio.load(PATH, {}, expect=dict)
    if not isinstance(raw, dict):
        raw = {}
    raw[key] = normalize(mods)
    ok, _ = jsonio.try_write(PATH, raw, indent=2)
    return ok


def effective(chart, mode="play"):
    """Набор, с которым запускается чарт: выбор игрока, иначе рекомендация автора.

    Практика без модификаторов: у неё свой темп и она не пишет рекорды."""
    if mode == "practice":
        return []
    chosen = load_choice(chart)
    return chosen if chosen is not None else normalize(getattr(chart, "modifiers", []))
