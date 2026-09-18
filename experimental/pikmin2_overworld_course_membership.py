'''Link/boot classifier for the overworld-course membership lane (#802).

Reads membership-probe and #738 smoke markers and returns linked vs
boot-pass vs blocked vs unguarded-refused vs unattributed. Pure text
logic; no engine, no runtime.
'''

import re

LINKED_RE = re.compile(r'P2_OVERWORLD_COURSE_MEMBERSHIP_LINKED')
MEMBERSHIP_PASS_RE = re.compile(r'PASS P2_OVERWORLD_COURSE_MEMBERSHIP')
SMOKE_PASS_RE = re.compile(r'PASS P2_OVERWORLD_BOOT_SMOKE')
SMOKE_FLAG_RE = re.compile(r'P2_OVERWORLD_BOOT_COURSE_FLAG course=(\S+) index=(\d+)')
DOWN_RE = re.compile(r'P2_FIXTURE_CAPTAIN_DOWN')
REFUSED_RE = re.compile(r'unguarded runs refused')


def classify_log(text, exit_code):
    if REFUSED_RE.search(text):
        return {'verdict': 'unguarded-refused',
                'detail': 'unguarded run refused; no observation claimed'}
    if DOWN_RE.search(text):
        return {'verdict': 'blocked',
                'detail': 'captain-down run cannot substantiate PASS'}
    smoke = SMOKE_PASS_RE.search(text)
    if smoke and exit_code == 0:
        flags = [(m.group(1), int(m.group(2))) for m in SMOKE_FLAG_RE.finditer(text)]
        return {'verdict': 'boot-pass', 'detail': 'smoke boot observed',
                'flags': flags}
    if MEMBERSHIP_PASS_RE.search(text) and exit_code == 0:
        return {'verdict': 'linked',
                'detail': 'module symbols resolved at link; flag+registration observed'}
    return {'verdict': 'unattributed',
            'detail': 'no membership or smoke pass markers'}
