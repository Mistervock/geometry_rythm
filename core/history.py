"""История редактирования: команды Undo/Redo.

Каждая значимая операция редактора — объект-команда с методами do() и undo(). История хранит не
полные копии чарта, а только то, что изменила команда (какие ноты добавлены/удалены/сдвинуты),
поэтому расходует мало памяти даже на чартах в десятки тысяч нот.

Правила:
* новая команда очищает ветку Redo;
* несколько команд можно объединить в одну запись: begin("метка") … end() (пакетное редактирование);
* повторные однотипные правки одних и тех же нот за короткое время (перетаскивание, колесо мыши,
  нажатия «сдвиг») сливаются в одну запись по ключу coalesce;
* размер истории ограничен числом записей и суммарной «стоимостью» (числом затронутых объектов);
* «чистое» состояние (после сохранения) помнится как запись на вершине стека — индикатор
  несохранённых изменений остаётся честным и после Undo/Redo.
"""
import bisect
import copy
import time

MAX_COMMANDS = 300
MAX_COST = 600_000           # сумма cost() всех записей: защита от разрастания памяти
COALESCE_WINDOW = 0.8        # секунд между однотипными правками, чтобы слить их в одну


class Command:
    label = ""
    coalesce = None

    def do(self, chart):
        raise NotImplementedError

    def undo(self, chart):
        raise NotImplementedError

    def cost(self):
        return 1

    def merge_with(self, other):
        """Попытка поглотить следующую команду того же вида. True — поглощена."""
        return False


def _insert_sorted(chart, notes):
    if len(notes) <= 8 and len(chart.notes) > 64:
        for n in notes:
            _insort(chart.notes, n)
    else:
        chart.notes.extend(notes)
        chart.sort()


def _insort(lst, note):
    key = (note.t, note.lane)
    lo, hi = 0, len(lst)
    while lo < hi:
        mid = (lo + hi) // 2
        if (lst[mid].t, lst[mid].lane) <= key:
            lo = mid + 1
        else:
            hi = mid
    lst.insert(lo, note)


class AddNotes(Command):
    label = "Добавить ноты"

    def __init__(self, notes):
        self.notes = list(notes)

    def do(self, chart):
        _insert_sorted(chart, self.notes)

    def undo(self, chart):
        drop = {id(n) for n in self.notes}
        chart.notes = [n for n in chart.notes if id(n) not in drop]

    def cost(self):
        return len(self.notes)


class RemoveNotes(Command):
    label = "Удалить ноты"

    def __init__(self, notes):
        self.notes = list(notes)

    def do(self, chart):
        drop = {id(n) for n in self.notes}
        chart.notes = [n for n in chart.notes if id(n) not in drop]

    def undo(self, chart):
        _insert_sorted(chart, self.notes)

    def cost(self):
        return len(self.notes)


class ModifyNotes(Command):
    """Изменение времени, дорожки и/или длительности существующих нот: [(нота, старое, новое)]."""
    label = "Изменить ноты"

    def __init__(self, changes, label=None, coalesce=None):
        self.changes = [(n, tuple(old), tuple(new)) for n, old, new in changes]
        if label:
            self.label = label
        self.coalesce = coalesce

    def _apply(self, chart, which):
        for item in self.changes:
            n, val = item[0], item[which]
            n.t, n.lane, n.dur = val
        chart.sort()

    def do(self, chart):
        self._apply(chart, 2)

    def undo(self, chart):
        self._apply(chart, 1)

    def cost(self):
        return len(self.changes)

    def effective(self):
        return any(old != new for _, old, new in self.changes)

    def merge_with(self, other):
        if not isinstance(other, ModifyNotes) or self.coalesce is None or other.coalesce != self.coalesce:
            return False
        if len(other.changes) != len(self.changes) or any(a[0] is not b[0] for a, b in zip(self.changes, other.changes)):
            return False
        self.changes = [(a[0], a[1], b[2]) for a, b in zip(self.changes, other.changes)]
        return True


class ReplaceNotes(Command):
    """Полная замена набора нот (авто-разметка): хранит старые и новые ноты целиком."""
    label = "Заменить все ноты"

    def __init__(self, before, after):
        self.before = list(before)
        self.after = list(after)

    def do(self, chart):
        chart.notes = list(self.after)
        chart.sort()

    def undo(self, chart):
        chart.notes = list(self.before)
        chart.sort()

    def cost(self):
        return len(self.before) + len(self.after)


class SetEvents(Command):
    """Снимок событий и папок до/после правок (экран событий). Событий немного, снимок дёшев."""
    label = "Изменить события"

    def __init__(self, before, after):
        self.before = copy.deepcopy(before)       # (events, folders)
        self.after = copy.deepcopy(after)

    @staticmethod
    def snapshot(chart):
        return (copy.deepcopy(chart.events), copy.deepcopy(chart.folders))

    def _apply(self, chart, snap):
        chart.events = copy.deepcopy(snap[0])
        chart.folders = copy.deepcopy(snap[1])

    def do(self, chart):
        self._apply(chart, self.after)

    def undo(self, chart):
        self._apply(chart, self.before)

    def cost(self):
        return 5 + len(self.before[0]) + len(self.after[0])

    def effective(self):
        return self.before != self.after


class SetMeta(Command):
    """Метаданные чарта: название, автор чарта, сложность, ачивка, настройки сетки."""
    label = "Изменить свойства чарта"
    FIELDS = ("name", "charter", "difficulty", "achievement", "grid")

    def __init__(self, before, after, label=None, coalesce=None):
        self.before = copy.deepcopy(before)
        self.after = copy.deepcopy(after)
        if label:
            self.label = label
        self.coalesce = coalesce

    @classmethod
    def snapshot(cls, chart):
        return {k: copy.deepcopy(getattr(chart, k)) for k in cls.FIELDS}

    def _apply(self, chart, data):
        for k, v in data.items():
            setattr(chart, k, copy.deepcopy(v))

    def do(self, chart):
        self._apply(chart, self.after)

    def undo(self, chart):
        self._apply(chart, self.before)

    def effective(self):
        return self.before != self.after

    def merge_with(self, other):
        if not isinstance(other, SetMeta) or self.coalesce is None or other.coalesce != self.coalesce:
            return False
        self.after = copy.deepcopy(other.after)
        return True


class Composite(Command):
    def __init__(self, label, commands):
        self.label = label
        self.commands = list(commands)

    def do(self, chart):
        for c in self.commands:
            c.do(chart)

    def undo(self, chart):
        for c in reversed(self.commands):
            c.undo(chart)

    def cost(self):
        return sum(c.cost() for c in self.commands)


class EditHistory:
    def __init__(self, chart, max_commands=MAX_COMMANDS, max_cost=MAX_COST, clock=time.monotonic):
        self.chart = chart
        self.max_commands = max_commands
        self.max_cost = max_cost
        self.clock = clock
        self.undo_stack = []
        self.redo_stack = []
        self.rev = 0                   # растёт при любом изменении содержимого (в том числе Undo/Redo)
        self.saved_token = None        # запись на вершине стека в момент сохранения
        self.force_dirty = False       # чарт новый/восстановлен: «не сохранён», пока не сохранят
        self.listeners = []
        self._group = None
        self._last_time = 0.0
        self._cost = 0

    #-- Состояние

    @property
    def top(self):
        return self.undo_stack[-1] if self.undo_stack else None

    @property
    def dirty(self):
        return self.force_dirty or self.top is not self.saved_token

    def mark_saved(self):
        self.saved_token = self.top
        self.force_dirty = False

    def can_undo(self):
        return bool(self.undo_stack)

    def can_redo(self):
        return bool(self.redo_stack)

    def next_undo_label(self):
        return self.top.label if self.top else ""

    def next_redo_label(self):
        return self.redo_stack[-1].label if self.redo_stack else ""

    def _changed(self, kind):
        self.rev += 1
        for fn in list(self.listeners):
            fn(kind)

    #-- Группы

    def begin(self, label="Пакетная правка"):
        if self._group is None:
            self._group = (label, [])

    def end(self):
        if self._group is None:
            return None
        label, cmds = self._group
        self._group = None
        if not cmds:
            return None
        cmd = cmds[0] if len(cmds) == 1 else Composite(label, cmds)
        self._push(cmd, merge=False, applied=True)
        return cmd

    def cancel_group(self):
        """Откатывает всё, что сделано внутри незавершённой группы."""
        if self._group is None:
            return
        _, cmds = self._group
        self._group = None
        for c in reversed(cmds):
            c.undo(self.chart)
        if cmds:
            self._changed("cancel")

    #-- Выполнение

    def execute(self, cmd, coalesce_window=COALESCE_WINDOW):
        eff = getattr(cmd, "effective", None)
        if eff is not None and not eff():
            return False
        cmd.do(self.chart)
        if self._group is not None:
            self._group[1].append(cmd)
            self._changed("do")
            return True
        self._push(cmd, merge=cmd.coalesce is not None, applied=True, window=coalesce_window)
        return True

    def _push(self, cmd, merge, applied, window=COALESCE_WINDOW):
        now = self.clock()
        top = self.top
        if (merge and top is not None and top is not self.saved_token and not self.redo_stack
                and now - self._last_time <= window and top.merge_with(cmd)):
            self._last_time = now
            self._changed("merge")
            return
        self.redo_stack.clear()
        self.undo_stack.append(cmd)
        self._cost += cmd.cost()
        self._last_time = now
        self._trim()
        self._changed("do")

    def _trim(self):
        while len(self.undo_stack) > 1 and (len(self.undo_stack) > self.max_commands or self._cost > self.max_cost):
            old = self.undo_stack.pop(0)
            self._cost -= old.cost()

    def undo(self):
        if self._group is not None:
            self.end()
        if not self.undo_stack:
            return None
        cmd = self.undo_stack.pop()
        cmd.undo(self.chart)
        self.redo_stack.append(cmd)
        self._cost -= cmd.cost()
        self._last_time = 0.0
        self._changed("undo")
        return cmd

    def redo(self):
        if not self.redo_stack:
            return None
        cmd = self.redo_stack.pop()
        cmd.do(self.chart)
        self.undo_stack.append(cmd)
        self._cost += cmd.cost()
        self._last_time = 0.0
        self._changed("redo")
        return cmd

    def clear(self):
        self.undo_stack.clear()
        self.redo_stack.clear()
        self._cost = 0
        self.saved_token = None
        self._changed("clear")
