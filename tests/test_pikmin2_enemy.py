import struct
import math
import pytest
from experimental.pikmin2_enemy import replace_texture_zero
from experimental.pikmin2_convert import blocks, u32
from experimental.pikmin2_rigid import apply
from experimental.pikmin2_purple import bca_pose
from test_pikmin2_purple import animation

def test_scaled_pose_is_explicit_and_normals_use_inverse_transpose():
    data=animation();struct.pack_into('>f',data,160,2)
    with pytest.raises(ValueError,match='Scaled'):bca_pose(data,0,1)
    _,pose=bca_pose(data,0,1,allow_scale=True)
    assert pose[0][0][0]==2 and pose[0][0][3]==1
    normal=apply([[2,0,0,7],[0,1,0,8],[0,0,1,9]],(1,1,0),normal=True)
    assert normal==pytest.approx((1/math.sqrt(5),2/math.sqrt(5),0))
    with pytest.raises(ValueError,match='Singular'):apply([[0,0,0,0],[0,1,0,0],[0,0,1,0]],(1,0,0),normal=True)

def model():
    result=bytearray(128);result[:8]=b'J3D2bmd3';struct.pack_into('>II',result,8,128,1)
    result[32:36]=b'TEX1';struct.pack_into('>IH',result,36,96,1);struct.pack_into('>I',result,44,32)
    result[64]=0;struct.pack_into('>HH',result,66,8,8);struct.pack_into('>I',result,92,32)
    return result

def test_texture_replacement_preserves_model_and_rebases_pixels():
    bti=bytearray(64);bti[0]=0;struct.pack_into('>HH',bti,2,8,8);struct.pack_into('>I',bti,28,32);bti[32:]=bytes(range(32))
    updated=replace_texture_zero(model(),bti);tex=blocks(updated)['TEX1'];header=u32(tex,12)
    at=header+u32(tex,header+28)
    assert tex[at:at+32]==bytes(range(32))
    assert u32(updated,8)==len(updated)
    with pytest.raises(ValueError,match='Truncated'):replace_texture_zero(model(),bti[:-1])
    bti[8]=1
    with pytest.raises(ValueError,match='non-paletted'):replace_texture_zero(model(),bti)

def test_install_rejects_duplicate_ids_before_writing(tmp_path):
    from experimental.pikmin2_enemy import install
    with pytest.raises(ValueError,match='unique'):
        install(tmp_path/'missing',tmp_path/'run',[1,1])
    assert not (tmp_path/'run').exists()

def _snow_mod():
    return struct.pack('>II',32,0)+struct.pack('>II',34,0)+struct.pack('>II',48,0)+struct.pack('>II',65535,0)

def _snow_import(tmp_path):
    import json
    from experimental.pikmin2_animation import CLIPS
    imported=tmp_path/'import';imported.mkdir()
    rows=['P2_SNOW_2'];motions={}
    for name in CLIPS:
        rows+= [name,'1','1','0']
        (imported/f'snow_{name}_00.mod').write_bytes(_snow_mod())
        motions[name]={'poses':1,'source_frames':1,'frames':[0]}
    (imported/'p2-snow.txt').write_text('\n'.join(rows)+'\n')
    (imported/'snow.json').write_text(json.dumps({'schema':1,'species':'YellowKochappy','motions':motions}))
    return imported

def test_snow_content_manifest_serves_seed_identity_at_asset_paths(tmp_path):
    from experimental.pikmin2_enemy import content_manifest,SNOW_SOURCE_ID
    from experimental.pikmin2_staging import verify_manifest
    manifest=content_manifest(_snow_import(tmp_path))
    assert manifest['identities']==[SNOW_SOURCE_ID]
    destinations={entry['destination'] for entry in manifest['entries']}
    assert 'p2-snow.txt' in destinations
    assert all(d=='p2-snow.txt' or d.startswith('dataDir/courses/pikmin2room/') for d in destinations)
    report=verify_manifest(manifest)
    assert report['ok'] and report['summary']['missing_source']==0
    with pytest.raises((ValueError,FileNotFoundError)):
        content_manifest(tmp_path/'empty')

def test_snow_generated_seed_binds_and_stages_its_identity(tmp_path,monkeypatch):
    from experimental.pikmin2_enemy import content_manifest,SNOW_SOURCE_ID
    from experimental.pikmin2_staging import stage_session_content,StagingError
    from experimental import pikmin2_seed_bridge as bridge
    from randomizer.seed import generate
    from randomizer.p2_placement_catalog import build_document
    from randomizer import p2_placement as placement
    monkeypatch.setattr(bridge,'admitted_ids',lambda roster:[SNOW_SOURCE_ID])
    full=build_document()
    profile=next(p for p in full['profiles'] if p['identity']=='YellowKochappy')
    slot=next(s for s in full['slots'] if not placement.compatibility(s,profile,{}))
    slot['evidence']={'xyz':True,'terrain':True,'route':True}
    profile['accepted_gates']=['xyz']
    manifest=generate('snow-gen',collection_checks=True,p2_enemies=True,
                      p2_placement={'schema':full['schema'],'slots':[slot],'profiles':[profile]})
    bindings=manifest['p2_layout']['bindings']
    assert [b['source_id'] for b in bindings]==[SNOW_SOURCE_ID]
    assert 'p2-enemy-bridge-v1' in manifest['capabilities']
    snow=content_manifest(_snow_import(tmp_path))
    receipt=stage_session_content(snow,tmp_path/'run',cache_dir=tmp_path/'cache',
                                  required_identities=[b['source_id'] for b in bindings])
    assert receipt['identities']==[str(SNOW_SOURCE_ID)]
    with pytest.raises(StagingError,match='does not cover'):
        stage_session_content(snow,tmp_path/'other',required_identities=[44])

def test_snow_content_overlay_connects_native_lookup(tmp_path):
    import json
    from experimental.pikmin2_enemy import content_manifest,write_content_manifest
    from experimental.pikmin2_staging import stage_session_content
    imported=_snow_import(tmp_path)
    retail=tmp_path/'retail';(retail/'dataDir'/'stages').mkdir(parents=True)
    (retail/'dataDir'/'stages'/'base.gen').write_bytes(b'retail')
    manifest_path=tmp_path/'snow-content.json'
    write_content_manifest(imported,manifest_path)
    assert json.loads(manifest_path.read_text())['identities']==[45]
    receipt=stage_session_content(manifest_path,tmp_path/'run'/'assets',
                                  required_identities=[45],retail_assets=retail)
    assets=tmp_path/'run'/'assets'
    assert receipt['mode']=='asset-overlay' and receipt['identities']==['45']
    assert (assets/'p2-snow.txt').read_text().startswith('P2_SNOW_2')
    assert (assets/'dataDir'/'courses'/'pikmin2room'/'snow_wait1_00.mod').is_file()
    assert (assets/'dataDir'/'stages'/'base.gen').read_bytes()==b'retail'



