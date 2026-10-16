
#-- Импорт
import time

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


def play_song(path, start_ms=0.0):
    try:
        pygame.mixer.music.load(path)
        pygame.mixer.music.set_volume(settings.get("music_volume") / 100.0)
        pygame.mixer.music.play(start=max(0.0, start_ms / 1000.0))
    except Exception:
        pass


def set_music_volume():
    try:
        pygame.mixer.music.set_volume(settings.get("music_volume") / 100.0)
    except Exception:
        pass


def pause_song():
    try:
        pygame.mixer.music.pause()
    except Exception:
        pass


def resume_song():
    try:
        pygame.mixer.music.unpause()
    except Exception:
        pass


def stop_song():
    try:
        pygame.mixer.music.stop()
    except Exception:
        pass


class SongClock:

    def __init__(self):
        self._t0 = None
        self._frozen = None

    def start(self, at_ms=0.0):
        self._t0 = time.perf_counter() - (at_ms + settings.get("latency_ms")) / 1000.0
        self._frozen = None

    def now(self):
        if self._t0 is None:
            return 0.0
        if self._frozen is not None:
            return self._frozen
        return (time.perf_counter() - self._t0) * 1000.0 - settings.get("latency_ms")

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
