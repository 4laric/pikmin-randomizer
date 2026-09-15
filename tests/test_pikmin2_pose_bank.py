from pathlib import Path
import shutil,subprocess,tempfile,unittest
from tests.test_pikmin2_pose_blend import model,ASSETS
from experimental.pikmin2_pose_compatibility import decode
ROOT=Path(__file__).resolve().parents[1]
class BankTests(unittest.TestCase):
 def test_native_validation(self):
  compiler=shutil.which('g++')
  if not compiler:self.skipTest('g++ required')
  with tempfile.TemporaryDirectory() as d:
   d=Path(d);exe=d/'bank.exe'
   subprocess.run([compiler,'-std=c++17','-Wall','-Wextra','-Werror','-I'+str(ROOT/'engine/pc_port'),str(ROOT/'engine/tools/test_p2_pose_bank.cpp'),'-o',str(exe)],check=True,capture_output=True)
   def check(a,b,ok):
    (d/'a.mod').write_bytes(a);(d/'b.mod').write_bytes(b)
    result=subprocess.run([str(exe),str(d/'a.mod'),str(d/'b.mod')],capture_output=True)
    self.assertEqual(result.returncode,0 if ok else 1,result.stderr)
   a=model();check(a,model(5,normal=(0,2,0)),True)
   for bad in [model(texture=2),model(normal=(0,0,0)),model(normal=(float('nan'),0,0)),a[:-1],a+b'x',a+a]:
    with self.subTest(kind='malformed',length=len(bad)):check(a,bad,False)
   chunks,_,_=decode(a)
   for tag,offset,value in [(80,8,2),(64,33,1),(96,70,1),(16,8,255),(17,12,1)]:
    b=bytearray(a);b[a.index(chunks[tag])+offset]=value
    with self.subTest(tag=tag):check(a,b,False)
   for species,clip in [('Queen','wait1'),('Baby','move'),('KingChappy','wait2')]:
    files=sorted((ASSETS/'bulblax-bank2-run1'/species).glob(f'bulblax_{species}_{clip}_*.mod'))
    if not files:self.skipTest('local source bank missing')
    for b in files:
     with self.subTest(bank=b.name):check(files[0].read_bytes(),b.read_bytes(),True)
