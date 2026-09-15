"""Kogane/Wealthy/Fart (IDs 9/10/11) source pose assets; no native behavior substitution.

Beetle lane (#212). All three registered IDs share one model and one animation
set (enemy/data/Kogane/model.szs + anim.szs); only the change-texture and the
parameter block differ per species. Extraction follows the sheargrub pattern:
sampled rigid poses, source metadata preserved verbatim, hashed manifest.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
from experimental.pikmin2_assets import disc_files, archive_files
from experimental.pikmin2_convert import blocks, decode, write_model, u16, u32
from experimental.pikmin2_purple import bca_pose
from experimental.pikmin2_animation import sample_frames
from experimental.pikmin2_skinning import draw_matrices


def sha(data):
    return hashlib.sha256(data).hexdigest()


# Source-backed species registry (native/pikmin2-research):
# enemyInfo.h:68-70, generalEnemyMgr.cpp:244-251, enemyInfo.cpp:25-27.
SPECIES = {
    'kogane': {
        'enemy_id': 9,
        'common_name': 'Iridescent Flint Beetle',
        'obj_class': 'Game::Koganemushi::Obj',
        'mgr_class': 'Game::Koganemushi::Mgr',
        'change_texture': 'enemy/data/Kogane/kogane_s3tc.bti',
        'karada_kcolor': [60, 60, 60, 255],
    },
    'wealthy': {
        'enemy_id': 10,
        'common_name': 'Iridescent Glint Beetle',
        'obj_class': 'Game::Wealthy::Obj',
        'mgr_class': 'Game::Wealthy::Mgr',
        'change_texture': 'enemy/data/Wealthy/oogane_s3tc.bti',
        'karada_kcolor': [100, 100, 100, 255],
    },
    'fart': {
        'enemy_id': 11,
        'common_name': 'Doodlebug',
        'obj_class': 'Game::Fart::Obj',
        'mgr_class': 'Game::Fart::Mgr',
        'change_texture': 'enemy/data/Fart/babakogane_s3tc.bti',
        'karada_kcolor': [15, 15, 15, 255],
    },
}

# Drop tables per flip (press) count, from Koganemushi.cpp:53-104,
# Wealthy.cpp:52-109 and Fart.cpp:116-167. createTreasureItem()
# (Kogane.cpp:386-414) runs first: a carried treasure (mPelletDropCode)
# replaces the whole table on the first flip when available.
# Entries: (surface_drop, cave_drop); each drop is (kind, arg, amount).
DROP_TABLES = {
    'kogane': [
        {'surface': ('pellet', 'PELLET_NUMBER_ONE', 1), 'cave': ('doping', 'HONEY_Y', 1)},
        {'surface': ('doping', 'HONEY_Y', 2), 'cave': ('doping', 'HONEY_Y', 2)},
        {'surface': ('doping', 'HONEY_R', 1, 'DEMO_First_Spicy_Spray_Made', ('doping', 'HONEY_Y', 3)),
         'cave': ('doping', 'HONEY_R', 1, 'DEMO_First_Spicy_Spray_Made', ('doping', 'HONEY_Y', 3))},
    ],
    'wealthy': [
        {'surface': ('pellet', 'PELLET_NUMBER_FIVE', 3), 'cave': ('doping', 'HONEY_Y', 3)},
        {'surface': ('doping', 'HONEY_R', 1, 'DEMO_First_Spicy_Spray_Made', ('doping', 'HONEY_Y', 3)),
         'cave': ('doping', 'HONEY_R', 1, 'DEMO_First_Spicy_Spray_Made', ('doping', 'HONEY_Y', 3))},
        {'surface': ('doping', 'HONEY_R', 1, 'DEMO_First_Spicy_Spray_Made', ('doping', 'HONEY_Y', 3)),
         'cave': ('doping', 'HONEY_R', 1, 'DEMO_First_Spicy_Spray_Made', ('doping', 'HONEY_Y', 3))},
    ],
    'fart': [
        {'surface': ('doping', 'HONEY_Y', 3), 'cave': ('doping', 'HONEY_Y', 3)},
        {'surface': ('doping', 'HONEY_B', 1, 'DEMO_First_Bitter_Spray_Made', ('doping', 'HONEY_Y', 3)),
         'cave': ('doping', 'HONEY_B', 1, 'DEMO_First_Bitter_Spray_Made', ('doping', 'HONEY_Y', 3))},
        {'surface': ('doping', 'HONEY_B', 1, 'DEMO_First_Bitter_Spray_Made', ('doping', 'HONEY_Y', 3)),
         'cave': ('doping', 'HONEY_B', 1, 'DEMO_First_Bitter_Spray_Made', ('doping', 'HONEY_Y', 3))},
    ],
}

# Third flip forces escape: createItem sets mAppearTimer = 12800 on hit 2,
# so StatePress::exec (KoganeState.cpp:260-265) transits to Disappear.
MAX_FLIPS = 3

# Doodlebug-only gas attack (Fart.cpp:76-110, 213-230):
# StateMove::init calls createFartEffect (KoganeState.cpp:136); the gas cloud
# persists for FART_GAS_DURATION seconds and stimulates Navi/Pikmin within
# mAttackRadius (fp22) of mFartPosition with InteractGas of mAttackDamage (fp24).
FART_GAS_DURATION = 2.5
FART_STATE_GATE = 2  # buzz sound only in state >= KOGANE_Move (Fart.cpp:28-30)


def drop_for(species, hit, in_cave, demo_flag=False):
    """Resolve the source drop table entry for one flip."""
    if species not in DROP_TABLES:
        raise ValueError('Unknown beetle species')
    if type(hit) != int or not 0 <= hit < MAX_FLIPS:
        raise ValueError('Hit count out of drop table range')
    entry = DROP_TABLES[species][hit]['cave' if in_cave else 'surface']
    if len(entry) == 5:
        return entry[:3] if demo_flag else entry[4]
    return entry


def animation_rows(text):
    clean = re.sub(r'#[^\r\n]*', '', text)
    count = int(clean.split()[0])
    rows = []
    for block in re.findall(r'\{([^{}]*)\}', clean):
        fields = block.split()
        if len(fields) < 3 or not re.fullmatch(r'[a-z0-9_]+\.bca', fields[1]) or fields[-1] != '-1':
            raise ValueError('Invalid animation registration')
        events = fields[2:-1]
        if len(events) % 2:
            raise ValueError('Invalid animation event pairs')
        rows.append({'file': fields[1], 'events': [[int(events[i]), int(events[i + 1])] for i in range(0, len(events), 2)]})
    if len(rows) != count or len({r['file'] for r in rows}) != count:
        raise ValueError('Animation registry count/identity mismatch')
    return rows


def parse_parms(text):
    """Parse one enemyparm.txt into ordered sections of {tag: value}."""
    out = []
    current = None
    for line in text.splitlines():
        head = re.match(r'\s*#\s*([A-Za-z][A-Za-z0-9:()]*)\s*$', line)
        if head:
            current = {'section': head.group(1), 'parms': {}}
            out.append(current)
            continue
        m = re.match(r'\s*\{(\w{4})\}\s+4\s+([-0-9.]+)', line)
        if m and current is not None:
            tag = m.group(1)
            if tag in current['parms']:
                raise ValueError('Duplicate parameter key in section')
            current['parms'][tag] = float(m.group(2))
    if not out or any(not s['parms'] for s in out):
        raise ValueError('Malformed parameter file')
    return out


def joints(model):
    data = blocks(model)['JNT1']
    count = u16(data, 8)
    offset = u32(data, 20)
    if offset + 4 > len(data) or u16(data, offset) != count:
        raise ValueError('Invalid joint name table')
    names = []
    for i in range(count):
        entry = offset + 4 + 4 * i
        if entry + 4 > len(data):
            raise ValueError('Truncated joint table')
        start = offset + u16(data, entry + 2)
        if start >= len(data):
            raise ValueError('Invalid joint name offset')
        end = data.find(b'\0', start)
        if end < 0:
            raise ValueError('Unterminated joint name')
        names.append(data[start:end].decode('ascii'))
    return names


def extract(iso, output, pose_limit=3):
    if type(pose_limit) != int or not 2 <= pose_limit <= 8:
        raise ValueError('Pose limit must be 2..8')
    output.mkdir(parents=True, exist_ok=False)
    index = disc_files(iso)
    hashes = {}
    result = {'schema': 1, 'family': 'Kogane', 'species': {}, 'native_ready': False}
    with iso.open('rb') as disc:
        def read(path):
            at, size = index[path]
            disc.seek(at)
            raw = disc.read(size)
            if len(raw) != size:
                raise ValueError('Truncated disc resource')
            hashes[path] = sha(raw)
            return raw
        motions = archive_files(read('enemy/data/Kogane/anim.szs'))
        params = archive_files(read('enemy/parm/enemyParms.szs'))
        model = archive_files(read('enemy/data/Kogane/model.szs'))['enemy.bmd']
        names = joints(model)
        shared = output / 'shared'
        shared.mkdir()
        modelpath = shared / 'enemy.bmd'
        modelpath.write_bytes(model)
        rows = animation_rows(params['kogane/enemyanimmgr.txt'].decode('shift_jis'))
        (shared / 'enemyanimmgr.txt').write_bytes(params['kogane/enemyanimmgr.txt'])
        (shared / 'enemycoll.txt').write_bytes(params['kogane/enemycoll.txt'])
        (shared / 'enemystoneinfo.txt').write_bytes(params['kogane/enemystoneinfo.txt'])
        clips = []
        for row in rows:
            raw = motions[row['file']]
            (shared / row['file']).write_bytes(raw)
            clip = dict(row, sha256=sha(raw), status='unsupported', poses=[])
            try:
                duration, _ = bca_pose(raw, 0, len(names), allow_scale=True)
                clip['source_frames'] = duration
                for i, frame in enumerate(sample_frames(duration, pose_limit)):
                    _, pose = bca_pose(raw, frame, len(names), allow_scale=True)
                    name = Path(row['file']).stem + f'_{i:02}.mod'
                    # Kogane's karada shape carries TEX1MTXIDX (retail sets
                    # TexMtxLoadType 0x2000, KoganeMgr.cpp:40-44), so the plain
                    # convert() path rejects it; bake through the explicit
                    # draw-matrix path established by the Groink lane.
                    matrices = draw_matrices(blocks(model), pose)
                    decoded = decode(model, True, bake_rigid=True, draw_matrices=matrices)
                    conversion = write_model(decoded, shared / name, 'enemy.bmd')
                    conversion['weighted_pose_baked'] = True
                    conversion['source'] = 'enemy.bmd'
                    conversion['output'] = name
                    (shared / Path(name).with_suffix('.json')).write_text(json.dumps(conversion, indent=2) + '\n')
                    clip['poses'].append(dict(file=name, frame=frame, sha256=sha((shared / name).read_bytes()), conversion=conversion))
                clip['status'] = 'converted'
            except ValueError as error:
                clip['unsupported_reason'] = str(error)
            clips.append(clip)
        tex = blocks(model)['TEX1']
        for species, info in SPECIES.items():
            root = output / species
            root.mkdir()
            parm_raw = params[species + '/enemyparm.txt']
            (root / 'enemyparm.txt').write_bytes(parm_raw)
            tex_raw = read(info['change_texture'])
            (root / Path(info['change_texture']).name).write_bytes(tex_raw)
            result['species'][species] = dict(
                info,
                parm_sha256=sha(parm_raw),
                change_texture_sha256=sha(tex_raw),
                sections=parse_parms(parm_raw.decode('shift_jis')),
                drop_table=DROP_TABLES[species],
            )
        result['shared'] = dict(model_sha256=sha(model), joints=names,
                                embedded_texture_count=u16(tex, 8), clips=clips,
                                collision_sha256=sha(params['kogane/enemycoll.txt']),
                                stoneinfo_sha256=sha(params['kogane/enemystoneinfo.txt']),
                                animmgr_sha256=sha(params['kogane/enemyanimmgr.txt']))
    result['source_sha256'] = hashes
    result['limitations'] = [
        'Sampled rigid poses with approximate materials; no skeletal playback or event execution.',
        'One shared model/animation bank; per-species identity is change-texture plus karada TEV k-color.',
        'Damage/damage-flip drops, treasure carry, burrow appear/disappear and Fart gas are source-documented only; native behavior is unimplemented in this lane.',
        'Collision and parameter text preserved verbatim, not replaced with mesh-bound guesses.',
    ]
    (output / 'beetles.json').write_text(json.dumps(result, indent=2) + '\n')
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--iso', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--pose-limit', type=int, default=3)
    a = p.parse_args()
    r = extract(a.iso, a.output, a.pose_limit)
    print(json.dumps({'joints': len(r['shared']['joints']),
                      'clips': [c['file'] + ':' + c['status'] for c in r['shared']['clips']],
                      'species': sorted(r['species'])}))
