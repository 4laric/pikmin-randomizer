"""Developer cave only: no released manifest, fill, campaign session, or AP imports."""
import copy
import hashlib
import json
import os
import unittest
from pathlib import Path
import tempfile
from unittest.mock import patch
from randomizer.cave_floor import create, validate, fingerprint, resolve, NAMES


class SpeciesBankTests(unittest.TestCase):
    """Tiny byte fixtures exercise policy only; they are not renderable source assets."""
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)

    def bank(self,species=3):
        name={3:'purple',4:'white'}[species];directory=self.root/name;directory.mkdir()
        text=f'P2_{name.upper()}_1\r\nstats 1 1 1 1 1 1 1 1 1\r\n'
        if species==4:text+='ivory_generators 2 25 4294967295\r\n'
        text+='wait 1 .5\r\nwalk 1 1\r\nattack1 1 2\r\n'
        for motion in ('wait','walk','attack1'):
            text+=f'happa {motion} 0 '+' '.join(['1']*12)+'\r\n'
            (directory/f'{name}_{motion}_00.mod').write_bytes(b'policy-only model '+motion.encode())
        for i in range(3):(directory/f'{name}_happa_{i}.mod').write_bytes(b'policy-only happa '+bytes([i]))
        (directory/f'p2-{name}.txt').write_bytes(text.encode())
        return directory

    def test_package_copy_pins_every_byte_and_detects_tamper(self):
        from scripts.stage_pikmin2_playable_cave import pin_species_banks,verify_species_banks
        source=self.bank();package=self.root/'package';package.mkdir()
        record=pin_species_banks(package,{3:source});banks=verify_species_banks(package,record)
        self.assertEqual(len(record['3']['files']),7)
        for name in record['3']['files']:self.assertEqual((source/name).read_bytes(),(banks[3]/name).read_bytes())
        (banks[3]/'purple_walk_00.mod').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'changed'):verify_species_banks(package,record)

    def test_missing_model_attachment_and_duplicate_ivory_refuse(self):
        from scripts.stage_pikmin2_playable_cave import species_bank_files
        source=self.bank(4);config=source/'p2-white.txt';original=config.read_bytes()
        for bad in (original.replace(b'25 4294967295',b'25 25'),original.replace(b'25 4294967295',b'25 4294967296'),
                    original.replace(b'happa walk 0',b'happa wait 0'),original.replace(b'walk 1 1',b'walk 33 1'),
                    original.replace(b'stats 1',b'stats nan'),original.replace(b'happa attack1 0',b'happa attack1 1')):
            config.write_bytes(bad)
            with self.assertRaises(ValueError):species_bank_files(4,source)
        config.write_bytes(original);(source/'white_happa_2.mod').unlink()
        with self.assertRaisesRegex(ValueError,'missing'):species_bank_files(4,source)

    def test_surface_impact_fails_without_stripping_room_config(self):
        from scripts.stage_pikmin2_playable_cave import species_bank_files
        source=self.bank();config=source/'p2-purple.txt';config.write_bytes(config.read_bytes()+b'impact red_earthquake_v1\n')
        self.assertEqual(species_bank_files(3,source)['p2-purple.txt'],config.read_bytes())
        with self.assertRaisesRegex(ValueError,'unsupported surface auxiliary bank'):species_bank_files(3,source,surface=True)

    def test_config_requires_native_float32_duration_and_matrix_values(self):
        from scripts.stage_pikmin2_playable_cave import species_bank_files
        source=self.bank();config=source/'p2-purple.txt';original=config.read_bytes()
        for bad in (original.replace(b'wait 1 .5',b'wait 1 1e100'),
                    original.replace(b'wait 1 .5',b'wait 1 1e-100'),
                    original.replace(b'happa wait 0 1 ',b'happa wait 0 1e100 ')):
            config.write_bytes(bad)
            with self.assertRaises(ValueError):species_bank_files(3,source)
        # A representable positive duration and matrix survive validation;
        # the loader must not rewrite their original decimal representation.
        valid=original.replace(b'wait 1 .5',b'wait 1 1.23456789e-3').replace(b'happa wait 0 1 ',b'happa wait 0 1.23456789 ')
        config.write_bytes(valid);self.assertEqual(species_bank_files(3,source)['p2-purple.txt'],valid)

    def test_route_impact_refuses_package_and_every_phase_before_staging(self):
        from scripts.stage_pikmin2_playable_cave import pin_species_banks
        from scripts.stage_pikmin2_cave_route import stage_package,stage_surface,ROUTE_START
        from scripts.play_pikmin2_cave_route import route_species_banks
        source=self.bank();config=source/'p2-purple.txt';config.write_bytes(config.read_bytes()+b'impact red_earthquake_v1\n')
        original=config.read_bytes();package=self.root/'package'
        with patch('scripts.stage_pikmin2_cave_route.stage_journey') as journey:
            with self.assertRaisesRegex(ValueError,'unsupported surface auxiliary bank'):
                stage_package('1161','Player1',self.root,self.root,self.root,self.root,self.root,'c'*64,package,self.root,{3:source})
            journey.assert_not_called()
        self.assertFalse(package.exists())
        package.mkdir();record=pin_species_banks(package,{3:source})
        # A package created outside route admission must also refuse at the
        # common package/floor/surface per-phase gate even though hashes match.
        with self.assertRaisesRegex(ValueError,'unsupported surface auxiliary bank'):route_species_banks(package,record)
        with patch('scripts.stage_pikmin2_cave_route.prepare') as prepare:
            with self.assertRaisesRegex(ValueError,'unsupported surface auxiliary bank'):
                stage_surface(self.root,self.root,'c'*64,self.root/'output',self.root,
                              dict(position=ROUTE_START,health=1,squad=[[1,0]]), 'a'*32,{3:source})
            prepare.assert_not_called()
        self.assertEqual(config.read_bytes(),original)
        from randomizer.cave_floor import create_wfg_acquisition
        from scripts.stage_pikmin2_playable_cave import stage
        white=self.bank(4);output=self.root/'direct-wfg'
        with self.assertRaisesRegex(ValueError,'unsupported surface auxiliary bank'):
            stage(create_wfg_acquisition('1161'),self.root,self.root,self.root,self.root,output,
                  species_banks={3:source,4:white})
        self.assertFalse(output.exists())

    def test_private_install_does_not_change_shared_hardlink(self):
        import os
        from scripts.stage_pikmin2_playable_cave import read_species_banks,install_species_banks,SPECIES_MODEL_DIR
        source=self.bank();run=self.root/'run';models=run/SPECIES_MODEL_DIR;models.mkdir(parents=True)
        shared=self.root/'shared.mod';shared.write_bytes(b'preserved shared model');os.link(shared,models/'purple_wait_00.mod')
        files=install_species_banks(run,read_species_banks({3:source}))
        self.assertEqual(shared.read_bytes(),b'preserved shared model');self.assertEqual(len(files),7)
        self.assertEqual((run/'p2-purple.txt').read_bytes(),(source/'p2-purple.txt').read_bytes())

    @unittest.skipUnless(os.name=='nt','Windows junction policy')
    def test_private_install_materializes_junction_without_editing_source(self):
        import _winapi
        from scripts.stage_pikmin2_playable_cave import read_species_banks,install_species_banks,SPECIES_MODEL_DIR
        source=self.bank();shared=self.root/'shared-room';shared.mkdir()
        (shared/'purple_wait_00.mod').write_bytes(b'original shared model')
        run=self.root/'run';target=run/SPECIES_MODEL_DIR;target.parent.mkdir(parents=True)
        _winapi.CreateJunction(str(shared),str(target))
        self.assertFalse(target.resolve().is_relative_to(run.resolve()))
        install_species_banks(run,read_species_banks({3:source}))
        self.assertTrue(target.resolve().is_relative_to(run.resolve()))
        self.assertEqual((shared/'purple_wait_00.mod').read_bytes(),b'original shared model')
        self.assertEqual((target/'purple_wait_00.mod').read_bytes(),(source/'purple_wait_00.mod').read_bytes())

    def test_surface_retained_wire2_base_party_has_no_bank_activation(self):
        import struct
        from scripts.stage_pikmin2_cave_route import stage_surface,ROUTE_START
        # Minimal private generator fixture, not runnable retail/generated content.
        run=self.root/'run';directory=run/'assets/dataDir/stages/p2_tutorial';directory.mkdir(parents=True)
        header=b'1.0v'+struct.pack('>4fI',0,0,0,0,20)
        row=bytearray(96);row[:8]=b'    0.0v';row[72:76]=b'ikip'
        (directory/'default.gen').write_bytes(header+bytes(row)*20)
        for name in ('init.gen','plants.gen','day.gen'):(directory/name).write_bytes(header[:20]+struct.pack('>I',0))
        (run/'assets/dataDir/courses/p2tutorial').mkdir(parents=True)
        (run/'assets/dataDir/courses/p2tutorial/full.water').write_bytes(b'policy water')
        (run/'surface-water.json').write_text('{}')
        (run/'surface-water-inputs.json').write_text('{}')
        (run/'full-surface-inputs.json').write_text(json.dumps({'files':{f'dataDir/stages/p2_tutorial/{name}':'' for name in ('default.gen','init.gen','plants.gen','day.gen')}}))
        exe=self.root/'source.exe';exe.write_bytes(b'policy-only executable')
        source=self.bank();surface=dict(position=ROUTE_START,health=1,squad=[[1,0]]*20,wire_schema=2)
        with patch('scripts.stage_pikmin2_cave_route.prepare',return_value=run):
            result,inputs=stage_surface(self.root,self.root,'c'*64,self.root/'output',exe,surface,'a'*32,{3:source})
        self.assertEqual(result,run)
        self.assertFalse((run/'p2-cave-route-species.txt').exists())
        self.assertFalse((run/'p2-purple.txt').exists())
        self.assertFalse((run/'p2-cave-route-destination.txt').exists())
        self.assertFalse(any('purple' in name for name in inputs))
        self.assertTrue((run/'p2-cave-route-surface.txt').read_text().startswith('P2_CAVE_ROUTE_SURFACE_2 '))
        token='b'*32
        with patch('scripts.stage_pikmin2_cave_route.prepare',return_value=run):
            result,inputs=stage_surface(self.root,self.root,'c'*64,self.root/'output',exe,surface,token,
                                       destination='forest_2/f_02')
        sidecar=run/'p2-cave-route-destination.txt'
        self.assertEqual(sidecar.read_text(),f'P2_CAVE_ROUTE_DESTINATION_1 {token} forest_2/f_02\n')
        self.assertIn(sidecar.name,inputs)
        recorded=json.loads((run/'route-surface-inputs.json').read_text())
        self.assertEqual(recorded['destination'],'forest_2/f_02')
        self.assertEqual(recorded['files'][sidecar.name],hashlib.sha256(sidecar.read_bytes()).hexdigest())
        sidecar.write_text('foreign token')
        self.assertNotEqual(recorded['files'][sidecar.name],hashlib.sha256(sidecar.read_bytes()).hexdigest())


    def test_surface_activation_seals_actual_party_config_and_identity(self):
        from scripts.stage_pikmin2_playable_cave import read_species_banks,install_species_banks,seal_surface_species
        from scripts.play_pikmin2_cave_route import verify_run_banks
        source=self.bank();run=self.root/'run';run.mkdir();(run/'assets/dataDir/courses').mkdir(parents=True)
        files=install_species_banks(run,read_species_banks({3:source}));token='a'*32
        config=run/'p2-cave-route-surface.txt';config.write_text(f'P2_CAVE_ROUTE_SURFACE_2 {token} -210 80 1160 60 .5 2\n3 2\n1 1\n')
        identity=dict(seed=18446744073709551615,slot_hash='b'*64,receipt_identity='c'*64)
        sealed=seal_surface_species(run,token,identity,files,[3])
        manifest=(run/'p2-cave-route-species.txt').read_text()
        self.assertIn(f'route tutorial forest_1 {token} 2 '+hashlib.sha256(config.read_bytes()).hexdigest(),manifest)
        self.assertIn('species 1 3\nfiles 8\n',manifest)
        self.assertIn('p2-cave-route-identity.txt',sealed)
        self.assertEqual((run/'p2-cave-route-identity.txt').read_text(),f"P2_CAVE_ROUTE_IDENTITY_1 {identity['seed']} {'b'*64} {'c'*64} forest_1 tutorial\n")
        with self.assertRaisesRegex(ValueError,'differs from actual party'):seal_surface_species(run,token,identity,files,[4])
        with self.assertRaisesRegex(ValueError,'identity'):seal_surface_species(run,token,dict(identity,slot_hash='foreign'),files,[3])
        records={'3':{'files':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in source.iterdir()}}}
        verify_run_banks(run,records,[3]);(run/'p2-purple.txt').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'differs from package'):verify_run_banks(run,records,[3])

    def test_between_phase_binary_and_replacement_metadata_cannot_repin(self):
        from scripts.play_pikmin2_cave_route import capture_package_pins,verify_package_pins,verify_copied_inputs
        package=self.root/'package';package.mkdir()
        for name in ('nectar.exe','cave-generator.exe','runtime.dll'):(package/name).write_bytes(('original '+name).encode())
        blueprint=package/'surface-blueprint/run';blueprint.mkdir(parents=True)
        (blueprint/'terrain.mod').write_bytes(b'original terrain')
        digest=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
        meta={'files':{name:digest(package/name) for name in ('nectar.exe','cave-generator.exe','runtime.dll')}}
        spec={'files':{'terrain.mod':digest(blueprint/'terrain.mod')},'geometry':{'terrain.mod':digest(blueprint/'terrain.mod')}}
        (package/'package.json').write_text(json.dumps(meta));(package/'route-package.json').write_text(json.dumps(spec))
        pins=capture_package_pins(package,meta,spec)
        # Phase1 passes. During its child, sources and on-disk authority may
        # both change; phase2 must still use the original captured pins.
        verify_package_pins(package,pins)
        original_meta=(package/'package.json').read_bytes()
        for name in ('nectar.exe','cave-generator.exe','runtime.dll'):
            original=(package/name).read_bytes();(package/name).write_bytes(b'changed between phases')
            replacement=copy.deepcopy(meta);replacement['files'][name]=digest(package/name)
            (package/'package.json').write_text(json.dumps(replacement))
            with self.assertRaisesRegex(ValueError,'original package input changed'):verify_package_pins(package,pins)
            (package/name).write_bytes(original);(package/'package.json').write_bytes(original_meta)
        run=self.root/'run';run.mkdir()
        for name in meta['files']:(run/name).write_bytes((package/name).read_bytes())
        self.assertEqual(set(verify_copied_inputs(run,pins,'floor1')),set(meta['files']))
        (run/'nectar.exe').write_bytes(b'copy changed after stage')
        with self.assertRaisesRegex(ValueError,'copied runtime input changed'):verify_copied_inputs(run,pins,'floor1')
        (package/'extra.dll').write_bytes(b'unpinned new dependency')
        with self.assertRaisesRegex(ValueError,'DLL inventory'):verify_package_pins(package,pins)

    @unittest.skipUnless(os.name=='nt','Windows junction policy')
    def test_package_pins_reject_linked_paths_even_with_matching_bytes(self):
        import _winapi
        from scripts.play_pikmin2_cave_route import verify_package_pins
        package=self.root/'package';package.mkdir();outside=self.root/'outside';outside.mkdir()
        (outside/'model.mod').write_bytes(b'unchanged model')
        _winapi.CreateJunction(str(outside),str(package/'linked'))
        digest=hashlib.sha256((outside/'model.mod').read_bytes()).hexdigest()
        with self.assertRaisesRegex(ValueError,'linked pinned path'):verify_package_pins(package,{'linked/model.mod':digest})
        with self.assertRaisesRegex(ValueError,'foreign pinned path'):verify_package_pins(package,{'../outside/model.mod':digest})


def fixture_layout():
    """Synthetic graph for geometry unit tests; not native-generation evidence."""
    table = create('930')['table']
    nodes = [dict(id=row['slot_id'], kind='segment', segment_index=row['index'])
             for row in table['segments']]
    first, last = [row['id'] for row in nodes]
    choke = table['chokes'][0]['slot_id']
    nodes.append(dict(id=choke, kind='choke', hazard='water', segment_index=1))
    edges = [[first, choke], [choke, last]]
    for row in table['leaves']:
        nodes.append(dict(id=row['slot_id'], kind='leaf', hazard=row['hazard'],
                          segment_index=row['segment']))
        edges.append([[first, last][row['segment']], row['slot_id']])
    for row in table['buds']:
        nodes.append(dict(id=row['slot_id'], kind='bud',
                          hazard={'blue': 'water', 'yellow': 'elec'}[row['species']],
                          segment_index=row['segment']))
        edges.append([[first, last][row['segment']], row['slot_id']])
    return dict(schema='p2-cave-observed-layout/1', source='fixture', cave='forest_1',
                floor=1, seed=930, nodes=nodes, edges=edges, entrance=first, hole=last)


class WfgAcquisitionTests(unittest.TestCase):
    """Synthetic policy fixtures; none is native generation or runtime evidence."""
    def fixture(self):
        from randomizer.cave_floor import create_wfg_acquisition
        from experimental.pikmin2_cave_lane41_generator import _seed_uint64
        descriptor=create_wfg_acquisition('1161')
        table=descriptor['table']; nodes=[]; edges=[]
        for row in table['segments']:
            nodes.append(dict(id=row['slot_id'],kind='segment',segment_index=row['index'],hazard='none',items=[]))
        for row in table['buds']:
            nodes.append(dict(id=row['slot_id'],kind='bud',segment_index=row['segment'],
                              hazard='none' if row['species']=='purple' else 'poison',items=[]))
            edges.append([table['segments'][row['segment']]['slot_id'],row['slot_id']])
        edges.append([table['segments'][0]['slot_id'],table['segments'][1]['slot_id']])
        layout=dict(schema='p2-cave-observed-layout/1',source='engine',cave='forest_2',floor=1,
                    seed=_seed_uint64(table['seed']),nodes=nodes,edges=edges,
                    entrance=table['segments'][0]['slot_id'],hole=table['segments'][1]['slot_id'])
        return descriptor,layout

    def test_optin_namespace_preserves_exact_legacy_descriptor_bytes(self):
        from randomizer.cave_floor import create_journey_floor,create_wfg_acquisition,fingerprint
        self.assertEqual(fingerprint(create('930')),'f4ac3b78b6ff81adbe0aad75398e35af9f89a49ad326a4bfaef646bf7078f54c')
        self.assertEqual(fingerprint(create_journey_floor('930','Player1',1)),
                         'b72abf88d58841b35f06bea920034f42e421cb4053f8b7d12dae4aed36414cf4')
        descriptor=create_wfg_acquisition('1161');self.assertEqual(descriptor,validate(copy.deepcopy(descriptor)))
        self.assertEqual(descriptor['source_course'],'forest_2/f_02')
        self.assertEqual([b['species'] for b in descriptor['table']['buds']],['purple','white'])
        self.assertNotEqual(fingerprint(descriptor),fingerprint(create_wfg_acquisition('1162')))
        bad=copy.deepcopy(descriptor);bad['table']['cave_id']='forest_1'
        with self.assertRaises(ValueError):validate(bad)

    def test_room_bridge_requires_exact_optin_capability_binding(self):
        from experimental.pikmin2_cave_rooms import rooms_from_layout
        descriptor,layout=self.fixture()
        with self.assertRaises(ValueError):rooms_from_layout(layout)
        rooms=rooms_from_layout(layout,acquisition_descriptor=descriptor)
        self.assertEqual(next(u for u in rooms['units'] if u['id'].endswith('bud:0'))['hazard'],'none')
        for alter in ('seed','cave','duplicate','species','edge'):
            bad=copy.deepcopy(layout)
            if alter=='seed':bad['seed']+=1
            elif alter=='cave':bad['cave']='forest_1'
            elif alter=='duplicate':bad['nodes'].append(copy.deepcopy(bad['nodes'][-1]))
            elif alter=='species':bad['nodes'][2]['hazard']='poison'
            else:bad['edges'][0]=bad['edges'][1]
            with self.assertRaises(ValueError):rooms_from_layout(bad,acquisition_descriptor=descriptor)

    @patch('scripts.stage_pikmin2_playable_cave.is_windows',return_value=True)
    def test_wfg_stage_pins_real_body_inputs_and_entry2_red_baseline(self,_platform):
        import struct
        from scripts.stage_pikmin2_playable_cave import stage,SPECIES_MODEL_DIR
        descriptor,layout=self.fixture()
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);helper=SpeciesBankTests();helper.root=root
            purple=helper.bank(3);white=helper.bank(4)
            config=white/'p2-white.txt';config.write_bytes(config.read_bytes().replace(
                b'ivory_generators 2 25 4294967295',b'ivory_generators 1 25'))
            original=config.read_bytes()
            assets=root/'assets';(assets/'dataDir/stages/chal0').mkdir(parents=True)
            (assets/'dataDir/stages/chal0/default.gen').write_bytes(b'policy template')
            (assets/'dataDir/stages/chal0.ini').write_bytes(b'map_file source.mod\nnavi_start 0 0\n')
            pod=root/'pod';pod.mkdir()
            for name in ('pod.mod','treasure.mod','p2-pod.txt'):(pod/name).write_bytes(b'policy '+name.encode())
            exe=root/'source.exe';exe.write_bytes(b'MZ'+bytes(1024))
            rows=[]
            for uid,label,kind in ((1,'preview red onion',b'goal'),(2,'preview ship',b'goal'),
                                   (3,'preview treasure bolt',b'cargo'),(4,'preview red pikmin',b'ikip')):
                row=bytearray(96);row[:8]=b'    0.0v';struct.pack_into('<I',row,8,uid)
                row[16:48]=label.encode().ljust(32,b'\0');row[72:76]=kind
                if kind==b'ikip':struct.pack_into('>I',row,92,1)
                rows.append(row)
            blob=b'1.0v'+struct.pack('>4fI',0,0,0,0,len(rows))+b''.join(rows)
            pom=bytearray(96);pom[:8]=b'    0.0v';pom[72:76]=b'ssob';pom[76:80]=b'\x02\x00\x00\x00'
            def private_overlay(source,dest,overrides):
                dest.mkdir(parents=True)
                for name,data in overrides.items():
                    path=dest/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
            def native_policy_fixture(tool,table,out):
                out.write_text(json.dumps(layout));return {'layout':layout}
            output=root/'run'
            with patch('scripts.stage_pikmin2_playable_cave.run_native_generator',side_effect=native_policy_fixture), \
                 patch('scripts.stage_pikmin2_playable_cave.generator',return_value=blob), \
                 patch('scripts.stage_pikmin2_playable_cave.records',return_value=[bytes(pom)]), \
                 patch('scripts.stage_pikmin2_playable_cave.mesh',return_value=(b'policy model',b'policy routes')) as mesh, \
                 patch('scripts.stage_pikmin2_playable_cave.overlay',side_effect=private_overlay):
                meta=stage(descriptor,assets,pod,exe,exe,output,species_banks={3:purple,4:white})
            self.assertIn('p2-cave-route-pom.txt',meta['files'])
            self.assertIn('p2-white.txt',meta['files'])
            self.assertFalse(mesh.call_args.kwargs['flower_markers'])
            self.assertEqual((output/'p2-white.txt').read_bytes(),original)
            self.assertEqual((output/SPECIES_MODEL_DIR/'white_wait_00.mod').read_bytes(),(white/'white_wait_00.mod').read_bytes())
            entry=(output/'p2-cave-entry.txt').read_text().splitlines()
            self.assertEqual(entry[0].split()[0],'P2_CAVE_ENTRY_2');self.assertEqual(entry[-20:],['1 0']*20)
            self.assertIn('not retail White Flower Garden',meta['geometry'])

    def test_explicit_three_phase_package_api_and_immutable_acquisition_inputs(self):
        from scripts.stage_pikmin2_cave_route import stage_package
        from scripts.play_pikmin2_cave_route import route_inputs,capture_package_pins,verify_package_pins,verify_copied_inputs
        from randomizer.cave_floor import WFG_POLICY
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);helper=SpeciesBankTests();helper.root=root
            banks={3:helper.bank(3),4:helper.bank(4)}
            exe=root/'source.exe';exe.write_bytes(b'policy executable');workspace=root
            def stage_policy(descriptor,assets,pod,exe,generator,out,salt,checkpoint,bank_paths):
                out.mkdir(parents=True)
                names=['p2-cave-floor.txt','p2-cave-entry.txt','p2-cave-bud-entry.txt','p2-cave-item-receipts.txt',
                       'p2-cave-items.txt','p2-cave-transition.txt','p2-cave-rooms.txt','p2-cave-gates.txt',
                       'p2-cave-barriers.txt','p2-pod.txt','p2-purple.txt','p2-white.txt']
                if descriptor['policy']==WFG_POLICY:names+=['p2-cave-route-pom.txt']
                for name in names:(out/name).write_text('policy '+name)
                (out/'cave.json').write_text(json.dumps(descriptor))
                for name in ('layout.json','render.mod','collision.json','assets/dataDir/courses/pikmin2room/room.mod',
                             'assets/dataDir/stages/chal0/default.gen'):
                    path=out/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(b'policy geometry')
                (out/'package.json').write_text('{}')
                return {'files':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.iterdir() if p.is_file()}}
            def surface_policy(assets,bundle,identity,out,exe,surface,token,**options):
                run=out/'run';run.mkdir(parents=True)
                names=['assets/dataDir/courses/p2tutorial/full.mod','assets/dataDir/courses/p2tutorial/full.water']
                for name in names:
                    path=run/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(b'policy terrain')
                self.assertEqual(options['destination'],'forest_2/f_02')
                sidecar='p2-cave-route-destination.txt'
                (run/sidecar).write_text(f'P2_CAVE_ROUTE_DESTINATION_1 {token} forest_2/f_02\n')
                return run,names+[sidecar]
            package=root/'output/package'
            with patch('scripts.stage_pikmin2_cave_route.stage',side_effect=stage_policy), \
                 patch('scripts.stage_pikmin2_cave_route.stage_surface',side_effect=surface_policy):
                spec=stage_package('1161','Player1',root,root,exe,exe,root,'c'*64,package,workspace,banks,wfg_acquisition=True)
            self.assertEqual(spec['schema'],2)
            meta,journey,spec=route_inputs(package)
            self.assertEqual([f['descriptor']['table']['floor'] for f in journey['floors']],[1,1,2])
            self.assertEqual([f['descriptor']['table']['cave_id'] for f in journey['floors']],['forest_2','forest_1','forest_1'])
            pins=capture_package_pins(package,meta,spec)
            run=root/'copied';run.mkdir();(run/'nectar.exe').write_bytes(exe.read_bytes());(run/'cave-generator.exe').write_bytes(exe.read_bytes())
            for name in pins:
                if name.startswith('floor-0/p2-') and Path(name).name not in ('p2-cave-entry.txt','p2-cave-bud-entry.txt','p2-cave-item-receipts.txt'):
                    (run/Path(name).name).write_bytes((package/name).read_bytes())
            self.assertIn('p2-cave-route-pom.txt',verify_copied_inputs(run,pins,'acquisition',0))
            (package/'floor-0/p2-cave-route-pom.txt').write_text('tampered actual body binding')
            with self.assertRaisesRegex(ValueError,'original package input changed'):verify_package_pins(package,pins)
            with patch('scripts.stage_pikmin2_cave_route.stage_wfg_journey') as stage:
                with self.assertRaisesRegex(ValueError,'both Purple and White'):
                    stage_package('1161','Player1',root,root,exe,exe,root,'c'*64,root/'output/refuse',workspace,{3:banks[3]},wfg_acquisition=True)
                stage.assert_not_called()

    def test_immutable_generator_allows_party_count_but_refuses_body_or_template_changes(self):
        import struct
        from scripts.play_pikmin2_cave_route import generator_invariants
        def record(kind,uid):
            row=bytearray(96);row[:8]=b'    0.0v';row[72:76]=kind;struct.pack_into('<I',row,8,uid)
            return row
        body=record(b'ssob',25);piki=record(b'ikip',1000)
        def blob(rows):return b'1.0v'+struct.pack('>4fI',0,0,0,0,len(rows))+b''.join(rows)
        original=blob([body,piki]);changed=bytearray(piki)
        struct.pack_into('<I',changed,8,1001);struct.pack_into('>3f',changed,48,10,0,20)
        self.assertEqual(generator_invariants(original),generator_invariants(blob([body,piki,changed])))
        bad_body=bytearray(body);bad_body[80]=99
        self.assertNotEqual(generator_invariants(original),generator_invariants(blob([bad_body,piki])))
        bad_piki=bytearray(piki);bad_piki[92]=99
        self.assertNotEqual(generator_invariants(original),generator_invariants(blob([body,bad_piki])))
        with self.assertRaises(ValueError):generator_invariants(blob([body,piki,bad_piki]))
        bad_uid=bytearray(piki);struct.pack_into('<I',bad_uid,8,999)
        with self.assertRaisesRegex(ValueError,'ID differs'):generator_invariants(blob([body,bad_uid]))

    def test_linux_staging_requires_elf_and_inspects_both_binaries_at_actual_cwd(self):
        from scripts.stage_pikmin2_playable_cave import stage
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);assets=root/'assets';(assets/'dataDir/stages/chal0').mkdir(parents=True)
            (assets/'dataDir/stages/chal0/default.gen').write_bytes(b'policy asset')
            (assets/'dataDir/stages/chal0.ini').write_bytes(b'policy stage')
            pod=root/'pod';pod.mkdir()
            for name in ('pod.mod','treasure.mod','p2-pod.txt'):(pod/name).write_bytes(b'policy')
            exe=root/'native';tool=root/'generator';exe.write_bytes(b'MZ'+bytes(1024));tool.write_bytes(b'\x7fELF'+bytes(128))
            output=root/'run'
            with patch('scripts.stage_pikmin2_playable_cave.is_windows',return_value=False), \
                 patch('scripts.stage_pikmin2_playable_cave.runtime_evidence') as evidence:
                with self.assertRaisesRegex(ValueError,'requires ELF'):stage(create('930'),assets,pod,exe,tool,output)
                evidence.assert_not_called();self.assertFalse(output.exists())
            exe.write_bytes(b'\x7fELF'+bytes(128))
            def evidence_check(binary,**kwargs):
                self.assertTrue(output.is_dir());self.assertEqual(kwargs['cwd'],output)
                self.assertIsInstance(kwargs['env'],dict)
                return {'policy_only':True,'path':str(binary)}
            with patch('scripts.stage_pikmin2_playable_cave.is_windows',return_value=False), \
                 patch('scripts.stage_pikmin2_playable_cave.runtime_evidence',side_effect=evidence_check) as evidence, \
                 patch('scripts.stage_pikmin2_playable_cave.portable_generator',side_effect=ValueError('stop before policy geometry')) as generate, \
                 patch('scripts.stage_pikmin2_playable_cave.run_native_generator') as windows:
                with self.assertRaisesRegex(ValueError,'stop before'):stage(create('930'),assets,pod,exe,tool,output)
                self.assertEqual([call.args[0] for call in evidence.call_args_list],[exe,tool])
                self.assertEqual(generate.call_args.args[3],output);windows.assert_not_called()
                self.assertTrue((output/'platform-inputs.json').is_file())

    def test_linux_generator_uses_fixed_argv_cwd_and_owned_cleanup(self):
        from scripts.stage_pikmin2_playable_cave import portable_generator
        from unittest.mock import MagicMock
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);tool=root/'generator';tool.write_bytes(b'policy');table=root/'table';table.write_text('policy')
            layout=root/'layout.json';layout.write_text(json.dumps(dict(schema='p2-cave-observed-layout/1',source='engine')))
            child=MagicMock();child.communicate.return_value=('P2_CAVE_GEN policy-only\n','');child.returncode=0
            with patch('scripts.stage_pikmin2_playable_cave.subprocess.Popen',return_value=child) as spawn, \
                 patch('scripts.stage_pikmin2_playable_cave.owned_process_options',return_value={'start_new_session':True}), \
                 patch('scripts.stage_pikmin2_playable_cave.terminate_owned_process') as retire:
                portable_generator(tool,table,layout,root,{'SAFE':'1'})
                self.assertEqual(spawn.call_args.args[0],[str(tool.resolve()),str(table.resolve()),str(layout.resolve())])
                self.assertEqual(spawn.call_args.kwargs['cwd'],root.resolve());self.assertTrue(spawn.call_args.kwargs['start_new_session'])
                retire.assert_called_once_with(child)

    def test_linux_controller_recipe_fails_closed_before_any_foreign_provider(self):
        from scripts.play_pikmin2_cave_route import require_controller_recipe,fixture_child,ROOT
        with patch('scripts.play_pikmin2_cave_route.is_windows',return_value=False):
            with self.assertRaisesRegex(RuntimeError,'pinned root'):require_controller_recipe(ROOT/'foreign')
            with self.assertRaisesRegex(RuntimeError,'not catalogued'):require_controller_recipe(ROOT)
            with self.assertRaisesRegex(RuntimeError,'not catalogued'):fixture_child(ROOT/'native',ROOT/'output/run',[],
                                                                                       'PASS',ROOT,ROOT/'output')
        with patch('scripts.play_pikmin2_cave_route.is_windows',return_value=True):require_controller_recipe(ROOT/'legacy-workspace')

    def test_dry_pads_and_actual_body_binding_do_not_force_party(self):
        import struct
        from scripts.stage_pikmin2_playable_cave import physical_layout,wfg_pom_bodies,read_species_banks
        descriptor,layout=self.fixture();rooms,tiles,water=physical_layout(layout,0,acquisition_descriptor=descriptor)
        self.assertFalse(water)
        for unit in rooms['units']:
            if unit['kind']=='bud':
                cx,cz=unit['gx']//100,unit['gz']//100
                self.assertTrue(all((cx+x,cz+z) in tiles for x in range(-5,6) for z in range(-5,6)))
        with tempfile.TemporaryDirectory() as tmp:
            helper=SpeciesBankTests();helper.root=Path(tmp)
            banks=read_species_banks({3:helper.bank(3),4:helper.bank(4)})
            # Byte policy templates only, not asserted to be renderable source assets.
            template=bytearray(96);template[72:76]=b'ssob';template[76:80]=b'\x02\x00\x00\x00'
            rows=[]
            for uid in range(1000,1020):
                row=bytearray(96);row[72:76]=b'ikip';struct.pack_into('<I',row,8,uid);rows.append(row)
            original=[bytes(row) for row in rows]
            # Exact one-generator binding required; preserve supplied bytes.
            config=banks[4]['p2-white.txt'];banks[4]['p2-white.txt']=config.replace(b'ivory_generators 2 25 4294967295',b'ivory_generators 1 25')
            with patch('scripts.stage_pikmin2_playable_cave.records',return_value=[bytes(template)]):
                text=wfg_pom_bodies(Path(tmp),rows,descriptor,rooms,banks)
            self.assertEqual([bytes(row) for row in rows[:20]],original)
            self.assertEqual(len(rows),22)
            self.assertIn('forest_2:f1:bud:0 2000 3 0 0 800 5',text)
            self.assertIn('forest_2:f1:bud:1 25 4 1600 0 800 5',text)
            self.assertEqual(struct.unpack_from('<I',rows[-1],8)[0],25)
            self.assertEqual(rows[-1][8:12],b'\x19\x00\x00\x00')
            self.assertEqual(struct.unpack_from('>I',rows[-1],80)[0],5|(1<<6))
            with patch('scripts.stage_pikmin2_playable_cave.records',return_value=[bytes(template)]):
                with self.assertRaisesRegex(ValueError,'colliding'):wfg_pom_bodies(Path(tmp),rows,descriptor,rooms,banks)
            banks[4]['p2-white.txt']=config
            with self.assertRaisesRegex(ValueError,'exactly one'):wfg_pom_bodies(Path(tmp),[],descriptor,rooms,banks)


class BoundedCaveTests(unittest.TestCase):
    def test_deterministic_standalone_contract(self):
        for seed in range(30):
            descriptor = create(str(seed))
            self.assertEqual(descriptor['table'], resolve(str(seed), 'Player1')['table'])
            self.assertEqual(descriptor, validate(json.loads(json.dumps(descriptor))))
            self.assertEqual(fingerprint(descriptor), fingerprint(create(str(seed))))
            self.assertNotEqual(fingerprint(descriptor), fingerprint(create(str(seed), 'Other')))
        self.assertEqual(create('930')['required_colors'],
                         {'treasure_water': ['blue'], 'treasure_elec': ['yellow', 'blue']})

    def test_rejects_campaign_ap_and_tampered_descriptors(self):
        for mutation in (lambda d: d.update(mode='ap'),
                         lambda d: d.update(schema=9),
                         lambda d: d['table']['buds'].clear(),
                         lambda d: d['table'].update(floor=True),
                         lambda d: d['required_colors'].clear(),
                         lambda d: d['table'].update(seed='42')):
            descriptor = create('930')
            mutation(descriptor)
            with self.assertRaises(ValueError): validate(descriptor)
        for seed, slot in ((None, 'Player1'), ('', 'Player1'), ('930', ''), (930, 'Player1')):
            with self.assertRaises(ValueError): create(seed, slot)

    def test_real_geometry_and_route_water_cut(self):
        from scripts.stage_pikmin2_playable_cave import mesh
        from experimental.pikmin2_collision import ground_height
        tiles={(x,z) for x in range(-1,9) for z in range(-1,2)}
        with tempfile.TemporaryDirectory() as tmp:
            binary,routes=mesh(tiles,{(4,0)},Path(tmp))
            room=json.loads((Path(tmp)/'collision.json').read_text())
        self.assertTrue(binary)
        self.assertIn(b'point {',routes)
        self.assertTrue(any(code>>29==5 for code in room['mapcodes']))
        self.assertEqual(ground_height(room['vertices'],room['triangles'],400,0),0)
        self.assertIsNone(ground_height(room['vertices'],room['triangles'],400,200))

    def test_fresh_staging_is_required(self):
        from scripts.stage_pikmin2_playable_cave import stage
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            with self.assertRaisesRegex(ValueError, 'fresh private'):
                stage(create('930'), directory, directory, directory, directory, directory)

    def test_layout_water_is_an_unavoidable_route_cut(self):
        from scripts.stage_pikmin2_playable_cave import physical_layout
        from experimental.pikmin2_cave_rooms import logical_projection
        previous = None
        for salt in (0, 1, 2, 100000):
            rooms, tiles, water = physical_layout(fixture_layout(), salt)
            end = max(x for x,z in tiles)-1
            # Flood-fill all dry tiles from spawn: neither water treasure nor
            # far segment/electric treasure may be reached via a side route.
            reached, todo = set(), [(0,0)]
            while todo:
                p = todo.pop()
                if p in reached or p not in tiles or p in water: continue
                reached.add(p)
                x,z = p
                todo.extend(((x-1,z),(x+1,z),(x,z-1),(x,z+1)))
            self.assertIn((-1,1), reached)  # Blue conversion available before water.
            self.assertNotIn((0,-5), reached)
            self.assertNotIn((end,0), reached)
            self.assertNotIn((end,-5), reached)
            self.assertEqual(physical_layout(fixture_layout(), salt), (rooms,tiles,water))
            projection = logical_projection(rooms)
            if previous is not None: self.assertEqual(previous,projection)
            previous = projection

    def test_barrier_sidecar_covers_corridor_and_excludes_buds(self):
        from scripts.stage_pikmin2_playable_cave import barriers_text, physical_layout
        from experimental.pikmin2_cave_gates import build_gates
        rooms, _, _ = physical_layout(fixture_layout(), 0)
        lines = barriers_text(rooms).splitlines()
        self.assertEqual(lines[:4], ['P2_CAVE_BARRIERS_1', 'cave forest_1', 'floor 1', 'seed 930'])
        rows = {words[0]: list(map(float,words[1:])) for words in map(str.split,lines[5:])}
        expected = {door['id'] for door in build_gates(rooms)['doors'] if door['carry_block'] != 'none'}
        self.assertEqual(set(rows),expected)
        self.assertEqual(lines[4], 'barriers '+str(len(expected)))
        for unit in rooms['units']:
            if unit['id'] not in rows: continue
            xmin,ymin,zmin,xmax,ymax,zmax = rows[unit['id']]
            self.assertLess(ymin,0); self.assertGreaterEqual(ymax,130)
            if unit['kind']=='choke':
                self.assertLess(zmin,-50); self.assertGreater(zmax,50)
            else:
                self.assertLess(xmin,unit['gx']-50)
                self.assertGreater(xmax,unit['gx']+50)
            self.assertLess(xmin,xmax); self.assertLess(zmin,zmax)

    def test_capacity_uses_canonical_policy(self):
        from scripts.play_pikmin2_cave import runtime_capacity
        with patch('scripts.capacity_gate.measure',return_value=object()), \
             patch('scripts.capacity_gate.admit',return_value=(False,'occupied')):
            with self.assertRaisesRegex(RuntimeError,'CAPACITY_GATE: occupied'): runtime_capacity()

    def test_receipt_and_checkpoint_recovery(self):
        from scripts.play_pikmin2_cave import checkpoint,receipts,recover_pending
        from experimental.pikmin2_cave_lane41_generator import _seed_uint64
        m=create('930')
        seed=_seed_uint64(m['table']['seed'])
        placement={'seed':seed,'items':[{'slot_id':'item:forest_1:f1:leaf:0:0',
                    'host':'forest_1:f1:leaf:0','item':'treasure_water'}]}
        ledger=f'P2_RECEIPTS_1\n{seed} treasure:forest_1:f1:item:forest_1:f1:leaf:0:0 forest_1:f1:leaf:0 cave_treasure\n'
        buds=f'P2_CAVE_BUD_STATE_1\n{seed} forest_1 1 2\nforest_1:f1:bud:0 5\nforest_1:f1:bud:1 1\n'
        transfer=f'P2_CAVE_TRANSFER_1\n{fingerprint(m)[:32]}\n1 0.5 2\n0 2\n2 1\n'
        saved=checkpoint(transfer,buds,ledger,m,placement)
        self.assertEqual(saved['squad'],[[0,2],[2,1]])
        self.assertEqual(receipts(ledger,placement),[NAMES[0]])
        with self.assertRaises(ValueError): receipts(ledger+ledger.splitlines()[1]+'\n',placement)
        with self.assertRaises(ValueError): checkpoint(transfer,buds.replace('bud:0 5','bud:0 6'),ledger,m,placement)
        for corrupt in (transfer.replace('0.5','nan'), transfer.replace('0.5','0'),
                        transfer.replace('0 2\n','4 2\n'), transfer+'0 0\n',
                        transfer.replace(fingerprint(m)[:32], '0'*32)):
            with self.assertRaises(ValueError): checkpoint(corrupt,buds,ledger,m,placement)
        for corrupt in (ledger.replace('cave_treasure','enemy'),ledger.replace(str(seed),'1'),
                        ledger.replace('leaf:0:0','leaf:999:0')):
            with self.assertRaises(ValueError): receipts(corrupt,placement)
        with tempfile.TemporaryDirectory() as tmp:
            session=Path(tmp); run=session/'runs'/'abc';run.mkdir(parents=True)
            (run/'p2-cave-transfer.txt').write_text(transfer)
            (run/'p2-cave-bud-transfer.txt').write_text(buds)
            (session/'pending.json').write_text(json.dumps({'run':str(run),'fingerprint':fingerprint(m)}))
            with self.assertRaises(RuntimeError): recover_pending(session,m,placement,ledger,[run/'nectar.exe'])
            recover_pending(session,m,placement,ledger)
            self.assertEqual(json.loads((session/'checkpoint.json').read_text()),saved)
