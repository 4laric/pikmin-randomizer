"""Two-identity mixed-scene probe: Dwarf Orange Bulborb + P1 control + Snow Bulborb.

Stages one private original-Impact-Site arena on the lane-13 native build that
contains both the ``pc_p2_dwarf_orange`` module (source BlueKochappy 44) and the
maintained Snow Bulborb module (YellowKochappy fp00 visual). A single
``dataDir/stages/chal0/default.gen`` carries:

* generator 211001, ``TEKI_Chappy`` -> Dwarf Orange Bulborb (health 250);
* generator 211002, ``TEKI_Chappy`` -> ordinary P1 Chappy control;
* generator 5001, ``TEKI_Chappy`` -> Snow Bulborb (health policy 150);

plus exactly 20 red starting Pikmin. Snow configs, the sampled pose bank, the
Pod anchor required by the Snow setup gate and the Dwarf Orange bank/profile are
installed byte-exactly from read-only sources. The fixture observer tolerates a
three-Teki roster (the old Dwarf Orange observer hardcodes two), asserts the
shared spawn identity of all three, forces a draw of each visual with a captain
reposition stimulus and records the native rolling ``[PC tick]`` timing.

Usage::

    py -3.12 -m experimental.pikmin2_mixed_bulborb_runtime build \
        --native <native worktree> --build-dir <build> --output <dir> --head <sha>
    py -3.12 -m experimental.pikmin2_mixed_bulborb_runtime prepare \
        --assets <P1 assets> --bank <bank dir> --profile <profile dir> \
        --snow <snow prepared dir> --output <dir>
    py -3.12 -m experimental.pikmin2_mixed_bulborb_runtime run \
        --stage <run dir> --exe <fixture.exe> --output <dir>
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import struct
import statistics
import subprocess
from pathlib import Path

from scripts import build_pikmin2_fixture as builder

ID_DWARF = 211001
ID_CONTROL = 211002
ID_SNOW = 5001
DWARF_HEALTH = 250
SNOW_HEALTH = 150
SNOW_SPECIES = 'YellowKochappy'
SNOW_DISPLAY = 'Snow Bulborb'
POSITIONS_FILE = 'mixed-arena-positions.txt'
MANIFEST = 'mixed-arena.json'
SNOW_POLICY = 'P2_SNOW_POLICY_1\nhealth 150\n'

# The Snow animation setup aborts unless a Pod anchor exists
# (pc_p2_preview_goal().pc_p2_snow_setup). The Pod is staged from the read-only
# Snow preparation and is a hard prerequisite of the maintained Snow module.
POD_CONFIG = 'p2-pod.txt'


def _append_rows(path, rows):
    records = rows
    path.write_bytes(path.read_bytes()[:20] +
                     struct.pack('>I', len(records)) + b''.join(records))


def snow_row(template, identity, name, position):
    """Copy an audited ``iket`` enemy template into a distinct Snow generator row."""
    if len(template) < 96 or template[72:76] != b'iket':
        raise ValueError('Expected an enemy generator template')
    if template[80] != 3:
        raise ValueError('Expected a TEKI_Chappy template')
    from experimental.pikmin2_generator_pose import write_position
    row = bytearray(template)
    struct.pack_into('<I', row, 8, identity)
    row[16:48] = name.encode('ascii')[:32].ljust(32, b'\0')
    write_position(row, position)
    return bytes(row)


def _install_snow(snow, run, generator):
    """Install p2-snow.txt, actor bindings, policy and all snow_*.mod bank files."""
    snow = Path(snow)
    room_source = snow / 'assets/dataDir/courses/pikmin2room'
    bank = (snow / 'p2-snow.txt').read_text()
    if not bank.startswith('P2_SNOW_'):
        raise ValueError('Expected a Snow animation bank')
    mods = sorted(room_source.glob('snow_*.mod'))
    if not mods:
        raise ValueError('Missing Snow pose bank')
    room = run / 'assets/dataDir/courses/pikmin2room'
    if not room.is_dir() or room.is_symlink() or room.is_junction():
        raise ValueError('Expected a private room directory')
    for mod in mods:
        shutil.copyfile(mod, room / mod.name)
    (run / 'p2-snow.txt').write_text(bank)
    (run / 'p2-snow-actors.txt').write_text(
        'P2_SNOW_ACTORS_1 1\n' + str(generator) + '\n')
    (run / 'p2-snow-policy.txt').write_text(SNOW_POLICY)
    pod = room_source / 'pod.mod'
    if not pod.is_file() or not (snow / POD_CONFIG).is_file():
        raise ValueError('Missing Pod anchor required by the Snow setup gate')
    shutil.copyfile(pod, room / 'pod.mod')
    (run / POD_CONFIG).write_text((snow / POD_CONFIG).read_text())
    return dict(pose_bank=len(mods), policy=SNOW_POLICY.split()[0])


def prepare(assets, bank, profile, snow, output):
    """Stage the mixed arena from the audited Dwarf Orange arena plus Snow assets."""
    from experimental.pikmin2_dwarf_orange_arena import prepare as dwarf_arena
    from scripts.preview_pikmin2_room import generator, records
    from experimental.pikmin2_uji_grounded_fixture import deterministic_births
    from experimental.pikmin2_generator_pose import write_position

    run = dwarf_arena(assets, bank, profile, output)
    stage = run / 'assets/dataDir/stages/chal0/default.gen'
    rows = list(records(stage))
    used = {struct.unpack_from('<I', r, 8)[0] for r in rows}
    if {ID_DWARF, ID_CONTROL} - used:
        raise ValueError('Dwarf Orange arena roster missing')
    if ID_SNOW in used:
        raise ValueError('Snow generator ID collision')
    # Source the untouched enemy template from the generator fixture: the dwarf
    # arena rows have already had their scatter radius zeroed in place.
    blob = generator(Path(assets).resolve())
    starts = [i for i in range(len(blob)) if blob.startswith(b'    0.0v', i)]
    candidates = [blob[a:(starts[n + 1] if n + 1 < len(starts) else len(blob))]
                  for n, a in enumerate(starts)]
    template = next(r for r in candidates
                    if r[72:76] == b'iket' and len(r) >= 96 and r[80] == 3)
    snow_at = (-150.0, 30.0, 1700.0)
    rows.append(snow_row(template, ID_SNOW, SNOW_DISPLAY, snow_at))
    _append_rows(stage, rows)

    # Exactly twenty red Pikmin: the overlay already appended a starting squad,
    # so top up defensively and never exceed the target.
    rows = list(records(stage))
    used = {struct.unpack_from('<I', r, 8)[0] for r in rows}
    squad = [r for r in rows if r[72:76] == b'ikip']
    if len(squad) < 20:
        template = next((r for r in rows if r[72:76] == b'ikip'), None)
        if template is None:
            raise ValueError('No Pikmin template for squad top-up')
        for i in range(20 - len(squad)):
            identity = 187000 + i
            while identity in used:
                identity += 1
            used.add(identity)
            row = bytearray(template)
            struct.pack_into('<I', row, 8, identity)
            struct.pack_into('>I', row, 84, 1)
            write_position(row, (-400. + i % 5 * 8, 30., 1800. + i // 5 * 8))
            rows.append(bytes(row))
        _append_rows(stage, rows)
    if len([r for r in records(stage) if r[72:76] == b'ikip']) != 20:
        raise ValueError('Mixed arena must carry exactly twenty red Pikmin')

    birth = deterministic_births(stage, [ID_SNOW])
    snow_install = _install_snow(snow, run, ID_SNOW)

    actors = [dict(generator=ID_DWARF, species='BlueKochappy',
                   display='Dwarf Orange Bulborb', expected_xyz=[-150., 30., 1850.]),
              dict(generator=ID_CONTROL, species='P1 Chappy',
                   display='P1 Chappy', expected_xyz=[150., 30., 1550.]),
              dict(generator=ID_SNOW, species=SNOW_SPECIES,
                   display=SNOW_DISPLAY, expected_xyz=list(snow_at))]
    (run / MANIFEST).write_text(json.dumps(dict(
        schema=1, scene='P1 Impact Site (chal0)', enemy_count=3,
        window='960x540', reds=20, actors=actors, snow_install=snow_install,
        snow_birth=birth,
        injected=['mixed-arena-positions.txt', 'mixed-arena.json'],
        natural_native_markers=['P2_ENEMY_READY', 'P2_DWARF_ORANGE_BANK',
                                'P2_SNOW_BANK', 'P2_SNOW_POLICY',
                                'P2_DWARF_ORANGE_DRAW', 'P2_SNOW_DRAW'],
        limitations=['Native Snow module reports P2_ENEMY_READY species=YellowKochappy '
                     '(source id); Snow Bulborb is its pc_p2_enemy_name display name.',
                     'Snow actor display identity is asserted by the private observer, '
                     'not by a native species=Snow Bulborb marker.',
                     'Engineered arena coordinates and zero scatter radius; no terrain or '
                     'production placement claim.'],
        ), indent=2))
    return run


def positions(stage):
    stage = Path(stage)
    manifest = json.loads((stage / MANIFEST).read_text())
    actors = manifest['actors']
    if len(actors) != 3:
        raise ValueError('Expected three mixed actors')
    (stage / POSITIONS_FILE).write_text(''.join(
        str(a['generator']) + ' ' + ' '.join(map(str, a['expected_xyz'])) + '\n'
        for a in actors))
    return actors


APP = r'''class RoomApp : public PlugPikiApp {
    int frames=0,observed=0;
    Teki* dwarf=nullptr;Teki* control=nullptr;Teki* snow=nullptr;
public:
    int idle() override {
        int result=PlugPikiApp::idle();require(++frames<10000,"mixed arena timeout");
        if(gameflow.mMoviePlayer && gameflow.mMoviePlayer->mIsActive){gameflow.mMoviePlayer->requestSkip();return result;}
        if(!pc_p2_preview_cargo_free_ready() || !naviMgr || !tekiMgr || !pikiMgr)return result;
        Navi* n=naviMgr->getNavi();if(!n || gameflow.mPauseAll || gameflow.mIsUIOverlayActive)return result;
        if(++observed==1){
            for(int f=0;f<DEMOFLAG_COUNT;++f)playerState->mDemoFlags.setFlagOnly(f);
            std::ifstream input("mixed-arena-positions.txt");unsigned id;float x,y,z;int expected=0;
            while(input>>id>>x>>y>>z){
                Teki* actor=nullptr;int matches=0;Iterator e(tekiMgr);CI_LOOP(e){Teki* a=static_cast<Teki*>(*e);if(a->mGenerator && a->mGenerator->_70==id){actor=a;++matches;}}
                require(matches==1 && actor->mTekiType==TEKI_Chappy,"mixed arena identity count/type");
                Vector3f birth=actor->mPersonality->mPosition,gen=actor->mGenerator->getPos();
                require(std::fabs(birth.x-x)<.02 && std::fabs(birth.y-y)<.02 && std::fabs(birth.z-z)<.02,"mixed arena stored birth XYZ");
                require(std::fabs(gen.x-x)<.02 && std::fabs(gen.y-y)<.02 && std::fabs(gen.z-z)<.02,"mixed arena generator XYZ");
                const char* display=pc_p2_enemy_name(actor);const char* dwarfName=pc_p2_dwarf_orange_name(actor);
                float fallback=actor->mTekiParams->getF(TPF_Life);
                if(id==211001){dwarf=actor;require(!display && dwarfName && !std::strcmp(dwarfName,"Dwarf Orange Bulborb"),"mixed dwarf display");
                    require(actor->mHealth==250 && actor->getParameterF(TPF_Life)==250,"mixed dwarf health");}
                else if(id==211002){control=actor;require(!display && !dwarfName && actor->mHealth==fallback && actor->getParameterF(TPF_Life)==fallback,"mixed control health");}
                else if(id==5001){snow=actor;require(display && !std::strcmp(display,"Snow Bulborb"),"mixed snow display");
                    require(actor->mHealth==150 && actor->getParameterF(TPF_Life)==150,"mixed snow health");}
                else require(false,"unexpected mixed arena generator");
                std::printf("P2_MIXED_ARENA_BIRTH id=%u x=%.3f y=%.3f z=%.3f health=%.1f fallback=%.1f display=%s\n",id,birth.x,birth.y,birth.z,actor->mHealth,fallback,display?display:(dwarfName?dwarfName:"-"));++expected;
            }
            require(expected==3,"mixed arena expected three actors");
            int live=0;Iterator all(tekiMgr);CI_LOOP(all){Teki* a=static_cast<Teki*>(*all);if(a->isAlive())++live;}
            int reds=0;Iterator p(pikiMgr);CI_LOOP(p){Piki* v=static_cast<Piki*>(*p);if(v->isAlive() && v->mColor==Red)++reds;}
            std::printf("P2_MIXED_ARENA_SPAWN teki=%d reds=%d\n",live,reds);
            require(live==3,"mixed arena expected three live Teki");
            require(reds==20,"expected twenty field reds");
            std::printf("P2_MIXED_SNOW_DISPLAY name=Snow Bulborb generator=%u source_marker=P2_ENEMY_READY species=%s\n",snow?snow->mGenerator->_70:0,"YellowKochappy");
            Vector3f stimulus=dwarf->getPosition()+Vector3f(70,0,0);stimulus.y=mapMgr->getMinY(stimulus.x,stimulus.z,true);n->resetPosition(stimulus);
            std::printf("P2_MIXED_STIMULUS tick=1 target=dwarf\n");
        }
        if(observed==90 && snow){Vector3f stimulus=snow->getPosition()+Vector3f(70,0,0);stimulus.y=mapMgr->getMinY(stimulus.x,stimulus.z,true);n->resetPosition(stimulus);
            std::printf("P2_MIXED_STIMULUS tick=90 target=snow\n");}
        if(observed%60==0){Iterator e(tekiMgr);CI_LOOP(e){Teki* a=static_cast<Teki*>(*e);if(!a->mGenerator)continue;
            std::printf("P2_MIXED_TICK tick=%d id=%u alive=%d health=%.1f\n",observed,a->mGenerator->_70,int(a->isAlive()),a->mHealth);}}
        if(observed==60)capture("mixed-arena.ppm");
        if(observed>=240){
            int reds=0;Iterator p(pikiMgr);CI_LOOP(p){Piki* v=static_cast<Piki*>(*p);if(v->isAlive() && v->mColor==Red)++reds;}
            std::printf("P2_MIXED_ARENA_DONE tick=%d reds=%d\n",observed,reds);
            std::puts("PASS P2 mixed Dwarf Orange + Snow Bulborb observation");std::fflush(stdout);std::_Exit(0);
        }
        std::fflush(stdout);return result;
    }
};
'''


def instrument(source):
    """Replace the room observer with a three-Teki-tolerant mixed-scene observer."""
    start = source.index('class RoomApp : public PlugPikiApp {')
    end = source.index('int main(', start)
    if 'P2_MIXED_ARENA_SPAWN' in source:
        raise ValueError('Already instrumented')
    prefix = ('#include <fstream>\n#include <cstring>\n#include "Generator.h"\n'
              '#include "pc_p2_enemy.h"\n#include "pc_p2_dwarf_orange.h"\n')
    return prefix + source[:start] + APP + source[end:]


TICK_HEADER = re.compile(r'\[PC tick\] last (\d+) ticks, budget ([-+\d.]+) ms')
TICK_ROW = re.compile(r'^\s*(\S+)\s+mean\s+([-+\d.]+)\s+p50\s+([-+\d.]+)\s+'
                      r'p95\s+([-+\d.]+)\s+p99\s+([-+\d.]+)\s+worst\s+([-+\d.]+)\s*$')


def tick_stats(log):
    """Native rolling ``[PC tick]`` windows; the ``tick`` row is measured ms."""
    windows, current = [], None
    for line in log.splitlines():
        header = TICK_HEADER.search(line)
        if header:
            current = dict(samples=int(header[1]), budget_ms=float(header[2]), regions={})
            windows.append(current)
            continue
        if current is None:
            continue
        row = TICK_ROW.match(line)
        if row:
            current['regions'][row[1]] = dict(zip(
                ('mean', 'p50', 'p95', 'p99', 'worst'), map(float, row.groups()[1:])))
    ticks = [w['regions']['tick'] for w in windows if 'tick' in w['regions']]
    if not ticks:
        return dict(windows=0, mean_tick_ms=None, last_tick_ms=None,
                    slowest_window_tick_ms=None, budget_ms=None, last_tick_p95_ms=None)
    return dict(windows=len(ticks),
                mean_tick_ms=statistics.mean(t['mean'] for t in ticks),
                last_tick_ms=ticks[-1]['mean'],
                slowest_window_tick_ms=max(t['mean'] for t in ticks),
                budget_ms=windows[-1]['budget_ms'],
                last_tick_p95_ms=ticks[-1]['p95'])


def evidence(log, exit_code):
    stats = tick_stats(log)
    checks = {
        'completion': 'PASS P2 mixed Dwarf Orange + Snow Bulborb observation' in log,
        'dwarf_ready': 'P2_ENEMY_READY species=BlueKochappy source_id=44' in log,
        'snow_ready': 'P2_ENEMY_READY species=YellowKochappy' in log,
        'snow_policy': 'P2_SNOW_POLICY' in log,
        'snow_bank': 'P2_SNOW_BANK poses=' in log,
        'dwarf_bank': 'P2_DWARF_ORANGE_BANK' in log,
        'snow_display': 'P2_MIXED_SNOW_DISPLAY name=Snow Bulborb' in log,
        'dwarf_draw': 'P2_DWARF_ORANGE_DRAW corpse=0' in log,
        'snow_draw': 'P2_SNOW_DRAW corpse=0' in log,
        'spawn_three': 'P2_MIXED_ARENA_SPAWN teki=3 reds=20' in log,
        'window': '960x540' in log,
        'no_extinction': 'Extinction' not in log,
        'tick_measured': stats['mean_tick_ms'] is not None,
    }
    return dict(
        schema=1, exit_code=exit_code, passed=exit_code == 0 and all(checks.values()),
        checks=checks, missing=[k for k, v in checks.items() if not v],
        tick=stats, rows=[line for line in log.splitlines()
                          if line.startswith('P2_MIXED_ARENA_BIRTH ')],
        scope='Private three-Teki spawn observation with captain reposition stimulus; '
              'the 20-red overlay and zero-scatter radius are fixture choices.',
        unmeasured=['player input', 'combat', 'corpse delivery', 'generated-session admission',
                    'production frame budget'],
        injected=['P2_MIXED_ARENA_BIRTH', 'P2_MIXED_ARENA_SPAWN', 'P2_MIXED_SNOW_DISPLAY',
                  'P2_MIXED_STIMULUS', 'P2_MIXED_TICK', 'P2_MIXED_ARENA_DONE'],
        natural=['P2_ENEMY_READY species=BlueKochappy ...', 'P2_DWARF_ORANGE_BANK',
                 'P2_DWARF_ORANGE_DRAW', 'P2_ENEMY_READY species=YellowKochappy ...',
                 'P2_SNOW_POLICY', 'P2_SNOW_BANK', 'P2_SNOW_DRAW', '[PC tick]'])


def running_games():
    """Names of a running game process, or ``None`` if the query is unavailable."""
    found = []
    for name in ('nectar.exe', 'fixture.exe'):
        try:
            result = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq ' + name, '/NH'],
                                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                    text=True, timeout=30)
        except (OSError, subprocess.SubprocessError):
            return None
        if name.lower() in (result.stdout or '').lower():
            found.append(name)
    return found


def run(stage, exe, output, timeout=180):
    from experimental.pikmin2_animation_profile import capture_command
    stage, output = Path(stage).resolve(), Path(output).resolve()
    active = running_games()
    if active is None:
        raise RuntimeError('Cannot confirm no game is running; refusing to launch')
    if active:
        raise RuntimeError('Another game is running: ' + ', '.join(active))
    positions(stage)
    os.environ['PIKMIN_P2_ROOM_WINDOW'] = '960x540'
    meta = capture_command([str(Path(exe).resolve()), '--experimental-pikmin2-room'],
                           stage, output, timeout)
    report = evidence((output / 'native.log').read_text(errors='replace'), meta['exit_code'])
    report['capture'] = meta
    report['arena_sha256'] = hashlib.sha256((stage / MANIFEST).read_bytes()).hexdigest()
    report['positions_sha256'] = hashlib.sha256((stage / POSITIONS_FILE).read_bytes()).hexdigest()
    (output / 'evidence.json').write_text(json.dumps(report, indent=2))
    return report


def build_fixture_for(instrument_fn, native, build_dir, output, head):
    native, build_dir, output = (Path(p).resolve() for p in (native, build_dir, output))
    output.mkdir(parents=True, exist_ok=False)
    room = output / 'room.cpp'
    room.write_text(instrument_fn((native / 'tools/preview_p2_room.cpp').read_text()))
    record = builder.build_fixture(build_dir, native, room, output / 'baseline', head)
    exe = output / 'baseline' / 'fixture.exe'
    print(exe)
    return exe, record


def build(native, build_dir, output, head):
    return build_fixture_for(instrument, native, build_dir, output, head)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    b = sub.add_parser('build')
    for name in ('native', 'build-dir', 'output'):
        b.add_argument('--' + name, type=Path, required=True)
    b.add_argument('--head', required=True)
    p = sub.add_parser('prepare')
    for name in ('assets', 'bank', 'profile', 'snow', 'output'):
        p.add_argument('--' + name, type=Path, required=True)
    r = sub.add_parser('run')
    for name in ('stage', 'exe', 'output'):
        r.add_argument('--' + name, type=Path, required=True)
    r.add_argument('--timeout', type=int, default=180)
    args = parser.parse_args()
    if args.command == 'build':
        build(args.native, args.build_dir, args.output, args.head)
    elif args.command == 'prepare':
        print(prepare(args.assets, args.bank, args.profile, args.snow, args.output))
    else:
        print(json.dumps({k: v for k, v in
                          run(args.stage, args.exe, args.output, args.timeout).items()
                          if k != 'rows'}, indent=2))
