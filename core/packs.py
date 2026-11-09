"""Пакеты визуальных эффектов: готовые наборы слоёв, которые автор ставит событием «ПАКЕТ».

Пакет — JSON-файл. Поставляемые пакеты лежат в packs/, пользовательские — в data/packs/; пользовательский пакет с
тем же id заменяет поставляемый. Код игры при этом не меняется: добавить эффект значит положить файл.

Формат (format = "geometry-rhythm-pack", api = 1):
  id           латиница, цифры и «_», 2–32 символа
  name, description, dur (мс, 100–20000)
  params       до 6 настраиваемых чисел: {id, name, min, max, step, default}
  layers       до 8 слоёв. Вид: ring (кольцо), particles (частицы, trail — со следом), flash (вспышка-диск).
               Общие поля слоя: start и end (доли длительности события, 0…1).
               Числовые поля: число, пара [от, до] (меняется за слой) или строка "$имя_параметра".
               Цвет: "#rrggbb", либо "$colour" (цвет события, индекс палитры 0…5).

Проверка при загрузке: неверный формат, битый id или новый api — пакет не попадает в библиотеку; мелкие ошибки
(диапазоны, неизвестный слой) исправляются и попадают в отчёт. Пакет не падает на ошибке в одном слое.
"""
import json
import math
import os
import random
import re

import pygame

import config as C
import screen_setting as SS

FORMAT = "geometry-rhythm-pack"
API = 1
BUILTIN_DIR = C.root("packs")
USER_DIR = C.root("data", "packs")
LAYER_KINDS = ("ring", "particles", "flash")
PALETTE = ("#ffffff", "#ffd27a", "#ff6a6a", "#6ad8ff", "#7dff9a", "#c08bff")
MAX_LAYERS = 8
MAX_PARTICLES = 96
MAX_PARAMS = 6
MAX_PACK_DUR = 20000
MAX_ACTIVE = 12
ID_RE = re.compile(r"^[a-z0-9_]{2,32}$")
PARAM_ID_RE = re.compile(r"^[a-z0-9_]{1,16}$")
SPEED_MAX = 1200
RADIUS_MAX = 400

_REG = None
_ISSUES = []


#-- Проверка

def _num(raw, lo, hi, default, where, probs):
    if isinstance(raw, bool) or not isinstance(raw, (int, float)):
        probs.append(("pack.field_type", where))
        return default
    v = float(raw)
    if not math.isfinite(v):
        probs.append(("pack.field_type", where))
        return default
    if v < lo or v > hi:
        probs.append(("pack.range", where))
    return max(lo, min(hi, v))


def _elem(raw, lo, hi, default, where, probs, params):
    if isinstance(raw, str) and raw.startswith("$"):
        if raw[1:] in params:
            return raw
        probs.append(("pack.unknown_param", where))
        return default
    return _num(raw, lo, hi, default, where, probs)


def _count(raw, params, where, probs):
    if isinstance(raw, str) and raw.startswith("$"):
        if raw[1:] in params:
            return raw
        probs.append(("pack.unknown_param", where))
        return 12
    return int(_num(raw, 1, 48, 12, where, probs))


def _pair_or_num(raw, lo, hi, default, where, probs, params):
    if isinstance(raw, list) and len(raw) == 2:
        return [_elem(raw[0], lo, hi, default, where, probs, params),
                _elem(raw[1], lo, hi, default, where, probs, params)]
    return _elem(raw, lo, hi, default, where, probs, params)


def _colour(raw, where, probs):
    if raw == "$colour":
        return raw
    if isinstance(raw, str) and re.fullmatch(r"#[0-9a-fA-F]{6}", raw):
        return raw.lower()
    probs.append(("pack.colour", where))
    return PALETTE[0]


def _params(raw, probs):
    out = []
    if raw is None:
        return out
    if not isinstance(raw, list):
        probs.append(("pack.params_type", "params"))
        return out
    for i, p in enumerate(raw[:MAX_PARAMS]):
        where = f"params[{i}]"
        if not isinstance(p, dict) or not isinstance(p.get("id"), str) or not PARAM_ID_RE.match(p["id"]):
            probs.append(("pack.param_id", where))
            continue
        lo = _num(p.get("min", 0), -100000, 100000, 0, where + ".min", probs)
        hi = _num(p.get("max", 100), -100000, 100000, 100, where + ".max", probs)
        if hi <= lo:
            probs.append(("pack.range", where))
            hi = lo + 1
        step = _num(p.get("step", 1), 0.001, 100000, 1, where + ".step", probs)
        default = _num(p.get("default", lo), lo, hi, lo, where + ".default", probs)
        out.append({"id": p["id"], "name": str(p.get("name", p["id"]))[:24], "min": lo, "max": hi,
                    "step": step, "default": default})
    if len(raw) > MAX_PARAMS:
        probs.append(("pack.too_many", "params"))
    return out


def _layer(raw, i, params, probs):
    where = f"layers[{i}]"
    if not isinstance(raw, dict):
        probs.append(("pack.layer_type", where))
        return None
    kind = raw.get("kind")
    if kind not in LAYER_KINDS:
        probs.append(("pack.layer_kind", where))
        return None
    start = _num(raw.get("start", 0), 0, 1, 0, where + ".start", probs)
    end = _num(raw.get("end", 1), 0, 1, 1, where + ".end", probs)
    if end <= start:
        probs.append(("pack.range", where + ".end"))
        end = min(1.0, start + 0.05)
    L = {"kind": kind, "start": start, "end": end}
    alpha = raw.get("alpha", [255, 0])
    L["alpha"] = _pair_or_num(alpha, 0, 255, 255, where + ".alpha", probs, params)
    L["colour"] = _colour(raw.get("colour", "$colour"), where + ".colour", probs)
    if kind == "ring":
        L["radius"] = _pair_or_num(raw.get("radius", [0, 120]), 0, RADIUS_MAX, 0, where + ".radius", probs, params)
        L["width"] = _pair_or_num(raw.get("width", 6), 1, 40, 6, where + ".width", probs, params)
    elif kind == "flash":
        L["radius"] = _pair_or_num(raw.get("radius", [40, 140]), 0, RADIUS_MAX, 0, where + ".radius", probs, params)
    else:
        L["count"] = _count(raw.get("count", 12), params, where + ".count", probs)
        L["speed"] = _pair_or_num(raw.get("speed", [80, 260]), 0, SPEED_MAX, 0, where + ".speed", probs, params)
        L["size"] = _pair_or_num(raw.get("size", [2, 5]), 1, 30, 2, where + ".size", probs, params)
        L["gravity"] = _pair_or_num(raw.get("gravity", 0), -2000, 2000, 0, where + ".gravity", probs, params)
        L["spread"] = _num(raw.get("spread", 360), 0, 360, 360, where + ".spread", probs)
        L["trail"] = raw.get("trail") is True
        L["length"] = _num(raw.get("length", 0), 0, 200, 0, where + ".length", probs)
    return L


def validate(raw):
    """Проверяет пакет. Возвращает (чистый пакет или None, список проблем: [(код, место)])."""
    probs = []
    if not isinstance(raw, dict):
        return None, [("pack.not_object", "")]
    if raw.get("format") != FORMAT:
        return None, [("pack.format", str(raw.get("format"))[:24])]
    api = raw.get("api")
    if isinstance(api, bool) or not isinstance(api, int):
        return None, [("pack.api", "api")]
    if api > API:
        return None, [("pack.api_new", str(api))]
    pid = raw.get("id")
    if not isinstance(pid, str) or not ID_RE.match(pid):
        return None, [("pack.id", "id")]
    params = _params(raw.get("params"), probs)
    names = {p["id"] for p in params}
    dur = _num(raw.get("dur", 1000), 100, MAX_PACK_DUR, 1000, "dur", probs)
    raw_layers = raw.get("layers")
    if not isinstance(raw_layers, list) or not raw_layers:
        return None, [("pack.no_layers", "layers")]
    if len(raw_layers) > MAX_LAYERS:
        probs.append(("pack.too_many", "layers"))
    layers = []
    for i, rl in enumerate(raw_layers[:MAX_LAYERS]):
        L = _layer(rl, i, names, probs)
        if L is not None:
            layers.append(L)
    if not layers:
        return None, probs + [("pack.no_layers", "layers")]
    clean = {"id": pid, "name": str(raw.get("name", pid))[:40], "description": str(raw.get("description", ""))[:200],
             "dur": int(dur), "params": params, "layers": layers}
    return clean, probs


def _json_files(folder):
    try:
        names = sorted(os.listdir(folder))
    except OSError:
        return []
    return [os.path.join(folder, n) for n in names if n.lower().endswith(".json") and not n.startswith("_")]


def load_file(path):
    """Читает один файл пакета. Возвращает (пакет или None, проблемы)."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except (OSError, ValueError) as e:
        return None, [("pack.file", str(e)[:80])]
    return validate(raw)


def reload(builtin=None, user=None):
    """Перечитывает библиотеку. Пользовательский пакет заменяет поставляемый с тем же id."""
    global _REG, _ISSUES
    reg, issues = {}, []
    for folder in (builtin or BUILTIN_DIR, user or USER_DIR):
        for path in _json_files(folder):
            pack, probs = load_file(path)
            name = os.path.basename(path)
            for code, where in probs:
                issues.append((name, code, where))
            if pack is None:
                continue
            if pack["id"] in reg:
                issues.append((name, "pack.duplicate", pack["id"]))
            reg[pack["id"]] = pack
    _REG = reg
    _ISSUES = issues
    return reg


def registry():
    if _REG is None:
        reload()
    return _REG


def issues():
    registry()
    return list(_ISSUES)


def known_ids():
    return set(registry())


def get(pid):
    return registry().get(pid)


#-- Экземпляры и отрисовка

def resolve_params(pack, values):
    """Значения параметров: из события, с ограничением диапазона, по умолчанию для отсутствующих."""
    out = {}
    raw = values if isinstance(values, dict) else {}
    for p in pack["params"]:
        v = raw.get(p["id"], p["default"])
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(float(v)):
            v = p["default"]
        out[p["id"]] = max(p["min"], min(p["max"], float(v)))
    return out


def _val(x, params):
    if isinstance(x, str) and x.startswith("$"):
        return params.get(x[1:], 0.0)
    return x


def _span(x, params, rnd):
    if isinstance(x, list):
        a, b = _val(x[0], params), _val(x[1], params)
        return a + (b - a) * rnd.random()
    return float(_val(x, params))


def _lerp_field(x, params, p):
    if isinstance(x, list):
        a, b = _val(x[0], params), _val(x[1], params)
        return a + (b - a) * p
    return float(_val(x, params))


def _colour_of(spec, colour_idx):
    if spec == "$colour":
        return PALETTE[colour_idx % len(PALETTE)]
    return spec


def _rgb(hexs):
    h = hexs.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


class Instance:
    """Один запущенный пакет: слои с уже выбранными случайными частицами (детерминированно по seed)."""

    def __init__(self, pack, values, power, colour_idx, seed, dur):
        params = resolve_params(pack, values)
        k = max(0.1, min(2.0, power / 100.0))
        rnd = random.Random(seed)
        self.dur = max(1, dur)
        self.layers = []
        budget = MAX_PARTICLES
        for L in pack["layers"]:
            R = dict(L)
            R["colour_rgb"] = _rgb(_colour_of(L["colour"], colour_idx))
            if L["kind"] == "particles":
                n = min(budget, max(1, int(round(_val(L["count"], params) * k))))
                budget -= n
                items = []
                for _ in range(n):
                    if L["spread"] >= 360:
                        ang = rnd.random() * 2 * math.pi
                    else:
                        ang = -math.pi / 2 + math.radians(L["spread"]) * (rnd.random() - 0.5)
                    sp = _span(L["speed"], params, rnd) * k
                    items.append((math.cos(ang) * sp, math.sin(ang) * sp, _span(L["size"], params, rnd) * k))
                R["items"] = items
                R["gravity_v"] = _span(L["gravity"], params, rnd) * k
            self.layers.append(R)
        self.params = params
        self.power = k

    def draw(self, surface, elapsed, ox, oy):
        draw(surface, self, elapsed, ox, oy)


def make_instance(pack, values, power, colour_idx, seed, dur):
    return Instance(pack, values, power, colour_idx, seed, dur)


def _scaled(rgb, a):
    f = max(0.0, min(1.0, a / 255.0))
    return int(rgb[0] * f), int(rgb[1] * f), int(rgb[2] * f)


def draw(surface, inst, elapsed, ox, oy):
    """Рисует пакет в момент elapsed (мс от начала события). ox, oy — точка в координатах холста."""
    for L in inst.layers:
        s0 = L["start"] * inst.dur
        s1 = L["end"] * inst.dur
        if elapsed < s0 or elapsed > s1:
            continue
        p = (elapsed - s0) / max(1.0, s1 - s0)
        tsec = (elapsed - s0) / 1000.0
        kind = L["kind"]
        alpha = _lerp_field(L["alpha"], inst.params, p)
        col = _scaled(L["colour_rgb"], alpha)
        if kind == "ring":
            r = SS.U(_lerp_field(L["radius"], inst.params, p) * inst.power)
            w = max(1, SS.U(_lerp_field(L["width"], inst.params, p)))
            if r >= 1:
                pygame.draw.circle(surface, col, (ox, oy), int(r), int(w))
        elif kind == "flash":
            r = SS.U(_lerp_field(L["radius"], inst.params, p) * inst.power)
            if r >= 1:
                pygame.draw.circle(surface, col, (ox, oy), int(r))
        else:
            _draw_particles(surface, L, inst, col, tsec, ox, oy)


def _draw_particles(surface, L, inst, col, tsec, ox, oy):
    g = L.get("gravity_v", 0.0)
    trail = L["trail"]
    tail = SS.U(L["length"]) if trail else 0
    for vx, vy, size in L["items"]:
        x = ox + SS.U(vx * tsec)
        y = oy + SS.U(vy * tsec + 0.5 * g * tsec * tsec)
        if trail:
            vyy = vy + g * tsec
            norm = math.hypot(vx, vyy) or 1.0
            tx = x - SS.U(vx) / norm * tail
            ty = y - SS.U(vyy) / norm * tail
            pygame.draw.line(surface, col, (int(x), int(y)), (int(tx), int(ty)), max(1, SS.U(size)))
        else:
            pygame.draw.circle(surface, col, (int(x), int(y)), max(1, SS.U(size)))


def total_ms(pack):
    return pack["dur"] if pack else 0
