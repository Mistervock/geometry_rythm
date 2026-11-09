import selftest


def test_stretch_check_passes_on_synthetic_tone():
    log = selftest._Log()
    selftest._check_stretch(log)
    assert log.counts[selftest.FAIL] == 0, log.lines


def test_beat_check_passes_on_synthetic_clicks():
    log = selftest._Log()
    selftest._check_beats(log)
    assert log.counts[selftest.FAIL] == 0, log.lines


def test_log_counts_levels():
    log = selftest._Log()
    log.ok("a", "x")
    log.warn("b", "y")
    log.fail("c", "z")
    assert log.counts == {"OK": 1, "WARN": 1, "FAIL": 1}
    assert log.lines[2].startswith("[FAIL] c: ")
