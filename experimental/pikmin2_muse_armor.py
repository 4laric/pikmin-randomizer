"""Muse Armor15 natural death/transport/re-entry observer (#165).

Lane `armor15-death-transport-reentry-observer`. Gates 4/5/6 (death_corpse,
transport_reward, cleanup_reentry); gates 1/2/3 are already natural PASS and
are preserved as-is, never relabelled. Family FSM/modules stay read-only under
the legacy lane-14 claim; no family change is requested.

Source facts (read-only retail + owned host on the wave base):
* The Armor actor is a TEKI_Chappy placement vehicle, so the generic Pod
  corpse path (`pc_p2_preview.cpp` corpses map + deliver branch) credits it
  with no shared or family edits. Receipt id shape is `corpse:<gen>` (plus the
  cave prefix, empty outside caves).
* The source damage receiver logs every decision (`P2_ARMOR_RECEIVER ...
  decision=accept/reject`); the weakpoint resolves at setup, so plain real
  Attack orders connect with no fixture flags, health writes or transport
  writes. Natural death = incremental accept decisions + monotonic observed
  drain to `P2_ARMOR_DEAD`, none of it written by the fixture.

This module stages a fresh Armor arena (lane-14 ground prepare with Sokkuri
parked, plus a staged Pod package for the corpse credit), builds the private
instrumented replacement-main fixture from the reserved App source, runs it,
and validates the native log via `validate()` - a dependency-free run-log
reader. `P2_MUSE_ARMOR_INJECT` / `P2_LIFECYCLE_INJECT` are never emitted by the
App; the reader rejects any run containing them, and the tests grep-assert the
App source contains no health or transport write.
"""

import argparse
import json
import os
import re
from pathlib import Path

import struct

from experimental.pikmin2_animation_profile import capture_command
from experimental.pikmin2_generator_pose import write_position
from scripts.preview_pikmin2_room import generator

# Sokkuri shares the lane-14 ground arena config (both actors must bind or the
# family setup aborts). It is parked far from the squad and never touched: an
# undisturbed bystander, documented so its presence is never read as scope.
SOKKURI_PARK = (330.0, 30.0, 1900.0)
POD_PACKAGE = os.environ.get(
    'PIKMIN_P2_POD_PACKAGE',
    str(Path(__file__).resolve().parents[2] / 'l19-out' / 'pod'))

READY_RE = re.compile(r'P2_MUSE_ARMOR_READY squad=(\d+) armor_gen=346001')
BIND_RE = re.compile(r'P2_ARMOR_BIND generator=346001 source_id=15 visual_only=0')
RECEIVER_ACCEPT_RE = re.compile(r'P2_ARMOR_RECEIVER generator=346001 decision=accept')
DEAD_RE = re.compile(r'P2_ARMOR_DEAD generator=346001 source_id=15 health=0')
CORPSE_RE = re.compile(r'P2_MUSE_ARMOR_CORPSE pellet=1 generator=346001')
RECEIPT_RE = re.compile(r'P2_POD_RECEIPT id=corpse:(?:armor:)?[^\s]*346001')
CARRY_RE = re.compile(r'P2_MUSE_ARMOR_CARRY [^\n]*\btransport=(\d+)')
NATURAL_DEATH_RE = re.compile(r'P2_MUSE_ARMOR_NATURAL_DEATH armor=1')
FORGET_RE = re.compile(r'P2_MUSE_ARMOR_FORGET count=0 registered=0')
REENTRY_RE = re.compile(r'P2_MUSE_ARMOR_REENTRY old=\S+ new=\S+ stale=0 fresh=1 count=1')
INJECT_RE = re.compile(r'P2_MUSE_ARMOR_INJECT|P2_LIFECYCLE_INJECT')
DRAIN_RE = re.compile(r'P2_MUSE_ARMOR_DRAIN events=(\d+) min=([\d.]+) start=([\d.]+)')
WINDOW_RE = re.compile(r'Experimental preview window set to 960x540 windowed and centered')
STAGED_WINDOW_RE = re.compile(r'P2_MUSE_ARMOR_WINDOW bittered=1 source=armor_module_input')
DEFAULT_MAX_HEALTH = 300.0  # pc_p2_armor.cpp LIFE

# Verbatim markers that would indicate a fixture health/transport write. The
# tests scan the reserved App source for these; validate() rejects the inject
# marker outright.
FORBIDDEN_FIXTURE_PATTERNS = (
    r'->mHealth\s*=',
    r'\.mHealth\s*=',
    r'mMode\s*=\s*PikiMode::TransportMode',
    r'P2_MUSE_ARMOR_INJECT',
    r'P2_LIFECYCLE_INJECT',
)


def validate(text, code=0):
    """Validate a muse-armor run log. Returns passed/checks/gates."""
    if not isinstance(text, str):
        raise ValueError('Expected a native log string')
    ready = READY_RE.search(text)
    squad = int(ready.group(1)) if ready else 0
    binds = bool(BIND_RE.search(text))
    accepts = len(RECEIVER_ACCEPT_RE.findall(text))
    natural_death = bool(NATURAL_DEATH_RE.search(text))
    dead = bool(DEAD_RE.search(text))
    drain = DRAIN_RE.search(text)
    drain_events = int(drain.group(1)) if drain else 0
    drain_min = float(drain.group(2)) if drain else float('inf')
    drain_start = float(drain.group(3)) if drain else 0.0
    # Natural drain: >= 2 observed health decreases ending at zero, started
    # from a positive max, and >= 2 receiver accepts proving real attacks
    # landed (no health was written by the fixture).
    drain_connects = (drain_events >= 2 and 0.0 < drain_min < drain_start
                      and drain_start > 0.0 and accepts >= 2)
    corpse = bool(CORPSE_RE.search(text))
    carry = [int(n) for n in CARRY_RE.findall(text)]
    receipt = bool(RECEIPT_RE.search(text))
    natural_carry = receipt and bool(carry) and max(carry) > 0
    cleanup = bool(FORGET_RE.search(text))
    reentry = bool(REENTRY_RE.search(text))
    injected = bool(INJECT_RE.search(text))
    no_inject = not injected
    window = bool(WINDOW_RE.search(text))
    session = (bool(re.search(r'P2_MUSE_ARMOR_SESSION navi=1\b', text))
               and not re.search(r'Extinction', text, re.IGNORECASE))
    completion = 'PASS P2_MUSE_ARMOR' in text
    checks = dict(
        binds=binds,
        window=window,
        live_squad=squad >= 1,
        staged_damage_window=bool(STAGED_WINDOW_RE.search(text)),
        natural_death=natural_death and dead and drain_connects and no_inject,
        corpse=corpse,
        natural_carry=natural_carry,
        cleanup=cleanup,
        reentry=reentry,
        session=session,
        completion=completion,
    )
    gates = dict(
        death_corpse=('pass' if (natural_death and dead and drain_connects and corpse
                                 and no_inject) else 'fail'),
        transport_reward=('pass' if (natural_carry and no_inject) else 'fail'),
        cleanup_reentry=('pass' if (cleanup and reentry) else 'fail'),
    )
    return dict(passed=(code == 0 and all(checks.values())), checks=checks,
                gates=gates, squad=squad, accepts=accepts, drain_events=drain_events,
                natural_vs_injected=dict(
                    natural_death=natural_death and dead and drain_connects,
                    natural_carry=natural_carry,
                    inject_present=injected))


POD_TREASURE_GENERATOR = 221004
POD_TREASURE_POSITION = (-150.0, 30.0, 1750.0)
POD_PACKAGE_FILES = ("p2-pod.txt", "pod.mod", "treasure.mod")


def _treasure_record(assets):
    """Clone the source pr05 treasure template into a Pod cargo record.

    Mirrors the wave-line Pod staging helper (the root base predates it) using
    only base-available helpers: no shared or family file is edited.
    """
    blob = generator(assets)
    starts = [i for i in range(len(blob)) if blob.startswith(b"    0.0v", i)]
    candidates = [blob[a:(starts[n + 1] if n + 1 < len(starts) else len(blob))]
                  for n, a in enumerate(starts)]
    source = next((r for r in candidates
                   if r[16:48].rstrip(b"\0") == b"preview treasure bolt"), None)
    if source is None or source[80:84] != b"50rp":
        raise ValueError("Source pr05 treasure template unavailable")
    record = bytearray(source)
    struct.pack_into("<I", record, 8, POD_TREASURE_GENERATOR)
    record[16:48] = b"P2 Armor pod cargo".ljust(32, b"\0")
    write_position(record, POD_TREASURE_POSITION)
    return bytes(record)


def _append_treasure(run, record):
    gen = run / "assets/dataDir/stages/chal0/default.gen"
    data = gen.read_bytes()
    starts = [m.start() for m in re.finditer(b"    0.0v", data)]
    count = struct.unpack_from(">I", data, 20)[0]
    if not starts or starts[0] != 24 or len(starts) != count:
        raise ValueError("Stage generator record framing mismatch")
    entries = [data[s:(starts[i + 1] if i + 1 < len(starts) else len(data))]
               for i, s in enumerate(starts)]
    if any(struct.unpack_from("<I", e, 8)[0] == POD_TREASURE_GENERATOR for e in entries):
        raise ValueError("Pod treasure generator already staged")
    if any(e[80:84] == b"50rp" for e in entries):
        raise ValueError("A pr05 treasure actor is already staged")
    gen.write_bytes(data[:20] + struct.pack(">I", count + 1) + b"".join(entries) + record)


def stage_pod(run, assets, package):
    """Stage the Pod + one pr05 treasure so the generic corpse credit works.

    Writes the converted pod/treasure models and the P2_POD_1 profile, appends
    the treasure record, and removes the arena's cargo-free marker (the native
    preview refuses cargo while it exists). No shared file is modified.
    """
    pkg = Path(package)
    missing = [name for name in POD_PACKAGE_FILES if not (pkg / name).is_file()]
    if missing:
        raise FileNotFoundError("Pod asset package incomplete at %s: missing %s"
                                % (pkg, ", ".join(missing)))
    profile = (pkg / "p2-pod.txt").read_text()
    parts = profile.split()
    if len(parts) != 7 or parts[0] != "P2_POD_1" or parts[5] != "Kochappy":
        raise ValueError("Invalid pod profile")
    room = run / "assets/dataDir/courses/pikmin2room"
    room.mkdir(parents=True, exist_ok=True)
    (room / "treasure.mod").write_bytes((pkg / "treasure.mod").read_bytes())
    (room / "pod.mod").write_bytes((pkg / "pod.mod").read_bytes())
    _append_treasure(run, _treasure_record(assets))
    marker = run / "p2-cargo-free.txt"
    if marker.exists():
        marker.unlink()
    (run / "p2-pod.txt").write_text(profile)
    (run / "p2-economy.txt").write_text("P2_ECONOMY_1\n")
    return dict(package=str(pkg), treasure_generator=POD_TREASURE_GENERATOR,
                position=list(POD_TREASURE_POSITION))


def prepare(assets, imported, output):
    """Stage a fresh Armor arena with a Pod.

    Reuses the lane-14 ground prepare/install (both family actors must bind)
    with Sokkuri parked far away, then stages the Pod + one pr05 treasure so
    the generic corpse credit has an anchor and a receipt path.
    """
    from experimental.pikmin2_batch2_core import prepare as _prepare
    from experimental.pikmin2_batch2_families import FAMILIES
    from experimental.pikmin2_ground_inverts_install import install, verify_install
    cfg = dict(FAMILIES["ground"])
    positions = list(cfg["arena_positions"])
    index = tuple(cfg["arena_species"]).index("Sokkuri")
    positions[index] = SOKKURI_PARK
    cfg["arena_positions"] = tuple(positions)
    run = _prepare(cfg, Path(assets), Path(imported), Path(output),
                   installer=install, verifier=verify_install)
    try:
        from experimental.pikmin2_sokkuri_behavior import normalize_pose_names
        override = dict(reason="park Sokkuri far away; Armor stays under the squad",
                        production_placement=False)
        override["pose_name_normalization"] = normalize_pose_names(run)
        (run / "muse-armor-override.json").write_text(json.dumps(override, indent=2) + "\n")
    except Exception:
        (run / "muse-armor-override.json").write_text(json.dumps(dict(
            reason="park Sokkuri far away; Armor stays under the squad",
            production_placement=False), indent=2) + "\n")
    run = Path(run)
    stage_pod(run, Path(assets), POD_PACKAGE)
    (run / "pikmin_settings.conf").write_text("disableTutorials = 0\n")
    return run


def instrument(source, app=None):
    """Splice the reserved Armor App into preview_p2_room.cpp."""
    if app is None:
        raise ValueError('muse armor fixture source text required')
    if 'P2_MUSE_ARMOR_READY' in source:
        raise ValueError('Room fixture already carries the muse armor app')
    start = source.index('class RoomApp : public PlugPikiApp {')
    end = source.index('int main(', start)
    includes = ('#include <cstring>\n#include <cstdlib>\n#include <cstdio>\n'
                '#include "Generator.h"\n#include "pc_p2_armor.h"\n'
                '#include "pc_p2_preview.h"\n#include "CinematicPlayer.h"\n'
                '#include "GameStat.h"\n#include "NaviState.h"\n')
    return includes + source[:start] + app + source[end:]


def _expand_response_line(line, build):
    """Splice on-disk @response-file contents into one Ninja command line."""
    def replace(match):
        path = match.group(1) or match.group(2)
        resolved = Path(path.replace("\\", "/"))
        if not resolved.is_absolute():
            resolved = (Path(build) / resolved).resolve()
        if not resolved.is_file():
            raise ValueError("Missing Ninja response file: " + path)
        return resolved.read_text(encoding="utf-8", errors="replace").strip()
    return re.sub(r'@(?:"([^"]+)"|(\S+))', replace, line)


def _expand_response_files(commands, build):
    """Expand Ninja response files the way the newer integration builder does.

    Bounded compatibility shim for the lane's pinned/canonical
    `scripts/build_pikmin2_fixture.py`, whose `windows_args` rejects the
    `@CMakeFiles\\*.rsp` token the host toolchain emits for the `pikmin_pc`
    link/archive steps. Ninja deletes rsp files after a run, so expansion asks
    Ninja itself via `-t compdb` / `-t compdb -x` and falls back to reading an
    on-disk rsp when present. The shared builder is NOT edited: `build()`
    wraps only its `select_commands` call for the duration of this build.
    """
    if not any("@" in line and ".rsp" in line for line in commands):
        return commands
    from scripts import build_pikmin2_fixture as builder
    cache = {}
    for line in (Path(build) / "CMakeCache.txt").read_text(encoding="utf-8").splitlines():
        if line and not line.startswith(("#", "//")) and "=" in line:
            key, value = line.split("=", 1)
            cache[key.split(":")[0]] = value
    ninja = cache["CMAKE_MAKE_PROGRAM"]
    databases = []
    for options in ([], ["-x"]):
        code, data = builder.run([ninja, "-t", "compdb", *options], build)
        if code:
            raise ValueError("Ninja cannot expand response files through compdb")
        databases.append(json.loads(data))
    raw, expanded = databases
    if len(raw) != len(expanded):
        raise ValueError("Ninja graph changed during response expansion")
    replacements = {}
    for before, after in zip(raw, expanded):
        if (before["file"], before["output"]) != (after["file"], after["output"]):
            raise ValueError("Ninja graph changed during response expansion")
        replacements[before["command"]] = after["command"]
    lines = []
    for line in commands:
        if "@" in line and ".rsp" in line:
            replacement = replacements.get(line)
            if replacement is not None and "@" not in replacement.split()[-1:]:
                if not ("@" in replacement and ".rsp" in replacement):
                    line = replacement
                else:
                    line = _expand_response_line(line, build)
            else:
                line = _expand_response_line(line, build)
            if "@" in line and ".rsp" in line:
                raise ValueError("Ninja response command is missing or unexpanded")
        lines.append(line)
    return lines


def build(native, build_dir, output, head, fixture_cpp, resume=False):
    """Build the private instrumented Armor fixture (never a run)."""
    from scripts import build_pikmin2_fixture as builder
    from experimental.pikmin2_kochappy_arena_fixture import instrument_tutorial
    native = Path(native).resolve()
    build_dir = Path(build_dir).resolve()
    output = Path(output).resolve()
    app = Path(fixture_cpp).read_text()
    room = output / 'room.cpp'
    source = instrument((native / 'tools/preview_p2_room.cpp').read_text(), app)
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
        # See _expand_response_line: wrap only the canonical builder's command
        # parsing so on-disk Ninja response files are spliced before the shared
        # windows_args check. The shared script is untouched.
        original_select = builder.select_commands

        def expanded_select(commands, src, bld):
            return original_select(_expand_response_files(commands, bld), src, bld)

        builder.select_commands = expanded_select
        try:
            record = builder.build_fixture(build_dir, native, room, output / 'baseline', head)
        finally:
            builder.select_commands = original_select
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
    record = json.loads((output / 'baseline/provenance.json').read_text())
    record.setdefault('artifacts', {})[str(output / 'fixture.exe')] = dict(
        audit['artifacts'][str(output / 'fixture.exe')], role='linked-run-executable')
    (output / 'baseline/provenance.json').write_text(json.dumps(record, indent=2) + '\n')


def run(assets, imported, output, exe, seconds=250):
    os.environ['PIKMIN_P2_ROOM_WINDOW'] = '960x540'
    os.environ['PATH'] = 'C:\\msys64\\mingw64\\bin;' + os.environ.get('PATH', '')
    run_dir = prepare(Path(assets), Path(imported), Path(output))
    meta = capture_command([str(Path(exe).resolve()), '--experimental-pikmin2-room'],
                           run_dir, run_dir / 'capture', seconds)
    text = (run_dir / 'capture' / 'native.log').read_text(errors='replace')
    result = validate(text, meta['exit_code'])
    result['capture'] = {k: meta[k] for k in ('executable_sha256', 'elapsed_seconds',
                                              'exit_code', 'timed_out')}
    (run_dir / 'muse-armor-validation.json').write_text(json.dumps(result, indent=2) + '\n')
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
            sub.add_argument('--seconds', type=int, default=250)
    build_cmd = commands.add_parser(name='build')
    for flag in ('native', 'build-dir', 'output', 'fixture'):
        build_cmd.add_argument('--' + flag, type=Path, required=True)
    build_cmd.add_argument('--head', required=True)
    build_cmd.add_argument('--resume', action='store_true')
    args = parser.parse_args()
    if args.command == 'prepare':
        print(prepare(args.assets, args.imported, args.output))
    elif args.command == 'build':
        build(args.native, args.build_dir, args.output, args.head, args.fixture, args.resume)
    else:
        run_dir, meta, result = run(args.assets, args.imported, args.output, args.exe, args.seconds)
        print(run_dir)
        print(json.dumps(result, indent=2))
