"""Build the P1 Challenge guarded boot fixture (prerequisite lane, #649).

Splices the owned RoomApp fragment into tools/preview_p2_room.cpp, swaps the
main entry require from the room flag to the challenge-level flag, and links
a provenance-checked replacement-main fixture through the shared fixture
builder (unmodified). Usage mirrors the other lane builders.
"""
import argparse
import json
import os
from pathlib import Path

from scripts import build_pikmin2_fixture as builder

FIXTURE_BEGIN = '// MUSE-CHALLENGE-BOOT-INCLUDES-BEGIN'
FIXTURE_SPLIT = '// MUSE-CHALLENGE-BOOT-INCLUDES-END'
FIXTURE_APP = '// MUSE-CHALLENGE-BOOT-APP-BEGIN'
FIXTURE_END = '// MUSE-CHALLENGE-BOOT-APP-END'
ROOM_REQUIRE = 'require(pc_pikipelago_room_preview(),"requires --experimental-pikmin2-room");'
CHALLENGE_REQUIRE = ('require(pc_pikipelago_challenge_level()>=0 && !pc_pikipelago_room_preview(),'
                     '"requires --experimental-challenge-level 0-4");')


def fixture_path(native=None):
    """Resolve the tracked fixture source."""
    root = Path(native) if native is not None else Path(__file__).resolve().parent.parent
    path = root / 'tools' / 'p2_challenge_guarded_boot_fixture.cpp'
    if not path.is_file():
        raise ValueError('Missing tracked challenge boot fixture: ' + str(path))
    return path


def fixture_sections(native=None, text=None):
    """Split the tracked fixture into (includes, app) splice sections."""
    if text is None:
        text = fixture_path(native).read_text(encoding='utf-8')
    try:
        includes = text.split(FIXTURE_BEGIN, 1)[1].split(FIXTURE_SPLIT, 1)[0]
        app = text.split(FIXTURE_APP, 1)[1].split(FIXTURE_END, 1)[0]
    except IndexError as error:
        raise ValueError('Challenge boot fixture section markers missing') from error
    if 'class RoomApp : public PlugPikiApp {' not in app:
        raise ValueError('Challenge boot fixture RoomApp missing')
    return includes, app


def instrument(source, app, _unused_includes=None):
    """Splice the fragment into a room.cpp copy and retarget its main entry."""
    start = source.index('class RoomApp : public PlugPikiApp {')
    end = source.index('int main(', start)
    room = ('#include <fstream>\n#include "Generator.h"\n#include "TekiPersonality.h"\n'
            + source[:start] + app + source[end:])
    if ROOM_REQUIRE not in room:
        raise ValueError('Room main entry require anchor missing')
    return room.replace(ROOM_REQUIRE, CHALLENGE_REQUIRE, 1)


def build(native, build_dir, output, head, resume=False):
    """Build the replacement-main fixture with provenance (shared builder)."""
    native = Path(native).resolve()
    build_dir = Path(build_dir).resolve()
    output = Path(output).resolve()
    room = output / 'room.cpp'
    includes, app = fixture_sections(native)
    source = instrument((native / 'tools/preview_p2_room.cpp').read_text(), includes + app)
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
    from experimental.pikmin2_kogane_runtime import instrument_tutorial
    tutorial_private.write_text(instrument_tutorial(tutorial.read_text()))
    tutorial_compile = [str(tutorial_private) if a == str(room) else a for a in compile_cmd]
    tutorial_compile[builder.option_index(tutorial_compile, '-o')] = str(output / 'tutorial.obj')
    tutorial_compile[builder.option_index(tutorial_compile, '-MF')] = str(output / 'tutorial.d')
    targets = [i for i, a in enumerate(link) if a.endswith('-libpikmin_legacy.a')]
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


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--native', type=Path, required=True)
    parser.add_argument('--build-dir', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--head', required=True)
    parser.add_argument('--resume', action='store_true')
    args = parser.parse_args()
    build(args.native, args.build_dir, args.output, args.head, args.resume)