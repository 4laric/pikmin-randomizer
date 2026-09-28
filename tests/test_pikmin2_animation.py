import json
import os
from pathlib import Path
import shutil
import struct
import subprocess

import pytest

from experimental.pikmin2_animation import (CLIPS, CLIP_BYTES, parse_bank, resource_chunks,
                                           sample_frames, validate_files)
from experimental.pikmin2_enemy import install


def manifest(version=2):
    return f'P2_SNOW_{version}\n' + ''.join(
        f'{name} 3 9' + (' 0 4 8' if version == 2 else '') + '\n' for name in CLIPS)


def mesh(pixel=b'pixels'):
    return b''.join(struct.pack('>II', tag, len(data)) + data for tag, data in
                    ((16, b'pose'), (32, pixel), (34, b'attr'), (48, b'material'), (65535, b'')))


def bank_files(directory):
    directory.mkdir()
    bank = parse_bank(manifest())
    for name in CLIPS:
        for index in range(3):
            (directory/f'snow_{name}_{index:02}.mod').write_bytes(mesh())
    (directory/'p2-snow.txt').write_text(manifest())
    (directory/'snow.json').write_text(json.dumps({'schema': 1, 'species': 'YellowKochappy', 'motions': bank}))
    return bank


def test_frame_sampling_preserves_endpoints_and_density_budget():
    for duration in (1, 2, 55, 75, 80, 90, 10000):
        frames = sample_frames(duration)
        assert frames[0] == 0 and frames[-1] == duration-1
        assert len(frames) == min(duration, 24)
        assert all(a < b for a, b in zip(frames, frames[1:]))
    with pytest.raises(ValueError):
        sample_frames(90, 390)


@pytest.mark.parametrize('text', [manifest().replace('0 4 8', '0 4 4', 1),
    manifest().replace('0 4 8', '0 9 8', 1), manifest().replace('0 4 8', '1 4 8', 1),
    manifest().replace('0 4 8', '0 4 7', 1), manifest()+'junk', manifest()[:-3],
    manifest().replace('wait1 3', 'wait1 25'), manifest().replace('wait1', 'attack', 1),
    manifest().replace('P2_SNOW_2', 'P2_SNOW_3')])
def test_manifest_rejects_invalid_bank(text):
    with pytest.raises(ValueError):
        parse_bank(text)


def test_legacy_bank_keeps_implicit_frames():
    assert parse_bank(manifest(1))['dead'] == {'poses': 3, 'source_frames': 9, 'frames': None}


def test_install_validates_all_resources_before_any_copy(tmp_path):
    imported = tmp_path/'import'
    bank = bank_files(imported)
    run = tmp_path/'run'
    room = run/'assets/dataDir/courses/pikmin2room'
    room.mkdir(parents=True)
    late = imported/'snow_flick_02.mod'
    late.write_bytes(mesh(b'different pixels'))
    with pytest.raises(ValueError, match='resources differ'):
        install(imported, run, [5002])
    assert list(room.iterdir()) == [] and not (run/'p2-snow.txt').exists()
    late.write_bytes(mesh())
    paths, count = validate_files(imported, bank)
    assert len(paths) == 15 and count == 15*len(mesh())
    install(imported, run, [5002])
    assert len(list(room.iterdir())) == 15
    assert (run/'p2-snow-actors.txt').read_text() == 'P2_SNOW_ACTORS_1 1\n5002\n'


def test_oversized_file_is_rejected_before_reading(tmp_path):
    bank = bank_files(tmp_path/'import')
    (tmp_path/'import/snow_wait1_00.mod').write_bytes(bytes(CLIP_BYTES+1))
    with pytest.raises(ValueError, match='byte budget'):
        validate_files(tmp_path/'import', bank)


@pytest.mark.parametrize('data', [b'', mesh()[:-1], mesh()[:-8], mesh()+b'x',
                                   struct.pack('>II', 32, 0xffffffff)])
def test_malformed_mod_resource_chunks(data):
    with pytest.raises(ValueError):
        resource_chunks(data)


def test_native_playback_and_validation(tmp_path):
    compiler = shutil.which('g++') or ('C:/msys64/mingw64/bin/g++.exe' if Path('C:/msys64/mingw64/bin/g++.exe').exists() else None)
    if not compiler:
        pytest.skip('C++ compiler unavailable')
    source = tmp_path/'animation.cpp'
    source.write_text(r'''
#include "pc_p2_animation.h"
#include <cassert>
#include <sstream>
#include <limits>
int main() {
    std::vector<p2animation::Clip> clips;
    std::stringstream modern;
    modern << "P2_SNOW_2\n";
    for(auto name:{"wait1","move1","attack","dead","flick"})modern<<name<<" 3 9 0 4 8\n";
    assert(p2animation::parse(modern,clips));
    auto clip=clips[0];
    assert(clip.index(.24f)==0 && clip.index(.26f)==1 && clip.index(.74f)==1 && clip.index(.76f)==2);
    assert(clip.index(-1)==0 && clip.index(2)==2 && clip.index(std::numeric_limits<float>::quiet_NaN())==0);
    assert(clip.index(0,true)==2); // corpse remains at final source pose
    clip.frames.clear();
    assert(clip.index(.49f)==0 && clip.index(.51f)==1); // legacy floor selection
    std::stringstream duplicate("P2_SNOW_2 wait1 3 9 0 4 4");
    assert(!p2animation::parse(duplicate,clips));
    std::vector<unsigned char> bad={0,0,0,32,255,255,255,255},out;
    assert(!p2animation::resources(bad,out));
    assert(!p2animation::resources({},out));
}
''')
    executable = tmp_path/'animation.exe'
    native = Path(__file__).resolve().parents[1]/'native/pc_port'
    env = dict(os.environ)
    env['PATH'] = str(Path(compiler).parent)+os.pathsep+env.get('PATH', '')
    subprocess.run([compiler, '-std=c++17', '-I', str(native), str(source), '-o', str(executable)], check=True, env=env, capture_output=True)
    subprocess.run([str(executable)], check=True, env=env, capture_output=True)
