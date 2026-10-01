import io
import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

from experimental.pikmin2_collision import plane
from experimental.pikmin2_surface_import import (COURSES, digest, import_surface,
                                                read_member, safe_path, surface_topology,
                                                source_generators, verify_bundle)
from experimental.pikmin2_surface_pocket import generators


class SurfaceImportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.iso = self.root/'source.iso'
        self.iso.write_bytes(b'header'.ljust(0x440, b'\0')+b'textarcroutebad')
        self.route = b'0'
        vertices = [[0, 0, 0], [0, 0, 10], [10, 0, 10]]
        triangle = [0, 2, 1]
        grid = struct.pack('>I', 3)+b''.join(struct.pack('>3f', *v) for v in vertices)
        grid += struct.pack('>I3I16f', 1, *triangle, *plane(vertices, triangle), *([0]*12))
        self.texts = {'grid.bin': grid, 'mapcode.bin': struct.pack('>I', 1)+bytes([9]),
                      'waterbox.txt': b'0 { 1 0 -10 0 10 4 10 }'}

    def extract(self, course='forest', output='bundle'):
        prefix = 'user/Kando/map/'+course+'/'
        gen = 'user/Abe/map/'+course+'/'
        # All sources are actual read bytes; only the disc/archive framing is mocked.
        catalog = {prefix+'texts.szs': (0x440, 4), prefix+'arc.szs': (0x444, 3),
                   gen+'route.txt': (0x447, len(self.route)),
                   gen+'defaultgen.txt': (0x447+len(self.route), 3)}
        def archive(data):
            return self.texts if data == b'text' else {'model.bmd': b'original model'}
        self.iso.write_bytes(b'header'.ljust(0x440, b'\0')+b'textarc'+self.route+b'bad')
        with patch('experimental.pikmin2_surface_import.disc_files', return_value=catalog), \
             patch('experimental.pikmin2_surface_import.archive_files', side_effect=archive):
            return import_surface(self.iso, course, self.root/output)

    def test_all_courses_decode_and_preserve_source_semantics(self):
        for course in COURSES:
            with self.subTest(course=course):
                result = self.extract(course, course)
                bundle = self.root/course
                receipt = verify_bundle(bundle, result['identity'])
                room = json.loads((bundle/'surface-geometry.json').read_bytes())
                self.assertEqual(room['mapcodes'], [9])
                self.assertEqual(result['water_volumes'], 1)
                self.assertEqual(result['vertices'], 3)
                self.assertFalse(result['playable'])
                self.assertTrue(result['generator_errors'])
                self.assertEqual((bundle/'generators/defaultgen.txt').read_bytes(), b'bad')
                self.assertEqual(receipt['course'], course)
                self.assertEqual((bundle/'arc/model.bmd').read_bytes(), b'original model')

    def test_repeated_import_identity_independent_of_destination(self):
        a, b = self.extract(output='first'), self.extract(output='second')
        self.assertEqual(a['identity'], b['identity'])

    def test_bundle_mutation_and_external_receipt_pin_refused(self):
        result = self.extract()
        bundle = self.root/'bundle'
        path = bundle/'surface-geometry.json'
        original = path.read_bytes()
        path.write_bytes(original+b' ')
        with self.assertRaisesRegex(ValueError, 'Changed bundle member'):
            verify_bundle(bundle, result['identity'])
        path.write_bytes(original)
        with self.assertRaisesRegex(ValueError, 'pinned identity'):
            verify_bundle(bundle, '0'*64)
        (bundle/'unexpected.gen').write_bytes(b'extra')
        with self.assertRaisesRegex(ValueError, 'Untracked'):
            verify_bundle(bundle, result['identity'])

    def test_overwrite_refused_before_disc_read(self):
        result = self.extract()
        original = (self.root/'bundle/surface-receipt.json').read_bytes()
        with self.assertRaises(FileExistsError):
            import_surface(self.root/'absent.iso', 'forest', self.root/'bundle')
        self.assertEqual(digest(original), result['identity'])

    def test_missing_source_and_truncated_reads(self):
        with self.assertRaisesRegex(ValueError, 'Missing disc member'):
            read_member(io.BytesIO(), {}, 'absent')
        with self.assertRaisesRegex(ValueError, 'Truncated disc member'):
            read_member(io.BytesIO(b'abc'), {'member': (0, 9)}, 'member')

    def test_unknown_course_and_unsafe_members(self):
        with self.assertRaisesRegex(ValueError, 'Unknown'):
            import_surface(self.iso, 'challenge', self.root/'new')
        for name in ('../outside', '/absolute', 'C:/drive', 'a\\b', './alias', 'a/../b', ''):
            with self.subTest(name=name), self.assertRaises(ValueError):
                safe_path(name)

    def test_decode_failure_has_no_completion_receipt(self):
        self.texts['grid.bin'] = b'bad'
        with self.assertRaisesRegex(ValueError, 'Truncated P2 grid'):
            self.extract()
        self.assertFalse((self.root/'bundle/surface-receipt.json').exists())

    def test_invalid_index_is_not_treated_as_source_degeneracy(self):
        grid = bytearray(self.texts['grid.bin'])
        struct.pack_into('>I', grid, 44, 999)
        self.texts['grid.bin'] = bytes(grid)
        with self.assertRaisesRegex(ValueError, 'Invalid source triangle index'):
            self.extract()
        self.assertFalse((self.root/'bundle/surface-receipt.json').exists())

    def test_degenerate_face_preserved_and_conversion_blocked(self):
        grid = bytearray(self.texts['grid.bin'])
        struct.pack_into('>3I', grid, 44, 0, 0, 1)
        self.texts['grid.bin'] = bytes(grid)
        result = self.extract()
        bundle = self.root/'bundle'
        room = json.loads((bundle/'surface-geometry.json').read_bytes())
        topology = json.loads((bundle/'surface-topology.json').read_bytes())
        self.assertEqual(room['triangles'], [[0, 0, 1]])
        self.assertEqual(room['mapcodes'], [9])
        self.assertEqual(result['degenerate_triangles'], [0])
        self.assertEqual((bundle/'texts/grid.bin').read_bytes(), bytes(grid))
        self.assertFalse(topology['native_conversion_approved'])
        self.assertEqual(topology['audit_triangle_source_ids'], [])
        self.assertEqual(topology['source_triangles'], 1)
        verify_bundle(bundle, result['identity'])

    def test_malformed_routes_refuse_completed_bundle(self):
        # A parsed route pointing to a missing destination is never accepted.
        self.route = b'1 { 0 1 99 0 0 0 1 }'
        with self.assertRaisesRegex(ValueError, 'route'):
            self.extract()
        self.assertFalse((self.root/'bundle/surface-receipt.json').exists())

    def test_topology_diagnostics_keep_source_ids_after_degenerate_face(self):
        room = dict(vertices=[[0,0,0], [0,0,10], [10,0,10], [20,0,10], [30,0,10]],
                    triangles=[[0,0,1], [0,2,1], [0,3,1], [0,4,1]],
                    mapcodes=[9,1,3,5], degenerate_triangles=[0])
        topology = surface_topology(room)
        self.assertFalse(topology['native_conversion_approved'])
        self.assertEqual(topology['audit_triangle_source_ids'], [1,2,3])
        edge = topology['nonmanifold_edges'][0]
        self.assertEqual([row['triangle'] for row in edge['incidents']], [1,2,3])
        self.assertEqual([row['mapcode'] for row in edge['incidents']], [1,3,5])

    def test_symlink_member_refused(self):
        result = self.extract()
        path = self.root/'bundle/arc/model.bmd'
        target = self.root/'external-model'
        target.write_bytes(path.read_bytes())
        path.unlink()
        try:
            path.symlink_to(target)
        except OSError:
            self.skipTest('Host does not permit file symlink creation')
        with self.assertRaisesRegex(ValueError, 'Symlinked'):
            verify_bundle(self.root/'bundle', result['identity'])

    def test_water_errors_refused_before_output_created(self):
        self.texts['waterbox.txt'] = b'0 { 1 0 0 0 1 nan 1 }'
        with self.assertRaisesRegex(ValueError, 'water box'):
            self.extract()
        self.assertFalse((self.root/'bundle').exists())


class DeclaredGeneratorTests(unittest.TestCase):
    def record(self, x=0, version='v0.1'):
        return ('{ {'+version+'} 5 3 '+'0 '*32+f'{x} 0 0 0 0 0 '
                +'{teki} {0005} 76 }')

    def manager(self, count, rows):
        return '{v0.1} 0 0 0 0 '+str(count)+' '+' '.join(rows)

    def test_count_zero_does_not_enable_dormant_rows(self):
        text = self.manager(0, [self.record(1), self.record(2)])
        definition = source_generators(text)
        self.assertEqual(definition['actors'], [])
        self.assertEqual(definition['declared_count'], 0)
        self.assertEqual(definition['serialized_count'], 2)
        self.assertEqual([row['file_record_index'] for row in definition['ignored_records']], [0,1])
        with self.assertRaises(ValueError):
            generators(text)

    def test_only_declared_prefix_is_active(self):
        text = self.manager(1, [self.record(1), self.record(2, 'v0.3')])
        definition = source_generators(text)
        self.assertEqual(len(definition['actors']), 1)
        self.assertEqual(definition['actors'][0]['position'], [1,0,0])
        self.assertEqual(definition['ignored_records'], [dict(file_record_index=1, version='v0.3')])

    def test_exact_count_preserves_existing_valley_result(self):
        text = self.manager(1, [self.record(1)])
        self.assertEqual(source_generators(text), generators(text))

    def test_negative_or_insufficient_declared_count_refused(self):
        for count in (-1, 2):
            with self.subTest(count=count), self.assertRaisesRegex(ValueError, 'declared generator count'):
                source_generators(self.manager(count, [self.record()]))

    def test_malformed_declared_and_dormant_rows_refused(self):
        for text in (self.manager(1, ['{ {v0.1} 5 }']),
                     self.manager(0, ['scalar']), self.manager(0, ['{ {v0.1} 5 }']),
                     self.manager(1, [self.record()])[:-1]):
            with self.subTest(text=text), self.assertRaises(ValueError):
                source_generators(text)


if __name__ == '__main__':
    unittest.main()
