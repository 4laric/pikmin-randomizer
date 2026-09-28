"""Lane 15 ShijimiChou (Unmarked Spectralids, EnemyID 77) lifecycle contract.

Native slice contract for ``pc_port/pc_p2_shijimi.cpp`` (source revision
``632af93787b9c95b63f0c13be32b161375ce3a96``). Source states from
``ShijimiChou.h:41-49``: wait=0, fly=1, fall=2, dead=3, leave=4, rest=5. Source
anims (``ShijimiChou.h:285-290``): carry=0, dead=1, move=2.

The validator grades a captured native stdout log. It deliberately does NOT
require a death path: the bounded slice exercises the natural
``wait -> fly -> leave`` departure plus the registration/visual markers. Gate 3
(receiver) is source-backed N/A (``shijimiChou.h`` ``damageCallBack`` is not
overridden to a family reward; the base battle path is retained) and gate 4
requires a natural health endpoint that an unattended arena does not produce.
"""
from __future__ import annotations

import re

SCHEMA = 'p2-shijimi-lifecycle-v1'
SOURCE_ID = 77
INTERNAL = 'ShijimiChou'
ENGLISH = 'Unmarked Spectralids'

STATE_IDS = {'wait': 0, 'fly': 1, 'fall': 2, 'dead': 3, 'leave': 4, 'rest': 5}
ANIM_IDS = {'carry': 0, 'dead': 1, 'move': 2}
CLIPS = ('carry', 'dead', 'move')
GATES = {
    'native_identity': 'untested-engine',
    'natural_AI': 'untested-engine',
    'receiver': 'source-backed N/A',
    'death_corpse': 'untested-engine',
    'transport_reward': 'blocked (lane 06)',
    'cleanup_reentry': 'blocked (#397)',
}


def contract():
    return dict(
        schema=SCHEMA,
        identity=f'P2_SHIJIMI_BIND generator=<gen> source_id={SOURCE_ID} visual_only=0',
        ready='P2_ENEMY_READY species=ShijimiChou .*behavior=native '
              '.*source_FSM=implemented',
        window='Experimental preview window set to 960x540 windowed and centered',
        bank='P2_SHIJIMI_BANK',
        draw='P2_SHIJIMI_DRAW corpse=0',
        states=list(STATE_IDS),
        clips=list(CLIPS),
        gates=dict(GATES),
    )


def validate_lifecycle(text):
    if not isinstance(text, str):
        raise ValueError('Expected a native log string')
    states = re.findall(r'P2_SHIJIMI_STATE generator=\d+ state=(\w+)', text)
    seen = set(states)
    checks = dict(
        identity=bool(re.search(rf'P2_SHIJIMI_BIND generator=\d+ source_id={SOURCE_ID} '
                                r'visual_only=0', text)),
        ready=bool(re.search(r'P2_ENEMY_READY species=ShijimiChou .*behavior=native '
                             r'.*source_FSM=implemented', text)),
        window=bool(re.search(r'Experimental preview window set to 960x540 windowed and centered',
                              text)),
        bank=bool(re.search(r'P2_SHIJIMI_BANK poses=\d+ mod_bytes=\d+', text)),
        draw=bool(re.search(r'P2_SHIJIMI_DRAW corpse=0', text)),
        wait='wait' in seen,
        fly='fly' in seen,
        departure=bool(seen & {'leave', 'dead'}),
        no_extinction=not re.search(r'Extinction', text, re.IGNORECASE),
        states=states,
    )
    scalar = {k: v for k, v in checks.items() if isinstance(v, bool)}
    return dict(passed=all(scalar.values()), checks=checks,
                gates=dict(GATES),
                unmeasured=['natural health-endpoint Fall/Dead (needs a real attacker)',
                            'receiver combat', 'physical reward semantics',
                            'cleanup/re-entry', 'source 25-member group factory'])


if __name__ == '__main__':
    import argparse
    import json
    from pathlib import Path

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('log', type=Path)
    args = parser.parse_args()
    print(json.dumps(validate_lifecycle(args.log.read_text(errors='replace')), indent=2))
