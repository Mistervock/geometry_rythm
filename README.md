# Geometry Rhythm

[English](#english) | [Русский](#русский)

## English

**Geometry Rhythm** is a rhythm game built with Python and Pygame. Press the keys in time with the music and hit notes as they reach the judgment line.

The project is inspired by **Friday Night Funkin' (FNF)**, but it is an independent fan-made project and is not an official FNF release.

### Features

- Four note lanes.
- Timing judgments, score, combo, and health.
- Hold notes.
- A chart editor for creating and editing note charts.
- Automatic chart generation using audio analysis.
- Saving charts and settings.

### Gameplay

1. Start the game and select an available song/chart.
2. Watch the notes move toward the judgment line.
3. Press the key for the corresponding lane when a note reaches the line.
4. For hold notes, press and hold the corresponding key until the note ends.
5. Aim for accurate timing to improve your score and combo. Misses may reduce your health.

#### Controls

| Key | Lane |
| --- | --- |
| `D` | Lane 1 |
| `F` | Lane 2 |
| `J` | Lane 3 |
| `K` | Lane 4 |

On-screen hints in the menus and editor may provide additional controls.

### Chart editor

The editor lets you create charts and change note placement for a song. Use the timing grid, scrolling, and zoom controls to place notes accurately. Undo is supported. Save your chart and test it in gameplay.

### Automatic chart generation

The generator analyzes the audio signal and looks for prominent changes or beats to suggest note placement. This is a starting point, not a guaranteed finished chart: results depend on the genre, mix, and structure of the track. Review the timing and adjust the notes in the editor after generation.

### Installation and launch

Python 3 and the project's dependencies are required. Clone the repository:

```bash
git clone https://github.com/Mistervock/geometry_rythm.git
cd geometry_rythm
```

Install the dependencies if the repository contains `requirements.txt`:

```bash
python -m pip install -r requirements.txt
```

Run the game's main file from the project root. On Windows, `py main.py` usually works; on Linux/macOS, use `python3 main.py`. If the entry-point filename differs in the current version, run the appropriate file.

#### Windows (.exe) — coming soon

A standalone **Windows `.exe` build is in development**. Once it is ready, it will be available in this repository's **Releases** section. No ready-to-download `.exe` has been published yet; use the setup instructions above for now.

### Music and charts

The game uses audio files and charts. Supported audio formats depend on the audio backend; the current implementation supports `.ogg`, `.mp3`, and `.wav`. Do not add music to the repository unless you have permission to distribute it. Use your own tracks or audio with a suitable license.

### Technology

- Python
- Pygame
- Audio analysis for chart generation

### Inspiration and copyright

Friday Night Funkin' was one source of inspiration for this rhythm game. The FNF name, characters, music, and other materials belong to their respective rights holders. Third-party assets used in this project must be distributed in accordance with their licenses.

### Project status

The project is under development. Gameplay mechanics and the interface may change as development continues.

---

## Русский

**Geometry Rhythm** — это ритм-игра, в которой нужно попадать по нотам в такт музыке. Проект вдохновлён **Friday Night Funkin' (FNF)** и другими rhythm games, но использует собственную геометрическую подачу и механику.

> Это независимый фан-проект/учебный проект, вдохновлённый жанром. Он не является официальной частью Friday Night Funkin'.

### Особенности

- Четыре дорожки и клавиши для попадания по нотам.
- Оценка точности попаданий, комбо, очки и шкала здоровья.
- Обычные ноты и удерживаемые ноты (hold notes).
- Редактор чартов с сеткой времени, прокруткой, масштабированием и отменой действий.
- Автоматическая генерация чарта на основе аудиоанализа.
- Сохранение чартов и настроек.

### Как играть

1. Запусти игру и выбери доступную песню/чарт.
2. Следи за нотами, которые движутся к линии попадания.
3. Нажимай клавишу соответствующей дорожки, когда нота достигает линии.
4. Для удерживаемой ноты зажми соответствующую клавишу и удерживай её до конца ноты.
5. Старайся попадать как можно точнее: точность влияет на оценку, очки и комбо. Промахи могут уменьшать здоровье.

#### Управление

| Клавиша | Действие |
| --- | --- |
| `D` | Дорожка 1 |
| `F` | Дорожка 2 |
| `J` | Дорожка 3 |
| `K` | Дорожка 4 |

В меню и редакторе подсказки на экране могут уточнять дополнительные действия.

### Редактор чартов

Редактор позволяет создавать и менять расположение нот для песни. Используй временную сетку, прокрутку и масштабирование, чтобы точнее размещать события. Поддерживается отмена последних действий. Сохраняй чарт и затем проверяй его в игровом режиме.

### Автоматическая генерация

Автогенератор анализирует аудиосигнал и ищет выраженные изменения/удары, чтобы предложить расположение нот. Это отправная точка, а не гарантированно готовый чарт: результат зависит от жанра, микса и структуры композиции. После генерации рекомендуется вручную проверить тайминг и поправить ноты в редакторе.

### Установка и запуск

Для запуска нужен Python 3 и зависимости проекта. Клонируй репозиторий:

```bash
git clone https://github.com/Mistervock/geometry_rythm.git
cd geometry_rythm
```

Установи зависимости, если в репозитории есть файл `requirements.txt`:

```bash
python -m pip install -r requirements.txt
```

Затем запусти главный файл игры из корня проекта. На Windows обычно подходит `py main.py`, на Linux/macOS — `python3 main.py`. Если точка входа в текущей версии называется иначе, используй соответствующий файл запуска.

#### Windows (.exe) — скоро

Сборка Geometry Rhythm в отдельный исполняемый файл **`.exe` для Windows находится в разработке**. Когда сборка будет готова, её можно будет скачать из раздела **Releases** этого GitHub-репозитория. Пока готовый `.exe` ещё не опубликован; для запуска используй инструкции выше.

### Данные и музыка

Игра работает с аудиофайлами и чартами. Поддерживаемые форматы аудио зависят от используемого backend; в текущей реализации предусмотрены `.ogg`, `.mp3` и `.wav`. Не добавляй в репозиторий музыку, если у тебя нет права распространять её. Используй собственные треки или аудио с подходящей лицензией.

### Технологии

- Python
- Pygame
- Аудиоанализ для генерации чартов

### Вдохновение и авторские права

Friday Night Funkin' послужила одним из источников вдохновения для идеи ритм-игры. Название, персонажи, музыка и другие материалы FNF принадлежат соответствующим правообладателям. Все сторонние ассеты, использованные в этом проекте, должны распространяться с соблюдением их лицензий.

### Статус проекта

Проект находится в разработке. Механики и интерфейс могут меняться по мере развития.
