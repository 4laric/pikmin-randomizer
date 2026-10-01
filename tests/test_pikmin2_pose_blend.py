import math
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
import unittest
from experimental.pikmin2_convert import Writer
from experimental.pikmin2_pose_compatibility import audit,decode,probe_text

ROOT=Path(__file__).resolve().parents[1]
ASSETS=Path('C:/Users/alari/pikmin-randomizer/output')

def model(x=0,normal=(1,0,0),texture=1):
    w=Writer()
    for tag,vec in ((16,(x,0,0)),(17,normal)):
        w.begin(tag,1);w.pad();w.put('3f',*vec);w.end()
    for tag in (32,34,48,80):w.begin(tag,texture if tag==32 else 1);w.end()
    w.begin(64,1);w.pad();w.put('h',0);w.end()
    w.begin(96,1);w.pad();w.put('iI6ff9fI',-1,0,x,0,0,x,0,0,0,1,1,1,0,0,0,0,0,0,0);w.end()
    w.begin(65535);w.end()
    return bytes(w.data)

class PoseTests(unittest.TestCase):
    def test_compatible_bounds_and_arrays(self):
        report,a,b=audit(model(),model(5,normal=(0,2,0)))
        self.assertTrue(report['compatible']);self.assertEqual(a[16],[(0,0,0)])
        self.assertEqual(b[16],[(5,0,0)]);self.assertTrue(probe_text(a,b).startswith('1 1\n'))

    def test_resources_topology_and_invalid_data_refused(self):
        a=model()
        for bad in (model(texture=2),model(normal=(0,0,0)),model(normal=(math.nan,0,0)),a[:-1],a+b'x',a+a):
            with self.subTest(size=len(bad)),self.assertRaises(ValueError):audit(a,bad)
        chunks,_,_=decode(a)
        for tag,offset,value in ((80,8,2),(64,33,1),(96,70,1),(16,8,255),(17,12,1)):
            b=bytearray(a);at=a.index(chunks[tag]);b[at+offset]=value
            with self.subTest(tag=tag),self.assertRaises(ValueError):audit(a,b)

    def test_native_kernel_and_real_banks(self):
        compiler=shutil.which('g++')
        if not compiler:self.skipTest('g++ required')
        with tempfile.TemporaryDirectory() as temp:
            temp=Path(temp);exe=temp/'probe.exe'
            subprocess.run([compiler,'-std=c++17','-Wall','-Wextra','-Werror','-I'+str(ROOT/'engine/pc_port'),str(ROOT/'engine/tools/test_p2_pose_blend.cpp'),'-o',str(exe)],check=True,capture_output=True)
            self.assertIn('PASS pose interpolation',subprocess.check_output([str(exe)],text=True))
            pairs=[(ASSETS/'bulblax-bank2-run1'/species/f'bulblax_{species}_{clip}_00.mod',ASSETS/'bulblax-bank2-run1'/species/f'bulblax_{species}_{clip}_01.mod') for species,clip in [('Queen','carry'),('Baby','move'),('KingChappy','move1')]]
            pairs += [(ASSETS/'p2-jellyfloat-converted-01'/species/'wait.mod',ASSETS/'p2-jellyfloat-converted-01'/species/'move1.mod') for species in ('Kurage','OniKurage')]
            for left,right in pairs:
                with self.subTest(pair=str(left)):
                    if not left.exists() or not right.exists():self.skipTest('Local retail pose pair unavailable')
                    report,a,b=audit(left.read_bytes(),right.read_bytes())
                    probe=temp/'pair.txt';probe.write_text(probe_text(a,b))
                    result=subprocess.check_output([str(exe),str(probe)],text=True)
                    self.assertIn('REAL_PAIR',result);print(left.parent.name,'max_delta=',report['max_position_delta'],result.strip())
