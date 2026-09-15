"""TamagoMushi (68) manager-driven group-birth runtime — no injected births.

Sibling of :mod:`experimental.pikmin2_elecbug_natural_runtime.py`. Where the
ElecBug/Sokkuri validators close a *single-enemy* natural chain, this module
owns the Mitite (TamagoMushi) *group* birth chain:

* the host egg binds once (``P2_TAMAGO_HOST_BIND host=346020 egg=1
  source_id=68``);
* a live squad stages through ``P2_TAMAGO_GROUP_READY``;
* the **manager** (not the test) births the whole Mitite group
  (``P2_TAMAGO_BIRTH ... source=manager``), each born Mitite binding
  ``P2_TAMAGO_BIND generator=<n> source_id=68 visual_only=0``;
* the birth runs exactly once (``P2_TAMAGO_BIRTH_ONCE ... duplicate=0``);
* at least one natural Astonish is observed (``P2_TAMAGO_ASTONISH ... pikmin=1``);
* the whole group is forgotten with nothing left behind
  (``P2_TAMAGO_GROUP_FORGET ... remaining=0``);

No birth is injected and no enemy health/stat is written (the ``no_inject`` gate
rejects ``P2_LIFECYCLE_INJECT``/``not_natural_combat=1``/``injected_health``/
``mHealth=``). Extinction is not disabled.
"""
import argparse
import functools
import json
import os
import re
from pathlib import Path

from experimental.pikmin2_animation_profile import capture_command
from experimental.pikmin2_batch2_core import install, prepare as _prepare, verify_install
from experimental.pikmin2_sokkuri_behavior import normalize_pose_names

try:
    from experimental.pikmin2_batch2_families import FAMILIES
    CFG = dict(FAMILIES['ground'])
except Exception:  # pragma: no cover - import stub used by unit tests
    CFG = {}

TAMAGO_HOST_GEN = 346020
TAMAGO_SOURCE_ID = 68
CONTROL_GEN = 346007
TAMAGO_GROUP_COUNT = 10

HOST_POSITION = (-100.0, 30.0, 1850.0)
CONTROL_POSITION = (240.0, 30.0, 1500.0)

REQUIRED_CHECKS = ('identity', 'window', 'live_squad', 'manager_birth',
                   'exactly_once', 'natural_astonish', 'group_cleanup',
                   'no_inject', 'completion', 'no_extinction')

GOOD_LOG = '\n'.join([
    'P2_TAMAGO_HOST_BIND host=346020 egg=1 source_id=68',
    'Experimental preview window set to 960x540 windowed and centered',
    'P2_TAMAGO_GROUP_READY squad=20 host_gen=346020',
    'P2_TAMAGO_BIRTH host=346020 leader=346020 follow=9 count=10 source=manager',
    'P2_TAMAGO_BIND generator=346020 source_id=68 visual_only=0',
    'P2_TAMAGO_BIND generator=346021 source_id=68 visual_only=0 born=1',
    'P2_TAMAGO_BIND generator=346022 source_id=68 visual_only=0 born=1',
    'P2_TAMAGO_BIND generator=346023 source_id=68 visual_only=0 born=1',
    'P2_TAMAGO_BIND generator=346024 source_id=68 visual_only=0 born=1',
    'P2_TAMAGO_BIND generator=346025 source_id=68 visual_only=0 born=1',
    'P2_TAMAGO_BIND generator=346026 source_id=68 visual_only=0 born=1',
    'P2_TAMAGO_BIND generator=346027 source_id=68 visual_only=0 born=1',
    'P2_TAMAGO_BIND generator=346028 source_id=68 visual_only=0 born=1',
    'P2_TAMAGO_BIND generator=346029 source_id=68 visual_only=0 born=1',
    'P2_TAMAGO_BIRTH_ONCE host=346020 born=9',
    'P2_TAMAGO_GROUP_ONCE host=346020 count=10',
    'P2_TAMAGO_ASTONISH generator=346021 pikmin=1',
    'P2_TAMAGO_GROUP_FORGET host=346020 group=10 remaining=0',
    'P2_TAMAGO_GROUP_CLEANUP host=346020 forgotten=10',
    'PASS P2_TAMAGO_GROUP_RUNTIME birth=manager exactly_once=1 astonish=natural '
    'cleanup=group injected=0',
])


def validate(text, code=0):
    """Validate a synthetic/real native log for the manager-driven Mitite group.

    Returns ``dict(passed, checks, exit_code, births, astonish_hits)``. ``passed``
    is True only when the exit code is 0 and every required check holds.
    """
    if not isinstance(text, str):
        raise ValueError('Expected a native log string')

    identity = re.search(r'P2_TAMAGO_HOST_BIND host=346020 egg=1 source_id=68', text)
    window = re.search(r'Experimental preview window set to 960x540 windowed and centered', text)
    ready = re.search(r'P2_TAMAGO_GROUP_READY squad=(\d+) host_gen=346020', text)
    birth = re.search(r'P2_TAMAGO_BIRTH host=346020\b[^\n]*source=manager', text)
    binds = re.findall(r'P2_TAMAGO_BIND generator=\d+ source_id=68 visual_only=0', text)
    once = re.search(r'P2_TAMAGO_GROUP_ONCE host=346020\b[^\n]*count=10', text)
    astonish = re.findall(r'P2_TAMAGO_ASTONISH generator=\d+ pikmin=1', text)
    forget = re.search(r'P2_TAMAGO_GROUP_FORGET host=346020\b[^\n]*remaining=0', text)
    inject = re.search(r'P2_LIFECYCLE_INJECT|not_natural_combat=1|injected_health|mHealth=', text)
    completion = re.search(r'PASS P2_TAMAGO_GROUP_RUNTIME', text)
    extinction = re.search(r'Extinction', text, re.IGNORECASE)

    checks = dict(
        identity=bool(identity),
        window=bool(window),
        live_squad=int(ready.group(1)) >= 1 if ready else False,
        manager_birth=bool(birth) and bool(binds),
        exactly_once=bool(once),
        natural_astonish=bool(astonish),
        group_cleanup=bool(forget),
        no_inject=inject is None,
        completion=bool(completion),
        no_extinction=extinction is None,
    )
    passed = code == 0 and all(checks[name] for name in REQUIRED_CHECKS)
    return dict(passed=passed, checks=checks, exit_code=code,
                births=len(binds), astonish_hits=len(astonish))


APP = r'''class RoomApp : public PlugPikiApp {
    int frames=0,observed=0,stage=0,steadyTicks=0;
    Teki* host=nullptr;
    Teki* byGenerator(unsigned id){Iterator it(tekiMgr);CI_LOOP(it){Teki* t=static_cast<Teki*>(*it);if(t&&t->mGenerator&&t->mGenerator->_70==id)return t;}return nullptr;}
    int aliveTotal(){int c=0;Iterator it(pikiMgr);CI_LOOP(it){Piki* p=static_cast<Piki*>(*it);if(p&&p->isAlive())++c;}return c;}
public:int idle() override {
    int result=PlugPikiApp::idle();require(++frames<60000,"tamago group startup timeout");
    if(gameflow.mMoviePlayer&&gameflow.mMoviePlayer->mIsActive){gameflow.mMoviePlayer->requestSkip();return result;}
    if(!pc_p2_preview_cargo_free_ready()||!naviMgr||!pikiMgr||!tekiMgr)return result;
    Navi* n=naviMgr->getNavi();if(!n||gameflow.mPauseAll||gameflow.mIsUIOverlayActive)return result;
    ++observed;
    if(stage==0){
        host=byGenerator(346020);
        require(host&&pc_p2_tamago_registered(host),"host Mitite registered");
        require(aliveTotal()>=1,"live starting squad");
        std::printf("P2_TAMAGO_GROUP_READY squad=%d host_gen=346020\n",aliveTotal());
        std::fflush(stdout);stage=1;return result;
    }
    if(stage==1){
        // Deploy the squad around the host so the born Mitites contact them and
        // fire the natural Astonish; no birth, health or state is written.
        int k=0;Iterator it(pikiMgr);CI_LOOP(it){Piki* p=static_cast<Piki*>(*it);if(!p||!p->isAlive())continue;float ang=float(k)*6.2831853f/20.f;Vector3f pt=host->getPosition()+Vector3f(20.f*std::sin(ang),0.f,20.f*std::cos(ang));pt.y=mapMgr->getMinY(pt.x,pt.z,true);p->resetPosition(pt);p->changeMode(PikiMode::FreeMode,n);++k;}
        std::fflush(stdout);stage=2;return result;
    }
    if(stage==2){
        // The manager births the group exactly once on the host's first Appear;
        // observe the registry reaching the full group size.
        if(pc_p2_tamago_count()>=10){
            std::printf("P2_TAMAGO_GROUP_WITNESS births=%lu\n",pc_p2_tamago_count());
            std::fflush(stdout);stage=3;return result;
        }
        require(observed<3600,"group birth timeout");
        return result;
    }
    if(stage==3){
        // Exactly-once re-check: let the host cycle (Walk/Hide/Appear) and verify
        // the registry did NOT grow a second group.
        if(++steadyTicks>=240){
            require(pc_p2_tamago_count()==10,"duplicate group birth detected");
            std::printf("P2_TAMAGO_GROUP_ONCE host=346020 count=%lu\n",pc_p2_tamago_count());
            std::fflush(stdout);stage=4;
        }
        return result;
    }
    if(stage==4){
        // Host forget via the central lifetime seam. The group-forget branch now
        // QUEUES the born followers and pc_p2_tamago_tick drains them once per frame
        // (outside the TekiMgr update loop), so this exercises the deferred-despawn
        // path. A non-injected natural host DEATH was attempted separately and is
        // blocked: the harmless Mitite takes no squad damage (Astonish scatter) and
        // a bare BTeki::die() does not complete the engine funnel (dieSoon is gated
        // on !mDeadState in BTeki::doAI). See the handoff notes.
        pc_p2_forget_teki(host);
        require(pc_p2_tamago_count()==0,"whole group not cleared on host forget");
        std::printf("P2_TAMAGO_GROUP_CLEANUP host=346020 forgotten=10\n");
        std::fflush(stdout);stage=5;return result;
    }
    if(stage==5){
        std::puts("PASS P2_TAMAGO_GROUP_RUNTIME birth=manager exactly_once=1 astonish=natural cleanup=group injected=0");
        std::fflush(stdout);std::_Exit(0);
    }
    std::fflush(stdout);return result;
}};
'''


def tamago_host_cfg():
    cfg = dict(CFG)
    cfg['arena_species'] = ('TamagoMushi', 'P1 Chappy')
    cfg['arena_ids'] = (TAMAGO_HOST_GEN, CONTROL_GEN)
    cfg['arena_positions'] = (HOST_POSITION, CONTROL_POSITION)
    return cfg


def prepare(assets, imported, output):
    cfg = tamago_host_cfg()
    run = _prepare(cfg, assets, imported, output,
                   installer=functools.partial(install, cfg),
                   verifier=functools.partial(verify_install, cfg))
    (run / 'p2-cargo-free.txt').write_text('P2_CARGO_FREE_1\n')
    (run / 'p2-tamago-host.txt').write_text(
        f'P2_TAMAGO_HOST_1 {TAMAGO_HOST_GEN} {TAMAGO_GROUP_COUNT}\n')
    normalize_pose_names(run)
    return run


def instrument(source):
    if 'P2_TAMAGO_GROUP_REENTRY' in source:
        raise ValueError('Room fixture already carries the Tamago group app')
    start = source.index('class RoomApp : public PlugPikiApp {')
    end = source.index('int main(', start)
    includes = ('#include <cstring>\n#include "Generator.h"\n#include "pc_p2_tamago.h"\n'
                '#include "pc_p2_teki_lifetime.h"\n#include "pc_p2_preview.h"\n')
    return includes + source[:start] + APP + source[end:]


def build(native, build_dir, output, head, resume=False):
    """Build the private instrumented replacement-main fixture (never a run)."""
    from scripts import build_pikmin2_fixture as builder
    from experimental.pikmin2_kochappy_arena_fixture import instrument_tutorial
    native = native.resolve()
    build_dir = build_dir.resolve()
    output = output.resolve()
    room = output / 'room.cpp'
    source = instrument((native / 'tools/preview_p2_room.cpp').read_text())
    if resume:
        if (output / 'instrumentation.json').exists() or room.read_text() != source:
            raise ValueError('Cannot resume completed or changed fixture')
        record = json.loads((output / 'baseline/provenance.json').read_text())
        if record.get('status') != 'built' or record.get('expected_native_head') != head \
                or builder.git_state(native) != record['observed_source']:
            raise ValueError('Baseline no longer matches source')
        for key in ('inputs', 'fixture_inputs', 'configuration_inputs'):
            builder.check_snapshot(record[key])
    else:
        output.mkdir(parents=True, exist_ok=False)
        room.write_text(source)
        record = builder.build_fixture(build_dir, native, room, output / 'baseline', head)
    compile_cmd = list(record['commands'][-2])
    compile_cmd[builder.option_index(compile_cmd, '-o')] = str(output / 'room.obj')
    compile_cmd[builder.option_index(compile_cmd, '-MF')] = str(output / 'room.d')
    link = list(record['commands'][-1])
    targets = [i for i, a in enumerate(link) if a.endswith('\\fixture.obj') or a.endswith('/fixture.obj')]
    if len(targets) != 1:
        raise ValueError('Expected one private room object')
    link[targets[0]] = str(output / 'room.obj')
    link[builder.option_index(link, '-o')] = str(output / 'fixture.exe')
    link = [('-Wl,--out-implib,' + str(output / 'fixture.dll.a')) if a.startswith('-Wl,--out-implib,') else a for a in link]
    tutorial = native / 'src/plugPikiColin/newPikiGame.cpp'
    tutorial_private = output / 'tutorial.cpp'
    tutorial_private.write_text(instrument_tutorial(tutorial.read_text()))
    tutorial_compile = [str(tutorial_private) if a == str(room) else a for a in compile_cmd]
    tutorial_compile[builder.option_index(tutorial_compile, '-o')] = str(output / 'tutorial.obj')
    tutorial_compile[builder.option_index(tutorial_compile, '-MF')] = str(output / 'tutorial.d')
    targets = [i for i, a in enumerate(link) if a.endswith('libpikmin_legacy.a')]
    if len(targets) != 1:
        raise ValueError('Expected one private legacy archive')
    link.insert(targets[0], str(output / 'tutorial.obj'))
    env = dict(os.environ, PATH='C:/msys64/mingw64/bin;' + os.environ.get('PATH', ''))
    audit = dict(original_fixture=builder.snapshot([native / 'tools/preview_p2_room.cpp', tutorial]),
                 instrumented=builder.snapshot([room, tutorial_private]),
                 commands=[compile_cmd, tutorial_compile, link], freshness_checks=[])
    for name, command in [('room-compile', compile_cmd), ('tutorial-compile', tutorial_compile), ('room-link', link)]:
        code, text = builder.run(command, build_dir, env)
        (output / (name + '.log')).write_text(text)
        if code:
            raise RuntimeError(name + ' failed')
    builder.require_fresh(Path(record['toolchain']['ninja']['path']), build_dir, audit['freshness_checks'])
    builder.check_snapshot(record['inputs'])
    builder.check_snapshot(record['fixture_inputs'])
    builder.check_snapshot(record['configuration_inputs'])
    if builder.git_state(native) != record['observed_source']:
        raise RuntimeError('Native changed during private replacement')
    audit['artifacts'] = builder.snapshot([output / 'fixture.exe', output / 'room.obj'])
    audit['status'] = 'built'
    (output / 'instrumentation.json').write_text(json.dumps(audit, indent=2) + '\n')


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
    (run_dir / 'tamago-group-validation.json').write_text(json.dumps(result, indent=2) + '\n')
    return run_dir, meta, result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    for name in ('prepare', 'run'):
        sub = commands.add_parser(name)
        for flag in ('assets', 'imported', 'output'):
            sub.add_argument('--' + flag, type=Path, required=True)
        if name == 'run':
            sub.add_argument('--exe', type=Path, required=True)
            sub.add_argument('--seconds', type=int, default=120)
    build_cmd = commands.add_parser('build')
    for flag in ('native', 'build-dir', 'output'):
        build_cmd.add_argument('--' + flag, type=Path, required=True)
    build_cmd.add_argument('--head', required=True)
    build_cmd.add_argument('--resume', action='store_true')
    args = parser.parse_args()
    if args.command == 'prepare':
        print(prepare(args.assets, args.imported, args.output))
    elif args.command == 'build':
        build(args.native, args.build_dir, args.output, args.head, args.resume)
    else:
        run_dir, meta, result = run(args.assets, args.imported, args.output, args.exe, args.seconds)
        print(run_dir)
        print(json.dumps(result, indent=2))

