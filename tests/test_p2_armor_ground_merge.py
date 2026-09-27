"""Armor (15) stages its ground sidecars by merging with other ground species.

frogs4 (#871): Armor used to stage through the legacy all-or-nothing
``ground.install``, which refused (``Refusing existing/conflicting ground
installation``, ``pikmin2_batch2_core.py:198-202``) whenever
``p2-ground-*.txt`` already existed -- so a seed binding Armor plus Sokkuri,
ElecBug or Imomushi could never stage. Armor now rides the shared
``_adapt_ground_inverts`` merge adapter like Imomushi (65) / Hana (84).

Hermetic: the Armor/Imomushi sources are synthetic ``ground_inverts.json``
manifests (same bytes in both dirs, exactly like the real extractor output,
which carries all six species converted in every species dir); the
Sokkuri/ElecBug sources reuse the synthetic trees from their own content
tests. No retail disc image is required.
"""
import hashlib
import itertools
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from experimental import pikmin2_ground_species_content as ground  # noqa: E402
from experimental.pikmin2_family_install import install_family  # noqa: E402
from experimental.pikmin2_staging import StagingError  # noqa: E402
from tests.test_p2_elecbug_content import make_source as make_elecbug_source  # noqa: E402
from tests.test_p2_sokkuri_content import make_source as make_sokkuri_source  # noqa: E402

ROOM = Path('assets/dataDir/courses/pikmin2room')

G_ARMOR = 346015
G_SOKKURI = 219079
G_ELECBUB = 219028
G_IMOMUSHI = 346065

# Anchors from experimental.pikmin2_batch2_families.GROUND.
ARMOR_CLIPS = {
    'dead': dict(frames=[0, 10], duration=20, events=[]),
    'move': dict(frames=[0, 7, 13], duration=14, events=[[4, 0], [13, 1]]),
    'attack1': dict(frames=[0, 5, 9], duration=10, events=[[0, 0], [9, 1]]),
}
IMOMUSHI_CLIPS = {
    'dead': dict(frames=[0, 10], duration=20, events=[]),
    'move1': dict(frames=[0, 6, 12], duration=12, events=[[6, 0], [12, 1]]),
}
SPECIES_IDS = {'Armor': 15, 'ElecBug': 28, 'Imomushi': 65,
               'TamagoMushi': 68, 'Sokkuri': 79, 'Hana': 84}


def _pose_bytes(species, clip, frame):
    return b'FROGS4-POSE %s %s %d\n' % (species.encode(), clip.encode(), frame)


def make_ground_source(root):
    """Write a synthetic full-family ground_inverts import dir.

    Both the Armor and Imomushi source dirs get byte-identical manifests
    (mirroring the real extractor, whose per-species dirs each carry all six
    species converted), so the shared profile payload is identical no matter
    which dir stages first.
    """
    root = Path(root)
    clips_by_species = {'Armor': ARMOR_CLIPS, 'Imomushi': IMOMUSHI_CLIPS}
    species_doc = {}
    for species, enemy_id in SPECIES_IDS.items():
        clips = []
        for clip, spec in clips_by_species.get(species, {}).items():
            poses = []
            for index, frame in enumerate(spec['frames']):
                name = f'ginv_{species}_{clip}_{index:02}.mod'
                data = _pose_bytes(species, clip, frame)
                subdir = root / species
                subdir.mkdir(parents=True, exist_ok=True)
                (subdir / name).write_bytes(data)
                poses.append({'frame': frame, 'file': name,
                              'bytes': len(data),
                              'sha256': hashlib.sha256(data).hexdigest()})
            clips.append({'name': clip,
                          'events': [list(event) for event in spec['events']],
                          'source_frames': spec['duration'],
                          'poses': poses, 'status': 'converted'})
        species_doc[species] = {
            'enemy_id': enemy_id,
            'role': f'{species}-role',
            'parameter_blocks': [{}, {'speed': 1.0, 'turn': 2.0}],
            'clips': clips,
        }
    document = {
        'schema': 1,
        'policy': 'P2_GROUND_INVERTS_1',
        'disc_id': 'GPVE01',
        'disc_revision': 0,
        'species': species_doc,
    }
    root.mkdir(parents=True, exist_ok=True)
    (root / 'ground_inverts.json').write_text(json.dumps(document, indent=2) + '\n',
                                              encoding='utf-8')
    return root


def make_content(root):
    """Write the four species source dirs under ``root``."""
    root = Path(root)
    make_ground_source(root / 'Armor')
    make_ground_source(root / 'Imomushi')
    make_sokkuri_source(root / 'Sokkuri')
    make_elecbug_source(root / 'ElecBug')
    return root


def make_run(root):
    run = Path(root)
    (run / ROOM).mkdir(parents=True, exist_ok=True)
    return run


STAGES = (
    ('armor', 'Armor', G_ARMOR),
    ('sokkuri', 'Sokkuri', G_SOKKURI),
    ('elecbug', 'ElecBug', G_ELECBUB),
    ('ground_inverts', 'Imomushi', G_IMOMUSHI),
)

SOURCE_DIR = {'armor': 'Armor', 'sokkuri': 'Sokkuri',
              'elecbug': 'ElecBug', 'ground_inverts': 'Imomushi'}


def _stage(content, run, order):
    for family, species, generator in order:
        install_family(family, content / SOURCE_DIR[family], run,
                       [(generator, species)])


def _sidecars(run):
    actors = (run / ground.ACTORS_TXT).read_bytes()
    bank = (run / ground.BANK_TXT).read_bytes()
    return actors, bank


def _parse_actors(data):
    tokens = data.decode('ascii').split()
    assert tokens[0] == 'P2_GROUND_ACTORS_1'
    count = int(tokens[1])
    assert len(tokens) == 2 + 2 * count
    return {int(tokens[i]): tokens[i + 1] for i in range(2, len(tokens), 2)}


def _parse_bank_species(data):
    tokens = data.decode('ascii').split()
    assert tokens[0] == 'P2_GROUND_BANK_1'
    return [tokens[i + 1] for i, word in enumerate(tokens)
            if word == 'species']


def test_armor_merges_with_ground_species_in_every_order(tmp_path):
    """Armor + Sokkuri + ElecBug + Imomushi stage in all 24 family orders.

    Every order must succeed (no legacy ``Refusing existing/conflicting``
    failure) and converge on the same merged content: the same actor map
    (actor rows are an order-preserving union, so file order follows staging
    order while the parsed map is identical) and byte-identical
    ``p2-ground-bank.txt`` with bank blocks in canonical family order.
    """
    content = make_content(tmp_path / 'content')
    results = []
    for order in itertools.permutations(STAGES):
        run = make_run(tmp_path / f'run-{len(results)}')
        _stage(content, run, order)
        actors, bank = _sidecars(run)
        assert _parse_actors(actors) == {G_ARMOR: 'Armor', G_SOKKURI: 'Sokkuri',
                                         G_ELECBUB: 'ElecBug', G_IMOMUSHI: 'Imomushi'}
        assert _parse_bank_species(bank) == ['Armor', 'ElecBug', 'Imomushi', 'Sokkuri']
        room_files = sorted(p.name for p in (run / ROOM).glob('*.mod'))
        assert any(name.startswith('ginv_Armor_') for name in room_files)
        assert any(name.startswith('ginv_Imomushi_') for name in room_files)
        assert any(name.startswith('ginv_Sokkuri_') for name in room_files)
        assert any(name.startswith('ginv_ElecBug_') for name in room_files)
        results.append((actors, bank))
    first_actors, first_bank = results[0]
    for actors, bank in results[1:]:
        assert _parse_actors(actors) == _parse_actors(first_actors)
        assert bank == first_bank


def test_armor_ground_staging_is_idempotent(tmp_path):
    """Restaging the merged families over the same run is a no-op success."""
    content = make_content(tmp_path / 'content')
    run = make_run(tmp_path / 'run')
    _stage(content, run, STAGES)
    before = (_sidecars(run),
              sorted((p.name, p.read_bytes()) for p in (run / ROOM).glob('*.mod')))
    _stage(content, run, reversed(STAGES))
    after = (_sidecars(run),
             sorted((p.name, p.read_bytes()) for p in (run / ROOM).glob('*.mod')))
    assert before == after


def test_armor_ground_rebinding_refuses(tmp_path):
    """A generator bound to Armor cannot be rebound to another species."""
    content = make_content(tmp_path / 'content')
    run = make_run(tmp_path / 'run')
    install_family('armor', content / 'Armor', run, [(G_ARMOR, 'Armor')])
    with pytest.raises(StagingError, match='already bound'):
        install_family('sokkuri', content / 'Sokkuri', run, [(G_ARMOR, 'Sokkuri')])
    assert _parse_actors((run / ground.ACTORS_TXT).read_bytes()) == {G_ARMOR: 'Armor'}
