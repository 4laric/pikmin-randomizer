"""Fresh cargo-free Beasts floor-2 conversion regression; synthetic action driver."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess

from experimental.pikmin2_beasts_floor2 import prepare, decode_no_cargo, generation_context
from experimental.pikmin2_beasts_party_snapshot import party_snapshot


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def conversion_witnesses(log, generators, *, refund=False):
    """Validate diagnostics for this twenty-Red fixture, not campaign handoffs."""
    records=[]
    for line in log.splitlines():
        if not line.startswith('P2_VIOLET_WITNESS'):continue
        match=re.fullmatch(r'P2_VIOLET_WITNESS sequence=([1-9][0-9]*) generator=([0-9]+) input=(red|blue|yellow|purple)',line)
        if match is None:raise ValueError('Malformed conversion witness')
        sequence,generator,color=match.groups()
        records.append(dict(sequence=int(sequence),generator=int(generator),input=color))
    expected=([generators[0]] if refund else [])+[generator for generator in generators for _ in range(5)]
    if ([r['sequence'] for r in records]!=list(range(1,len(expected)+1))
            or [r['generator'] for r in records]!=expected
            or [r['input'] for r in records]!=(['purple'] if refund else [])+['red']*(len(expected)-int(refund))):
        raise ValueError('Conversion witness sequence/source/input differs')
    if records:
        ready=log.index('P2_BEASTS_READY ');sprouts=log.index('P2_BEASTS_SPROUTS ')
        if refund:
            initialization=log.index('P2_BEASTS_REFUND_INITIAL reds=19 purple=1')
            batch=log.find('P2_VIOLET_CONVERT count=1\n')
            red_throw=log.find('P2_BEASTS_THROW original=1 flower=62000\n')
            if not initialization<ready<batch<red_throw:
                raise ValueError('Same-color cycle must finish before Red inputs')
        positions=[m.start() for m in re.finditer(r'^P2_VIOLET_WITNESS',log,re.M)]
        if not all(ready<position<sprouts for position in positions):raise ValueError('Conversion witness outside conversion phase')
        # Every successful batch must account for exactly its preceding witnesses.
        pending=0
        for line in log.splitlines():
            if line.startswith('P2_VIOLET_WITNESS'):pending+=1
            elif line.startswith('P2_VIOLET_CONVERT'):
                if line!=f'P2_VIOLET_CONVERT count={pending}':raise ValueError('Conversion witness batch differs')
                pending=0
        if pending:raise ValueError('Uncommitted conversion witness batch')
    return records


def validate(log, readiness, *, require_witnesses=False, refund=False):
    extra=int(refund)
    if refund and log.count("P2_BEASTS_REFUND_INITIAL reds=19 purple=1")!=1:raise ValueError("Missing mixed-input initialization")
    if not refund and "P2_BEASTS_REFUND_INITIAL" in log:raise ValueError("Unexpected mixed-input initialization")
    context=readiness.get('generation_context')
    if context is not None:
        try:expected_context=generation_context(context['global_plus_cave_purple'])
        except (KeyError,TypeError) as error:raise ValueError('Malformed generation context') from error
        identity=hashlib.sha256(json.dumps(expected_context,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        if context!=expected_context or readiness.get('generation_identity')!=identity:
            raise ValueError('Generation context identity differs')
        if [f['generator_id'] for f in readiness['flowers']] != context['spawned_generators']:
            raise ValueError('Staged flower selection differs from generation snapshot')
        actual=re.findall(r'^P2_BEASTS_GENERATION purple=(\d+) flowers=(\d+)$',log,re.M)
        if actual!=[(str(context['global_plus_cave_purple']),str(len(context['spawned_generators'])))]:
            raise ValueError('Native generation context differs')
        if not context['spawned_generators']:
            if refund:raise ValueError('Refund fixture requires spawned flowers')
            milestones=['P2_ROOM_CARGO_FREE_READY cargo=0','P2_BEASTS_GENERATION purple='+str(context['global_plus_cave_purple'])+' flowers=0',
                        'P2_BEASTS_READY reds=20 flowers=0 cargo=0',
                        'PASS P2_BEASTS_SUPPRESSED reds=20 purple=0 sprouts=0 flowers=0 cargo=0 pokos=0 repairs_unchanged=1']
            if any(log.count(m)!=1 for m in milestones) or [log.index(m) for m in milestones]!=sorted(log.index(m) for m in milestones):
                raise ValueError('Missing or unordered suppression milestones')
            if any(m in log for m in ('FAIL ','P2_POD_RECEIPT','P2_TREASURE_DELIVERED','P2_ROOM_READY treasure=',
                                     'P2_BEASTS_FLOWER ','P2_BEASTS_THROW','P2_VIOLET_CONVERT','P2_VIOLET_WITNESS','P2_BEASTS_APPROACH',
                                     'P2_BEASTS_SPROUTS','P2_BEASTS_CAPTAIN_PLUCK','P2_BEASTS_FLOWER_CONVERTED','PASS P2_BEASTS_FLOOR2')):
                raise ValueError('Suppressed floor produced unexpected actors/actions/rewards')
            return dict(flowers=[],conversions=[],throw_attempts=0,final_population=dict(red=20,purple=0,sprouts=0),cargo=0,pokos=0)
    expected = f'PASS P2_BEASTS_FLOOR2 reds={10-extra} purple={10+extra} sprouts=0 cargo=0 pokos=0 repairs_unchanged=1'
    milestones = ['P2_ROOM_CARGO_FREE_READY cargo=0', f'P2_BEASTS_READY reds={20-extra} flowers=2 cargo=0',
                  f'P2_BEASTS_SPROUTS reds={10-extra} purple=0 sprouts={10+extra}', 'P2_BEASTS_CAPTAIN_PLUCK purple=1', expected]
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
    if not throws or any(not 0 <= int(i) < 10+extra or int(f) != (62000 if int(i)<5+extra else 62001) for i,f in throws):
        raise ValueError('Invalid throw assignment')
    if {int(i) for i,_ in throws} != set(range(10+extra)):
        raise ValueError('Missing original throw subjects')
    conversions = [int(n) for n in re.findall(r'^P2_VIOLET_CONVERT count=(\d+)$',log,re.M)]
    if sum(conversions) != 10+extra or any(n>5 for n in conversions):
        raise ValueError('Native conversion total differs')
    if re.findall(r'^P2_BEASTS_FLOWER_CONVERTED id=(\d+) count=(\d+)$',log,re.M) != [('62000',str(5+extra)),('62001','5')]:
        raise ValueError('Both flowers must complete five conversions')
    approaches = re.findall(r'^P2_BEASTS_APPROACH flower=(\d+) distance=([\d.]+)$',log,re.M)
    if [i for i,_ in approaches] != ['62000','62001'] or any(not 0 <= float(d) <= 80 for _,d in approaches):
        raise ValueError('Both flowers need controller approach evidence')
    witnesses=conversion_witnesses(log,sorted(planned),refund=refund) if refund or require_witnesses or 'P2_VIOLET_WITNESS' in log else None
    return dict(flowers=flowers, conversions=conversions, witnesses=witnesses, throw_attempts=len(throws),
                final_population=dict(red=10-extra,purple=10+extra,sprouts=0),cargo=0,pokos=0)


def run(args):
    context=generation_context(args.global_purple_count)
    refund=getattr(args,'refund',False)
    if refund and not 1<=args.global_purple_count<20:raise ValueError('Refund fixture requires an incoming Purple and spawned flowers')
    root = args.root.resolve()
    stage = prepare(args.assets.resolve(), root/'output/p2-mapcode0-batch/import',
                    root/'output/p2-cave-catalog-batch/audit-final/catalog.json',
                    root/'output/pikmin2-purple113/import-05',args.output.resolve(),
                    pod=root/'output/pikmin2-pod111/import-02',global_purple_count=args.global_purple_count)
    readiness = json.loads((stage/'readiness.json').read_text())
    decode_no_cargo((stage/'assets/dataDir/stages/chal0/default.gen').read_bytes(),len(context['spawned_generators']))
    (stage/'p2-beasts-floor2-fixture.txt').write_text(f'P2_BEASTS_FLOOR2_FIXTURE_2\n{args.global_purple_count}\n')
    exe = args.exe.resolve()
    inputs = ['readiness.json','p2-purple.txt','p2-pod.txt','p2-cargo-free.txt','p2-beasts-floor2-fixture.txt']
    if refund:
        (stage/'p2-beasts-refund-fixture.txt').write_text('P2_BEASTS_REFUND_1\n')
        inputs.append('p2-beasts-refund-fixture.txt')
    inputs += ['assets/'+name for name in readiness['override_sha256']]
    hashes = {name:sha(stage/name) for name in inputs}
    evidence = dict(schema=1,issue=287,party_policy='P2_BEASTS_PARTY_1',refund_fixture=refund,witness_policy='P2_VIOLET_DIAGNOSTIC_1',run=str(stage),executable=str(exe),executable_sha256=sha(exe),
                    generation_context=context,generation_identity=readiness['generation_identity'],
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
        evidence['observed'] = validate(text,readiness,require_witnesses=True,refund=refund)
        evidence['party_snapshot'] = party_snapshot(text,evidence['observed']['final_population'])
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
    parser.add_argument('--refund',action='store_true',help='Engineering one-Purple input followed by ten Reds; verify same-color slot refund')
    parser.add_argument('--timeout',type=int,default=240)
    parser.add_argument('--global-purple-count',type=int,required=True,help='Declared global-plus-cave Purple population at generation; not inferred from the twenty-Red fixture')
    raise SystemExit(0 if run(parser.parse_args()) else 1)
