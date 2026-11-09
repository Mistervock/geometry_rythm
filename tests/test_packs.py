"""Пакеты визуальных эффектов (core/packs.py): проверка файлов, библиотека, параметры, лимиты и отрисовка."""
import json

import pygame
import pytest

import packs as PK


def _good(pid="mine", **kw):
    pack = {"format": PK.FORMAT, "api": PK.API, "id": pid, "name": "Мой", "dur": 800,
            "params": [{"id": "size", "name": "Размер", "min": 10, "max": 100, "step": 5, "default": 50}],
            "layers": [{"kind": "ring", "start": 0, "end": 1, "radius": [0, "$size"], "width": 4,
                        "alpha": [255, 0], "colour": "$colour"}]}
    pack.update(kw)
    return pack


def _write(folder, name, data):
    folder.mkdir(parents=True, exist_ok=True)
    p = folder / name
    p.write_text(json.dumps(data, ensure_ascii=False) if not isinstance(data, str) else data, encoding="utf-8")
    return p


@pytest.fixture(autouse=True)
def _restore_library():
    yield
    PK.reload()


@pytest.fixture
def lib(tmp_path):
    builtin = tmp_path / "builtin"
    user = tmp_path / "user"
    user.mkdir()
    return builtin, user


def test_shipped_packs_all_load_without_issues():
    reg = PK.reload(builtin=PK.BUILTIN_DIR, user=PK.USER_DIR)
    assert {"burst", "ring_pulse", "sparks", "fade_puff"} <= set(reg)
    assert "_template" not in "".join(reg)
    bad = [i for i in PK.issues() if i[1] != "pack.file"]
    assert bad == []


def test_template_file_is_not_loaded_as_a_pack(lib):
    builtin, user = lib
    _write(builtin, "_template.json", _good("template_only"))
    reg = PK.reload(builtin=builtin, user=user)
    assert reg == {}


def test_good_pack_passes_and_keeps_its_fields():
    clean, probs = PK.validate(_good())
    assert probs == []
    assert clean["id"] == "mine" and clean["dur"] == 800
    assert clean["params"][0]["default"] == 50 and len(clean["layers"]) == 1


@pytest.mark.parametrize("raw, code", [
    ("не объект", "pack.not_object"),
    ({"format": "other", "api": 1, "id": "x_y", "layers": []}, "pack.format"),
    (_good(api=True), "pack.api"),
    (_good(api=2), "pack.api_new"),
    (_good(id="Bad Id"), "pack.id"),
    (_good(layers=[]), "pack.no_layers"),
    (_good(layers="ring"), "pack.no_layers"),
])
def test_unusable_packs_are_refused_with_reason(raw, code):
    clean, probs = PK.validate(raw)
    assert clean is None
    assert any(c == code for c, _ in probs)


def test_unknown_layer_kind_is_skipped_others_kept():
    raw = _good(layers=[{"kind": "laser"}, {"kind": "flash", "radius": 40}])
    clean, probs = PK.validate(raw)
    assert [L["kind"] for L in clean["layers"]] == ["flash"]
    assert any(c == "pack.layer_kind" for c, _ in probs)


def test_out_of_range_values_are_clamped_and_reported():
    raw = _good(layers=[{"kind": "ring", "radius": [0, 9999], "width": 500, "alpha": 300}])
    clean, probs = PK.validate(raw)
    L = clean["layers"][0]
    assert L["radius"][1] == PK.RADIUS_MAX and L["width"] == 40 and L["alpha"] == 255
    assert any(c == "pack.range" for c, _ in probs)


def test_unknown_parameter_reference_is_reported_and_defaulted():
    raw = _good(layers=[{"kind": "ring", "radius": "$nope"}])
    clean, probs = PK.validate(raw)
    assert clean is not None
    assert any(c == "pack.unknown_param" for c, _ in probs)


def test_bad_colour_falls_back_to_white_with_warning():
    clean, probs = PK.validate(_good(layers=[{"kind": "flash", "colour": "красный"}]))
    assert clean["layers"][0]["colour"] == PK.PALETTE[0]
    assert any(c == "pack.colour" for c, _ in probs)


def test_too_many_layers_keeps_the_first_eight():
    layers = [{"kind": "flash", "radius": 20} for _ in range(10)]
    clean, probs = PK.validate(_good(layers=layers))
    assert len(clean["layers"]) == PK.MAX_LAYERS
    assert any(c == "pack.too_many" for c, _ in probs)


def test_broken_json_file_is_reported_and_others_still_load(lib):
    builtin, user = lib
    _write(builtin, "broken.json", "{не json")
    _write(builtin, "good.json", _good("good_one"))
    reg = PK.reload(builtin=builtin, user=user)
    assert set(reg) == {"good_one"}
    assert any(name == "broken.json" and code == "pack.file" for name, code, _ in PK.issues())


def test_user_pack_replaces_shipped_pack_with_same_id(lib):
    builtin, user = lib
    _write(builtin, "a.json", _good("shared", name="Поставляемый"))
    _write(user, "b.json", _good("shared", name="Мой вариант"))
    reg = PK.reload(builtin=builtin, user=user)
    assert reg["shared"]["name"] == "Мой вариант"
    assert any(code == "pack.duplicate" for _, code, _ in PK.issues())


def test_known_ids_and_get_follow_the_registry(lib):
    builtin, user = lib
    _write(user, "c.json", _good("only_user"))
    PK.reload(builtin=builtin, user=user)
    assert PK.known_ids() == {"only_user"}
    assert PK.get("only_user")["id"] == "only_user"
    assert PK.get("missing") is None


def test_parameters_are_clamped_and_defaulted():
    pack, _ = PK.validate(_good())
    assert PK.resolve_params(pack, {"size": 9999})["size"] == 100
    assert PK.resolve_params(pack, {"size": -5})["size"] == 10
    assert PK.resolve_params(pack, {"size": "много"})["size"] == 50
    assert PK.resolve_params(pack, None)["size"] == 50


def test_particle_budget_is_capped_across_layers():
    layers = [{"kind": "particles", "count": 48, "speed": [10, 20]} for _ in range(3)]
    pack, _ = PK.validate(_good(layers=layers))
    inst = PK.make_instance(pack, {}, power=200, colour_idx=0, seed=1, dur=800)
    total = sum(len(L["items"]) for L in inst.layers if L["kind"] == "particles")
    assert total <= PK.MAX_PARTICLES


def test_power_scales_particle_count():
    pack, _ = PK.validate(_good(layers=[{"kind": "particles", "count": 10}]))
    low = PK.make_instance(pack, {}, power=50, colour_idx=0, seed=2, dur=800)
    high = PK.make_instance(pack, {}, power=150, colour_idx=0, seed=2, dur=800)
    assert len(low.layers[0]["items"]) < len(high.layers[0]["items"])


def test_same_seed_gives_same_particles_and_other_seed_differs():
    pack, _ = PK.validate(_good(layers=[{"kind": "particles", "count": 12}]))
    a = PK.make_instance(pack, {}, 100, 0, seed=7, dur=800).layers[0]["items"]
    b = PK.make_instance(pack, {}, 100, 0, seed=7, dur=800).layers[0]["items"]
    c = PK.make_instance(pack, {}, 100, 0, seed=8, dur=800).layers[0]["items"]
    assert a == b and a != c


def test_drawing_outside_the_pack_life_changes_nothing():
    pack, _ = PK.validate(_good())
    inst = PK.make_instance(pack, {"size": 60}, 100, 0, seed=1, dur=800)
    surf = pygame.Surface((400, 300))
    surf.fill((0, 0, 0))
    before = pygame.image.tostring(surf, "RGB")
    PK.draw(surf, inst, -50, 200, 150)
    PK.draw(surf, inst, 900, 200, 150)
    assert pygame.image.tostring(surf, "RGB") == before


def test_ring_is_drawn_around_the_origin_mid_life():
    pack, _ = PK.validate(_good(layers=[{"kind": "ring", "radius": [30, 30], "width": 6, "alpha": 255}]))
    inst = PK.make_instance(pack, {}, 100, 0, seed=1, dur=800)
    surf = pygame.Surface((400, 300))
    surf.fill((0, 0, 0))
    PK.draw(surf, inst, 400, 200, 150)
    lit = sum(1 for x in range(400) for y in range(300) if sum(surf.get_at((x, y))[:3]) > 0)
    assert lit > 0
    assert sum(surf.get_at((200, 150))[:3]) == 0


def test_trail_particles_draw_without_error():
    pack, _ = PK.validate(_good(layers=[{"kind": "particles", "count": 8, "trail": True, "length": 30,
                                         "gravity": 400}]))
    inst = PK.make_instance(pack, {}, 100, 1, seed=3, dur=800)
    surf = pygame.Surface((400, 300))
    surf.fill((0, 0, 0))
    PK.draw(surf, inst, 300, 200, 150)
    assert surf.get_size() == (400, 300)


def test_colour_index_selects_palette_for_colour_token():
    pack, _ = PK.validate(_good(layers=[{"kind": "flash", "radius": 20, "alpha": 255, "colour": "$colour"}]))
    inst = PK.make_instance(pack, {}, 100, 2, seed=1, dur=800)
    assert inst.layers[0]["colour_rgb"] == PK._rgb(PK.PALETTE[2])
