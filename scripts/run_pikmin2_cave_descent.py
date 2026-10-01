"""Bounded compiled-consumer proof for the actual ordinary two-floor supervisor."""
import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from randomizer.cave_floor import atomic_write
from randomizer.cave_journey import Session, zero_buds, read_json
from scripts.stage_pikmin2_cave_journey import stage_package
from scripts.play_pikmin2_cave_journey import main as play


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def driver(package, crash):
    if crash:
        original = Session.recover
        def interrupt(self, live_paths=()):
            if self.pending_path.exists():
                pending = read_json(self.pending_path)
                run = self.run_path(pending['run'])
                if self.load()['floor'] == 1 and (run/'p2-cave-transfer.txt').exists():
                    saved, boundary = self.source_boundary(run)
                    atomic_write(self.directory/'injected-crash.json',json.dumps(dict(
                        method='abrupt supervisor exit73 after actual native42 and before atomic boundary commit',
                        native_run=str(run),incoming=saved,boundary=boundary),indent=2)+'\n')
                    os._exit(73)
            return original(self,live_paths)
        Session.recover = interrupt
    return play(package,agent_test=True)


def child_proof(run):
    raw = read_json(run/'run-result.json')
    log = (run/'native.log').read_text(errors='replace')
    floor = int((run/'p2-cave-entry.txt').read_text().split()[2])
    checks = dict(bounded=raw.get('timeout_seconds') == 60 and not raw.get('timed_out'),
                  no_autoplay='FOCUS_HOLD' not in log and 'AUTOPLAY_' not in log and 'P2_AUTOPLAY' not in log)
    if raw.get('exit_code') == 86:
        checks.update(captain_negative=raw.get('captain_down') is True,
                      no_success='PASS CAVE_DESCENT' not in log)
    else:
        checks.update(captain_safe=not raw.get('captain_down'),
                      window='P2_CAVE_FINAL_WINDOW width=960 height=540 mode=0' in log,
                      centered='centered=1' in log,
                      gamepad='input=SDL_virtual process_local=1 navi_override=0' in log)
        if floor == 1:
            checks.update(native42=raw.get('exit_code') == 42,
                          native_red='P2_CAVE_DESCENT_SPECIES red_id=1 yellow_id=2 blue_id=0 red_count=20 yellow_count=0 blue_count=0' in log,
                          source_boundary='P2_CAVE_DESCENT_CHECKPOINT red=15 blue=5 survivors=20 conversions=5' in log,
                          source_bud_accepts=log.count('colour=blue thrown_colour=1 used=') == 5)
        else:
            checks.update(native0=raw.get('exit_code') == 0,
                          native_floor2='PASS CAVE_DESCENT_FLOOR2 floor=2 red=15 blue=5 yellow=0 count=20 health=1 maturity_exact=1' in log,
                          actual_actors='observed_native_actors=1' in log)
    names = ['native.log','run-result.json','run-inputs.json','cave.json','layout.json','p2-cave-entry.txt']
    names += [p.name for p in run.iterdir() if p.is_file() and p.name in (
        'p2-cave-transfer.txt','p2-cave-bud-transfer.txt','p2-cave-bud-entry.txt','fixture-floor2-observed-buds.txt')]
    return dict(run=str(run),floor=floor,exit_code=raw.get('exit_code'),elapsed_seconds=raw.get('elapsed_seconds'),
                checks=checks,passed=all(checks.values()),hashes={name:sha(run/name) for name in names})


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--driver',action='store_true'); p.add_argument('--package',type=Path)
    p.add_argument('--mode',choices=('normal','restart','crash','resume','negative'),default='normal')
    for name in ('workspace','fixture','production','generator','assets','pod','output','previous'):
        p.add_argument('--'+name,type=Path)
    a = p.parse_args()
    if a.driver:
        driver(a.package.resolve(),a.mode == 'crash')
        return 0
    if any(getattr(a,name) is None for name in ('workspace','fixture','production','generator','assets','pod','output')):
        p.error('workspace, fixture, production, generator, assets, pod and output are required')
    workspace,out = a.workspace.resolve(),a.output.resolve()
    if not out.is_relative_to(workspace/'output') or out.exists():
        raise ValueError('use fresh private case output')
    provenance = read_json(a.fixture.with_name('provenance.json'))
    if provenance['status'] != 'built' or provenance['artifacts'][str(a.fixture.resolve())]['sha256'] != sha(a.fixture):
        raise ValueError('fixture is not its frozen built artifact')
    source = Path(__file__).resolve().parents[1]
    root_head = subprocess.check_output(['git','rev-parse','HEAD'],cwd=source,text=True).strip()
    root_dirty = subprocess.check_output(['git','status','--porcelain'],cwd=source,text=True)
    if root_dirty:
        raise ValueError('commit and freeze root source before runtime acceptance')
    source_hashes = {name:sha(source/name) for name in ('randomizer/cave_floor.py','randomizer/cave_journey.py',
        'scripts/play_pikmin2_cave.py','scripts/play_pikmin2_cave_journey.py',
        'scripts/stage_pikmin2_playable_cave.py','scripts/stage_pikmin2_cave_journey.py',
        'scripts/run_pikmin2_cave_descent.py')}
    out.mkdir(parents=True)
    before = set()
    if a.mode in ('restart','resume'):
        if a.previous is None:
            raise ValueError('restart/resume requires its prior proof')
        previous = read_json(a.previous/'assessment.json')
        if not previous['passed'] or (a.mode == 'resume' and previous['mode'] != 'crash'):
            raise ValueError('previous compiled case failed')
        for child in previous['children']:
            for name,digest in child['hashes'].items():
                if sha(Path(child['run'])/name) != digest:
                    raise ValueError('prior compiled evidence changed')
        package = Path(previous['package']).resolve()
        before = set((package/'session/runs').iterdir())
    else:
        package = out/'package'
        # Explicit replacement-main test executable; production binary is a
        # separately hashed build artifact, never mistaken for the fixture.
        stage_package('1127','Player1',a.assets,a.pod,a.fixture,a.generator,package,workspace)
    command = [sys.executable,'-X','utf8',str(Path(__file__).resolve()),'--driver','--package',str(package),'--mode',a.mode]
    env = os.environ.copy()
    env.pop('P2_CAVE_GUARDED_BOOT_FORCE_CAPTAIN_DOWN',None)
    if a.mode == 'negative':
        env['P2_CAVE_GUARDED_BOOT_FORCE_CAPTAIN_DOWN'] = '1'
    with (out/'driver.log').open('w',encoding='utf-8') as log:
        code = subprocess.run(command,cwd=workspace,env=env,stdout=log,stderr=subprocess.STDOUT).returncode
    runs = sorted(set((package/'session/runs').iterdir())-before)
    children = [child_proof(run) for run in runs]
    state = read_json(package/'session/state.json')
    atomic_write(out/'journey-state.json',json.dumps(state,indent=2)+'\n')
    checks = dict(children_pass=bool(children) and all(c['passed'] for c in children))
    if a.mode == 'negative':
        checks.update(driver_rejected=code != 0,one_negative=len(children) == 1 and children[0]['exit_code'] == 86,
                      no_transition=state['floor'] == 1 and state['revision'] == 0)
    elif a.mode == 'crash':
        crash = read_json(package/'session/injected-crash.json')
        atomic_write(out/'crash-observation.json',json.dumps(crash,indent=2)+'\n')
        checks.update(abrupt_exit=code == 73,actual_source=len(children) == 1 and children[0]['exit_code'] == 42,
                      pending= (package/'session/pending.json').is_file(),uncommitted=state['floor'] == 1 and state['revision'] == 0)
    else:
        invocation = read_json(package/'session/last-launch.json')
        atomic_write(out/'invocation.json',json.dumps(invocation,indent=2)+'\n')
        checks.update(driver0=code == 0,committed_floor2=state['floor'] == 2 and state['revision'] == 1,
                      actual_mixed=state['entry']['squad'].count([1,0]) == 15 and state['entry']['squad'].count([0,0]) == 5,
                      source_budget='bud:0 5' in state['boundary']['buds'],
                      no_pending=not (package/'session/pending.json').exists())
        manifests = read_json(package/'journey.json')['floors']
        for child in children:
            if child['floor'] == 2:
                snapshot = (Path(child['run'])/'fixture-floor2-observed-buds.txt').read_text()
                checks['destination_budget'] = snapshot == state['entry']['buds'] == zero_buds(manifests[1]['descriptor'])
        expected_floors = [1,2] if a.mode == 'normal' else [2]
        checks['actual_supervisor_children'] = sorted(c['floor'] for c in children) == expected_floors
        checks['recovery_policy'] = invocation['recovered_boundary'] == (a.mode == 'resume')
    checks['source_unchanged'] = all(sha(source/name) == digest for name,digest in source_hashes.items())
    report = dict(schema=1,mode=a.mode,package=str(package),passed=all(checks.values()),driver_exit=code,
                  checks=checks,children=children,inputs=dict(fixture_sha256=sha(a.fixture),production_sha256=sha(a.production),
                      runner_sha256=sha(__file__),native_head=provenance['expected_native_head'],
                      root_head=root_head,root_dirty=root_dirty,source_hashes=source_hashes),
                  limitations=['Ordinary staged20Red baseline; SDL virtual controller scripted input.',
                      'Bud auto-pluck, captain-only source exit, confirmation bypass.',
                      'Runtime incoming maturity all leaf/health1; heterogeneous values covered only by policy tests.',
                      'Abrupt supervisor73 crash injection; actual native source transfer bytes preserved.',
                      'No floor3/terminal return/campaign/AP/full mixed hazard traversal.'])
    atomic_write(out/'assessment.json',json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
