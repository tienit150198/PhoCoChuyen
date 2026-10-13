# NPC Career Competition Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development; independent ownership below. Execute continuously; no deploy/push or live database.

**Goal:** Every one of54 careers gets three deterministic NPC peers, earned10-shift competition periods, meaningful recognition and career-specific leadership situations.
**Architecture:** Isolated competition content + state reducer; root engine hooks completed work after fair feedback, settles once at end_day, publishes sanitized state. The existing promotion screen shows competition without changing prior promotion/mastery/org rights. Worker ownership prevents concurrent edits.
**Tech Stack:** Python reducers/PostgreSQL; plain JavaScript/HTML/CSS; pytest/Node/Playwright.

## Concrete interfaces and decisions

```python
# game/career_competition_content.py, no engine/content imports (avoid cycles)
PROFILES[career] = dict(recognizer=str, focus=str, rivals=[dict(id=str,name=str,strength=str)] * 3,
    scenarios=[dict(id=str,title=str,text=str,options=[dict(id=str,label=str,score=int,feedback=str)] * 3)] * 3)
# game/career_competition.py (never directly pays money)
completed(c, career, task, feedback, income=0)  # server task_done; feedback has fair,criteria
close(s, c, career, allow_reward=True, abandoned=False)  # returns bonus/spirit/score/period result; idempotent
public(s, c, career)  # pure; no answer scores/future NPC sequence
validate(c, career)
action(s, c, career, name, payload)  # competition_start {}, competition_answer {option}
```

- c.competition optionalversion1. Existing saves start from now; public read never creates state.
- Completedhook counts only current-day samecareer, actual task object in c.tasks, completed_ids contains id, manual nonplayer jobs. Skip referred outcomes neutrally; accepted failed/cancelled work is penalized at close, never queued unaccepted work. Exact setup/brief activities are excluded.
- Score: fair reviewquality50, mistake-free procedure25, judgment15 only for explicit applicable feedback criteria; teamwork10 only when a leadership case was resolved. Normalize availableweights. Missing evidence is not a perfectscore. Fairfeedback rather than unfair reviewer stars is authoritative.
-10 nonempty manually worked shifts per period; unfinished accepted tasks/abandoned shifts count poor outcomes, empty days give neither progress nor award. Three NPC daily scores are deterministic from career/period/tier, independent of player actions; expose only completed-day totals. Shared ranks for ties.
- Five leagues, successive goodperiod thresholds2/3/4/6 and existingpromotionranks2/3/5/7. Save goodperiod progress; no free promotion of actual jobpost. Cap rewards300/900/2000/5000/10000 per10shiftperiod and10% eligible base manual completionincome (conservative; no bank/loans/capital/staff/gear reward multiplication). Only paid-day completions contribute monetary budget; award itself needs paid-day authorization; denied award isn't replayed later. Pagoda grants cappedspirit and recognition, zero cash.
- Leadershipcase after promotionrank>=3 OR league>=1, onecase per manually worked careerday.3scenarios percareer (assignment/inspection/commendation) rotate; no correctanswers in public state. Selection immutable after answer, persistsreload; correctchoice doesn't create cash. Cases are NPC only.
-Root engine: hook after made=fbk.make_review with made.feedback; dailyclose before income finalization and after promotion; money categorybonus, exactref competition-{careerday}; exclude from ownedfinancial base by passing only completionbase, NOT raw earnings. Pagoda spirit via currentjourney API with ceiling, once.

## Task1: content (content worker)

- [x] Create tests/test_career_competition_content.py; expect import failure, then54 unique profiles/3unique rivals/3scenarios each/valid options/no copied police authority into other professions.
- [x] Create game/career_competition_content.py; author explicit54 contexts from approvedspec and existing module roles; selectNPC names, eachcareer3 authoredmeaningful decisions. Keep localization source in output/career-competition/content-en.json as strings/patterns.
- [x] Run focusedpytest and return contract/examples for garbage/art/laundry/lawyer/police. Commit only ownedfiles.

## Task2: reducer (backend worker)

- [x] Create tests/test_career_competition.py; exercise stale/empty/duplicate/foreign/player jobs, deterministic peers, fair grading,10-shift settlement,5leagues, rewardcaps, no-reward days, pagoda, leadership replay, invalidsave and purepublic. RecordRED before implementation.
- [x] Create game/career_competition.py using interface above. Lists bounded by period/history limits; preserve only needed task evidence. Validator derives aggregate rules and rejects bool-as-int, hidden answerforgery, unknownIDs, wrong sums and periodaward duplication.
- [x] Focusedtests green; informroot exact publicschema and payout fields. Commit only ownedfiles. Don't editengine/content/UI.

## Task3: interface (UI worker)

- [x] Create tests/career_competition.mjs with empty/active/settled/maxleague/locked case/activecase rendering, escaping and no hiddenanswer. RecordRED then implement.
- [x] Create public/js/v4/career-competition.js; mount in public/js/v4/promo.js beside mastery for allreturnpaths. Add isolated rules public/css/promo.css if needed. Work on backend publiccontract; coordinate finalfieldnames. Commands via existing data-command/data-payload dispatcher.
- [x] Show periodprogress, threeNPCnames and standings, actualscore components/evidence, supervisorresult, rewardcap and no-cash pagoda, nextleague requirements and casecontrols. Don't present gear purchase as rankbuying. Englishsource output/career-competition/ui-en.json.
- [x] Node checks; commit only ownedfiles.

## Task4: engine and integration (root)

- [x] tests/test_competition_integration.py RED: realtask completion→close→public roundtrip, oldsave, all54publicprofiles, ten real shifts pay once, reference financial identity.
- [x] Modify game/engine.py imports, task_done, no_tick/dispatch, end_day, public_state/_FOCUS_OWN, validation as agreedinterfaces. Root alone edits engine/globali18n.
- [x] Merge workertranslations, testpack. Real localbrowser openpromotionpanel and answercase with synthetic save,390/1280; verify no clipping and persistentresult. No prod access.
- [x] Independent spec+code review, fix confirmed regressions. Run focusedsuite + mastery/promotion/taskcompat appropriate checks. Recordknownbaselinefailures separately.
- [x] Update checkedplan/specstatus/evidence, localcommit, stoplocalDB. State exactimplemented scope and no deploy.


## Verification record (local, 2026-10-13)

- Initial engine integration RED: 5 tests failed before hooks/dispatcher/payout exclusion existed; fixed by implementation.
- Main reducer/content/engine/mastery/promotion/x3/English run: 143 passed, 1 skipped; one localization failure was the final content wording exported during the run. After merging those54 final strings, localization suite:6 passed. Final focused competition/content/integration/English suite:44 passed.
- Feedback, laundry and pagoda regression:80 passed. Generated task compatibility:10 passed.
- Node: competition UI, mastery UI, promotion title extensions all passed.
- Actual Chromium browser with isolated PostgreSQL:390px and1280px start/answer/reload persisted, exactly3NPC standings, no turn cost or horizontal clipping. DB stopped after completion.
- Independent review found pagoda spirit receipt mismatch near100; fixed with persisted spirit_room witness and actual engine end_day regression tests for99/100. Review also checked reward budget exact margin and denied tenth-day award/no replay.
- Approved quality threshold remains80/100 regardless of NPC rank; rank4 regression ensures recognition and progress are not blocked.
- Known baseline exclusion: tests/test_promotion.py::Saves::test_saves_cross_the_previous_build fails against local _rel1431 with “Bản lưu cần đủ các nghề.” Reproduced from git285e2e63 before this feature in output/career-competition/baseline-285e2e63. Not a new competition regression.
- No push, packaging, deployment, production DB access or player-data migration performed.
