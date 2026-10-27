"""Встроенные достижения игры и счётчики прогресса.

Это ТА ЖЕ система достижений, а не вторая: полученные достижения хранятся в том же файле
data/achievements_unlocked.json (achievements.unlock), встроенные отличаются только префиксом «gr:».
Старый прогресс и авторские достижения чартов не затрагиваются.

Правила честности:
  * считаются только реальные результаты: проход обычного режима, не проигранный, на чарте от MIN_NOTES нот;
  * практика НЕ засчитывается в достижения за прохождение (ранг, точность, комбо, серии), у неё свои
    достижения и счётчики; результаты практики не попадают ни в рекорды, ни в ранги;
  * получить достижение повторно нельзя (unlock идемпотентен), счётчики только растут;
  * достижения «за создание/редактор» дают только сохранённые в редакторе чарты, а не открытие экрана.
Счётчики начинаются с нуля с момента появления файла data/progress.json — прошлые игры задним числом не
пересчитываются (их результатов нигде не хранилось).
"""
import achievements
import config as C
import jsonio
from i18n import t

PATH = C.root("data", "progress.json")
VERSION = 1
MIN_NOTES = 30                 # короче — слишком легко получить «без промахов»
MIN_EDIT_NOTES = 10
MAX_COUNTER = 10 ** 9

#-- Определения: id, категория, счётчик, цель, (RU имя, RU описание), (EN имя, EN описание)
DEFS = (
    ("first_clear", "play", "finishes", 1, ("Первый финиш", "Пройдите любой чарт до конца."),
     ("First clear", "Finish any chart.")),
    ("clears_25", "play", "finishes", 25, ("Постоянный игрок", "Пройдите 25 чартов до конца."),
     ("Regular", "Finish 25 runs.")),
    ("no_miss", "no_miss", "no_miss_runs", 1, ("Без промахов", f"Пройдите чарт от {MIN_NOTES} нот без единого MISS."),
     ("No miss", f"Finish a chart of {MIN_NOTES}+ notes without a single MISS.")),
    ("no_miss_10", "no_miss", "no_miss_runs", 10, ("Чистая игра", "10 проходов без единого MISS."),
     ("Clean player", "10 runs without a single MISS.")),
    ("full_combo", "combo", "fc_runs", 1, ("Фулл-комбо", "Пройдите чарт без промахов и сорванных удержаний."),
     ("Full combo", "Finish a chart with no misses and no broken holds.")),
    ("full_combo_5", "combo", "fc_runs", 5, ("Мастер комбо", "5 фулл-комбо."), ("Combo master", "5 full combos.")),
    ("rank_a", "rank", "a_ranks", 1, ("Ранг A", "Получите ранг A или выше."), ("Rank A", "Earn rank A or better.")),
    ("rank_s", "rank", "s_ranks", 1, ("Ранг S", "Получите ранг S."), ("Rank S", "Earn rank S.")),
    ("rank_s_5", "rank", "s_charts", 5, ("Пять S", "Получите ранг S на 5 разных чартах."),
     ("Five S", "Earn rank S on 5 different charts.")),
    ("acc_95", "accuracy", "acc95_runs", 1, ("Точность 95%", "Пройдите чарт с точностью 95% и выше."),
     ("95% accuracy", "Finish a chart with 95%+ accuracy.")),
    ("acc_100", "accuracy", "acc100_runs", 1, ("Идеал", "Точность 100%: только PERFECT и все удержания."),
     ("Flawless", "100% accuracy: only PERFECT and every hold.")),
    ("hard_clear", "difficulty", "hard_clears", 1, ("Сложный чарт", "Пройдите чарт сложности 4 или 5."),
     ("Hard clear", "Finish a chart of difficulty 4 or 5.")),
    ("hard_s", "difficulty", "hard_s", 1, ("Эксперт", "Ранг S на чарте сложности 5."),
     ("Expert", "Rank S on a difficulty 5 chart.")),
    ("streak_3", "streak", "best_streak", 3, ("Серия 3", "3 прохода подряд без проигрыша."),
     ("Streak 3", "3 runs in a row without failing.")),
    ("streak_10", "streak", "best_streak", 10, ("Серия 10", "10 проходов подряд без проигрыша."),
     ("Streak 10", "10 runs in a row without failing.")),
    ("editor_save", "editor", "charts_saved", 1, ("Первое сохранение", f"Сохраните чарт от {MIN_EDIT_NOTES} нот в редакторе."),
     ("First save", f"Save a chart of {MIN_EDIT_NOTES}+ notes in the editor.")),
    ("editor_grid", "editor", "grid_saves", 1, ("Ритмичный мастер", "Сохраните чарт, где 20+ нот поставлены по BPM-сетке."),
     ("On the beat", "Save a chart with 20+ notes placed on the BPM grid.")),
    ("editor_export", "editor", "exports", 1, ("Поделиться чартом", "Экспортируйте чарт из редактора."),
     ("Share it", "Export a chart from the editor.")),
    ("create_1", "create", "charts_created", 1, ("Автор", "Создайте и сохраните новый чарт."),
     ("Author", "Create and save a new chart.")),
    ("create_5", "create", "charts_created", 5, ("Плодовитый автор", "Создайте 5 новых чартов."),
     ("Prolific author", "Create 5 new charts.")),
    ("practice_1", "practice", "practice_runs", 1, ("Тренировка", "Завершите проход в режиме практики."),
     ("Training", "Complete a practice run.")),
    ("practice_20", "practice", "practice_runs", 20, ("Усердный ученик", "20 завершённых проходов практики."),
     ("Diligent student", "20 completed practice runs.")),
    ("practice_slow", "practice", "practice_slow_runs", 1, ("Медленно, но верно", "Практика на скорости до 75% с точностью 90%+."),
     ("Slow and steady", "Practice at 75% speed or slower with 90%+ accuracy.")),
)
CATEGORIES = ("play", "no_miss", "combo", "rank", "accuracy", "difficulty", "streak", "editor", "create", "practice")
CATEGORY_NAMES = {
    "play": ("Игра", "Play"), "no_miss": ("Без промахов", "No miss"), "combo": ("Комбо", "Combo"),
    "rank": ("Ранги", "Ranks"), "accuracy": ("Точность", "Accuracy"), "difficulty": ("Сложность", "Difficulty"),
    "streak": ("Серии", "Streaks"), "editor": ("Редактор", "Editor"), "create": ("Создание", "Creating"),
    "practice": ("Практика", "Practice"),
}
GLYPH = {"play": "▶", "no_miss": "✕", "combo": "♪", "rank": "S", "accuracy": "%", "difficulty": "★",
         "streak": "»", "editor": "✎", "create": "+", "practice": "◐"}

NUMERIC = ("finishes", "no_miss_runs", "fc_runs", "a_ranks", "s_ranks", "acc95_runs", "acc100_runs",
           "hard_clears", "hard_s", "streak", "best_streak", "charts_created", "charts_saved", "grid_saves",
           "exports", "practice_runs", "practice_slow_runs", "practice_seconds")


def prefix(ident):
    return "gr:" + ident


def default_state():
    d = {k: 0 for k in NUMERIC}
    d.update({"v": VERSION, "s_chart_keys": [], "created_ids": []})
    return d


def load():
    raw = jsonio.load(PATH, None, expect=dict)
    st = default_state()
    if isinstance(raw, dict):
        for k in NUMERIC:
            v = raw.get(k)
            if isinstance(v, int) and not isinstance(v, bool) and 0 <= v <= MAX_COUNTER:
                st[k] = v
        for k in ("s_chart_keys", "created_ids"):
            v = raw.get(k)
            if isinstance(v, list):
                st[k] = [x for x in v if isinstance(x, str)][:2000]
    st["s_charts"] = len(st["s_chart_keys"])
    st["charts_created"] = max(st["charts_created"], len(st["created_ids"]))
    return st


def save(state):
    out = {k: state[k] for k in NUMERIC}
    out.update({"v": VERSION, "s_chart_keys": state["s_chart_keys"][:2000], "created_ids": state["created_ids"][:2000]})
    jsonio.try_write(PATH, out)


def definitions():
    return DEFS


def display(defn, lang):
    i = 0 if lang == "ru" else 1
    return defn[4 + i][0], defn[4 + i][1]


def category_name(cat, lang):
    return CATEGORY_NAMES[cat][0 if lang == "ru" else 1]


def is_unlocked(ident):
    return achievements.is_unlocked(prefix(ident))


def counter_value(state, defn):
    return min(state.get(defn[2], 0), defn[3])


def _unlock_due(state, lang):
    names = []
    for defn in DEFS:
        if state.get(defn[2], 0) >= defn[3] and achievements.unlock(prefix(defn[0])):
            names.append(display(defn, lang)[0])
    return names


def _lang():
    import settings
    return settings.get("lang")


#-- Уведомления от игры и редактора

def notify(kind, **data):
    """Обновляет счётчики и возвращает названия достижений, полученных прямо сейчас."""
    handler = _HANDLERS.get(kind)
    if handler is None:
        return []
    st = load()
    handler(st, data)
    save(st)
    return _unlock_due(st, _lang())


def _run_finished(st, d):
    ch, out = d["chart"], d["outcome"]
    if out.get("practice"):
        return
    if out.get("failed"):
        st["streak"] = 0
        return
    s = out["stats"]
    st["streak"] += 1
    st["best_streak"] = max(st["best_streak"], st["streak"])
    st["finishes"] += 1
    if s["total"] < MIN_NOTES:
        return
    if s["counts"]["miss"] == 0:
        st["no_miss_runs"] += 1
    if s["full_combo"]:
        st["fc_runs"] += 1
    grade = s["grade"]
    if grade in ("S", "A"):
        st["a_ranks"] += 1
    if grade == "S":
        st["s_ranks"] += 1
        key = ch.key or ch.id or ch.name
        if key not in st["s_chart_keys"]:
            st["s_chart_keys"].append(key)
            st["s_charts"] = len(st["s_chart_keys"])
        if ch.difficulty >= 5:
            st["hard_s"] += 1
    if s["acc"] >= 95:
        st["acc95_runs"] += 1
    if s["acc"] >= 100 and s["holds_broken"] == 0 and s["counts"]["miss"] == 0 and s["counts"]["great"] == 0 \
            and s["counts"]["good"] == 0:
        st["acc100_runs"] += 1
    if ch.difficulty >= 4:
        st["hard_clears"] += 1


def _practice_finished(st, d):
    out = d["outcome"]
    s = out["stats"]
    a, b = out["section"]
    if s["judged"] < 10 or (b - a) < 5000:
        return                                       # слишком короткий отрезок практикой не считается
    st["practice_runs"] += 1
    st["practice_seconds"] = min(MAX_COUNTER, st["practice_seconds"] + int((b - a) / 1000 / max(0.25, out.get("speed", 1.0))))
    if out.get("speed", 1.0) <= 0.75 and s["acc"] >= 90:
        st["practice_slow_runs"] += 1


def _chart_saved(st, d):
    ch = d["chart"]
    if len(ch.notes) < MIN_EDIT_NOTES:
        return
    st["charts_saved"] += 1
    if d.get("snapped_notes", 0) >= 20:
        st["grid_saves"] += 1
    if d.get("new") and ch.id and ch.id not in st["created_ids"]:
        st["created_ids"].append(ch.id)
        st["charts_created"] = len(st["created_ids"])


def _chart_exported(st, d):
    if len(d["chart"].notes) >= MIN_EDIT_NOTES:
        st["exports"] += 1


_HANDLERS = {"run_finished": _run_finished, "practice_finished": _practice_finished,
             "chart_saved": _chart_saved, "chart_exported": _chart_exported}
