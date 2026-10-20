# Geometry Rhythm

<p align="center">
  <strong>A geometric rhythm game inspired by Friday Night Funkin' and Geometry Catcher.</strong><br>
  <a href="#english">English</a> · <a href="#русский">Русский</a> · <a href="https://github.com/Mistervock/geometry_rythm/releases">Releases / Скачать</a>
</p>

<p align="center">
  <strong>Version 0.2 · HD 1280 × 720 · Python + Pygame</strong>
</p>

---

## English

**Geometry Rhythm** is an independent rhythm game built around four geometric lanes. Hit notes in time with the music, build combos, manage your health, and make your own charts for the tracks you want to play.

The project is inspired by **Friday Night Funkin'** and the geometric style of **Geometry Catcher**, with its own chart editor, song metadata, event timeline, and custom achievement-card library. It is a fan-made project, not an official Friday Night Funkin' game and not affiliated with its creators.

### Features

- **HD layout:** 1280 × 720 game resolution with an optional scaled fullscreen mode.
- **Four geometric lanes:** each lane has its own shape and colour. Default keys: **D**, **F**, **J**, **K**.
- **Tap notes and hold notes:** hit notes at the right moment and keep holding for the full duration of long notes.
- **Scoring and health:** timing judgements, combo multipliers up to ×4, a 5 HP health bar, accuracy, grades, and a results screen.
- **Song browser:** browse tracks, listen to automatic previews, or start a random song. Preview playback can be disabled in Settings.
- **Custom song and chart metadata:** set a song title and artist, and give each chart an author and a 1–5 star difficulty rating.
- **Chart editor:** place notes by mouse, record them during playback, edit hold lengths, undo changes, snap to a grid, and change editor playback speed.
- **Automatic chart generation:** analyse a song's audio with NumPy to create an editable first draft.
- **Timeline events:** glitches, flashes, background changes, images, videos, heal pickups, text cards, and screen-colour inversion.
- **Event folders:** group related events, sort the list by time or type, and lock individual events or whole folders against accidental edits.
- **Achievement cards:** create, edit, view, and delete custom achievement entries with a name, description, and image.
- **Settings:** remappable lane keys, audio latency, note speed, volume controls, fullscreen mode, language, preview playback, and media dimming.

### Requirements

- Python
- **pygame** — game window, input, graphics, and audio
- **numpy** — automatic chart generation and alternate-speed audio in the editor
- **opencv-python** — video playback in chart events

The dependencies are listed in **requirements.txt**. NumPy and OpenCV are required for their respective extra features; video playback is not required for ordinary gameplay.

### Run from source

Install Python and Git, then clone the repository, install its dependencies, and start the game:

~~~bash
git clone https://github.com/Mistervock/geometry_rythm.git
cd geometry_rythm
python -m pip install -r requirements.txt
python main.py
~~~

On Windows, use **py** instead of **python** if that is the command available on your system.

### Gameplay

A run begins with the countdown **3 · 2 · 1 · RYTHM!**

| Action | Controls |
| --- | --- |
| Hit the four lanes | **D**, **F**, **J**, **K** by default |
| Hit a regular note | Press its lane key as it reaches the hit line |
| Hit a hold note | Press at the start and keep holding until the end |
| Pause or resume | **P** or **Esc** |
| Return to the menu from pause | **M** |

You can remap the lane keys in Settings. The default health is 5 HP. Missing a note reduces health and breaks the combo; every 10 combo steps increase the score multiplier, up to **×4**. Releasing a hold too early causes a hold break.

### Songs and charts

Put music files in **songs/**. Supported formats are **.ogg**, **.mp3**, and **.wav**. The repository includes **game.ogg** as a sample track.

1. Open **Songs** from the main menu.
2. Select a song to see its charts, or use the **Random** button (or press **R** on the song list) to play a random track.
3. Select a chart to play it. Use **Edit** or **New** to edit a chart or create one.
4. Save chart changes in the editor with **Ctrl + S**.

You can keep several charts for one song. Each chart can have its own name, author, and 1–5 star difficulty rating. The star rating is chart metadata; it does not automatically change the chart's note pattern.

#### Song and chart metadata

Open a chart in the editor, press **Esc**, and choose **Song Settings**. You can edit:

- **Song title** — the title displayed in the song browser instead of the audio file name.
- **Artist** — the performer or creator credited for the track.
- **Charter** — the author of the selected chart.
- **Difficulty** — a rating from 1 to 5 stars.

Song title and artist are stored as local song metadata; charter and difficulty are stored with the chart. Save the chart after changing chart details.

### Chart editor

The editor works directly on the song timeline. When playback is stopped, use the mouse to place notes; while playing, press lane keys to record notes. Longer recorded presses create hold notes. Right-click a note to remove it, and use the mouse wheel over a note to adjust a hold's length. The undo history stores up to 80 steps.

| Action | Controls |
| --- | --- |
| Start or stop playback | **Space** |
| Move by one grid step | **Left** / **Right** |
| Move by one second | **Shift + Left** / **Shift + Right** |
| Jump to the start / end | **Home** / **End** |
| Seek by 5 seconds | **Page Up** / **Page Down** |
| Seek by 30 seconds | **Shift + Page Up** / **Shift + Page Down** |
| Change timeline zoom | **Up** / **Down** |
| Change the snap-grid interval | **G** |
| Decrease / increase editor playback speed | **-** / **=** |
| Toggle event-effect preview | **V** |
| Undo | **Ctrl + Z** |
| Save | **Ctrl + S** |
| Rename the chart | **F2** |
| Delete the nearest note | **Delete** or **Backspace** |
| Shift all notes by 10 ms | **[** / **]** |
| Open the editor menu | **Esc** |

Editor playback speeds are **0.5×**, **0.75×**, **1.0×**, and **1.25×**. They only affect playback inside the editor, not gameplay speed; changing the rate also changes the audio pitch. NumPy is needed to prepare alternate-speed audio. You can also use the speed buttons in the right-hand panel.

Click the timeline bar at the top to seek. Hold **Ctrl** while using the mouse wheel to change the timeline zoom. The editor menu contains chart saving, Song Settings, the achievement editor, Auto Chart, and exit options.

### Automatic chart generation

Choose **Auto Chart** from the editor menu. The analyser reads audio through Pygame, examines four frequency ranges, and detects stronger changes in spectral energy. It applies spacing and density limits to avoid excessive note density; sustained sounds may be converted into hold notes.

- Requires **numpy**.
- Auto Chart replaces the current note list with a generated draft. Save a copy first if you need to preserve the original.
- Review the result manually. Different songs and mixes may require corrections to timing, lane choice, and hold length.

### Song events and event folders

Open a chart in the editor, press **Esc**, and choose **Events**. Events are attached to positions on the song timeline and can be previewed individually. The event editor also supports copy/paste of properties, duplication, folders, sorting, and locking.

| Event | What it does |
| --- | --- |
| **Glitch** | Distorts the screen with horizontal bands; duration and strength are adjustable. |
| **Flash** | Adds a white flash with adjustable fade-in and duration. |
| **Background** | Changes the background colour, with an optional transition back to the original colour. |
| **Image (beta)** | Displays an image behind the lanes, with pop-in, fade, or movement animation. |
| **Video (beta)** | Plays a clip with adjustable duration, size, position, fade, and movement. |
| **Heal** | Sends a white pickup down a selected lane. Hit it with the matching lane key to restore **1 HP**, up to the 5 HP maximum. Missing it causes a visual glitch but does not remove health. |
| **Text card** | Displays custom text for a set duration, fading in and out. Text is limited to 80 characters. |
| **Invert** | Temporarily applies a negative/inverted-colour effect to the screen. |

Place image and video files in **images/**. Supported image formats are **.png**, **.jpg**, and **.jpeg**; supported video formats are **.mp4**, **.webm**, **.mov**, **.avi**, **.mkv**, and **.m4v**. Video playback requires **opencv-python**. The Settings screen includes a media-dimming control for images and videos displayed behind the lanes.

Useful event-editor keys:

| Action | Controls |
| --- | --- |
| Add glitch / flash / image / background / video / heal / text card / invert | **1** / **2** / **3** / **4** / **5** / **6** / **7** / **8** |
| Select the previous or next event or folder | **Up** / **Down** |
| Move between event fields | **Tab** |
| Change a selected value | **Left** / **Right** (**Shift** changes it faster) |
| Preview the selected event | **P** |
| Fit an image or video to the screen | **F** |
| Set the selected event's time to the current cursor | **C** |
| Restore the original background colour | **R** |
| Copy / paste / duplicate event properties | **Ctrl + C** / **Ctrl + V** / **Ctrl + D** |
| Paste properties to all events of the same type | **Ctrl + Shift + V** |
| Delete the selected event or folder | **Delete** |
| Leave the event editor | **Esc** |

Use the **Folders** controls to create a folder, move events into or out of it, rename it, and lock or unlock it. Folders can be collapsed and expanded, and the event list can be sorted by time or type. A locked event or folder is protected from edits until it is unlocked. A chart can contain up to eight event folders.

### Achievement cards

The project includes an achievement-card catalogue and editor. Open **Achievements** from the main menu to browse the cards. To create or manage them, open a chart in the editor, press **Esc**, and choose **Achievements**.

Each custom entry stores:

- **Name** — up to 40 characters.
- **Description** — up to 200 characters.
- **Image** — selected from the supported images in **images/**.

Entries are saved as JSON content using the **.vcld** extension in the **achievements/** folder. The project includes **images/achievement_template.png** as a visual template. This feature manages custom achievement cards; it is not an automatic challenge-unlock or progression system.

### Settings

The Settings screen includes:

- Audio latency adjustment
- Note travel speed
- Music and sound-effect volume
- Rebindable keys for all four lanes
- Windowed or scaled fullscreen display
- Automatic song previews in the song browser
- Image and video dimming
- English / Russian interface language

Settings are stored locally in **data/settings.json**.

### Chart file format

Charts use JSON format version **4**. Times are measured in milliseconds. For notes, **lane** is numbered from **0** to **3**; **d** is the hold duration and is omitted for regular notes. Charts can also contain **charter**, **difficulty**, **events**, and **folders** fields.

~~~json
{
  "version": 4,
  "song": "game.ogg",
  "name": "Example chart",
  "charter": "Chart author",
  "difficulty": 3,
  "notes": [
    { "t": 4000, "lane": 0 },
    { "t": 5000, "lane": 2, "d": 600 }
  ],
  "events": [
    { "type": "flash", "t": 4200, "attack": 40, "dur": 500 },
    { "type": "heal", "t": 8200, "lane": 1, "speed": 170 },
    { "type": "card", "t": 9000, "dur": 2500, "text": "Example text" },
    { "type": "invert", "t": 12000, "dur": 200 }
  ],
  "folders": [
    { "name": "Intro", "locked": false }
  ]
}
~~~

For a heal event, **lane** is numbered from **1** to **4** (matching the gameplay lanes in order), and **speed** is the fall speed as a percentage. Events can also include **folder** and **locked** fields. A **folders** entry stores a folder's name and lock state. Older charts without metadata or folders can use their default values when loaded.

### Project structure

~~~text
geometry_rythm/
├── main.py                     # Application entry point
├── requirements.txt            # Python dependencies
├── core/
│   ├── game.py                 # Gameplay, scoring, health, and event playback
│   ├── chart.py                # Notes, chart metadata, JSON loading/saving
│   ├── editor.py               # Chart editor and playback-speed controls
│   ├── autochart.py            # Audio analysis and automatic chart generation
│   ├── events.py               # Timeline events and media helpers
│   ├── events_screen.py        # Event editor, folders, and event locking
│   ├── achievements.py         # Achievement-card storage
│   ├── achievement_editor.py  # Create, edit, and delete achievement cards
│   ├── achievements_screen.py # Achievement-card catalogue
│   ├── achievements_view.py   # Achievement-card rendering
│   ├── song_settings.py        # Song and chart metadata editor
│   ├── display.py              # Window/fullscreen display management
│   ├── stretch.py              # Alternate-speed audio generation
│   ├── dialogs.py              # Confirmation, text input, and selection dialogs
│   └── ...                     # Menus, sound, results, records, translation, visuals
├── songs/                      # Audio tracks (includes game.ogg)
├── images/                     # Event media and achievement images
├── achievements/               # Custom achievement cards (*.vcld)
└── data/                       # Charts, settings, records, and caches
~~~

Local generated data includes **data/charts/** for charts, **data/songmeta/** for song titles and artists, **data/songinfo/** for audio analysis, **data/cache/speed/** for alternate-speed audio, **data/settings.json** for preferences, and **data/records.json** for records.

### Windows executable

Check the [GitHub Releases page](https://github.com/Mistervock/geometry_rythm/releases) for downloadable Windows builds. If a release includes **GeometryRhythm.exe** or an archive, download it from the release **Assets** and follow the release notes. Unless the package specifies another layout, keep the executable beside the **songs/**, **data/**, and **images/** folders so the game can access your music, charts, settings, and media.

If no packaged build is available, run the game from source using the instructions above. The current repository version no longer includes **build_exe.bat** or **GeometryRhythm.spec**, so it does not provide a maintained one-click EXE build script.

---

## Русский

**Geometry Rhythm** — независимая ритм-игра с четырьмя геометрическими дорожками. Попадай в ноты в такт музыке, собирай комбо, следи за здоровьем и создавай собственные чарты для любимых треков.

Проект вдохновлён **Friday Night Funkin'** и геометрическим стилем **Geometry Catcher**, но содержит собственные инструменты: редактор чартов, метаданные песен, события на временной шкале и каталог пользовательских карточек достижений. Это фан-проект, а не официальная игра Friday Night Funkin'; он не связан с её создателями.

### Возможности

- **HD-разрешение:** 1280 × 720 и масштабируемый полноэкранный режим.
- **Четыре геометрические дорожки:** у каждой свой цвет и форма. Стандартные клавиши — **D**, **F**, **J**, **K**.
- **Обычные ноты и удержания:** нажимай в нужный момент и держи клавишу до конца длинной ноты.
- **Очки и здоровье:** оценки попаданий, множитель комбо до ×4, шкала здоровья на 5 HP, точность, итоговая оценка и экран результатов.
- **Список песен:** просматривай треки, слушай автоматические предпрослушивания или запускай случайную песню. Предпрослушивание отключается в настройках.
- **Метаданные песни и чарта:** задавай название и автора трека, автора чарта и сложность от 1 до 5 звёзд.
- **Редактор чартов:** ставь ноты мышью или записывай их во время проигрывания, меняй длину удержаний, отменяй действия, используй сетку и меняй скорость воспроизведения в редакторе.
- **Автоматическая разметка:** анализируй музыку с NumPy, чтобы создать черновик чарта и затем исправить его вручную.
- **События на временной шкале:** глюки, вспышки, фон, картинки, видео, хиллы, текстовые карточки и инверсия цветов.
- **Папки событий:** группируй события, сортируй список по времени или типу, блокируй отдельные события или целые папки от случайного редактирования.
- **Карточки достижений:** создавай, редактируй, просматривай и удаляй собственные карточки с названием, описанием и изображением.
- **Настройки:** клавиши дорожек, аудиозадержка, скорость нот, громкость, полноэкранный режим, язык, предпрослушивание и затемнение медиа.

### Требования

- Python
- **pygame** — окно игры, ввод, графика и звук
- **numpy** — автоматическая разметка и подготовка аудио для изменения скорости в редакторе
- **opencv-python** — воспроизведение видео в событиях

Все зависимости перечислены в **requirements.txt**. NumPy и OpenCV необходимы для отдельных функций; для обычной игры воспроизведение видео не требуется.

### Запуск из исходников

Установи Python и Git, склонируй репозиторий, установи зависимости и запусти игру:

~~~bash
git clone https://github.com/Mistervock/geometry_rythm.git
cd geometry_rythm
python -m pip install -r requirements.txt
python main.py
~~~

В Windows, если команда **python** не распознаётся, используй **py**, если эта команда доступна в системе.

### Игровой процесс

Перед началом идёт отсчёт **3 · 2 · 1 · RYTHM!**

| Действие | Управление |
| --- | --- |
| Попадать по четырём дорожкам | По умолчанию **D**, **F**, **J**, **K** |
| Обычная нота | Нажми клавишу дорожки, когда нота достигнет линии попадания |
| Удержание | Нажми в начале и держи до конца ноты |
| Пауза или продолжение | **P** или **Esc** |
| Вернуться в меню из паузы | **M** |

Клавиши дорожек можно изменить в настройках. Начальное здоровье — 5 HP. Пропуск ноты уменьшает здоровье и сбрасывает комбо; каждые 10 комбо повышают множитель очков, максимум — **×4**. Если отпустить удержание слишком рано, удержание будет сорвано.

### Песни и чарты

Помещай музыкальные файлы в папку **songs/**. Поддерживаются форматы **.ogg**, **.mp3** и **.wav**. В репозитории есть пример трека — **game.ogg**.

1. Открой раздел **«ПЕСНИ»** в главном меню.
2. Выбери песню, чтобы увидеть её чарты, или нажми **«Случайная»** (либо клавишу **R** в списке песен), чтобы запустить случайный трек.
3. Выбери чарт для игры. Кнопки **«Править»** и **«Новый»** позволяют отредактировать существующий чарт или создать новый.
4. Сохраняй изменения в редакторе сочетанием **Ctrl + S**.

Для одной песни можно создавать несколько чартов. У каждого могут быть собственное название, автор и сложность от 1 до 5 звёзд. Звёзды — это метаданные чарта; сами по себе они не изменяют последовательность нот.

#### Название песни, автор и сложность чарта

Открой чарт в редакторе, нажми **Esc** и выбери **«Настройки песни»**. Там можно изменить:

- **Название песни** — отображается в списке вместо имени аудиофайла.
- **Автор песни** — исполнитель или автор трека.
- **Автор чарта** — человек, создавший выбранный чарт.
- **Сложность** — оценка от 1 до 5 звёзд.

Название и автор песни сохраняются в локальных метаданных трека; автор и сложность хранятся вместе с чартом. После изменения данных чарта не забудь его сохранить.

### Редактор чартов

Когда песня остановлена, ноты можно ставить мышью; во время проигрывания — записывать клавишами дорожек. Более длинные нажатия создают удержания. Правая кнопка мыши удаляет ноту, а колёсико над нотой изменяет длину удержания. История отмены хранит до 80 шагов.

| Действие | Управление |
| --- | --- |
| Начать или остановить проигрывание | **Space** |
| Передвинуть курсор на шаг сетки | **Left** / **Right** |
| Передвинуть курсор на секунду | **Shift + Left** / **Shift + Right** |
| Перейти в начало / конец песни | **Home** / **End** |
| Перемотка на 5 секунд | **Page Up** / **Page Down** |
| Перемотка на 30 секунд | **Shift + Page Up** / **Shift + Page Down** |
| Изменить масштаб таймлайна | **Up** / **Down** |
| Изменить шаг сетки | **G** |
| Уменьшить / увеличить скорость проигрывания в редакторе | **-** / **=** |
| Включить или выключить предпросмотр событий | **V** |
| Отменить действие | **Ctrl + Z** |
| Сохранить чарт | **Ctrl + S** |
| Переименовать чарт | **F2** |
| Удалить ближайшую ноту | **Delete** или **Backspace** |
| Сдвинуть все ноты на 10 мс | **[** / **]** |
| Открыть меню редактора | **Esc** |

Скорости предпрослушивания в редакторе: **0.5×**, **0.75×**, **1.0×** и **1.25×**. Они влияют только на прослушивание внутри редактора, а не на скорость игры; при изменении скорости меняется и высота звука. Для подготовки аудио с другой скоростью нужен NumPy. Скорость также можно выбрать кнопками правой панели.

Нажми на верхнюю полосу таймлайна, чтобы переместить курсор. Удерживай **Ctrl** и крути колёсико мыши, чтобы изменить масштаб. В меню редактора доступны сохранение, настройки песни, редактор достижений, авто-разметка и выход.

### Автоматическая разметка

Выбери **«АВТО-РАЗМЕТКА»** в меню редактора. Анализатор читает аудио средствами Pygame, изучает четыре частотных диапазона и ищет выраженные изменения спектральной энергии. Затем он ограничивает плотность нот и интервалы между ними; длительные звуки могут превращаться в удержания.

- Требуется **numpy**.
- Авто-разметка заменяет текущий список нот черновиком. Если нужно сохранить исходный вариант, заранее сделай копию.
- Проверь результат вручную: в зависимости от трека могут понадобиться поправки тайминга, дорожек и длины удержаний.

### События песни и папки событий

Открой чарт в редакторе, нажми **Esc** и выбери **«СОБЫТИЯ»**. События привязаны ко времени песни и могут просматриваться по отдельности. В редакторе доступны копирование и вставка параметров, дублирование, папки, сортировка и блокировка.

| Событие | Что делает |
| --- | --- |
| **Глюк** | Искажает экран горизонтальными полосами; можно настроить силу и длительность. |
| **Вспышка** | Создаёт белую вспышку с настройкой скорости появления и длительности. |
| **Фон** | Меняет цвет фона; можно настроить переход и возврат исходного цвета. |
| **Картинка (бета)** | Показывает изображение под дорожками; доступны резкое появление, плавность и движение. |
| **Видео (бета)** | Показывает ролик с настройками длительности, размера, позиции, плавности и движения. |
| **Хилл** | Белый круг падает по выбранной дорожке. Попади по нему нужной клавишей, чтобы восстановить **1 HP** (не выше 5 HP). Пропуск вызывает визуальный глитч, но здоровье не уменьшает. |
| **Текстовая карточка** | Показывает заданный текст на определённое время с плавным появлением и исчезновением. Лимит — 80 символов. |
| **Инверсия** | На короткое время превращает цвета экрана в негатив. |

Помещай изображения и видео в **images/**. Поддерживаются изображения **.png**, **.jpg**, **.jpeg** и видео **.mp4**, **.webm**, **.mov**, **.avi**, **.mkv**, **.m4v**. Для видео нужен **opencv-python**. В настройках есть регулировка затемнения медиа, отображаемого за дорожками.

Полезные клавиши редактора событий:

| Действие | Управление |
| --- | --- |
| Добавить глюк / вспышку / картинку / фон / видео / хилл / карточку / инверсию | **1** / **2** / **3** / **4** / **5** / **6** / **7** / **8** |
| Выбрать предыдущее или следующее событие или папку | **Up** / **Down** |
| Перейти между полями события | **Tab** |
| Изменить значение | **Left** / **Right** (**Shift** ускоряет изменение) |
| Просмотреть выбранное событие | **P** |
| Подогнать картинку или видео под экран | **F** |
| Привязать время события к курсору | **C** |
| Вернуть исходный цвет фона | **R** |
| Копировать / вставить / дублировать параметры | **Ctrl + C** / **Ctrl + V** / **Ctrl + D** |
| Вставить параметры во все события того же типа | **Ctrl + Shift + V** |
| Удалить событие или папку | **Delete** |
| Выйти из редактора событий | **Esc** |

В разделе **«ПАПКИ»** можно создавать папки, перемещать события в папки и из них, переименовывать и блокировать папки. Содержимое папок можно сворачивать и раскрывать; список сортируется по времени или типу. Заблокированное событие или папку сначала нужно разблокировать. Для одного чарта можно создать до восьми папок событий.

### Карточки достижений

В проекте есть каталог и редактор карточек достижений. Открой **«Достижения»** в главном меню, чтобы просмотреть карточки. Чтобы создавать и редактировать их, открой чарт в редакторе, нажми **Esc** и выбери **«Достижения»**.

У каждой карточки есть:

- **Название** — до 40 символов.
- **Описание** — до 200 символов.
- **Изображение** — выбирается из поддерживаемых файлов папки **images/**.

Карточки сохраняются в виде JSON-содержимого с расширением **.vcld** в папке **achievements/**. В проекте есть шаблон изображения **images/achievement_template.png**. Эта функция позволяет создавать и просматривать пользовательские карточки; автоматического отслеживания разблокировок или прогрессии достижений пока нет.

### Настройки

В разделе настроек можно менять:

- аудиозадержку;
- скорость падения нот;
- громкость музыки и звуковых эффектов;
- клавиши всех четырёх дорожек;
- оконный или масштабируемый полноэкранный режим;
- автоматическое предпрослушивание песен;
- затемнение изображений и видео;
- язык интерфейса — English или Русский.

Настройки сохраняются локально в **data/settings.json**.

### Формат файла чарта

Чарты хранятся в JSON-формате версии **4**. Время задаётся в миллисекундах. Для нот **lane** — номер дорожки от **0** до **3**, **d** — длительность удержания (у обычной ноты отсутствует). Чарт может содержать поля **charter**, **difficulty**, **events** и **folders**.

~~~json
{
  "version": 4,
  "song": "game.ogg",
  "name": "Пример чарта",
  "charter": "Автор чарта",
  "difficulty": 3,
  "notes": [
    { "t": 4000, "lane": 0 },
    { "t": 5000, "lane": 2, "d": 600 }
  ],
  "events": [
    { "type": "flash", "t": 4200, "attack": 40, "dur": 500 },
    { "type": "heal", "t": 8200, "lane": 1, "speed": 170 },
    { "type": "card", "t": 9000, "dur": 2500, "text": "Пример текста" },
    { "type": "invert", "t": 12000, "dur": 200 }
  ],
  "folders": [
    { "name": "Вступление", "locked": false }
  ]
}
~~~

У события **heal** поле **lane** нумеруется от **1** до **4**, в соответствии с игровыми дорожками, а **speed** задаёт скорость падения в процентах. События также могут содержать поля **folder** и **locked**. В записи **folders** хранится название папки и состояние блокировки. Старые чарты без метаданных и папок загружаются с настройками по умолчанию для отсутствующих полей.

### Структура проекта

~~~text
geometry_rythm/
├── main.py                     # Точка входа в приложение
├── requirements.txt            # Зависимости Python
├── core/
│   ├── game.py                 # Игровой процесс, счёт, здоровье и события
│   ├── chart.py                # Ноты, метаданные и JSON-чарты
│   ├── editor.py               # Редактор и скорость воспроизведения
│   ├── autochart.py            # Анализ аудио и авто-разметка
│   ├── events.py               # События и работа с медиа
│   ├── events_screen.py        # Редактор событий и папок
│   ├── achievements.py         # Хранение карточек достижений
│   ├── achievement_editor.py   # Создание, редактирование и удаление карточек
│   ├── achievements_screen.py  # Просмотр каталога карточек
│   ├── achievements_view.py    # Отрисовка карточек достижений
│   ├── song_settings.py        # Метаданные песни и чарта
│   ├── display.py              # Оконный и полноэкранный режим
│   ├── stretch.py              # Подготовка аудио для другой скорости
│   ├── dialogs.py              # Подтверждение, ввод текста и выбор
│   └── ...                     # Меню, звук, результаты, рекорды, переводы и эффекты
├── songs/                      # Музыкальные файлы, включая game.ogg
├── images/                     # Изображения и видео для событий и карточек
├── achievements/               # Пользовательские карточки (*.vcld)
└── data/                       # Чарты, настройки, рекорды и кэш
~~~

Локально создаются данные: **data/charts/** — чарты, **data/songmeta/** — названия и авторы песен, **data/songinfo/** — анализ аудио, **data/cache/speed/** — аудио для альтернативной скорости, **data/settings.json** — настройки, **data/records.json** — рекорды.

### Windows-версия (.exe)

Проверь [страницу GitHub Releases](https://github.com/Mistervock/geometry_rythm/releases): готовые Windows-сборки, если они опубликованы, находятся в разделе **Assets** соответствующего релиза. Скачай EXE или архив и следуй инструкциям в описании релиза. Если в пакете не указано иное, размести исполняемый файл рядом с папками **songs/**, **data/** и **images/**, чтобы игра могла читать музыку, чарты, настройки и медиа.

Если готовой сборки нет, запусти игру из исходников по инструкции выше. В текущей версии репозитория больше нет файлов **build_exe.bat** и **GeometryRhythm.spec**, поэтому проект сейчас не содержит поддерживаемого скрипта для сборки EXE в один клик.
