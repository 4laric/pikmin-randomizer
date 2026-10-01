"""Private generated-seed delivery acceptance; readiness is separate from gameplay."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import shutil
import os
import subprocess

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from randomizer.seed import generate, fingerprint, validate
from randomizer.session import Session
from randomizer.runner import NativeRun
from randomizer.campaign_data import CAMPAIGN_SLOTS
from experimental.pikmin2_family_install import install_layout
from scripts.preview_pikmin2_room import overlay
from randomizer.test_run import apply_test_run_env

TARGET = 1849273021
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
                        p2_checks=True, p2_placement=document, starting_area='forest',
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


def prepare(directory, content, assets, seed='p2-journal-1096'):
    if directory.exists():
        raise ValueError('Use a fresh private output directory')
    directory.mkdir(parents=True)
    manifest, audit = case(seed)
    (directory / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    session = Session(manifest, directory / 'session')
    run = NativeRun(session)
    # This is local bridge acceptance in AP mode, without a network server.
    # No item/check/receipt is injected. Session's starting inventory supplies state.
    run.write_state(True)
    receipt = install_layout(run.directory, manifest['p2_layout'], content,
                             actor_bindings={str(TARGET): TARGET}, retail_assets=assets)
    # Existing production TEST_BACKGROUND startup withdraws the real20 starting
    # Pikmin through GoalItem::exitPikis and their native descent/join states.
    # Use that tested equivalent baseline; no generator/player inventory edits.
    game=directory/'game';game.mkdir()
    overlay(run.directory/'assets',game/'assets',{})
    for file in run.directory.iterdir():
        if file.is_file() and file.name not in ('bootstrap.txt','state.txt'):
            shutil.copy2(file,game/file.name)
    audit.update(schema=1, fingerprint=fingerprint(manifest), native_run=str(run.directory),
                 bootstrap_sha256=digest(run.bootstrap), content_receipt=receipt,
                 state_sha256=digest(run.directory / 'state.txt'),
                 runtime_status='UNTESTED', delivery_status='UNTESTED', game=str(game),
                 field_staging={'count':20,'species':'Red','method':'Existing production TEST_BACKGROUND real Onion withdrawal',
                                'fixture_inventory_writes':False,'fixture_generator_writes':False,
                                'enemy_position_override':False,
                                'source_default_sha256':digest(assets/'dataDir/stages/stage1/default.gen'),
                                'original_enemy_file_sha256':digest(assets/'dataDir/stages/stage1/0-29.gen')},
                 local_ap_readiness=True, network_ap_acceptance=False)
    (directory / 'readiness.json').write_text(json.dumps(audit, indent=2) + '\n')
    return audit, session, run


def observe(audit, session, run, fixture, workspace, negative=False):
    provenance=json.loads(fixture.with_name('provenance.json').read_text())
    if provenance['status']!='built' or provenance['artifacts'][str(fixture.resolve())]['sha256']!=digest(fixture):
        raise ValueError('Use the exact built replacement-main fixture')
    env=os.environ.copy()
    for key in list(env):
        if key.startswith(('PIKMIN_RANDOMIZER_AUTOPLAY','PIKMIN_P2_','P2_GENERATED_')):
            del env[key]
    env['PIKMIN_RANDOMIZER_AUTOPLAY']='0'
    env.pop('PIKMIN_RANDOMIZER_MANUAL_START',None)
    apply_test_run_env(env,workspace)
    if negative:env['P2_GENERATED_FORCE_CAPTAIN_DOWN']='1'
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
                    limitations=['Local AP-mode bridge; no network server/item relay/reconnect proof.','Controller automated; tutorial/movie skip instrumented.','Original enemy placement preserved.'])
    report.update(fixture_sha256=digest(fixture),native_head=provenance['expected_native_head'],runtime_log_sha256=digest(game/'native.log'))
    (game/'assessment.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
    return 0 if report['passed'] else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--workspace', required=True, type=Path)
    parser.add_argument('--assets', required=True, type=Path)
    parser.add_argument('--content', required=True, type=Path)
    parser.add_argument('--seed', default='p2-journal-1096')
    parser.add_argument('--fixture',type=Path)
    parser.add_argument('--negative',action='store_true')
    args = parser.parse_args()
    if not args.output.resolve().is_relative_to(args.workspace.resolve() / 'output'):
        raise ValueError('Private output must be under the canonical workspace output/')
    report,session,run = prepare(args.output.resolve(), args.content.resolve(), args.assets.resolve(), args.seed)
    print(json.dumps({k: report[k] for k in ('fingerprint', 'native_run', 'runtime_status', 'delivery_status')}))
    if args.fixture:return observe(report,session,run,args.fixture.resolve(),args.workspace.resolve(),args.negative)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
