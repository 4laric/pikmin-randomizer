import pytest
import json
import struct
from pathlib import Path
from experimental.pikmin2_rigid import local_matrix, compose, apply, bake
from experimental.pikmin2_pod import pellet_catalog


def test_bind_pose_parent_rotation_and_normal():
    parent=local_matrix((0,0,16384),(10,20,30))
    child=local_matrix((0,0,0),(2,0,0))
    world=compose(parent,child)
    assert apply(world,(1,0,0))==pytest.approx((10,23,30))
    assert apply(world,(1,0,0),normal=True)==pytest.approx((0,1,0))


def test_shared_vertex_baked_separately_for_each_joint():
    arrays={9:[(1,0,0)],10:[(0,1,0)]}
    vertices=[{0:j,9:0,10:0} for j in (0,1,0)]
    bake(arrays,[[vertices]],[local_matrix((0,0,0),(0,0,0)),local_matrix((0,0,0),(5,0,0))])
    assert arrays[9]==[(1,0,0),(6,0,0)]
    assert arrays[10]==[(0,1,0),(0,1,0)]
    assert [v[9] for v in vertices]==[0,1,0]
    assert all(0 not in v for v in vertices)


def test_source_pellet_catalog_preserves_weight_value_and_offset():
    text='1 { name dia_a_red money 180 min 15 max 25 offset 0 1 2 end }'
    item=pellet_catalog(text)['dia_a_red']
    assert (item['money'],item['min'],item['max'])==('180','15','25')
    assert item['offset']==['0','1','2']


@pytest.mark.parametrize('text',['2 { name a end }','2 { name a end } { name a end }','1 { name a money 1 }'])
def test_bad_catalog_rejected(text):
    with pytest.raises(ValueError):pellet_catalog(text)


def test_local_assembled_pod_preview_manifest(tmp_path):
    from scripts.preview_pikmin2_emergence import prepare, UNIT
    assets=Path('C:/Users/alari/bbft/dist/cohesion/pikmin/assets')
    imported=Path('output/pikmin2-emergence110/import-03')
    assembled=Path('output/pikmin2-emergence110/floor1-03')
    pod=Path('output/pikmin2-pod111/import-01')
    treasure=Path('output/pikmin2-room105/treasure.mod')
    if not all(p.exists() for p in (assets,imported,assembled,pod,treasure)):
        pytest.skip('Requires local user-owned assets')
    run=prepare(assets,imported,treasure,tmp_path,assembled,1,pod)
    manifest=json.loads((run/'preview.json').read_text())
    assert manifest['unit']==UNIT and manifest['pod'] and manifest['assembled_geometry']
    assert not manifest['save_resume'] and not manifest['ap']
    assert (run/'p2-pod.txt').read_bytes()==(pod/'p2-pod.txt').read_bytes()


def test_local_pod_bind_pose_is_explicit_and_rejects_skinning(tmp_path):
    from experimental.pikmin2_convert import decode, convert
    source=Path('output/pikmin2-pod111/import-01/pod/pot.bmd')
    if not source.exists():pytest.skip('Requires locally extracted user-owned model')
    data=source.read_bytes()
    with pytest.raises(ValueError,match='one rigid joint'):decode(data,True)
    report=convert(source,tmp_path/'pod.mod',True,bake_rigid=True)
    assert (report['vertices'],report['triangles'],report['shapes'])==(367,594,2)
    assert report['rigid_bind_pose_baked']
    modified=bytearray(data);at=32
    while modified[at:at+4]!=b'EVP1':at+=struct.unpack_from('>I',modified,at+4)[0]
    struct.pack_into('>H',modified,at+8,1)
    with pytest.raises(ValueError,match='Skinned envelopes'):decode(modified,True,True)
