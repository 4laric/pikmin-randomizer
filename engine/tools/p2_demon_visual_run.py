"""Private two-pose Demon visual run with hashed provenance."""
import argparse
import json
import subprocess
from pathlib import Path
from p2_groink_volley_run import fixture_provenance, load_preview_prepare, file_record, copy_new, sha256


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('root','assets','room','demon','fixture','output'):
        parser.add_argument('--'+name,type=Path,required=True)
    a=parser.parse_args()
    prov,_,exe,_=fixture_provenance(a.fixture.resolve())
    data=json.loads((a.demon/'demon.json').read_text())
    clip=next(c for c in data['clips'] if c['file']=='attack1.bca')
    selected=[next(p for p in clip['poses'] if p['frame']==f) for f in (0,17)]
    for pose in selected:
        if sha256(a.demon/pose['file'])!=pose['sha256']:
            raise ValueError('Demon model hash mismatch')
    run=load_preview_prepare(a.root.resolve())(a.assets.resolve(),a.room.resolve(),a.output.resolve())
    record={'status':'failed','fixture':file_record(exe),'provenance':file_record(prov),
            'manifest':file_record(a.demon/'demon.json'),'inputs':{},'limitations':['Two baked poses, no attachment.']}
    for pose in selected:
        dest=run/'assets/dataDir/courses/pikmin2room'/f"demon{pose['frame']}.mod"
        copy_new(a.demon/pose['file'],dest)
        record['inputs'][dest.name]=file_record(dest)
    text='\n'.join(' '.join(str(x) for row in mouth['matrix'] for x in row) for pose in selected for mouth in pose['mouths'])+'\n'
    (run/'demon-mouths.txt').write_text(text,encoding='utf-8')
    record['inputs']['mouths']=file_record(run/'demon-mouths.txt')
    for name in ('room.mod','room.ini','treasure.mod'):
        record['inputs'][name]=file_record(a.room/name)
    record['inputs']['preview_helper']=file_record(a.root/'scripts/preview_pikmin2_room.py')
    try:
        command=[str(exe),'--experimental-pikmin2-room']; record['command']=command
        r=subprocess.run(command,cwd=run,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=75)
        (run/'stdout.log').write_text(r.stdout,encoding='utf-8')
        (run/'stderr.log').write_text(r.stderr,encoding='utf-8')
        record['stdout']=file_record(run/'stdout.log'); record['stderr']=file_record(run/'stderr.log')
        record['returncode']=r.returncode
        record['captures']=[file_record(run/name) for name in ('demon0.ppm','demon17.ppm')]
        markers=[f'DEMON_VISUAL_CAPTURE frame={frame} markers=2 no_attachment=1' for frame in (0,17)]
        markers.append('DEMON_CAPTAIN_SHAPES count=2 display_only=1 ordinary_animation=1')
        if r.returncode==0 and 'PASS DEMON_VISUAL' in r.stdout and all(marker in r.stdout for marker in markers):
            record['status']='captured_requires_visual_review'
    except Exception as error:
        record['error']=str(error)
    (run/'verification.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
    print(run/'verification.json')
    return 0 if record['status']=='captured_requires_visual_review' else 1


if __name__=='__main__':
    raise SystemExit(main())
