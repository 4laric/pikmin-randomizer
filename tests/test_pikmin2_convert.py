"""Asset-independent format contracts plus optional locally supplied room regression."""
from pathlib import Path
import struct
import unittest
import tempfile
from experimental.pikmin2_convert import Writer, blocks, convert, decode

ROOM=Path(__file__).resolve().parents[1]/'output/pikmin2-content-probe/arc/view.bmd'
class ConverterTests(unittest.TestCase):
    def test_rejects_wrong_container_and_truncated_blocks(self):
        with self.assertRaises(ValueError): blocks(b'not a model')
        data=b'J3D2bmd3'+struct.pack('>II',40,1)+bytes(16)+b'VTX1'+struct.pack('>I',64)
        with self.assertRaisesRegex(ValueError,'block length'): blocks(data)

    def test_chunk_size_excludes_header_and_padding_is_aligned(self):
        w=Writer();w.begin(16,2);w.pad();w.put('6f',1,2,3,4,5,6);w.end()
        assert len(w.data)==64
        assert struct.unpack_from('>III',w.data)==(16,56,2)
        assert struct.unpack_from('>6f',w.data,32)==(1,2,3,4,5,6)

    @unittest.skipUnless(ROOM.exists(),'Requires locally extracted user-owned asset')
    def test_room_geometry_bounds_and_mod_chunk_chain(self):
        temporary=tempfile.TemporaryDirectory(); self.addCleanup(temporary.cleanup); tmp_path=Path(temporary.name)
        report=convert(ROOM,tmp_path/'room.mod')
        assert report['vertices']==350
        assert report['triangles']==530
        assert report['bounds']==[-425.,-1.,-425.,425.,65.,425.]
        blob=(tmp_path/'room.mod').read_bytes(); at=0; tags=[]
        while at<len(blob):
            assert at%32==0
            tag,size=struct.unpack_from('>II',blob,at);tags.append(tag)
            if tag==64:
                # VtxMatrix::read: >=0 indexes joints; -(n+1) indexes envelopes.
                # There are zero envelopes, so -1 would read beyond animated matrices.
                assert struct.unpack_from('>I',blob,at+8)[0]==1
                assert struct.unpack_from('>h',blob,at+32)[0]==0
            if tag==34:
                assert struct.unpack_from('>4Hf',blob,at+32)==(0,0,0,0,0.)
                assert struct.unpack_from('>4Hf',blob,at+44)==(1,0,0,0,0.)
            at+=8+size
        assert at==len(blob)
        assert tags==[0,16,17,19,24,32,34,48,64,80,96,65535]

    @unittest.skipUnless(ROOM.exists(),'Requires locally extracted user-owned asset')
    def test_nonidentity_joint_is_rejected(self):
        blob=bytearray(ROOM.read_bytes());at=32
        while blob[at:at+4]!=b'JNT1':at+=struct.unpack_from('>I',blob,at+4)[0]
        joint=at+struct.unpack_from('>I',blob,at+12)[0]
        struct.pack_into('>f',blob,joint+4,2.)
        with self.assertRaisesRegex(ValueError,'Non-identity'):decode(blob)

    @unittest.skipUnless(ROOM.exists(),'Requires locally extracted user-owned asset')
    def test_floor_alignment_translates_only_positions_and_bounds(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)
            original=convert(ROOM,path/'original.mod')
            shifted=convert(ROOM,path/'shifted.mod',y_offset=-1)
            assert shifted['bounds']==[-425.,-2.,-425.,425.,64.,425.]
            def chunks(data):
                out={};at=0
                while at<len(data):
                    tag,size=struct.unpack_from('>II',data,at)
                    out[tag]=data[at:at+8+size];at+=8+size
                return out
            a=chunks((path/'original.mod').read_bytes()); b=chunks((path/'shifted.mod').read_bytes())
            for tag in a:
                if tag not in (16,96): assert a[tag]==b[tag]
            for i in range(original['vertices']):
                x,y,z=struct.unpack_from('>3f',a[16],32+i*12)
                xx,yy,zz=struct.unpack_from('>3f',b[16],32+i*12)
                assert (xx,zz)==(x,z)
                self.assertAlmostEqual(yy,y-1,delta=0.00001)
