"""Bounded keepsake metadata; gesture progress itself is a local workshop interaction."""
import json
import math

RECIPES = {
    'teddy': dict(steps=['measure', 'cut', 'sew', 'stuff', 'decorate'], size=[24, 30]),
    'pot': dict(steps=['shape', 'glaze', 'decorate'], size=[20, 24]),
    'bracelet': dict(steps=['thread', 'beads', 'decorate'], size=[18, 1]),
    'card': dict(steps=['fold', 'decorate'], size=[15, 20]),
}


def validate(kind, work):
    from .engine import need
    msg = 'Hoàn thành các bước trên bàn thủ công trước khi cất món đồ nhé.'
    if work is None:
        need(kind != 'teddy', msg)
        return
    recipe = RECIPES.get(kind)
    need(recipe is not None and type(work) is dict and set(work) == {'v', 'steps', 'size', 'marks'}, msg)
    need(type(work['v']) is int and work['v'] == 1, msg)
    need(type(work['steps']) is list and work['steps'] == recipe['steps'], msg)
    need(type(work['size']) is list and all(type(n) is int for n in work['size']) and work['size'] == recipe['size'], msg)
    marks = work['marks']
    need(type(marks) is list and 1 <= len(marks) <= 12, msg)
    for mark in marks:
        need(type(mark) is list and len(mark) == 2, msg)
        need(all(type(n) in (int, float) and 0 <= n <= 1 and math.isfinite(n) for n in mark), msg)


def identity(kind, color, pattern, work=None):
    # 0 and 0.0 describe the same position. No client text or arbitrary payload is stored.
    marks = [[round(float(n), 4) for n in p] for p in work['marks']] if work else None
    return kind, color, pattern, json.dumps(marks, separators=(',', ':'))
