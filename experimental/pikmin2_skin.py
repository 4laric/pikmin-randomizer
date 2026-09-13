"""Export stable rigid vertex bindings for opt-in Snow skeletal playback."""
import argparse,json,hashlib
from pathlib import Path
from experimental.pikmin2_convert import decode
from experimental.pikmin2_attachments import snow_bank,bank_text
from experimental.pikmin2_assets import disc_files,archive_files
from experimental.pikmin2_animation import parse_bank
from experimental.pikmin2_sheargrub_assets import joints

def export(iso,snow,output):
    report=snow_bank(iso,snow,output)
    model=(snow/'snow.bmd').read_bytes();bindings={}
    # Keep every integer source frame; interpolate joints only between adjacent
    # source frames, rather than inheriting the sparse mesh-bank sample rate.
    timing=parse_bank((snow/'p2-snow.txt').read_text())
    for clip in timing.values():clip['frames']=list(range(clip['source_frames']))
    offset,size=disc_files(iso)['enemy/data/Kochappy/anim.szs']
    with iso.open('rb') as stream:
        stream.seek(offset);archive=archive_files(stream.read(size))
    text=bank_text(model,{n:archive[n+'.bca'] for n in timing},timing).encode('ascii')
    (output/'attachments.txt').write_bytes(text)
    report['bank_sha256']=hashlib.sha256(text).hexdigest()
    report['sampling']='All integer BCA frames; shortest-path quaternion interpolation between frames'
    (output/'attachments.json').write_text(json.dumps(report,indent=2)+'\n')

    _,arrays,_,_=decode(model,approximate_materials=True,bake_rigid=True,pose=[[[1,0,0,0],[0,1,0,0],[0,0,1,0]] for _ in joints(model)],bindings=bindings)
    if any(len(bindings[a])!=len(arrays[a]) for a in (9,10)):raise ValueError('Incomplete vertex binding coverage')
    rows=[f'P2_SKIN_RIGID_1 {len(joints(model))} {len(bindings[9])} {len(bindings[10])}']
    for a in (9,10):
        rows += [str(j)+' '+' '.join(format(v,'.9g') for v in value) for j,value in bindings[a]]
    data=('\n'.join(rows)+'\n').encode('ascii');(output/'skin.txt').write_bytes(data)
    report.update(skin_sha256=hashlib.sha256(data).hexdigest(),positions=len(bindings[9]),normals=len(bindings[10]),scope='Rigid draw bindings; envelopes and joint callbacks rejected/unsupported')
    (output/'skin.json').write_text(json.dumps(report,indent=2)+'\n');return report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('iso','snow','output'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();print(json.dumps(export(a.iso,a.snow,a.output),indent=2))
