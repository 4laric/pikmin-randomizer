from pathlib import Path
import pytest

from experimental.pikmin2_white import extract


def test_white_extractor_rejects_unbound_or_duplicate_ivory(tmp_path):
    with pytest.raises(ValueError,match='nonempty'): extract(tmp_path/'missing.iso',tmp_path/'out',[])
    with pytest.raises(ValueError,match='unique'): extract(tmp_path/'missing.iso',tmp_path/'out',[7,7])
    with pytest.raises(ValueError,match='Invalid'): extract(tmp_path/'missing.iso',tmp_path/'out',[-1])


def test_local_white_source_data_and_pose_bank():
    directory=Path('output/pikmin2-white395/import-04')
    if not directory.exists(): pytest.skip('Requires local user-owned disc extraction')
    import json
    report=json.loads((directory/'white.json').read_text())
    assert report['source_revision']=='632af93787b9c95b63f0c13be32b161375ce3a96'
    assert set(report['source_stats'])=={'movement','attack','scale','carry_power','bud_bonus','flower_bonus','carry_max_factor','carry_min_factor','base_run_speed'}
    assert report['ivory_generators']
    for name in ('wait','walk','attack1'):
        assert list(directory.glob(f'white_{name}_*.mod'))


def test_local_white_preview_has_one_bound_ivory(tmp_path):
    from scripts.preview_pikmin2_emergence import prepare
    from scripts.preview_pikmin2_room import records
    import struct
    assets=Path('C:/Users/alari/bbft/dist/cohesion/pikmin/assets')
    imported=Path('output/pikmin2-emergence110/import-03');white=Path('output/pikmin2-white395/import-04')
    pod=Path('output/pikmin2-purple113/atlas-01');treasure=Path('output/pikmin2-room105/treasure.mod')
    if not all(path.exists() for path in (assets,imported,white,pod,treasure)):pytest.skip('Requires local user-owned assets')
    run=prepare(assets,imported,treasure,tmp_path,pod=pod,white=white)
    ivory=[row for row in records(run/'assets/dataDir/stages/chal0/default.gen') if row[16:48].rstrip(b'\0')==b'preview ivory']
    assert len(ivory)==1 and struct.unpack_from('>I',ivory[0],8)[0]==25
    assert (run/'p2-white.txt').read_bytes()==(white/'p2-white.txt').read_bytes()
