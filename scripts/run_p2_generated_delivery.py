"""Private generated-seed delivery acceptance; readiness is separate from gameplay."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import shutil
import os
import subprocess
import asyncio

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from randomizer.seed import generate, fingerprint, validate
from randomizer.session import Session
from randomizer.runner import NativeRun, ap_connect
from randomizer.campaign_data import CAMPAIGN_SLOTS
from experimental.pikmin2_family_install import install_layout
from scripts.preview_pikmin2_room import overlay
from randomizer.test_run import apply_test_run_env

TARGET = 3921089765
SOURCE = 44
ABSENT = 34


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def case(seed='p2-journal-1096'):
    """A supported placement subset; preserve existing slot and profile facts."""
    document_path = Path(__file__).resolve().parents[1] / 'docs/PIKMIN2_ADMITTED_PLACEMENT.json'
    original = json.loads(document_path.read_text())
    document = dict(original)
    document['slots'] = [s for s in original['slots'] if s['uid'] == TARGET]
    document.pop('arenas', None)
    document.pop('held_parts', None)
    assert len(document['slots']) == 1
    manifest = generate(seed, mode='ap', p2_enemies=True, p2_species=[SOURCE, ABSENT],
                        p2_checks=True, p2_placement=document, starting_area='spring',
                        starting_color='red', starting_flarlic=2)
    validate(manifest)
    assert manifest['p2_layout']['bindings'] == [dict(target=str(TARGET), source_id=SOURCE, enum_name='BlueKochappy')]
    assert manifest['p2_layout']['unplaced'] == [ABSENT]
    checks = manifest['enemy_catalog']['checks']
    assert any(r['game'] == 'p1' and r['species'] == 3 for r in checks)
    assert [r['species'] for r in checks if r['game'] == 'p2'] == [SOURCE]
    return manifest, dict(slot=document['slots'][0], original_document_sha256=digest(document_path),
                          placement_subset=document, campaign_slot=next(r for r in CAMPAIGN_SLOTS if r['uid'] == TARGET),
                          note='Subset of existing audited targets; unchanged geometry/profile/admission facts. Not the stock all-target seed.')


def prepare(directory, content, assets, seed='p2-journal-1096', supplied_manifest=None, minimal_surroundings=False):
    if directory.exists():
        raise ValueError('Use a fresh private output directory')
    directory.mkdir(parents=True)
    manifest, audit = case(seed)
    if supplied_manifest is not None:
        validate(supplied_manifest)
        if supplied_manifest['p2_layout']['bindings'] != manifest['p2_layout']['bindings'] or supplied_manifest['p2_layout']['unplaced'] != [ABSENT]:
            raise ValueError('Server manifest must preserve the selected source44 and excluded34 case')
        manifest = supplied_manifest
        audit['manifest_source'] = 'Genuine private AP Generate/Main output'
    (directory / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    session = Session(manifest, directory / 'session')
    run = NativeRun(session)
    # This is local bridge acceptance in AP mode, without a network server.
    # Selected starting color/area are native manifest grants; received stream may
    # legitimately be empty. Authentic readiness still requires AP authentication.
    run.write_state(False)
    receipt = install_layout(run.directory, manifest['p2_layout'], content,
                             actor_bindings={str(TARGET): TARGET}, retail_assets=assets)
    # Existing production TEST_BACKGROUND startup withdraws the real20 starting
    # Pikmin through GoalItem::exitPikis and their native descent/join states.
    # Use that tested equivalent baseline; no generator/player inventory edits.
    game=directory/'game';game.mkdir()
    overrides={};suppressed={}
    stage_folder=('practice','stage1','stage2','stage3','last')[audit['campaign_slot']['stage']]
    target_file=audit['campaign_slot']['source'].split('/',1)[1].split('@',1)[0]
    stage_dir='dataDir/stages/'+stage_folder
    if minimal_surroundings:
        for path in (assets/stage_dir).glob('*.gen'):
            if path.name in ('default.gen',target_file):continue
            blob=path.read_bytes()
            if blob[:4]!=b'1.0v' or len(blob)<24:raise ValueError('Unsupported generator header: '+str(path))
            key=stage_dir+'/'+path.name
            overrides[key]=blob[:20]+bytes(4)
            suppressed[key]={'original_sha256':digest(path),'zero_record_sha256':hashlib.sha256(overrides[key]).hexdigest()}
    overlay(run.directory/'assets',game/'assets',overrides)
    audit['surrounding_content_subset']={'enabled':minimal_surroundings,'suppressed':suppressed,'target_file_byte_exact':digest(game/'assets'/stage_dir/target_file)==digest(assets/stage_dir/target_file),'original_ship_onions_default_byte_exact':digest(game/'assets'/stage_dir/'default.gen')==digest(assets/stage_dir/'default.gen'),'full_campaign_route_acceptance':False}
    for file in run.directory.iterdir():
        if file.is_file() and file.name not in ('bootstrap.txt','state.txt'):
            shutil.copy2(file,game/file.name)
    source_root=Path(__file__).resolve().parents[1]
    audit.update(schema=1, root_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=source_root,text=True).strip(), root_dirty=subprocess.check_output(['git','status','--porcelain'],cwd=source_root,text=True), stager_sha256=digest(__file__), fingerprint=fingerprint(manifest), native_run=str(run.directory),
                 bootstrap_sha256=digest(run.bootstrap), content_receipt=receipt,
                 state_sha256=digest(run.directory / 'state.txt'),
                 runtime_status='UNTESTED', delivery_status='UNTESTED', game=str(game),
                 field_staging={'count':20,'species':'Red','method':'Existing production TEST_BACKGROUND real Onion withdrawal',
                                'fixture_inventory_writes':False,'fixture_generator_writes':False,
                                'enemy_position_override':False,
                                'source_default_sha256':digest(assets/stage_dir/'default.gen'),
                                'original_enemy_file_sha256':digest(assets/stage_dir/target_file)},
                 local_ap_readiness=False, network_ap_acceptance=False)
    (directory / 'readiness.json').write_text(json.dumps(audit, indent=2) + '\n')
    return audit, session, run


def observe(audit, session, run, fixture, workspace, negative=False):
    provenance=json.loads(fixture.with_name('provenance.json').read_text())
    if provenance['status']!='built' or provenance['artifacts'][str(fixture.resolve())]['sha256']!=digest(fixture):
        raise ValueError('Use the exact built replacement-main fixture')
    env=os.environ.copy()
    removed_env={}
    for key in list(env):
        if key.startswith(('PIKMIN_','P2_')) and key not in ('PIKMIN_WATCH_RUNS','PIKMIN_WORKFLOW_DIR'):
            removed_env[key]=env.pop(key)
    env['PIKMIN_RANDOMIZER_AUTOPLAY']='0'
    env.pop('PIKMIN_RANDOMIZER_MANUAL_START',None)
    apply_test_run_env(env,workspace)
    if negative:env['P2_GENERATED_FORCE_CAPTAIN_DOWN']='1'
    (Path(audit['game'])/'test-environment.json').write_text(json.dumps({'removed_game_environment':removed_env,'effective_game_environment':{k:v for k,v in env.items() if k.startswith(('PIKMIN_','P2_'))},'input_source':'SDL virtual P1 through native polling; no input-script calls'},indent=2)+'\n')
    command=[sys.executable,str(workspace/'scripts/run_pikmin2_fixture.py'),'--exe',str(fixture.resolve()),
             '--run-dir',audit['game'],'--arg=--randomizer-seed','--arg='+str(run.bootstrap.resolve()),
             '--pass-marker','PASS P2_GENERATED_DELIVERY','--timeout','60']
    subprocess.run(command,cwd=workspace,env=env,check=False)
    game=Path(audit['game']);raw=json.loads((game/'run-result.json').read_text())
    log=(game/'native.log').read_text(errors='replace')
    if negative:
        passed=raw['exit_code']==86 and raw['captain_down'] and not raw['timed_out'] and 'PASS P2_GENERATED_DELIVERY' not in log
        report=dict(passed=passed,method='artificial guard input',raw=raw)
    else:
        run.poll()
        target=next(r for r in session.manifest['enemy_catalog']['checks'] if r['game']=='p2' and r['species']==SOURCE)
        recovered=Session(session.manifest,session.directory)
        checks=dict(raw_pass=raw['passed'],guard_safe=not raw['captain_down'],bounded=raw['timeout_seconds']==60 and not raw['timed_out'],
                    actual_native_check='PASS P2_GENERATED_DELIVERY actual_native_check=1' in log,
                    exact_session_check=session.data['checked'].count(target['name'])==1,
                    persisted_recovery=recovered.data==session.data,
                    natural_death='P2_GENERATED_NATURAL_DEATH observed=1 health_writes=0' in log)
        report=dict(passed=all(checks.values()),checks=checks,raw=raw,checked=list(session.data['checked']),
                    journal_sha256=digest(run.directory/'checks.txt') if (run.directory/'checks.txt').exists() else None,
                    session_sha256=digest(session.path),handshake=run.handshaken,
                    limitations=['Native gameplay assessment; network/reconnect evidence is separate.','Controller automated; tutorial/movie skip instrumented.','Original enemy placement preserved.'])
    report.update(fixture_sha256=digest(fixture),native_head=provenance['expected_native_head'],runtime_log_sha256=digest(game/'native.log'))
    (game/'assessment.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
    return 0 if report['passed'] else 1


async def network_observe(audit, session, run, fixture, workspace, server, negative):
    ready = [False]
    connection = asyncio.create_task(ap_connect(session, server, '', ready))
    try:
        for _ in range(200):
            if connection.done():
                await connection
            if ready[0]:
                break
            await asyncio.sleep(.1)
        if not ready[0] or session.data['ap_identity'] is None:
            raise RuntimeError('Private AP authentication/item reconciliation did not complete')
        audit['local_ap_readiness'] = True
        audit['network_setup'] = {'server': server, 'identity': session.data['ap_identity'], 'received_count':len(session.data['received']), 'artificial_receipts':False}
        run.write_state(True)
        (Path(audit['game']).parent/'authenticated-readiness.json').write_text(json.dumps(audit,indent=2)+'\n')
        async def maintain_native_protocol():
            while True:
                run.poll()
                run.write_state(run.handshaken and ready[0])
                await asyncio.sleep(.1)
        heartbeat = asyncio.create_task(maintain_native_protocol())
        try:
            result = await asyncio.to_thread(observe,audit,session,run,fixture,workspace,negative)
            if heartbeat.done():await heartbeat
        finally:
            heartbeat.cancel()
            try:await heartbeat
            except asyncio.CancelledError:pass
        await asyncio.sleep(2) # Permit actual LocationChecks -> actual server reward stream.
        if connection.done():
            await connection
        connection.cancel()
        try:
            await connection
        except asyncio.CancelledError:
            pass
        before = json.loads(json.dumps(session.data))
        ready[0] = False
        connection = asyncio.create_task(ap_connect(session,server,'',ready))
        for _ in range(200):
            if connection.done():
                await connection
            if ready[0]:
                break
            await asyncio.sleep(.1)
        network = {'authenticated':ready[0], 'before_reconnect':before, 'after_reconnect':session.data, 'no_duplicate_receipts':before['received']==session.data['received'], 'gameplay_result':result, 'no_check_injection':True}
        (Path(audit['game']).parent/'network-assessment.json').write_text(json.dumps(network,indent=2)+'\n')
        return result if ready[0] and network['no_duplicate_receipts'] else 1
    finally:
        connection.cancel()
        try:
            await connection
        except asyncio.CancelledError:
            pass


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--workspace', required=True, type=Path)
    parser.add_argument('--assets', required=True, type=Path)
    parser.add_argument('--content', required=True, type=Path)
    parser.add_argument('--seed', default='p2-journal-1096')
    parser.add_argument('--fixture',type=Path)
    parser.add_argument('--negative',action='store_true')
    parser.add_argument('--manifest',type=Path)
    parser.add_argument('--server')
    parser.add_argument('--shader-cache',type=Path)
    parser.add_argument('--minimal-surroundings',action='store_true')
    args = parser.parse_args()
    if not args.output.resolve().is_relative_to(args.workspace.resolve() / 'output'):
        raise ValueError('Private output must be under the canonical workspace output/')
    report,session,run = prepare(args.output.resolve(), args.content.resolve(), args.assets.resolve(), args.seed, json.loads(args.manifest.read_text()) if args.manifest else None,args.minimal_surroundings)
    if args.shader_cache:
        cache=args.shader_cache.resolve()
        if not cache.is_relative_to(args.workspace.resolve()/'output') or not cache.is_dir():raise ValueError('Reuse only private shader cache directories')
        shutil.copytree(cache,Path(report['game'])/'shader_cache')
        report['shader_cache']={str(p.relative_to(cache)):digest(p) for p in cache.rglob('*') if p.is_file()}
        (args.output.resolve()/'readiness.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k: report[k] for k in ('fingerprint', 'native_run', 'runtime_status', 'delivery_status')}))
    if args.fixture:
        if not args.server:raise ValueError('Runtime requires a genuine private AP server; readiness staging alone is allowed')
        return asyncio.run(network_observe(report,session,run,args.fixture.resolve(),args.workspace.resolve(),args.server,args.negative))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
