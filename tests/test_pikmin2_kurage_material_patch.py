from pathlib import Path
import struct
import tempfile
import unittest
from experimental.pikmin2_convert import Writer
from experimental.pikmin2_kurage_material_patch import descriptor,patch,prepare,COLOR,ALPHA

ROOT=Path('C:/Users/alari/pikmin-randomizer/output')


class MaterialTests(unittest.TestCase):
    def fixture(self):
        w=Writer();w.begin(48,2,2);w.pad()
        for _ in range(2):
            for _ in range(3):w.put('4hIfII',255,255,255,255,0,0.,0,0)
            w.data+=bytes([255])*16;w.put('I',1)
            w.data+=bytes([0,0,0,4,0,0,0,0,15,8,10,15,0,0,0,1,0,0,0,0,7,4,5,7,0,0,0,1,0,0,0,0])
        w.data+=b'opaque pixel-state sentinel';w.end();w.begin(65535);w.end()
        rows=[dict(registers=[[195,220,90,100],[240,210,80,0],[0,0,0,0]],color=COLOR,alpha=ALPHA)]*2
        return bytes(w.data),rows

    def test_byte_scope_and_source_opacity(self):
        original,rows=self.fixture();changed=patch(original,rows)
        allowed=set()
        for pos in (32,156):
            for start,size in [(pos,8),(pos+24,8),(pos+48,8),(pos+100,9),(pos+112,9)]:
                allowed.update(range(start,start+size))
            self.assertEqual(struct.unpack_from('>4h',changed,pos),tuple(rows[0]['registers'][0]))
            self.assertEqual(list(changed[pos+112:pos+121]),ALPHA)
        self.assertEqual(len(original),len(changed))
        self.assertTrue(all(i in allowed for i,(a,b) in enumerate(zip(original,changed)) if a!=b))
        # Interpret the emitted operands, not the converter's default expression.
        operands=list(changed[32+112:32+116])
        a0=struct.unpack_from('>4h',changed,32)[3]/255
        for texture_alpha,expected in ((0,100/255),(.25,100/255+.25),(1,1)):
            inputs={7:0,5:1,4:texture_alpha,1:a0}
            a,b,c,d=(inputs[x] for x in operands)
            self.assertAlmostEqual(min(1,max(0,d+a*(1-c)+b*c)),expected)
        self.assertIn(b'opaque pixel-state sentinel',changed)

    def test_refuse_repatch_truncation_and_unknown_source(self):
        original,rows=self.fixture()
        for bad in (b'',original[:-1],patch(original,rows)):
            with self.assertRaises((ValueError,struct.error)):patch(bad,rows)
        with self.assertRaises(ValueError):descriptor(b'unknown')

    def test_real_source_and_no_overwrite(self):
        model=ROOT/'p2-jellyfloat-assets-01/Kurage/enemy.bmd'
        mod=ROOT/'kurage-runtime-sessions-11/assets/dataDir/courses/pikmin2room/kurage_wait.mod'
        if not model.exists() or not mod.exists():self.skipTest('Local retail assets absent')
        with tempfile.TemporaryDirectory() as directory:
            dest=Path(directory)/'patch';r=prepare(model,mod,dest)
            self.assertEqual(r['changed_bytes'],36)
            self.assertEqual(r['materials'][0]['registers'][0][3],100)
            saved=(dest/'patched.mod').read_bytes()
            with self.assertRaises(FileExistsError):prepare(model,mod,dest)
            self.assertEqual((dest/'patched.mod').read_bytes(),saved)
        other=ROOT/'p2-jellyfloat-assets-01/OniKurage/enemy.bmd'
        self.assertEqual(descriptor(other.read_bytes())[0]['registers'][0],[254,20,169,100])
