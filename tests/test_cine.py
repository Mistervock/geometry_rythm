"""Камера и переходы (core/cine.py): дорожка по времени, прерывания, пропуск и отрисовка кадра."""
import pygame
import pytest

import cine as CN


def _cam(t, dur, zoom=100, x=0, y=0, ease="linear"):
    return {"type": "camera", "t": t, "dur": dur, "zoom": zoom, "x": x, "y": y, "ease": ease}


def _tr(t, dur, mode="out", kind="fade", colour=0, skip=True, ease="linear"):
    return {"type": "transition", "t": t, "dur": dur, "mode": mode, "kind": kind, "colour": colour,
            "skip": skip, "ease": ease}


def _grid(surf):
    return pygame.image.tostring(surf, "RGB")


def test_no_events_means_rest_camera_and_no_overlay():
    c = CN.build([])
    assert not c
    assert c.camera_at(12345) == CN.CAM_REST
    assert c.overlay_at(12345) is None
    assert c.skippable_at(0) is None


def test_camera_glides_from_rest_to_target():
    c = CN.build([_cam(1000, 1000, zoom=200)])
    assert c.camera_at(999) == CN.CAM_REST
    assert c.camera_at(1500)[0] == pytest.approx(150.0)
    assert c.camera_at(2000)[0] == pytest.approx(200.0)
    assert c.camera_at(9000)[0] == pytest.approx(200.0)


def test_camera_pan_is_interpolated_too():
    c = CN.build([_cam(0, 1000, x=100, y=-50)])
    zoom, x, y = c.camera_at(500)
    assert zoom == pytest.approx(100.0)
    assert x == pytest.approx(50.0) and y == pytest.approx(-25.0)


def test_new_camera_event_interrupts_from_current_pose():
    c = CN.build([_cam(0, 1000, zoom=200), _cam(500, 1000, zoom=50)])
    assert c.camera_at(500)[0] == pytest.approx(150.0)
    assert c.camera_at(1000)[0] == pytest.approx(100.0)
    assert c.camera_at(1500)[0] == pytest.approx(50.0)


def test_camera_track_does_not_depend_on_event_order():
    evs = [_cam(0, 1000, zoom=200), _cam(500, 1000, zoom=50), _cam(3000, 400, x=80)]
    a = CN.build(evs)
    b = CN.build(list(reversed(evs)))
    for now in (0, 250, 500, 800, 1400, 3100, 4000):
        assert a.camera_at(now) == b.camera_at(now)


def test_fade_out_holds_covered_until_fade_in():
    c = CN.build([_tr(0, 1000, mode="out"), _tr(2000, 500, mode="in")])
    assert c.overlay_at(500)[0] == pytest.approx(0.5)
    assert c.overlay_at(1500)[0] == pytest.approx(1.0)
    assert c.overlay_at(2250)[0] == pytest.approx(0.5)
    assert c.overlay_at(2500) is None


def test_pulse_goes_up_and_back_to_nothing():
    c = CN.build([_tr(0, 1000, mode="pulse")])
    assert c.overlay_at(0) is None
    assert c.overlay_at(500)[0] == pytest.approx(1.0)
    assert c.overlay_at(1000) is None


def test_interrupting_a_transition_starts_from_current_coverage():
    c = CN.build([_tr(0, 1000, mode="out"), _tr(500, 1000, mode="in")])
    assert c.overlay_at(500)[0] == pytest.approx(0.5)
    assert c.overlay_at(1000)[0] == pytest.approx(0.25)
    assert c.overlay_at(1500) is None


def test_colour_and_kind_come_from_the_event():
    c = CN.build([_tr(0, 1000, mode="out", kind="iris", colour=2)])
    cov, kind, colour = c.overlay_at(900)
    assert kind == "iris" and colour == CN.COLOURS[2]


def test_skip_ends_an_in_transition_at_once():
    c = CN.build([_tr(0, 500, mode="out"), _tr(1000, 1000, mode="in", ease="linear", skip=True)])
    eid = c.skippable_at(1500)
    assert eid == 1
    assert c.overlay_at(1500)[0] == pytest.approx(0.5)
    assert c.overlay_at(1500, skipped={eid}) is None
    assert c.skippable_at(2500) is None


def test_closing_transition_cannot_be_skipped():
    c = CN.build([_tr(0, 1000, mode="out", skip=True)])
    assert c.skippable_at(500) is None
    assert c.overlay_at(500, skipped={0})[0] == pytest.approx(0.5)


def test_skip_flag_off_is_not_skippable():
    c = CN.build([_tr(0, 1000, mode="pulse", skip=False)])
    assert c.skippable_at(500) is None


def test_zero_coverage_is_none_not_a_blank_cover():
    c = CN.build([_tr(0, 1000, mode="in")])
    assert c.overlay_at(0) is None


def test_rest_camera_leaves_frame_untouched():
    s = pygame.Surface((32, 24))
    s.fill((10, 200, 30))
    before = _grid(s)
    CN.apply_camera(s, CN.CAM_REST)
    assert _grid(s) == before


def _split():
    s = pygame.Surface((40, 30))
    s.fill((0, 0, 0))
    pygame.draw.rect(s, (255, 0, 0), (0, 0, 20, 30))
    pygame.draw.rect(s, (0, 0, 255), (20, 0, 20, 30))
    return s


def test_zoom_in_magnifies_the_centre_and_fills_the_frame():
    s = _split()
    CN.apply_camera(s, (200.0, 0.0, 0.0), smooth=False)
    left, right = s.get_at((0, 15)), s.get_at((39, 15))
    assert left[0] > 200 and left[2] < 50
    assert right[2] > 200 and right[0] < 50
    assert all(s.get_at((x, y))[:3] != (0, 0, 0) for x in (0, 39) for y in (0, 29))


def test_pan_shifts_the_picture_and_leaves_black_edge():
    s = _split()
    CN.apply_camera(s, (100.0, 8.0, 0.0), smooth=False)
    assert all(s.get_at((x, 15))[:3] == (0, 0, 0) for x in range(8))
    assert s.get_at((30, 15))[:3] != (0, 0, 0)


def test_zoom_out_letterboxes_with_black():
    s = pygame.Surface((40, 30))
    s.fill((200, 200, 200))
    CN.apply_camera(s, (50.0, 0.0, 0.0), smooth=False)
    assert s.get_at((0, 0))[:3] == (0, 0, 0)
    assert s.get_at((20, 15))[:3] == (200, 200, 200)


def test_fade_overlay_blends_colour_by_coverage():
    s = pygame.Surface((8, 6))
    s.fill((200, 200, 200))
    CN.apply_overlay(s, (1.0, "fade", (0, 0, 0)))
    assert s.get_at((3, 3))[:3] == (0, 0, 0)
    s.fill((200, 200, 200))
    CN.apply_overlay(s, (0.5, "fade", (0, 0, 0)))
    assert 90 < s.get_at((3, 3))[0] < 110


def test_wipe_covers_left_part_by_coverage():
    s = pygame.Surface((40, 6))
    s.fill((200, 200, 200))
    CN.apply_overlay(s, (0.5, "wipe", (255, 70, 70)))
    assert s.get_at((5, 3))[:3] == (255, 70, 70)
    assert s.get_at((35, 3))[:3] == (200, 200, 200)


def test_iris_closes_to_a_circle_and_opens_again():
    s = pygame.Surface((60, 40))
    s.fill((200, 200, 200))
    CN.apply_overlay(s, (1.0, "iris", (0, 0, 0)))
    assert s.get_at((30, 20))[:3] == (0, 0, 0) and s.get_at((0, 0))[:3] == (0, 0, 0)
    s.fill((200, 200, 200))
    CN.apply_overlay(s, (0.0001, "iris", (0, 0, 0)))
    assert s.get_at((0, 0))[:3] == (200, 200, 200)
    s.fill((200, 200, 200))
    CN.apply_overlay(s, (0.5, "iris", (0, 0, 0)))
    assert s.get_at((30, 20))[:3] == (200, 200, 200)
    assert s.get_at((0, 0))[:3] == (0, 0, 0)


def test_no_overlay_state_draws_nothing():
    s = pygame.Surface((8, 6))
    s.fill((9, 9, 9))
    before = _grid(s)
    CN.apply_overlay(s, None)
    assert _grid(s) == before


def test_bad_colour_index_falls_back_to_black():
    c = CN.build([_tr(0, 1000, mode="out", colour=99)])
    assert c.overlay_at(500)[2] == CN.COLOURS[0]
