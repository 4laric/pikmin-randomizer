"""Private fixture party restoration; not campaign or floor resume."""
from collections import Counter
from copy import deepcopy
import math
import re
from experimental.pikmin2_campaign import SPECIES, squad_valid
from experimental.pikmin2_beasts_party_snapshot import party_snapshot


def restore_party(party):
    if not isinstance(party,dict) or set(party)!={'health','squad'}:raise ValueError('Invalid restore party fields')
    squad_valid(party['squad'])
    if len(party['squad'])!=20 or any(p['species'] not in ('red','purple') for p in party['squad']):
        raise ValueError('Restore fixture requires twenty Red/Purple survivors')
    health=party['health']
    if type(health) not in (int,float) or not math.isfinite(health) or not 0<health<=1:
        raise ValueError('Invalid restore health')
    return deepcopy(party)


def entry_text(party,token):
    party=restore_party(party)
    if not isinstance(token,str) or not re.fullmatch('[0-9a-f]{32}',token):raise ValueError('Invalid entry token')
    lines=['P2_CAVE_ENTRY_1',token,f'2 {party["health"]:.9g} 20']
    lines.extend(f'{SPECIES.index(p["species"])} {p["maturity"]}' for p in party['squad'])
    return '\n'.join(lines)+'\n'


def validate_restore(log,expected):
    expected=restore_party(expected)
    passed='PASS P2_BEASTS_RESTORE updates=300 cargo=0 pokos=0 repairs_unchanged=1'
    if log.count(passed)!=1 or log.count('P2_ROOM_CARGO_FREE_READY cargo=0')!=1:
        raise ValueError('Missing restoration completion')
    if any(value in log for value in ('FAIL ', 'P2_VIOLET_', 'P2_BEASTS_THROW', 'P2_POD_RECEIPT', 'P2_TREASURE_DELIVERED')):
        raise ValueError('Unexpected restoration action/reward')
    records=re.findall(r'^P2_CAVE_RESTORE species=([0-3]) maturity=([0-2])$',log,re.M)
    if len(records)!=sum(line.startswith('P2_CAVE_RESTORE') for line in log.splitlines()):
        raise ValueError('Malformed native restore record')
    if records!=[(str(SPECIES.index(p['species'])),str(p['maturity'])) for p in expected['squad']]:
        raise ValueError('Native entry restoration differs')
    colors=Counter(p['species'] for p in expected['squad'])
    actual=party_snapshot(log,dict(red=colors['red'],purple=colors['purple'],sprouts=0),restored=True)
    if actual['squad']!=expected['squad'] or not math.isclose(actual['health'],expected['health'],rel_tol=1e-6,abs_tol=1e-7):
        raise ValueError('Restored party changed')
    return actual
