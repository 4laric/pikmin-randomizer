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
