"""Дорожки и групповые правки событий (Geometry Rhythm 7.0).

Дорожка — это папка событий (chart.folders) с двумя полями:
  * kind — тип: effects (эффекты), decor (оформление) или custom (свободная, по умолчанию);
  * visible — показывать события дорожки в списке редактора.
Скрытие меняет только редактор: скрытые события играются как обычные.

Групповые правки работают со списком выбранных событий. Если у выбранных значения поля различаются,
common_value() возвращает MIXED (в редакторе это «—»); правка сдвигает или задаёт поле только у выбранных.
Заблокированные события пропускаются, остальные меняются. Модуль не импортирует другие модули проекта,
поэтому его можно подключать из валидации и проверять без pygame.
"""
#-- Импорт
#-- Определения
KINDS = ("effects", "decor", "custom")
DEFAULT_KIND = "custom"
KIND_NAMES = {"effects": "ЭФФЕКТЫ", "decor": "ОФОРМЛЕНИЕ", "custom": "СВОБОДНАЯ"}
MIXED = object()


#-- Дорожки

def new_folder(name):
    return {"name": name, "locked": False, "kind": DEFAULT_KIND, "visible": True}


def next_kind(kind):
    i = KINDS.index(kind) if kind in KINDS else -1
    return KINDS[(i + 1) % len(KINDS)]


def hidden_names(folders):
    return {f["name"] for f in folders if not f.get("visible", True)}


#-- Выбор и значения

def unlocked(events):
    return [e for e in events if not e.get("locked")]


def common_value(events, key):
    """Общее значение поля у всех событий или MIXED, если значения различаются."""
    if not events:
        return MIXED
    first = events[0].get(key)
    return first if all(e.get(key) == first for e in events) else MIXED


def common_fields(kinds, fields_of):
    """Числовые поля, общие для всех типов: диапазон — пересечение диапазонов.

    fields_of(тип) → [(ключ, подпись, lo, hi, шаг)]. Порядок и подписи берутся у первого типа по алфавиту."""
    kinds = sorted(set(kinds))
    if not kinds:
        return []
    per = [fields_of(k) for k in kinds]
    out = []
    for key, label, lo, hi, step in per[0]:
        others = []
        for other in per[1:]:
            row = next((r for r in other if r[0] == key), None)
            if row is None:
                break
            others.append(row)
        else:
            lo2 = max([lo] + [r[2] for r in others])
            hi2 = min([hi] + [r[3] for r in others])
            if lo2 <= hi2:
                out.append((key, label, lo2, hi2, step))
    return out


#-- Групповые правки

def shift_values(events, key, lo, hi, delta):
    """Сдвигает поле на delta у каждого незаблокированного события, в пределах [lo, hi]. Возвращает число изменённых."""
    changed = 0
    for e in unlocked(events):
        new = max(lo, min(hi, e[key] + delta))
        if new != e[key]:
            e[key] = new
            changed += 1
    return changed


def set_values(events, key, value, lo, hi):
    """Задаёт одно значение поля всем незаблокированным событиям. Возвращает число изменённых."""
    free = unlocked(events)
    v = max(lo, min(hi, int(value)))
    for e in free:
        e[key] = v
    return len(free)


def toggle_flag(events, key):
    """Логическое поле: если у всех оно включено — выключает, иначе включает у всех незаблокированных."""
    free = unlocked(events)
    if not free:
        return 0
    target = not all(bool(e.get(key)) for e in free)
    for e in free:
        e[key] = target
    return len(free)


def set_flag(events, key, value):
    """Ставит логический флаг всем выбранным, включая заблокированные (замок снимается этой же правкой)."""
    for e in events:
        e[key] = bool(value)
    return len(events)


def assign_folder(events, folder):
    free = unlocked(events)
    for e in free:
        e["folder"] = folder
    return len(free)


def move_to(events, at, duration):
    """Переносит группу так, чтобы самое раннее из незаблокированных событий оказалось в at."""
    free = unlocked(events)
    if not free:
        return 0
    base = min(e["t"] for e in free)
    for e in free:
        e["t"] = max(0, min(duration, e["t"] + at - base))
    return len(free)


def duplicate_at(events, at, duration):
    """Копии выбранных событий. Самое раннее копируется в at, интервалы между событиями сохраняются."""
    if not events:
        return []
    base = min(e["t"] for e in events)
    copies = []
    for e in events:
        c = dict(e)
        c["t"] = max(0, min(duration, at + e["t"] - base))
        c["locked"] = False
        copies.append(c)
    return copies


def remove_events(all_events, targets):
    """Удаляет незаблокированные из all_events на месте. Возвращает (удалено, пропущено)."""
    drop = {id(e) for e in unlocked(targets)}
    before = len(all_events)
    all_events[:] = [e for e in all_events if id(e) not in drop]
    removed = before - len(all_events)
    return removed, len(targets) - removed
