"""Геометрия и отрисовка тела удержания (общая для игры и редактора).

Что исправлено по сравнению с прямой отрисовкой «голой» прямоугольной плашкой:
* позиции головы и хвоста округляются ОДИН раз и одинаково (раньше rect() отбрасывал дробную часть у
  верхней границы и у высоты по отдельности — длина тела «дрожала» на пиксель от кадра к кадру);
* тело тянется до центра головы, а головка рисуется поверх на ТОЙ ЖЕ целой координате — между телом
  и головкой не бывает щели;
* тело не обрезается вручную у края экрана (раньше обрезка превращала край в скруглённый «срез»),
  скругляются только настоящие концы, а край экрана режет сам surface;
* яркость тела при зажатии/отпускании меняется плавно (smooth_factor), а не скачком.

Все функции зависят только от координат, а не от частоты кадров.
"""
import math

import pygame

import config as C
import screen_setting as SS

FAR = 4000          # дальше этого за краем экрана концы не рисуем — они всё равно не видны


def _mix(a, b, k):
    return tuple(int(a[i] + (b[i] - a[i]) * k) for i in range(3))


def body_width():
    return int(C.LANE_W * 0.42)


def snap_y(y):
    """Единое округление координаты (в пиксели) для головы, хвоста и спрайта."""
    return int(math.floor(y + 0.5))


def body_rect(cx, y_head, y_tail, width=None, screen_h=None):
    """Прямоугольник тела между головой и хвостом (целые координаты, непрерывный по y)."""
    width = body_width() if width is None else width
    screen_h = C.HEIGHT if screen_h is None else screen_h
    a, b = snap_y(y_head), snap_y(y_tail)
    top, bot = min(a, b), max(a, b)
    top = max(top, -FAR)
    bot = min(bot, screen_h + FAR)
    return pygame.Rect(cx - width // 2, top, width, max(0, bot - top))


def smooth_factor(cur, target, dt, rate=18.0):
    """Плавное приближение яркости к целевой; не зависит от частоты кадров."""
    return target + (cur - target) * math.exp(-rate * dt)


def visible(rect, screen_h=None):
    screen_h = C.HEIGHT if screen_h is None else screen_h
    return rect.h > 0 and rect.bottom >= 0 and rect.top <= screen_h


def draw_body(surface, lane, cx, y_head, y_tail, fill_k, edge_k):
    """Рисует тело удержания. fill_k / edge_k — доля цвета дорожки в заливке и в контуре (0…1)."""
    rect = body_rect(cx, y_head, y_tail, screen_h=surface.get_height())
    if not visible(rect, surface.get_height()):
        return rect
    col = C.LANE_COLORS[lane]
    radius = max(0, min(SS.U(6), rect.h // 2, rect.w // 2))
    pygame.draw.rect(surface, _mix(C.BG_DARK, col, fill_k), rect, border_radius=radius)
    if rect.h > 2:
        pygame.draw.rect(surface, _mix(C.BG_DARK, col, edge_k), rect, SS.U(2), border_radius=radius)
    return rect
