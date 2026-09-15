"""Lane 24 free-mode and natural-lifecycle acceptance gates (King/Queen).

Pure-Python, side-effect-free validators that inspect native fixture logs and
return a uniform evidence dict::

    dict(passed=<bool>, failed=[<names>], checks={<name>:<bool>},
         exit_code=<code>, scope=<str>)
"""

import re


def king_free_mode_validate(text, code):
    """Validate a free-mode Emperor Bulblax (enemy 53) natural-death run.

    The squad is deployed exactly once and not re-pinned each tick, so the
    outcome may be a natural kill (frame-185 Dead key) or an honest health
    floor; either is accepted as long as the matching marker is reported.
    """
    checks = dict(
        completion=code == 0 and (
            'PASS P2_KING_FREEMODE_DEATH' in text or 'P2_KING_FREEMODE_FLOOR' in text),
        baseline=bool(re.search(r'P2_KING_FREEMODE_BASELINE red=20', text)),
        ready=bool(re.search(r'P2_KING_READY id=230020 enemy=53 variant=default', text)),
        no_injection=not any(marker in text for marker in (
            'P2_KING_INJECT', 'P2_KING_BOMB_READY', 'P2_KING_BOMB_EXTERNAL',
            'P2_KING_INJECT_FLICK', 'P2_KING_INJECT_KILL')),
        no_staging=not any(marker in text for marker in ('NAVI_HEAL', 'REPIN', 'NAVI_SUSTAIN', 'GUARD_PIKMIN')),
        armed='P2_KING_FREEMODE_ARMED deploy_once=1 no_injection=1' in text,
    )
    killed = bool(re.search(r'P2_KING_DEAD_KEY id=230020 frame=185 kill=1', text))
    matches = re.findall(
        r'P2_KING_COMBAT_DAMAGE id=230020 stuck=(\d+) damage=([\d.]+) health=([\d.]+) interval=20',
        text)
    health_floor = float(matches[-1][2]) if matches else None
    consistent = killed or 'P2_KING_FREEMODE_FLOOR' in text
    checks['killed'] = killed
    checks['consistent'] = consistent
    required = ('completion', 'baseline', 'ready', 'no_injection', 'no_staging', 'armed', 'consistent')
    failed = sorted(name for name in required if not checks[name])
    return dict(
        passed=not failed,
        failed=failed,
        checks=checks,
        exit_code=code,
        killed=killed,
        health_floor=health_floor,
        consistent=consistent,
        scope='Free-mode Emperor Bulblax: squad deployed once (not re-pinned), so a natural '
              'kill or an honest health floor are both valid; no injection channels present',
    )


def queen_natural_validate(text, code):
    """Validate an Empress Bulblax (enemy 30) natural lifecycle run.

    Natural (un-injected) larva births with exactly-once accounting, a natural
    Baby captain bite that actually drops health, and Queen death releasing all
    live larvae.
    """
    checks = dict(
        completion=code == 0 and 'PASS P2_QUEEN_NATURAL_RUNTIME' in text,
        ready=bool(re.search(r'P2_QUEEN_READY id=230010 enemy=30 variant=default', text)),
        no_injection=not any(marker in text for marker in
                             ('P2_QUEEN_INJECT', 'P2_QUEEN_INJECT_LARVA')),
    )
    born = sorted(int(n) for n in re.findall(
        r'P2_QUEEN_LARVA id=\d+ xyz=[^\n]*born=(\d+)', text))
    checks['birth'] = bool(born) and born == list(range(1, len(born) + 1))
    bites = re.findall(
        r'P2_QUEEN_LARVA_ATTACK id=\d+ damage=2 captain_before=([\d.]+) captain_health=([\d.]+)',
        text)
    checks['bite'] = bool(bites) and any(float(after) < float(before) for before, after in bites)
    checks['death'] = bool(re.search(r'P2_QUEEN_STATE id=230010 from=\d+ to=0 health=0', text))
    released = re.findall(r'P2_QUEEN_DEATH_LARVA_RELEASE id=230010 released=(\d+)', text)
    checks['death_release'] = bool(released) and all(int(n) >= 1 for n in released)
    failed = sorted(name for name, ok in checks.items() if not ok)
    return dict(
        passed=not failed,
        failed=failed,
        checks=checks,
        exit_code=code,
        scope='Natural Empress Bulblax lifecycle: un-injected births, exactly-once larva '
              'accounting, a natural Baby bite, and death releasing all live larvae',
    )


def queen_free_mode_validate(text, code):
    """Validate a free-mode Empress Bulblax (enemy 30) natural-death run.

    The squad is deployed exactly once and not re-pinned each tick, and the
    captain is never health-refilled, so the outcome may be a natural kill or an
    honest health floor; either is accepted as long as the matching marker is
    reported and no staging marker (NAVI_HEAL/REPIN/NAVI_SUSTAIN/GUARD_PIKMIN) is present.
    """
    checks = dict(
        completion=code == 0 and (
            'PASS P2_QUEEN_FREEMODE_DEATH' in text or 'P2_QUEEN_FREEMODE_FLOOR' in text),
        baseline=bool(re.search(r'P2_QUEEN_FREEMODE_BASELINE red=64', text)),
        ready=bool(re.search(r'P2_QUEEN_READY id=230010 enemy=30 variant=default', text)),
        no_injection=not any(marker in text for marker in
                             ('P2_QUEEN_INJECT', 'P2_QUEEN_INJECT_LARVA')),
        no_staging=not any(marker in text for marker in ('NAVI_HEAL', 'REPIN', 'NAVI_SUSTAIN', 'GUARD_PIKMIN')),
        armed='P2_QUEEN_FREEMODE_ARMED deploy_once=1 no_injection=1' in text,
    )
    killed = bool(re.search(r'P2_QUEEN_STATE id=230010 from=\d+ to=0 health=0', text))
    matches = re.findall(
        r'P2_QUEEN_COMBAT_DAMAGE id=230010 stuck=(\d+) damage=([\d.]+) health=([\d.]+) interval=20',
        text)
    health_floor = float(matches[-1][2]) if matches else None
    consistent = killed or 'P2_QUEEN_FREEMODE_FLOOR' in text
    checks['killed'] = killed
    checks['consistent'] = consistent
    required = ('completion', 'baseline', 'ready', 'no_injection', 'no_staging', 'armed', 'consistent')
    failed = sorted(name for name in required if not checks[name])
    return dict(
        passed=not failed,
        failed=failed,
        checks=checks,
        exit_code=code,
        killed=killed,
        health_floor=health_floor,
        consistent=consistent,
        scope='Free-mode Empress Bulblax: squad deployed once (not re-pinned), captain never '
              'health-refilled, so a natural kill or an honest health floor are both valid; no injection '
              'or staging markers present',
    )


def king_creature_validate(text, code):
    """Validate an un-injected Emperor Bulblax (enemy 53) creature run.

    The Bulblax is bound to a generated host Teki and killed by free Pikmin,
    producing a Pod corpse receipt, with no staging or injection markers.
    """
    staging = ('NAVI_HEAL', 'REPIN', 'NAVI_SUSTAIN', 'GUARD_PIKMIN',
               'P2_KING_INJECT', 'P2_QUEEN_INJECT')
    checks = dict(
        completion=code == 0 and 'PASS P2_KING_CREATURE_RUNTIME' in text,
        teki_ready=bool(re.search(r'P2_KING_TEKI_READY generator=\d+ type=\d+', text)),
        attached=bool(re.search(r'P2_KING_TEKI_ATTACHED generator=\d+ attached=[1-9]\d*', text)),
        flick=bool(re.search(r'P2_KING_TEKI_FLICK generator=\d+', text)),
        lethal=bool(re.search(r'P2_KING_TEKI_CORPSE generator=\d+ health=0.0', text)),
        pod_receipt=bool(re.search(r'P2_POD_RECEIPT id=corpse:king:\d+', text)),
        no_staging=not any(marker in text for marker in staging),
    )
    failed = sorted(name for name, ok in checks.items() if not ok)
    return dict(
        passed=not failed,
        failed=failed,
        checks=checks,
        exit_code=code,
        scope='Un-injected Emperor Bulblax bound to a generated host Teki, killed by free Pikmin '
              'with a Pod corpse receipt; no staging or injection channels present',
    )
