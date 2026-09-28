"""Private material-only fixture, frozen Kurage host; no receiver changes."""
import argparse,json,os,subprocess
from pathlib import Path
from scripts import build_pikmin2_fixture as builder
from scripts.preview_pikmin2_room import overlay
from experimental.pikmin2_kurage_material_patch import prepare as base_prepare
from experimental.pikmin2_kurage_envmap import prepare

FROZEN='0894922ef53575590eae6a28b69caeaab1c0e948'


def build(native,build_dir,family,output,head):
    output=output.resolve();output.mkdir(parents=True,exist_ok=False)
    def read(path):return subprocess.check_output(['git','-C',str(family),'show',FROZEN+':'+path]).decode()
    for name in ('pc_p2_kurage_arena.h','pc_p2_kurage_arena.cpp'):
        (output/name).write_text(read('pc_port/'+name))
    source=read('tools/p2_kurage_runtime.cpp')
    source='#include "Pcam/Camera.h"\n#include "Pcam/CameraManager.h"\n'+source
    anchor='        if (readyFrames > 240) {'
    if source.count(anchor)!=1:raise ValueError('Frozen fixture mismatch')
    source=source.replace(anchor,'''        if (readyFrames == 190) {
            require(cameraMgr && cameraMgr->mCamera,"camera missing");
            auto* camera=cameraMgr->mCamera; camera->mControlsEnabled=false;
            camera->mCurrentAzimuth+=0.6f;camera->mPolarDir.mAzimuth=camera->mCurrentAzimuth;
            std::printf("P2_ENVMAP_CAMERA azimuth=%.6f\\n",camera->mCurrentAzimuth);
        }
'''+anchor)
    anchor='        if (!ownerAlive) {'
    if source.count(anchor)!=1:raise ValueError('Frozen capture mismatch')
    source=source.replace(anchor,'        if (readyFrames == 220) capture("kurage-camera-two.ppm");\n'+anchor)
    source+='\n#include "pc_p2_kurage_arena.cpp"\n'
    path=output/'fixture.cpp';path.write_text(source)
    return builder.build_fixture(build_dir,native,path,output/'build',head)


def run(source,imports,converted,exe,output):
    output=output.resolve();output.mkdir(parents=True,exist_ok=False);report={}
    relative='dataDir/courses/pikmin2room/kurage_wait.mod'
    for species in ('Kurage','OniKurage'):
        for mode,patcher in (('base',base_prepare),('envmap',prepare)):
            directory=output/(species+'-'+mode);directory.mkdir()
            patcher(imports/species/'enemy.bmd',converted/species/'wait.mod',directory/'patch')
            overlay(source/'assets',directory/'assets',{relative:(directory/'patch/patched.mod').read_bytes(),
                    'config.ini':(source/'assets/config.ini').read_bytes(),'log.txt':b''})
            for name in ('p2-kurage-arena.txt','p2-groink-arena.txt'):
                (directory/name).write_bytes((source/name).read_bytes())
            with (directory/'native.log').open('w') as log:
                code=subprocess.run([str(exe.resolve()),'--experimental-pikmin2-room'],cwd=directory,
                    env=dict(os.environ,PATH='C:/msys64/mingw64/bin;'+os.environ.get('PATH',''),SDL_AUDIODRIVER='dummy'),
                    stdout=log,stderr=subprocess.STDOUT,timeout=180).returncode
            text=(directory/'native.log').read_text(errors='replace')
            if code!=0 or 'PASS KURAGE_RUNTIME' not in text or 'P2_ENVMAP_CAMERA ' not in text:raise RuntimeError(text[-2000:])
            from PIL import Image
            for name in ('kurage-host-flight','kurage-camera-two','kurage-host-teardown'):
                Image.open(directory/(name+'.ppm')).save(directory/(name+'.png'))
            report[species+'-'+mode]=dict(exit_code=code,directory=str(directory),visual_acceptance='requires capture review',exe_sha256=builder.sha256(exe),
                model_sha256=builder.sha256(directory/'patch/patched.mod'))
            (output/'result.json').write_text(json.dumps(report,indent=2));print(species,mode,'RUNTIME PASS; visual review required',flush=True)
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser();s=p.add_subparsers(dest='command',required=True);b=s.add_parser('build');r=s.add_parser('run')
    for name in ('native','build-dir','family','output'):b.add_argument('--'+name,type=Path,required=True)
    b.add_argument('--head',required=True)
    for name in ('source','imports','converted','exe','output'):r.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args()
    if a.command=='build':build(a.native,a.build_dir,a.family,a.output,a.head)
    else:run(a.source,a.imports,a.converted,a.exe,a.output)
