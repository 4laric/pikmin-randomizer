"""Build a bounded engineered forest_1 floor from the canonical seed contract.

Geometry is original simple mesh/collision, not a reproduction of retail rooms.
The native generator supplies the graph; layout salt changes physical spacing
only. Legal installed P1 assets and locally extracted Pod/treasure are required.
"""
import argparse
import hashlib
import json
import re
import shutil
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from randomizer.cave_floor import create, validate, fingerprint
from experimental.pikmin2_collision import attach_collision, route_ini, ground_height
from experimental.pikmin2_convert import write_model
from experimental.pikmin2_cave_lane41_generator import write_native_table, run_native_generator
from experimental.pikmin2_cave_rooms import rooms_from_layout, rooms_text
from experimental.pikmin2_cave_items import items_from_layout, items_text
from experimental.pikmin2_cave_gates import build_gates, gates_text
from scripts.preview_pikmin2_room import generator, overlay


def physical_layout(layout, salt):
    if type(salt) is not int or not 0 <= salt <= 100000:
        raise ValueError('invalid layout salt')
    rooms = rooms_from_layout(layout, salt=salt)
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


def mesh(tiles, water, output):
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
    for x,color in ((-100,(70,125,255,255)),((max(x for x,z in tiles))*100,(255,220,35,255))):
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


def stage(manifest, assets, pod, exe, generator_exe, output, salt=0, checkpoint=None):
    validate(manifest)
    if output.exists(): raise ValueError('use a fresh private output directory')
    for p in (assets/'dataDir/stages/chal0/default.gen',assets/'dataDir/stages/chal0.ini',
              pod/'pod.mod',pod/'treasure.mod',pod/'p2-pod.txt',exe,generator_exe):
        if not p.is_file(): raise ValueError('missing input: '+str(p))
    for binary in (exe,generator_exe):
        with binary.open('rb') as stream:
            if stream.read(2)!=b'MZ' or binary.stat().st_size<1024:
                raise ValueError('executable is incomplete; wait for its build: '+str(binary))
    output.mkdir(parents=True)
    table=manifest['table']
    write_native_table(table,output/'p2-cave-floor.txt')
    layout=run_native_generator(generator_exe,output/'p2-cave-floor.txt',output/'layout.json')['layout']
    rooms,tiles,water=physical_layout(layout,salt)
    items=items_from_layout(layout)
    (output/'p2-cave-rooms.txt').write_text(rooms_text(rooms))
    (output/'p2-cave-items.txt').write_text(items_text(items))
    (output/'p2-cave-gates.txt').write_text(gates_text(build_gates(rooms)))
    (output/'p2-cave-barriers.txt').write_text(barriers_text(rooms))
    model,routes=mesh(tiles,water,output)
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
    actors=blob[:20]+struct.pack('>I',len(rows))+b''.join(rows)
    overrides={'dataDir/stages/chal0.ini':stage_ini,'dataDir/stages/chal0/default.gen':actors,
               'dataDir/courses/pikmin2room/room.mod':model,'dataDir/courses/pikmin2room/room.ini':routes,
               'dataDir/courses/pikmin2room/pod.mod':(pod/'pod.mod').read_bytes(),
               'dataDir/courses/pikmin2room/treasure.mod':(pod/'treasure.mod').read_bytes()}
    empty=blob[:20]+struct.pack('>I',0)
    for p in (assets/'dataDir/stages/chal0').glob('*.gen'):
        overrides.setdefault('dataDir/stages/chal0/'+p.name,empty)
    overlay(assets,output/'assets',overrides)
    (output/'p2-pod.txt').write_bytes((pod/'p2-pod.txt').read_bytes())
    token=fingerprint(manifest)[:32]
    health=checkpoint['health'] if checkpoint else 1
    (output/'p2-cave-entry.txt').write_text(f'P2_CAVE_ENTRY_1 {token} 1 {health} {len(squad)}\n'+''.join(f'{s} {m}\n' for s,m in squad))
    end=8+salt%3*2
    (output/'p2-cave-transition.txt').write_text(f'P2_CAVE_TRANSITION_1 hole {end*100} 0 100 40\n')
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
