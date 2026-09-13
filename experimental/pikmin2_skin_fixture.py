"""Private skeletal Snow lifecycle and populated-scene A/B fixture."""
from pathlib import Path
import hashlib,json,shutil
from experimental import pikmin2_snow_interpolation as reference

def build(native,build_dir,output,head):
    old=' require(p2pose::blend(probeBank[clip][span.left].pose,probeBank[clip][span.right].pose,span.weight,expected),"probe blend");'
    new=''' if(std::ifstream("p2-snow-skeletal.txt")){
  std::ifstream jf("p2-snow-joints.txt"),mf("p2-snow-skin.txt");auto bank=p2attach::read(jf);auto mesh=p2skin::read(mf);require(bank&&mesh,"probe skeleton");
  p2attach::Instance instance;auto token=instance.bind(bank);expected.positions.resize(mesh->positions.size());expected.normals.resize(mesh->normals.size());
  require(instance.sample(token,bank->clip(clip),frame,p2attach::Affine{},1)&&p2skin::deform(*mesh,instance,token,expected),"probe deformation");
 }else{'''+old+'\n }'
    assert reference.PROBE.count(old)==1
    probe='#include "pc_p2_skin.h"\n'+reference.PROBE.replace(old,new).replace('if(probeBank.empty()){','if(probeBank.empty() && !std::ifstream("p2-snow-skeletal.txt")){')
    return reference.build(native,build_dir,output,head,probe=probe)

def enable(bank,snow,run):
    report=json.loads((bank/'skin.json').read_text())
    for file,key in [('skin.txt','skin_sha256'),('attachments.txt','bank_sha256')]:
        if hashlib.sha256((bank/file).read_bytes()).hexdigest()!=report[key]:raise ValueError('Skeletal bank hash mismatch')
    for file,key in [('snow.bmd','model_sha256'),('p2-snow.txt','timing_sha256')]:
        if hashlib.sha256((snow/file).read_bytes()).hexdigest()!=report[key]:raise ValueError('Skeletal visual identity mismatch')
    shutil.copyfile(bank/'skin.txt',run/'p2-snow-skin.txt');shutil.copyfile(bank/'attachments.txt',run/'p2-snow-joints.txt')
    (run/'p2-snow-interpolation.txt').write_text('P2_SNOW_INTERPOLATION_1\n')
    (run/'p2-snow-skeletal.txt').write_text('P2_SNOW_SKELETAL_1\n')
    # Only remove generated pose copies inside this fresh private stage.
    directory=run/'assets/dataDir/courses/pikmin2room'
    removed=[]
    for path in directory.glob('snow_*.mod'):
        if path.name=='snow_wait1_00.mod':continue
        if not path.resolve().is_relative_to(run.resolve()):raise ValueError('Pose outside private stage')
        removed.append(dict(name=path.name,bytes=path.stat().st_size));path.unlink()
    (run/'skeletal-models.json').write_text(json.dumps(dict(removed=removed,base_bytes=(directory/'snow_wait1_00.mod').stat().st_size),indent=2))


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    b=sub.add_parser('build')
    for name in ('native','build-dir','output'):b.add_argument('--'+name,type=Path,required=True)
    b.add_argument('--head',required=True)
    r=sub.add_parser('run')
    for name in ('assets','converted','pod','snow','bank','exe','output'):r.add_argument('--'+name,type=Path,required=True)
    r.add_argument('--profile',action='store_true');r.add_argument('--reference',action='store_true')
    a=p.parse_args()
    if a.command=='build':build(a.native.resolve(),a.build_dir.resolve(),a.output.resolve(),a.head)
    else:
        from experimental.pikmin2_snow_lifecycle import prepare
        a.output.mkdir(parents=True,exist_ok=False)
        run=(reference.stage_profile if a.profile else prepare)(a.assets.resolve(),a.converted.resolve(),a.pod.resolve(),a.snow.resolve(),a.output/'stage')
        (run/'p2-snow-interpolation.txt').write_text('P2_SNOW_INTERPOLATION_1\n')
        if not a.reference:enable(a.bank,a.snow,run)
        (a.output/'run.txt').write_text(str(run))
        report=reference.execute(a.exe.resolve(),run,profile=a.profile)
        print(json.dumps(report,indent=2));raise SystemExit(0 if report['passed'] else 1)
