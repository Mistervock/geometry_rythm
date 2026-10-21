# Geometry Rhythm

<p align="center">
  <strong>A geometric rhythm game inspired by Friday Night Funkin' and Geometry Catcher.</strong><br>
  <a href="#english">English</a> · <a href="#русский">Русский</a> · <a href="https://github.com/Mistervock/geometry_rythm/releases">Releases / Релизы</a>
</p>

<p align="center">
  <strong>Version 0.2 · HD 1280 × 720 / Full HD 1920 × 1080 · Python + Pygame</strong>
</p>

---

## English

**Geometry Rhythm** is an independent rhythm game built around four geometric lanes. Hit notes in time with the music, build combos, manage your health, and make your own charts for the tracks you want to play.

The project is inspired by **Friday Night Funkin'** and the geometric style of **Geometry Catcher**, with its own chart editor, song metadata, event timeline, and custom achievement-card library. It is a fan-made project, not an official Friday Night Funkin' game and not affiliated with its creators.

### Features

- **HD and Full HD display:** selectable 1280 × 720 and 1920 × 1080 resolutions, with a windowed or scaled fullscreen mode.
- **Four geometric lanes:** each lane has its own shape and colour. Default gameplay keys: **D**, **F**, **J**, **K**.
- **Tap notes and hold notes:** hit notes at the right moment and keep holding for the full duration of long notes.
- **Scoring, ranks, and health:** timing judgements, combo multipliers up to ×4, 5 HP, accuracy, grades, results, per-chart best ranks (**D–S**), and overall song ranks.
- **Song browser:** song covers, artist-grouped lists, search, sorting by title/rank/chart count, track previews, and random selection.
- **Song and chart metadata:** set a song title, artist, cover image, chart author, 1–5 star difficulty, and an optional achievement awarded for completing that chart.
- **Chart editor:** place or record notes, edit hold lengths, undo, snap to a grid, adjust editor playback speed, and view an on-screen shortcut guide.
- **Automatic chart generation:** analyse audio with NumPy and choose **Easy**, **Normal**, or **Hard** note density before generating an editable draft.
- **Chart safety and sharing:** periodic autosave snapshots plus JSON chart import/export.
- **Timeline events:** glitches, flashes, background changes, images, videos, heal pickups, text cards, and screen-colour inversion.
- **Event folders:** group related events, sort by time or type, and lock individual events or whole folders against accidental edits.
- **Achievement progression:** create custom achievement cards and assign one to a chart; completing that chart without failing unlocks the assigned achievement.
- **Customisable controls:** remap the four gameplay lanes and keyboard actions for menus, the song list, and the chart editor.
- **Developer tools:** edit song/chart metadata and set artist-group colours from Developer Mode.
- **Settings and diagnostics:** audio latency, note speed, volume, fullscreen mode, resolution, language, song previews, media dimming, and an optional FPS counter.

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

Put music files in **songs/**. Supported formats are **.ogg**, **.mp3**, and **.wav**.

1. Open **Songs** from the main menu.
2. Choose a track to view its charts, or use the random-selection button / **R** (default) to start a random available chart.
3. Select a chart to play it. Use **Edit** or **New** to edit a chart or create one.
4. Save chart changes in the editor with **Ctrl + S**.

You can keep several charts for one song. Each chart can have its own name, author, 1–5 star difficulty, and optional achievement. The star rating is chart metadata; it does not automatically change the chart's note pattern.

#### Search, sorting, ranks, and Developer Mode

The song list can be searched by song title, artist, chart name, or charter. By default, press **/** or **F** to start a search, and **Tab** to cycle sorting modes: author groups, title, best rank, or number of charts. Search and sorting shortcuts can be remapped in Settings.

The song and chart lists show completion and rank information. Finishing a chart without failing records a win; the game stores the best chart rank from **D** to **S** and calculates an overall song rank from its charts.

Press **7** (default) in the song list to open **Developer Mode**. It provides tools for editing a song's title, artist and cover image, changing a chart's name or assigned song, and setting background colours for artist groups. This is a developer utility, not a gameplay mode.

#### Song and chart metadata

Open a chart in the editor, press **Esc**, and choose **Song Settings**. You can edit:

- **Song title** — the title displayed in the song browser instead of the audio file name.
- **Artist** — the performer or creator credited for the track.
- **Cover image** — select an image from **images/** for the song-list background.
- **Charter** — the author of the selected chart.
- **Difficulty** — a rating from 1 to 5 stars.
- **Achievement on win** — optionally assign a custom achievement card to this chart.

Song title, artist, and cover image are stored as local song metadata; charter, difficulty, and the assigned achievement are stored with the chart. Save the chart after changing chart details. An assigned achievement unlocks only when the chart is completed without failing; the game remembers unlocked achievement cards locally.

### Chart editor

The editor works directly on the song timeline. When playback is stopped, use the mouse to place notes; while playing, press lane keys to record notes. Longer recorded presses create hold notes. Right-click a note to remove it, and use the mouse wheel over a note to adjust a hold's length. The undo history stores up to 80 steps.

| Action | Default controls |
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

Editor playback speeds are **0.5×**, **0.75×**, **1.0×**, and **1.25×**. They only affect playback inside the editor, not gameplay speed; changing the rate also changes the audio pitch. NumPy is needed to prepare alternate-speed audio. The speed buttons are also available in the right-hand panel.

The default keyboard shortcuts can be changed in **Settings → Chart Editor Keys**. Press **F1** inside the editor to open a shortcut guide that reflects your current bindings; press any key to close it. Press **F3** on any screen to toggle the FPS counter.

Click the timeline bar at the top to seek. Hold **Ctrl** while using the mouse wheel to change the timeline zoom. The editor menu contains chart saving, Song Settings, the achievement editor, chart import/export, Auto Chart, and exit options.

#### Chart import, export, and autosave

Choose **Export Chart** from the editor menu to save the current chart as JSON under **exports/**. **Import Chart** reads a JSON file from that folder and creates a separate chart; the song file referenced by the chart must already exist in **songs/**.

When the chart has unsaved changes and playback is stopped, the editor creates an autosave snapshot approximately every **60 seconds** in **data/autosave/**. Autosaves are kept separate from the regular chart list. Use **Ctrl + S** to save the chart normally; autosave snapshots are an extra safeguard, not a replacement for manual saving.

### Automatic chart generation

Choose **Auto Chart** from the editor menu. Before analysis, select one of three note-density presets:

- **Easy** — fewer notes and more space between them.
- **Normal** — the standard balance of density and spacing.
- **Hard** — denser note placement with shorter minimum gaps.

The analyser reads audio through Pygame, examines four frequency ranges, and detects stronger changes in spectral energy. It applies spacing and density limits to avoid excessive note density; sustained sounds may be converted into hold notes.

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

The project includes an achievement-card catalogue and editor. Open **Achievements** from the main menu to browse available cards. To create or manage cards, open a chart in the editor, press **Esc**, and choose **Achievements**.

Each custom entry stores:

- **Name** — up to 40 characters.
- **Description** — up to 200 characters.
- **Image** — selected from supported images in **images/**.

Entries are saved as JSON content using the **.vcld** extension in **achievements/**. The project includes **images/achievement_template.png** as a visual template.

To make a card unlockable, open **Song Settings** for a chart and select it under **Achievement on win**. Completing that chart without failing unlocks the assigned card; the results screen reports the unlock and the catalogue marks received cards. Local unlock state is stored in **data/achievements_unlocked.json**.

### Settings

The Settings screen includes:

- Audio latency adjustment
- Note travel speed
- Music and sound-effect volume
- Rebindable keys for all four gameplay lanes
- Rebindable actions for menu/song navigation and chart editing
- Windowed or scaled fullscreen display
- Selectable resolution: **1280 × 720** or **1920 × 1080**
- Automatic song previews in the song browser
- Image and video dimming
- English / Russian interface language

Settings are stored locally in **data/settings.json**. The **F3** shortcut toggles the FPS counter and is available throughout the game.

### Chart file format

Charts use JSON format version **4**. Times are measured in milliseconds. For notes, **lane** is numbered from **0** to **3**; **d** is the hold duration and is omitted for regular notes. Charts can also contain **charter**, **difficulty**, **achievement** (the assigned **.vcld** filename), **events**, and **folders** fields. The achievement field is optional.

~~~json
{
  "version": 4,
  "song": "game.ogg",
  "name": "Example chart",
  "charter": "Chart author",
  "difficulty": 3,
  "achievement": "achievement__example.vcld",
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
│   ├── game.py                 # Gameplay, scoring, ranks, health, and event playback
│   ├── chart.py                # Notes, metadata, achievement link, and JSON chart format
│   ├── editor.py               # Chart editor, autosave, and chart import/export
│   ├── autochart.py            # Audio analysis and density presets
│   ├── songs.py                # Songs, metadata, ranks, wins, autosaves, and chart files
│   ├── songs_screen.py         # Song search, sorting, covers, and chart browser
│   ├── song_settings.py        # Song/chart metadata and achievement assignment
│   ├── settings.py             # Local settings
│   ├── settings_screen.py      # Gameplay, display, and audio settings
│   ├── keymap.py               # Configurable keyboard actions
│   ├── keys_screen.py          # Menu/song/editor key bindings
│   ├── screen_setting.py       # Resolution and layout scaling
│   ├── dev_menu.py             # Developer tools for songs, charts, and artist colours
│   ├── events.py               # Timeline events and media helpers
│   ├── events_screen.py        # Event editor, folders, and event locking
│   ├── achievements.py         # Achievement cards and unlock state
│   ├── achievement_editor.py  # Create, edit, and delete achievement cards
│   ├── achievements_screen.py # Achievement-card catalogue
│   ├── achievements_view.py   # Achievement-card rendering
│   ├── display.py              # Window/fullscreen display and FPS counter
│   ├── stretch.py              # Alternate-speed audio generation
│   ├── dialogs.py              # Confirmation, text input, and selection dialogs
│   └── ...                     # Menu, results, records, translation, visuals, audio, cache
├── songs/                      # Audio tracks (.ogg, .mp3, .wav)
├── images/                     # Song covers, event media, and achievement images
├── achievements/               # Custom achievement cards (*.vcld)
├── exports/                    # Exported/importable chart JSON files (created as needed)
└── data/                       # Local charts, settings, records, ranks, wins, and caches
~~~

Local data includes **data/charts/** for charts, **data/songmeta/** for song titles/artists/covers, **data/songinfo/** for audio analysis, **data/cache/speed/** for alternate-speed audio, **data/autosave/** for chart snapshots, **data/settings.json** for preferences, **data/records.json** for score records, **data/ranks.json** for best chart ranks, **data/wins.json** for completed charts, **data/author_colors.json** for artist-group colours, and **data/achievements_unlocked.json** for unlocked achievement cards.

### Windows executable and distribution

There is **no prebuilt Windows .exe** available at the moment. The repository does not include an executable build script or a PyInstaller specification. Compiling or repackaging a distributable executable is currently unavailable under the copyright restrictions set by the project author. Please do not expect a compiled download until the author explicitly authorizes and publishes one.

The [GitHub Releases page](https://github.com/Mistervock/geometry_rythm/releases) may be used for release announcements, but **there is no downloadable .exe right now**.

### Credits, copyright, and free mods

**Game code:** Copyright © 2026 Mistervock. All rights reserved except for the limited permissions explicitly described in [LICENSE.md](LICENSE.md).

**Music credit:** **“YARARARA (ヤラララ)” — AnythingBecomeMoe, featuring Kasane Teto SV2.** [Official music video](https://www.youtube.com/watch?v=T24rF_x0TmQ). This credit identifies the song's creator; it does not mean the music or video is licensed by the game author. Third-party music, video, characters, artwork, and other assets remain subject to their respective rights holders' terms.

**Free modding is allowed under the custom terms in [LICENSE.md](LICENSE.md):**
- You may download and use the project for personal, non-commercial purposes and create modifications.
- Mods must be available to everyone free of charge. Do not sell mods, charge for downloads or access, put them behind a paywall or subscription, or sell bundles that include them.
- Distribute mods as separate files (for example, chart JSON, your own assets, or patches) that require a copy of the game. Do not bundle the game's source code, complete game, executable, or original third-party media with a mod.
- Do not republish the game's full source code or substantial portions on other websites, repositories, or file-sharing services without the author's prior written permission.
- Keep the original copyright notice, credit **Geometry Rhythm** and link to this repository. Clearly label mods as unofficial; do not claim authorship of the original game, impersonate the project author, or imply endorsement.
- Do not present a modified version as an official release or distribute a compiled/repackaged game without prior written permission.

This is a **custom, restrictive permission notice**, not a standard open-source licence. GitHub's own terms may still allow users to view or fork a public repository within GitHub; this README and the custom terms do not disable that platform feature.
---

## Русский

**Geometry Rhythm** — независимая ритм-игра с четырьмя геометрическими дорожками. Попадай в ноты в такт музыке, собирай комбо, следи за здоровьем и создавай собственные чарты для любимых треков.

Проект вдохновлён **Friday Night Funkin'** и геометрическим стилем **Geometry Catcher**, но содержит собственные инструменты: редактор чартов, метаданные песен, события на временной шкале и каталог пользовательских карточек достижений. Это фан-проект, а не официальная игра Friday Night Funkin'; он не связан с её создателями.

### Возможности

- **HD и Full HD:** выбор разрешения 1280 × 720 или 1920 × 1080, оконный и масштабируемый полноэкранный режимы.
- **Четыре геометрические дорожки:** у каждой свой цвет и форма. Стандартные игровые клавиши — **D**, **F**, **J**, **K**.
- **Обычные ноты и удержания:** нажимай в нужный момент и держи клавишу до конца длинной ноты.
- **Очки, ранги и здоровье:** оценки попаданий, множитель комбо до ×4, шкала на 5 HP, точность, итоговая оценка, ранги чартов **D–S** и общий ранг песни.
- **Список песен:** обложки, группировка по авторам, поиск, сортировка по названию/рангу/числу чартов, предпрослушивание и случайный выбор.
- **Метаданные песни и чарта:** название, автор и обложка трека, автор чарта, сложность от 1 до 5 звёзд и необязательное достижение за прохождение.
- **Редактор чартов:** расстановка и запись нот, изменение длины удержаний, отмена действий, сетка, скорость воспроизведения и экранная подсказка по клавишам.
- **Автоматическая разметка:** анализ музыки с NumPy и выбор плотности нот — **лёгкая**, **средняя** или **сложная**.
- **Защита и обмен чартами:** периодическое автосохранение черновиков, импорт и экспорт чартов в JSON.
- **События на временной шкале:** глюки, вспышки, смена фона, картинки, видео, хиллы, текстовые карточки и инверсия цветов.
- **Папки событий:** группировка и сортировка событий, блокировка отдельных событий и целых папок.
- **Система достижений:** создавай карточки и назначай одну из них чарту; прохождение чарта без провала открывает назначенное достижение.
- **Настраиваемое управление:** смена клавиш дорожек и горячих клавиш меню, списка песен и редактора.
- **Инструменты разработчика:** изменение метаданных песен/чартов и цветов групп авторов.
- **Настройки и диагностика:** задержка звука, скорость нот, громкость, режим экрана, разрешение, язык, предпрослушивание, затемнение медиа и счётчик FPS.

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

Помещай музыкальные файлы в папку **songs/**. Поддерживаются форматы **.ogg**, **.mp3** и **.wav**.

1. Открой раздел **«ПЕСНИ»** в главном меню.
2. Выбери песню, чтобы увидеть её чарты, или используй случайный выбор — по умолчанию клавиша **R**.
3. Выбери чарт для игры. Кнопки **«Править»** и **«Новый»** позволяют отредактировать существующий чарт или создать новый.
4. Сохраняй изменения в редакторе сочетанием **Ctrl + S**.

Для одной песни можно создавать несколько чартов. У каждого могут быть собственное название, автор, сложность от 1 до 5 звёзд и необязательное достижение. Звёзды — это метаданные чарта; сами по себе они не изменяют последовательность нот.

#### Поиск, сортировка, ранги и режим разработчика

Список можно искать по названию песни, автору, названию чарта и автору чарта. По умолчанию клавиша **/** или **F** включает поиск, а **Tab** переключает сортировку: группы по авторам, название, лучший ранг или количество чартов. Горячие клавиши можно переназначить в настройках.

В списках показываются прохождения и ранги. Завершение чарта без провала записывает победу; игра хранит лучший ранг каждого чарта от **D** до **S** и рассчитывает общий ранг песни по её чартам.

Нажми **7** (по умолчанию) в списке песен, чтобы открыть **режим разработчика**. В нём можно менять название, автора и обложку песни, переименовывать чарт, назначать ему другую песню и задавать цвета фона для групп авторов. Это инструмент разработчика, а не отдельный игровой режим.

#### Название песни, автор и сложность чарта

Открой чарт в редакторе, нажми **Esc** и выбери **«Настройки песни»**. Там можно изменить:

- **Название песни** — отображается в списке вместо имени аудиофайла.
- **Автор песни** — исполнитель или автор трека.
- **Обложка песни** — изображение из папки **images/** для фона экрана выбора песни.
- **Автор чарта** — человек, создавший выбранный чарт.
- **Сложность** — оценка от 1 до 5 звёзд.
- **Достижение за победу** — необязательная карточка, которая откроется за успешное прохождение этого чарта.

Название, автор и обложка сохраняются в локальных метаданных трека; автор, сложность и назначенное достижение хранятся вместе с чартом. После изменения данных чарта не забудь его сохранить. Назначенное достижение открывается после завершения чарта без провала; игра хранит состояние открытых карточек локально.

### Редактор чартов

Когда песня остановлена, ноты можно ставить мышью; во время проигрывания — записывать клавишами дорожек. Более длинные нажатия создают удержания. Правая кнопка мыши удаляет ноту, а колёсико над нотой изменяет длину удержания. История отмены хранит до 80 шагов.

| Действие | Клавиши по умолчанию |
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

Скорости воспроизведения в редакторе: **0.5×**, **0.75×**, **1.0×** и **1.25×**. Они влияют только на прослушивание внутри редактора, а не на скорость игры; при изменении скорости меняется и высота звука. Для подготовки аудио с другой скоростью нужен NumPy.

Клавиши редактора можно переназначить в **«Настройки» → «Клавиши редактора»**. Нажми **F1** внутри редактора, чтобы открыть подсказку со своими текущими клавишами; любая клавиша закрывает её. **F3** на любом экране включает или выключает счётчик FPS.

Нажми на верхнюю полосу таймлайна, чтобы переместить курсор. Удерживай **Ctrl** и крути колёсико мыши, чтобы изменить масштаб. В меню редактора доступны сохранение, настройки песни, редактор достижений, импорт/экспорт чартов, авто-разметка и выход.

#### Импорт, экспорт и автосохранение чартов

Пункт **«Экспорт чарта»** сохраняет текущий чарт в JSON в папку **exports/**. Пункт **«Импорт чарта»** загружает JSON из этой папки и создаёт отдельный чарт; указанный в файле музыкальный трек должен уже находиться в **songs/**.

Если в чарте есть несохранённые изменения и песня не проигрывается, редактор примерно раз в **60 секунд** создаёт копию автосохранения в **data/autosave/**. Эти копии не отображаются в обычном списке чартов. Для обычного сохранения по-прежнему используй **Ctrl + S**.

### Автоматическая разметка

Выбери **«АВТО-РАЗМЕТКА»** в меню редактора. Перед анализом можно выбрать один из трёх пресетов плотности:

- **Лёгкая** — меньше нот и больше промежутки между ними.
- **Средняя** — стандартный баланс количества нот и интервалов.
- **Сложная** — более плотная разметка и меньшие минимальные интервалы.

Анализатор читает аудио средствами Pygame, изучает четыре частотных диапазона и ищет выраженные изменения спектральной энергии. Затем он ограничивает плотность нот и интервалы между ними; длительные звуки могут превращаться в удержания.

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

Карточки сохраняются в виде JSON-содержимого с расширением **.vcld** в папке **achievements/**. В проекте есть шаблон изображения **images/achievement_template.png**.

Чтобы карточка открывалась за прохождение, назначь её в пункте **«Достижение за победу»** в настройках чарта. Завершение выбранного чарта без провала открывает карточку; экран результатов сообщает об этом, а в каталоге полученные карточки отмечаются. Состояние хранится в **data/achievements_unlocked.json**.

### Настройки

В разделе настроек можно менять:

- аудиозадержку;
- скорость падения нот;
- громкость музыки и звуковых эффектов;
- клавиши всех четырёх дорожек;
- горячие клавиши меню, списка песен и редактора;
- оконный или масштабируемый полноэкранный режим;
- разрешение **1280 × 720** или **1920 × 1080**;
- автоматическое предпрослушивание песен;
- затемнение изображений и видео;
- язык интерфейса — English или Русский.

Настройки сохраняются локально в **data/settings.json**. Клавиша **F3** включает или выключает счётчик FPS на любом экране.

### Формат файла чарта

Чарты хранятся в JSON-формате версии **4**. Время задаётся в миллисекундах. Для нот **lane** — номер дорожки от **0** до **3**, **d** — длительность удержания (у обычной ноты отсутствует). Чарт может содержать поля **charter**, **difficulty**, **achievement** (имя файла карточки **.vcld**), **events** и **folders**. Поле **achievement** необязательно.

~~~json
{
  "version": 4,
  "song": "game.ogg",
  "name": "Пример чарта",
  "charter": "Автор чарта",
  "difficulty": 3,
  "achievement": "achievement__example.vcld",
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
│   ├── game.py                 # Игровой процесс, очки, ранги, здоровье и события
│   ├── chart.py                # Ноты, метаданные, достижение и JSON-чарты
│   ├── editor.py               # Редактор, автосохранение, импорт и экспорт
│   ├── autochart.py            # Анализ аудио и пресеты плотности нот
│   ├── songs.py                # Песни, метаданные, ранги, победы и файлы чартов
│   ├── songs_screen.py         # Поиск песен, сортировка, обложки и список чартов
│   ├── song_settings.py        # Метаданные песни/чарта и назначение достижения
│   ├── settings.py             # Локальные настройки
│   ├── settings_screen.py      # Настройки игры, экрана и звука
│   ├── keymap.py               # Настраиваемые клавиши управления
│   ├── keys_screen.py          # Назначение клавиш меню, песен и редактора
│   ├── screen_setting.py       # Разрешение и масштаб интерфейса
│   ├── dev_menu.py             # Инструменты разработчика и цвета авторов
│   ├── events.py               # События и работа с медиа
│   ├── events_screen.py        # Редактор событий и папок
│   ├── achievements.py         # Карточки и состояние достижений
│   ├── achievement_editor.py   # Создание, редактирование и удаление карточек
│   ├── achievements_screen.py  # Просмотр каталога карточек
│   ├── achievements_view.py    # Отрисовка карточек
│   ├── display.py              # Оконный/полноэкранный режим и счётчик FPS
│   ├── stretch.py              # Подготовка аудио для другой скорости
│   ├── dialogs.py              # Подтверждение, ввод текста и выбор
│   └── ...                     # Меню, результаты, рекорды, переводы, эффекты, звук и кэш
├── songs/                      # Музыкальные файлы (.ogg, .mp3, .wav)
├── images/                     # Обложки песен, медиа событий и картинки достижений
├── achievements/               # Пользовательские карточки (*.vcld)
├── exports/                    # Экспортируемые/импортируемые JSON-чарты (создаётся при необходимости)
└── data/                       # Чарты, настройки, рекорды, ранги, победы и кэш
~~~

Локальные данные: **data/charts/** — чарты, **data/songmeta/** — названия, авторы и обложки песен, **data/songinfo/** — анализ аудио, **data/cache/speed/** — аудио для альтернативной скорости, **data/autosave/** — копии автосохранения, **data/settings.json** — настройки, **data/records.json** — рекорды очков, **data/ranks.json** — лучшие ранги чартов, **data/wins.json** — пройденные чарты, **data/author_colors.json** — цвета групп авторов, **data/achievements_unlocked.json** — открытые достижения.

### Windows-версия (.exe) и распространение

**Готового Windows-файла .exe пока нет.** В репозитории также нет скрипта сборки исполняемого файла или спецификации PyInstaller. Компиляция или перепаковка распространяемого EXE сейчас недоступна из-за авторских ограничений, установленных автором проекта. Не следует ожидать готовую сборку, пока автор явно не разрешит её и не опубликует сам.

Страница [GitHub Releases](https://github.com/Mistervock/geometry_rythm/releases) может использоваться для объявлений о релизах, но **скачать с неё готовый .exe сейчас нельзя**.

### Авторские права, указание авторства и бесплатные модификации

**Исходный код игры:** © 2026 Mistervock. Все права защищены, кроме ограниченных разрешений, прямо указанных в файле [LICENSE.md](LICENSE.md).

**Музыка:** **«YARARARA (ヤラララ)» — AnythingBecomeMoe, при участии Kasane Teto SV2.** [Официальный музыкальный клип на YouTube](https://www.youtube.com/watch?v=T24rF_x0TmQ). Эта запись указывает автора песни, но сама по себе не означает, что автор игры получил права на распространение музыки или видео. Музыка, видео, персонажи, иллюстрации и другие сторонние материалы остаются под условиями соответствующих правообладателей.

**Создавать модификации можно бесплатно — на условиях [LICENSE.md](LICENSE.md):**
- Игру разрешено скачивать и использовать в личных некоммерческих целях, а также создавать собственные модификации.
- Модификации должны быть доступны всем бесплатно. Запрещено продавать моды, брать плату за скачивание или доступ, размещать их за платной подпиской/пейволлом или продавать наборы с модами.
- Распространяй модификации отдельными файлами (например, JSON-чартами, собственными ресурсами или патчами), для которых нужна копия игры. Не включай в мод исходный код игры, полную копию игры, исполняемый файл или оригинальные сторонние медиа.
- Без предварительного письменного разрешения автора нельзя публиковать полный исходный код игры или его существенные части на других сайтах, в репозиториях или файлообменниках.
- Сохраняй уведомление об авторских правах, указывай **Geometry Rhythm** и ссылку на этот репозиторий. Помечай мод как неофициальный. Нельзя приписывать себе авторство оригинальной игры, выдавать себя за автора проекта или создавать впечатление, что автор одобрил мод.
- Нельзя выдавать изменённую версию за официальный релиз или распространять скомпилированную/перепакованную игру без предварительного письменного разрешения автора.

Это **специальные ограничительные условия использования**, а не стандартная open-source-лицензия. Условия GitHub могут по-прежнему разрешать просмотр и создание форков публичного репозитория внутри GitHub; текст README и эти условия не отключают такую возможность платформы.
