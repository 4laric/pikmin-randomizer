"""Focused tests for the Damagumo arena assembly adapter (#798).

Synthetic inputs only (no engine, no runtime). Verifies the fail-closed
contract: exact canonical hashes, well-formed family/slot profiles, safe actor
identities and correct actor-config grammar. The bind mod size and the
CRLF->LF canonicalization are covered because the landed converter artifacts
store the JSON text CRLF while the pins are canonical LF.
"""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1] / 'experimental' / 'pikmin2_damagumo_arena_assembly.py'
spec = importlib.util.spec_from_file_location('damagumo_arena_assembly', MODULE)
assembly = importlib.util.module_from_spec(spec)
spec.loader.exec_module(assembly)


FAMILY = {
    'schema': 1, 'family': 'Long Legs', 'lane': 'damagumo-profile-convert',
    'profiles': {'56': {
        'enemy_id': 56, 'folder': 'Demon', 'name': 'Damagumo',
        'model_sha256': '8fc0ac7fd6c7585113cf10da12ecd7faccf807896d2d642ab0f80019fff2a961',
        'animation_rows': {'wait': [0, 75], 'flick': [0, 69], 'landing': [0, 69]},
    }},
}
SLOT = {'schema': 1, 'slot': 312004, 'source_id': 56, 'species': 'Damagumo',
        'mesh': 'Demon/enemy.bmd', 'profile': 'damagumo-family.json'}


def build_inputs(directory, family=FAMILY, slot=SLOT, bind_size=assembly.BIND_MOD_BYTES):
    root = Path(directory)
    (root / 'Demon').mkdir(parents=True, exist_ok=True)
    texts = {
        assembly.FAMILY_MANIFEST: json.dumps(family).encode(),
        assembly.SLOT_PROFILE: json.dumps(slot).encode(),
    }
    for name, data in texts.items():
        # store CRLF to mimic the landed artifacts; pins are canonical LF
        (root / name).write_bytes(data.replace(b'\n', b'\r\n'))
    (root / assembly.MESH_NAME).write_bytes(b'MESH' * 4)
    (root / assembly.BIND_MOD).write_bytes(b'M' * bind_size)
    return root


class AssemblyTests(unittest.TestCase):
    def patch_pins(self, root):
        self._saved = assembly.PINNED
        assembly.PINNED = {
            assembly.FAMILY_MANIFEST: (assembly.canonical_sha(
                (root / assembly.FAMILY_MANIFEST).read_bytes(), True), True),
            assembly.SLOT_PROFILE: (assembly.canonical_sha(
                (root / assembly.SLOT_PROFILE).read_bytes(), True), True),
            assembly.MESH_NAME: (assembly.sha((root / assembly.MESH_NAME).read_bytes()), False),
            assembly.BIND_MOD: (assembly.sha((root / assembly.BIND_MOD).read_bytes()), False),
        }

    def tearDown(self):
        if hasattr(self, '_saved'):
            assembly.PINNED = self._saved

    def test_canonical_sha_normalizes_crlf(self):
        self.assertEqual(assembly.canonical_sha(b'a\r\nb', True),
                         assembly.canonical_sha(b'a\nb', True))
        self.assertNotEqual(assembly.canonical_sha(b'a\r\nb', False),
                            assembly.canonical_sha(b'a\nb', False))

    def test_verify_inputs_accepts_crlf_stored_pins(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = build_inputs(tmp)
            self.patch_pins(root)
            loaded = assembly.verify_inputs(root)
            self.assertEqual(loaded['slot']['slot'], 312004)
            self.assertEqual(len(loaded['bind_mod']), assembly.BIND_MOD_BYTES)

    def test_hash_drift_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = build_inputs(tmp)
            self.patch_pins(root)
            (root / assembly.BIND_MOD).write_bytes(b'X' * assembly.BIND_MOD_BYTES)
            with self.assertRaises(assembly.AssemblyRejected):
                assembly.verify_inputs(root)

    def test_missing_input_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = build_inputs(tmp)
            self.patch_pins(root)
            (root / assembly.SLOT_PROFILE).unlink()
            with self.assertRaises(assembly.AssemblyRejected):
                assembly.verify_inputs(root)

    def test_malformed_json_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = build_inputs(tmp)
            self.patch_pins(root)
            (root / assembly.FAMILY_MANIFEST).write_bytes(b'{not json')
            assembly.PINNED[assembly.FAMILY_MANIFEST] = (
                assembly.canonical_sha(b'{not json', True), True)
            with self.assertRaises(assembly.AssemblyRejected):
                assembly.verify_inputs(root)

    def test_wrong_slot_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = dict(SLOT, slot=1)
            root = build_inputs(tmp, slot=bad)
            self.patch_pins(root)
            with self.assertRaises(assembly.AssemblyRejected):
                assembly.verify_inputs(root)

    def test_missing_anchor_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = json.loads(json.dumps(FAMILY))
            bad['profiles']['56']['animation_rows'].pop('flick')
            root = build_inputs(tmp, family=bad)
            self.patch_pins(root)
            with self.assertRaises(assembly.AssemblyRejected):
                assembly.verify_inputs(root)

    def test_actors_text_grammar_and_rejection(self):
        payload = assembly.actors_text([(312004, 'Damagumo'), (312005, 'P1 Chappy')])
        self.assertEqual(payload, b'P2_LONG_LEGS_ACTORS_1\n2\n312004 Damagumo\n312005 P1 Chappy\n')
        with self.assertRaises(assembly.AssemblyRejected):
            assembly.actors_text([(312004, 'Damagumo'), (312004, 'Damagumo')])
        with self.assertRaises(assembly.AssemblyRejected):
            assembly.actors_text([('312004', 'Damagumo')])


if __name__ == '__main__':
    unittest.main()
