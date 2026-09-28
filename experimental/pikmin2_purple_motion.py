"""Extract the retail Purple throw/fall pose bank used by the native preview."""
import argparse,hashlib,json,struct
from pathlib import Path
from experimental.pikmin2_assets import disc_files,archive_files
from experimental.pikmin2_convert import blocks,convert,u16,u32
from experimental.pikmin2_purple import bca_pose
from experimental.pikmin2_rigid import joint_matrices

CLIPS=(('rolljmp',14),('fall',20))
PHASE_CLIPS={'Ascent':'rolljmp','EntryPause':'rolljmp','Descent':'fall','Recovery':'fall'}

def sha(data): return hashlib.sha256(data).hexdigest()

def validate_profile(text):
    lines=text.splitlines()
    if len(lines)<3 or lines[0]!='P2_PURPLE_MOTION_1':raise ValueError('Invalid motion profile header')
    if lines[1].split()[:2]!=['rolljmp','14'] or lines[2].split()[:2]!=['fall','20']:
        raise ValueError('Motion clip headers must precede attachment rows')
    if any(not line.startswith('happa ') for line in lines[3:]):raise ValueError('Unexpected motion profile row')
    keys={(parts[1],int(parts[2])) for line in lines[3:] if len(parts:=line.split())==15}
    expected={(name,index) for name,count in CLIPS for index in range(count)}
    if keys!=expected or len(lines[3:])!=34:raise ValueError('Incomplete attachment matrix bank')
    return text

def extract(iso:Path,output:Path):
    output.mkdir(parents=True,exist_ok=False)
    catalog=disc_files(iso);key='user/Kando/piki/pikis.szs';offset,size=catalog[key]
    with iso.open('rb') as stream:stream.seek(offset);archive_raw=stream.read(size)
    archive=archive_files(archive_raw);model_raw=archive['piki_model/piki_p2_black.bmd']
    skeleton=blocks(model_raw);joints=struct.unpack_from('>H',skeleton['JNT1'],8)[0]
    material=skeleton['MAT3'];names=u32(material,20)
    labels=[material[names+u16(material,names+6+4*i):].split(b'\0',1)[0] for i in range(u16(material,names))]
    if labels!=[b'body1',b'eye1']:raise ValueError('Unexpected Purple material mapping')
    body_color=struct.unpack_from('>4h',material,u32(material,80))
    rows=['P2_PURPLE_MOTION_1'];happa_rows=[];report={}
    for name,expected in CLIPS:
        raw=archive[f'motion/{name}.bca'];duration,_=bca_pose(raw,0,joints,allow_scale=True)
        if duration!=expected or raw[40]!=2:raise ValueError('Unexpected source duration or loop mode')
        rows.append(f'{name} {duration} {duration/30:.6f}')
        for frame in range(duration):
            _,pose=bca_pose(raw,frame,joints,allow_scale=True)
            convert_bytes=output/f'purple_{name}_{frame:02}.mod'
            model=output/'_source_purple.bmd';model.write_bytes(model_raw)
            convert(model,convert_bytes,True,bake_rigid=True,pose=pose,material_colors=[body_color,(255,255,255,255)])
            convert_bytes.with_suffix('.json').unlink()
            matrix=joint_matrices(skeleton,pose)[8]
            happa_rows.append('happa '+name+' '+str(frame)+' '+' '.join(str(v) for row in matrix for v in row))
        report[name]={'frames':duration,'seconds':duration/30,'loop_mode':2,'bca_event_metadata':'absent', 'sha256':sha(raw)}
    (output/'_source_purple.bmd').unlink()
    profile=validate_profile('\n'.join(rows+happa_rows)+'\n');(output/'p2-purple-motion.txt').write_text(profile)
    result={'schema':1,'source_archive':key,'source_archive_sha256':sha(archive_raw),'model_sha256':sha(model_raw),'joints':joints,'body_color':body_color,'motions':report,'phase_clips':PHASE_CLIPS,'source_contract':{'flying_init':'ROLLJUMP','hipdrop_pause_seconds':0.25,'descent_start':'FALL','recovery_seconds':0.3,'recovery_restarts_motion':False}}
    (output/'purple-motion.json').write_text(json.dumps(result,indent=2)+'\n');return result

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--iso',required=True,type=Path);p.add_argument('--output',required=True,type=Path);a=p.parse_args();print(json.dumps(extract(a.iso,a.output),indent=2))
if __name__=='__main__':main()
