import pytest

import beatgrid as B
import history as H
from chart import Chart, Note
from noteindex import NoteIndex


def make_chart(n=0):
    ch = Chart("a.ogg", notes=[Note(i * 100, i % 4) for i in range(n)])
    ch.sort()
    return ch


def keys(ch):
    return [n.key() for n in ch.notes]


class Clock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


def test_undo_redo_add_remove():
    ch = make_chart(3)
    h = H.EditHistory(ch)
    base = keys(ch)
    a = Note(50, 2)
    h.execute(H.AddNotes([a]))
    assert len(ch.notes) == 4 and ch.notes[1] is a                # вставлена по порядку
    h.execute(H.RemoveNotes([ch.notes[0]]))
    assert len(ch.notes) == 3
    h.undo()
    h.undo()
    assert keys(ch) == base
    h.redo()
    h.redo()
    assert len(ch.notes) == 3 and a in ch.notes


def test_new_operation_clears_redo():
    ch = make_chart(2)
    h = H.EditHistory(ch)
    h.execute(H.AddNotes([Note(1, 0)]))
    h.undo()
    assert h.can_redo()
    h.execute(H.AddNotes([Note(2, 0)]))
    assert not h.can_redo()


def test_modify_notes_and_coalescing():
    clk = Clock()
    ch = make_chart(2)
    h = H.EditHistory(ch, clock=clk)
    n = ch.notes[1]
    old = n.key()
    for dt in (10, 20, 30):                                      # перетаскивание: много мелких правок
        clk.t += 0.05
        cur = n.key()
        h.execute(H.ModifyNotes([(n, cur, (cur[0] + dt, cur[1], cur[2]))], coalesce=("drag", id(n))))
    assert len(h.undo_stack) == 1                                 # одна запись истории
    assert n.t == old[0] + 60
    h.undo()
    assert n.key() == old


def test_coalesce_not_across_time_or_after_save():
    clk = Clock()
    ch = make_chart(1)
    h = H.EditHistory(ch, clock=clk)
    n = ch.notes[0]
    h.execute(H.ModifyNotes([(n, n.key(), (5, 0, 0))], coalesce="k"))
    h.mark_saved()
    h.execute(H.ModifyNotes([(n, n.key(), (9, 0, 0))], coalesce="k"))
    assert len(h.undo_stack) == 2                                 # в сохранённую запись не вливаемся
    assert h.dirty
    clk.t += 5
    h.execute(H.ModifyNotes([(n, n.key(), (11, 0, 0))], coalesce="k"))
    assert len(h.undo_stack) == 3


def test_noop_modify_not_recorded():
    ch = make_chart(1)
    h = H.EditHistory(ch)
    n = ch.notes[0]
    assert not h.execute(H.ModifyNotes([(n, n.key(), n.key())]))
    assert not h.undo_stack


def test_group_is_one_entry():
    ch = make_chart(4)
    h = H.EditHistory(ch)
    base = keys(ch)
    h.begin("batch")
    h.execute(H.RemoveNotes([ch.notes[0]]))
    h.execute(H.AddNotes([Note(7, 3)]))
    h.execute(H.ModifyNotes([(ch.notes[-1], ch.notes[-1].key(), (999, 0, 50))]))
    h.end()
    assert len(h.undo_stack) == 1
    h.undo()
    assert keys(ch) == base
    h.redo()
    assert len(ch.notes) == 4 and any(n.key() == (999, 0, 50) for n in ch.notes)


def test_dirty_tracking_follows_undo_redo():
    ch = make_chart(2)
    h = H.EditHistory(ch)
    assert not h.dirty
    h.execute(H.AddNotes([Note(5, 1)]))
    assert h.dirty
    h.mark_saved()
    assert not h.dirty
    h.undo()
    assert h.dirty
    h.redo()
    assert not h.dirty
    h.force_dirty = True
    assert h.dirty


def test_history_limits_memory():
    ch = make_chart(0)
    h = H.EditHistory(ch, max_commands=10)
    for i in range(50):
        h.execute(H.AddNotes([Note(i * 10, 0)]))
    assert len(h.undo_stack) == 10
    big = H.EditHistory(make_chart(0), max_cost=100)
    for i in range(20):
        big.execute(H.AddNotes([Note(i, 0), Note(i, 1), Note(i, 2)]))
    assert big._cost <= 100 + 3 and len(big.undo_stack) >= 1


def test_events_and_meta_commands():
    ch = make_chart(1)
    h = H.EditHistory(ch)
    before = H.SetEvents.snapshot(ch)
    ch.events.append({"type": "flash", "t": 5})
    h.execute(H.SetEvents(before, H.SetEvents.snapshot(ch)))
    h.undo()
    assert ch.events == []
    h.redo()
    assert len(ch.events) == 1
    snap = H.SetMeta.snapshot(ch)
    ch.name = "Новое"
    h.execute(H.SetMeta(snap, H.SetMeta.snapshot(ch)))
    h.undo()
    assert ch.name == "Чарт"


def test_listener_called_and_rev_increments():
    ch = make_chart(0)
    h = H.EditHistory(ch)
    seen = []
    h.listeners.append(seen.append)
    h.execute(H.AddNotes([Note(1, 1)]))
    h.undo()
    h.redo()
    assert seen == ["do", "undo", "redo"] and h.rev == 3


def test_cancel_group_rolls_back():
    ch = make_chart(2)
    h = H.EditHistory(ch)
    base = keys(ch)
    h.begin()
    h.execute(H.AddNotes([Note(1, 3)]))
    h.cancel_group()
    assert keys(ch) == base and not h.undo_stack


def test_undo_integrity_with_many_random_ops():
    import random
    rnd = random.Random(7)
    ch = make_chart(50)
    h = H.EditHistory(ch)
    snapshots = [keys(ch)]
    for _ in range(80):
        r = rnd.random()
        if r < 0.4:
            h.execute(H.AddNotes([Note(rnd.randrange(0, 9000), rnd.randrange(4))]))
        elif r < 0.7 and ch.notes:
            h.execute(H.RemoveNotes(rnd.sample(ch.notes, min(3, len(ch.notes)))))
        elif ch.notes:
            n = rnd.choice(ch.notes)
            h.execute(H.ModifyNotes([(n, n.key(), (rnd.randrange(0, 9000), rnd.randrange(4), 0))]))
        snapshots.append(keys(ch))
    for want in reversed(snapshots[:-1]):
        h.undo()
        assert keys(ch) == want
    assert not h.can_undo()
    for want in snapshots[1:]:
        h.redo()
        assert keys(ch) == want
    assert keys(ch) == sorted(keys(ch), key=lambda k: (k[0], k[1]))


#-- BPM-сетка

def test_snap_on_off_and_free_placement():
    g = B.BeatGrid({"mode": "beat", "bpm": 120, "div": 4, "offset": 0, "snap": True})
    assert g.step_ms == 125.0
    assert g.place(130) == 125 and g.place(190) == 250
    assert g.place(130, free=True) == 130                        # модификатор отключает привязку на операцию
    g.snap_on = False
    assert g.place(131) == 131 and g.place(0.4) == 0 and g.place(-7) == 0


def test_changing_bpm_never_moves_notes():
    ch = make_chart(5)
    before = keys(ch)
    g = B.BeatGrid(ch.grid)
    g.set_bpm(173.3)
    g.cycle(1)
    g.set_offset(77)
    ch.grid = g.to_dict()
    assert keys(ch) == before


def test_no_float_drift_on_long_tracks():
    g = B.BeatGrid({"mode": "beat", "bpm": 137.0, "div": 16, "offset": 11.0})
    for hours in (1, 3, 6):
        t = hours * 3600 * 1000
        i = g.index_near(t)
        assert abs(g.time_at(i) - t) <= g.step_ms / 2 + 1e-6
        assert g.snap(g.snap(t)) == g.snap(t)                    # идемпотентность


def test_lines_kinds_and_limit():
    g = B.BeatGrid({"mode": "beat", "bpm": 120, "div": 2, "bar": 4, "offset": 0})
    lines = g.lines(0, 4000)
    kinds = [k for _, k in lines]
    assert kinds.count(B.BAR) == 3 and kinds.count(B.BEAT) >= 6 and kinds.count(B.SUB) >= 6
    assert g.lines(0, 10 ** 8) == []                             # слишком плотно — не рисуем ничего лишнего
    g.show_bars = False
    assert B.BAR not in [k for _, k in g.lines(0, 4000)]


def test_cycle_includes_custom_division():
    g = B.BeatGrid({"mode": "beat", "div": 5})
    assert ("beat", 5) in g.specs()
    seen = set()
    for _ in range(len(g.specs())):
        g.cycle(1)
        seen.add(g.spec())
    assert len(seen) == len(g.specs())


def test_snap_changes_only_moves_off_grid_notes():
    g = B.BeatGrid({"mode": "ms", "ms_step": 50})
    notes = [Note(100, 0), Note(113, 1)]
    ch = B.snap_changes(notes, g)
    assert len(ch) == 1 and ch[0][2][0] == 100 + 0 or ch[0][2][0] == 100


def test_note_index_window_and_nearest():
    notes = [Note(100, 0, 5000), Note(200, 1), Note(300, 2), Note(10_000, 0)]
    idx = NoteIndex(notes)
    got = [n.t for n in idx.visible(4000, 4500)]
    assert got == [100]                                          # длинное удержание видно, пока не кончилось
    assert [n.t for n in idx.visible(0, 250)] == [100, 200]
    assert idx.nearest(290, limit=50).t == 300 and idx.nearest(1000, limit=50) is None
    assert idx.nearest(150, lane=2, limit=500).t == 300
    assert [n.t for n in idx.in_range(150, 350)] == [200, 300]


def test_note_index_large():
    notes = [Note(i * 3, i % 4) for i in range(200_000)]
    idx = NoteIndex(notes)
    assert len(list(idx.visible(300_000, 301_000))) <= 340
