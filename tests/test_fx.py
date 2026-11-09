"""Эффекты изображения (core/fx.py): огибающая, пульс в такт, пиксели, качество, бюджет и откат."""
import pygame
import pytest

import fx as FX
import settings


#-- Помощники

@pytest.fixture
def split():
    """Левая половина красная, правая синяя: на границе видно размытие, хроматику и сдвиг."""
    s = pygame.Surface((64, 48))
    s.fill((0, 0, 0))
    pygame.draw.rect(s, (255, 0, 0), (0, 0, 32, 48))
    pygame.draw.rect(s, (0, 0, 255), (32, 0, 32, 48))
    return s


def _fx(**kw):
    ev = {"type": "fx", "t": 0, "kind": "blur", "amount": 100, "attack": 0, "dur": 1000, "beat": False}
    ev.update(kw)
    return ev


def _px(surf, x, y):
    c = surf.get_at((x, y))
    return c.r, c.g, c.b


def _bytes(surf):
    return pygame.image.tostring(surf, "RGB")


#-- Огибающая и сила

def test_envelope_rises_holds_and_falls():
    ev = _fx(attack=200, dur=1000)
    assert FX.envelope(ev, -1) == 0.0
    assert FX.envelope(ev, 100) == pytest.approx(0.5)
    assert FX.envelope(ev, 500) == 1.0
    assert FX.envelope(ev, 900) == pytest.approx(0.5)
    assert FX.envelope(ev, 1000) == 0.0


def test_envelope_without_attack_is_flat_inside_the_event():
    ev = _fx(attack=0, dur=1000)
    assert FX.envelope(ev, 0) == 1.0 and FX.envelope(ev, 999) == 1.0


def test_level_scales_by_amount():
    ev = _fx(amount=50, attack=0, dur=1000)
    assert FX.level(ev, 500) == pytest.approx(0.5)


def test_level_is_clamped_to_one():
    assert FX.level(_fx(amount=100), 500) <= 1.0


def test_beat_factor_is_full_on_the_beat_and_dips_between_beats():
    assert FX.beat_factor(0, 120, 0) == pytest.approx(1.0)
    assert FX.beat_factor(250, 120, 0) == pytest.approx(0.625)
    assert FX.beat_factor(499.9, 120, 0) == pytest.approx(0.5, abs=0.01)


def test_beat_factor_respects_offset_and_missing_tempo():
    assert FX.beat_factor(1000, 120, 1000) == pytest.approx(1.0)
    assert FX.beat_factor(777, 0, 0) == 1.0
    assert FX.beat_factor(777, None, 0) == 1.0


def test_level_with_beat_flag_follows_the_grid():
    ev = _fx(amount=100, attack=0, dur=1000, beat=True)
    grid = {"bpm": 120, "offset": 0}
    assert FX.level(ev, 0, grid) == pytest.approx(1.0)
    assert FX.level(ev, 250, grid) == pytest.approx(0.625)
    assert FX.level(ev, 250) == pytest.approx(1.0)


def test_active_levels_keeps_strongest_per_kind_and_skips_other_events():
    events = [_fx(kind="glow", amount=40), _fx(kind="glow", amount=80), _fx(kind="mono", amount=30, t=600),
              {"type": "flash", "t": 0, "attack": 10, "dur": 100}]
    levels = dict(FX.active_levels(events, 100))
    assert levels["glow"] == pytest.approx(0.8)
    assert "mono" not in levels
    assert len(levels) == 1


#-- Пиксели

def test_blur_leaks_colour_across_the_edge(split):
    FX.apply_kind(split, "blur", 1.0, 0)
    r, g, b = _px(split, 31, 24)
    assert b > 0 and r < 255


def test_mono_makes_channels_equal(split):
    FX.apply_kind(split, "mono", 1.0, 0)
    r, g, b = _px(split, 10, 10)
    assert r == g == b


def test_warm_tint_favours_red_over_blue():
    s = pygame.Surface((8, 8))
    s.fill((255, 255, 255))
    FX.apply_kind(s, "warm", 1.0, 0)
    r, g, b = _px(s, 4, 4)
    assert r > g > b


def test_cool_tint_favours_blue_over_red():
    s = pygame.Surface((8, 8))
    s.fill((255, 255, 255))
    FX.apply_kind(s, "cool", 1.0, 0)
    r, g, b = _px(s, 4, 4)
    assert b > g > r


def test_zero_level_tint_changes_nothing():
    s = pygame.Surface((8, 8))
    s.fill((120, 60, 30))
    before = _bytes(s)
    FX.apply_kind(s, "warm", 0.0, 0)
    assert _bytes(s) == before


def test_chroma_changes_the_edge(split):
    before = _bytes(split)
    FX.apply_kind(split, "chroma", 1.0, 0)
    assert _bytes(split) != before


def test_wave_shifts_rows_sideways(split):
    FX.apply_kind(split, "wave", 1.0, 90)
    assert _px(split, 34, 0)[0] == 255 and _px(split, 34, 0)[2] == 0


def test_glow_brightens_around_a_bright_spot():
    s = pygame.Surface((64, 48))
    s.fill((0, 0, 0))
    pygame.draw.rect(s, (255, 255, 255), (30, 20, 4, 4))
    FX.apply_kind(s, "glow", 1.0, 0)
    assert sum(_px(s, 26, 22)) > 0


def test_unknown_kind_raises_value_error():
    with pytest.raises(ValueError):
        FX.apply_kind(pygame.Surface((4, 4)), "nope", 1.0, 0)


def test_every_kind_runs_on_a_small_surface():
    for kind in FX.KINDS:
        s = pygame.Surface((5, 3))
        s.fill((90, 90, 90))
        FX.apply_kind(s, kind, 0.7, 10, low=True)
        FX.apply_kind(s, kind, 0.7, 10, low=False)
        assert s.get_size() == (5, 3)


#-- Качество, бюджет и откат

def _set_quality(monkeypatch, value):
    monkeypatch.setattr(settings, "get", lambda key: value if key == "fx_quality" else 0)


def test_quality_off_leaves_frame_untouched(monkeypatch, split):
    _set_quality(monkeypatch, 0)
    before = _bytes(split)
    FX.frame(split, [("mono", 1.0)], 0, FX.Budget())
    assert _bytes(split) == before


def test_quality_high_applies_layers(monkeypatch, split):
    _set_quality(monkeypatch, 2)
    FX.frame(split, [("mono", 1.0)], 0, FX.Budget())
    r, g, b = _px(split, 10, 10)
    assert r == g == b


def test_quality_low_keeps_frame_size_and_still_applies(monkeypatch, split):
    _set_quality(monkeypatch, 1)
    before = _bytes(split)
    FX.frame(split, [("wave", 1.0), ("blur", 0.5)], 90, FX.Budget())
    assert split.get_size() == (64, 48)
    assert _bytes(split) != before


def test_empty_layers_do_nothing(monkeypatch, split):
    _set_quality(monkeypatch, 2)
    before = _bytes(split)
    FX.frame(split, [], 0, FX.Budget())
    assert _bytes(split) == before


def test_slow_frames_downgrade_high_to_low(monkeypatch):
    _set_quality(monkeypatch, 2)
    bud = FX.Budget()
    assert bud.mode() == "high"
    for _ in range(FX.SAMPLES):
        bud.record(FX.BUDGET_MS + 4)
    assert bud.mode() == "low"


def test_fast_frames_keep_high_quality(monkeypatch):
    _set_quality(monkeypatch, 2)
    bud = FX.Budget()
    for _ in range(FX.SAMPLES * 2):
        bud.record(0.5)
    assert bud.mode() == "high"


def test_auto_downgrade_never_turns_off_a_low_setting(monkeypatch):
    _set_quality(monkeypatch, 1)
    bud = FX.Budget()
    for _ in range(FX.SAMPLES):
        bud.record(50.0)
    assert bud.mode() == "low"


def test_failing_effect_is_disabled_and_others_still_run(monkeypatch, split):
    _set_quality(monkeypatch, 2)
    calls = []

    def fake(surface, kind, lvl, now, low=False):
        calls.append(kind)
        if kind == "blur":
            raise pygame.error("unsupported")

    monkeypatch.setattr(FX, "apply_kind", fake)
    bud = FX.Budget()
    FX.frame(split, [("blur", 0.5), ("mono", 1.0)], 0, bud)
    assert "blur" in bud.broken
    assert calls == ["blur", "mono"]
    FX.frame(split, [("blur", 0.5), ("mono", 1.0)], 0, bud)
    assert calls == ["blur", "mono", "mono"]


def test_unknown_kind_in_frame_is_reported_as_broken(monkeypatch, split):
    _set_quality(monkeypatch, 2)
    bud = FX.Budget()
    FX.frame(split, [("nope", 1.0)], 0, bud)
    assert "nope" in bud.broken


def test_missing_pygame_functions_turn_effects_off(monkeypatch, split):
    _set_quality(monkeypatch, 2)
    monkeypatch.setattr(FX, "available", lambda: False)
    before = _bytes(split)
    FX.frame(split, [("mono", 1.0)], 0, FX.Budget())
    assert _bytes(split) == before


def test_object_look_returns_copy_only_when_effect_applies(monkeypatch):
    _set_quality(monkeypatch, 2)
    s = pygame.Surface((8, 8))
    s.fill((200, 10, 10))
    assert FX.look(s, "", 50, 0) is s
    assert FX.look(s, "mono", 0, 0) is s
    out = FX.look(s, "mono", 100, 0)
    assert out is not s
    r, g, b = _px(out, 4, 4)
    assert r == g == b
    assert _px(s, 4, 4) == (200, 10, 10)


def test_object_look_is_off_with_setting_zero(monkeypatch):
    _set_quality(monkeypatch, 0)
    s = pygame.Surface((8, 8))
    assert FX.look(s, "blur", 100, 0) is s


def test_available_in_this_pygame():
    assert FX.available()
