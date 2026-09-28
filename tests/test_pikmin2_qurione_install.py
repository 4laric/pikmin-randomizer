import tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from experimental.pikmin2_qurione_install import install,verified
class QurioneInstallTests(unittest.TestCase):
    def test_hash_refusal(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'asset';p.write_bytes(b'changed')
            with self.assertRaises(ValueError):verified(p,'0'*64)
    def test_ids(self):
        for ids in ([],[True],[1,1],[-1],[2**32],list(range(9))):
            with self.assertRaises(ValueError):install(Path('.'),Path('.'),ids,'0'*64)
    def test_install_exact_bytes_and_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            run=Path(d);room=run/'assets/dataDir/courses/pikmin2room';room.mkdir(parents=True)
            with patch('experimental.pikmin2_qurione_install.payload',return_value=({'qurione_waitl_00.mod':b'model'},b'bank\n')):
                install(Path('.'),run,[203001],'a'*64)
                self.assertEqual((run/'p2-qurione-bank.txt').read_bytes(),b'bank\n')
                self.assertEqual((run/'p2-qurione-actors.txt').read_bytes(),b'P2_QURIONE_ACTORS_1 1\n203001\n')
                with self.assertRaises(ValueError):install(Path('.'),run,[203001],'a'*64)
    def test_conflict_before_write(self):
        with tempfile.TemporaryDirectory() as d:
            run=Path(d);room=run/'assets/dataDir/courses/pikmin2room';room.mkdir(parents=True)
            (run/'p2-other-actors.txt').write_bytes(b'P2_OTHER_ACTORS_1 1\n203001\n')
            with patch('experimental.pikmin2_qurione_install.payload',return_value=({'qurione_waitl_00.mod':b'model'},b'bank\n')):
                with self.assertRaises(ValueError):install(Path('.'),run,[203001],'a'*64)
            self.assertFalse(list(room.iterdir()))
if __name__=='__main__':unittest.main()
