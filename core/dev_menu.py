#-- Режим разработчика (клавиша 7 в списке песен): песни, чарты, цвета авторов
import dialogs
import events as EV
import songs
from i18n import t

PAGE = 7

AUTHOR_PRESETS = (
    ("Фиолетовый", (60, 20, 90)),
    ("Синий", (20, 40, 100)),
    ("Бирюзовый", (15, 80, 85)),
    ("Зелёный", (20, 80, 40)),
    ("Красный", (100, 25, 30)),
    ("Оранжевый", (110, 60, 15)),
    ("Жёлтый", (100, 90, 20)),
    ("Розовый", (100, 30, 80)),
)


def _pick(clock, title, items):
    """Выбор из списка (значение, подпись) страницами по PAGE. Возвращает значение или None."""
    page = 0
    pages = max(1, (len(items) + PAGE - 1) // PAGE)
    while True:
        chunk = items[page * PAGE:(page + 1) * PAGE]
        labels = [label for _, label in chunk]
        actions = [("item", value) for value, _ in chunk]
        if page > 0:
            labels.append(t("← Назад"))
            actions.append(("prev", None))
        if page < pages - 1:
            labels.append(t("Дальше →"))
            actions.append(("next", None))
        labels.append(t("Отмена"))
        actions.append(("cancel", None))
        head = title if pages == 1 else f"{title}  ({page + 1}/{pages})"
        idx = dialogs.choose(clock, head, labels)
        if idx is None:
            return None
        kind, value = actions[idx]
        if kind == "item":
            return value
        if kind == "prev":
            page -= 1
        elif kind == "next":
            page += 1
        else:
            return None


def run(clock):
    while True:
        choice = dialogs.choose(clock, t("РЕЖИМ РАЗРАБОТЧИКА"),
                                [t("Изменить музыку"), t("Изменить чарт"), t("Цвета авторов"), t("Закрыть")])
        if choice is None or choice == 3:
            return
        if choice == 0:
            _edit_song(clock)
        elif choice == 1:
            _edit_chart(clock)
        else:
            _author_colors(clock)


def _edit_song(clock):
    names = songs.list_songs()
    if not names:
        dialogs.choose(clock, t("Песен пока нет"), [t("Назад")])
        return
    song = _pick(clock, t("Какую музыку изменить"),
                 [(n, songs.display_title(n)) for n in names])
    while song is not None:
        m = songs.meta(song)
        field = dialogs.choose(clock, songs.display_title(song), [
            f"{t('Название')}: {songs.display_title(song)}",
            f"{t('Автор')}: {m.get('artist') or '—'}",
            f"{t('Картинка (images/)')}: {m.get('image') or '—'}",
            t("Назад"),
        ])
        if field is None or field == 3:
            return
        if field == 0:
            value = dialogs.ask_text(clock, t("Название песни"), songs.display_title(song), 60)
            if value is not None:
                songs.update_meta(song, title=value)
        elif field == 1:
            value = dialogs.ask_text(clock, t("Автор песни"), m.get("artist", ""), 60)
            if value is not None:
                songs.update_meta(song, artist=value)
        elif field == 2:
            items = [("", t("нет"))] + [(n, n) for n in EV.list_media("image")]
            value = _pick(clock, t("Картинка песни"), items)
            if value is not None:
                songs.update_meta(song, image=value)


def _edit_chart(clock):
    charts = songs.all_charts()
    if not charts:
        dialogs.choose(clock, t("Чартов пока нет"), [t("Назад")])
        return
    items = [(i, f"{ch.name} — {songs.display_title(ch.song)}") for i, ch in enumerate(charts)]
    idx = _pick(clock, t("Какой чарт изменить"), items)
    while idx is not None:
        ch = charts[idx]
        field = dialogs.choose(clock, ch.name, [
            f"{t('Название')}: {ch.name}",
            f"{t('Музыка чарта')}: {songs.display_title(ch.song)}",
            t("Назад"),
        ])
        if field is None or field == 2:
            return
        if field == 0:
            value = dialogs.ask_text(clock, t("Название чарта"), ch.name, 24)
            if value is not None:
                ch.name = value
                songs.save_chart(ch)
        elif field == 1:
            song = _pick(clock, t("Какую музыку использует чарт"),
                         [(n, songs.display_title(n)) for n in songs.list_songs()])
            if song is not None:
                ch.song = song
                songs.save_chart(ch)


def _author_colors(clock):
    while True:
        authors = songs.all_authors()
        items = [(a, a) for a in authors] + [("__new__", t("+ новый автор"))]
        author = _pick(clock, t("Цвет фона для автора"), items)
        if author is None:
            return
        if author == "__new__":
            author = dialogs.ask_text(clock, t("Имя автора"), "", 40)
            if not author:
                continue
        color = _pick(clock, f"{t('Цвет для')}: {author}",
                      [(rgb, t(name)) for name, rgb in AUTHOR_PRESETS] + [("reset", t("Сбросить цвет"))])
        if color is None:
            continue
        songs.set_author_color(author, None if color == "reset" else color)
