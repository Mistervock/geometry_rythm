"""Английские переводы для строк, добавленных при расширении проекта (редактор, практика, призрак, история…).

Подмешиваются в i18n.EN при импорте i18n (см. конец i18n.py). Ключ — русский текст, значение — английский."""

EXT = {
    # события: на весь экран
    "Растянуть на весь экран": "Stretch to full screen",
    "На весь экран: ДА": "Full screen: ON", "На весь экран: НЕТ": "Full screen: OFF",
    "ДА — картинка или ролик растягиваются на весь экран (пропорции не сохраняются, размер и смещение не используются)":
        "ON — the picture or video is stretched over the whole screen (proportions are not kept; size and offset are not used)",
    # достижения
    "ЗА ЧАРТЫ": "CHART ACHIEVEMENTS", "ВСТРОЕННЫЕ": "BUILT-IN",
    # редактор: сообщения
    "SPACE играть · ←→ курсор · PgUp/PgDn ±5 с · -/= скорость · G привязка · H деление · Del удалить · F1 помощь":
        "SPACE play · ←→ cursor · PgUp/PgDn ±5 s · -/= speed · G snap · H division · Del delete · F1 help",
    "ПРОВЕРКА ЧАРТА": "CHART CHECK", "Здесь уже есть нота": "There is already a note here",
    "Нет выделенных нот": "No notes selected", "Все ноты уже на сетке": "All notes are already on the grid",
    "Буфер пуст": "Clipboard is empty", "Нечего вставлять: ноты уже есть": "Nothing to paste: notes already exist",
    "Тап-темп: нажимайте в такт": "Tap tempo: tap to the beat", "Нечего повторять": "Nothing to redo",
    "При загрузке часть записей была пропущена; исходный файл будет сохранён в data/backups/charts при первом сохранении.":
        "Some records were skipped on load; the original file will be kept in data/backups/charts on first save.",
    "Проблем не найдено.": "No problems found.", "BPM-СЕТКА": "BPM GRID", "Привязано нот": "Notes snapped",
    "Скопировано нот": "Notes copied", "Вставлено нот": "Notes pasted", "Привязка к сетке": "Grid snap",
    "Нужно число": "A number is required", "Выделено нот": "Notes selected",
    "авто: сохранение…": "auto: saving…", "СОХРАНЕНО": "SAVED", "НЕ СОХРАНЕНО": "UNSAVED",
    "СОХРАНЕНИЕ…": "SAVING…", "ОШИБКА СОХРАНЕНИЯ": "SAVE ERROR",
    "Восстановлено из автосохранения": "Restored from autosave", "Повтор": "Redo",
    "ИМПОРТ НЕ УДАЛСЯ": "IMPORT FAILED", "выделено": "selected",
    "Часть записей чарта пропущена при загрузке": "Some chart records were skipped on load",
    "событий": "events", "Исходный файл сохранится в резервной копии": "The original file will be kept as a backup",
    "Смещение ритма, мс": "Rhythm offset, ms", "чарт создан в более новой версии игры": "the chart was made by a newer game version",
    "чарт не проходит проверку": "the chart failed validation", "Нельзя поставить ноту точно поверх другой": "Cannot place a note exactly on top of another",
    "Чарт загружен с предупреждениями": "Chart loaded with warnings", "меню → ПРОВЕРКА ЧАРТА": "menu → CHART CHECK",
    "Делений на долю (1–192)": "Divisions per beat (1–192)", "авто: ошибка": "auto: error", "авто": "auto",
    "Начало ритма": "Rhythm start", "Экспорт не удался": "Export failed",
    "Есть несохранённые изменения. Выйти без сохранения? Автосохранение будет удалено.":
        "There are unsaved changes. Quit without saving? The autosave will be deleted.",
    "ВЫЙТИ": "QUIT", "ОСТАТЬСЯ": "STAY", "Деление": "Division", "Удалено нот": "Notes deleted",
    "ВСЕ": "ALL", "ДОЛИ": "BEATS", "ТАКТЫ": "BARS", "СКРЫТЬ": "HIDE",
    "ПРИВЯЗКА": "SNAP", "СМЕЩЕНИЕ": "OFFSET", "ДЕЛЕНИЕ": "DIVISION", "ДОЛЕЙ В ТАКТЕ": "BEATS PER BAR",
    "ЛИНИИ": "LINES", "НАЧАЛО ← КУРСОР": "ORIGIN ← CURSOR",
    # подсказка F1
    "ЛКМ · Shift+рамка": "LMB · Shift+box", "нота / выделить рамкой": "note / box select",
    "ЛКМ-тяга": "LMB drag", "переместить ноту, хвост — длительность": "move a note; tail = length",
    "курсор (шаг сетки)": "cursor (grid step)", "масштаб (Ctrl+колесо)": "zoom (Ctrl+wheel)",
    "сдвиг всех нот ±10 мс": "shift all notes ±10 ms",
    "привязка к сетке вкл / выкл (Alt — разово)": "grid snap on / off (Alt — once)",
    "деление сетки": "grid division", "тап-темп": "tap tempo", "двигать выделение": "nudge selection",
    "выделение по дорожкам": "move selection between lanes", "привязать выделение к сетке": "snap selection to grid",
    "удалить ноту / выделение": "delete note / selection", "отмена / повтор": "undo / redo",
    "выделить все / копировать / вставить": "select all / copy / paste", "подсказка · FPS": "help · FPS",
    "играть / пауза": "play / pause", "поставить ноту на дорожку": "place a note on a lane",
    # команды истории
    "Добавить ноты": "Add notes", "Удалить ноты": "Delete notes", "Изменить ноты": "Edit notes",
    "Заменить все ноты": "Replace all notes", "Изменить события": "Edit events",
    "Изменить свойства чарта": "Edit chart properties", "Пакетная правка": "Batch edit",
    "Сдвиг выделенных нот": "Shift selected notes", "Смена дорожки": "Change lane", "Чарт": "Chart",
    "Длительность удержания": "Hold length", "Смещение сетки": "Grid offset", "Перемещение нот": "Move notes",
    "Деление сетки": "Grid division", "Размер такта": "Bar size", "Свойства чарта": "Chart properties",
    "Сдвиг всех нот": "Shift all notes", "Название чарта": "Chart name", "Привязка к сетке": "Grid snap",
    # клавиши
    "Избранное: песня / чарт": "Favorite: song / chart", "Только избранное": "Favorites only", "Практика": "Practice",
    "Привязка к сетке вкл / выкл": "Grid snap on / off", "Повтор (с Ctrl)": "Redo (with Ctrl)",
    "Выделить все ноты (с Ctrl)": "Select all notes (with Ctrl)", "Копировать выделение (с Ctrl)": "Copy selection (with Ctrl)",
    "Вставить в курсор (с Ctrl)": "Paste at cursor (with Ctrl)", "Снять выделение": "Deselect",
    "Сдвинуть выделенное раньше": "Nudge selection earlier", "Сдвинуть выделенное позже": "Nudge selection later",
    "Выделенное на дорожку левее": "Selection one lane left", "Выделенное на дорожку правее": "Selection one lane right",
    "Привязать выделенное к сетке": "Snap selection to grid", "Следующее деление сетки": "Next grid division",
    "Тап-темп (BPM)": "Tap tempo (BPM)",
    # игра и практика
    "P / ESC — продолжить, R — заново, M — в меню": "P / ESC — resume, R — restart, M — menu",
    "ПОВТОР": "REPEAT", "ESC — пауза · R — заново": "ESC — pause · R — restart", "ЗАНОВО (R)": "RESTART (R)",
    "УЧАСТОК И СКОРОСТЬ": "SECTION & SPEED", "ЗАВЕРШИТЬ": "FINISH", "ПРАКТИКА": "PRACTICE",
    "СТАРТ": "START",
    "A / B / Tab — маркер · ←→ ±0.25 с (Shift ±1 с, Ctrl ±10 мс) · мышь — тянуть · 1–4 скорость · ENTER старт":
        "A / B / Tab — marker · ←→ ±0.25 s (Shift ±1 s, Ctrl ±10 ms) · mouse — drag · 1–4 speed · ENTER start",
    "Результаты практики не попадают в рекорды и достижения": "Practice results do not count for records or achievements",
    "длина": "length", "ЦИКЛ": "LOOP", "ПОТЕРЯ HP": "HP LOSS",
    # результаты
    "ИЗМЕНИТЬ УЧАСТОК": "CHANGE SECTION", "SPACE — ещё раз, S — участок, M — в меню, TAB — подробно":
        "SPACE — again, S — section, M — menu, TAB — details",
    "SPACE — ещё раз, M — в меню, TAB — подробно": "SPACE — again, M — menu, TAB — details",
    "ОБЗОР": "OVERVIEW", "ПОДРОБНО": "DETAILS", "попыток": "attempts", "★ НОВЫЙ ЛИЧНЫЙ РЕКОРД": "★ NEW PERSONAL BEST",
    "лучшая точность": "best accuracy", "СТАТИСТИКА": "STATISTICS",
    "ОТКЛОНЕНИЕ ПО ВРЕМЕНИ (мс)": "TIMING ERROR OVER TIME (ms)", "РАСПРЕДЕЛЕНИЕ ОТКЛОНЕНИЙ": "ERROR DISTRIBUTION",
    "поздно": "late", "рано": "early", "ТОЧНОСТЬ И ОШИБКИ ПО ПЕСНЕ": "ACCURACY AND ERRORS OVER THE SONG",
    "золото — точность, красное — ошибки": "gold — accuracy, red — errors",
    "ТЕКУЩИЙ ПРОХОД И РЕКОРД": "THIS RUN VS PERSONAL BEST", "РАНО / ПОЗДНО": "EARLY / LATE",
    "сейчас": "now", "рекорда ещё нет": "no record yet", "Нот всего": "Total notes",
    "Удержания ок / сорвано": "Holds ok / broken", "Фулл-комбо": "Full combo", "Макс. комбо": "Max combo",
    "Очки": "Score", "Точность": "Accuracy", "Ранг": "Rank", "Среднее отклонение": "Mean deviation",
    "Среднее |откл.|": "Mean |dev.|", "Разброс (σ)": "Spread (σ)", "Рано / поздно": "Early / late",
    "ЛУЧШЕ РЕКОРДА": "BETTER THAN RECORD", "РЕКОРД НЕ ПОБИТ": "RECORD NOT BEATEN", "нет попаданий": "no hits",
    "рекорд": "record", "очки": "score", "точность": "accuracy", "промахи": "misses",
    "Личного рекорда для сравнения ещё нет": "No personal best to compare with yet",
    "ДА": "YES", "нет": "no", "с": "s", "ДОСТИЖЕНИЕ ПОЛУЧЕНО": "ACHIEVEMENT UNLOCKED",
    "Призрак устарел: чарт изменён после рекорда — пройдите чарт заново":
        "Ghost is outdated: the chart changed after the record — play the chart again",
    "Файл призрака повреждён и убран в карантин": "The ghost file is damaged and was moved to quarantine",
    "Призрак создан более новой версией игры": "The ghost was made by a newer game version",
    # подготовка
    "ПОДГОТОВКА": "PREPARING", "ESC / ENTER — назад": "ESC / ENTER — back", "В чарте нет нот": "The chart has no notes",
    "Чарт не проходит проверку": "The chart failed validation", "Песня не найдена": "Song not found",
    "Не удалось прочитать песню": "Could not read the song",
    "Звук недоступен: игра пойдёт без музыки": "Audio unavailable: the game will run without music",
    "Не удалось загрузить песню": "Could not load the song", "Предупреждения": "Warnings",
    "Откройте чарт в редакторе и добавьте ноты.": "Open the chart in the editor and add notes.",
    "Замедление недоступно": "Slowdown unavailable", "Установите numpy (pip install numpy).": "Install numpy (pip install numpy).",
    "Нет файла события": "Event file missing", "событие пропущено": "event skipped",
    "Ролики недоступны: установите opencv": "Videos unavailable: install opencv",
    "Проверка чарта": "Chart check", "Проверка песни": "Song check", "Построение структур": "Building structures",
    "Картинки и ролики событий": "Event images and videos", "Подготовка звука": "Preparing audio", "мс": "ms",
    # история, избранное
    "не завершён": "not finished", "ОЧИСТИТЬ": "CLEAR", "ИСТОРИЯ": "HISTORY", "Запись удалена": "Entry deleted",
    "История пуста — сыграйте первый чарт": "History is empty — play your first chart",
    "Песня или чарт больше не найдены": "Song or chart no longer found",
    "Нажмите ещё раз, чтобы очистить всю историю": "Press again to clear the whole history",
    "История очищена": "History cleared", "ИГРА": "PLAY", "нет файла": "no file",
    "★ ИЗБР.": "★ FAV.", "Избранное": "Favorites", "Чарт добавлен в избранное": "Chart added to favorites",
    "Чарт убран из избранного": "Chart removed from favorites", "Песня добавлена в избранное": "Song added to favorites",
    "Песня убрана из избранного": "Song removed from favorites", "Показано только избранное": "Showing favorites only",
    "Показаны все песни": "Showing all songs",
    # восстановление
    "Редактор был закрыт без сохранения.": "The editor was closed without saving.", "ВОССТАНОВИТЬ": "RESTORE",
    "УДАЛИТЬ КОПИЮ": "DELETE COPY", "ПОТОМ": "LATER", "ВОССТАНОВЛЕНИЕ": "RECOVERY",
    "Найдено повреждённое автосохранение — восстановить его нельзя.": "A damaged autosave was found — it cannot be restored.",
    "Файл не удалён автоматически.": "The file was not deleted automatically.",
    "ОТКРЫТЬ ОБЫЧНЫЙ ЧАРТ": "OPEN NORMAL CHART", "ОШИБКА": "ERROR",
    "Автосохранение новее файла чарта.": "The autosave is newer than the chart file.",
    "Файл чарта изменился после начала редактирования: версия откроется как НОВАЯ КОПИЯ, оригинал не будет затёрт.":
        "The chart file changed after editing began: the version opens as a NEW COPY, the original will not be overwritten.",
    "Исходного файла чарта больше нет: версия откроется как новый чарт.":
        "The original chart file is gone: the version opens as a new chart.",
    "Чарт ещё ни разу не сохранялся: версия откроется как новый чарт.":
        "The chart was never saved: the version opens as a new chart.",
    "Автосохранение старого формата: версия откроется как новый чарт.":
        "Old-format autosave: the version opens as a new chart.",
    "Удалить автосохранение «%s»? Это нельзя отменить.": "Delete the autosave “%s”? This cannot be undone.",
    "УДАЛИТЬ": "DELETE", "ОТМЕНА": "CANCEL",
    "Песня чарта не найдена в songs/:": "The chart's song was not found in songs/:",
    "Автосохранение сохранено — добавьте песню и повторите.": "The autosave is kept — add the song and try again.",
    "Автосохранение не удалось прочитать:": "Could not read the autosave:", "Исходный чарт не открывается:": "The original chart cannot be opened:",
    # настройки
    "Призрак лучшего прохода": "Best-run ghost", "Автосохранение редактора": "Editor autosave",
    "Вкл": "On", "Выкл": "Off", "ВКЛ": "ON", "ВЫКЛ": "OFF",
}
