"""Самопроверка: GeometryRhythm.exe --selftest  (из исходников: python main.py --selftest).

Окно не открывается. Проверяются: окружение и пакеты, папки и право записи в data/,
шрифты, звуковое устройство, чарты в songs/ и моды, а также два алгоритма на синтетическом
сигнале — растяжение без смены тона (WSOLA) и авто-ритм. Отчёт печатается и пишется
в data/selftest.log рядом с exe: в собранной версии без консоли читать его нужно из файла.

Код выхода: 0 — нет ошибок (предупреждения возможны), 1 — есть ошибки.
"""
import os
import platform
import sys
import time

OK, WARN, FAIL = "OK", "WARN", "FAIL"


class _Log:
    def __init__(self):
        self.lines = []
        self.counts = {OK: 0, WARN: 0, FAIL: 0}

    def add(self, level, section, text):
        self.counts[level] += 1
        self.lines.append(f"[{level:<4}] {section}: {text}")

    def ok(self, section, text):
        self.add(OK, section, text)

    def warn(self, section, text):
        self.add(WARN, section, text)

    def fail(self, section, text):
        self.add(FAIL, section, text)


def _check_env(log):
    log.ok("Система", f"{platform.platform()}, Python {platform.python_version()}")
    try:
        import pygame
        log.ok("pygame", pygame.version.ver)
    except ImportError as e:
        log.fail("pygame", f"не найден: {e}")
    try:
        import numpy
        log.ok("numpy", numpy.__version__)
    except ImportError:
        log.warn("numpy", "не найден: растяжение темпа и авто-ритм будут недоступны")
    import video
    if video.AVAILABLE:
        log.ok("OpenCV", "видео-события доступны")
    else:
        log.warn("OpenCV", "не найден: видео-события (БЕТА) будут недоступны")


def _check_folders(log):
    import config as C
    for name, must in (("songs", True), ("images", False), ("data", False)):
        path = C.root(name)
        if os.path.isdir(path):
            log.ok("Папки", f"{name}/ найдена")
        elif must:
            log.fail("Папки", f"{name}/ не найдена: {path}")
        else:
            log.warn("Папки", f"{name}/ не найдена (будет создана при необходимости)")
    try:
        os.makedirs(C.root("data"), exist_ok=True)
        probe = C.root("data", "selftest_write.tmp")
        with open(probe, "w", encoding="utf-8") as f:
            f.write("ok")
        os.remove(probe)
        log.ok("Запись", "data/ доступна для записи (настройки, рекорды, кэш)")
    except OSError as e:
        log.fail("Запись", f"data/ недоступна для записи: {e}")


def _check_fonts(log):
    import pygame
    import style as S
    pygame.font.init()
    S.font(13).render("Тест Test", True, (255, 255, 255))
    log.ok("Шрифты", "шрифты загружаются")


def _check_audio(log):
    import pygame
    try:
        pygame.mixer.pre_init(44100, -16, 2, 512)
        pygame.mixer.init()
    except pygame.error as e:
        log.fail("Звук", f"устройство не открылось: {e}. Игра пойдёт без звука")
        return
    if pygame.mixer.get_init():
        freq, fmt, channels = pygame.mixer.get_init()
        log.ok("Звук", f"устройство открыто: {freq} Гц, {channels} канала")
    else:
        log.fail("Звук", "устройство не открылось. Игра пойдёт без звука")


def _check_mods(log):
    import modsys
    modsys.load()
    loaded = modsys.LOADED
    broken = [m.id for m in loaded if m.errors]
    active = sum(1 for m in loaded if m.active)
    if broken:
        log.warn("Моды", f"с ошибками (отключены, игра работает): {', '.join(broken)}")
    log.ok("Моды", f"найдено {len(loaded)}, активно {active} (подробности — data/mods.log)")


def _check_charts(log):
    import songs
    import validation as V
    names = songs.list_songs()
    if names:
        log.ok("Песни", f"найдено песен: {len(names)}")
    else:
        log.warn("Песни", "в songs/ не найдено ни одной песни")
    total, bad, dirty = 0, [], 0
    for path, _from_mod in songs._chart_files():
        total += 1
        ch, rep = songs.load_chart_file(path, check_resources=True)
        if ch is None or rep.sev_counts[V.ERROR]:
            bad.append(os.path.basename(path))
        elif rep.sev_counts[V.WARNING]:
            dirty += 1
    if bad:
        shown = ", ".join(bad[:5]) + (" и др." if len(bad) > 5 else "")
        log.fail("Чарты", f"с ошибками {len(bad)} из {total}: {shown}")
    elif total:
        log.ok("Чарты", f"проверено {total}, ошибок нет")
    else:
        log.warn("Чарты", "чарты не найдены")
    if dirty:
        log.warn("Чарты", f"с предупреждениями (игра их откроет): {dirty}")


def _check_stretch(log):
    import numpy as np
    import stretch
    sr = 44100
    t = np.arange(sr) / sr
    tone = (np.sin(2 * np.pi * 440 * t) * 12000).astype(np.int16)
    arr = np.stack([tone, tone], axis=1)
    out = stretch.wsola(arr, 0.5)
    seconds = len(out) / sr
    x = out[:, 0].astype(np.float64)
    crossings = int(np.count_nonzero(np.signbit(x[1:]) != np.signbit(x[:-1])))
    freq = crossings / 2 / seconds
    if abs(seconds - 2.0) > 0.01:
        log.fail("Растяжение", f"длина {seconds:.3f} с вместо 2.000 с")
    elif abs(freq - 440) > 5:
        log.fail("Растяжение", f"тон изменился: {freq:.1f} Гц вместо 440 Гц")
    else:
        log.ok("Растяжение", f"0.5×: длина {seconds:.2f} с, тон {freq:.1f} Гц (сохранён)")


def _check_beats(log):
    import numpy as np
    import beatdetect
    sr, dur, beat = 22050, 12, 0.5
    y = np.zeros(dur * sr)
    n = int(0.015 * sr)
    tt = np.arange(n) / sr
    burst = np.sin(2 * np.pi * 1000 * tt) * np.exp(-tt / 0.004)
    for when in np.arange(1.0, dur - 1.0, beat):
        i = int(round(when * sr))
        y[i:i + n] += burst
    res = beatdetect.analyze(y, sr)
    if res is None:
        log.fail("Авто-ритм", "ритм не найден на синтетическом сигнале")
        return
    bpm = res["bpm"]
    off = res["offset_ms"] % 500.0
    off_err = min(off, 500.0 - off)
    if abs(bpm - 120) > 1.0 or off_err > 20:
        log.fail("Авто-ритм", f"{bpm:.2f} BPM, смещение {off_err:.0f} мс (ожидалось 120 BPM, ±20 мс)")
    else:
        log.ok("Авто-ритм", f"{bpm:.2f} BPM, смещение ±{off_err:.0f} мс")


CHECKS = (
    ("Система", _check_env),
    ("Папки", _check_folders),
    ("Шрифты", _check_fonts),
    ("Звук", _check_audio),
    ("Моды", _check_mods),
    ("Чарты", _check_charts),
    ("Растяжение", _check_stretch),
    ("Авто-ритм", _check_beats),
)


def run():
    import config as C
    log = _Log()
    started = time.time()
    for name, fn in CHECKS:
        try:
            fn(log)
        except Exception as e:
            log.fail(name, f"проверка упала: {type(e).__name__}: {e}")
    status = ("ОШИБКИ" if log.counts[FAIL] else
              "с предупреждениями" if log.counts[WARN] else "всё в порядке")
    header = [
        f"Geometry Rhythm {C.VERSION} — самопроверка",
        f"Дата: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        f"Папка игры: {C.ROOT_DIR}",
        "",
    ]
    footer = [
        "",
        f"ИТОГ: {status}  (OK {log.counts[OK]}, предупреждений {log.counts[WARN]}, ошибок {log.counts[FAIL]})",
        f"Время: {time.time() - started:.1f} с",
    ]
    text = "\n".join(header + log.lines + footer) + "\n"
    print(text)
    try:
        os.makedirs(C.root("data"), exist_ok=True)
        with open(C.root("data", "selftest.log"), "w", encoding="utf-8") as f:
            f.write(text)
        print(f"Отчёт записан: {C.root('data', 'selftest.log')}")
    except OSError as e:
        print(f"Не удалось записать отчёт: {e}")
    try:
        import pygame
        pygame.quit()
    except Exception:
        pass
    return 1 if log.counts[FAIL] else 0


if __name__ == "__main__":
    sys.exit(run())
