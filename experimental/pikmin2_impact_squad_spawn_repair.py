'''Stall classifier for headed chal0 boot logs (#745).

Reads PARK_ALIVE, GATE_DIAG, SQUAD, BOOT and PASS markers plus the captain
guard line and returns spawned vs frozen-attributed vs frozen-unattributed
vs blocked. Pure text logic; no engine, no runtime.'''

import re

PARK_ALIVE_RE = re.compile(r'P2_CHALLENGE_PARK_ALIVE pikis=(\d+)')
DIAG_RE = re.compile(r'P2_CHALLENGE_GATE_DIAG gate=(\S+) observed=(\d+) alive=(-?\d+)'
    r' frames=(\d+) movie=(\d) pause=(\d) ui=(\d) navi=(\d)')
SQUAD_RE = re.compile(r'P2_CHALLENGE_SQUAD pikis=(\d+)')
BOOT_RE = re.compile(r'P2_CHALLENGE_BOOT level=(\d+) slot=(\S+)')
PASS_RE = re.compile(r'PASS P2_CHALLENGE_GUARDED_BOOT')
DOWN_RE = re.compile(r'P2_FIXTURE_CAPTAIN_DOWN')



def classify_log(text, exit_code):
    if DOWN_RE.search(text):
        return {'verdict': 'blocked', 'detail': 'captain-down run cannot substantiate PASS'}
    diags = [dict(gate=m.group(1), observed=int(m.group(2)), alive=int(m.group(3)),
                  frames=int(m.group(4)), movie=int(m.group(5)), pause=int(m.group(6)),
                  ui=int(m.group(7)), navi=int(m.group(8))) for m in DIAG_RE.finditer(text)]
    squad = SQUAD_RE.search(text)
    boot = BOOT_RE.search(text)
    passed = bool(PASS_RE.search(text))
    park = [int(m.group(1)) for m in PARK_ALIVE_RE.finditer(text)]
    if squad and boot and passed and exit_code == 0:
        return {'verdict': 'spawned', 'detail': 'squad, boot and pass observed', 'diags': diags}
    if diags:
        last = diags[-1]
        return {'verdict': 'frozen-attributed', 'detail': 'holding gate ' + last['gate'],
                'state': last, 'park_alive': park}
    return {'verdict': 'frozen-unattributed', 'detail': 'no squad and no diag markers', 'park_alive': park}

