# Geometry Rhythm

<p align="center">
  <strong>A geometric rhythm game inspired by Friday Night Funkin' and Geometry Catcher.</strong><br>
  <a href="#english">English</a> · <a href="#русский">Русский</a>
</p>

<p align="center">
  <strong>Version 0.2 · HD 1280 × 720 · Python / Pygame</strong>
</p>

---

## English

**Geometry Rhythm** is an independent rhythm game where you hit notes across four geometric lanes, build combos, and create charts for your own music.

The project takes inspiration from **Friday Night Funkin'** and the geometric look of **Geometry Catcher**, while adding its own chart editor, custom song metadata, and timeline-based visual events. It is a fan-made project; it is not an official Friday Night Funkin' game and is not affiliated with its creators.

### Highlights

- **HD presentation:** a 1280 × 720 game layout, with an optional scaled fullscreen mode.
- **Four geometric lanes:** each lane has its own colour and shape. The default keys are **D**, **F**, **J**, and **K**.
- **Tap notes and holds:** hit notes in time, hold keys through long notes, build your combo, and aim for higher accuracy.
- **Scoring and health:** timing grades, score multipliers, a 5-point health bar, and a results screen with accuracy and grade.
- **Song browser with previews:** browse tracks and hear short previews; automatic previews can be switched off in Settings.
- **Custom song and chart details:** set a display title and artist for a song, and set a chart author plus a 1–5 star difficulty rating.
- **Chart editor:** place notes with the mouse or record them while the song plays, edit holds, use snapping and undo, and adjust playback speed to make charting easier.
- **Automatic chart generation:** analyse audio with NumPy to create a draft chart that you can correct by hand.
- **Timeline events:** add glitches, flashes, background changes, images, video clips, and heal pickups that can restore health during gameplay.
- **Customisable settings:** key bindings, note speed, audio latency, music and effect volume, fullscreen mode, language, song previews, and media dimming.

### Requirements

- Python
- **pygame** — game window, input, graphics, and audio
- **numpy** — automatic chart generation and alternate-speed playback in the editor
- **opencv-python** — video playback in chart events

All listed packages are included in **requirements.txt**. NumPy and OpenCV support specific features; video events require OpenCV, while auto-charting and alternate editor playback speeds require NumPy.

### Run from source

Install Python and Git, then clone the repository and install the dependencies:

~~~bash
git clone https://github.com/Mistervock/geometry_rythm.git
cd geometry_rythm
python -m pip install -r requirements.txt
python main.py
~~~

On Windows, use **py** instead of **python** if that is the command available on your system.

### Gameplay

A run begins with a short countdown: **3 · 2 · 1 · RYTHM!**

| Action | Controls |
| --- | --- |
| Hit the four lanes | **D**, **F**, **J**, **K** by default |
| Hit a regular note | Press its lane key as it reaches the hit line |
| Hit a hold note | Press at the start and keep holding until the end |
| Pause or resume | **P** or **Esc** |
| Return to the menu from pause | **M** |

The lane keys can be changed in **Settings**. The default health is 5 HP. Missed notes reduce health and break the combo; every 10 combo steps increase the score multiplier, up to **×4**. Releasing a hold too early causes a hold break.

### Songs and charts

Place audio files in **songs/**. Supported formats are **.ogg**, **.mp3**, and **.wav**. The repository includes **game.ogg** as a sample track.

1. Open **Songs** from the main menu.
2. Select a song to view its charts.
3. Choose a chart to play it, or use **Edit** / **New** to change an existing chart or create one.
4. Save chart changes with **Ctrl + S** in the editor.

Charts are saved as JSON files in **data/charts/**. You can create several charts for one song, each with its own name, author, and 1–5 star difficulty.

#### Song and chart metadata

Open a chart in the editor, press **Esc**, and choose **Song Settings**. You can edit:

- **Song title** — the name shown in the song browser instead of the file name.
- **Artist** — the performer or creator credited for the track.
- **Charter** — the author of the selected chart.
- **Difficulty** — a rating from 1 to 5 stars.

Song title and artist are stored as local song metadata; charter and difficulty are stored with the chart. Save the chart after changing chart details.

### Chart editor

The editor works on the song timeline. You can place notes with the mouse while stopped, record them by pressing lane keys during playback, remove notes, and adjust hold lengths with the mouse wheel over a note. The editor keeps an undo history of up to 80 steps.

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
| Lower / raise editor playback speed | **-** / **=** |
| Toggle event-effect preview | **V** |
| Undo | **Ctrl + Z** |
| Save | **Ctrl + S** |
| Rename the chart | **F2** |
| Delete the nearest note | **Delete** or **Backspace** |
| Shift all notes by 10 ms | **[** / **]** |
| Open the editor menu | **Esc** |

Editor playback speeds are **0.5×**, **0.75×**, **1.0×**, and **1.25×**. These affect playback inside the editor, not the actual gameplay speed; changing the rate also changes the audio pitch. NumPy is needed to prepare alternate-speed audio. Speed can also be selected using the buttons in the editor's right-hand panel.

Click the timeline bar to seek. A left click places a note; a right click removes a note. During playback, lane-key presses record notes, and longer presses create holds. In the editor menu, you can save, save and exit, open Song Settings, run Auto Chart, or leave without saving.

### Automatic chart generation

Choose **Auto Chart** in the editor menu. The analyser reads the song through Pygame, examines four frequency ranges, and detects stronger changes in spectral energy. It then applies spacing and density limits; sustained sounds may be converted into hold notes.

- Requires **numpy**.
- Auto Chart replaces the chart's current note list with a generated draft. Save a separate copy first if you need to keep the original.
- Review the result manually. Different mixes and arrangements can require timing, lane, and hold-length corrections.

### Song events

Open a chart in the editor, press **Esc**, and choose **Events**. Events are placed at specific times in the song. The event editor lets you preview the selected event, adjust its properties, copy and paste properties, and duplicate events.

| Event | What it does |
| --- | --- |
| **Glitch** | Distorts the screen with horizontal bands; duration and strength are adjustable. |
| **Flash** | Adds a timed white flash with adjustable fade-in and duration. |
| **Background** | Changes the background colour, with an optional transition back to the original colour. |
| **Image (beta)** | Displays an image behind the lanes; supports fade, pop-in, or movement animation. |
| **Video (beta)** | Plays a video clip with adjustable duration, size, position, fade, and movement. |
| **Heal** | Sends a white pickup down a chosen lane. Hit it with the matching lane key to restore **1 HP** (up to the 5 HP maximum). Missing a heal causes a visual glitch but does not deal health damage. |

Put media files in **images/**. Supported image formats are **.png**, **.jpg**, and **.jpeg**. Supported video formats are **.mp4**, **.webm**, **.mov**, **.avi**, **.mkv**, and **.m4v**. Video playback requires **opencv-python**.

Useful event-editor shortcuts:

| Action | Controls |
| --- | --- |
| Add glitch / flash / image / background / video / heal | **1** / **2** / **3** / **4** / **5** / **6** |
| Select the previous or next event | **Up** / **Down** |
| Move between event fields | **Tab** |
| Change a selected value | **Left** / **Right** (**Shift** changes it faster) |
| Preview the selected event | **P** |
| Fit an image or video to the screen | **F** |
| Set the selected event's time to the current cursor | **C** |
| Restore the original background colour | **R** |
| Copy / paste / duplicate event properties | **Ctrl + C** / **Ctrl + V** / **Ctrl + D** |
| Paste properties to all events of the same type | **Ctrl + Shift + V** |
| Delete an event / leave the editor | **Delete** / **Esc** |

For image and video events, choose a file from the **images/** folder. The **Fit** action scales the selected media to the screen. The Settings menu also includes a control for dimming images and videos displayed behind the lanes.

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

Charts use JSON format version **4**. Time values are measured in milliseconds. **lane** is the note lane from **0** to **3**; **d** is the duration of a hold and is omitted for regular notes. The optional **events** array stores timeline events. Charts can also include a **charter** string and **difficulty** value from **1** to **5**.

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
    { "type": "heal", "t": 8200, "lane": 1, "speed": 170 }
  ]
}
~~~

For a heal event, **lane** is numbered from **1** to **4** (corresponding to the four gameplay lanes), and **speed** is the fall speed as a percentage. Other event types have their own properties. Older charts without charter, difficulty, or events can still use default values for those fields.

### Project structure

~~~text
geometry_rythm/
├── main.py                    # Application entry point
├── requirements.txt           # Python dependencies
├── GeometryRhythm.spec        # PyInstaller build specification
├── core/
│   ├── game.py                # Gameplay, scoring, health, and event playback
│   ├── chart.py               # Notes, chart metadata, JSON loading/saving
│   ├── editor.py              # Chart editor and playback-speed controls
│   ├── autochart.py           # Audio analysis and automatic chart generation
│   ├── events.py              # Timeline events and media helpers
│   ├── events_screen.py       # Event editor
│   ├── song_settings.py       # Song and chart metadata editor
│   ├── display.py             # Window/fullscreen display management
│   ├── stretch.py             # Alternate-speed audio generation for the editor
│   ├── songs.py               # Song, metadata, and chart management
│   ├── settings.py            # Settings persistence
│   └── ...                    # Menus, sound, results, translations, visual effects
├── songs/                     # Audio tracks (includes game.ogg)
├── images/                    # Image and video media for events
└── data/                      # Local charts, settings, records, and caches
~~~

Local generated data includes **data/charts/** for charts, **data/songmeta/** for song titles and artists, **data/songinfo/** for audio-analysis data, **data/cache/speed/** for alternate-speed audio, **data/settings.json** for preferences, and **data/records.json** for records.

### Windows executable

A ready-to-download Windows **.exe** is not currently published in the repository or in GitHub Releases. A PyInstaller specification (**GeometryRhythm.spec**) is included, but for now the documented way to run the game is from source.

---

## Русский

**Geometry Rhythm** — независимая ритм-игра, в которой нужно попадать в ноты на четырёх геометрических дорожках, собирать комбо и создавать собственные чарты для любимой музыки.

Проект вдохновлён **Friday Night Funkin'** и геометрическим стилем **Geometry Catcher**, но развивает собственные идеи: редактор чартов, настройки метаданных треков и визуальные события на временной шкале. Это фан-проект, а не официальная игра Friday Night Funkin'; проект не связан с её создателями.

### Главное

- **HD-графика:** игровое разрешение 1280 × 720 и масштабируемый полноэкранный режим.
- **Четыре геометрические дорожки:** у каждой свой цвет и форма. По умолчанию используются клавиши **D**, **F**, **J**, **K**.
- **Обычные ноты и удержания:** нажимай в такт, держи клавишу до конца длинной ноты, собирай комбо и повышай точность.
- **Счёт и здоровье:** оценки попаданий, множитель очков, шкала здоровья на 5 HP и экран результатов с точностью и оценкой.
- **Предпрослушивание песен:** в списке треков можно слушать короткие фрагменты. Автоматическое предпрослушивание отключается в настройках.
- **Метаданные песен и чартов:** задавай название и автора песни, указывай автора чарта и его сложность от 1 до 5 звёзд.
- **Редактор чартов:** расставляй ноты мышью или записывай их во время проигрывания, редактируй удержания, пользуйся сеткой и отменой действий, меняй скорость воспроизведения для удобства разметки.
- **Автоматическая разметка:** анализируй аудио с помощью NumPy, чтобы создать черновой чарт и затем поправить его вручную.
- **События на временной шкале:** добавляй глюки, вспышки, смену фона, картинки, видео и хиллы, восстанавливающие здоровье во время игры.
- **Настройки:** клавиши, скорость нот, аудиозадержка, громкость музыки и эффектов, полноэкранный режим, язык, предпрослушивание и затемнение медиа.

### Требования

- Python
- **pygame** — окно игры, ввод, графика и звук
- **numpy** — автоматическая разметка и альтернативная скорость воспроизведения в редакторе
- **opencv-python** — воспроизведение видео в событиях чарта

Все перечисленные пакеты указаны в **requirements.txt**. NumPy и OpenCV нужны для отдельных функций: видео требует OpenCV, а авто-разметка и альтернативная скорость воспроизведения в редакторе — NumPy.

### Запуск из исходников

Установи Python и Git, затем клонируй репозиторий, установи зависимости и запусти игру:

~~~bash
git clone https://github.com/Mistervock/geometry_rythm.git
cd geometry_rythm
python -m pip install -r requirements.txt
python main.py
~~~

В Windows, если команда **python** не распознаётся, используй **py**, если эта команда доступна в системе.

### Игровой процесс

Перед началом идёт короткий отсчёт: **3 · 2 · 1 · RYTHM!**

| Действие | Управление |
| --- | --- |
| Попадать по четырём дорожкам | По умолчанию **D**, **F**, **J**, **K** |
| Обычная нота | Нажми клавишу дорожки, когда нота достигнет линии попадания |
| Удержание | Нажми в начале и держи до конца ноты |
| Пауза или продолжение | **P** или **Esc** |
| Вернуться в меню из паузы | **M** |

Клавиши дорожек можно изменить в разделе **«Настройки»**. Начальное здоровье — 5 HP. Пропуск ноты уменьшает здоровье и сбрасывает комбо; каждые 10 комбо повышают множитель очков, максимум — **×4**. Если отпустить удержание слишком рано, удержание будет сорвано.

### Песни и чарты

Помещай аудиофайлы в папку **songs/**. Поддерживаются форматы **.ogg**, **.mp3** и **.wav**. В репозитории есть пример трека — **game.ogg**.

1. Открой раздел **«ПЕСНИ»** в главном меню.
2. Выбери песню, чтобы увидеть список её чартов.
3. Выбери чарт для игры или нажми **«Править»** / **«Новый»**, чтобы отредактировать существующий или создать новый.
4. Сохраняй изменения чарта в редакторе с помощью **Ctrl + S**.

Чарты хранятся как JSON-файлы в **data/charts/**. Для одной песни можно создать несколько чартов; у каждого могут быть собственное название, автор и сложность от 1 до 5 звёзд.

#### Название песни, автор и сложность чарта

Открой чарт в редакторе, нажми **Esc** и выбери **«Настройки песни»**. Там можно изменить:

- **Название песни** — отображается в списке вместо имени аудиофайла.
- **Автор песни** — исполнитель или автор трека.
- **Автор чарта** — человек, который сделал выбранный чарт.
- **Сложность** — от 1 до 5 звёзд.

Название и автор песни сохраняются в локальных метаданных трека. Автор и сложность хранятся вместе с чартом. После изменения данных чарта не забудь его сохранить.

### Редактор чартов

Редактор работает с временной шкалой песни. Когда воспроизведение остановлено, ноты можно ставить мышью; во время проигрывания — записывать клавишами дорожек. Можно удалять ноты и менять длину удержания колёсиком мыши над нотой. История отмены хранит до 80 шагов.

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
| Уменьшить / увеличить скорость воспроизведения в редакторе | **-** / **=** |
| Включить или выключить предпросмотр событий | **V** |
| Отменить действие | **Ctrl + Z** |
| Сохранить | **Ctrl + S** |
| Переименовать чарт | **F2** |
| Удалить ближайшую ноту | **Delete** или **Backspace** |
| Сдвинуть все ноты на 10 мс | **[** / **]** |
| Открыть меню редактора | **Esc** |

В редакторе доступны скорости **0.5×**, **0.75×**, **1.0×** и **1.25×**. Они меняют скорость предпрослушивания внутри редактора, но не скорость самой игры; вместе со скоростью меняется высота звука. Для подготовки аудио с другой скоростью нужен NumPy. Скорость также можно выбрать кнопками в правой панели редактора.

Нажми на верхнюю полосу таймлайна, чтобы переместить курсор. Левая кнопка мыши ставит ноту, правая — удаляет. Во время записи удерживай клавиши дорожек; более длинные нажатия превращаются в удержания. В меню редактора можно сохранить чарт, сохранить и выйти, открыть настройки песни, запустить авто-разметку или выйти без сохранения.

### Автоматическая разметка

Выбери **«АВТО-РАЗМЕТКА»** в меню редактора. Анализатор читает песню средствами Pygame, изучает четыре частотных диапазона и ищет выраженные изменения спектральной энергии. Затем он ограничивает плотность нот и интервалы между ними; длительные звуки могут превращаться в удержания.

- Требуется **numpy**.
- Авто-разметка заменяет текущий список нот сгенерированным черновиком. Если нужно сохранить исходный вариант, заранее сделай копию.
- Проверь результат вручную: в зависимости от сведения и структуры песни могут понадобиться поправки тайминга, дорожек и длины удержаний.

### События песни

Открой чарт в редакторе, нажми **Esc** и выбери **«СОБЫТИЯ»**. События располагаются в конкретные моменты времени. В редакторе можно просматривать выбранное событие, менять его параметры, копировать и вставлять свойства, а также дублировать события.

| Событие | Что делает |
| --- | --- |
| **Глюк** | Искажает экран горизонтальными полосами; можно настроить силу и длительность. |
| **Вспышка** | Создаёт белую вспышку с заданной скоростью появления и длительностью. |
| **Фон** | Меняет цвет фона; можно настроить переход и возврат исходного цвета. |
| **Картинка (бета)** | Показывает изображение под дорожками; доступны резкое появление, плавность и движение. |
| **Видео (бета)** | Показывает ролик с настройками длительности, размера, позиции, плавности и движения. |
| **Хилл** | Белый круг падает по выбранной дорожке. Попади по нему нужной клавишей, чтобы восстановить **1 HP** (не выше максимума 5 HP). Если пропустить хилл, произойдёт визуальный глитч, но здоровье не уменьшится. |

Помещай файлы медиа в **images/**. Поддерживаются изображения **.png**, **.jpg**, **.jpeg** и видео **.mp4**, **.webm**, **.mov**, **.avi**, **.mkv**, **.m4v**. Для воспроизведения видео нужен **opencv-python**.

Полезные клавиши редактора событий:

| Действие | Управление |
| --- | --- |
| Добавить глюк / вспышку / картинку / фон / видео / хилл | **1** / **2** / **3** / **4** / **5** / **6** |
| Выбрать предыдущее или следующее событие | **Up** / **Down** |
| Перейти между полями события | **Tab** |
| Изменить выбранное значение | **Left** / **Right** (**Shift** ускоряет изменение) |
| Просмотреть выбранное событие | **P** |
| Подогнать картинку или видео под экран | **F** |
| Привязать время события к текущему курсору | **C** |
| Вернуть исходный цвет фона | **R** |
| Копировать / вставить / дублировать параметры | **Ctrl + C** / **Ctrl + V** / **Ctrl + D** |
| Вставить параметры во все события того же типа | **Ctrl + Shift + V** |
| Удалить событие / выйти из редактора | **Delete** / **Esc** |

Для событий изображения и видео выбери файл из папки **images/**. Команда **«Подогнать»** вписывает выбранный медиафайл в экран. В настройках игры также есть регулировка затемнения изображений и видео, отображаемых за дорожками.

### Настройки

В меню настроек можно изменять:

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

Чарты используют JSON-формат версии **4**. Время задаётся в миллисекундах. **lane** — дорожка ноты от **0** до **3**, **d** — длительность удержания (у обычной ноты отсутствует). Необязательный массив **events** содержит события таймлайна. Чарт также может хранить строку **charter** и сложность **difficulty** от **1** до **5**.

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
    { "type": "heal", "t": 8200, "lane": 1, "speed": 170 }
  ]
}
~~~

У события типа **heal** поле **lane** нумеруется от **1** до **4** (по порядку игровых дорожек), а **speed** задаёт скорость падения в процентах. У остальных событий собственные параметры. Старые чарты без полей charter, difficulty и events могут загружаться с настройками по умолчанию.

### Структура проекта

~~~text
geometry_rythm/
├── main.py                    # Точка входа
├── requirements.txt           # Зависимости Python
├── GeometryRhythm.spec        # Конфигурация сборки PyInstaller
├── core/
│   ├── game.py                # Игровой процесс, счёт, здоровье и события
│   ├── chart.py               # Ноты, метаданные и JSON-чарты
│   ├── editor.py              # Редактор и управление скоростью воспроизведения
│   ├── autochart.py           # Анализ аудио и авто-разметка
│   ├── events.py              # События таймлайна и медиа
│   ├── events_screen.py       # Редактор событий
│   ├── song_settings.py       # Настройки песни и чарта
│   ├── display.py             # Оконный и полноэкранный режим
│   ├── stretch.py             # Подготовка аудио для скоростей редактора
│   ├── songs.py               # Песни, метаданные и чарты
│   ├── settings.py            # Сохранение настроек
│   └── ...                    # Меню, звук, результаты, переводы, эффекты
├── songs/                     # Музыкальные файлы (включая game.ogg)
├── images/                    # Картинки и ролики для событий
└── data/                      # Локальные чарты, настройки, рекорды и кэш
~~~

К локальным генерируемым данным относятся **data/charts/** (чарты), **data/songmeta/** (названия и авторы песен), **data/songinfo/** (аудиоанализ), **data/cache/speed/** (аудио для альтернативной скорости), **data/settings.json** (настройки) и **data/records.json** (рекорды).

### Windows-версия (.exe)

Готовый для скачивания Windows **.exe** пока не опубликован ни в файлах репозитория, ни в GitHub Releases. В проект добавлен файл сборки PyInstaller (**GeometryRhythm.spec**), но пока рекомендуемый способ запуска — из исходников по инструкции выше.
