"""Анимации: интерполяция, цикл, нормализация и правка ключей (core/anim.py)."""
import pytest

import anim as AN


#-- Помощники

def _anim(keys, dur=1000, loop=False):
    return {"id": "a1", "name": "A", "dur": dur, "loop": loop, "keys": keys}


def _key(t, ease="linear", **kw):
    return AN.make_key(t, ease=ease, **kw)


#-- Интерполяция

def test_linear_interpolation_between_two_keys():
    a = _anim([_key(0, x=0), _key(1000, x=100)])
    assert AN.sample(a, 250)["x"] == pytest.approx(25)
    assert AN.sample(a, 1000)["x"] == pytest.approx(100)


def test_time_is_clamped_outside_the_animation():
    a = _anim([_key(0, alpha=0), _key(1000, alpha=100)])
    assert AN.sample(a, -50)["alpha"] == 0
    assert AN.sample(a, 5000)["alpha"] == 100


def test_ease_in_out_is_symmetric_and_flat_at_ends():
    assert AN.ease("ease_in_out", 0.0) == 0.0
    assert AN.ease("ease_in_out", 1.0) == 1.0
    assert AN.ease("ease_in_out", 0.5) == pytest.approx(0.5)
    assert AN.ease("ease_in_out", 0.25) < 0.25


def test_ease_in_starts_slow_and_ease_out_starts_fast():
    assert AN.ease("ease_in", 0.5) < 0.5
    assert AN.ease("ease_out", 0.5) > 0.5


def test_step_holds_left_value_until_the_next_key():
    a = _anim([_key(0, ease="step", x=0), _key(1000, x=80)])
    assert AN.sample(a, 999)["x"] == 0
    assert AN.sample(a, 1000)["x"] == 80


def test_ease_is_taken_from_the_left_key():
    a = _anim([_key(0, ease="ease_out", scale=100), _key(1000, scale=200)])
    assert AN.sample(a, 500)["scale"] > 150


def test_tint_is_interpolated_per_channel_and_stays_integer():
    a = _anim([_key(0, tint=[0, 0, 0]), _key(1000, tint=[255, 128, 0])])
    tint = AN.sample(a, 500)["tint"]
    assert tint == (128, 64, 0) or tint == (127, 64, 0)
    assert all(isinstance(c, int) for c in tint)


def test_loop_wraps_time_and_keeps_end_connected_to_start():
    a = _anim([_key(0, x=0), _key(500, x=100)], dur=1000, loop=True)
    assert AN.sample(a, 1250)["x"] == pytest.approx(AN.sample(a, 250)["x"])
    assert AN.sample(a, 750)["x"] == pytest.approx(50)


def test_loop_ends_back_at_start_value():
    a = _anim([_key(0, x=0), _key(500, x=100)], dur=1000, loop=True)
    assert AN.sample(a, 999)["x"] == pytest.approx(0, abs=1)


#-- Нормализация

def _warned(raw, **kw):
    codes = []
    out = AN.normalize(raw, warn=lambda code, **a: codes.append(code), **kw)
    return out, codes


def test_normalize_keeps_a_valid_animation_without_warnings():
    raw = {"id": "ab12", "name": "Рывок", "dur": 1000, "loop": True,
           "keys": [{"t": 0, "ease": "ease_in", "x": 0, "y": 0, "scale": 100, "rot": 0, "alpha": 100,
                     "tint": [255, 255, 255]},
                    {"t": 800, "ease": "linear", "x": 40, "y": 0, "scale": 100, "rot": 0, "alpha": 100,
                     "tint": [255, 255, 255]}]}
    anim, codes = _warned(raw)
    assert codes == []
    assert anim["id"] == "ab12" and anim["dur"] == 1000 and anim["loop"] is True
    assert [k["t"] for k in anim["keys"]] == [0, 800]


def test_key_at_loop_end_is_reported_because_wrap_ignores_it():
    anim, codes = _warned({"id": "ab13", "dur": 800, "loop": True,
                           "keys": [{"t": 0}, {"t": 800, "x": 40}]})
    assert "anim.loop_key" in codes
    assert [k["t"] for k in anim["keys"]] == [0, 800]


def test_values_are_clamped_to_limits_and_bad_types_get_defaults():
    raw = {"id": "x1", "dur": 1000, "keys": [
        {"t": 0, "x": 99999, "scale": -5, "alpha": "много", "tint": [999, -4, 10]}]}
    anim, codes = _warned(raw)
    key = anim["keys"][0]
    assert key["x"] == AN.LIMITS["x"][1]
    assert key["scale"] == AN.LIMITS["scale"][0]
    assert key["alpha"] == AN.DEFAULT_VALUES["alpha"]
    assert key["tint"] == [255, 0, 10]
    assert "anim.value" in codes


def test_unknown_ease_falls_back_to_default_with_warning():
    anim, codes = _warned({"id": "x2", "keys": [{"t": 0, "ease": "bounce"}]})
    assert anim["keys"][0]["ease"] == AN.DEFAULT_EASE
    assert "anim.ease" in codes


def test_missing_start_key_is_created_at_zero():
    anim, _ = _warned({"id": "x3", "dur": 1000, "keys": [{"t": 400, "x": 10}]})
    assert anim["keys"][0]["t"] == 0 and anim["keys"][0]["x"] == 10
    assert anim["keys"][-1]["t"] == 400


def test_empty_keys_get_a_default_pair():
    anim, _ = _warned({"id": "x4", "dur": 700, "keys": []})
    assert [k["t"] for k in anim["keys"]] == [0, 700]


def test_duplicate_key_times_keep_the_first_with_warning():
    anim, codes = _warned({"id": "x5", "dur": 1000, "keys": [{"t": 0}, {"t": 500, "x": 1}, {"t": 500, "x": 9}]})
    assert [k["x"] for k in anim["keys"] if k["t"] == 500] == [1]
    assert "anim.duplicate_key" in codes


def test_duration_is_clamped_to_limits():
    anim, _ = _warned({"id": "x6", "dur": 10**9, "keys": []})
    assert anim["dur"] == AN.DUR_LIMITS[1]


def test_duplicate_id_gets_a_new_one_with_warning():
    anim, codes = _warned({"id": "same", "keys": []}, existing_ids=("same",))
    assert anim["id"] != "same" and "anim.id" in codes


def test_non_dict_animation_is_dropped():
    anim, codes = _warned("нет")
    assert anim is None and codes == ["anim.item_type"]


def test_list_drops_bad_items_and_caps_count():
    raw = [{"id": "a"}, 5, {"id": "a"}]
    out = AN.normalize_list(raw)
    assert [a["id"] for a in out][0] == "a" and len(out) == 2
    many = [{"id": "m%d" % i} for i in range(AN.MAX_ANIMS + 5)]
    codes = []
    out = AN.normalize_list(many, warn=lambda code, **a: codes.append(code))
    assert len(out) == AN.MAX_ANIMS and "anim.too_many" in codes


def test_list_none_is_empty_and_non_list_is_reported():
    assert AN.normalize_list(None) == []
    codes = []
    assert AN.normalize_list({"x": 1}, warn=lambda code, **a: codes.append(code)) == []
    assert codes == ["anim.list_type"]


def test_normalized_tint_list_is_not_shared_with_source():
    src = {"t": 300, "tint": [1, 2, 3]}
    anim, _ = _warned({"id": "s1", "dur": 1000, "keys": [src]})
    anim["keys"][0]["tint"].append(9)
    assert src["tint"] == [1, 2, 3]


#-- Правка

def test_add_key_copies_the_current_value_and_returns_index():
    a = _anim([_key(0, x=0), _key(1000, x=100)])
    idx = AN.add_key(a, 500)
    assert a["keys"][idx]["t"] == 500
    assert a["keys"][idx]["x"] == pytest.approx(50)


def test_add_key_at_existing_time_does_not_duplicate():
    a = _anim([_key(0), _key(1000)])
    assert AN.add_key(a, 1000) == 1 and len(a["keys"]) == 2


def test_first_key_cannot_be_removed_and_last_remaining_stays():
    a = _anim([_key(0), _key(500), _key(1000)])
    assert AN.remove_key(a, 0) is False
    assert AN.remove_key(a, 1) is True
    assert [k["t"] for k in a["keys"]] == [0, 1000]
    assert AN.remove_key(a, 1) is True
    assert AN.remove_key(a, 0) is False


def test_shrinking_duration_keeps_the_end_frame():
    a = _anim([_key(0, x=0), _key(1000, x=100)])
    AN.set_dur(a, 400)
    assert a["dur"] == 400
    assert a["keys"][-1]["t"] == 400
    assert a["keys"][-1]["x"] == pytest.approx(40)


def test_growing_duration_keeps_keys_and_moves_nothing():
    a = _anim([_key(0, x=0), _key(1000, x=100)])
    AN.set_dur(a, 2000)
    assert [k["t"] for k in a["keys"]] == [0, 1000]
    assert a["dur"] == 2000


def test_new_animation_has_two_keys_and_unique_ids():
    a = AN.new_animation(existing_ids=("zz",))
    assert [k["t"] for k in a["keys"]] == [0, AN.DEFAULT_DUR]
    assert a["id"] != "zz" and len(a["id"]) == 8
    assert AN.normalize(a) is not None
