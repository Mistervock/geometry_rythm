"""Геометрия тела удержания: непрерывность, отсутствие дрожания и щелей."""
import random

import pygame

import config as C
import holdviz


def test_body_covers_head_to_tail_without_gap():
    rnd = random.Random(7)
    for _ in range(500):
        head = rnd.uniform(-300, C.HEIGHT + 300)
        tail = head - rnd.uniform(1, 900)
        r = holdviz.body_rect(300, head, tail)
        assert r.top == holdviz.snap_y(tail) or r.top == -holdviz.FAR
        assert r.bottom == holdviz.snap_y(head) or r.bottom == C.HEIGHT + holdviz.FAR
        assert r.h == r.bottom - r.top >= 0


def test_length_does_not_jitter_with_subpixel_motion():
    """Сдвиг на доли пикселя меняет длину не больше чем на 1 px (раньше rect() давал скачки)."""
    length = 200.0
    prev = None
    for i in range(600):
        head = 100 + i * 0.37
        r = holdviz.body_rect(300, head, head - length)
        if prev is not None:
            assert abs(r.h - prev.h) <= 1
            assert 0 <= r.bottom - prev.bottom <= 1
        prev = r


def test_head_and_body_share_same_integer_coordinate():
    for head in (10.2, 10.5, 10.49, 99.999, 400.5):
        r = holdviz.body_rect(300, head, head - 120)
        assert r.bottom == holdviz.snap_y(head)


def test_body_has_no_gaps_when_drawn():
    surf = pygame.Surface((C.WIDTH, C.HEIGHT))
    surf.fill(C.BG_DARK)
    for head in (250.3, 300.7, 500.5):
        rect = holdviz.draw_body(surf, 1, 400, head, head - 180, 0.6, 0.9)
        assert rect.h > 0
        col = [surf.get_at((400, y))[:3] for y in range(rect.top + 3, rect.bottom - 3)]
        assert all(c != tuple(C.BG_DARK[:3]) for c in col), "в теле удержания есть незакрашенные пиксели"


def test_smooth_factor_is_framerate_independent_and_monotonic():
    def run(dt, total=0.3):
        v = 0.0
        for _ in range(int(round(total / dt))):
            v = holdviz.smooth_factor(v, 1.0, dt)
        return v
    assert abs(run(1 / 60) - run(1 / 240)) < 1e-6
    v, last = 0.0, -1.0
    for _ in range(100):
        v = holdviz.smooth_factor(v, 1.0, 1 / 60)
        assert last <= v <= 1.0
        last = v
