"""Nhóm Cư Dân Phố: the neighbourhood group board (game/board.py, game/board_content.py)."""
import copy
import json
import unittest

from game import board as bd
from game import board_content as C
from game import journey as jr
from game.engine import GameError, apply_action, new_state, public_state, validate_state

NPC = 'milk_tea_npc_01'


def story_state(seed=4242, gender='female'):
    s = new_state()
    jr.enable_story(s, seed)
    s['journey'].update(gender=gender, intro=True)
    s, _ = apply_action(s, 'milk_tea', 'select_career', {})
    s, _ = apply_action(s, 'milk_tea', 'talk', dict(npc=NPC, text='chào'))  # first career action: board exists
    return s


def beats(s, n):
    """n career actions' worth of neighbourhood time (engine.apply_action calls board.after the same way)."""
    for _ in range(n):
        bd.after(s, 'milk_tea', 'talk', {})


def next_day(s, n=1, per_day=40):
    for _ in range(n):
        s['journey']['life_day'] += 1
        beats(s, per_day)


def board(s):
    return s['journey']['board']


def act(s, _action, **p):
    return apply_action(s, 'milk_tea', _action, p)


class Generation(unittest.TestCase):
    def test_same_seed_same_board(self):
        a, b = story_state(7), story_state(7)
        next_day(a, 4)
        next_day(b, 4)
        self.assertEqual(json.dumps(board(a), sort_keys=True, ensure_ascii=False), json.dumps(board(b), sort_keys=True, ensure_ascii=False))
        c = story_state(8)
        next_day(c, 4)
        self.assertNotEqual([p['text'] for p in board(a)['posts']], [p['text'] for p in board(c)['posts']])

    def test_first_day_welcome_then_posts_arrive_with_play(self):
        s = story_state()
        first = board(s)['posts']
        self.assertEqual(first[0]['key'] and first[0]['who'], 'co_lua')
        self.assertIn(s['name'], first[0]['text'])
        before = len(board(s)['posts']) + sum(len(p['cmts']) for p in board(s)['posts'])
        beats(s, 30)
        after = len(board(s)['posts']) + sum(len(p['cmts']) for p in board(s)['posts'])
        self.assertGreater(after, before + 8)

    def test_volume_three_to_seven_posts_a_day(self):
        s = story_state(99)
        next_day(s, 30)
        per_day = {}
        for p in board(s)['posts']:
            if p['kind'] == 'daily':
                per_day[p['day']] = per_day.get(p['day'], 0) + 1
        full = [d for d in per_day if d > 1]
        self.assertTrue(full)
        for d in full:
            self.assertTrue(3 <= per_day[d] <= 7, (d, per_day[d]))
        self.assertGreaterEqual(sum(per_day.values()) / len(per_day), 4)

    def test_neighbours_talk_to_each_other_in_character(self):
        s = story_state(5)
        next_day(s, 6)
        threads = [p for p in board(s)['posts'] if p['who'] != 'player']
        lively = [p for p in threads if len({c['who'] for c in p['cmts']}) >= 3]
        self.assertGreaterEqual(len(lively), len(threads) // 2)
        cast = set(C.CAST)
        for p in threads:
            self.assertIn(p['who'], cast)
            for c in p['cmts']:
                self.assertIn(c['who'], cast)
                self.assertEqual(c['mode'], 'auth')
        # Terse and talkative residents sound like themselves.
        texts = {w: [c['text'] for p in threads for c in p['cmts'] if c['who'] == w] for w in ('minh_quan', 'ba_tam')}
        if texts['minh_quan']:
            self.assertLessEqual(max(len(x) for x in texts['minh_quan']), 80)
        if texts['ba_tam']:
            self.assertGreater(max(len(x) for x in texts['ba_tam']), 120)

    def test_cast_and_content_are_complete(self):
        self.assertGreaterEqual(len(C.CAST), 18)
        tempers = {p['temper'] for p in C.CAST.values()}
        for t in ('warm', 'cold', 'tsundere', 'gossip', 'joker', 'grumpy', 'genz', 'knowitall', 'shy', 'drama', 'practical',
                  'showoff', 'official', 'kid', 'judge', 'camera', 'superstitious', 'beer', 'tigermom', 'suspicious', 'optimist'):
            self.assertIn(t, tempers)
            self.assertIn(t, C.REPLY)
            self.assertIn(t, C.FLOAT)
        self.assertEqual({p['verbosity'] for p in C.CAST.values()}, {'terse', 'normal', 'talker'})
        for jid in jr.CAST:
            if jid in C.CAST:
                self.assertEqual(C.CAST[jid]['name'], jr.CAST[jid]['name'])
        for th in C.THREADS + [C.WELCOME] + list(C.CONTEXT.values()) + list(C.LIFE.values()):
            self.assertIn(th['who'], C.CAST, th['key'])
            for who, _, _ in th['comments']:
                self.assertIn(who, C.CAST, th['key'])
        self.assertGreaterEqual(len(C.THREADS), 40)


class PlayerPosts(unittest.TestCase):
    def test_post_gets_in_character_replies(self):
        s = story_state()
        s, r = act(s, 'bd_post', text='Hôm nay mình buồn quá, làm sai hoài bị chủ quán la 😢')
        self.assertEqual(r['intent'], 'sad')
        post = bd._find(board(s), r['post'])
        self.assertEqual(post['who'], 'player')
        self.assertTrue(2 <= len(post['cmts']) <= 3)
        self.assertEqual(len(r['replies']), len(post['cmts']))
        first = C.CAST[post['cmts'][0]['who']]['temper']
        self.assertIn(first, C.INTENT_TEMPERS['sad'][:4])
        for c in post['cmts']:
            self.assertEqual(c['mode'], 'scripted')
            self.assertNotIn('{', c['text'])
        self.assertGreater(sum(post['react'].values()), 0)
        validate_state(s)

    def test_intents(self):
        self.assertEqual(bd.classify('Ai biết chỗ sửa xe gần đây không ạ?'), 'ask')
        self.assertEqual(bd.classify('Cho mình mượn cái thang với'), 'help')
        self.assertEqual(bd.classify('Mình vừa được lên lương, vui quá!'), 'happy')
        self.assertEqual(bd.classify('Bạn ơi đi chơi không'), 'any')
        self.assertEqual(bd.classify('Nhà ai hát karaoke ồn quá'), 'complain')

    def test_mention_gets_that_neighbour_first(self):
        s = story_state()
        s, r = act(s, 'bd_post', text='@Chú Tư ơi cái quạt nhà con kêu cạch cạch, chú coi giùm được không')
        self.assertEqual(r['replies'][0]['who'], 'chu_tu')
        post = bd._find(board(s), r['post'])
        self.assertEqual(post['to'], ['chu_tu'])
        self.assertEqual(bd.mentions('@quan @ba tam hi @Cô Hai Loa'), ['minh_quan', 'ba_tam', 'co_hai_loa'])

    def test_reply_in_a_thread_and_mention(self):
        s = story_state()
        beats(s, 10)
        post = next(p for p in board(s)['posts'] if p['who'] != 'player')
        s, r = act(s, 'bd_reply', post=post['id'], text='Cảm ơn cô nhiều ạ!')
        post = bd._find(board(s), post['id'])
        mine = [c for c in post['cmts'] if c['who'] == 'player']
        self.assertEqual(mine[-1]['text'], 'Cảm ơn cô nhiều ạ!')
        self.assertEqual(r['replies'][0]['who'], post['who'])  # the author answers
        s, r = act(s, 'bd_reply', post=post['id'], text='@Bé Tí em ơi mai đi đá bóng không')
        self.assertEqual(r['replies'][0]['who'], 'be_ti')

    def test_reactions_toggle(self):
        s = story_state()
        pid = board(s)['posts'][0]['id']
        base = dict(bd._find(board(s), pid)['react'])
        s, _ = act(s, 'bd_react', post=pid, r='heart')
        self.assertEqual(bd._find(board(s), pid)['react']['heart'], base['heart'] + 1)
        s, _ = act(s, 'bd_react', post=pid, r='haha')
        p = bd._find(board(s), pid)
        self.assertEqual((p['mine'], p['react']['heart'], p['react']['haha']), ('haha', base['heart'], base['haha'] + 1))
        s, _ = act(s, 'bd_react', post=pid, r='haha')
        self.assertEqual(bd._find(board(s), pid)['react'], base)
        with self.assertRaises(GameError):
            act(s, 'bd_react', post=pid, r='love')

    def test_moderation_privacy_and_limits(self):
        s = story_state()
        with self.assertRaises(GameError):
            act(s, 'bd_post', text='đm cả hẻm')
        with self.assertRaises(GameError):
            act(s, 'bd_post', text='x' * 501)
        with self.assertRaises(GameError):
            act(s, 'bd_post', text='   ')
        s, r = act(s, 'bd_post', text='Ai cần gia sư gọi mình 0912345678 hoặc mail a@b.com')
        text = bd._find(board(s), r['post'])['text']
        self.assertNotIn('0912345678', text)
        self.assertNotIn('a@b.com', text)
        for i in range(bd.PLAYER_DAY_MAX - 1):
            s, _ = act(s, 'bd_post', text=f'Bài thử số {i}')
        with self.assertRaises(GameError):
            act(s, 'bd_post', text='một bài nữa')

    def test_server_only_commands(self):
        s = story_state()
        beats(s, 5)
        p = board(s)['posts'][0]
        with self.assertRaises(GameError):
            act(s, 'bd_voice', lines=[dict(post=p['id'], cmt='c1', canonical='x', text='y')])
        with self.assertRaises(GameError):
            act(s, 'bd_npc', post=p['id'], who='ba_tam', text='hi')

    def test_voice_only_rewrites_the_same_scripted_line(self):
        s = story_state()
        s, r = act(s, 'bd_post', text='Mình mới chuyển tới, chào cả nhà!')
        rep = r['replies'][0]
        job = bd.voice_job(s, rep['post'], rep['cmt'])
        self.assertEqual(job['said'], 'Mình mới chuyển tới, chào cả nhà!')
        s, out = apply_action(s, None, 'bd_voice', dict(lines=[dict(post=rep['post'], cmt=rep['cmt'], canonical=job['canonical'], text='Chào con nha!')]), internal=True)
        self.assertEqual(out['voiced'], 1)
        c = next(c for c in bd._find(board(s), rep['post'])['cmts'] if c['id'] == rep['cmt'])
        self.assertEqual((c['mode'], c['text'], c['canonical']), ('ai', 'Chào con nha!', job['canonical']))
        s, out = apply_action(s, None, 'bd_voice', dict(lines=[dict(post=rep['post'], cmt=rep['cmt'], canonical=job['canonical'], text='Lần hai')]), internal=True)
        self.assertEqual(out['voiced'], 0)
        self.assertIsNone(bd.voice_job(s, rep['post'], rep['cmt']))
        validate_state(s)


class Rumours(unittest.TestCase):
    def test_rumours_come_every_few_days_from_real_facts(self):
        from game import archive as ar
        s = story_state(31)
        s['careers']['grocery']['started'] = True
        seen = []
        with ar.collect() as box:  # the save keeps the newest posts; older ones are archived
            for _ in range(30):
                s['journey']['life_day'] += 1
                beats(s, 75)
                bd.after(s, 'grocery', 'talk', {})
        posts = [r for _, kind, r in box.rows if kind == 'board.posts'] + board(s)['posts']
        rum = [p for p in posts if p['kind'] == 'rumour']
        self.assertGreaterEqual(len(rum), 4)
        days = sorted(p['day'] for p in rum)
        self.assertTrue(all(b - a >= bd.RUMOUR_GAP for a, b in zip(days, days[1:])))
        for p in rum:
            self.assertIn(p['who'], C.GOSSIPS)
            self.assertIn(p['rumour']['fact'], ('late', 'multi', 'money', 'van', 'debt'))
            roles = {C.CAST[c['who']]['temper'] for c in p['cmts']}
            self.assertTrue(roles & {'warm', 'tsundere', 'genz'}, 'someone defends the player')
            seen.append(p['rumour']['fact'])
        self.assertTrue(set(seen) & {'late', 'multi'})

    def test_player_answers_a_rumour(self):
        for tone, who in (('clarify', 'camera'), ('joke', 'joker'), ('confront', 'camera'), ('ignore', 'optimist')):
            s = story_state()
            key = bd.on_rumour(s, 'late')
            self.assertTrue(key)
            beats(s, 8)
            post = next(p for p in board(s)['posts'] if p['kind'] == 'rumour')
            s, r = act(s, 'bd_reply', post=post['id'], tone=tone)
            post = bd._find(board(s), post['id'])
            self.assertEqual(post['rumour']['state'], tone)
            self.assertEqual(any(c['who'] == 'player' for c in post['cmts']), tone != 'ignore')
            self.assertEqual(C.CAST[r['replies'][0]['who']]['temper'], who)
            if tone == 'confront':
                self.assertIn('@' + C.CAST[post['rumour']['by']]['name'], next(c['text'] for c in post['cmts'] if c['who'] == 'player'))
            with self.assertRaises(GameError):
                act(s, 'bd_reply', post=post['id'], tone='joke')
            validate_state(s)

    def test_free_text_in_a_rumour_thread(self):
        s = story_state()
        bd.on_rumour(s, dict(kind='multi'))
        beats(s, 6)
        post = next(p for p in board(s)['posts'] if p['kind'] == 'rumour')
        by = C.CAST[post['rumour']['by']]['name']
        s, r = act(s, 'bd_reply', post=post['id'], text=f'@{by} có gì cô hỏi thẳng con nha')
        self.assertEqual((r['tone'], bd._find(board(s), post['id'])['rumour']['state']), ('confront', 'confront'))

    def test_hooks_for_the_life_layer(self):
        s = story_state()
        self.assertTrue(bd.on_life_event(s, dict(kind='heartbreak')))
        self.assertTrue(bd.on_life_event(s, dict(kind='unknown_kind', text='Hôm nay hẻm mình có chuyện vui.', who='chi_mai')))
        self.assertIsNone(bd.on_life_event(s, dict(kind='bullied')))  # LIFE_PER_DAY
        self.assertTrue(bd.on_life_event(s, dict(kind='rumour', fact='late')))
        self.assertTrue(bd.on_rumour(s, dict(kind='whatever', text='Nghe đâu dạo này hay đi đâu đó…', who='thim_bay')))
        beats(s, 12)
        kinds = [p['kind'] for p in board(s)['posts']]
        self.assertEqual(kinds.count('life'), 2)
        self.assertEqual(kinds.count('rumour'), 2)
        custom = next(p for p in board(s)['posts'] if p['kind'] == 'rumour' and p['who'] == 'thim_bay' and 'hay đi đâu' in p['text'])
        self.assertEqual(custom['rumour']['fact'], 'custom')
        validate_state(s)

    def test_board_reacts_to_the_game(self):
        s = story_state()
        s['journey']['chapter'] = 2
        s['journey']['done'] = [1]
        beats(s, 3)
        ctx = [p for p in board(s)['posts'] if p['kind'] == 'ctx']
        self.assertEqual(len(ctx), 1)
        self.assertIn('Chuyển tới khu phố', ctx[0]['text'])
        beats(s, 3)
        self.assertEqual(len([p for p in board(s)['posts'] if p['kind'] == 'ctx']), 1)  # once

    def test_effect_note_when_a_rumour_arrives(self):
        s = story_state()
        bd.on_rumour(s, 'money')
        result = {}
        for _ in range(3):
            bd.after(s, 'milk_tea', 'talk', result)
        self.assertTrue(any('bàn tán' in x for x in result.get('effects', [])))


class Limits(unittest.TestCase):
    def test_caps_hold_over_many_days(self):
        s = story_state(3)
        for d in range(70):
            next_day(s, 1, per_day=35)
            if d % 3 == 0:
                s, _ = act(s, 'bd_post', text=f'Ngày {d}: ai đi chợ chung không?')
        b = board(s)
        self.assertLessEqual(len(b['posts']), bd.POSTS_MAX)
        self.assertEqual(len(b['posts']), bd.POSTS_MAX)
        self.assertTrue(all(len(p['cmts']) <= bd.CMTS_MAX for p in b['posts']))
        self.assertLessEqual(len(b['queue']), bd.QUEUE_MAX)
        self.assertLess(len(json.dumps(b, ensure_ascii=False)), 400_000)
        validate_state(s)
        view = bd.public(s)
        self.assertEqual(len(view['posts']), bd.VIEW_LIMIT)
        older = bd.public(s, before=view['posts'][-1]['seq'])
        self.assertTrue(older['posts'] and older['posts'][0]['seq'] < view['posts'][-1]['seq'])

    def test_a_long_absence_only_fills_the_last_days(self):
        s = story_state()
        s['journey']['life_day'] += 50
        beats(s, 1)
        days = {p['day'] for p in board(s)['posts']}
        self.assertLessEqual(len(days), 1 + bd.CATCHUP_DAYS)
        validate_state(s)

    def test_story_off_stays_quiet(self):
        s = new_state()
        s, _ = apply_action(s, 'milk_tea', 'select_career', {})
        for _ in range(4):
            s, _ = act(s, 'talk', npc=NPC, text='chào')
        beats(s, 300)
        b = board(s)
        self.assertEqual({p['day'] for p in b['posts']}, {1})
        self.assertLessEqual(len(b['posts']), 4)
        self.assertFalse([p for p in b['posts'] if p['kind'] in ('rumour', 'ctx')])
        s['journey'].update(chapter=2, done=[1])
        beats(s, 3)
        self.assertFalse([p for p in b['posts'] if p['kind'] == 'ctx'])
        validate_state(s)

    def test_validate_rejects_tampering(self):
        s = story_state()
        beats(s, 5)
        for mutate in (lambda b: b['posts'][0].update(who='hacker'),
                       lambda b: b['posts'][0]['react'].update(heart=-1),
                       lambda b: b['posts'][0].update(text='x' * 900),
                       lambda b: b.update(extra=1),
                       lambda b: b['posts'].extend(copy.deepcopy(b['posts'][:1])),
                       lambda b: b['queue'].append(dict(k='post')),
                       lambda b: b.update(day=b['day'] + 5)):
            t = copy.deepcopy(s)
            mutate(board(t))
            with self.assertRaises(GameError):
                validate_state(t)

    def test_older_saves_get_a_board_without_retro_posts(self):
        s = story_state()
        s['journey'].pop('board')
        s['journey']['chapter'] = 3
        s['journey']['done'] = [1, 2]
        s, _ = act(s, 'talk', npc=NPC, text='chào')
        self.assertFalse([p for p in board(s)['posts'] if p['kind'] == 'ctx'])
        validate_state(s)

    def test_public_state_summary_and_unread(self):
        s = story_state()
        beats(s, 20)
        v = public_state(s)['board']
        self.assertGreater(v['unread'], 0)
        self.assertEqual(v['rev'], board(s)['seq'])
        self.assertTrue(v['latest']['name'])
        s, _ = act(s, 'bd_seen')
        self.assertEqual(public_state(s)['board']['unread'], 0)
        s, r = act(s, 'bd_post', text='Chào cả nhà nha')
        self.assertEqual(public_state(s)['board']['unread'], len(r['replies']))


class AIGuard(unittest.TestCase):
    def test_length_follows_verbosity(self):
        long = 'Trời ơi con ơi. Bà nói nghe nè. Hồi xưa bà cũng vậy. Rồi cũng qua thôi. Ăn cơm chưa con. Mai qua bà. Bà nấu chè. Thương lắm.'
        text, why = bd.guard(long, set(), 'ba_tam')
        self.assertIsNone(why)
        self.assertEqual(len([x for x in text.split('.') if x.strip()]), 6)
        text, why = bd.guard('ok. để mình xem. mai sửa.', set(), 'minh_quan')
        self.assertEqual(text, 'ok.')
        text, why = bd.guard('Quân: ừ.', set(), 'minh_quan')
        self.assertEqual(text, 'ừ.')

    def test_guard_rejects_unsafe_lines(self):
        self.assertEqual(bd.guard('Bà cho con 5000 xu nha.', set(), 'ba_tam')[1], 'new_numeric_claim')
        self.assertEqual(bd.guard('Tôi là AI nên không biết.', set(), 'chu_tu')[1], 'breaks_character')
        self.assertEqual(bd.guard('Chú đã chuyển khoản cho con rồi.', set(), 'chu_tu')[1], 'state_claim')
        text, _ = bd.guard('Xem ở http://x.example nha con.', set(), 'ba_tam')
        self.assertNotIn('http', text or '')

    def test_prompt_keeps_the_player_name_and_contacts_out(self):
        s = story_state()
        s, _ = act(s, 'settings', name='Ngọc Lan')
        s, r = act(s, 'bd_post', text='Ngọc Lan đây, ai cần gì gọi 0912345678 nha')
        job = bd.voice_job(s, r['post'], r['replies'][0]['cmt'])
        msgs = bd.ai_messages(s, job)
        blob = json.dumps(msgs, ensure_ascii=False)
        self.assertNotIn('Ngọc Lan', blob)
        self.assertNotIn('0912345678', blob)
        self.assertIn('player_says', msgs[1]['content'])
        en = bd.ai_messages(s, job, 'en')[0]['content']
        self.assertIn('English', en)

    def test_prompt_has_attitude_for_mapped_tempers(self):
        from game import spice
        s = story_state()
        for who, p in C.CAST.items():
            job = dict(kind='npc', post='p-x', cmt=None, who=who, canonical='👍', said='',
                       thread=dict(author='Bà Tám', text='Chiều nay cúp điện nha cả nhà.', rumour=False, comments=[]))
            system = bd._system(s, job, 'vi')
            arch = spice.BOARD_TEMPER_TO_ARCH.get(p['temper'])
            if arch:
                self.assertIn('THÁI ĐỘ', system, who)
                self.assertIn('KHÔNG xéo CON NGƯỜI', system, who)
                if p['age'] < 16:
                    self.assertIn('Học sinh tan học', system, who)
            else:
                self.assertIn(p['temper'], ('cold', 'shy'))
                self.assertNotIn('THÁI ĐỘ', system, who)
        self.assertIn(bd._arch_of('ba_tam')[0], spice.ARCHETYPES)
        self.assertEqual(bd._arch_of('be_na')[1]['slang'], 0)  # a seven-year-old keeps it mild
        from unittest.mock import patch
        with patch.dict('os.environ', {'AI_SPICE': '0'}):
            self.assertNotIn('THÁI ĐỘ', bd._system(s, dict(job, who='ba_tam'), 'vi'))

    def test_guard_rejects_looks_and_rude_pronouns(self):
        self.assertEqual(bd.guard('Nhìn nhà quê ghê con.', set(), 'ba_tam')[1], 'unsafe')
        self.assertEqual(bd.guard('Tao nói rồi mà.', set(), 'chu_tu')[1], 'rude_pronoun')
        self.assertIsNone(bd.guard('Sáng giờ bị bom hàng hai đơn, mệt chết đi được.', set(), 'tung_tun')[1])


if __name__ == '__main__':
    unittest.main()


# ---------------------------------------------------------------- life layer -> board (game/life.py → board.on_life_log)
from game import invest as iv  # noqa: E402
from game import life as lf  # noqa: E402
from game.life_content import FACTS, GOSSIPS, HARD  # noqa: E402


def life_state(seed=4242, gender='female', wallet=200):
    s = story_state(seed, gender)
    s['journey']['wallet'] = wallet
    s['journey']['life_day'] = 8
    beats(s, 3)
    iv.migrate(s)
    lf.migrate(s)
    s['journey']['life']['day'] = 8
    validate_state(s)
    return s


def fire(s, hid, gossip=None):
    L = s['journey']['life']
    card = lf._fire_hard(s, L, lf.HARD_INDEX[hid], 8, 'milk_tea', gossip=gossip)
    L['pending'] = card
    return card


def choose(s, *choices):
    """Answer the pending life card through the real command (lf_choose → validate_state)."""
    for c in choices:
        card = s['journey']['life']['pending']
        s, _ = lf.action(s, 'lf_choose', dict(id=card['id'], choice=c))
    return s


def life_posts(s):
    return [p for p in board(s)['posts'] if p['kind'] in ('life', 'rumour')]


class LifeWiring(unittest.TestCase):
    def test_gossips_are_the_life_layers_gossips(self):
        self.assertEqual(set(C.GOSSIPS), set(GOSSIPS))
        for gid, g in GOSSIPS.items():
            self.assertEqual((C.CAST[gid]['name'], C.CAST[gid]['emoji']), (g['name'], g['emoji']))
        for fact, openers in C.RUMOUR_OPEN.items():
            self.assertEqual(set(openers), set(C.GOSSIPS), fact)
        self.assertEqual(set(C.LIFE_FACT), set(FACTS))
        self.assertLessEqual(set(C.LIFE_FACT.values()), set(C.RUMOUR_OPEN))
        for tone in ('clarify', 'joke'):
            self.assertLessEqual(set(C.RUMOUR_OPEN), set(C.RUMOUR_TONES[tone]['text']), tone)
        # Innuendo only: nothing explicit in what the gossips say.
        explicit = ('mai dam', 'ban dam', 'gai goi', 'ngu voi', 'sex', 'khach lang', 'di khach', 'bao nuoi')
        for openers in C.RUMOUR_OPEN.values():
            for line in openers.values():
                self.assertFalse([w for w in explicit if w in bd._fold(line)], line)

    def test_scam_warning_then_the_collection_thread(self):
        s = life_state()
        card = fire(s, 'lu_bank')
        self.assertEqual(card['stage'], 'react')
        react = next(c['id'] for c in lf.HARD_INDEX['lu_bank']['choices'] if c['money'] >= 0)
        s = choose(s, react)
        card = s['journey']['life']['pending']
        if card['stage'] != 'gop' or not card['gop']['rows']:
            self.skipTest('this seed brings a gift/comfort instead of a collection')
        rows = card['gop']['rows']
        s = choose(s, 'take')
        beats(s, 12)
        warn = next(p for p in life_posts(s) if p['who'] == 'anh_tam')
        self.assertIn('giả nhân viên ngân hàng', warn['text'])
        self.assertNotIn(s['name'], warn['text'])                       # no names in the warning
        gop = next(p for p in life_posts(s) if p['who'] == 'co_lua' and 'Quỹ' in p['text'])
        for r in rows:
            self.assertIn(f'{C.CAST[r["who"]]["name"]} {r["amount"]} xu', gop['text'])
        self.assertIn(f'tổng {sum(r["amount"] for r in rows)} xu', gop['text'])
        self.assertTrue({c['who'] for c in gop['cmts']} & {r['who'] for r in rows})
        validate_state(s)

    def test_declining_the_collection_is_said_on_the_board(self):
        for seed in range(1, 40):
            s = life_state(seed)
            fire(s, 'lu_invest')
            s = choose(s, next(c['id'] for c in lf.HARD_INDEX['lu_invest']['choices'] if c['money'] >= 0))
            card = s['journey']['life']['pending']
            if card and card['stage'] == 'gop' and card['gop']['rows']:
                break
        else:
            self.fail('no collection in 40 seeds')
        s = choose(s, 'thanks')
        beats(s, 15)
        gop = next(p for p in life_posts(s) if 'Quỹ' in p['text'])
        self.assertIn(C.GOP_DECLINED, [c['text'] for c in gop['cmts']])

    def test_rumour_thread_piles_on_defends_and_advises(self):
        s = life_state()
        fire(s, 'dd_late_1', gossip='co_hai_loa')
        s = choose(s, 'ignore')
        card = s['journey']['life']['pending']
        adviser = None
        if card and card['stage'] == 'comfort':
            adviser = next(k['who'] for k in lf.COMFORT if k['id'] == card['comfort'])
            s = choose(s, 'yes')
        beats(s, 12)
        post = next(p for p in life_posts(s) if p['kind'] == 'rumour')
        self.assertEqual((post['who'], post['rumour']), ('co_hai_loa', dict(fact='late', state='open', by='co_hai_loa')))
        self.assertIn('phố đêm', post['text'])
        tempers = [C.CAST[c['who']]['temper'] for c in post['cmts']]
        self.assertTrue({'gossip', 'judge'} & set(tempers[:1]), 'someone piles on first')
        self.assertTrue({'warm', 'tsundere', 'genz'} & set(tempers), 'someone defends')
        last = post['cmts'][-1]
        if adviser in C.RUMOUR_ADVICE:
            self.assertEqual((last['who'], last['text']), (adviser, bd._fill(s, C.RUMOUR_ADVICE[adviser], adviser)))
        else:
            self.assertIn(last['who'], ('chi_mai', 'co_lua'))
        self.assertEqual(board(s)['stats']['last_rumour'], board(s)['day'])
        # The player can still answer on the board.
        s, r = act(s, 'bd_reply', post=post['id'], tone='clarify')
        self.assertEqual(bd._find(board(s), post['id'])['rumour']['state'], 'clarify')
        self.assertEqual(r['replies'][0]['who'], 'co_hai_loa')          # the gossip backs down
        validate_state(s)

    def test_answering_on_the_group_in_the_life_card(self):
        s = life_state()
        fire(s, 'dd_late_2', gossip='chi_tu_zalo')
        s = choose(s, 'post')
        while s['journey']['life']['pending'] and s['journey']['life']['pending']['stage'] != 'done':
            s = choose(s, 'no' if s['journey']['life']['pending']['stage'] == 'comfort' else 'skip')
        post = next(p for p in life_posts(s) if p['kind'] == 'rumour')
        self.assertEqual((post['who'], post['rumour']['state']), ('chi_tu_zalo', 'clarify'))
        mine = [c for c in post['cmts'] if c['who'] == 'player']
        self.assertEqual([c['text'] for c in mine], ['Em làm ở mấy tiệm trong hẻm ạ'])
        validate_state(s)

    def test_every_life_fact_and_gossip_makes_a_thread(self):
        for fact in FACTS:
            hid = next(x['id'] for x in HARD if x['cat'] == 'dat_dieu' and x['fact'] == fact)
            for gid in GOSSIPS:
                s = life_state()
                card = fire(s, hid, gossip=gid)
                row = lf._log(s, s['journey']['life'], dict(card, stage='done'), 'x')
                post = next(p for p in life_posts(s) if p['kind'] == 'rumour')
                self.assertEqual((post['who'], post['rumour']['fact']), (gid, C.LIFE_FACT[fact]), (fact, gid))
                self.assertNotIn('{', post['text'])
                beats(s, 10)
                self.assertGreaterEqual(len(bd._find(board(s), post['id'])['cmts']), 2)
                self.assertEqual(bd.on_life_log(s, row, card), [])      # each row once
                validate_state(s)

    def test_heartbreak_brings_invitations(self):
        s = life_state()
        fire(s, 'tt_break')
        s = choose(s, lf.public(s)['pending']['choices'][0]['id'])
        while s['journey']['life']['pending'] and s['journey']['life']['pending']['stage'] != 'done':
            s = choose(s, 'yes' if s['journey']['life']['pending']['stage'] == 'comfort' else 'skip')
        beats(s, 15)
        post = next(p for p in life_posts(s) if p['who'] == 'ba_tam')
        self.assertNotIn('chia tay', post['text'])                     # discreet: nobody says what happened
        self.assertGreaterEqual(len(post['cmts']), 3)
        self.assertTrue({'chu_hung', 'kieu_trang', 'chi_diep', 'be_ti', 'chu_tu', 'chi_mai'} >= {c['who'] for c in post['cmts']})

    def test_neighbour_in_trouble_and_joys(self):
        s = life_state()
        L = s['journey']['life']
        L['pending'] = lf._new_card(L, 8, 'ask', 'ask_roof', 'xom', 'ask', 'milk_tea', who=['ba_sau'])
        s = choose(s, 'big')
        beats(s, 12)
        post = next(p for p in life_posts(s) if 'nhà bà Sáu dột' in p['text'])
        ask = next(a for a in lf.ASK if a['id'] == 'ask_roof')
        self.assertIn(f'Cảm ơn {s["name"]} góp {ask["big"]} xu', ' '.join(c['text'] for c in post['cmts']))
        self.assertEqual(post['cmts'][-1]['who'], 'ba_sau')                 # the owner thanks everyone
        L = s['journey']['life']
        L['pending'] = lf._new_card(L, 8, 'joy', 'joy_kitten', 'vui', 'joy', 'milk_tea', who=['ba_sau'])
        s, _ = lf.action(s, 'lf_close', dict(id=L['pending']['id']))
        beats(s, 12)
        joy = next(p for p in life_posts(s) if 'Mướp đẻ' in p['text'])
        self.assertEqual((joy['who'], joy['mood']), ('ba_sau', 'happy'))
        self.assertGreaterEqual(len(joy['cmts']), 2)
        validate_state(s)

    def test_life_threads_are_deterministic(self):
        def run():
            s = life_state(99)
            fire(s, 'dd_money_1', gossip='thim_bay')
            s = choose(s, 'ignore')
            beats(s, 10)
            return [(p['who'], p['text'], [(c['who'], c['text']) for c in p['cmts']]) for p in life_posts(s)]
        self.assertEqual(run(), run())

    def test_a_broken_board_never_breaks_the_life_layer(self):
        s = life_state()
        before = copy.deepcopy(board(s))
        real = bd.on_life_log

        def boom(st, *a, **k):
            st['journey']['board']['posts'].append('half written')
            raise RuntimeError('boom')
        bd.on_life_log = boom
        try:
            fire(s, 'dd_late_1', gossip='thim_bay')
            s = choose(s, 'ignore')
        finally:
            bd.on_life_log = real
        self.assertEqual(board(s), before)
        validate_state(s)

    def test_older_boards_get_the_new_gossip_ids(self):
        s = story_state()
        bd.on_rumour(s, dict(kind='late', who='co_hai_loa'))
        beats(s, 10)
        raw = json.dumps(board(s), ensure_ascii=False).replace('co_hai_loa', 'co_huong').replace('chi_tu_zalo', 'chi_tham')
        s['journey']['board'] = json.loads(raw)
        del s['journey']['board']['marks']['life']
        bd.migrate(s)
        self.assertNotIn('co_huong', json.dumps(board(s)))
        self.assertNotIn('chi_tham', json.dumps(board(s)))
        validate_state(s)
