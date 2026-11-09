"""Поле «Текст карточки» на экране событий: открывается для ввода, принимает новый текст и не роняет отрисовку."""
import pygame

import events as EV


def _screen(text):
    import events_screen as ES
    import chart as chartmod
    ch = chartmod.Chart("t.ogg")
    ch.events.append(EV.normalize({"type": "card", "t": 1000, "dur": 800, "text": text}))
    return ES.EventsScreen(pygame.time.Clock(), ch, 1000, 20000), ch


def _index(scr, key):
    return [f[0] for f in scr._fields()].index(key)


def test_card_text_field_opens_for_editing():
    scr, _ = _screen("Текст карточки")
    scr._start_edit(_index(scr, "text"))
    assert scr.edit_buf == "Текст карточки"


def test_card_text_edit_applies_and_screen_still_draws():
    scr, ch = _screen("Старый")
    scr._start_edit(_index(scr, "text"))
    scr.edit_buf = "Новый текст"
    scr._finish_edit(True)
    assert ch.events[0]["text"] == "Новый текст"
    scr._draw((5, 5))
