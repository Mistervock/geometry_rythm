"""Запуск игры и открытие редактора: проверка автосохранений и диалог восстановления.

Диалог показывает название чарта и время автосохранения и предлагает:
  ВОССТАНОВИТЬ          — открыть редактор с автосохранённой версией (исходный файл не меняется,
                          пока автор сам не нажмёт «Сохранить»);
  ОТКРЫТЬ ОБЫЧНЫЙ ЧАРТ  — открыть файл как есть; автосохранение остаётся, но больше не напоминает,
                          пока не появится более свежее;
  УДАЛИТЬ КОПИЮ         — удалить автосохранение (с подтверждением);
  ПОТОМ                 — ничего не делать, напомнить при следующем запуске.
Повреждённое автосохранение не удаляется само: его можно удалить вручную из этого диалога.
"""
import os

import autosave as AS
import chart as chartmod
import dialogs
import settings
import songs
import stretch
from i18n import t

ACTIONS = ("restore", "normal", "delete", "later")


def _status_text(rec):
    return {AS.NEWER: t("Автосохранение новее файла чарта."),
            AS.CONFLICT: t("Файл чарта изменился после начала редактирования: версия откроется как НОВАЯ КОПИЯ, оригинал не будет затёрт."),
            AS.ORPHAN: t("Исходного файла чарта больше нет: версия откроется как новый чарт."),
            AS.DRAFT: t("Чарт ещё ни разу не сохранялся: версия откроется как новый чарт."),
            AS.LEGACY: t("Автосохранение старого формата: версия откроется как новый чарт."),
            }.get(rec.status, "")


def ask(clock, rec):
    """Показывает диалог. Возвращает один из ACTIONS."""
    lang = settings.get("lang")
    if rec.status == AS.CORRUPT:
        lines = [t("Найдено повреждённое автосохранение — восстановить его нельзя."), rec.name,
                 rec.note or "", t("Файл не удалён автоматически.")]
        idx = dialogs.info_lines(clock, t("ВОССТАНОВЛЕНИЕ"), lines, accent=None,
                                 buttons=[t("УДАЛИТЬ КОПИЮ"), t("ПОТОМ")])
        return "delete" if idx == 0 else "later"
    lines = [t("Редактор был закрыт без сохранения."), "", rec.describe(lang), _status_text(rec)]
    buttons = [t("ВОССТАНОВИТЬ")]
    actions = ["restore"]
    if rec.source_path:
        buttons.append(t("ОТКРЫТЬ ОБЫЧНЫЙ ЧАРТ"))
        actions.append("normal")
    buttons += [t("УДАЛИТЬ КОПИЮ"), t("ПОТОМ")]
    actions += ["delete", "later"]
    idx = dialogs.info_lines(clock, t("ВОССТАНОВЛЕНИЕ"), lines, buttons=buttons)
    return actions[idx] if idx is not None else "later"


def _open_editor(clock, chart, rec=None):
    import editor
    return editor.Editor(clock, chart, recovery=rec).run()


def handle(clock, rec):
    """Выполняет выбор игрока. Не бросает исключений наружу: ошибки показываются сообщением."""
    action = ask(clock, rec)
    if action == "later":
        return "later"
    if action == "delete":
        if dialogs.confirm(clock, t("Удалить автосохранение «%s»? Это нельзя отменить.") % rec.name,
                           yes=t("УДАЛИТЬ"), no=t("ОТМЕНА")):
            AS.discard(rec)
            return "deleted"
        return "later"
    if action == "normal":
        chart, rep = songs.load_chart_file(rec.source_path)
        if chart is None:
            dialogs.info_lines(clock, t("ОШИБКА"), [t("Исходный чарт не открывается:")] + rep.lines(settings.get("lang")))
            return "later"
        if not os.path.isfile(songs.song_path(chart.song)):
            dialogs.info_lines(clock, t("ОШИБКА"), [t("Песня чарта не найдена в songs/:"), chart.song])
            return "later"
        AS.ignore(AS.default_dir(), rec)
        _open_editor(clock, chart)
        return "normal"
    # restore
    try:
        chart = AS.restore_chart(rec)
    except (chartmod.ChartFormatError, ValueError, TypeError) as e:
        dialogs.info_lines(clock, t("ОШИБКА"), [t("Автосохранение не удалось прочитать:"), str(e)])
        return "later"
    if not os.path.isfile(songs.song_path(chart.song)):
        dialogs.info_lines(clock, t("ОШИБКА"), [t("Песня чарта не найдена в songs/:"), chart.song,
                                                 t("Автосохранение сохранено — добавьте песню и повторите.")])
        return "later"
    _open_editor(clock, chart, rec)
    return "restored"


def run(clock):
    """При запуске игры: чистка старых автосохранений и диалог по каждому найденному."""
    try:
        AS.cleanup()
        stretch.prune()
        found = [r for r in AS.scan() if not r.ignored]
    except Exception as e:                       # noqa: BLE001 — сбой проверки не должен мешать запуску
        print(f"[autosave] scan: {e}")
        return
    for rec in found:
        handle(clock, rec)


def open_editor(clock, chart):
    """Открытие редактора из списка песен: если у чарта есть неигнорируемое автосохранение — спросить."""
    rec = None
    try:
        rec = AS.find_for(chart)
    except Exception as e:                       # noqa: BLE001
        print(f"[autosave] find_for: {e}")
    if rec is not None and not rec.ignored:
        res = handle(clock, rec)
        if res in ("restored", "normal"):
            return
        if res == "later":
            pass
    _open_editor(clock, chart)
