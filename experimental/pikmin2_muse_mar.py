"""Muse Mar29 (Puffy Blowhog) death/corpse/transport/re-entry observer (#375).

Lane `shard-enemies-2-mar29-observer`. Gates 4/5/6 (`death_corpse`,
`transport_reward`, `cleanup_reentry`); gates 1/2/3 are already natural PASS in
the merged family implementation and are preserved as-is, never relabelled.

This module is the additive, dependency-free observer for the lane. It provides:

* `validate()` - a run-log reader that accepts only a natural Mar death plus a
  cleanup/re-entry, and that REFUSES injected runs and any receipt the native
  base cannot produce.
* `dependency_report()` - the verified reason `transport_reward` is blocked:
  Mar spawns as `TEKI_Mar` and has no corpse-receipt hook, so a delivered Mar
  corpse hits the generic Pod abort path.

Source facts (read-only; `pc_port/` on native pin e44b5d70):
* `pc_p2_mar.cpp:422` emits `P2_MAR_BIND generator=<g> source_id=29 visual_only=0`.
* `pc_p2_mar.cpp:452` emits `P2_MAR_DEAD generator=<g> source_id=29 health=0`.
* `pc_p2_mar.cpp:530` calls `actor->die()` once the death clip completes.
* `pc_p2_batch3.cpp:77` spawns Mar/Hanachirashi as `TEKI_Mar`.
* `pc_p2_preview.cpp:119` registers only `TEKI_Chappy` in the corpse map, and
  `:383-384` aborts on an unregistered delivered corpse. No `pc_p2_mar_receipt`
  exists anywhere in `pc_port/`.

The reader is intentionally conservative: while the receipt dependency is
unresolved it never reports `transport_reward=pass`.
"""

import argparse
import json
import os
import re
from pathlib import Path

MARSOURCE = 'pc_port/pc_p2_mar.cpp'
PREVIEWSOURCE = 'pc_port/pc_p2_preview.cpp'
BATCH3SOURCE = 'pc_port/pc_p2_batch3.cpp'

# Native markers emitted by the family module (read-only; not written here).
BIND_RE = re.compile(r'P2_MAR_BIND generator=(\d+) source_id=29 visual_only=0')
DEAD_RE = re.compile(r'P2_MAR_DEAD generator=(\d+) source_id=29 health=0')
READY_RE = re.compile(r'P2_ENEMY_READY species=Mar\b[^\n]*generator=(\d+)')
STATE_RE = re.compile(r'P2_MAR_STATE generator=(\d+) state=(\w+)')
BLOW_RE = re.compile(r'P2_MAR_BLOW generator=(\d+) pikmin=(\d+)')
POS_RE = re.compile(r'P2_MAR_POS generator=(\d+) state=\w+ clip=(\S+)')

# Muse observer markers (emitted by native/tools/p2_muse_mar_fixture.cpp).
DRAIN_RE = re.compile(r'P2_MUSE_MAR_DRAIN events=(\d+) min=([\d.]+) start=([\d.]+)')
NATURAL_DEATH_RE = re.compile(r'P2_MUSE_MAR_NATURAL_DEATH mar=1 health=0\.00')
CORPSE_RE = re.compile(r'P2_MUSE_MAR_CORPSE pellet=(\d+) generator=(\d+)')
CARRY_RE = re.compile(r'P2_MUSE_MAR_CARRY [^\n]*\btransport=(\d+)')
RECEIPT_RE = re.compile(r'P2_POD_RECEIPT id=corpse:(?:[a-z]+:)?(\d+)')
FORGET_RE = re.compile(r'P2_MUSE_MAR_FORGET count=0 registered=0')
REENTRY_RE = re.compile(r'P2_MUSE_MAR_REENTRY old=\S+ new=\S+ stale=0 fresh=1 count=1')
WINDOW_RE = re.compile(r'Experimental preview window set to 960x540 windowed and centered')
GUARD_DOWN_RE = re.compile(r'P2_FIXTURE_CAPTAIN_DOWN [^\n]*outcome=BLOCKED')
INJECT_RE = re.compile(r'P2_MUSE_MAR_INJECT|P2_LIFECYCLE_INJECT')
BLOCKED_RE = re.compile(r'BLOCKED transport=missing_receipt')
SESSION_RE = re.compile(r'P2_MUSE_MAR_SESSION navi=1\b')
PROXY_CARRY_RE = re.compile(r'P2_MUSE_MAR_CARRY [^\n]*proxy=1')

FORBIDDEN_FIXTURE_PATTERNS = (
    r'->mHealth\s*=',
    r'\.mHealth\s*=',
    r'mMode\s*=\s*PikiMode::TransportMode',
    r'P2_MUSE_MAR_INJECT',
    r'P2_LIFECYCLE_INJECT',
)

# The unresolved native dependency that blocks gate 5.
TRANSPORT_DEPENDENCY = {
    'gate': 'transport_reward',
    'reason': ('Mar spawns as TEKI_Mar; no pc_p2_mar_receipt hook exists and the '
               'generic Pod corpse path registers only TEKI_Chappy, so a '
               'delivered Mar corpse hits the abort branch.'),
    'evidence': [
        MARSOURCE + ':422 P2_MAR_BIND source_id=29',
        MARSOURCE + ':452 P2_MAR_DEAD source_id=29 health=0',
        MARSOURCE + ':530 actor->die()',
        BATCH3SOURCE + ':77 Mar/Hanachirashi -> TEKI_Mar',
        PREVIEWSOURCE + ':119 rebind registers TEKI_Chappy only',
        PREVIEWSOURCE + ':383-384 unregistered corpse abort',
    ],
    'needs': ('existing-owner review of an additive pc_p2_mar_receipt() plus a '
              'pc_p2_preview_deliver registration; both files are outside this '
              'lane four owned files and are read-only here.'),
    'resolved_by': ('mar-native-registration-668 (#668, issue #636): the #650 '
                    'adapter pc_p2_mar_receipt.{h,cpp} plus the #186-approved '
                    'Queen-preserving dispatch arm and family hook wiring landed '
                    'on the species native line (integrated native commit '
                    '07b460631013faa0b7eb8fc622be4fc95b0754f7) and were merged '
                    'into this lane private native worktree. Runtime gates 4/5/6 '
                    'still require a leased guarded GL run.'),
}

def dependency_report():
    """Return the verified transport_reward dependency (no native access)."""
    return dict(TRANSPORT_DEPENDENCY)


def validate(text, code=0):
    """Validate a muse-Mar run log. Returns passed/checks/gates.

    A run passes only when it shows a natural death (monotonic observed drain
    to zero with real attacks), an observed corpse, a pod receipt for the SAME
    generator with real transport, and a forget/reset/re-bind re-entry - and
    carries none of the injected markers. While the receipt dependency is
    unresolved the native base cannot produce such a receipt, so a receipt-less
    log reports transport_reward=blocked rather than failing the whole run.
    """
    if not isinstance(text, str):
        raise ValueError('Expected a native log string')
    bind = BIND_RE.search(text)
    mar_generator = bind.group(1) if bind else None
    ready = READY_RE.search(text)
    dead = DEAD_RE.search(text)
    states = STATE_RE.findall(text)
    blows = [int(n) for _, n in BLOW_RE.findall(text)]
    drain = DRAIN_RE.search(text)
    drain_events = int(drain.group(1)) if drain else 0
    drain_min = float(drain.group(2)) if drain else float('inf')
    drain_start = float(drain.group(3)) if drain else 0.0
    natural_death_marker = bool(NATURAL_DEATH_RE.search(text))
    natural_death = (natural_death_marker and bool(dead) and drain_events >= 2
                     and 0.0 < drain_min < drain_start and drain_start > 0.0
                     and len(blows) >= 1)
    corpse = CORPSE_RE.search(text)
    corpse_ok = bool(corpse) and (mar_generator is None or corpse.group(2) == mar_generator)
    carry = [int(n) for n in CARRY_RE.findall(text)]
    receipt = RECEIPT_RE.search(text)
    same_generator_receipt = bool(receipt) and (mar_generator is not None
                                                and receipt.group(1) == mar_generator)
    proxy_carry = bool(PROXY_CARRY_RE.search(text))
    blocked = bool(BLOCKED_RE.search(text))
    # A receipt is only credible while the native dependency is unresolved.
    if same_generator_receipt and blocked:
        same_generator_receipt = False
    natural_carry = (same_generator_receipt and bool(carry) and max(carry) > 0
                     and not proxy_carry)
    cleanup = bool(FORGET_RE.search(text))
    reentry = bool(REENTRY_RE.search(text))
    injected = bool(INJECT_RE.search(text))
    captain_down = bool(GUARD_DOWN_RE.search(text))
    window = bool(WINDOW_RE.search(text))
    session = bool(SESSION_RE.search(text))
    completion = 'PASS P2_MUSE_MAR' in text
    checks = dict(
        binds=bool(bind),
        window=window,
        ready=bool(ready),
        live_states=any(state in ('wait', 'move', 'chase') for _, state in states),
        real_attacks=bool(blows) and max(blows) >= 1,
        natural_death=natural_death and not injected,
        corpse=corpse_ok,
        natural_carry=natural_carry and not injected,
        cleanup=cleanup,
        reentry=reentry,
        session=session,
        no_inject=not injected,
        captain_safe=not captain_down,
        completion=completion,
    )
    gates = dict(
        death_corpse=('pass' if (natural_death and corpse_ok and not injected) else 'fail'),
        transport_reward=('pass' if natural_carry else ('blocked' if blocked else 'fail')),
        cleanup_reentry=('pass' if (cleanup and reentry and not injected) else 'fail'),
    )
    return dict(passed=(code == 0 and all(checks.values())), checks=checks,
                gates=gates, mar_generator=mar_generator, blow_events=len(blows),
                drain_events=drain_events,
                natural_vs_injected=dict(
                    natural_death=natural_death,
                    natural_carry=natural_carry,
                    inject_present=injected))


def validate_log(path, code=0, out=None):
    """Read a native.log and validate it; optionally write the result JSON."""
    text = Path(path).read_text(errors='replace')
    result = validate(text, code)
    result['source'] = str(path)
    if out is not None:
        Path(out).write_text(json.dumps(result, indent=2) + '\n')
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description='Muse Mar29 observer reader (#375)')
    sub = parser.add_subparsers(dest='command', required=True)
    reader = sub.add_parser('validate')
    reader.add_argument('--log', type=Path, required=True)
    reader.add_argument('--exit-code', type=int, default=0)
    reader.add_argument('--out', type=Path)
    sub.add_parser('dependencies')
    args = parser.parse_args(argv)
    if args.command == 'dependencies':
        print(json.dumps(dependency_report(), indent=2))
        return 0
    result = validate_log(args.log, args.exit_code, args.out)
    print(json.dumps(result, indent=2))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
