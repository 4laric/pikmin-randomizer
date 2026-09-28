from pathlib import Path
import os
import shutil
import struct
import subprocess
import pytest
from experimental.pikmin2_material_color import decode, bank_text
ROOT=Path(__file__).resolve().parents[1]

def fixture():
    block=bytearray(160);block[:4]=b'TRK1';struct.pack_into('>I',block,4,len(block))
    struct.pack_into('>BBh10H',block,8,2,255,10,1,0,1,1,1,1,0,0,0,0)
    struct.pack_into('>14I',block,32,88,0,124,0,128,0,116,118,120,122,0,0,0,0)
    for i in range(4):struct.pack_into('>3H',block,88+6*i,1,0,0)
    struct.pack_into('>4h',block,116,100,120,140,255)
    struct.pack_into('>HHHH',block,128,1,65535,0,8);block[136:141]=b'body\0'
    header=bytearray(32);header[:8]=b'J3D1brk1';struct.pack_into('>II',header,8,192,1)
    return bytes(header+block)

def test_import():
    r=decode(fixture());assert r['tracks'][0]['curves'][2]==[[0,140,0,0]]
    assert decode(fixture())==r and 'P2_MATERIAL_COLOR_1' in bank_text(r)

def test_konst_group():
    b=bytearray(fixture())
    struct.pack_into('>BBh10H',b,40,2,255,10,0,1,0,0,0,0,1,1,1,1)
    struct.pack_into('>14I',b,64,0,88,0,124,0,128,0,0,0,0,116,118,120,122)
    b[32+112]=3
    t=decode(b)['tracks'][0];assert t['kind']==1 and t['register']==3 and t['curves'][0][0][1]==100

@pytest.mark.parametrize('offset,value,fmt',[(40,3,'B'),(42,0,'h'),(44,129,'H'),(64,1,'I'),(32+88,4097,'H'),(32+92,2,'H'),(32+112,3,'B'),(32+128,2,'H')])
def test_refusals(offset,value,fmt):
    b=bytearray(fixture());struct.pack_into('>'+fmt,b,offset,value)
    with pytest.raises(ValueError):decode(b)

def test_native(tmp_path):
    cc=shutil.which('g++')
    if not cc:pytest.skip('g++ required')
    exe=tmp_path/'probe.exe'
    compiled=subprocess.run([cc,'-std=c++17','-O2','-Wall','-Wextra','-Werror','-I'+str(ROOT/'engine/tools/color_stubs'),'-I'+str(ROOT/'engine/pc_port'),str(ROOT/'engine/tools/test_p2_material_color.cpp'),str(ROOT/'engine/pc_port/pc_p2_color_binding.cpp'),'-o',str(exe)],capture_output=True,text=True)
    assert compiled.returncode==0,compiled.stderr
    data=Path(os.environ['P2_BRK_SOURCE']).read_bytes() if os.environ.get('P2_BRK_SOURCE') else fixture()
    report=decode(data);bank=tmp_path/'bank.txt';bank.write_text(bank_text(report))
    output=subprocess.check_output([str(exe),str(bank)],text=True);assert 'PASS material colors' in output
    for line in output.splitlines()[:-1]:
        f,*got=map(int,line.split());want=[]
        for c in report['tracks'][0]['curves']:
            if len(c)==1:v=c[0][1];v=v%256 if report['tracks'][0]['kind'] else v
            else:
                if f<=c[0][0]:v=c[0][1]
                elif f>=c[-1][0]:v=c[-1][1]
                else:
                    a,b=next((a,b) for a,b in zip(c,c[1:]) if a[0]<=f<b[0]);span=b[0]-a[0];t=(f-a[0])/span
                    v=(2*t**3-3*t**2+1)*a[1]+(t**3-2*t**2+t)*span*a[3]+(-2*t**3+3*t**2)*b[1]+(t**3-t**2)*span*b[2]
                v=max(0 if report['tracks'][0]['kind'] else -1024,min(255 if report['tracks'][0]['kind'] else 1023,v))
            want.append(int(v))
        assert got==want
