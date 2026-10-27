import config as C
import engine as EN
import scoring
from chart import Note


def mk(specs):
    notes = [Note(t, lane, d) for t, lane, d in specs]
    for i, n in enumerate(notes):
        n.idx = i
    return notes


def run_hit(e, lane, t, off=0):
    e.update(t + off)
    e.press(lane, t + off)


def test_grades_and_offsets():
    e = EN.Engine(mk([(1000, 0, 0), (2000, 1, 0), (3000, 2, 0), (4000, 3, 0)]))
    run_hit(e, 0, 1000, 0)
    run_hit(e, 1, 2000, -60)
    run_hit(e, 2, 3000, 100)
    e.update(4000 + C.WIN_GOOD + 5)
    assert e.counts == {"perfect": 1, "great": 1, "good": 1, "miss": 1}
    offs = [j.offset for j in e.judgments if j.grade != "miss"]
    assert offs == [0, -60, 100]
    s = e.summary()
    assert s["early"] == 1 and s["late"] == 1
    assert s["mean_offset"] == round((0 - 60 + 100) / 3, 2)
    assert s["total"] == 4 and s["judged"] == 4
    assert not s["full_combo"]


def test_broken_hold_counts_in_accuracy():
    e = EN.Engine(mk([(1000, 0, 1000), (3000, 1, 0)]))
    e.update(1000)
    e.press(0, 1000)
    e.update(1400)
    e.release(0, 1400)                 # рано отпустили: хвост сорван
    run_hit(e, 1, 3000)
    assert e.holds_broken == 1 and e.holds_ok == 0
    # решения: голова 1.0, хвост 0.0, обычная нота 1.0 → 2/3
    assert abs(e.accuracy() - 100 * 2 / 3) < 1e-9
    assert e.summary()["holds_broken"] == 1 and not e.summary()["full_combo"]


def test_hold_ok_and_ticks_do_not_depend_on_frame_rate():
    def play(step):
        e = EN.Engine(mk([(1000, 0, 2000)]))
        e.update(1000)
        e.press(0, 1000)
        t = 1000
        while t < 3000:
            t += step
            e.update(min(t, 3000))
        assert e.holds_ok == 1
        return e.score
    assert play(1) == play(16) == play(250)


def test_miss_costs_hp_and_fails():
    e = EN.Engine(mk([(1000 + i * 500, 0, 0) for i in range(8)]))
    e.update(10000)
    assert e.failed and e.done


def test_practice_never_fails_and_hp_toggle():
    notes = mk([(1000 + i * 500, 0, 0) for i in range(8)])
    e = EN.Engine(notes, practice=True, hp_loss=False)
    e.update(10000)
    assert not e.failed and e.hp == C.MAX_HP
    assert e.counts["miss"] == 8 and e.summary()["grade"] == "D"
    e = EN.Engine(mk([(1000 + i * 500, 0, 0) for i in range(8)]), practice=True, hp_loss=True)
    e.update(10000)
    assert e.hp == 1 and not e.failed


def test_section_reset_has_no_leftovers():
    notes = mk([(500, 0, 0), (1000, 1, 600), (2000, 2, 0), (3000, 3, 0)])
    e = EN.Engine(notes, practice=True)
    e.set_section(1000, 2000)
    e.start_attempt()
    assert e.total == 2 and notes[0].state == "skip" and notes[3].state == "skip"
    e.update(1000)
    e.press(1, 1000)
    e.update(1200)
    e.release(1, 1200)                       # сорвали удержание
    e.update(2000 + C.WIN_GOOD + 1)
    assert e.counts["miss"] == 1 and e.holds_broken == 1
    assert e.combo == 0
    # повтор: всё с нуля, ноты не дублируются
    e.start_attempt()
    assert e.total == 2 and e.score == 0 and e.counts["miss"] == 0 and not e.holds and e.judgments == []
    assert all(n.state in ("wait", "skip") for n in notes)
    assert sum(len(q) for q in e.pending) == 2
    assert e.attempt == 3


def test_boundary_notes_inclusive_and_hold_extends_end():
    notes = mk([(1000, 0, 0), (2000, 1, 1500), (2001, 2, 0)])
    e = EN.Engine(notes, practice=True)
    e.set_section(1000, 2000)
    e.start_attempt()
    assert [n.idx for n in e.active] == [0, 1]
    assert e.end_time >= 3500                # хвост удержания, начатого внутри участка, не обрезается


def test_finish_when_all_done():
    e = EN.Engine(mk([(1000, 0, 0)]), duration=60000)
    run_hit(e, 0, 1000)
    e.update(1000 + 1300)
    assert e.done and not e.failed
    assert e.summary()["full_combo"]


def test_inputs_logged_and_heal():
    e = EN.Engine(mk([(5000, 0, 0)]), heals=[{"t": 1000, "lane": 1, "fall": 1000}], max_hp=5)
    e.hp = 3
    e.press(1, 1010)
    assert e.hp == 4
    assert e.inputs == [(1010.0, 1, 1)]


def test_scoring_buckets_and_compare():
    e = EN.Engine(mk([(1000 + i * 100, i % 4, 0) for i in range(30)]))
    for n in list(e.notes):
        run_hit(e, n.lane, n.t, (n.idx % 7) * 10 - 30)
    s = e.summary()
    assert sum(s["hist"]["bins"]) == 30
    assert len(s["series"]) == scoring.SERIES_BUCKETS
    assert sum(b["n"] for b in s["series"]) == 30
    assert s["running"][-1][1] == s["acc"]
    best = dict(s, score=s["score"] + 100, acc=s["acc"] + 1.0)
    cmp = scoring.compare(s, best)
    assert cmp["score"] == -100 and not cmp["better"]
    assert scoring.compare(s, None) is None


def test_grade_thresholds():
    assert [scoring.grade_for(a) for a in (100, 95, 94.9, 85, 70, 50, 10)] == list("SSAABCD")
    assert scoring.grade_for(99, failed=True) == "F"
