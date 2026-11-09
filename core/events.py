
#-- Импорт
import os

import pygame

import anim as AN
import cine as CN
import config as C
import fx as FX
import screen_setting as SS
import settings
import style as S
import video

TYPES = ("glitch", "flash", "image", "bg", "video", "heal", "card", "invert", "fx", "camera", "transition", "pack")
TYPE_NAMES = {"glitch": "ГЛЮК", "flash": "ВСПЫШКА", "image": "КАРТИНКА (БЕТА)", "bg": "ФОН", "video": "ВИДЕО (БЕТА)", "heal": "ХИЛЛ", "card": "КАРТОЧКА", "invert": "ИНВЕРСИЯ", "fx": "ЭФФЕКТ", "camera": "КАМЕРА", "transition": "ПЕРЕХОД", "pack": "ПАКЕТ"}
TYPE_COLORS = {"glitch": C.RED_LIGHT, "flash": C.WHITE, "image": C.GOLD, "bg": (200, 200, 210), "video": (120, 200, 255), "heal": C.WHITE, "card": (255, 200, 110), "invert": (190, 140, 255), "fx": (120, 255, 200), "camera": (255, 170, 90), "transition": (230, 230, 255), "pack": (255, 120, 200)}
DESCRIPTIONS = {
    "glitch": "Экран дрожит и рвётся на полосы. Сила и длительность настраиваются.",
    "flash": "Белая вспышка: появляется за «скорость появления» и гаснет за «длительность».",
    "image": "Картинка из папки images/ появляется в центре, может двигаться и плавно исчезать. Можно растянуть на весь экран.",
    "bg": "Меняет цвет фона. Кнопка «ВЕРНУТЬ ФОН» возвращает исходный цвет.",
    "video": "Ролик из папки images/ на заданное время. «ПОДОГНАТЬ» вписывает его в экран, «Растянуть на весь экран» заполняет весь экран.",
    "heal": "Белый круг падает быстрее нот. Поймать нажатием клавиши — +1 HP, промах — только глитч, без урона.",
    "card": "Текст на экране на заданное время. Плавно появляется и исчезает. Текст меняется в поле «Текст».",
    "invert": "На заданное время весь экран становится негативом. Длительность настраивается.",
    "fx": "Эффект на весь экран: размытие, свечение, хроматика, волна или цветовой фильтр. «В ТАКТ» делает пульс по сетке.",
    "camera": "Плавно меняет масштаб кадра и сдвигает его за «плавность». Новое событие камеры обрывает предыдущее и начинается с текущего положения.",
    "transition": "Затемнение, диафрагма или шторка за «длительность». «Закрыть» держит экран закрытым до следующего перехода, «открыть» показывает игру, «акцент» закрывает и открывает. Enter пропускает переходы «открыть» и «акцент».",
    "pack": "Визуальный пакет из библиотеки (кольца, частицы, вспышки). Пакет выбирается полем «Пакет» или клавишей B; параметры пакета — отдельными строками.",
}
BASE_BG = tuple(C.BG_DARK)
ANIMS = ("pop", "fade", "drift")
ANIM_NAMES = {"pop": "РЕЗКО", "fade": "ПЛАВНО", "drift": "ДВИЖЕНИЕ"}
TINT_NONE = (255, 255, 255)
IMAGE_DIR = C.root("images")
IMAGE_EXT = (".png", ".jpg", ".jpeg")
VIDEO_EXT = (".mp4", ".webm", ".mov", ".avi", ".mkv", ".m4v")
MAX_T = 60 * 60 * 1000

FIELDS = {
    "glitch": (("dur", "Длительность, мс", 100, 5000, 100, 800),
               ("strength", "Сила, %", 10, 100, 5, 60)),
    "flash": (("attack", "Скорость появления, мс", 10, 500, 10, 40),
              ("dur", "Длительность, мс", 50, 3000, 50, 500)),
    "video": (("dur", "Длительность, мс", 200, 100000, 100, 3000),
              ("w", "Ширина, px", 80, 1280, 20, 480),
              ("h", "Высота, px", 45, 720, 20, 270),
              ("x", "Смещение X, px", -600, 600, 10, 0),
              ("y", "Смещение Y, px", -400, 400, 10, 0),
              ("fade", "Плавность, мс", 50, 2000, 50, 300),
              ("dx", "Движение X, px", -600, 600, 10, 0),
              ("dy", "Движение Y, px", -400, 400, 10, 0),
              ("look_amt", "Сила эффекта «ОБЪЕКТ», %", 0, 100, 5, 60)),
    "image": (("dur", "Длительность, мс", 200, 20000, 100, 3000),
              ("w", "Ширина, px", 80, 1280, 20, 480),
              ("x", "Смещение X, px", -600, 600, 10, 0),
              ("y", "Смещение Y, px", -400, 400, 10, 0),
              ("fade", "Плавность, мс", 50, 2000, 50, 300),
              ("dx", "Движение X, px", -600, 600, 10, 0),
              ("dy", "Движение Y, px", -400, 400, 10, 0),
              ("look_amt", "Сила эффекта «ОБЪЕКТ», %", 0, 100, 5, 60)),
    "fx": (("amount", "Сила, %", 0, 100, 5, 60),
           ("attack", "Нарастание, мс", 0, 5000, 50, 300),
           ("dur", "Длительность, мс", 100, 60000, 100, 2000)),
    "bg": (("r", "Красный", 0, 255, 8, BASE_BG[0]),
           ("g", "Зелёный", 0, 255, 8, BASE_BG[1]),
           ("b", "Синий", 0, 255, 8, BASE_BG[2]),
           ("fade", "Переход, мс", 0, 3000, 50, 500)),
    "heal": (("lane", "Дорожка (1=D … 4=K)", 1, 4, 1, 1),
             ("speed", "Скорость падения, %", 100, 300, 10, 170)),
    "card": (("dur", "Длительность, мс", 300, 20000, 100, 2500),),
    "invert": (("dur", "Длительность, мс", 50, 3000, 50, 200),),
    "camera": (("dur", "Плавность, мс", 0, 10000, 50, 800),
               ("zoom", "Масштаб, %", CN.ZOOM_MIN, CN.ZOOM_MAX, 5, 100),
               ("x", "Сдвиг X, px", -CN.PAN_MAX_X, CN.PAN_MAX_X, 10, 0),
               ("y", "Сдвиг Y, px", -CN.PAN_MAX_Y, CN.PAN_MAX_Y, 10, 0)),
    "transition": (("dur", "Длительность, мс", 50, 5000, 50, 600),
                   ("colour", "Цвет (0 чёрный … 3 голубой)", 0, len(CN.COLOURS) - 1, 1, 0)),
    "pack": (("dur", "Длительность, мс", 100, 20000, 100, 1000),
             ("lane", "Дорожка (0 — экран, 1=D … 4=K)", 0, 4, 1, 0),
             ("x", "Смещение X, px", -600, 600, 10, 0),
             ("y", "Смещение Y, px", -400, 400, 10, 0),
             ("power", "Сила пакета, %", 10, 200, 10, 100),
             ("colour", "Цвет пакета (0–5)", 0, 5, 1, 0)),
}
CARD_TEXT_MAX = 80


def image_path(name):
    """Путь к файлу картинки/ролика: папка игры, затем моды (см. songs.image_path)."""
    import songs
    return songs.image_path(name)


def list_media(kind):
    exts = VIDEO_EXT if kind == "video" else IMAGE_EXT
    names = set()
    try:
        os.makedirs(IMAGE_DIR, exist_ok=True)
        import modsys
        for d in [IMAGE_DIR] + modsys.dirs("images"):
            if os.path.isdir(d):
                names.update(f for f in os.listdir(d) if f.lower().endswith(exts))
    except OSError:
        return []
    names = sorted(names, key=str.lower)
    return sorted(names, key=str.lower)


def list_images():
    return list_media("image")


def _defaults(kind):
    ev = {"type": kind, "t": 0, "folder": "", "locked": False}
    for key, _, _, _, _, default in FIELDS[kind]:
        ev[key] = default
    if kind in ("image", "video"):
        ev["file"] = ""
        ev["anim"] = "fade"
        ev["full"] = False
        ev["anim_id"] = ""
        ev["look"] = ""
    if kind == "bg":
        ev["orig"] = False
    if kind == "card":
        ev["text"] = "Текст"
    if kind == "fx":
        ev["kind"] = "blur"
        ev["beat"] = False
    if kind == "camera":
        ev["ease"] = AN.DEFAULT_EASE
    if kind == "transition":
        ev["kind"] = "fade"
        ev["mode"] = "out"
        ev["ease"] = AN.DEFAULT_EASE
        ev["skip"] = True
    if kind == "pack":
        ev["pack"] = ""
        ev["params"] = {}
    return ev


def make(kind, t):
    ev = _defaults(kind)
    ev["t"] = max(0, min(MAX_T, int(t)))
    if kind in ("image", "video"):
        names = list_media(kind)
        ev["file"] = names[0] if names else ""
    return ev


def _num(v, lo, hi, default):
    try:
        v = int(round(float(v)))
    except (TypeError, ValueError, OverflowError):
        return default
    return max(lo, min(hi, v))


def normalize(raw):
    if not isinstance(raw, dict) or raw.get("type") not in TYPES:
        return None
    kind = raw["type"]
    ev = _defaults(kind)
    ev["t"] = _num(raw.get("t"), 0, MAX_T, 0)
    ev["folder"] = str(raw.get("folder", ""))[:24]
    ev["locked"] = bool(raw.get("locked", False))
    for key, _, lo, hi, _, default in FIELDS[kind]:
        ev[key] = _num(raw.get(key), lo, hi, default)
    if kind in ("image", "video"):
        ev["file"] = str(raw.get("file", ""))[:120]
        ev["anim"] = raw.get("anim") if raw.get("anim") in ANIMS else "fade"
        ev["full"] = raw.get("full") is True or raw.get("full") in (1, "1", "true", "True")
        anim_id = raw.get("anim_id", "")
        ev["anim_id"] = anim_id[:16] if isinstance(anim_id, str) else ""
        look = raw.get("look", "")
        ev["look"] = look if look in FX.LOOKS else ""
    if kind == "bg":
        ev["orig"] = bool(raw.get("orig", False))
    if kind == "card":
        ev["text"] = str(raw.get("text", "Текст"))[:CARD_TEXT_MAX] or "Текст"
    if kind == "fx":
        ev["kind"] = raw.get("kind") if raw.get("kind") in FX.KINDS else "blur"
        ev["beat"] = raw.get("beat") is True
    if kind == "camera":
        ev["ease"] = _ease(raw.get("ease"))
    if kind == "transition":
        ev["kind"] = raw.get("kind") if raw.get("kind") in CN.KINDS else "fade"
        ev["mode"] = raw.get("mode") if raw.get("mode") in CN.MODES else "out"
        ev["ease"] = _ease(raw.get("ease"))
        ev["skip"] = raw.get("skip") is not False
    if kind == "pack":
        pid = raw.get("pack", "")
        ev["pack"] = pid[:40] if isinstance(pid, str) else ""
        ev["params"] = _params_dict(raw.get("params"))
    return ev


def _ease(name):
    return name if name in AN.EASES else AN.DEFAULT_EASE


def _params_dict(raw):
    """Значения параметров пакета: до 8 записей, имя до 16 символов, только настоящие числа."""
    out = {}
    if not isinstance(raw, dict):
        return out
    for k, v in list(raw.items())[:8]:
        if not isinstance(k, str) or len(k) > 16:
            continue
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            continue
        if v != v or v in (float("inf"), float("-inf")):
            continue
        out[k] = float(v)
    return out


def total_ms(ev):
    if ev["type"] in ("bg", "heal"):
        return 0
    if ev["type"] == "flash":
        return ev["attack"] + ev["dur"]
    return ev["dur"]


def bg_target(ev):
    if ev.get("orig", False):
        return BASE_BG
    return (ev.get("r", BASE_BG[0]), ev.get("g", BASE_BG[1]), ev.get("b", BASE_BG[2]))


def bg_at(bg_events, ms):
    prev, active = BASE_BG, None
    for ev in bg_events:
        if ev.get("t", 0) > ms:
            break
        if active is not None:
            prev = bg_target(active)
        active = ev
    if active is None:
        return BASE_BG
    target = bg_target(active)
    fade = active.get("fade", 0)
    k = 1.0 if fade <= 0 else _clamp01((ms - active.get("t", 0)) / fade)
    return tuple(int(prev[i] + (target[i] - prev[i]) * k) for i in range(3))


def cycle(seq, cur, step):
    if not seq:
        return cur
    i = seq.index(cur) if cur in seq else 0
    return seq[(i + step) % len(seq)]


#-- Картинки: загрузка и кэш

_src = {}
_scaled = {}


def image_surface(name, width, bright=1.0, height=None):
    """Картинка масштабом по ширине (высота по пропорциям) или точно width × height (height задана)."""
    if not name:
        return None
    key = (name, width, height, bright)
    surf = _scaled.get(key)
    if surf is not None:
        return surf
    if name not in _src:
        try:
            _src[name] = pygame.image.load(image_path(name) or os.path.join(IMAGE_DIR, name)).convert_alpha()
        except (pygame.error, OSError):
            _src[name] = None
    src = _src[name]
    if src is None:
        return None
    h = height if height else max(1, round(src.get_height() * width / src.get_width()))
    surf = pygame.transform.smoothscale(src, (max(1, width), max(1, h)))
    if bright < 1.0:
        c = int(255 * bright)
        surf.fill((c, c, c), special_flags=pygame.BLEND_RGB_MULT)
    _scaled[key] = surf
    return surf


#-- Состояние события в момент elapsed (мс от его t)

def _clamp01(v):
    return 0.0 if v < 0 else 1.0 if v > 1 else v


def glitch_level(ev, elapsed):
    if elapsed < 0 or elapsed >= ev["dur"]:
        return 0.0
    k = 1.0 if elapsed < ev["dur"] * 0.8 else (ev["dur"] - elapsed) / (ev["dur"] * 0.2)
    return ev["strength"] / 100.0 * _clamp01(k)


def flash_alpha(ev, elapsed):
    if elapsed < 0 or elapsed >= ev["attack"] + ev["dur"]:
        return 0.0
    if elapsed < ev["attack"]:
        return _clamp01(elapsed / ev["attack"])
    return _clamp01(1.0 - (elapsed - ev["attack"]) / ev["dur"])


def media_size(ev):
    """Размер показа в пикселях экрана: (ширина, высота). Высота картинки None — по пропорциям."""
    if ev.get("full"):
        return C.WIDTH, C.HEIGHT
    if ev["type"] == "video":
        return SS.U(ev["w"]), SS.U(ev.get("h", 0))
    return SS.U(ev["w"]), None


def image_state(ev, elapsed):
    dur = ev["dur"]
    if elapsed < 0 or elapsed >= dur:
        return 0.0, 0, 0
    fade = max(1, min(ev["fade"], dur // 2))
    if ev["anim"] == "pop":
        alpha = 1.0
    else:
        alpha = _clamp01(min(elapsed / fade, (dur - elapsed) / fade))
    p = elapsed / dur
    if ev.get("full"):
        return alpha, 0, 0
    if ev["anim"] == "drift":
        p = p * p * (3 - 2 * p)
        return alpha, ev["x"] + ev["dx"] * p, ev["y"] + ev["dy"] * p
    return alpha, ev["x"], ev["y"]


#-- Текстовая карточка и инверсия

def card_alpha(ev, elapsed):
    dur = ev["dur"]
    if elapsed < 0 or elapsed >= dur:
        return 0.0
    fade = max(1, min(300, dur // 3))
    return _clamp01(min(elapsed / fade, (dur - elapsed) / fade))


def _wrap_text(fnt, text, width):
    lines, line = [], ""
    for ch in text:
        cand = line + ch
        if fnt.size(cand)[0] > width and line:
            lines.append(line)
            line = ch
        else:
            line = cand
    if line:
        lines.append(line)
    return lines or [""]


_card_cache = {}


def _card_layout(text):
    """Перенос строк, готовые строки текста и подложка — один раз на текст и размер экрана."""
    key = (text, C.WIDTH, C.HEIGHT)
    entry = _card_cache.get(key)
    if entry is None:
        fnt = S.font(44, True)
        lines = _wrap_text(fnt, text, C.WIDTH - SS.U(160))
        line_h = fnt.get_linesize()
        width = max(fnt.size(line)[0] for line in lines) + SS.U(60)
        band = pygame.Surface((width, len(lines) * line_h + SS.U(30)), pygame.SRCALPHA)
        band.fill((0, 0, 0, 150))
        rendered = [fnt.render(line, True, C.WHITE) for line in lines]
        entry = (line_h, width, band, rendered)
        if len(_card_cache) > 32:
            _card_cache.clear()
        _card_cache[key] = entry
    return entry


def draw_card(surface, ev, elapsed):
    alpha = card_alpha(ev, elapsed)
    if alpha <= 0 or not ev.get("text"):
        return
    line_h, width, band, rendered = _card_layout(ev["text"])
    top = C.HEIGHT // 2 - len(rendered) * line_h // 2
    band.set_alpha(int(255 * alpha))
    surface.blit(band, (C.WIDTH // 2 - width // 2, top - SS.U(15)))
    a = int(255 * alpha)
    for i, surf in enumerate(rendered):
        surf.set_alpha(a)
        surface.blit(surf, (C.WIDTH // 2 - surf.get_width() // 2,
                            top + i * line_h + line_h // 2 - surf.get_height() // 2))


def prewarm(events_list):
    """Подготовка картинок и роликов до старта песни, чтобы не было заикания на показе."""
    for ev in events_list:
        if not ev.get("file"):
            continue
        if ev["type"] == "image":
            w, h = media_size(ev)
            image_surface(ev["file"], w, media_bright(), h)
        elif ev["type"] == "video":
            path = image_path(ev["file"]) or os.path.join(IMAGE_DIR, ev["file"])
            video.prepare(path, (path, ev["t"]))


def invert_level(ev, elapsed):
    return 1.0 if 0 <= elapsed < ev["dur"] else 0.0


_neg = None


def apply_invert(surface, level):
    global _neg
    if level <= 0:
        return
    if _neg is None or _neg.get_size() != surface.get_size():
        _neg = pygame.Surface(surface.get_size())
    _neg.fill((255, 255, 255))
    _neg.blit(surface, (0, 0), special_flags=pygame.BLEND_RGB_SUB)
    surface.blit(_neg, (0, 0))


#-- Эффекты по времени (для редактора: считаются из позиции курсора)

def active_fx(events_list, now):
    glitch, flash, invert = 0.0, 0.0, 0.0
    images, cards = [], []
    for ev in events_list:
        if ev["type"] == "bg":
            continue
        elapsed = now - ev["t"]
        if elapsed < 0 or elapsed >= total_ms(ev):
            continue
        if ev["type"] == "glitch":
            glitch = max(glitch, glitch_level(ev, elapsed))
        elif ev["type"] == "flash":
            flash = max(flash, flash_alpha(ev, elapsed))
        elif ev["type"] in ("image", "video"):
            images.append((ev, elapsed))
        elif ev["type"] == "card":
            cards.append((ev, elapsed))
        elif ev["type"] == "invert":
            invert = max(invert, invert_level(ev, elapsed))
    return glitch, flash, images, cards, invert


def media_bright():
    return 1.0 - settings.get("media_dim") / 100.0


def media_pose(ev, elapsed, anims=None):
    """Альфа 0..1, смещение x и y, масштаб %, поворот в градусах и цвет умножения картинки в момент elapsed.

    Если у события задан anim_id и такая анимация есть в чарте, её значения заменяют пресеты «ПЛАВНО /
    РЕЗКО / ДВИЖЕНИЕ»; смещение самого события прибавляется. Иначе работают прежние пресеты."""
    anim = anims.get(ev["anim_id"]) if anims and ev.get("anim_id") else None
    if anim is None:
        alpha, ox, oy = image_state(ev, elapsed)
        return alpha, ox, oy, 100, 0, TINT_NONE
    if elapsed < 0 or elapsed >= ev["dur"]:
        return 0.0, 0, 0, 100, 0, TINT_NONE
    vals = AN.sample(anim, elapsed)
    base_x = 0 if ev.get("full") else ev["x"]
    base_y = 0 if ev.get("full") else ev["y"]
    return (vals["alpha"] / 100.0, base_x + vals["x"], base_y + vals["y"],
            vals["scale"], vals["rot"], tuple(vals["tint"]))


def draw_media(surface, ev, elapsed, anims=None):
    alpha, ox, oy, scale, rot, tint = media_pose(ev, elapsed, anims)
    if alpha <= 0 or not ev.get("file"):
        return
    bright = media_bright()
    w, h = media_size(ev)
    if ev["type"] == "video":
        path = image_path(ev["file"]) or os.path.join(IMAGE_DIR, ev["file"])
        img = video.frame(path, (path, ev["t"]), elapsed, w, h, bright)
    else:
        img = image_surface(ev["file"], w, bright, h)
    if img is None:
        return
    if scale != 100 or rot:
        img = pygame.transform.rotozoom(img, rot, scale / 100.0)
    if ev.get("look"):
        img = FX.look(img, ev["look"], ev.get("look_amt", 0), elapsed)
    if tuple(tint) != TINT_NONE:
        img = img.copy()
        img.fill(tuple(tint) + (255,), special_flags=pygame.BLEND_RGB_MULT)
    img.set_alpha(int(255 * alpha))
    surface.blit(img, (C.WIDTH // 2 + SS.U(round(ox)) - img.get_width() // 2,
                       C.HEIGHT // 2 + SS.U(round(oy)) - img.get_height() // 2))


def draw_images(surface, images, anims=None):
    for ev, elapsed in images:
        draw_media(surface, ev, elapsed, anims)


def draw_cards(surface, cards):
    for ev, elapsed in cards:
        draw_card(surface, ev, elapsed)


_natural = {}


def natural_size(ev):
    if not ev.get("file"):
        return None
    path = image_path(ev["file"]) or os.path.join(IMAGE_DIR, ev["file"])
    if ev["type"] == "video":
        return video.size(path)
    if path not in _natural:
        try:
            _natural[path] = pygame.image.load(path).get_size()
        except (pygame.error, OSError):
            _natural[path] = None
    return _natural[path]


def fit_box(nw, nh, box_w, box_h):
    scale = min(box_w / nw, box_h / nh)
    w = max(FIELDS["video"][1][2], min(FIELDS["video"][1][3], round(nw * scale)))
    h = max(FIELDS["video"][2][2], min(FIELDS["video"][2][3], round(nh * scale)))
    return w, h


def stats(events_list):
    counts = {k: 0 for k in TYPES}
    media_ms = 0
    for ev in events_list:
        counts[ev["type"]] = counts.get(ev["type"], 0) + 1
        if ev["type"] in ("image", "video"):
            media_ms += ev["dur"]
    return counts, media_ms
