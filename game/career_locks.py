"""🔒 Vì sao chưa làm được nghề này (owner 23/10: "nhiều người k biết tại sao mình k đc chơi nghề này nghề kia nữa").

One place that says, in plain words, why a career cannot be picked or worked right now and what opens it, read from
the very rules that refuse it (journey.gate, accounting_jobs.can_work, gov_rules, employment, abroad):

* `why(s, cid)` → None (free to pick and work) or {k, t, how, act?, soft?}: k the kind, t the short line on the card
  ("🔒 Mở ở chương 3"), how what to do, act the client action that helps (accountingSchool, abroad), soft True when
  the switch itself goes through and only the work waits (the job sheet then says the same).
* `public(s)` → {cid: why} for the careers whose reason is not the chapter rule (the picker derives that one from
  journey.unlocked + content unlock_chapter + goals, in the same words: v4/career-pick.js chapterLock, tested by
  tests/test_career_locks.py), so a new player's ~50 chapter locks do not ride on every response.
* `refusal(s, cid)` → the sentence select_career answers with (journey.gate).

Kinds: chapter (its chapter not reached), customs (Hải quan: 3 chapters), cert (kế toán: the exam), gov_ban (khai trừ
khỏi ngành nhà nước: good days elsewhere lift it), entry (Hải quan's other conditions), retry (a failed interview:
the day it takes an application again), abroad (a contract abroad: only that branch opens a shift).
"""
from __future__ import annotations


def _jr():
    from . import journey
    return journey


def _place(cid: str) -> str:
    from .content import CAREER_META
    return CAREER_META.get(cid, {}).get('place', cid)


def _goals_left(s: dict) -> tuple[int, int]:
    """(done, total) of the current chapter's goals."""
    jr = _jr()
    j = s['journey']
    goals = jr._goals_view(jr._context(s), j['chapter'])
    return sum(1 for g in goals if g['done']), len(goals)


def chapter_lock(s: dict, cid: str, progress: tuple[int, int] | None = None) -> dict | None:
    """The chapter rule alone (journey.gate's first need): None once the place is open to this save."""
    jr = _jr()
    from . import accounting_jobs as aj, gov_rules as gvr
    j = s.get('journey') or {}
    if not j.get('story') or cid in j.get('unlocked', ()) or aj.opens(s, cid) or gvr.opens(s, cid) or jr.late_opens(s, cid):
        return None
    ch = int(j.get('chapter') or 1)
    if cid == gvr.HQ_CAREER:
        n, need = gvr.chapters_done(s), gvr.ENTRY['chapters']
        return dict(k='customs', t=f'🔒 Cần xong {need} chương truyện ({min(n, need)}/{need})',
                    how=f'Hải quan nhận hồ sơ khi bạn đã xong {need} chương của nhân vật (đang {min(n, need)}/{need}). '
                        'Sau đó cần làm Công an tới cấp Hạ sĩ trở lên.')
    n = dict((c, k) for k, ids in jr.CH_UNLOCKS.items() for c in ids).get(cid) or jr.LATE_UNLOCKS.get(cid)
    if not n:
        return dict(k='chapter', t='🔒 Chưa mở', how='Nơi này chưa mở trong câu chuyện của bạn.')
    done, total = progress or _goals_left(s)
    if n == ch + 1:
        t = f'🔒 Xong chương {ch} là mở'
        how = f'Làm xong việc cần làm của chương {ch} (đã xong {done}/{total}) là sang chương {n} và mở nơi này.'
    else:
        t = f'🔒 Mở ở chương {n}'
        how = f'Mở khi tới chương {n}; bạn đang ở chương {ch} (đã xong {done}/{total} việc cần làm). Xong việc cần làm của từng chương là đi tiếp.'
    if cid in aj.JOBS:
        how += f' Hoặc thi đạt chứng nhận “{aj._school().course(aj.JOBS[cid])["name"]}” ở Học kế toán để vào làm sớm.'
    return dict(k='chapter', t=t, how=how, **({'act': 'accountingSchool'} if cid in aj.JOBS else {}))


def why(s: dict, cid: str, progress: tuple[int, int] | None = None) -> dict | None:
    """Why `cid` cannot be picked (or, soft, worked) now; None when nothing stands in the way."""
    j = s.get('journey') or {}
    c = (s.get('careers') or {}).get(cid)
    if not isinstance(c, dict):
        return None
    lock = chapter_lock(s, cid, progress)
    if lock:
        return lock
    from . import accounting_jobs as aj
    ok, text = aj.can_work(s, cid)
    if not ok:
        name = aj._school().course(aj.JOBS[cid])['name']
        return dict(k='cert', t=f'🔒 Cần chứng nhận “{name}”', how=text, act='accountingSchool')
    job = c.get('job') if isinstance(c.get('job'), dict) else {}
    from . import employment as emp
    hired = job.get('status') == 'hired'
    if emp.required(cid) and not hired:
        from . import promotion as pm
        if pm.banned(s, cid):
            v = pm.redeem_view(s) or {}
            return dict(k='gov_ban', soft=True, t=f'🔒 Bị khai trừ ngành nhà nước · còn {v.get("left", 0)} ngày tốt để gỡ',
                        how='Bạn đang chịu kỷ luật khai trừ nên Công an, Hải quan chưa nhận hồ sơ. ' + pm.redeem_text(s))
        block = emp.entry_block(s, cid)
        if block:
            return dict(k='entry', soft=True, t='🔒 Chưa đủ điều kiện xét tuyển', how=block)
        retry = emp.retry_view(s, c)
        if retry and not retry['open']:
            return dict(k='retry', soft=True, t=f'⏳ Phỏng vấn lại được từ Ngày {retry["day"]} (còn {retry["left"]} ngày)',
                        how=f'Lần phỏng vấn trước chưa đạt. Nơi này nhận hồ sơ lại {retry["text"]}; '
                            'cứ làm ở nơi khác và khép ca, đủ ngày là xin lại được.')
    if j.get('story'):
        from . import abroad as ab
        w = ab.contract(s)
        if w and w.get('career') != cid:
            d = ab.DEST.get(w.get('to'), {})
            left = max(0, int(w.get('need') or 0) - int(w.get('n') or 0))
            return dict(k='abroad', soft=True, act='abroad', t=f'✈️ Đang làm ở {d.get("city", "nước ngoài")} · còn {left} ngày',
                        how=f'Bạn đang làm ở chi nhánh {d.get("city", "nước ngoài")}, còn {left} ngày nữa: chỉ {_place(w["career"])} mở ca được. '
                            'Làm tiếp ở đó, hoặc về nước sớm ở mục 🌏 Làm việc ở nước ngoài.')
    return None


def public(s: dict, progress: tuple[int, int] | None = None) -> dict:
    """{cid: why} for every reason except the plain chapter one (see the module notes); {} outside the story.
    progress: (done, total) of this chapter's goals, when the caller has them (journey.public)."""
    if not (s.get('journey') or {}).get('story'):
        return {}
    out = {}
    for cid in s.get('careers') or {}:
        w = why(s, cid, progress)
        if w and w['k'] != 'chapter':   # the chapter line: the client says it
            out[cid] = w
    return out


def refusal(s: dict, cid: str) -> str:
    """select_career's answer for a place still shut: the place, why, and what opens it."""
    w = why(s, cid)
    if not w:
        return f'{_place(cid)} chưa mở với bạn.'
    return f'{_place(cid)} chưa mở với bạn. {w["how"]}'
