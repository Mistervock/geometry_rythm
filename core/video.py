#-- Импорт
import threading

import pygame

try:
    import cv2
except ImportError:
    cv2 = None

AVAILABLE = cv2 is not None
MAX_OPEN = 6

_players = {}


#-- Декодер ролика

class _Player:
    def __init__(self, path):
        self.cap = cv2.VideoCapture(path)
        self.ok = self.cap.isOpened()
        self.fps = 30.0
        self.size = (0, 0)
        if self.ok:
            fps = self.cap.get(cv2.CAP_PROP_FPS) or 0.0
            if 1.0 <= fps <= 240.0:
                self.fps = fps
            self.size = (int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                         int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)))
            if self.size[0] <= 0 or self.size[1] <= 0:
                self.ok = False
        self.cond = threading.Condition()
        self.wanted = None
        self.key = None
        self.index = -1
        self.last = None
        self.emitted = None
        self.raw = None
        self.stop = False
        self.scaled_tag = None
        self.scaled = None
        self.thread = None
        if self.ok:
            self.thread = threading.Thread(target=self._run, daemon=True)
            self.thread.start()
        else:
            self.cap.release()

    def _busy(self):
        if self.wanted is None or self.key is None:
            return False
        if self.index != self.wanted:
            return True
        return self.last is not None and self.emitted != (self.index, self.key)

    def _run(self):
        cap = self.cap
        while True:
            with self.cond:
                while not self.stop and not self._busy():
                    self.cond.wait(0.5)
                if self.stop:
                    break
                target = self.wanted
                key = self.key
            if self.index != target:
                if target < self.index or target - self.index > int(self.fps * 2):
                    cap.set(cv2.CAP_PROP_POS_FRAMES, target)
                    self.index = target - 1
                if self.index < target - 1:
                    if cap.grab():
                        self.index += 1
                    else:
                        self.index = target
                    continue
                ok, frame = cap.read()
                if ok:
                    self.last = frame
                self.index = target
            if self.last is None:
                continue
            src = self.last
            size, bright = key[:2], key[2]
            if size != self.size:
                interp = cv2.INTER_AREA if size[0] < self.size[0] else cv2.INTER_LINEAR
                src = cv2.resize(src, size, interpolation=interp)
            if bright < 1.0:
                src = cv2.convertScaleAbs(src, alpha=bright, beta=0)
            rgb = cv2.cvtColor(src, cv2.COLOR_BGR2RGB).tobytes()
            with self.cond:
                self.raw = (self.index, key, rgb)
                self.emitted = (self.index, key)
        cap.release()

    def frame(self, ms, w, h, bright=1.0):
        if not self.ok:
            return None
        target = max(0, int(ms * self.fps / 1000.0))
        key = (w, h, round(bright, 3))
        with self.cond:
            if target != self.wanted or key != self.key:
                self.wanted = target
                self.key = key
                self.cond.notify()
            item = self.raw
        if item is None:
            return self.scaled
        idx, ikey, rgb = item
        if ikey != key:
            return self.scaled
        if self.scaled_tag != (idx, key):
            self.scaled = pygame.image.frombuffer(rgb, key[:2], "RGB")
            self.scaled_tag = (idx, key)
        return self.scaled

    def close(self):
        with self.cond:
            self.stop = True
            self.cond.notify_all()
        if self.thread is not None:
            self.thread.join(timeout=2.0)


#-- Общий доступ

def _player(path, key):
    p = _players.get(key)
    if p is None:
        if len(_players) >= MAX_OPEN:
            oldest = next(iter(_players))
            _players.pop(oldest).close()
        p = _Player(path)
        _players[key] = p
    return p


def frame(path, key, ms, w, h, bright=1.0):
    if not AVAILABLE:
        return None
    return _player(path, key).frame(ms, w, h, bright)


def size(path):
    if not AVAILABLE:
        return None
    p = _player(path, ("size", path))
    if not p.ok:
        return None
    return p.size


def close_all():
    while _players:
        _players.popitem()[1].close()
