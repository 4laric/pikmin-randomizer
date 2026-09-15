"""Native skeletal kernel and optional retail-source deformation comparison."""
import os,shutil,subprocess
from pathlib import Path
import pytest
from experimental.pikmin2_rigid import bake
ROOT=Path(__file__).resolve().parents[1]

def test_bindings_preserve_separate_joint_vertex_keys():
    arrays={9:[(1,2,3)],10:[(0,1,0)]};shapes=[[[{0:j,9:0,10:0} for j in (0,1,0)]]];bindings={}
    identity=[[1,0,0,0],[0,1,0,0],[0,0,1,0]]
    bake(arrays,shapes,[identity,identity],bindings=bindings)
    assert bindings[9]==[(0,(1,2,3)),(1,(1,2,3))]
    assert len(arrays[9])==2

def test_native_kernel_and_source(tmp_path):
    compiler=shutil.which('g++')
    if not compiler:pytest.skip('g++ required')
    exe=tmp_path/'skin.exe'
    subprocess.run([compiler,'-std=c++17','-Wall','-Wextra','-Werror','-I'+str(ROOT/'engine/pc_port'),str(ROOT/'engine/tools/test_p2_skin.cpp'),'-o',str(exe)],check=True,capture_output=True)
    assert 'PASS skeletal deformation' in subprocess.check_output([str(exe)],text=True)
    directory=os.environ.get('P2_SKIN_BANK')
    if not directory:return
    from experimental.pikmin2_assets import disc_files,archive_files
    from experimental.pikmin2_purple import bca_pose
    from experimental.pikmin2_convert import decode
    directory=Path(directory);snow=Path(os.environ['P2_ATTACHMENT_SNOW']);iso=Path(os.environ['P2_ATTACHMENT_ISO'])
    files=disc_files(iso);offset,size=files['enemy/data/Kochappy/anim.szs']
    with iso.open('rb') as stream:
        stream.seek(offset);animations=archive_files(stream.read(size))
    model=(snow/'snow.bmd').read_bytes();dump=tmp_path/'dump.txt'
    subprocess.run([str(exe),str(directory/'attachments.txt'),str(directory/'skin.txt'),str(dump)],check=True)
    lines=iter(dump.read_text().splitlines());maximum=0;count=0
    for line in lines:
        clip,frame,p,n=line.split();p,n=int(p),int(n)
        actual=[[tuple(map(float,next(lines).split())) for _ in range(size)] for size in (p,n)]
        _,pose=bca_pose(animations[clip+'.bca'],int(frame),13,allow_scale=True)
        _,arrays,_,_=decode(model,approximate_materials=True,bake_rigid=True,pose=pose)
        for got,want in zip(actual,(arrays[9],arrays[10])):
            assert len(got)==len(want)
            maximum=max(maximum,max(abs(a-b) for x,y in zip(got,want) for a,b in zip(x,y)))
        count+=1
    assert count>120 and maximum<.0001
    print(f'SOURCE_SKIN frames={count} maximum_component_error={maximum}')
