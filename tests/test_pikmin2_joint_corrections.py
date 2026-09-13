"""Corrected joint/skin/attachment contract and optional retail Groink oracle."""
import json,os,shutil,subprocess
from pathlib import Path
import pytest
from experimental.pikmin2_convert import blocks,decode
from experimental.pikmin2_skinning import draw_matrices
from experimental.pikmin2_purple import bca_pose
from experimental.pikmin2_rigid import compose,local_matrix,joint_matrices
from experimental.pikmin2_sheargrub_assets import joints

ROOT=Path(__file__).resolve().parents[1]

def test_corrected_native_and_source(tmp_path):
    compiler=shutil.which('g++')
    if not compiler:pytest.skip('g++ required')
    exe=tmp_path/'probe.exe'
    subprocess.run([compiler,'-std=c++17','-O2','-Wall','-Wextra','-Werror','-I'+str(ROOT/'engine/pc_port'),str(ROOT/'engine/tools/test_p2_joint_corrections.cpp'),'-o',str(exe)],check=True,capture_output=True)
    assert 'PASS joint corrections' in subprocess.check_output([str(exe)],text=True)
    path=os.environ.get('P2_WEIGHTED_BANK')
    if not path:return
    bank=Path(path);dump=tmp_path/'dump.txt';metadata=json.loads((bank/'weighted.json').read_text())
    import hashlib
    for file in ('source.bmd','attachments.txt','skin.txt'):
        assert hashlib.sha256((bank/file).read_bytes()).hexdigest()==metadata[file+'_sha256']
    model=(bank/'source.bmd').read_bytes();source=blocks(model)
    subprocess.run([str(exe),str(bank/'attachments.txt'),str(bank/'skin.txt'),str(dump)],check=True)
    lines=iter(dump.read_text().splitlines());count=0;max_position=max_normal=0
    for row in lines:
        clip,frame,p,n=row.split();p,n=int(p),int(n)
        actual=[[tuple(map(float,next(lines).split())) for _ in range(size)] for size in (p,n)]
        raw=(bank/(clip+'.bca')).read_bytes();assert hashlib.sha256(raw).hexdigest()==metadata['clips'][clip]['sha256']
        _,pose=bca_pose(raw,int(frame),metadata['joints'],allow_scale=True)
        uncorrected=None
        if clip=='attack1' and int(frame)==20:
            _,uncorrected,_,_=decode(model,True,bake_rigid=True,draw_matrices=draw_matrices(source,pose))
        muzzle=joints(model).index('kuti');pose[muzzle]=compose(pose[muzzle],local_matrix((0,8192,0),(0,0,0)))
        _,arrays,_,_=decode(model,True,bake_rigid=True,draw_matrices=draw_matrices(source,pose))
        socket=next(lines).split();assert socket[0]=='socket'
        expected_socket=[x for row in joint_matrices(source,pose)[muzzle] for x in row]
        assert len(socket)==13 and max(abs(float(x)-y) for x,y in zip(socket[1:],expected_socket))<.0002
        if uncorrected is not None:
            delta=max(abs(a-b) for x,y in zip(uncorrected[9],arrays[9]) for a,b in zip(x,y))
            assert delta>20;print(f'MUZZLE_GEOMETRY_CHANGE {delta}')
        errors=[]
        for got,want in zip(actual,(arrays[9],arrays[10])):
            assert len(got)==len(want)
            errors.append(max(abs(a-b) for x,y in zip(got,want) for a,b in zip(x,y)))
        max_position=max(max_position,errors[0]);max_normal=max(max_normal,errors[1]);count+=1
    assert count==sum(v['frames'] for v in metadata['clips'].values())
    assert max_position<.0002 and max_normal<.0002
    print(f'CORRECTED_GROINK_SOURCE frames={count} position_error={max_position} normal_error={max_normal}')
