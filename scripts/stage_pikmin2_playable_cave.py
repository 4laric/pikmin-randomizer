"""Build a bounded engineered forest_1 floor from the canonical seed contract.

Geometry is original simple mesh/collision, not a reproduction of retail rooms.
The native generator supplies the graph; layout salt changes physical spacing
only. Legal installed P1 assets and locally extracted Pod/treasure are required.
"""
import argparse
import hashlib
import json
import math
import os
import re
import shutil
import struct
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from randomizer.cave_floor import create, validate, fingerprint, WFG_POLICY
from experimental.pikmin2_collision import attach_collision, route_ini, ground_height
from experimental.pikmin2_convert import write_model
from experimental.pikmin2_cave_lane41_generator import write_native_table, run_native_generator
from experimental.pikmin2_cave_rooms import rooms_from_layout, rooms_text
from experimental.pikmin2_cave_items import items_from_layout, items_text
from experimental.pikmin2_cave_gates import build_gates, gates_text
from scripts.preview_pikmin2_room import generator, overlay, records
from scripts.fixture_platform import (is_windows, runtime_evidence, owned_process_options,
                                     terminate_owned_process)


SPECIES_NAMES = {3: 'purple', 4: 'white'}
SPECIES_MODEL_DIR = 'assets/dataDir/courses/pikmin2room'


def species_bank_files(species, directory, *, surface=False):
    """Read an explicit local bank; derive its exact model inventory from native config.

    Bytes are retained verbatim. Surface impact auxiliaries are deliberately not
    admitted: red_earthquake_v1 needs a separately reviewed auxiliary bank.
    """
    if type(species) is not int or species not in SPECIES_NAMES:
        raise ValueError('unsupported species bank')
    directory = Path(directory).resolve()
    name = SPECIES_NAMES[species]; config = f'p2-{name}.txt'
    try:
        data = (directory/config).read_bytes(); words = data.decode('utf-8').split()
        cursor = 0
        def take():
            nonlocal cursor
            if cursor == len(words): raise ValueError('incomplete species config')
            value = words[cursor]; cursor += 1; return value
        def expect(value):
            if take() != value: raise ValueError('unexpected species config field: '+value)
        def integer():
            value = take()
            if not re.fullmatch(r'[0-9]+', value): raise ValueError('invalid species config integer')
            return int(value)
        def number():
            value = take()
            if not re.fullmatch(r'[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?', value):
                raise ValueError('invalid species config number')
            value = float(value)
            if not math.isfinite(value): raise ValueError('nonfinite species config')
            # Native config extraction targets float, not Python double. Apply
            # the same precision before bounds/positive-duration checks while
            # retaining the original config bytes for the eventual copy.
            try: value = struct.unpack('f',struct.pack('f',value))[0]
            except (OverflowError,struct.error) as error:
                raise ValueError('species config overflows native float32') from error
            if not math.isfinite(value): raise ValueError('nonfinite native float32 config')
            return value
        expect(f'P2_{name.upper()}_1'); expect('stats')
        stats = [number() for _ in range(9)]
        if species == 3:
            valid = all(0 <= value <= 1000 for value in stats)
        else:
            bounds = [(1,3),(1,30),(0,2),(0,5),(0,2),(0,2),(0,2),(0,2),(0,500)]
            valid = all(lo <= value <= hi for value,(lo,hi) in zip(stats,bounds)) and stats[2] > 0 and stats[8] > 0
        if not valid: raise ValueError('species stats outside native bounds')
        if species == 4:
            expect('ivory_generators'); count = integer()
            if not 1 <= count <= 32: raise ValueError('invalid Ivory generator count')
            ids = [integer() for _ in range(count)]
            if len(set(ids)) != count or any(i > 0xffffffff for i in ids):
                raise ValueError('invalid or duplicate Ivory generator IDs')
        clips = {}
        for motion in ('wait','walk','attack1'):
            expect(motion); count = integer(); seconds = number()
            if not 1 <= count <= 32 or seconds <= 0: raise ValueError('invalid species clip')
            clips[motion] = count
        expected = {(motion,i) for motion,count in clips.items() for i in range(count)}
        seen = set(); impact = False
        while cursor < len(words):
            field = take()
            if field == 'impact' and species == 3:
                if impact: raise ValueError('duplicate Purple impact config')
                expect('red_earthquake_v1'); impact = True
                continue
            if field != 'happa': raise ValueError('unknown species config field')
            attachment = (take(),integer())
            if attachment not in expected or attachment in seen: raise ValueError('invalid or duplicate happa attachment')
            seen.add(attachment)
            for _ in range(12): number()
        if seen != expected: raise ValueError('incomplete happa attachments')
        if surface and impact:
            raise ValueError('unsupported surface auxiliary bank: Purple impact red_earthquake_v1')
        names = [f'{name}_{motion}_{i:02d}.mod' for motion,count in clips.items() for i in range(count)]
        names += [f'{name}_happa_{i}.mod' for i in range(3)]
        result = {config: data}
        for model in names:
            path = directory/model
            if not path.resolve().is_relative_to(directory): raise ValueError('species model escapes bank')
            blob = path.read_bytes()
            if not blob: raise ValueError('empty species model: '+model)
            result[model] = blob
        if not (directory/config).resolve().is_relative_to(directory): raise ValueError('species config escapes bank')
        return result
    except (OSError, UnicodeError) as error:
        raise ValueError('missing or unreadable species bank: '+str(directory)) from error


def read_species_banks(species_banks=None, *, surface=False):
    if species_banks is None: return {}
    if type(species_banks) is not dict: raise ValueError('species_banks must map 3/4 to local directories')
    return {species: species_bank_files(species,path,surface=surface) for species,path in species_banks.items()}


def install_species_banks(run, banks):
    """Install validated byte banks without writing through shared asset links."""
    if not banks: return []
    run = Path(run).resolve(); target = run/SPECIES_MODEL_DIR
    if not target.parent.resolve().is_relative_to(run): raise ValueError('species parent is not private')
    model_bytes = {name:data for files in banks.values() for name,data in files.items() if name.endswith('.mod')}
    if target.is_junction() or target.is_symlink():
        source = target.resolve(); temporary = target.with_name('pikmin2room-species-private')
        overlay(source,temporary,model_bytes)
        if target.is_junction(): os.rmdir(target)  # remove this private junction, never its target
        else: target.unlink()
        temporary.rename(target)
    else:
        if not target.resolve().is_relative_to(run): raise ValueError('species models are not private')
        target.mkdir(parents=True,exist_ok=True)
        for name,data in model_bytes.items():
            path=target/name
            # Existing overlay files may be hardlinks; replacement must not edit their source.
            if path.exists() or path.is_symlink(): path.unlink()
            path.write_bytes(data)
    files=[]
    for bank in banks.values():
        for name,data in bank.items():
            relative=f'{SPECIES_MODEL_DIR}/{name}' if name.endswith('.mod') else name
            if not name.endswith('.mod'):
                path=run/name
                if path.exists() or path.is_symlink(): path.unlink()
                path.write_bytes(data)
            files.append(relative)
    return sorted(files)


def pin_species_banks(package,species_banks=None):
    banks=read_species_banks(species_banks)
    record={}
    for species,files in sorted(banks.items()):
        relative=f'species-banks/{SPECIES_NAMES[species]}'
        directory=Path(package)/relative; directory.mkdir(parents=True,exist_ok=False)
        for name,data in files.items(): (directory/name).write_bytes(data)
        record[str(species)]=dict(directory=relative,files={name:hashlib.sha256(data).hexdigest() for name,data in sorted(files.items())})
    return record


def verify_species_banks(package,record):
    package=Path(package).resolve()
    if type(record) is not dict or any(k not in ('3','4') for k in record): raise ValueError('invalid package species banks')
    result={}
    for key,item in record.items():
        if type(item) is not dict or set(item)!={'directory','files'}: raise ValueError('invalid package bank record')
        expected=f'species-banks/{SPECIES_NAMES[int(key)]}'
        if item['directory']!=expected: raise ValueError('foreign package bank path')
        directory=(package/expected).resolve()
        if not directory.is_relative_to(package): raise ValueError('package bank escapes package')
        files=species_bank_files(int(key),directory)
        hashes={name:hashlib.sha256(data).hexdigest() for name,data in files.items()}
        if hashes!=item['files'] or set(p.name for p in directory.iterdir())!=set(files):
            raise ValueError('package species bank changed')
        result[int(key)]=directory
    return result


def seal_surface_species(run,token,route_identity,files,species):
    """Bind private bank bytes to the actual versioned surface config and identity."""
    if (not re.fullmatch('[0-9a-f]{32}',token) or type(route_identity) is not dict
            or set(route_identity)!={'seed','slot_hash','receipt_identity'}
            or type(route_identity['seed']) is not int or not 0<=route_identity['seed']<2**64
            or any(not isinstance(route_identity[k],str) or not re.fullmatch('[0-9a-f]{64}',route_identity[k])
                   for k in ('slot_hash','receipt_identity'))):
        raise ValueError('invalid package-derived species route identity')
    if not species or sorted(set(species))!=species or any(type(s) is not int or s not in SPECIES_NAMES for s in species):
        raise ValueError('invalid surface activation species')
    run=Path(run).resolve();config=run/'p2-cave-route-surface.txt'
    words=config.read_text().split()
    if len(words)<8 or words[:2]!=['P2_CAVE_ROUTE_SURFACE_2',token]:
        raise ValueError('surface species activation requires matching version2 config')
    from randomizer.cave_route import surface_transfer
    party=surface_transfer('P2_CAVE_ROUTE_TRANSFER_2 '+token+' '+' '.join(words[2:5]+words[6:]),token)
    if sorted({s for s,m in party['squad'] if s>2})!=species: raise ValueError('surface activation differs from actual party')
    identity=f"{route_identity['seed']} {route_identity['slot_hash']} {route_identity['receipt_identity']}"
    identity_path=run/'p2-cave-route-identity.txt'
    identity_path.write_text(f'P2_CAVE_ROUTE_IDENTITY_1 {identity} forest_1 tutorial\n',encoding='ascii')
    paths=sorted(set(files+['p2-cave-route-identity.txt']))
    hashes={}
    for name in paths:
        path=(run/name).resolve()
        if not path.is_relative_to(run) or not path.is_file(): raise ValueError('foreign activation file')
        hashes[name]=hashlib.sha256(path.read_bytes()).hexdigest()
    text=(f'P2_CAVE_ROUTE_SPECIES_1\nroute tutorial forest_1 {token} 2 {hashlib.sha256(config.read_bytes()).hexdigest()}\n'
          f'identity {identity}\nspecies {len(species)} '+ ' '.join(map(str,species))+f'\nfiles {len(paths)}\n'
          +''.join(f'{name} {digest}\n' for name,digest in hashes.items()))
    (run/'p2-cave-route-species.txt').write_text(text,encoding='ascii')
    return paths+['p2-cave-route-species.txt']


def physical_layout(layout, salt, *, acquisition_descriptor=None):
    if type(salt) is not int or not 0 <= salt <= 100000:
        raise ValueError('invalid layout salt')
    rooms = rooms_from_layout(layout, salt=salt,acquisition_descriptor=acquisition_descriptor)
    if acquisition_descriptor is not None:
        end=16+salt%3*2
        for unit in rooms['units']:
            unit['gx']=(0 if unit['segment_index']==0 else end)*100
            unit['gz']=800 if unit['kind']=='bud' else 0
        rooms['origin']=[0,0];rooms['cell']=100
        # 110 horizontal / 750 vertical source launch returns to level ground
        # after ~1.53s at gravity980: ~169 units. Each pad provides550 units
        # to its nearest edge; body/throw/landing acceptance is still UNTESTED.
        tiles={(x,z) for x in range(-2,end+3) for z in range(-2,3)}
        tiles.update((x,z) for cx in (0,end) for x in range(cx-5,cx+6) for z in range(3,14))
        return rooms,tiles,set()
    # A straight trunk with two single-door alcoves; no alternate route around
    # either hazard. Blue is before water; Yellow is beyond it, before electricity.
    end = 8 + salt % 3 * 2
    points = {}
    for unit in rooms['units']:
        kind, seg = unit['kind'], unit['segment_index']
        if kind == 'segment': pos = (0 if seg == 0 else end, 0)
        elif kind == 'choke': pos = (end // 2, 0)
        elif kind == 'bud': pos = (-1 if unit['hazard'] == 'water' else end+1, 1)
        elif kind in ('leaf', 'gate'): pos = (0 if seg == 0 else end, -5)
        elif kind == 'hole': pos = (end, 1)
        else: raise ValueError('unsupported native node ' + kind)
        unit['gx'], unit['gz'] = pos[0] * 100, pos[1] * 100
        points[unit['id']] = pos
    rooms['origin'] = [0, 0]
    rooms['cell'] = 100
    tiles = {(x,z) for cx in (0,end) for x in range(cx-1,cx+2) for z in range(-1,2)}
    tiles.update((x,0) for x in range(2,end-1))
    tiles.update((x,z) for x in (0,end) for z in range(-5,-1))
    water = {(end//2,0),(0,-3),(0,-4),(0,-5)}
    return rooms, tiles, water


def barriers_text(rooms):
    """Cover complete 100-wide passages, including wall overlap, by identity."""
    plan = build_gates(rooms)
    units = {unit['id']: unit for unit in rooms['units']}
    rows = []
    for door in plan['doors']:
        if door['carry_block'] == 'none':
            continue
        unit = units[door['id']]
        x, z = unit['gx'], unit['gz']
        if unit['kind'] == 'choke':
            bounds = (x-50, -20, -60, x+50, 130, 60)
        elif door['carry_block'] == 'water':
            bounds = (x-60, -20, -560, x+60, 130, -240)
        else:
            bounds = (x-60, -20, -460, x+60, 130, -440)
        rows.append(door['id'] + ' ' + ' '.join(map(str, bounds)))
    return (f"P2_CAVE_BARRIERS_1\ncave {rooms['cave']}\nfloor {rooms['floor']}\n"
            f"seed {rooms['seed']}\nbarriers {len(rows)}\n" + '\n'.join(rows) + '\n')


def mesh(tiles, water, output, *, flower_markers=True):
    vertices, triangles, codes, colors = [], [], [], []
    def quad(corners, code, color):
        first = len(vertices)
        vertices.extend(corners)
        triangles.extend([[first,first+1,first+2],[first,first+2,first+3]])
        codes.extend([code,code]); colors.extend([color,color])
    for x,z in sorted(tiles):
        a,b,c,d = x*100-50,x*100+50,z*100-50,z*100+50
        wet = (x,z) in water
        quad([[a,0,c],[b,0,c],[b,0,d],[a,0,d]], 5<<29 if wet else 0,
             (45,145,205,255) if wet else (130,112,79,255))
        for neighbour,edge in (((x,z-1),((a,c),(b,c))),((x+1,z),((b,c),(b,d))),
                               ((x,z+1),((b,d),(a,d))),((x-1,z),((a,d),(a,c)))):
            if neighbour not in tiles:
                (ax,az),(bx,bz)=edge
                quad([[ax,0,az],[ax,130,az],[bx,130,bz],[bx,0,bz]],0,(77,65,51,255))
    # Visible flower disks match the actual conversion-volume centers.
    for x,color in (((-100,(70,125,255,255)),((max(x for x,z in tiles))*100,(255,220,35,255))) if flower_markers else ()):
        quad([[x-32,2,68],[x+32,2,68],[x+32,2,132],[x-32,2,132]],0,color)
    unique={}; welded=[]; indices=[]
    for vertex in vertices:
        key=tuple(vertex)
        if key not in unique: unique[key]=len(welded); welded.append(vertex)
        indices.append(unique[key])
    triangles=[[indices[v] for v in tri] for tri in triangles]
    vertices=welded
    ids={p:i for i,p in enumerate(sorted(tiles))}
    routes=[dict(id=i,position=[x*100,0,z*100],radius=35,
                 links=[ids[q] for q in ((x-1,z),(x+1,z),(x,z-1),(x,z+1)) if q in ids])
            for (x,z),i in ids.items()]
    room=dict(vertices=vertices,triangles=triangles,mapcodes=codes,routes=routes)
    tex=bytes(32)
    shapes=[[[{9:v,10:0} for v in t]] for t in triangles]
    decoded=({'TEX1':tex,'_render_states':[(0x101,1,0x700007,0x303,0)]*len(shapes),
              '_draw_order':list(range(len(shapes)))},
             {9:vertices.copy(),10:[(0,1,0)]},shapes,[-1]*len(shapes))
    render=output/'render.mod'
    write_model(decoded,render,'original bounded cave geometry',material_colors=colors)
    data=attach_collision(render.read_bytes(),room,mapcode_translator=lambda c:c)
    (output/'collision.json').write_text(json.dumps(room))
    if any(ground_height(vertices,triangles,x*100,z*100) is None for x,z in tiles):
        raise ValueError('missing walkable tile')
    return data,route_ini(routes).encode()


def wfg_pom_bodies(assets, rows, manifest, rooms, banks):
    """Append actual legacy Pom generator bodies, bound to canonical PW slots."""
    validate(manifest)
    if manifest['policy']!=WFG_POLICY or set(banks)!={3,4}:
        raise ValueError('WFG acquisition requires exact Purple/White banks')
    words=banks[4]['p2-white.txt'].decode('utf8').split()
    at=words.index('ivory_generators')
    if words[at+1]!='1':raise ValueError('WFG bank must bind exactly one Ivory generator')
    ivory=int(words[at+2])
    # Stream::readInt swaps BE, then Generator::readID swaps again on PC.
    # Generator identity bytes are therefore LE; body numeric fields remain BE.
    used={struct.unpack_from('<I',row,8)[0] for row in rows}
    if len(used)!=len(rows) or ivory in used:raise ValueError('duplicate or colliding WFG generator ID')
    used.add(ivory);violet=2000
    while violet in used:violet+=1
    templates=[r for r in records(assets/'dataDir/stages/chal0/default.gen')
               if r[72:76]==b'ssob' and r[76:80]==b'\x02\x00\x00\x00']
    if not templates:raise ValueError('missing actual Pom body template')
    units={u['id']:u for u in rooms['units']}
    lines=['P2_CAVE_ROUTE_POM_1','profile '+WFG_POLICY,
           f"seed {rooms['seed']} cave forest_2 floor 1 token {fingerprint(manifest)[:32]}",'buds 2']
    for bud,uid,species in zip(manifest['table']['buds'],(violet,ivory),(3,4)):
        unit=units[bud['slot_id']];x,z=unit['gx'],unit['gz'];y=0
        row=bytearray(templates[0]);struct.pack_into('<I',row,8,uid)
        row[16:48]=('WFG '+bud['species']+' bud').encode('ascii').ljust(32,b'\0')
        struct.pack_into('>6f',row,48,x,y,z,0,0,0)
        struct.pack_into('>I',row,80,5|(1<<6))
        rows.append(row)
        lines.append(f"{bud['slot_id']} {uid} {species} {x} {y} {z} 5")
    return '\n'.join(lines)+'\n'


def portable_generator(tool,table,layout_out,directory,env):
    """The Linux generator uses its actual private staging cwd and owned group."""
    argv=[str(Path(tool).resolve(strict=True)),str(Path(table).resolve(strict=True)),str(Path(layout_out).resolve())]
    proc=subprocess.Popen(argv,cwd=Path(directory).resolve(strict=True),env=env,
                          stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,**owned_process_options())
    try:
        stdout,stderr=proc.communicate(timeout=60)
        if proc.returncode:raise ValueError(f'native generator failed (rc={proc.returncode}): {stderr.strip()}')
    finally:terminate_owned_process(proc)
    marker=next((line for line in stdout.splitlines() if line.startswith('P2_CAVE_GEN')),'')
    if not marker:raise ValueError('native generator emitted no P2_CAVE_GEN marker')
    layout=json.loads(Path(layout_out).read_text(encoding='utf8'))
    if layout.get('schema')!='p2-cave-observed-layout/1' or layout.get('source')!='engine':
        raise ValueError('native generator returned unsupported layout provenance')
    return dict(marker=marker,layout=layout)


def stage(manifest, assets, pod, exe, generator_exe, output, salt=0, checkpoint=None, species_banks=None):
    validate(manifest)
    acquisition=manifest['policy']==WFG_POLICY
    banks=read_species_banks(species_banks,surface=acquisition)
    if checkpoint and any(s>2 and s not in banks for s,m in checkpoint['squad']):
        raise ValueError('missing bank for actual cave checkpoint species')
    if acquisition and set(banks)!={3,4}:raise ValueError('WFG acquisition requires exact Purple/White banks')
    if output.exists(): raise ValueError('use a fresh private output directory')
    for p in (assets/'dataDir/stages/chal0/default.gen',assets/'dataDir/stages/chal0.ini',
              pod/'pod.mod',pod/'treasure.mod',pod/'p2-pod.txt',exe,generator_exe):
        if not p.is_file(): raise ValueError('missing input: '+str(p))
    for binary in (exe,generator_exe):
        with binary.open('rb') as stream:
            if is_windows():
                if stream.read(2)!=b'MZ' or binary.stat().st_size<1024:
                    raise ValueError('executable is incomplete; wait for its build: '+str(binary))
            elif stream.read(4)!=b'\x7fELF':raise ValueError('Linux staging requires ELF binaries: '+str(binary))
    output.mkdir(parents=True)
    env=dict(os.environ)
    if not is_windows():
        evidence={name:runtime_evidence(binary,env=env,cwd=output)
                  for name,binary in (('native',exe),('generator',generator_exe))}
        (output/'platform-inputs.json').write_text(json.dumps(evidence,indent=2)+'\n')
    table=manifest['table']
    floor=table['floor']
    write_native_table(table,output/'p2-cave-floor.txt')
    layout=(run_native_generator(generator_exe,output/'p2-cave-floor.txt',output/'layout.json') if is_windows()
            else portable_generator(generator_exe,output/'p2-cave-floor.txt',output/'layout.json',output,env))['layout']
    rooms,tiles,water=physical_layout(layout,salt,acquisition_descriptor=manifest if acquisition else None)
    items=(dict(schema='p2-cave-items/1',source=layout['source'],geometry='proxy',cave='forest_2',
                floor=1,seed=layout['seed'],items=[]) if acquisition else items_from_layout(layout))
    (output/'p2-cave-rooms.txt').write_text(rooms_text(rooms))
    (output/'p2-cave-items.txt').write_text(items_text(items))
    (output/'p2-cave-gates.txt').write_text(gates_text(build_gates(rooms)))
    (output/'p2-cave-barriers.txt').write_text(barriers_text(rooms))
    model,routes=mesh(tiles,water,output,flower_markers=not acquisition)
    stage_ini=(assets/'dataDir/stages/chal0.ini').read_bytes()
    stage_ini=re.sub(rb'(?m)^map_file[^\r\n]*',b'map_file courses/pikmin2room/room.mod',stage_ini)
    stage_ini=re.sub(rb'(?m)^navi_start[^\r\n]*',b'navi_start -50.0 0.0',stage_ini)
    blob=generator(assets)
    starts=[m.start() for m in re.finditer(b'    0.0v',blob)]+[len(blob)]
    squad=checkpoint['squad'] if checkpoint else [[1,0]]*20
    rows=[]; piki_template=None
    for a,b in zip(starts,starts[1:]):
        row=bytearray(blob[a:b]); label=row[16:48].rstrip(b'\0')
        if row[72:76]==b'ikip': piki_template=row; continue
        if label==b'preview dwarf bulborb': continue
        if label==b'preview red onion': xyz=(0,0,0)
        elif label==b'preview ship': xyz=(-80,0,-80)
        else: xyz=(-80,0,0)  # the required preview template remains labelled scaffold cargo
        struct.pack_into('>3f',row,48,*xyz); rows.append(row)
    for i in range(len(squad)):
        if piki_template is None: raise ValueError('current overlay has no starting Pikmin template')
        row=bytearray(piki_template); struct.pack_into('<I',row,8,1000+i)
        struct.pack_into('>3f',row,48,-40+(i%5)*12,0,10+(i//5)*12); rows.append(row)
    if acquisition:
        (output/'p2-cave-route-pom.txt').write_text(wfg_pom_bodies(assets,rows,manifest,rooms,banks),encoding='ascii')
    actors=blob[:20]+struct.pack('>I',len(rows))+b''.join(rows)
    overrides={'dataDir/stages/chal0.ini':stage_ini,'dataDir/stages/chal0/default.gen':actors,
               'dataDir/courses/pikmin2room/room.mod':model,'dataDir/courses/pikmin2room/room.ini':routes,
               'dataDir/courses/pikmin2room/pod.mod':(pod/'pod.mod').read_bytes(),
               'dataDir/courses/pikmin2room/treasure.mod':(pod/'treasure.mod').read_bytes()}
    empty=blob[:20]+struct.pack('>I',0)
    for p in (assets/'dataDir/stages/chal0').glob('*.gen'):
        overrides.setdefault('dataDir/stages/chal0/'+p.name,empty)
    overlay(assets,output/'assets',overrides)
    install_species_banks(output,banks)
    (output/'p2-pod.txt').write_bytes((pod/'p2-pod.txt').read_bytes())
    token=fingerprint(manifest)[:32]
    health=checkpoint['health'] if checkpoint else 1
    from randomizer.cave_checkpoint import entry_text
    party=dict(checkpoint or {},health=health,squad=squad)
    if acquisition:party['wire_schema']=2
    (output/'p2-cave-entry.txt').write_text(entry_text(token,floor,party))
    end=(16 if acquisition else 8)+salt%3*2
    kind='geyser' if floor==2 else 'hole'
    (output/'p2-cave-transition.txt').write_text(f'P2_CAVE_TRANSITION_1 {kind} {end*100} 0 100 40\n')
    if checkpoint:
        (output/'p2-cave-item-receipts.txt').write_text(checkpoint['receipts'])
        (output/'p2-cave-bud-entry.txt').write_text(checkpoint['buds'])
    (output/'cave.json').write_text(json.dumps(manifest,indent=2)+'\n')
    shutil.copy2(exe,output/'nectar.exe')
    shutil.copy2(generator_exe,output/'cave-generator.exe')
    for dll in exe.parent.glob('*.dll'): shutil.copy2(dll,output/dll.name)
    package=dict(schema=2,policy='forest1-bounded-developer-package-v2',fingerprint=fingerprint(manifest),salt=salt,
                 assets=str(assets.resolve()),pod=str(pod.resolve()),
                 native_runtime_acceptance='UNTESTED',geometry='original engineered tiles, native collision and water attributes',
                 limitations=['Not retail forest_1 geometry or full campaign.',
                              'No campaign rewards, campaign save integration, AP locations or network transport.',
                              'The template cargo beside the Pod is scaffolding, not one of the two cave treasures.',
                              'Bud graphics are colored floor markers; conversion currently uses automatic ordinary pluck.',
                              'Natural Blue/Yellow carry, gate traversal and exit/restart require runtime validation.'])
    if acquisition:
        package.update(policy='wfg-pw-acquisition-package-v1',source_course='forest_2/f_02',
            geometry='original dry engineering mesh; not retail White Flower Garden rooms',
            limitations=['Actual Pom bodies and source PW conversion require native runtime validation.',
                         'Ordinary throw, contact, sprout landing and SDL pluck are UNTESTED.',
                         'No forced PW starting party, stock grants, AP or campaign save integration.'])
    launcher=Path(__file__).with_name('play_pikmin2_cave.py').resolve()
    (output/'Play.cmd').write_text('@echo off\r\npy -3.12 "'+str(launcher)+'" "'+str(output.resolve())+'"\r\npause\r\n')
    package['files']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in output.iterdir() if p.is_file()}
    (output/'package.json').write_text(json.dumps(package,indent=2)+'\n')
    return package


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('assets','pod','exe','generator','output'): p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--seed',default='930'); p.add_argument('--salt',type=int,default=0)
    p.add_argument('--slot',default='Player1')
    a=p.parse_args(); m=create(a.seed,a.slot)
    print(json.dumps(stage(m,a.assets,a.pod,a.exe,a.generator,a.output,a.salt),indent=2))


if __name__=='__main__': main()
