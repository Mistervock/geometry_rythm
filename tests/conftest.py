"""Общая настройка тестов: headless-pygame и изолированная папка данных."""
import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORE = os.path.join(ROOT, "core")
if CORE not in sys.path:
    sys.path.insert(0, CORE)

import pytest


@pytest.fixture(scope="session", autouse=True)
def _pygame_session():
    import pygame
    pygame.mixer.pre_init(44100, -16, 2, 512)
    pygame.init()
    import display
    display.apply()
    import cache
    cache.warm()
    yield
    pygame.quit()


@pytest.fixture
def data_root(tmp_path, monkeypatch):
    """Подменяет каталоги данных на временные, чтобы тесты не трогали настоящие файлы игры."""
    import songs
    import autosave
    import records
    import achievements
    d = tmp_path / "data"
    (d / "charts").mkdir(parents=True)
    monkeypatch.setattr(songs, "CHART_DIR", str(d / "charts"))
    monkeypatch.setattr(songs, "BACKUP_DIR", str(d / "backups" / "charts"))
    monkeypatch.setattr(songs, "WINS_PATH", str(d / "wins.json"))
    monkeypatch.setattr(songs, "RANKS_PATH", str(d / "ranks.json"))
    monkeypatch.setattr(songs, "EXPORT_DIR", str(tmp_path / "exports"))
    monkeypatch.setattr(songs, "META_DIR", str(d / "songmeta"))
    monkeypatch.setattr(songs, "INFO_DIR", str(d / "songinfo"))
    monkeypatch.setattr(records, "PATH", str(d / "records.json"))
    monkeypatch.setattr(achievements, "UNLOCKED_PATH", str(d / "achievements_unlocked.json"))
    import ghost
    import library
    import practice
    import progress
    import stretch
    monkeypatch.setattr(progress, "PATH", str(d / "progress.json"))
    monkeypatch.setattr(library, "PATH", str(d / "library.json"))
    monkeypatch.setattr(ghost, "DIR", str(d / "ghosts"))
    monkeypatch.setattr(practice, "PATH", str(d / "practice.json"))
    monkeypatch.setattr(stretch, "DIR", str(d / "speed"))
    monkeypatch.setattr(autosave, "default_dir", lambda: str(d / "autosave"))
    library.reset_for_tests()
    songs.forget_cached()
    songs._json_cache.clear()
    return d


@pytest.fixture(autouse=True)
def _isolate_settings(tmp_path, monkeypatch):
    """Тесты не читают и не пишут настоящий data/settings.json."""
    import settings
    monkeypatch.setattr(settings, "PATH", str(tmp_path / "_settings.json"))
    monkeypatch.setattr(settings, "_data", None)
    yield
    settings._data = None
