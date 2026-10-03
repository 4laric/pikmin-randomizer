"""Extract private retail bridge/barrel resources and their stage topology."""
from pathlib import Path
import argparse
import hashlib
import json
import struct
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from experimental.pikmin2_assets import archive_files, disc_files
from experimental.pikmin2_convert import blocks, u16, u32
from experimental.pikmin2_bridge_geometry import convert_bridge


def joint_names(model):
    joint = blocks(model)['JNT1']
    table = u32(joint, 20)
    count = u16(joint, table)
    names = []
    for i in range(count):
        start = table + u16(joint, table + 4 + 4*i + 2)
        names.append(joint[start:joint.index(0, start)].decode('shift_jis'))
    if count != u16(joint, 8):
        raise ValueError('Joint/name count mismatch')
    return names


def extract(iso, output):
    catalog = disc_files(iso)
    output.mkdir(parents=True, exist_ok=False)
    report = {'bridges': [], 'barrel': {}, 'sources': {}}
    with iso.open('rb') as disc:
        def read(member):
            offset, size = catalog[member]
            disc.seek(offset)
            data = disc.read(size)
            if len(data) != size:
                raise ValueError('Truncated disc member: ' + member)
            report['sources'][member] = {'bytes': size, 'sha256': hashlib.sha256(data).hexdigest()}
            return data
        for kind, folder, bmd in [(0,'s_bridge','s_bridge.bmd'), (1,'slope_u','slope_u.bmd'), (2,'l_bridge','l_bridge.bmd')]:
            target = output/folder
            target.mkdir()
            model = archive_files(read('user/Kando/bridge/'+folder+'/arc.szs'))[bmd]
            (target/bmd).write_bytes(model)
            names = joint_names(model)
            rooms = [n for n in names if n.startswith('room')]
            if len(rooms)%2 or sorted(rooms) != ['room%02d'%i for i in range(len(rooms))] or 'final' not in names:
                raise ValueError('Unsupported retail bridge joint topology')
            for name, data in archive_files(read('user/Kando/bridge/'+folder+'/texts.szs')).items():
                path = target/name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
            geometry = convert_bridge(model, (target/'platform.bin').read_bytes(), target/'bridge.mod')
            report['bridges'].append({'type': kind, 'stages': len(rooms)//2, 'joints': names, 'model_sha256': hashlib.sha256(model).hexdigest(), 'native_geometry': geometry, 'native_geometry_sha256': hashlib.sha256((target/'bridge.mod').read_bytes()).hexdigest()})
        for member, folder in [('user/Kando/objects/barrel/arc.szs','barrel'), ('user/Kando/objects/barrel/texts.szs','barrel')]:
            for name, data in archive_files(read(member)).items():
                target = output/folder/name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
        for member in ['user/Abe/item/bridgeParms.txt','user/Abe/item/barrelParms.txt']:
            (output/Path(member).name).write_bytes(read(member))
    (output/'source-receipt.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    return report


def bridge_manifest(inventory, output):
    rows = []
    for member in json.loads(inventory.read_text(encoding='utf-8')):
        for entry in member['records']:
            actor = entry['actor']
            if actor.get('item') != 'brdg':
                continue
            payload, eof = actor['source_payload']
            if actor['object_version'] != '0002' or payload[0] != ['brdg'] or payload[4] != ['0001'] or len(payload) != 6 or eof != [['_eof']]:
                raise ValueError('Unsupported bridge source payload: '+entry['source_key'])
            kind = int(payload[5])
            if kind not in (0,1,2):
                raise ValueError('Unsupported retail bridge type')
            if actor['reserved'] != 3 or actor['respawn_days'] != 0:
                raise ValueError('Unsupported retail bridge schedule/cache flags')
            fields = [entry['generator_uid'], entry['source_key'], member['source_sha256'], '0002', '0001', actor['reserved'], actor['respawn_days'], entry.get('day_limit',-1), kind, 3000]
            fields += actor['position'] + actor['offset'] + actor['rotation']
            rows.append(' '.join(map(str, fields)))
    output.write_text('P2_ORIGINAL_BRIDGE_1 '+str(len(rows))+'\n'+'\n'.join(rows)+'\n', encoding='ascii')


def barrel_manifest(inventory, output):
    rows=[]
    for member in json.loads(inventory.read_text(encoding='utf-8')):
        for entry in member['records']:
            actor=entry['actor']
            if actor.get('item')!='barl':continue
            payload,eof=actor['source_payload']
            if (actor['object_version']!='0002' or payload[0]!=['barl']
                or len(payload)!=5 or payload[4]!=['0000'] or eof!=[['_eof']]):
                raise ValueError('Unsupported barrel source payload: '+entry['source_key'])
            if actor['reserved']!=3 or actor['respawn_days']!=0:
                raise ValueError('Unsupported barrel source cache/schedule')
            fields=[entry['generator_uid'],entry['source_key'],member['source_sha256'],
                    '0002','0000',actor['reserved'],actor['respawn_days'],entry.get('day_limit',-1),4000]
            fields+=actor['position']+actor['offset']+actor['rotation']
            rows.append(' '.join(map(str,fields)))
    output.write_text('P2_ORIGINAL_BARREL_1 '+str(len(rows))+'\n'+'\n'.join(rows)+'\n',encoding='ascii')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iso', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--inventory', type=Path)
    args = parser.parse_args()
    report = extract(args.iso, args.output)
    if args.inventory:
        bridge_manifest(args.inventory,args.output/'bridges.txt')
        barrel_manifest(args.inventory,args.output/'barrels.txt')
    print(json.dumps(report, indent=2))
