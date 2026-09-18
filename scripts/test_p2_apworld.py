"""Isolated packaged AP plumbing test. Synthetic placement is NOT gameplay evidence."""
import argparse
import importlib
import json
from pathlib import Path
import sys
import tempfile


def main(ap, archive):
    # Deliberately exclude the repository: a package must carry its dependencies.
    root = Path(__file__).resolve().parents[1]
    sys.path[:] = [p for p in sys.path if p and Path(p).resolve() not in (root, root / 'scripts')]
    sys.path.insert(0, str(ap.resolve()))
    import ModuleUpdate
    ModuleUpdate.update_ran = True
    import worlds
    sys.path.insert(0, str(archive.resolve()))
    world = importlib.import_module('pikmin_randomizer')
    from test.general import setup_multiworld
    from Fill import distribute_items_restrictive
    from pikmin_randomizer.core.seed import validate, fingerprint
    from pikmin_randomizer.experimental.pikmin2_enemy_roster import load_and_validate, admitted_ids
    roster = load_and_validate()
    ids = set(admitted_ids(roster))
    assert ids, 'Test requires the pinned real admitted cohort'
    names = [e.enum_name for e in roster if e.source_id in ids]
    synthetic = {'schema': 'p2-placement-v1',
        'slots': [{'uid': i + 1, 'label': 'TEST ONLY', 'stage': 1,
                   'terrain': 'ground', 'radius': 300,
                   'evidence': {'xyz': True, 'terrain': True, 'route': True}}
                  for i in range(len(ids))],
        'profiles': [{'identity': name, 'terrains': ['ground'],
                      'accepted_gates': ['TEST ONLY']} for name in names]}
    def make(options):
        return setup_multiworld(world.PikminRandomizerWorld, seed=1818, options=options)
    ordinary = make({})
    assert 'p2_layout' not in ordinary.worlds[1].manifest()
    for doc in ({}, {'schema': 'invalid'},
                dict(synthetic, profiles=[dict(p, accepted_gates=[]) for p in synthetic['profiles']])):
        try:
            make({'p2_enemy_randomizer': True, 'p2_placement': doc})
        except ValueError:
            pass
        else:
            raise AssertionError('Missing, invalid or denied placement was accepted')
    options = {'p2_enemy_randomizer': True, 'p2_placement': synthetic}
    mw = make(options)
    m = mw.worlds[1].manifest()
    validate(m)
    assert {b['source_id'] for b in m['p2_layout']['bindings']} == ids
    assert fingerprint(make(options).worlds[1].manifest()) == fingerprint(m)
    distribute_items_restrictive(mw)
    assert mw.can_beat_game() and not mw.get_unfilled_locations()
    with tempfile.TemporaryDirectory() as out:
        mw.worlds[1].generate_output(out)
        saved = json.loads(next(Path(out).glob('*.pikmin.json')).read_text())
        validate(saved)
        assert fingerprint(saved) == fingerprint(m)
    assert 'randomizer' not in sys.modules and 'experimental' not in sys.modules
    print('PASS: isolated zip imports, normal AP, missing/invalid/denied placement, deterministic P2 fill, output roundtrip')
    print('Synthetic placement only; this does not establish campaign or runtime acceptance.')


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--ap', type=Path, required=True)
    p.add_argument('--archive', type=Path, required=True)
    args = p.parse_args()
    main(args.ap, args.archive)
