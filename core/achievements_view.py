
#-- Импорт
import pygame

import config as C
import events as EV
import style as S
import screen_setting as SS
from i18n import t

_thumbs = {}


def _thumb(name, size):
    key = (name, size)
    if key in _thumbs:
        return _thumbs[key]
    surf = None
    if name:
        src = EV.image_surface(name, size)
        if src is not None:
            w, h = src.get_size()
            scale = min(size / w, size / h)
            surf = pygame.transform.smoothscale(src, (max(1, int(w * scale)), max(1, int(h * scale))))
    _thumbs[key] = surf
    return surf


def draw_thumb(scr, rect, name):
    pygame.draw.rect(scr, (12, 12, 28), rect, border_radius=SS.U(6))
    pygame.draw.rect(scr, C.DIM, rect, SS.U(2), border_radius=SS.U(6))
    surf = _thumb(name, min(rect.w, rect.h) - SS.U(8))
    if surf is not None:
        scr.blit(surf, surf.get_rect(center=rect.center))


def clip_text(fnt, text, max_w):
    if fnt.size(text)[0] <= max_w:
        return text
    while text and fnt.size(text + "…")[0] > max_w:
        text = text[:-1]
    return text + "…"


def draw_row(scr, rect, data, selected, unlocked=False):
    if selected:
        pygame.draw.rect(scr, (34, 34, 68), rect, border_radius=SS.U(6))
        pygame.draw.rect(scr, C.CYAN, rect, SS.U(2), border_radius=SS.U(6))
    thumb = pygame.Rect(rect.x + SS.U(10), rect.y + SS.U(8), rect.h - SS.U(16), rect.h - SS.U(16))
    draw_thumb(scr, thumb, data["image"])
    tx = thumb.right + SS.U(16)
    col = C.WHITE if selected else (190, 190, 210)
    scr.blit(S.font(18, True).render(data["name"], True, col), (tx, rect.y + SS.U(10)))
    tag_w = 0
    if unlocked:
        label = S.font(12, True).render(t("ПОЛУЧЕНО"), True, (20, 16, 0))
        tag_w = label.get_width() + SS.U(20)
        tag = pygame.Rect(rect.right - tag_w - SS.U(12), rect.y + SS.U(10), tag_w, label.get_height() + SS.U(8))
        pygame.draw.rect(scr, C.GOLD, tag, border_radius=SS.U(4))
        scr.blit(label, (tag.x + SS.U(10), tag.y + SS.U(4)))
    desc = clip_text(S.font(14), data["description"], rect.right - tx - SS.U(16) - tag_w)
    scr.blit(S.font(14).render(desc, True, C.GREY), (tx, rect.y + SS.U(40)))


def draw_detail(scr, rect, data):
    S.panel(scr, rect, C.GOLD, alpha=215)
    if data is None:
        S.blit_text(scr, S.font(16), t("Выберите достижение"), C.GREY, rect.centerx, rect.centery)
        return
    scr.blit(S.font(20, True).render(data["name"], True, C.GOLD), (rect.x + SS.U(24), rect.y + SS.U(14)))
    fnt = S.font(15)
    y = rect.y + SS.U(46)
    for line in wrap(fnt, data["description"] or t("Без описания"), rect.w - SS.U(48))[:3]:
        scr.blit(fnt.render(line, True, C.WHITE), (rect.x + SS.U(24), y))
        y += fnt.get_linesize()


def wrap(fnt, text, width):
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
