"""Correlate an ordinary Yellow throw with actual electric receiver rejection."""
import math
import re


def witness(text):
    staged = None
    phase = None
    frame = -1
    for line in text.splitlines():
        tag, _, tail = line.partition(' ')
        if tag == 'P2_FIXTURE_CAPTAIN_DOWN' or ('GUARD_OBSERVATION' in tag and 'injected=1' in tail):
            return None
        if tag not in {'P2_ELECBUG_YELLOW_STAGED', 'P2_ELECBUG_THROW',
                       'P2_ELECBUG_OFF_CONTACT', 'P2_ELECBUG_PRESS_IMMUNE',
                       'P2_ELECBUG_CONTACT_DISPATCH', 'P2_ELECBUG_YELLOW_SURVIVED',
                       'P2_ELECBUG_CONTACT_CANDIDATE'}:
            continue
        pairs = [part.split('=', 1) for part in tail.split()]
        if any(len(pair) != 2 for pair in pairs) or len({p[0] for p in pairs}) != len(pairs):
            return None
        fields = dict(pairs)
        pointer = fields.get('piki', '').lower().removeprefix('0x')
        if not re.fullmatch('[0-9a-f]+', pointer) or not int(pointer, 16):
            return None
        pointer = int(pointer, 16)
        if tag == 'P2_ELECBUG_YELLOW_STAGED':
            if staged is not None or fields.get('species') != '2' or fields.get('acquisition') != '0':
                return None
            staged = pointer
            continue
        if pointer != staged:
            continue
        try:
            current = int(fields['frame']) if 'frame' in fields else frame
            if current < frame:
                return None
            if tag == 'P2_ELECBUG_THROW':
                next_phase = fields.get('phase')
                if next_phase == 'held':
                    phase = 'held'
                elif next_phase == 'invalidated':
                    phase = None
                elif {'released': 'held', 'rising': 'released', 'descending': 'rising'}.get(next_phase) == phase and phase is not None:
                    phase = next_phase
                else:
                    phase = None
            elif tag == 'P2_ELECBUG_OFF_CONTACT' and phase == 'descending' and fields.get('generator') == '346002' and fields.get('contact') == '0':
                phase = 'off_contact'
            elif tag == 'P2_ELECBUG_PRESS_IMMUNE' and phase == 'off_contact':
                if not (fields.get('generator') == '346002' and fields.get('source_id') == '28'
                        and fields.get('species') == '2' and fields.get('accepted') == '0'
                        and fields.get('alive') == '1' and int(fields['target_state']) == 14
                        and fields['state_before'] == fields['target_state']):
                    return None
                phase = 'rejected'
            elif tag == 'P2_ELECBUG_CONTACT_DISPATCH' and phase == 'rejected':
                velocity = float(fields['vy'])
                if not (fields.get('generator') == '346002' and fields.get('species') == '2'
                        and fields.get('contact') == '1' and fields.get('enemy_before') in ('discharge', 'childdischarge')
                        and fields.get('enemy_after') == 'reverse' and math.isfinite(velocity) and velocity < -.01):
                    return None
                phase = 'dispatch'
            elif tag == 'P2_ELECBUG_YELLOW_SURVIVED' and phase == 'dispatch':
                if not (fields.get('species') == '2' and fields.get('alive') == '1'
                        and fields.get('grounded') == '1' and fields.get('live') == '20'
                        and int(fields['state']) not in (6, 7, 12, 14, 24, 35)):
                    return None
                phase = 'survived'
            elif tag == 'P2_ELECBUG_CONTACT_CANDIDATE' and phase == 'survived':
                if fields.get('generator') == '346002' and fields.get('species') == '2' and fields.get('mode') == 'yellow-electric' and fields.get('observed_reverse') == '1':
                    return {'piki': hex(staged), 'actual_receiver_rejected': True,
                            'ordinary_throw_contact': True, 'grounded_survivor': True,
                            'population': 20, 'original_acquisition': False}
            frame = current
        except (KeyError, ValueError):
            return None
    return None


def staged_red_witness(text):
    """Bind the inherited vulnerable control chain to its disclosed debug body."""
    from scripts.run_elecbug_contact_runtime import contact_witness
    staged = None
    held = False
    for line in text.splitlines():
        tag, _, tail = line.partition(' ')
        if tag not in ('P2_ELECBUG_RED_STAGED', 'P2_ELECBUG_THROW'):
            continue
        try:
            pairs = [part.split('=', 1) for part in tail.split()]
            if any(len(pair) != 2 for pair in pairs) or len({p[0] for p in pairs}) != len(pairs):
                return None
            fields = dict(pairs)
            pointer = int(fields['piki'], 16)
            if not pointer:
                return None
            if tag == 'P2_ELECBUG_RED_STAGED':
                if staged is not None or not all(fields.get(key) == value for key, value in {
                    'species': '1', 'synthetic_control': '1', 'non_story_fixture': '1',
                    'acquisition': '0', 'campaign': '0',
                    'catalog_key': 'fixture-red-control/initgen.txt#0',
                    'fingerprint': '8926e466ec3c5d6fb8b9db2f93a7164cf5ff87d4719b5454a61eb9688ae368b3',
                }.items()):
                    return None
                staged = pointer
            elif fields.get('phase') == 'held' and pointer == staged:
                held = True
        except (KeyError, ValueError):
            return None
    proof = contact_witness(text, 'red-electric')
    if staged is None or not held or not proof or proof['piki_hex'] != hex(staged):
        return None
    return dict(proof, synthetic_control=True, original_acquisition=False)
