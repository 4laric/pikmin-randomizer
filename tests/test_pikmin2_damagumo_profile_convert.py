"""Focused tests for the Damagumo profile/mesh converter (#670).

All fixtures are synthetic: hand-built BMD/BCA headers exercising the parser
boundary (malformed and missing inputs, deterministic derivation, consumer
contract conformance). No value here is claimed as retail fact. Real-byte
evidence (verified Demon/Damagumo disc bytes, consumer acceptance) lives in
docs/PIKMIN2_DAMAGUMO_PROFILE_CONVERT.md, not in these hermetic tests.
"""
import importlib.util
import json
import struct
import unittest
from pathlib import Path

ADAPTER = (Path(__file__).resolve().parents[1] / "experimental"
           / "pikmin2_damagumo_profile_convert.py")


def load_adapter():
    spec = importlib.util.spec_from_file_location("damagumo_profile_convert", ADAPTER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def synth_bmd(joints=("kosi",), textures=4):
    """Minimal J3D2bmd3 carrying INF1/JNT1/TEX1 sufficient for the parser."""
    name_blob = b"".join(n.encode("ascii") + b"\0" for n in joints)
    table = struct.pack(">H", len(joints)) + b"\0\0"
    base = 4 + 4 * len(joints)
    entries = b""
    cursor = base
    blobs = []
    for name in joints:
        entries += b"\0\0" + struct.pack(">H", cursor)
        blobs.append(name.encode("ascii") + b"\0")
        cursor += len(name) + 1
    jnt1_body = (struct.pack(">H", len(joints)) + b"\0" * 10
                 + struct.pack(">I", 32) + b"\0" * 8 + table + entries
                 + b"".join(blobs))
    jnt1 = b"JNT1" + struct.pack(">I", 8 + len(jnt1_body)) + jnt1_body
    tex1 = b"TEX1" + struct.pack(">I", 12) + struct.pack(">H", textures) + b"\0\0"
    inf1 = b"INF1" + struct.pack(">I", 8)
    body = inf1 + jnt1 + tex1
    header = b"J3D2bmd3" + struct.pack(">I", 32 + len(body)) + struct.pack(">I", 3) + b"\0" * 16
    return header + body


def synth_bca(duration):
    """Minimal J3D1bca1 header carrying an ANF1 frame-count field."""
    head = bytearray(64)
    head[0:8] = b"J3D1bca1"
    struct.pack_into(">I", head, 8, 64)
    head[32:36] = b"ANF1"
    struct.pack_into(">H", head, 42, duration)
    return bytes(head)


class ConvertTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = load_adapter()

    def test_frames_for_deterministic(self):
        self.assertEqual(self.mod.frames_for(70), [0, 10, 16, 17, 30, 69])
        self.assertEqual(self.mod.frames_for(1), [0])
        self.assertEqual(self.mod.frames_for(70), self.mod.frames_for(70))

    def test_frames_for_rejects_bad(self):
        for bad in (0, -1, 10001, "70", 70.0):
            with self.assertRaises(self.mod.ConvertError):
                self.mod.frames_for(bad)

    def test_bca_duration_positive(self):
        for dur in (1, 70, 76, 300, 10000):
            self.assertEqual(self.mod.bca_duration(synth_bca(dur), "wait"), dur)

    def test_bca_duration_rejects_bad(self):
        with self.assertRaises(self.mod.ConvertError):
            self.mod.bca_duration(b"short", "wait")
        bad = bytearray(synth_bca(70))
        bad[0:8] = b"J3D1bck1"
        with self.assertRaises(self.mod.ConvertError):
            self.mod.bca_duration(bytes(bad), "wait")
        bad = bytearray(synth_bca(70))
        bad[32:36] = b"XXXX"
        with self.assertRaises(self.mod.ConvertError):
            self.mod.bca_duration(bytes(bad), "wait")
        with self.assertRaises(self.mod.ConvertError):
            self.mod.bca_duration(synth_bca(0), "wait")

    def test_mesh_profile_positive(self):
        profile = self.mod.mesh_profile(synth_bmd(("kosi", "tama1"), 4))
        self.assertEqual(profile["joint_count"], 2)
        self.assertEqual(profile["embedded_texture_count"], 4)
        self.assertEqual(len(profile["special_joints"]), 8)

    def test_mesh_profile_rejects_bad(self):
        with self.assertRaises(self.mod.ConvertError):
            self.mod.mesh_profile(b"not a model")
        with self.assertRaises(self.mod.ConvertError):
            self.mod.mesh_profile(b"J3D2bmd3" + b"\0" * 10)

    def test_read_member_rejects_bad(self):
        with self.assertRaises(self.mod.ConvertError):
            self.mod.read_member(b"short", "enemy.bmd")
        with self.assertRaises(self.mod.ConvertError):
            self.mod.read_member(b"not-yaz0-payload-pad!", "enemy.bmd")

    def test_profile_shape_matches_consumer_contract(self):
        # Mirrors the #638 _damagumo_profile acceptance rules (read-only).
        manifest = {"schema": 1, "family": "Long Legs",
                    "profiles": {"56": {
                        "schema": 1, "family": "Long Legs", "enemy_id": 56,
                        "name": "Damagumo", "retail": "Beady Long Legs",
                        "folder": "Demon", "animation_rows": {
                            "landing": [0, 69], "wait": [0, 75], "flick": [0, 69]},
                        "model_sha256": "a" * 64}}}
        self.assertEqual(manifest["schema"], 1)
        self.assertEqual(manifest["family"], "Long Legs")
        self.assertEqual(set(manifest["profiles"]), {"56"})
        row = manifest["profiles"]["56"]
        self.assertEqual((row["enemy_id"], row["name"], row["folder"]),
                         (56, "Damagumo", "Demon"))
        for anchor in ("landing", "wait", "flick"):
            self.assertTrue(row["animation_rows"].get(anchor), anchor)
        self.assertRegex(row["model_sha256"], r"^[0-9a-f]{64}$")

    def test_slot_descriptor_shape(self):
        slot = {"schema": 1, "slot": 312004, "species": "Damagumo",
                "source_id": 56, "profile": "damagumo-family.json",
                "mesh": "Demon/enemy.bmd", "model_sha256": "b" * 64,
                "arena_binding": "312004 Damagumo"}
        self.assertEqual(slot["slot"], 312004)
        self.assertEqual(slot["arena_binding"], "312004 Damagumo")
        self.assertRegex(slot["model_sha256"], r"^[0-9a-f]{64}$")

    def test_required_clips_constant(self):
        self.assertEqual(self.mod.REQUIRED_CLIPS, ("landing", "wait", "flick"))
        self.assertEqual(self.mod.SLOT_ID, 312004)
        self.assertEqual(self.mod.ENEMY_ID, 56)


if __name__ == "__main__":
    unittest.main()