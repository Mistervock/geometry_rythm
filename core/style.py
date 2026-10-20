
#-- Импорт
import math
import random

import pygame

import config as C
import screen_setting as SS

_fonts = {}
_meta = {}
_scan = None
_band = None


def font(size, bold=False):
    px = max(8, round(size * C.UI_FONT_SCALE * SS.SCALE))
    key = (px, bold)
    if key not in _fonts:
        name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
        try:
            _fonts[key] = pygame.font.Font(C.res("fonts", name), px)
        except Exception:
            _fonts[key] = pygame.font.Font(None, px + 6)
        _meta[id(_fonts[key])] = key
    return _fonts[key]


def fit(fnt, text, max_w):
    if fnt.size(text)[0] <= max_w:
        return fnt
    size, bold = _meta.get(id(fnt), (18, False))
    while size > 8:
        size -= 1
        f = font(size, bold)
        if f.size(text)[0] <= max_w:
            return f
    return font(size, bold)


def clamp(x, a=0.0, b=1.0):
    return a if x < a else b if x > b else x


def ease_out_cubic(t):
    t = clamp(t)
    return 1 - (1 - t) ** 3


def smoothstep(t):
    t = clamp(t)
    return t * t * (3 - 2 * t)


def approach(cur, target, dt, rate):
    return target + (cur - target) * math.exp(-rate * dt)


def _scanlines():
    global _scan
    if _scan is None:
        _scan = pygame.Surface((C.WIDTH, C.HEIGHT), pygame.SRCALPHA)
        for y in range(0, C.HEIGHT, SS.U(3)):
            pygame.draw.line(_scan, (0, 0, 0, 45), (0, y), (C.WIDTH, y))
    return _scan


SCANLINES = True
_scan_mult = None


def _scan_multiply():
    """Скан-линии одним проходом умножения: без альфа-смешивания на весь экран."""
    global _scan_mult
    if _scan_mult is None or _scan_mult.get_size() != (C.WIDTH, C.HEIGHT):
        _scan_mult = pygame.Surface((C.WIDTH, C.HEIGHT))
        _scan_mult.fill((255, 255, 255))
        for y in range(0, C.HEIGHT, SS.U(3)):
            pygame.draw.line(_scan_mult, (210, 210, 210), (0, y), (C.WIDTH, y))
    return _scan_mult


def post_fx(surface, frame, grain=50, lines=True):
    global _band
    if lines and SCANLINES:
        surface.blit(_scan_multiply(), (0, 0), special_flags=pygame.BLEND_MULT)
    for _ in range(grain):
        c = random.randint(15, 55)
        surface.set_at((random.randrange(C.WIDTH), random.randrange(C.HEIGHT)), (c, c, c))
    if _band is None or _band.get_width() != C.WIDTH:
        _band = pygame.Surface((C.WIDTH, SS.U(40)))
        _band.fill((255, 255, 255))
        _band.set_alpha(9)
    y = (frame * SS.U(3)) % (C.HEIGHT + SS.U(80)) - SS.U(40)
    surface.blit(_band, (0, y))


_glitch_buf = None


def glitch(surface, strength=1.0):
    global _glitch_buf
    if _glitch_buf is None or _glitch_buf.get_size() != surface.get_size():
        _glitch_buf = pygame.Surface(surface.get_size())
    _glitch_buf.blit(surface, (0, 0))
    snap = _glitch_buf
    shift = max(1, int(SS.U(30) * strength))
    for _ in range(random.randint(3, 6)):
        y = random.randrange(0, C.HEIGHT - SS.U(20))
        h = random.randint(SS.U(3), SS.U(24))
        dx = random.randint(-shift, shift)
        surface.blit(snap, (dx, y), pygame.Rect(0, y, C.WIDTH, h))
    tint = pygame.Surface((C.WIDTH, random.randint(SS.U(3), SS.U(8))))
    tint.fill((255, 40, 70))
    tint.set_alpha(int(90 * strength))
    surface.blit(tint, (0, random.randrange(C.HEIGHT)))


def blit_text(surface, fnt, text, color, cx, cy, alpha=255, shown=None, dx=0, dy=0):
    if alpha <= 0:
        return
    full_w = fnt.size(text)[0]
    part = text if shown is None else text[:shown]
    if not part:
        return
    surf = fnt.render(part, True, color)
    surf.set_alpha(max(0, min(255, int(alpha))))
    surface.blit(surf, (cx - full_w // 2 + dx, cy - surf.get_height() // 2 + dy))


def glitch_title(surface, fnt, text, color, cx, cy, k, length=40):
    if k >= length:
        blit_text(surface, fnt, text, color, cx, cy)
        return
    glitching = random.random() < 0.4
    dx = random.randint(-SS.U(5), SS.U(5)) if glitching else 0
    dy = random.randint(-SS.U(2), SS.U(2)) if glitching else 0
    alpha = random.randint(90, 255) if glitching else 255
    blit_text(surface, fnt, text, color, cx, cy, alpha, dx=dx, dy=dy)
    if glitching:
        blit_text(surface, fnt, text, C.CYAN, cx, cy, 110, dx=dx + SS.U(3), dy=dy)


def draw_grid(surface, offset, pulse=0.0):
    col = tuple(min(255, c + int(pulse * 35)) for c in C.GRID_COL)
    step = SS.U(60)
    off = int(SS.U(offset))
    for x in range(0, C.WIDTH, step):
        pygame.draw.line(surface, col, (x, 0), (x, C.HEIGHT))
    for y in range(0, C.HEIGHT, step):
        pygame.draw.line(surface, col, (0, (y + off) % C.HEIGHT),
                         (C.WIDTH, (y + off) % C.HEIGHT))


def star_centers(cx, cy, total=5, gap=40):
    start = cx - (total - 1) * gap / 2
    return [(int(start + i * gap), cy) for i in range(total)]


_disc_cache = {}


def draw_disc(surface, cx, cy, r, alpha=70):
    """Очень прозрачный чёрный круг под кнопкой-стрелкой (поверхность кэшируется)."""
    key = (r, alpha)
    disc = _disc_cache.get(key)
    if disc is None:
        disc = pygame.Surface((2 * r + 2, 2 * r + 2), pygame.SRCALPHA)
        pygame.draw.circle(disc, (0, 0, 0, alpha), (r + 1, r + 1), r)
        _disc_cache[key] = disc
    surface.blit(disc, (cx - r - 1, cy - r - 1))


def draw_star(surface, cx, cy, r, color, filled=True):
    pts = []
    for i in range(10):
        ang = -math.pi / 2 + i * math.pi / 5
        rad = r if i % 2 == 0 else r * 0.45
        pts.append((cx + math.cos(ang) * rad, cy + math.sin(ang) * rad))
    if filled:
        pygame.draw.polygon(surface, color, pts)
    else:
        pygame.draw.polygon(surface, color, pts, 2)


def panel(surface, area, accent, alpha=215):
    back = pygame.Surface((area.w, area.h), pygame.SRCALPHA)
    back.fill((10, 10, 25, alpha))
    surface.blit(back, area.topleft)
    edge = tuple(c // 2 + 20 for c in accent)
    pygame.draw.rect(surface, edge, area, 1, border_radius=SS.U(8))
    L = SS.U(16)
    for cx, cy, dx, dy in ((area.left, area.top, 1, 1), (area.right, area.top, -1, 1),
                           (area.left, area.bottom, 1, -1), (area.right, area.bottom, -1, -1)):
        pygame.draw.line(surface, accent, (cx, cy), (cx + dx * L, cy), SS.U(2))
        pygame.draw.line(surface, accent, (cx, cy), (cx, cy + dy * L), SS.U(2))


class Btn:

    def __init__(self, rect, label, color=C.CYAN, fnt=None):
        self.rect = pygame.Rect(rect)
        self.label = label
        self.color = color
        self.base_fnt = fnt or font(18)
        self.fnt = fit(self.base_fnt, label, self.rect.w - 16)

    def set_label(self, label):
        if label != self.label:
            self.label = label
            self.fnt = fit(self.base_fnt, label, self.rect.w - 16)

    def hovered(self, mouse):
        return self.rect.collidepoint(mouse)

    def draw(self, surface, mouse, active=False):
        hov = self.hovered(mouse) or active
        r = self.rect
        pygame.draw.rect(surface, (34, 34, 68) if hov else (14, 14, 30), r, border_radius=SS.U(6))
        pygame.draw.rect(surface, self.color if hov else C.DIM, r, SS.U(2), border_radius=SS.U(6))
        col = C.WHITE if hov else (190, 190, 210)
        s = self.fnt.render(self.label, True, col)
        dx = random.randint(-SS.U(2), SS.U(2)) if hov and random.random() < 0.04 else 0
        surface.blit(s, (r.centerx - s.get_width() // 2 + dx, r.centery - s.get_height() // 2))
        if hov:
            cy = r.centery
            a, b, c = SS.U(9), SS.U(15), SS.U(5)
            pygame.draw.polygon(surface, self.color,
                                [(r.x + a, cy - c), (r.x + b, cy), (r.x + a, cy + c)])
            pygame.draw.polygon(surface, self.color,
                                [(r.right - a, cy - c), (r.right - b, cy), (r.right - a, cy + c)])


def _shape_points(kind, cx, cy, r, rot=0.0):
    if kind == "square":
        return [(cx + r * math.cos(math.radians(rot + 45 + 90 * k)),
                 cy + r * math.sin(math.radians(rot + 45 + 90 * k))) for k in range(4)]
    if kind == "triangle":
        a = math.radians(rot - 90)
        return [(cx + r * math.cos(a + 2.0944 * k), cy + r * math.sin(a + 2.0944 * k))
                for k in range(3)]
    if kind == "hexagon":
        return [(cx + r * math.cos(math.radians(rot + 60 * k)),
                 cy + r * math.sin(math.radians(rot + 60 * k))) for k in range(6)]
    return [(cx, cy - r * 1.2), (cx + r * 0.85, cy), (cx, cy + r * 1.2), (cx - r * 0.85, cy)]


def draw_shape(surface, kind, cx, cy, r, color, alpha=255, rot=0.0, glow=True):
    alpha = int(clamp(alpha / 255) * 255)
    if alpha <= 0 or r <= 0:
        return
    size = int(r * 3) + 8
    layer = pygame.Surface((size, size), pygame.SRCALPHA)
    ox = oy = size // 2
    if glow:
        for i in range(3):
            rr = int(r * 1.5) - i * 4
            pygame.draw.circle(layer, (*color, max(1, alpha // 14)), (ox, oy), rr)
    pts = [(x - cx + ox, y - cy + oy) for x, y in _shape_points(kind, cx, cy, r, rot)]
    pygame.draw.polygon(layer, (*color, alpha // 3 * 2), pts)
    pygame.draw.polygon(layer, (*C.WHITE, alpha), pts, 2)
    surface.blit(layer, (cx - ox, cy - oy))
