"""Анимации объектов (Geometry Rhythm 7.0, пункт 4): ключевые кадры, интерполяция и цикл.

Анимация — запись в чарте (поле chart.animations): {"id", "name", "dur", "loop", "keys"}. dur — длительность
в мс; loop — зацикливание; keys — ключи, отсортированные по t (мс от начала анимации). Ключ задаёт значения
свойств в момент t; между ключами значения интерполируются по типу перехода ease левого ключа.
Свойства: x, y — смещение в пикселях базового экрана; scale — масштаб в процентах (100 — исходный размер);
rot — поворот в градусах; alpha — прозрачность в процентах; tint — цвет умножения [r, g, b] (255 — без изменения).

Анимация привязывается к картинке или видео через поле события anim_id и запускается вместе с событием.
Модуль не зависит от pygame и других модулей проекта: его используют валидация, редактор и тесты.
"""
#-- Импорт
import secrets

#-- Определения
EASES = ("linear", "ease_in", "ease_out", "ease_in_out", "step")
EASE_NAMES = {"linear": "ЛИНЕЙНО", "ease_in": "РАЗГОН", "ease_out": "ТОРМОЖЕНИЕ",
              "ease_in_out": "МЯГКО", "step": "СТУПЕНЬКА"}
NUMERIC = ("x", "y", "scale", "rot", "alpha")
LIMITS = {"x": (-900, 900), "y": (-600, 600), "scale": (10, 400), "rot": (-720, 720), "alpha": (0, 100)}
DEFAULT_VALUES = {"x": 0, "y": 0, "scale": 100, "rot": 0, "alpha": 100, "tint": (255, 255, 255)}
DEFAULT_EASE = "ease_in_out"
DUR_LIMITS = (100, 60000)
DEFAULT_DUR = 1000
MAX_KEYS = 64
MAX_ANIMS = 64
NAME_MAX = 32
DEFAULT_NAME = "Анимация"


#-- Ключи и значения

def make_key(t, ease=DEFAULT_EASE, **values):
    key = {"t": int(t), "ease": ease}
    for prop in NUMERIC:
        key[prop] = values.get(prop, DEFAULT_VALUES[prop])
    key["tint"] = list(values.get("tint", DEFAULT_VALUES["tint"]))
    return key


def _rounded_key(t, vals):
    """Ключ из значений, полученных интерполяцией: числа округлены, чтобы в чарте не было дробных значений."""
    out = make_key(t)
    for prop in NUMERIC:
        out[prop] = int(round(vals[prop]))
    out["tint"] = [int(round(c)) for c in vals["tint"]]
    return out


def new_id(existing=()):
    while True:
        cand = secrets.token_hex(4)
        if cand not in existing:
            return cand


def new_animation(name=DEFAULT_NAME, existing_ids=()):
    return {"id": new_id(existing_ids), "name": name[:NAME_MAX], "dur": DEFAULT_DUR, "loop": False,
            "keys": [make_key(0), make_key(DEFAULT_DUR)]}


def ease(name, p):
    p = min(max(float(p), 0.0), 1.0)
    if name == "ease_in":
        return p * p
    if name == "ease_out":
        return 1.0 - (1.0 - p) ** 2
    if name == "ease_in_out":
        return p * p * (3.0 - 2.0 * p)
    if name == "step":
        return 0.0 if p < 1.0 else 1.0
    return p


def _values(key):
    out = {prop: key[prop] for prop in NUMERIC}
    out["tint"] = tuple(key["tint"])
    return out


def _lerp(a, b, e):
    return a + (b - a) * e


def sample(anim, t_ms):
    """Значения свойств анимации в момент t_ms (мс от её начала). Без цикла время зажимается в [0, dur]."""
    keys = anim["keys"]
    dur = anim["dur"]
    if anim.get("loop") and dur > 0:
        t = t_ms % dur
        timeline = [k for k in keys if k["t"] < dur] + [dict(keys[0], t=dur)]
    else:
        t = min(max(t_ms, 0), dur)
        timeline = keys
    if t <= timeline[0]["t"]:
        return _values(timeline[0])
    if t >= timeline[-1]["t"]:
        return _values(timeline[-1])
    for a, b in zip(timeline, timeline[1:]):
        if a["t"] <= t <= b["t"]:
            span = b["t"] - a["t"]
            e = ease(a["ease"], (t - a["t"]) / span if span > 0 else 1.0)
            out = {prop: _lerp(a[prop], b[prop], e) for prop in NUMERIC}
            out["tint"] = tuple(round(_lerp(ca, cb, e)) for ca, cb in zip(a["tint"], b["tint"]))
            return out
    return _values(timeline[-1])


#-- Проверка и нормализация

def _num(value, lo, hi, default, warn, code):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        if warn is not None:
            warn(code)
        return default
    return min(max(value, lo), hi)


def _normalize_key(raw, dur, loop, warn):
    if not isinstance(raw, dict):
        if warn is not None:
            warn("anim.key_type")
        return None
    t = _num(raw.get("t", 0), 0, dur, 0, warn, "anim.value")
    ease_name = raw.get("ease", DEFAULT_EASE)
    if ease_name not in EASES:
        if warn is not None:
            warn("anim.ease")
        ease_name = DEFAULT_EASE
    key = {"t": int(round(t)), "ease": ease_name}
    for prop in NUMERIC:
        lo, hi = LIMITS[prop]
        key[prop] = _num(raw.get(prop, DEFAULT_VALUES[prop]), lo, hi, DEFAULT_VALUES[prop], warn, "anim.value")
    tint = raw.get("tint", list(DEFAULT_VALUES["tint"]))
    if (not isinstance(tint, list) or len(tint) != 3
            or not all(isinstance(c, int) and not isinstance(c, bool) for c in tint)):
        if warn is not None:
            warn("anim.value")
        tint = list(DEFAULT_VALUES["tint"])
    key["tint"] = [min(max(c, 0), 255) for c in tint]
    if loop and key["t"] >= dur and warn is not None:
        warn("anim.loop_key")
    return key


def normalize(raw, existing_ids=(), warn=None):
    """Проверенная анимация или None. Лишние и неверные значения исправляются или отбрасываются с предупреждением.

    existing_ids — id, которые уже заняты в чарте (повтор получает новый id)."""
    if not isinstance(raw, dict):
        if warn is not None:
            warn("anim.item_type")
        return None
    dur = _num(raw.get("dur", DEFAULT_DUR), DUR_LIMITS[0], DUR_LIMITS[1], DEFAULT_DUR, warn, "anim.value")
    dur = int(round(dur))
    loop = raw.get("loop", False) is True
    name = raw.get("name", DEFAULT_NAME)
    if not isinstance(name, str) or not name.strip():
        name = DEFAULT_NAME
    aid = raw.get("id")
    if not isinstance(aid, str) or not aid or len(aid) > 16 or aid in existing_ids:
        if warn is not None:
            warn("anim.id")
        aid = new_id(existing_ids)
    raw_keys = raw.get("keys")
    if not isinstance(raw_keys, list):
        if warn is not None:
            warn("anim.keys")
        raw_keys = []
    keys = []
    for item in raw_keys:
        key = _normalize_key(item, dur, loop, warn)
        if key is not None:
            keys.append(key)
    if len(keys) > MAX_KEYS:
        if warn is not None:
            warn("anim.too_many_keys", n=MAX_KEYS)
        keys = keys[:MAX_KEYS]
    keys.sort(key=lambda k: k["t"])
    unique = []
    for key in keys:
        if unique and unique[-1]["t"] == key["t"]:
            if warn is not None:
                warn("anim.duplicate_key")
            continue
        unique.append(key)
    if not unique:
        unique = [make_key(0), make_key(dur)]
    if unique[0]["t"] > 0:
        first = unique[0]
        unique.insert(0, dict(first, t=0, tint=list(first["tint"])))
    return {"id": aid, "name": name[:NAME_MAX], "dur": dur, "loop": loop, "keys": unique}


def normalize_list(raw, warn=None):
    """Список анимаций чарта: без повторов id и не больше MAX_ANIMS."""
    if raw is None:
        return []
    if not isinstance(raw, list):
        if warn is not None:
            warn("anim.list_type")
        return []
    out = []
    ids = []
    for item in raw:
        if len(out) >= MAX_ANIMS:
            if warn is not None:
                warn("anim.too_many", n=MAX_ANIMS)
            break
        anim = normalize(item, ids, warn)
        if anim is not None:
            out.append(anim)
            ids.append(anim["id"])
    return out


def by_id(animations):
    return {a["id"]: a for a in animations or []}


#-- Правка (для редактора)

def add_key(anim, t):
    """Добавляет ключ в момент t со значениями анимации в этой точке. Возвращает индекс ключа."""
    t = int(min(max(t, 0), anim["dur"]))
    for i, key in enumerate(anim["keys"]):
        if key["t"] == t:
            return i
    key = _rounded_key(t, sample(anim, t))
    anim["keys"].append(key)
    anim["keys"].sort(key=lambda k: k["t"])
    return anim["keys"].index(key)


def remove_key(anim, index):
    """Удаляет ключ. Ключ в t=0 и последний оставшийся ключ удалить нельзя. Возвращает True, если удалён."""
    keys = anim["keys"]
    if len(keys) <= 1 or index <= 0 or index >= len(keys):
        return False
    del keys[index]
    return True


def set_dur(anim, dur):
    """Меняет длительность. При укорочении ключи за новой длительностью удаляются, а в её конце ставится ключ
    со значениями, которые анимация имела в этот момент, — так кадр в конце не меняется."""
    dur = int(min(max(dur, DUR_LIMITS[0]), DUR_LIMITS[1]))
    if dur < anim["dur"]:
        vals = sample(anim, dur)
        keys = [k for k in anim["keys"] if k["t"] < dur]
        keys.append(_rounded_key(dur, vals))
        anim["keys"] = keys
    anim["dur"] = dur
    return anim
