
#-- Импорт
import time
import wave

import pygame

import config as C
import settings

_sounds = {}
_loaded = False


def _load():
    global _loaded
    if _loaded:
        return
    _loaded = True
    try:
        if not pygame.mixer.get_init():
            return
        for name in ("catch", "combo", "hurt", "tick", "split", "shield", "upgrade", "achieve"):
            try:
                _sounds[name] = pygame.mixer.Sound(C.res("sounds", name + ".wav"))
            except Exception:
                pass
    except Exception:
        pass


def play(name, volume=0.6):
    _load()
    snd = _sounds.get(name)
    if snd is not None:
        snd.set_volume(volume * settings.get("sfx_volume") / 100.0)
        snd.play()


_music_path = None

# --- Воспроизведение песни -------------------------------------------------------------------------
# Потоковый mixer.music.play(start=...) для WAV отбрасывает дробную часть секунд (измерено: старт с 7.3 с
# играет с 7.0 с, ошибка до 1 с). Замедленные дорожки — именно WAV, поэтому в редакторе звук «уезжал» от нот.
# Поэтому PCM-WAV (формат которых совпадает с микшером) играются из памяти: срез сэмплов с нужной позиции,
# точно до сэмпла. Остальные форматы (MP3/OGG, если кэш PCM недоступен) идут через mixer.music как раньше.

SONG_CHANNEL = 0
_pcm = {"path": None, "raw": None, "frame": 0, "freq": 0}
_snd = None
_exact = False                      # сейчас играет песня из памяти (а не поток)


def _reserve_channel():
    try:
        if pygame.mixer.get_num_channels() > SONG_CHANNEL:
            pygame.mixer.set_reserved(SONG_CHANNEL + 1)       # эффекты не займут канал песни
    except Exception:
        pass


def _load_pcm(path):
    """Читает PCM-WAV в память, если формат совпадает с микшером. Иначе False (играем потоком)."""
    if _pcm["path"] == path and _pcm["raw"] is not None:
        return True
    init = pygame.mixer.get_init()
    if not init or not str(path).lower().endswith(".wav"):
        return False
    freq, fmt, chans = init
    try:
        with wave.open(path, "rb") as w:
            if fmt != -16 or w.getsampwidth() != 2 or w.getframerate() != freq or w.getnchannels() != chans:
                return False
            raw = w.readframes(w.getnframes())
    except Exception:
        return False
    _pcm.update(path=path, raw=raw, frame=2 * chans, freq=freq)
    return True


def _music_volume():
    return settings.get("music_volume") / 100.0


def preload_song(path):
    """Загрузка музыки заранее (до отсчёта), чтобы старт песни не тормозил."""
    global _music_path
    if _load_pcm(path):
        _music_path = path
        return
    try:
        pygame.mixer.music.load(path)
        _music_path = path
    except Exception:
        _music_path = None


def play_song(path, start_ms=0.0):
    global _music_path, _snd, _exact
    stop_song()
    start_ms = max(0.0, float(start_ms))
    try:
        if _load_pcm(path):
            _reserve_channel()
            raw, fb = _pcm["raw"], _pcm["frame"]
            offset = int(round(start_ms / 1000.0 * _pcm["freq"])) * fb
            if offset >= len(raw):
                _music_path, _exact = path, True
                return                                        # позиция за концом песни — тишина
            _snd = pygame.mixer.Sound(buffer=memoryview(raw)[offset:])
            _snd.set_volume(_music_volume())
            pygame.mixer.Channel(SONG_CHANNEL).play(_snd)
            _music_path, _exact = path, True
            return
        if _music_path != path or _exact:
            pygame.mixer.music.load(path)
            _music_path = path
        _exact = False
        pygame.mixer.music.set_volume(_music_volume())
        pygame.mixer.music.play(start=start_ms / 1000.0)
    except Exception:
        pass


def set_music_volume():
    try:
        pygame.mixer.music.set_volume(_music_volume())
        if _snd is not None:
            _snd.set_volume(_music_volume())
    except Exception:
        pass


def pause_song():
    try:
        pygame.mixer.music.pause()
        if _exact:
            pygame.mixer.Channel(SONG_CHANNEL).pause()
    except Exception:
        pass


def resume_song():
    try:
        pygame.mixer.music.unpause()
        if _exact:
            pygame.mixer.Channel(SONG_CHANNEL).unpause()
    except Exception:
        pass


def stop_song():
    try:
        pygame.mixer.music.stop()
        if _exact and pygame.mixer.get_init():
            pygame.mixer.Channel(SONG_CHANNEL).stop()
    except Exception:
        pass


class SongClock:
    """Часы песни в мс чарта. speed < 1 — замедленная практика: реальное время идёт медленнее чарта.

    latency_ms — задержка звука в РЕАЛЬНЫХ миллисекундах; в мс чарта она масштабируется скоростью,
    поэтому синхронизация звука, нот и окон оценок не расходится при замедлении.
    time_fn нужен тестам (подмена часов)."""

    def __init__(self, speed=1.0, time_fn=time.perf_counter, latency_fn=None):
        self.speed = float(speed)
        self._time = time_fn
        self._latency = latency_fn or (lambda: settings.get("latency_ms"))
        self._t0 = None
        self._frozen = None

    def start(self, at_ms=0.0):
        """at_ms — позиция в мс ЧАРТА."""
        self._t0 = self._time() - (at_ms / self.speed + self._latency()) / 1000.0
        self._frozen = None

    def now(self):
        if self._t0 is None:
            return 0.0
        if self._frozen is not None:
            return self._frozen
        return ((self._time() - self._t0) * 1000.0 - self._latency()) * self.speed

    def pause(self):
        if self._frozen is None:
            self._frozen = self.now()

    def resume(self):
        if self._frozen is not None:
            self.start(self._frozen)

    def seek(self, ms):
        paused = self._frozen is not None
        self.start(ms)
        if paused:
            self._frozen = ms
