"""Fresh cargo-free Beasts floor-2 conversion regression; synthetic action driver."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess

from experimental.pikmin2_beasts_floor2 import prepare, decode_no_cargo


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate(log, readiness):
    expected = 'PASS P2_BEASTS_FLOOR2 reds=10 purple=10 sprouts=0 cargo=0 pokos=0 repairs_unchanged=1'
    milestones = ['P2_ROOM_CARGO_FREE_READY cargo=0', 'P2_BEASTS_READY reds=20 flowers=2 cargo=0',
                  'P2_BEASTS_SPROUTS reds=10 purple=0 sprouts=10', 'P2_BEASTS_CAPTAIN_PLUCK purple=1', expected]
    if any(log.count(marker) != 1 for marker in milestones):
        raise ValueError('Missing or duplicate native milestone')
    if [log.index(marker) for marker in milestones] != sorted(log.index(marker) for marker in milestones):
        raise ValueError('Native conversion milestone order differs')
    if any(marker in log for marker in ('FAIL ', 'P2_POD_RECEIPT', 'P2_TREASURE_DELIVERED', 'P2_ROOM_READY treasure=')):
        raise ValueError('Failed or cargo-bearing floor')
    flowers = []
    for line in log.splitlines():
        if not line.startswith('P2_BEASTS_FLOWER '):continue
        try:
            fields = dict(field.split('=', 1) for field in line.split()[1:])
            flowers.append(dict(id=int(fields['id']), position=[float(fields[k]) for k in ('x','y','z')],
                                live=[float(fields[k]) for k in ('live_x','live_y','live_z')], ground=float(fields['ground'])))
        except (ValueError, KeyError) as error:
            raise ValueError('Malformed native flower evidence') from error
    planned = {f['generator_id']:f['position'] for f in readiness['flowers']}
    if len(flowers) != 2 or sorted(f['id'] for f in flowers) != sorted(planned):
        raise ValueError('Native flower identity differs')
    for f in flowers:
        if any(not math.isfinite(v) for v in f['position']+f['live']+[f['ground']]):
            raise ValueError('Nonfinite flower coordinates')
        if any(abs(a-b)>.1 for a,b in zip(f['position'],planned[f['id']])) or abs(f['ground']-f['position'][1])>.1:
            raise ValueError('Native flower birth/ground differs from source slot')
        if any(abs(a-b)>.1 for a,b in zip(f['live'],f['position'])):
            raise ValueError('Native flower drifted from its source slot')
    throws = re.findall(r'^P2_BEASTS_THROW original=(\d+) flower=(\d+)$',log,re.M)
    if not throws or any(not 0 <= int(i) < 10 or int(f) != 62000+int(i)//5 for i,f in throws):
        raise ValueError('Invalid throw assignment')
    if {int(i) for i,_ in throws} != set(range(10)):
        raise ValueError('Missing original throw subjects')
    conversions = [int(n) for n in re.findall(r'^P2_VIOLET_CONVERT count=(\d+)$',log,re.M)]
    if sum(conversions) != 10 or any(n>5 for n in conversions):
        raise ValueError('Native conversion total differs')
    if re.findall(r'^P2_BEASTS_FLOWER_CONVERTED id=(\d+) count=(\d+)$',log,re.M) != [('62000','5'),('62001','5')]:
        raise ValueError('Both flowers must complete five conversions')
    approaches = re.findall(r'^P2_BEASTS_APPROACH flower=(\d+) distance=([\d.]+)$',log,re.M)
    if [i for i,_ in approaches] != ['62000','62001'] or any(not 0 <= float(d) <= 80 for _,d in approaches):
        raise ValueError('Both flowers need controller approach evidence')
    return dict(flowers=flowers, conversions=conversions, throw_attempts=len(throws),
                final_population=dict(red=10,purple=10,sprouts=0),cargo=0,pokos=0)


def run(args):
    root = args.root.resolve()
    stage = prepare(args.assets.resolve(), root/'output/p2-mapcode0-batch/import',
                    root/'output/p2-cave-catalog-batch/audit-final/catalog.json',
                    root/'output/pikmin2-purple113/import-05',args.output.resolve(),
                    pod=root/'output/pikmin2-pod111/import-02')
    readiness = json.loads((stage/'readiness.json').read_text())
    decode_no_cargo((stage/'assets/dataDir/stages/chal0/default.gen').read_bytes())
    (stage/'p2-beasts-floor2-fixture.txt').write_text('P2_BEASTS_FLOOR2_FIXTURE_1\n')
    exe = args.exe.resolve()
    inputs = ['readiness.json','p2-purple.txt','p2-pod.txt','p2-cargo-free.txt','p2-beasts-floor2-fixture.txt']
    inputs += ['assets/'+name for name in readiness['override_sha256']]
    hashes = {name:sha(stage/name) for name in inputs}
    evidence = dict(schema=1,issue=263,run=str(stage),executable=str(exe),executable_sha256=sha(exe),
                    readiness_sha256=sha(stage/'readiness.json'),natural_gameplay=False,
                    scripted_native_throws=True,scripted_captain_pluck=True,remaining_plucks='InteractBikkuri',
                    source_p2_pom_fsm=False,passed=False,input_sha256=hashes)
    print(stage,flush=True)
    env = dict(os.environ,SDL_AUDIODRIVER='dummy',PATH='C:/msys64/mingw64/bin'+os.pathsep+os.environ.get('PATH',''))
    with (stage/'native.log').open('w') as log:
        try:
            result = subprocess.run([str(exe),'--experimental-pikmin2-room'],cwd=stage,env=env,
                                    stdout=log,stderr=subprocess.STDOUT,timeout=args.timeout)
            evidence['returncode'] = result.returncode
        except subprocess.TimeoutExpired:
            evidence['timeout'] = True
    text = (stage/'native.log').read_text(errors='replace')
    try:
        if evidence.get('returncode') != 0:raise ValueError('Native fixture did not exit successfully')
        evidence['observed'] = validate(text,readiness)
        if sha(exe) != evidence['executable_sha256'] or any(sha(stage/name)!=digest for name,digest in hashes.items()):
            raise ValueError('Executable or staged input changed during run')
        for name in ('treasure-receipt.txt','p2-economy.txt','p2-cargo.txt'):
            if (stage/name).exists():raise ValueError('Unexpected cargo or receipt file: '+name)
        evidence['passed'] = True
    except (ValueError,OSError) as error:
        evidence['validation_error'] = str(error)
    evidence['log_sha256'] = sha(stage/'native.log')
    evidence['captures'] = {p.name:sha(p) for p in stage.glob('beasts-floor2-*.ppm')}
    (stage/'acceptance.json').write_text(json.dumps(evidence,indent=2)+'\n')
    print(json.dumps(evidence),flush=True)
    return evidence['passed']


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('root','assets','exe','output'):parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--timeout',type=int,default=240)
    raise SystemExit(0 if run(parser.parse_args()) else 1)
