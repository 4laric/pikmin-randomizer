from pathlib import Path
import tempfile
import unittest
from scripts.bundle_pikmin2_fixture import bundle, plan


class BundleTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve()
        self.dlls, self.system = self.root/'dlls', self.root/'system'
        self.dlls.mkdir(); self.system.mkdir()
        self.exe = self.root/'fixture.exe'; self.exe.write_bytes(b'exe')
        for name in ('a.dll', 'b.dll'):
            (self.dlls/name).write_bytes(name.encode())
        (self.system/'kernel32.dll').write_bytes(b'system')
        self.graph = {'fixture.exe':['A.dll'], 'a.dll':['b.dll'],
                      'b.dll':['a.dll','KERNEL32.dll']}

    def imports(self, path):
        return self.graph[path.name.lower()]

    def test_transitive_cycle_and_system_exclusion(self):
        result = bundle(self.exe, [self.dlls], self.system, self.root/'out', self.imports)
        self.assertEqual([f['name'] for f in result['files']], ['a.dll','b.dll','fixture.exe'])
        self.assertEqual(result['system_imports'], ['KERNEL32.dll'])
        self.assertEqual((self.root/'out/b.dll').read_bytes(), b'b.dll')
        self.assertFalse((self.root/'out/kernel32.dll').exists())

    def test_missing_rejected_before_output(self):
        (self.dlls/'b.dll').unlink()
        with self.assertRaisesRegex(ValueError, 'Missing or ambiguous'):
            bundle(self.exe,[self.dlls],self.system,self.root/'out',self.imports)
        self.assertFalse((self.root/'out').exists())

    def test_ambiguous_even_with_identical_bytes(self):
        other=self.root/'other'; other.mkdir(); (other/'a.dll').write_bytes(b'a.dll')
        with self.assertRaisesRegex(ValueError, 'ambiguous'):
            plan(self.exe,[self.dlls,other],self.system,self.imports)

    def test_existing_directory_untouched(self):
        out=self.root/'out'; out.mkdir(); (out/'keep').write_bytes(b'keep')
        with self.assertRaisesRegex(ValueError,'existing output'):
            bundle(self.exe,[self.dlls],self.system,out,self.imports)
        self.assertEqual(list(out.iterdir()),[out/'keep'])

    def test_system_shadow_rejected(self):
        (self.dlls/'kernel32.dll').write_bytes(b'fake')
        with self.assertRaisesRegex(ValueError,'shadowed'):
            plan(self.exe,[self.dlls],self.system,self.imports)

    def test_unsafe_dependency(self):
        self.graph['fixture.exe']=['../a.dll']
        with self.assertRaisesRegex(ValueError,'Unsafe'):
            plan(self.exe,[self.dlls],self.system,self.imports)

    def test_mutating_input_rejected(self):
        def mutate(path):
            path.write_bytes(b'changed')
            return []
        with self.assertRaisesRegex(ValueError,'changed during'):
            plan(self.exe,[self.dlls],self.system,mutate)


if __name__ == '__main__':
    unittest.main()
