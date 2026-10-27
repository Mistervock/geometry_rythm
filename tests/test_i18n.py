import ast
import glob
import os
import re

import i18n
import keymap

CYR = re.compile("[А-Яа-яЁё]")
CORE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "core")


def literals_in_t_calls():
    out = {}
    for f in glob.glob(os.path.join(CORE, "*.py")):
        tree = ast.parse(open(f, encoding="utf-8").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "t" and node.args:
                a = node.args[0]
                if isinstance(a, ast.Constant) and isinstance(a.value, str) and CYR.search(a.value):
                    out.setdefault(a.value, os.path.basename(f))
    return out


def test_every_t_literal_has_english():
    missing = {k: v for k, v in literals_in_t_calls().items() if k not in i18n.EN}
    assert not missing, missing


def test_keymap_labels_translated():
    assert [a[2] for a in keymap._RAW if a[2] not in i18n.EN] == []


def test_editor_help_and_history_labels_translated():
    import editor
    import history
    texts = [what for _, what in editor.help_lines()]
    texts += [p[3] for p in editor.LINE_PRESETS]
    for name in dir(history):
        cls = getattr(history, name)
        lab = getattr(cls, "label", None)
        if isinstance(lab, str) and CYR.search(lab):
            texts.append(lab)
    assert [x for x in texts if CYR.search(x) and x not in i18n.EN] == []
