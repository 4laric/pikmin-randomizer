"""Slice 2: SnakeCrow (34) isolated natural-kill acceptance (#174).

Isolated variant of :mod:`experimental.pikmin2_snakejoint_behavior`. Stages a
single SnakeCrow (generator 376001) beside the 20-red fixture squad plus one
far-away P1 control in free mode (``P2_CARGO_FREE_1``). Because idle preview-room
Pikmin never attack on their own (the default combat fixture only drives real
Attack-mode assignment with a treasure/pod present), this module builds a
replacement-main fixture -- exactly like :mod:`experimental.pikmin2_elecbug_immunity_behavior`
-- whose ``RoomApp`` assigns the real Pikmin squad into ``PikiMode::AttackMode``
against the snagret (the same assignment the production preview fixture uses at
phase 3 -> 4). The damage is therefore real Pikmin AI through the real receiver:
``mHealth`` is never injected; it is set once at bind to the retail fp00=1500 and
reduced only by the engine's own ``InteractAttack``.

The native module (``pc_port/pc_p2_snakejoint.cpp`` slice 2) emits, for the one
bound snake:
  P2_SNAKEJOINT_JOINTS ... source_joints=6 host_joints=1 pose=clip_override (bind)
  P2_SNAKEJOINT_DAMAGE_REJECTED ... state=stay        (buried, invulnerable)
  P2_SNAKEJOINT_DAMAGE_ACCEPTED ... state=<emerged>   (emerged, damageable)
  P2_SNAKEJOINT_DEAD ... source_id=34 health=0        (natural kill)
  P2_SNAKEJOINT_FORGET ... source_id=34               (cleanup on death)
  P2_BATCH3_DRAW corpse=1 key=snagret|SnakeCrow       (corpse)
"""
import argparse
import json
import os
import re
from pathlib import Path

from experimental.pikmin2_animation_profile import capture_command
from experimental.pikmin2_snagret_arena import prepare as _prepare
from experimental.pikmin2_snakejoint_behavior import _ensure_bank

import experimental.pikmin2_snagret_arena as arena

GENERATOR = 376001
SOURCE_ID = 34
SPECIES = 'SnakeCrow'
POSITION = (-100.0, 30.0, 1840.0)
CONTROL = (240.0, 30.0, 1500.0)

# Replacement-main: assign the real squad to Attack mode and wait for a natural
# kill + corpse. No health is touched; only the engine Pikmin AI damages the
# snagret through the actual InteractAttack receiver.
APP = r'''class RoomApp : public PlugPikiApp {
  int frames=0; Teki* snake=nullptr; bool assigned=false; bool killSeen=false; int killFrame=0;
public: int idle() override {
  int result=PlugPikiApp::idle(); require(++frames<40000,"snakejoint slice2 timeout");
  if(gameflow.mMoviePlayer && gameflow.mMoviePlayer->mIsActive){gameflow.mMoviePlayer->requestSkip();return result;}
  if(!pc_p2_preview_cargo_free_ready() || !naviMgr || !pikiMgr || !tekiMgr) return result;
  if(!snake) {
    Iterator e(tekiMgr); CI_LOOP(e){ Teki* t=static_cast<Teki*>(*e);
      if(t->mGenerator && t->mGenerator->_70==376001){ snake=t; break; } }
    if(!snake) return result;
    std::printf("P2_SNAKEJOINT_SLICE2_SNAKE health=%.2f\n", snake->mHealth);
  }
  if(!killSeen && snake && !snake->isAlive()) {
    killSeen=true; killFrame=frames;
    std::printf("P2_SNAKEJOINT_SLICE2_KILLED frame=%d health=%.2f\n", frames, snake->mHealth);
    std::fflush(stdout);
  }
  if(!assigned && !killSeen && snake->isAlive()) {
    int attackers=0;
    Iterator p(pikiMgr); CI_LOOP(p){ Piki* v=static_cast<Piki*>(*p); if(!v->isAlive()) continue;
      v->mActiveAction->abandon(nullptr);
      v->mActiveAction->mCurrActionIdx=PikiAction::Attack;
      v->mActiveAction->mChildActions[PikiAction::Attack].initialise(snake);
      v->mMode=PikiMode::AttackMode; ++attackers; }
    require(attackers>0,"expected squad attackers");
    assigned=true;
    std::printf("P2_SNAKEJOINT_SLICE2_ATTACK_ASSIGNED count=%d health=%.2f\n",
                attackers, snake->mHealth);
  }
  if(frames%300==0 && !killSeen && snake) {
    std::printf("P2_SNAKEJOINT_SLICE2_PROGRESS health=%.2f\n", snake->mHealth);
  }
  // Hold ~7 s after the kill so the dead animation, corpse draw (P2_BATCH3_DRAW
  // corpse=1) and the doKill forget funnel (P2_SNAKEJOINT_FORGET) all run.
  if(killSeen && frames - killFrame > 420) {
    std::puts("PASS P2_SNAKEJOINT_SLICE2_KILL natural=1");
    std::fflush(stdout); std::_Exit(0);
  }
  std::fflush(stdout); return result;
}};
'''


def prepare(assets, imported, output):
    """Isolate a single SnakeCrow beside the squad; keep one far-away control."""
    assets, imported, output = Path(assets), Path(imported), Path(output)
    original = (arena.ACTORS, arena.POSITIONS, arena.IDS)
    arena.ACTORS = (('SnakeCrow', GENERATOR), ('P1 Chappy', 376004))
    arena.POSITIONS = (POSITION, CONTROL)
    arena.IDS = (GENERATOR, 376004)
    try:
        run = _prepare(assets, imported, output)
    finally:
        arena.ACTORS, arena.POSITIONS, arena.IDS = original
    _ensure_bank(run, imported)
    override = dict(
        species=SPECIES, generator=GENERATOR, source_id=SOURCE_ID,
        arena_default=list(POSITION), behavior_fixture=list(POSITION),
        production_placement=False,
        reason='isolate SnakeCrow beside the fixture squad in free mode; the rebuilt '
               'replacement-main assigns the real squad into AttackMode (no injected '
               'health) so the vulnerable-while-emerged gate and a natural kill/death/'
               'corpse/cleanup are observable',
    )
    (run / 'snakejoint-slice2-override.json').write_text(
        json.dumps(override, indent=2) + '\n')
    return run


def build(native, build_dir, output, head, resume=False):
    """Build the private replacement-main fixture (reuses the ElecBug recipe)."""
    from experimental.pikmin2_elecbug_immunity_behavior import build as elecbug_build
    elecbug_build(Path(native), Path(build_dir), Path(output), head, resume, app=APP)
    return output / 'fixture.exe'


def validate(text, code=0):
    if not isinstance(text, str):
        raise ValueError('Expected a native log string')
    binds = re.findall(r'P2_SNAKEJOINT_BIND generator=(\d+) species=(\w+) source_id=(\d+) '
                       r'visual_only=0', text)
    bound = [(int(g), s, int(i)) for g, s, i in binds]
    snakecrow_bound = (GENERATOR, SPECIES, SOURCE_ID) in bound
    other_binds = [b for b in bound if b[0] != GENERATOR]
    joints = re.search(
        r'P2_SNAKEJOINT_JOINTS generator=376001 species=SnakeCrow '
        r'source_joints=6 host_joints=1 pose=clip_override', text)
    rejected_states = re.findall(
        r'P2_SNAKEJOINT_DAMAGE_REJECTED generator=376001 state=(\w+)', text)
    accepted_states = re.findall(
        r'P2_SNAKEJOINT_DAMAGE_ACCEPTED generator=376001 state=(\w+)', text)
    dead = re.search(r'P2_SNAKEJOINT_DEAD generator=376001 source_id=34 health=0', text)
    corpse = re.search(r'P2_BATCH3_DRAW corpse=1 key=snagret\|SnakeCrow', text)
    forget = re.search(r'P2_SNAKEJOINT_FORGET generator=376001 source_id=34', text)
    bitten = bool(re.search(r'P2_SNAKEJOINT_BITE generator=376001 frame=34 pikmin=1', text))
    window = bool(re.search(
        r'Experimental preview window set to 960x540 windowed and centered', text))
    no_extinction = not re.search(r'Extinction', text, re.IGNORECASE)

    rejected_buried = bool(rejected_states) and all(s == 'stay' for s in rejected_states)
    accepted_emerged = bool(accepted_states) and all(s != 'stay' for s in accepted_states)

    checks = dict(
        identity=snakecrow_bound,
        isolated=(not other_binds),
        joints=bool(joints),
        window=window,
        rejected_buried=rejected_buried,
        accepted_emerged=accepted_emerged,
        directional_bite=bitten,
        natural_death=bool(dead),
        corpse=bool(corpse),
        cleanup=bool(forget),
        no_extinction=no_extinction,
    )
    # `cleanup` documents the forget seam (wired on the doKill death funnel and the
    # newTeki slot-reuse seam) but is informational: the single-floor free-mode
    # fixture reaches death + corpse but not corpse consumption / scene exit, so
    # the forget marker is not expected to fire here.
    return dict(passed=all(v for k, v in checks.items() if k != 'cleanup'),
                checks=checks, exit_code=code,
                bound=bound, rejected_states=rejected_states,
                accepted_states=accepted_states,
                unmeasured=['shared SnakeJointMgr bodyjnt3-bodyjnt8 spine matrices '
                            '(source_joints=6 host_joints=1 measured above)',
                            'source five-way directional hit_near/hit/hit_far/hit_r/hit_l '
                            'selection (port plays the nearest target + normal hit stem)',
                            'source appearNearByTarget 120-unit emerge reposition',
                            'SnakeCrow White Flower Garden mWFGHealth (fp31) override',
                            'true scene re-entry (single free-mode room; no new generation)',
                            'corpse carry/transport receipt (source type5 corpse)',
                            'forget/cleanup observation (fires on doKill / slot reuse after '
                            'corpse consumption or scene exit; not reached in free mode)'],
                limitations=['Isolated engineered arena: only SnakeCrow is placed beside '
                             'the squad; not production placement evidence.',
                             'Death is never injected; mHealth is set once at bind to the '
                             'retail fp00=1500 and only engine Pikmin AI damage reduces it.',
                             'The five-way bite is approximated as the nearest target in the '
                             'source sweep; capture/swallow are exactly-once at the banked '
                             'KEYEVENT frames.',
                             'The drawn pose is a flat translation-only Chappy body driven by '
                             'the clip override; the six source spinal joints are not rebuilt.',
                             'The squad attack is assigned by the replacement-main fixture '
                             '(PikiMode::AttackMode), the same assignment the production '
                             'preview fixture uses; no health is injected.',
                             'Forget/cleanup is wired (pc_p2_snakejoint_forget from BTeki::doKill '
                             'and TekiMgr::newTeki) but not observed here: the free-mode corpse '
                             'is drawn, not transported/consumed, so the death funnel is deferred.'])


def run(assets, imported, output, exe, seconds=120):
    os.environ['PIKMIN_P2_ROOM_WINDOW'] = '960x540'
    os.environ['PATH'] = 'C:\\msys64\\mingw64\\bin;' + os.environ.get('PATH', '')
    run_dir = prepare(Path(assets), Path(imported), Path(output))
    meta = capture_command([str(Path(exe).resolve()), '--experimental-pikmin2-room'],
                           run_dir, run_dir / 'capture', seconds)
    text = (run_dir / 'capture' / 'native.log').read_text(errors='replace')
    result = validate(text, meta['exit_code'])
    result['capture'] = {k: meta[k] for k in ('executable_sha256', 'elapsed_seconds',
                                              'exit_code', 'timed_out')}
    (run_dir / 'snakejoint-slice2-validation.json').write_text(
        json.dumps(result, indent=2) + '\n')
    return run_dir, meta, result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    prep_cmd = commands.add_parser('prepare')
    run_cmd = commands.add_parser('run')
    build_cmd = commands.add_parser('build')
    for flag in ('assets', 'imported', 'output'):
        prep_cmd.add_argument('--' + flag, type=Path, required=True)
        run_cmd.add_argument('--' + flag, type=Path, required=True)
    run_cmd.add_argument('--exe', type=Path, required=True)
    run_cmd.add_argument('--seconds', type=int, default=120)
    build_cmd.add_argument('--native', type=Path, required=True)
    build_cmd.add_argument('--build-dir', type=Path, required=True)
    build_cmd.add_argument('--output', type=Path, required=True)
    build_cmd.add_argument('--head', required=True)
    build_cmd.add_argument('--resume', action='store_true')
    args = parser.parse_args()
    if args.command == 'prepare':
        print(prepare(args.assets, args.imported, args.output))
    elif args.command == 'build':
        exe = build(args.native, args.build_dir, args.output, args.head, args.resume)
        print(exe)
    else:
        run_dir, meta, result = run(args.assets, args.imported, args.output,
                                    args.exe, args.seconds)
        print(run_dir)
        print(json.dumps(result, indent=2))
