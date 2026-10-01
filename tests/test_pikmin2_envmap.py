from pathlib import Path
import shutil,struct,subprocess,tempfile,unittest
from experimental.pikmin2_kurage_envmap import descriptor,patch
from experimental.pikmin2_convert import u32

ROOT=Path(__file__).resolve().parents[1]
ASSETS=Path('C:/Users/alari/pikmin-randomizer/output')


def chunks(data):
    result={};at=0
    while at<len(data):
        tag,size=struct.unpack_from('>II',data,at);result[tag]=data[at:at+8+size];at+=8+size
    return result


class EnvmapTests(unittest.TestCase):
    def test_native_source_matrix(self):
        compiler=shutil.which('g++')
        if not compiler:self.skipTest('g++ required')
        with tempfile.TemporaryDirectory() as directory:
            exe=Path(directory)/'probe.exe'
            p=subprocess.run([compiler,'-std=c++17','-Wall','-Wextra','-Werror','-I',str(ROOT/'engine/pc_port'),
                str(ROOT/'engine/tools/test_p2_envmap.cpp'),'-o',str(exe)],capture_output=True,text=True)
            self.assertEqual(p.returncode,0,p.stderr)
            p=subprocess.run([str(exe)],capture_output=True,text=True)
            self.assertEqual(p.returncode,0,p.stdout+p.stderr);print(p.stdout.strip())

    def test_real_two_stage_export(self):
        if not (ASSETS/'p2-jellyfloat-assets-01').exists():self.skipTest('Local retail sources required')
        for species in ('Kurage','OniKurage'):
            with self.subTest(species=species):
                model=(ASSETS/'p2-jellyfloat-assets-01'/species/'enemy.bmd').read_bytes()
                before=(ASSETS/'p2-jellyfloat-converted-01'/species/'wait.mod').read_bytes()
                rows=descriptor(model);after=patch(before,rows);a=chunks(before);b=chunks(after)
                self.assertEqual(set(a),set(b))
                for tag in a:
                    if tag!=48:self.assertEqual(a[tag],b[tag])
                material=b[48];pos=32
                for row in rows:
                    self.assertEqual(u32(material,pos+88),2)
                    for index,stage in enumerate(row['stages']):
                        start=pos+92+index*32
                        self.assertEqual(list(material[start+1:start+4]),stage['order'])
                        self.assertEqual(list(material[start+8:start+17]),stage['color'])
                        self.assertEqual(list(material[start+20:start+29]),stage['alpha'])
                    pos+=156
                oldpos=32+248
                for row in rows:
                    self.assertEqual(material[pos:pos+76],a[48][oldpos:oldpos+76])
                    self.assertEqual(material[pos+80:pos+88],bytes([0,1,4,10,1,1,1,0]))
                    self.assertEqual(u32(material,pos+88),2)
                    env=pos+92+64
                    self.assertEqual(material[env+8:env+10],bytes([0xE6,2]))
                    self.assertEqual(struct.unpack_from('>2f',material,env+24),tuple(row['scale']))
                    pos+=220;oldpos+=152
                with self.assertRaises(ValueError):patch(after,rows)

    def test_unknown_source_refused(self):
        with self.assertRaises(ValueError):descriptor(b'not an audited model')
