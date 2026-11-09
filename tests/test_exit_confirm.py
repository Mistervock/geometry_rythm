"""Esc в главном меню спрашивает «Покинуть игру?»: выход только после выбора ПОКИНУТЬ."""
import pygame

import dialogs
import menu


def _post(*keys):
    for k in keys:
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=k, mod=0, unicode="", scancode=0))


def test_escape_in_menu_asks_and_quits_when_confirmed(monkeypatch):
    asked = []
    monkeypatch.setattr(dialogs, "leave_game", lambda clock: asked.append(True) or True)
    _post(pygame.K_ESCAPE)
    assert menu.main_menu(pygame.time.Clock()) == "quit"
    assert asked == [True]


def test_escape_in_menu_keeps_the_game_when_cancelled(monkeypatch):
    asked = []
    monkeypatch.setattr(dialogs, "leave_game", lambda clock: asked.append(True) or False)
    _post(pygame.K_ESCAPE, pygame.K_RETURN)
    assert menu.main_menu(pygame.time.Clock()) == "songs"
    assert asked == [True]


def test_leave_dialog_defaults_to_stay(monkeypatch):
    _post(pygame.K_RETURN)
    assert dialogs.leave_game(pygame.time.Clock()) is False


def test_leave_dialog_leave_button_needs_selecting(monkeypatch):
    _post(pygame.K_LEFT, pygame.K_RETURN)
    assert dialogs.leave_game(pygame.time.Clock()) is True


def test_leave_dialog_escape_stays(monkeypatch):
    _post(pygame.K_ESCAPE)
    assert dialogs.leave_game(pygame.time.Clock()) is False
