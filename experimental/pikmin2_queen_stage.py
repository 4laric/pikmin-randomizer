"""Stage the native Empress Bulblax (Queen, 30) OWN inputs (#256).

The native campaign binding (native ``pc_port/pc_p2_queen_teki.cpp`` with the
engine-free FSM in ``pc_p2_queen_own.h``) opens exactly these files, relative
to the run dir (the native cwd):

* ``p2-queen-bank.txt``: ``P2_QUEEN_BANK_1`` -- disc parameter rows (general
  and proper blocks of ``queen/enemyparm.txt`` and ``baby/enemyparm.txt``,
  validated against ``pikmin2_bulblax_assets.DISC_PARMS`` by the extractor),
  then one ``clip`` row per Queen/Baby clip carrying the disc frame count, the
  ``enemyanimmgr.txt`` key events and the staged pose frames.
* ``p2-queen-specular.txt``: the Queen BTK specular sidecar
  (``pikmin2_queen_specular``), optional.
* ``assets/dataDir/courses/pikmin2room/bulblax_{Queen,Baby}_<clip>_<ii>.mod``:
  the sampled pose meshes (Queen poses carry the source UV1 diffuse bake).

The source tree is the ``extract_queen`` output (``<content>/Queen``):
``identity.json``, ``bulblax.json`` (import report with events), and the
prepared bank directory ``bank/`` (``p2-bulblax-bank.txt``,
``p2-queen-specular.txt``, ``Queen/``, ``Baby/``).
"""
import hashlib
import json
from pathlib import Path

ROOM = 'assets/dataDir/courses/pikmin2room'
BANK_TXT = 'p2-queen-bank.txt'
SPECULAR_TXT = 'p2-queen-specular.txt'
MESH_BYTES = 2 * 1024 * 1024
TOTAL_BYTES = 40 * 1024 * 1024

QUEEN_CLIPS = ('dead', 'sleep', 'wait1', 'damage', 'flick', 'rolling_l', 'rolling_r', 'born', 'carry')
BABY_CLIPS = ('dead', 'deadpress', 'move', 'attack', 'attackfail', 'born')

# Native parm row name -> (species, block, key) in DISC_PARMS.
PARM_ROWS = (
    ('health', 'Queen', 'general', 'fp00'),
    ('move_speed', 'Queen', 'general', 'fp06'),
    ('territory_radius', 'Queen', 'general', 'fp09'),
    ('home_radius', 'Queen', 'general', 'fp10'),
    ('shake_knockback', 'Queen', 'general', 'fp17'),
    ('shake_damage', 'Queen', 'general', 'fp18'),
    ('attack_radius', 'Queen', 'general', 'fp22'),
    ('attack_damage', 'Queen', 'general', 'fp24'),
    ('shake_off_blow_a', 'Queen', 'general', 'ip01'),
    ('shake_off_sticking_1', 'Queen', 'general', 'ip02'),
    ('shake_off_blow_b', 'Queen', 'general', 'ip03'),
    ('shake_off_sticking_2', 'Queen', 'general', 'ip04'),
    ('shake_off_blow_c', 'Queen', 'general', 'ip05'),
    ('shake_off_sticking_3', 'Queen', 'general', 'ip06'),
    ('shake_off_blow_d', 'Queen', 'general', 'ip07'),
    ('rolling_time', 'Queen', 'proper', 'fp01'),
    ('birth_interval', 'Queen', 'proper', 'fp02'),
    ('hob_health', 'Queen', 'proper', 'fp11'),
    ('max_births', 'Queen', 'proper', 'ip01'),
    ('min_births', 'Queen', 'proper', 'ip02'),
    ('baby_health', 'Baby', 'general', 'fp00'),
    ('baby_move_speed', 'Baby', 'general', 'fp06'),
    ('baby_sight_radius', 'Baby', 'general', 'fp12'),
    ('baby_view_angle', 'Baby', 'general', 'fp13'),
    ('baby_max_attack_range', 'Baby', 'general', 'fp20'),
    ('baby_max_attack_angle', 'Baby', 'general', 'fp21'),
    ('baby_attack_damage', 'Baby', 'general', 'fp24'),
)
# General-block rows the #235 audit did not pin in DISC_PARMS but the import
# report carries verbatim (parameter_blocks of the disc enemyparm.txt).
REPORT_ROWS = (
    ('search_distance', 'Queen', 'fp14'),
    ('attack_hit_angle', 'Queen', 'fp23'),
)


class QueenStageError(ValueError):
    pass


def pose_name(species, clip, number):
    return f'bulblax_{species}_{clip}_{number:02}.mod'


def _fmt(value):
    if isinstance(value, int) or float(value).is_integer():
        return str(int(value))
    return repr(float(value))


def _general_block(report, species):
    blocks = report['species'][species]['parameter_blocks']
    if len(blocks) != 3:
        raise QueenStageError(f'{species} parameter blocks malformed')
    return blocks[1], blocks[2]


def parm_rows(report):
    from experimental.pikmin2_bulblax_assets import DISC_PARMS
    rows = []
    for name, species, block, key in PARM_ROWS:
        general, proper = _general_block(report, species)
        source = general if block == 'general' else proper
        if key not in source:
            raise QueenStageError(f'{species} {block} {key} missing from the import report')
        expected = DISC_PARMS[species][block].get(key)
        if expected is not None and abs(float(source[key]) - float(expected)) > 1e-6:
            raise QueenStageError(f'{species} {block} {key} is not the audited disc value')
        rows.append((name, source[key]))
    for name, species, key in REPORT_ROWS:
        general, _ = _general_block(report, species)
        if key in general:
            rows.append((name, general[key]))
    return rows


def _pose_span(bank_dir, species, clip, index):
    report = bank_dir / species / pose_name(species, clip, index).replace('.mod', '.json')
    bounds = json.loads(report.read_text(encoding='utf-8')).get('bounds')
    if not bounds or len(bounds) != 6:
        raise QueenStageError(f'pose report without bounds: {report.name}')
    return max(bounds[3] - bounds[0], bounds[4] - bounds[1], bounds[5] - bounds[2])


def carcass_pose_rows(bank_dir, parsed):
    """Carcass draw fallback (#256).

    The staged Queen ``carry`` poses (and the tail of ``dead``) bake to a
    collapsed mesh (every vertex within ~0.2 units): the converter's baked
    carry pose is not a usable carcass. When that holds, the native carcass
    draw uses the last ``dead`` pose that still spans the body, and says so
    (P2_QUEEN_CARCASS draw=dead_pose_<n>). Nothing is emitted when the carry
    poses are usable.
    """
    carry = [_pose_span(bank_dir, 'Queen', 'carry', i) for i in range(len(parsed['Queen']['carry']['frames']))]
    if carry and max(carry) >= 50.0:
        return []
    dead = [_pose_span(bank_dir, 'Queen', 'dead', i) for i in range(len(parsed['Queen']['dead']['frames']))]
    usable = [i for i, span in enumerate(dead) if span >= 50.0]
    if not usable:
        raise QueenStageError('no usable Queen carcass pose (carry and dead collapse)')
    return [('carcass_carry_degenerate', 1), ('carcass_dead_pose', usable[-1])]


def bank_text(parms, clips):
    lines = ['P2_QUEEN_BANK_1', '# Empress Bulblax OWN bank (#256); disc parms + enemyanimmgr events']
    for name, value in parms:
        lines.append(f'parm {name} {_fmt(value)}')
    for who, name, frames, events, poses in clips:
        ev = ' '.join(f'{f} {t}' for f, t in events)
        ps = ' '.join(str(p) for p in poses)
        lines.append(f'clip {who} {name} {frames} {len(events)}' + (f' {ev}' if ev else '')
                     + f' {len(poses)}' + (f' {ps}' if ps else ''))
    lines.append('end')
    return ('\n'.join(lines) + '\n').encode('ascii')


def plan(source):
    """Plan the staged files from an ``extract_queen`` tree."""
    from experimental.pikmin2_bulblax_bank import parse_bank
    source = Path(source)
    report_path = source / 'bulblax.json'
    bank_dir = source / 'bank'
    if not report_path.is_file() or not (bank_dir / 'p2-bulblax-bank.txt').is_file():
        raise QueenStageError(f'not a Queen extractor tree: {source}')
    report = json.loads(report_path.read_text(encoding='utf-8'))
    parsed = parse_bank((bank_dir / 'p2-bulblax-bank.txt').read_text(encoding='ascii'))
    parms = parm_rows(report)
    clips, room = [], []
    total = 0
    for species, who, names in (('Queen', 'queen', QUEEN_CLIPS), ('Baby', 'baby', BABY_CLIPS)):
        events = {c['name']: c['events'] for c in report['species'][species]['clips']}
        frames_by = {c['name']: int(c['source_frames']) for c in report['species'][species]['clips']}
        reference = None
        for name in names:
            if name not in parsed[species] or name not in events:
                raise QueenStageError(f'{species} clip {name} missing')
            info = parsed[species][name]
            if int(info['source_frames']) != frames_by[name]:
                raise QueenStageError(f'{species} clip {name} frame count drift')
            poses = list(info['frames'])
            for index in range(len(poses)):
                file = bank_dir / species / pose_name(species, name, index)
                data = file.read_bytes()
                if not data or len(data) > MESH_BYTES:
                    raise QueenStageError(f'pose mesh out of budget: {file.name}')
                total += len(data)
                if total > TOTAL_BYTES:
                    raise QueenStageError('Queen pose budget exceeded')
                room.append((file.name, data))
            clips.append((who, name, frames_by[name], [tuple(e) for e in events[name]], poses))
    parms += carcass_pose_rows(bank_dir, parsed)
    specular = bank_dir / SPECULAR_TXT
    return dict(bank=bank_text(parms, clips), room=room,
                specular=specular.read_bytes() if specular.is_file() else None,
                parms=len(parms), poses=len(room), pose_bytes=total)


def _write_new_or_same(path, data):
    if path.exists() or path.is_symlink():
        if not path.is_file() or path.read_bytes() != data:
            raise QueenStageError(f'refusing to replace existing {path.name}')
        return False
    path.write_bytes(data)
    return True


def stage(run, planned):
    """Write a plan into ``run``; idempotent for byte-identical repeats."""
    run = Path(run)
    room = run / ROOM
    private = room.is_dir() and room.resolve().is_relative_to(run.resolve())
    receipt = dict(bank=hashlib.sha256(planned['bank']).hexdigest(), parms=planned['parms'],
                   poses=0, pose_bytes=0, specular=planned['specular'] is not None)
    if private:
        # The retail/preview asset overlay may already carry older #235 bank
        # poses under the same bulblax_* names. The room is this run's private
        # copy, so replace them; unlink first so a hard-linked overlay file is
        # never written through to the shared asset source.
        replaced = 0
        for name, data in planned['room']:
            path = room / name
            if path.is_symlink() or path.exists():
                if path.is_file() and not path.is_symlink() and path.read_bytes() == data:
                    continue
                path.unlink()
                replaced += 1
            path.write_bytes(data)
        receipt['replaced'] = replaced
        receipt['poses'] = len(planned['room'])
        receipt['pose_bytes'] = planned['pose_bytes']
    else:
        receipt['poses_skipped'] = 'no private model room'
    if planned['specular'] is not None:
        _write_new_or_same(run / SPECULAR_TXT, planned['specular'])
    _write_new_or_same(run / BANK_TXT, planned['bank'])
    return receipt


def stage_from(source, run):
    return stage(run, plan(source))
