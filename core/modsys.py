"""Моды: папки mods/<id>/ с описанием mod.json. Моды ТОЛЬКО ДАННЫЕ — их Python-код никогда не исполняется.

Что может мод (версия формата api=1):
  * palette      — переопределить цвета интерфейса и дорожек (см. PALETTE_KEYS);
  * translations — добавить или заменить английские строки (только en; русские тексты не трогаем);
  * songs / charts / images — папки с песнями (.ogg/.mp3/.wav), чартами (.json) и картинками/роликами событий.
    Песни и картинки ищутся сначала в папках игры, потом в модах. Чарты из модов открываются как копии: при
    сохранении создаётся новый файл в data/charts, файл мода не меняется.

Проверка строгая и изолированная: каждый мод проверяется отдельно; ошибка в одном моде отключает только его,
остальное работает. Причины пишутся в data/mods.log и выводятся в консоль при запуске.
"""
import json
import os
import re

import config as C
import jsonio

FORMAT = "geometry-rhythm-mod"
API = 1
ID_RE = re.compile(r"^[a-z0-9_-]{2,40}$")
PALETTE_KEYS = ("BG_DARK", "GRID_COL", "WHITE", "GREY", "DIM", "GREEN", "PURPLE", "PURPLE_LIGHT",
                "RED", "RED_LIGHT", "GOLD", "CYAN", "LANE_COLORS")
TRANSLATION_MAX = 2000
TEXT_MAX = 300
MANIFEST_MAX_BYTES = 256 * 1024
KNOWN_KEYS = {"format", "api", "id", "name", "version", "author", "description", "enabled", "palette",
              "translations", "songs", "charts", "images"}

MODS_DIR = C.root("mods")
LOG_PATH = C.root("data", "mods.log")


class Mod:
    def __init__(self, ident, path):
        self.id = ident
        self.path = path
        self.name = ident
        self.version = ""
        self.author = ""
        self.enabled = True
        self.palette = {}
        self.translations = {}
        self.dirs = {"songs": None, "charts": None, "images": None}
        self.warnings = []
        self.errors = []

    @property
    def active(self):
        return self.enabled and not self.errors


class ModError(Exception):
    pass


LOADED = []


def _text(value, limit, field):
    if not isinstance(value, str):
        raise ModError(f"«{field}» должно быть строкой")
    value = value.strip()
    if len(value) > limit:
        raise ModError(f"«{field}» длиннее {limit} символов")
    return value


def _color(value, field):
    if (not isinstance(value, list) or len(value) != 3
            or any(not isinstance(c, int) or isinstance(c, bool) or not 0 <= c <= 255 for c in value)):
        raise ModError(f"цвет «{field}» должен быть списком из трёх целых чисел 0–255")
    return tuple(value)


def _folder(value, mod_path, field):
    if not isinstance(value, str) or not value.strip():
        raise ModError(f"«{field}» должно быть именем папки внутри мода")
    if os.path.isabs(value) or ".." in re.split(r"[\\/]", value):
        raise ModError(f"«{field}»: путь выходит за пределы папки мода")
    full = os.path.normpath(os.path.join(mod_path, value))
    if os.path.commonpath([os.path.abspath(full), os.path.abspath(mod_path)]) != os.path.abspath(mod_path):
        raise ModError(f"«{field}»: путь выходит за пределы мода")
    return full


def parse(mod_path, folder_id):
    """Читает и проверяет mod.json. Возвращает Mod (с errors, если что-то не так)."""
    mod = Mod(folder_id, mod_path)
    manifest_path = os.path.join(mod_path, "mod.json")
    try:
        if os.path.getsize(manifest_path) > MANIFEST_MAX_BYTES:
            raise ModError("mod.json слишком большой")
    except OSError as e:
        mod.errors.append(f"нет mod.json ({e.__class__.__name__})")
        return mod
    res = jsonio.read(manifest_path)
    if not res.ok:
        mod.errors.append(f"mod.json не читается: {res.message}")
        return mod
    data = res.data
    if not isinstance(data, dict):
        mod.errors.append("mod.json должен содержать объект {…}")
        return mod
    try:
        if data.get("format") != FORMAT:
            raise ModError(f"формат должен быть «{FORMAT}»")
        if data.get("api") != API:
            raise ModError(f"поддерживается api {API}, в моде указано {data.get('api')!r}")
        ident = data.get("id")
        if not isinstance(ident, str) or not ID_RE.match(ident):
            raise ModError("«id» — 2–40 символов: a–z, 0–9, «_» и «-»")
        mod.id = ident
        mod.name = _text(data.get("name", ident), 60, "name") or ident
        mod.version = _text(data.get("version", ""), 20, "version")
        mod.author = _text(data.get("author", ""), 60, "author")
        if "description" in data:
            _text(data["description"], TEXT_MAX, "description")
        if "enabled" in data:
            if not isinstance(data["enabled"], bool):
                raise ModError("«enabled» должно быть true или false")
            mod.enabled = data["enabled"]
        pal = data.get("palette", {})
        if not isinstance(pal, dict):
            raise ModError("«palette» должно быть объектом")
        for key, value in pal.items():
            if key not in PALETTE_KEYS:
                mod.warnings.append(f"неизвестный цвет «{key}» проигнорирован")
                continue
            if key == "LANE_COLORS":
                if not isinstance(value, list) or len(value) != 4:
                    raise ModError("«LANE_COLORS» — список из четырёх цветов")
                mod.palette[key] = tuple(_color(c, key) for c in value)
            else:
                mod.palette[key] = _color(value, key)
        tr = data.get("translations", {})
        if not isinstance(tr, dict):
            raise ModError("«translations» должно быть объектом")
        for lang, table in tr.items():
            if lang != "en":
                mod.warnings.append(f"перевод «{lang}» пока не поддерживается (только en)")
                continue
            if not isinstance(table, dict):
                raise ModError("«translations.en» должно быть объектом")
            if len(table) > TRANSLATION_MAX:
                raise ModError(f"в переводе больше {TRANSLATION_MAX} строк")
            for k, v in table.items():
                if not isinstance(k, str) or not isinstance(v, str) or len(k) > TEXT_MAX or len(v) > TEXT_MAX:
                    raise ModError("перевод: ключи и значения — строки до 300 символов")
                mod.translations[k] = v
        for kind in ("songs", "charts", "images"):
            if kind in data:
                mod.dirs[kind] = _folder(data[kind], mod_path, kind)
        for key in data:
            if key not in KNOWN_KEYS:
                mod.warnings.append(f"неизвестное поле «{key}» проигнорировано")
    except ModError as e:
        mod.errors.append(str(e))
    return mod


def load():
    """Сканирует mods/, проверяет каждый мод, применяет палитру и перевод. Ошибки не бросает."""
    LOADED.clear()
    if not os.path.isdir(MODS_DIR):
        return LOADED
    seen = set()
    for name in sorted(os.listdir(MODS_DIR), key=str.lower):
        path = os.path.join(MODS_DIR, name)
        if not os.path.isdir(path) or name.startswith((".", "_")):
            continue
        mod = parse(path, name)
        if mod.id in seen and not mod.errors:
            mod.errors.append(f"id «{mod.id}» уже занят другим модом")
        seen.add(mod.id)
        LOADED.append(mod)
    _apply()
    _write_log()
    return LOADED


def _apply():
    import i18n
    for mod in LOADED:
        if not mod.active:
            continue
        for key, value in mod.palette.items():
            setattr(C, key, value)
        i18n.EN.update(mod.translations)


def dirs(kind):
    """Папки модов для песен/чартов/картинок (только включённых и корректных модов)."""
    out = []
    for mod in LOADED:
        p = mod.dirs.get(kind)
        if mod.active and p and os.path.isdir(p):
            out.append(p)
    return out


def report_lines():
    lines = []
    for mod in LOADED:
        state = "ВКЛ" if mod.active else ("ВЫКЛ (выключен в mod.json)" if not mod.enabled else "ОШИБКА")
        lines.append(f"[{state}] {mod.id} {mod.version} — {mod.name}")
        lines += [f"    ! {e}" for e in mod.errors]
        lines += [f"    · {w}" for w in mod.warnings]
    return lines or ["Модов нет (папка mods/ пуста или отсутствует)."]


def _write_log():
    try:
        os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
        with open(LOG_PATH, "w", encoding="utf-8") as f:
            f.write("\n".join(report_lines()) + "\n")
    except OSError:
        pass
    for line in report_lines():
        print(f"[mods] {line}")
