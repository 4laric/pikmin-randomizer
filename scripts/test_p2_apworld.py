"""Isolated packaged AP plumbing test. Synthetic placement is NOT gameplay evidence."""
import argparse
import importlib
import json
import os
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
    original_cwd = Path.cwd()
    sandbox = tempfile.TemporaryDirectory()
    try:
        os.chdir(sandbox.name)
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
        for doc in ({'schema': 'invalid'},
                    dict(synthetic, profiles=[dict(p, accepted_gates=[]) for p in synthetic['profiles']])):
            try:
                make({'p2_enemy_randomizer': True, 'p2_placement': doc})
            except ValueError:
                pass
            else:
                raise AssertionError('Missing, invalid or denied placement was accepted')
        from pikmin_randomizer.core.seed import PLAYABLE_P2_SPECIES
        playable = make({'p2_enemy_randomizer': True}).worlds[1].manifest()  # default pool: playable
        assert {b['source_id'] for b in playable['p2_layout']['bindings']} == set(PLAYABLE_P2_SPECIES)
        options = {'p2_enemy_randomizer': True, 'p2_enemy_pool': 'all'}
        # Real packaged admitted placement, not the synthetic denial fixture.
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
        # The `full` pool (playable six + PROVEN proxy tier) must generate inside the package:
        # proxy declarations, roster snapshot and the stage-A placement sibling are all bundled.
        from pikmin_randomizer.core.p2_proxy import tier_ids
        full_mw = make({'p2_enemy_randomizer': True, 'p2_enemy_pool': 'full'})
        full = full_mw.worlds[1].manifest()
        validate(full)
        bound = {b['source_id'] for b in full['p2_layout']['bindings']}
        assert full.get('p2_proxy_tier') == 'proven' and 'p2-proxy-tier-v1' in full['capabilities']
        # With no proven row yet `full` is exactly the playable six on the legacy policy; proxy rows switch it to sampled-v1.
        assert (full['p2_layout']['density'] == 'sampled-v1') == bool(tier_ids('proven')) and len(full['p2_layout']['bindings']) <= 64
        assert bound | set(full['p2_layout'].get('unplaced', [])) == set(PLAYABLE_P2_SPECIES) | set(tier_ids('proven'))
        assert set(PLAYABLE_P2_SPECIES) <= bound
        assert fingerprint(make({'p2_enemy_randomizer': True, 'p2_enemy_pool': 'full'}).worlds[1].manifest()) == fingerprint(full)
        distribute_items_restrictive(full_mw)
        assert full_mw.can_beat_game() and not full_mw.get_unfilled_locations()
        # And the declared tier (every row) resolves too, so the bundled sibling/rows are really reachable.
        from pikmin_randomizer.core.seed import generate as _generate
        declared = _generate('packaged-declared', p2_enemies=True, p2_species='full', p2_proxy_tier='declared')
        assert len({b['source_id'] for b in declared['p2_layout']['bindings']}) == len(declared['p2_layout']['bindings']) >= 35
        assert 'randomizer' not in sys.modules and 'experimental' not in sys.modules
        print('PASS: isolated zip imports, normal AP, invalid/denied placement, deterministic P2 fill, full proxy pool, output roundtrip')
        print('Real admitted placement fill passed; runtime acceptance is separate.')
    finally:
        os.chdir(original_cwd)
        sandbox.cleanup()



if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--ap', type=Path, required=True)
    p.add_argument('--archive', type=Path, required=True)
    args = p.parse_args()
    main(args.ap, args.archive)
