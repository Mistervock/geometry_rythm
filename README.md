# Geometry Rhythm

<p align="center">
  <strong>A geometric rhythm game inspired by Friday Night Funkin' and Geometry Catcher.</strong><br>
  <a href="#english">English</a> · <a href="#русский">Русский</a>
</p>

---

## English

**Geometry Rhythm** is an independent rhythm game built around four geometric lanes. Follow the beat, hit notes at the right moment, maintain your combo, and create your own charts for the music you like.

The project is inspired by the feel of **Friday Night Funkin'** and the geometric style of **Geometry Catcher**, while offering its own chart editor and timeline-based visual events. It is a fan-made project, not an official Friday Night Funkin' game and not affiliated with its creators.

### Features

- **Four lanes, four shapes.** Each lane has its own colour and geometric shape. The default controls are **D**, **F**, **J**, and **K**.
- **Tap notes and hold notes.** Press a key at the hit line for a regular note; keep it pressed for the full duration of a hold.
- **Timing judgements and scoring.** Get **PERFECT**, **GREAT**, or **GOOD** hits, build a combo, and track your accuracy, score, health, and results.
- **Song and chart selection.** Keep supported audio files in **songs/** and create separate charts for each track.
- **Built-in chart editor.** Place, remove, record, move, and resize notes on a timeline. Use snapping, undo, and playback to refine the chart.
- **Audio auto-charting.** Generate a first-draft chart from a song's frequency bands. The result is a starting point for editing, not a guaranteed finished chart.
- **Timeline events.** Add glitches, flashes, background-colour changes, images, and video clips to a chart. Image and video events are marked as beta.
- **Customisable settings.** Adjust the lane keys, note speed, music and sound-effect volume, audio latency, and interface language.
- **Records and results.** Review your performance after a run and keep local records.

### Requirements

- Python
- Dependencies listed in **requirements.txt**
- **pygame** for the game and audio
- **numpy** for automatic chart generation
- **opencv-python** for video playback in chart events

The requirements file installs the project's listed Python dependencies. NumPy and OpenCV are used for their specific features; the core game does not rely on OpenCV for ordinary gameplay.

### Run from source

1. Install Python and Git.
2. Clone the repository and enter its folder.
3. Install the dependencies and launch the game:

~~~bash
git clone https://github.com/Mistervock/geometry_rythm.git
cd geometry_rythm
python -m pip install -r requirements.txt
python main.py
~~~

On Windows, if **python** is not recognised, try using **py** in its place.

### Gameplay

The game begins with a short countdown: **3 · 2 · 1 · RYTHM!**

| Action | Controls |
| --- | --- |
| Hit the four lanes | **D**, **F**, **J**, **K** by default |
| Play a regular note | Press the matching lane key as the note reaches the hit line |
| Play a hold note | Press at the start and keep holding until the end |
| Pause or resume | **P** or **Esc** |
| Return to the menu while paused | **M** |

You can change the lane keys and other gameplay settings in **Settings**. Missing notes reduces health and breaks your combo; releasing a hold too early causes a hold break.

### Songs and charts

Place your music files in the **songs/** folder. Supported extensions are **.ogg**, **.mp3**, and **.wav**. The repository includes **game.ogg** as a sample track.

To create or edit a chart:

1. Open **Songs** from the main menu.
2. Select a song and choose an existing chart, or create a new one.
3. Open the chart editor, make your changes, and save with **Ctrl + S**.

Charts are stored locally as JSON files in **data/charts/**. Settings, records, and song-analysis cache are kept in the **data/** directory. These files are generated or updated as you use the game.

### Chart editor

The editor lets you work directly against the song timeline.

| Action | Controls |
| --- | --- |
| Start or stop song playback | **Space** |
| Move by one grid step | **Left** / **Right** |
| Move by one second | **Shift + Left** / **Shift + Right** |
| Change timeline zoom | **Up** / **Down** |
| Change snap-grid interval | **G** |
| Toggle event-effect preview in the editor | **V** |
| Undo an edit | **Ctrl + Z** |
| Save the chart | **Ctrl + S** |
| Rename the chart | **F2** |
| Delete the nearest note | **Delete** or **Backspace** |
| Shift all notes by 10 ms | **[** / **]** |

You can also place notes with the mouse when the song is stopped, remove notes with the right mouse button, and adjust a hold's length with the mouse wheel over that note. While recording during playback, pressing lane keys creates notes; longer presses create holds. The editor includes an undo history of up to 80 steps.

### Automatic chart generation

Choose **Auto Chart** from the chart editor's menu. The analyser decodes audio through Pygame and examines four frequency ranges, mapping them to the four lanes. It detects strong changes in spectral energy, then applies spacing and density limits to avoid filling the chart with too many notes. Sustained sounds may be turned into hold notes.

- Requires **numpy**.
- The generated chart replaces the current note list with a draft. Save a copy first if you want to keep the existing notes.
- Listen to the song and review the generated notes manually. Music mixes vary, so the result may need timing, lane, and hold-length adjustments.

### Song events (beta for images and video)

Open a chart in the editor, press **Esc**, then choose **Events**. Events are placed on the song timeline and can be previewed without playing the entire chart.

Available event types:

- **Glitch** — distort the screen with horizontal bands.
- **Flash** — create a timed white flash.
- **Background** — change the background colour, with an optional transition back to the original colour.
- **Image (beta)** — display an image behind the lanes, with optional fade or movement.
- **Video (beta)** — display a video clip with configurable size, position, duration, fade, and movement.

Put image and video files in **images/**. Images support **.png**, **.jpg**, and **.jpeg**; videos support **.mp4**, **.webm**, **.mov**, **.avi**, **.mkv**, and **.m4v**. Video playback requires **opencv-python**.

Useful event-editor shortcuts:

| Action | Controls |
| --- | --- |
| Add glitch / flash / image / background / video | **1** / **2** / **3** / **4** / **5** |
| Move selection between events | **Up** / **Down** |
| Move between event fields | **Tab** |
| Change a selected value | **Left** / **Right** (**Shift** changes it faster) |
| Preview the selected event | **P** |
| Fit selected image or video to the screen | **F** |
| Set the selected event's time to the current cursor | **C** |
| Restore the original background colour | **R** |
| Copy event properties / paste / duplicate | **Ctrl + C** / **Ctrl + V** / **Ctrl + D** |
| Paste properties to all events of the same type | **Ctrl + Shift + V** |
| Delete the selected event or leave the editor | **Delete** / **Esc** |

### Chart file format

Charts use JSON. The current format version is **4**. Time values are measured in milliseconds; **lane** is numbered from **0** to **3**, and **d** is the hold duration (omitted for regular notes). The **events** field is optional.

~~~json
{
  "version": 4,
  "song": "game.ogg",
  "name": "Example chart",
  "notes": [
    { "t": 4000, "lane": 0 },
    { "t": 5000, "lane": 2, "d": 600 }
  ],
  "events": [
    { "type": "flash", "t": 4200, "attack": 40, "dur": 500 }
  ]
}
~~~

Each event type has its own fields. The example above shows a flash event; image, video, glitch, and background events use their own properties.

### Project layout

~~~text
geometry_rythm/
├── main.py                 # Application entry point
├── requirements.txt        # Python dependencies
├── GeometryRhythm.spec     # PyInstaller build specification
├── core/
│   ├── game.py             # Rhythm gameplay
│   ├── chart.py            # Notes, charts, JSON loading/saving
│   ├── editor.py           # Chart editor
│   ├── autochart.py        # Audio analysis and auto-charting
│   ├── events.py           # Timeline events and media helpers
│   ├── events_screen.py    # Event editor
│   ├── songs.py            # Song and chart management
│   ├── settings.py         # Settings persistence
│   └── ...                 # Menus, audio, results, translations, visuals
├── songs/                  # Audio tracks
├── images/                 # Images and video clips for events
└── data/                   # Charts, settings, records, and cache
~~~

### Windows executable

A prebuilt Windows **.exe** is **not published yet**. The repository includes a PyInstaller specification (**GeometryRhythm.spec**); until a ready-to-use build is released, run the project from source using the instructions above.

---

## Русский

**Geometry Rhythm** — ритм-игра с четырьмя геометрическими дорожками. Попадай в ноты в такт музыке, собирай комбо и создавай собственные чарты для любимых треков.

Проект вдохновлён **Friday Night Funkin'** и геометрическим стилем **Geometry Catcher**, но у него есть собственный редактор чартов и система визуальных событий на временной шкале. Это независимый фан-проект: он не является официальной игрой Friday Night Funkin' и не связан с её создателями.

### Возможности

- **Четыре дорожки и четыре формы.** У каждой дорожки свой цвет и геометрическая фигура. Стандартные клавиши — **D**, **F**, **J**, **K**.
- **Обычные ноты и удержания.** Обычную ноту нужно нажать в момент попадания на линию; удержание — зажать и держать до конца.
- **Оценки и очки.** За попадания начисляются **PERFECT**, **GREAT** или **GOOD**; игра отслеживает счёт, точность, комбо, здоровье и итоговый результат.
- **Выбор песен и чартов.** Добавляй музыку в папку **songs/** и создавай отдельные чарты для каждого трека.
- **Встроенный редактор чартов.** Ставь, удаляй, записывай и перемещай ноты на временной шкале. Используй сетку, отмену действий и прослушивание.
- **Авто-разметка музыки.** Создавай черновик чарта по частотным диапазонам песни. Это отправная точка для редактирования, а не гарантированно готовый чарт.
- **События на таймлайне.** Добавляй глюки, вспышки, смену цвета фона, изображения и видеоролики. События изображений и видео помечены как бета.
- **Настройки.** Меняй клавиши дорожек, скорость нот, громкость музыки и эффектов, аудиозадержку и язык интерфейса.
- **Результаты и рекорды.** Просматривай итоги прохождения и сохраняй локальные рекорды.

### Требования

- Python
- Зависимости из файла **requirements.txt**
- **pygame** — игра и звук
- **numpy** — автоматическая разметка чартов
- **opencv-python** — воспроизведение видео в событиях чарта

Файл зависимостей устанавливает перечисленные пакеты. NumPy и OpenCV нужны для своих отдельных функций; для обычного игрового процесса OpenCV не требуется.

### Запуск из исходников

1. Установи Python и Git.
2. Склонируй репозиторий и перейди в его папку.
3. Установи зависимости и запусти игру:

~~~bash
git clone https://github.com/Mistervock/geometry_rythm.git
cd geometry_rythm
python -m pip install -r requirements.txt
python main.py
~~~

В Windows, если команда **python** не распознаётся, попробуй заменить её на **py**.

### Игровой процесс

Перед началом идёт короткий отсчёт: **3 · 2 · 1 · RYTHM!**

| Действие | Управление |
| --- | --- |
| Попадать по четырём дорожкам | По умолчанию **D**, **F**, **J**, **K** |
| Обычная нота | Нажми клавишу дорожки, когда нота достигнет линии попадания |
| Удержание | Нажми в начале и держи до конца ноты |
| Пауза или продолжение | **P** или **Esc** |
| Вернуться в меню из паузы | **M** |

Клавиши дорожек и другие параметры можно изменить в разделе **«Настройки»**. Пропуски уменьшают здоровье и сбрасывают комбо; слишком раннее отпускание удержания приводит к срыву удержания.

### Песни и чарты

Помещай аудиофайлы в папку **songs/**. Поддерживаются расширения **.ogg**, **.mp3** и **.wav**. В репозитории уже есть пример песни — **game.ogg**.

Чтобы создать или отредактировать чарт:

1. Открой раздел **«ПЕСНИ»** в главном меню.
2. Выбери песню и существующий чарт либо создай новый.
3. Открой редактор, внеси изменения и сохрани их сочетанием **Ctrl + S**.

Чарты хранятся локально в формате JSON в папке **data/charts/**. Настройки, рекорды и кэш анализа песен находятся в каталоге **data/**. Эти файлы создаются или обновляются по мере использования игры.

### Редактор чартов

Редактор позволяет работать с нотами прямо на временной шкале песни.

| Действие | Управление |
| --- | --- |
| Начать или остановить проигрывание | **Space** |
| Переместить курсор на шаг сетки | **Left** / **Right** |
| Переместить курсор на секунду | **Shift + Left** / **Shift + Right** |
| Изменить масштаб таймлайна | **Up** / **Down** |
| Изменить шаг сетки | **G** |
| Включить или отключить предпросмотр событий в редакторе | **V** |
| Отменить действие | **Ctrl + Z** |
| Сохранить чарт | **Ctrl + S** |
| Переименовать чарт | **F2** |
| Удалить ближайшую ноту | **Delete** или **Backspace** |
| Сдвинуть все ноты на 10 мс | **[** / **]** |

Когда песня остановлена, ноты также можно ставить мышью; правая кнопка мыши удаляет ноту. Колёсико мыши над нотой изменяет длину удержания. Во время записи при проигрывании нажатия клавиш дорожек создают ноты, а более длинные нажатия — удержания. В редакторе есть история отмены до 80 действий.

### Автоматическая разметка

Выбери **«АВТО-РАЗМЕТКА»** в меню редактора. Анализатор декодирует аудио средствами Pygame, изучает четыре частотных диапазона и сопоставляет их четырём дорожкам. Он ищет выраженные изменения спектральной энергии и ограничивает плотность нот и интервалы между ними. Достаточно долгие звуки могут превращаться в удержания.

- Требуется **numpy**.
- Авто-разметка заменяет текущий список нот черновиком. Сохрани копию, если нужно оставить исходные ноты.
- После генерации прослушай песню и проверь ноты вручную: результат зависит от конкретного трека и может потребовать исправления таймингов, дорожек и длины удержаний.

### События песни (изображения и видео — бета)

Открой чарт в редакторе, нажми **Esc** и выбери **«СОБЫТИЯ»**. События размещаются на временной шкале и могут просматриваться отдельно от полного прохождения песни.

Доступны следующие типы событий:

- **Глюк** — искажение экрана горизонтальными полосами.
- **Вспышка** — белая вспышка с заданной длительностью.
- **Фон** — смена цвета фона с возможностью плавного перехода и возврата исходного цвета.
- **Картинка (бета)** — изображение под дорожками; можно настроить плавное появление или движение.
- **Видео (бета)** — видеоролик с настройкой размера, позиции, длительности, плавности и движения.

Помещай файлы изображений и видео в **images/**. Для изображений поддерживаются **.png**, **.jpg**, **.jpeg**; для видео — **.mp4**, **.webm**, **.mov**, **.avi**, **.mkv** и **.m4v**. Для показа видео нужен **opencv-python**.

Полезные клавиши редактора событий:

| Действие | Управление |
| --- | --- |
| Добавить глюк / вспышку / картинку / фон / видео | **1** / **2** / **3** / **4** / **5** |
| Выбрать предыдущее или следующее событие | **Up** / **Down** |
| Перейти между полями события | **Tab** |
| Изменить выбранное значение | **Left** / **Right** (**Shift** ускоряет изменение) |
| Просмотреть выбранное событие | **P** |
| Подогнать картинку или видео под экран | **F** |
| Привязать время события к курсору | **C** |
| Вернуть исходный цвет фона | **R** |
| Копировать параметры / вставить / дублировать | **Ctrl + C** / **Ctrl + V** / **Ctrl + D** |
| Вставить параметры во все события того же типа | **Ctrl + Shift + V** |
| Удалить событие или выйти из редактора | **Delete** / **Esc** |

### Формат файла чарта

Чарты хранятся в JSON. Текущая версия формата — **4**. Время задаётся в миллисекундах; **lane** — номер дорожки от **0** до **3**, **d** — длительность удержания (у обычной ноты поле отсутствует). Поле **events** необязательное.

~~~json
{
  "version": 4,
  "song": "game.ogg",
  "name": "Пример чарта",
  "notes": [
    { "t": 4000, "lane": 0 },
    { "t": 5000, "lane": 2, "d": 600 }
  ],
  "events": [
    { "type": "flash", "t": 4200, "attack": 40, "dur": 500 }
  ]
}
~~~

У каждого типа событий собственный набор полей. В примере показана вспышка; глюк, изображение, видео и фон используют свои параметры.

### Структура проекта

~~~text
geometry_rythm/
├── main.py                 # Точка входа в приложение
├── requirements.txt        # Зависимости Python
├── GeometryRhythm.spec     # Конфигурация сборки PyInstaller
├── core/
│   ├── game.py             # Игровой процесс
│   ├── chart.py            # Ноты, чарты, чтение и запись JSON
│   ├── editor.py           # Редактор чартов
│   ├── autochart.py        # Анализ аудио и авто-разметка
│   ├── events.py           # События и работа с медиа
│   ├── events_screen.py    # Редактор событий
│   ├── songs.py            # Управление песнями и чартами
│   ├── settings.py         # Сохранение настроек
│   └── ...                 # Меню, звук, результаты, переводы, визуальные эффекты
├── songs/                  # Музыкальные треки
├── images/                 # Картинки и видео для событий
└── data/                   # Чарты, настройки, рекорды и кэш
~~~

### Windows-версия (.exe)

Готовый исполняемый файл Windows **пока не опубликован**. В репозитории есть конфигурация PyInstaller (**GeometryRhythm.spec**); пока отдельная сборка не выпущена, запускай игру из исходников по инструкции выше.
