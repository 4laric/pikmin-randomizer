"""Extract a source-backed White Pikmin sampled pose bank for a private preview."""
import argparse
import hashlib
import json
import math
import re
import struct
from pathlib import Path

from experimental.pikmin2_assets import disc_files, archive_files
from experimental.pikmin2_convert import blocks, convert, decode, write_model
from experimental.pikmin2_purple import bca_pose
from experimental.pikmin2_rigid import joint_matrices
from experimental.pikmin2_skinning import draw_matrices


def extract(iso, output, ivory_generators):
    if not ivory_generators or len(set(ivory_generators)) != len(ivory_generators):
        raise ValueError('Ivory generator IDs must be nonempty and unique')
    if any(type(value) is not int or not 0 <= value <= 0xffffffff for value in ivory_generators):
        raise ValueError('Invalid Ivory generator ID')
    output.mkdir(parents=True, exist_ok=False)
    catalog = disc_files(iso); archive_key = 'user/Kando/piki/pikis.szs'
    with iso.open('rb') as source:
        offset, size = catalog[archive_key];source.seek(offset);archive_data = source.read(size)
        parm_key = 'user/Abe/piki/pikiParms.txt';offset, size = catalog[parm_key]
        source.seek(offset);parm_data = source.read(size)
    text = parm_data.decode('shift_jis')
    def value(key):
        found = re.findall(r'\{'+key+r'\}\s+4\s+(\S+)', text)
        if len(found) != 1 or not math.isfinite(float(found[0])): raise ValueError('Missing or ambiguous source parameter')
        return float(found[0])
    stats = [value(key) for key in ('P001','P004','p008','P006','P020','P021','P018','P019','p001')]
    archive = archive_files(archive_data)
    model = output/'white.bmd';model.write_bytes(archive['piki_model/piki_p2_white.bmd'])
    skeleton = blocks(model.read_bytes());joints = struct.unpack_from('>H', skeleton['JNT1'], 8)[0]
    rows = ['P2_WHITE_1', 'stats '+' '.join(map(str,stats)),
            'ivory_generators '+str(len(ivory_generators))+' '+' '.join(map(str,ivory_generators))]
    report = {}
    for name in ('wait','walk','attack1'):
        clip = archive['motion/'+name+'.bca'];duration,_ = bca_pose(clip,0,joints)
        frames=min(12,duration);rows.append(f'{name} {frames} {duration/30:.6f}')
        for index in range(frames):
            _,pose=bca_pose(clip,index*duration//frames,joints)
            target=output/f'white_{name}_{index:02}.mod'
            matrices=draw_matrices(skeleton,pose)
            conversion=write_model(decode(model.read_bytes(),True,bake_rigid=True,draw_matrices=matrices),target,str(model))
            conversion.update(rigid_bind_pose_baked=True,weighted_pose_baked=True)
            target.with_suffix('.json').write_text(json.dumps(conversion,indent=2))
        report[name]={'source_frames':duration,'sampled_poses':frames,'sha256':hashlib.sha256(clip).hexdigest()}
    for growth,name in enumerate(('leaf','bud_red','flower_red')):
        attachment=output/(name+'.bmd');attachment.write_bytes(archive['happa_model/'+name+'.bmd'])
        convert(attachment,output/f'white_happa_{growth}.mod',True,bake_rigid=True)
    for name, details in report.items():
        clip=archive['motion/'+name+'.bca']
        for index in range(details['sampled_poses']):
            _,pose=bca_pose(clip,index*details['source_frames']//details['sampled_poses'],joints)
            matrix=joint_matrices(skeleton,pose)[8]
            rows.append('happa '+name+' '+str(index)+' '+' '.join(str(v) for row in matrix for v in row))
    (output/'p2-white.txt').write_text('\n'.join(rows)+'\n')
    result={'schema':1,'source_revision':'632af93787b9c95b63f0c13be32b161375ce3a96',
            'source_sha256':{archive_key:hashlib.sha256(archive_data).hexdigest(),parm_key:hashlib.sha256(parm_data).hexdigest()},
            'source_stats':dict(zip(('movement','attack','scale','carry_power','bud_bonus','flower_bonus','carry_max_factor','carry_min_factor','base_run_speed'),stats)),
            'ivory_generators':ivory_generators,'joints':joints,'motions':report,
            'limitations':['Sampled immutable pose bank; unsupported actions use the nearest wait/walk/attack pose.',
                           'Retail p008 is extracted but unused by the audited game code; the authored model stays at scale 1.0.',
                           'Movement uses the extracted White multiplier on the inherited P1 maturity formula; doped/source-complete speed remains pending.',
                           'Generator IDs bind Ivory conversion only inside the disposable preview.']}
    (output/'white.json').write_text(json.dumps(result,indent=2));return result


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--iso',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True);parser.add_argument('--ivory-generator',type=int,action='append',required=True)
    args=parser.parse_args();print(json.dumps(extract(args.iso,args.output,args.ivory_generator),indent=2))
