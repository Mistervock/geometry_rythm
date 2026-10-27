"""События «картинка»/«ролик»: растягивание на весь экран."""
import pygame
import pytest

import config as C
import events as EV
import validation as V


@pytest.fixture
def img_dir(tmp_path, monkeypatch):
    s = pygame.Surface((40, 20))
    s.fill((200, 30, 30))
    pygame.image.save(s, str(tmp_path / "red.png"))
    monkeypatch.setattr(EV, "IMAGE_DIR", str(tmp_path))
    EV._src.clear()
    EV._scaled.clear()
    return tmp_path


def _ev(kind="image", **kw):
    ev = EV.normalize({"type": kind, "t": 0, "file": "red.png", "dur": 2000, "w": 200, "h": 100, "fade": 100,
                       "anim": "pop", **kw})
    return ev


def test_full_flag_defaults_and_normalization():
    assert EV.make("image", 0)["full"] is False
    assert EV.make("video", 0)["full"] is False
    assert _ev()["full"] is False                         # старые чарты без поля
    assert _ev(full=True)["full"] is True
    assert _ev(full="yes?")["full"] is False              # мусор не включает режим
    assert "full" not in EV.normalize({"type": "flash", "t": 0})


def test_chart_validation_keeps_full_flag():
    rep = V.Report("t")
    ev = V.check_event({"type": "image", "t": 10, "file": "x.png", "full": True}, "events[0]", rep)
    assert ev["full"] is True


def test_media_size_full_vs_normal():
    assert EV.media_size(_ev(full=True)) == (C.WIDTH, C.HEIGHT)
    assert EV.media_size(_ev("video", full=True)) == (C.WIDTH, C.HEIGHT)
    w, h = EV.media_size(_ev())
    assert w > 0 and h is None
    w, h = EV.media_size(_ev("video"))
    assert w > 0 and h > 0


def test_full_ignores_offset_and_motion():
    ev = _ev(full=True, x=300, y=-200, dx=400, dy=100, anim="drift")
    for el in (100, 1000, 1900):
        _, ox, oy = EV.image_state(ev, el)
        assert (ox, oy) == (0, 0)
    ev2 = _ev(x=300, y=-200, dx=400, dy=100, anim="drift")
    assert EV.image_state(ev2, 1000)[1] != 0


def test_full_image_covers_every_corner(img_dir):
    scr = pygame.Surface((C.WIDTH, C.HEIGHT))
    scr.fill((0, 0, 0))
    EV.draw_media(scr, _ev(full=True), 500)
    for pos in ((0, 0), (C.WIDTH - 1, 0), (0, C.HEIGHT - 1), (C.WIDTH - 1, C.HEIGHT - 1),
                (C.WIDTH // 2, C.HEIGHT // 2)):
        assert scr.get_at(pos)[0] > 100, pos
    scr.fill((0, 0, 0))
    EV.draw_media(scr, _ev(), 500)                        # обычный режим — углы пустые
    assert scr.get_at((0, 0))[0] == 0


def test_full_fade_still_applies(img_dir):
    scr = pygame.Surface((C.WIDTH, C.HEIGHT))
    ev = _ev(full=True, anim="fade", fade=400)
    scr.fill((0, 0, 0))
    EV.draw_media(scr, ev, 50)
    faint = scr.get_at((10, 10))[0]
    scr.fill((0, 0, 0))
    EV.draw_media(scr, ev, 1000)
    assert 0 < faint < scr.get_at((10, 10))[0]


def test_full_video_requests_screen_size(monkeypatch, img_dir):
    got = []
    monkeypatch.setattr(EV.video, "frame", lambda path, key, ms, w, h, bright=1.0: got.append((w, h)) or None)
    scr = pygame.Surface((C.WIDTH, C.HEIGHT))
    EV.draw_media(scr, _ev("video", file="clip.mp4", full=True), 500)
    assert got == [(C.WIDTH, C.HEIGHT)]


def test_prewarm_builds_full_size_surface(img_dir):
    EV.prewarm([_ev(full=True)])
    surf = EV.image_surface("red.png", C.WIDTH, EV.media_bright(), C.HEIGHT)
    assert surf.get_size() == (C.WIDTH, C.HEIGHT)
    assert (("red.png", C.WIDTH, C.HEIGHT, EV.media_bright()) in EV._scaled)


def test_events_screen_toggle_and_fields(img_dir, monkeypatch):
    import events_screen as ES
    import chart as chartmod
    ch = chartmod.Chart("t.ogg")
    scr = ES.EventsScreen(pygame.time.Clock(), ch, 0, 60000)
    scr._add("video")
    keys = [r[0] for r in scr._fields()]
    assert keys[-1] == "full" and len(keys) == 12
    assert scr._fstep() < ES.FIELD_STEP                   # 12 строк: теснее, чтобы влезли
    scr._adjust("full", None, None, None, 1)
    assert scr.cur["full"] is True
    scr._adjust("full", None, None, None, 1)
    assert scr.cur["full"] is False
    scr._add("image")
    assert len(scr._fields()) == 11 and scr._fstep() == ES.FIELD_STEP
    scr.cur["full"] = True
    scr._fit()                                            # не падает
    for kind in ("video", "image"):
        scr._add(kind)
        scr.cur["full"] = True
        scr._draw((5, 5))
