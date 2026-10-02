"""Supervise a fresh <=60s engineering mechanic diagnostic, never tutorial/AP approval."""
import argparse,hashlib,json,os,re,subprocess,uuid
from pathlib import Path
from scripts.stage_pikmin2_purple_kochappy import prepare
from scripts.run_pikmin2_cave_fixture import supervise
from scripts.fixture_platform import is_windows, runtime_evidence, linux_admission

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

DLLS=('SDL2.dll','libgcc_s_seh-1.dll','libstdc++-6.dll','libwinpthread-1.dll')

def runtime_dependencies(exe,runtime_dir,native_pin):
    """Refuse missing/conflicting DLLs before staging or launching anything."""
    exe,runtime_dir=Path(exe).resolve(),Path(runtime_dir).resolve()
    info=runtime_dir/'BUILD_INFO.txt';manifest=runtime_dir/'sha256.txt'
    if f'commit {native_pin}' not in info.read_text().splitlines():
        raise ValueError('CI runtime package source pin mismatch')
    wanted={}
    for line in manifest.read_text().splitlines():
        match=re.fullmatch(r'([0-9a-f]{64}) \*?(?:\./)?([^/\\]+)',line)
        if match and match[2] in DLLS:
            if match[2] in wanted:raise ValueError('Duplicate CI DLL manifest row')
            wanted[match[2]]=match[1]
    if set(wanted)!=set(DLLS):raise ValueError('CI runtime manifest missing required DLL')
    records={}
    for name in DLLS:
        source=runtime_dir/name;local=exe.parent/name
        if not source.is_file() or sha(source)!=wanted[name]:
            raise ValueError('Missing/conflicting CI runtime DLL: '+name)
        if not local.is_file() or sha(local)!=wanted[name]:
            raise ValueError('Missing/conflicting executable-local DLL: '+name)
        records[name]=dict(sha256=wanted[name],source=str(source),exe_local=str(local))
    return dict(native=native_pin,package=str(runtime_dir),manifest_sha256=sha(manifest),
                build_info_sha256=sha(info),dlls=records)

def controlled_environment(ambient,exe,runtime_dir,save,mode):
    env={k:v for k,v in ambient.items() if not k.upper().startswith(('PIKMIN_','P2_','COOP_','NECTAR_')) and k.lower()!='path'}
    runtime_paths=[str(Path(exe).resolve().parent)]
    if runtime_dir is not None:runtime_paths.append(str(Path(runtime_dir).resolve()))
    runtime_paths.append(next((v for k,v in ambient.items() if k.lower()=='path'),''))
    env.update(PATH=os.pathsep.join(runtime_paths),
               NECTAR_EXECUTABLE_PATH=str(Path(exe).resolve()),NECTAR_SAVE_DIR=str(Path(save).resolve()),
               PIKMIN_P2_TEST_START_DAY='5',PIKMIN_P2_ROOM_WINDOW='960x540',PIKMIN_RANDOMIZER_TEST_BACKGROUND='1')
    switches={'ready':'P2_PURPLE_KOCHAPPY_READY_ONLY','forced-down':'P2_PURPLE_KOCHAPPY_FORCE_DOWN','paused-down':'P2_PURPLE_KOCHAPPY_PAUSED_DOWN'}
    if mode in switches:env[switches[mode]]='1'
    return env

def linux_runtime_inputs(exe,root,session,run,env,root_pin,native_pin,source_hash):
    """ELF closure plus the actual fixed broker admission; no caller proof fallback."""
    dependencies=runtime_evidence(exe,env=env,cwd=run)
    proof=linux_admission(exe,root,session,run)
    if proof['pins']['FIXTURE_SUITE']!='purple-kochappy-runtime':
        raise ValueError('Fixed Purple runtime recipe required; compile proof is insufficient')
    if proof['exe_sha256']!=dependencies['executable']['sha256']:
        raise ValueError('Executable drift between ELF closure and broker admission')
    if proof['target']!='pikmin_ci_fixture_purple_kochappy' or proof['source']!='tools/p2_purple_kochappy_runtime.cpp':
        raise ValueError('Wrong fixed Purple target/source')
    if proof['pins']['PIKMIN_SHA']!=root_pin or proof['pins']['NATIVE_SHA']!=native_pin or proof['pins']['FIXTURE_SOURCE_SHA256']!=source_hash:
        raise ValueError('Broker source pins differ from requested Purple inputs')
    return dependencies,proof

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('exe','assets','bundle','red-bank','purple-bank','motion','pod','output','native'):
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--runtime-dir',type=Path,help='Mandatory matching CI DLL package on Windows; forbidden on Linux')
    p.add_argument('--exe-sha256',required=True);p.add_argument('--root-sha',required=True);p.add_argument('--native-sha',required=True)
    p.add_argument('--mode',choices=('ready','positive','forced-down','paused-down'),required=True)
    p.add_argument('--plan',action='store_true')
    a=p.parse_args();root=Path(__file__).resolve().parent.parent
    for repo,pin in ((root,a.root_sha),(a.native,a.native_sha)):
        if subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip()!=pin:
            raise ValueError('Actual source HEAD differs from requested pin')
        if subprocess.check_output(['git','-C',str(repo),'status','--porcelain'],text=True).strip():
            raise ValueError('Commit and disclose actual source before runtime')
    if sha(a.exe)!=a.exe_sha256:raise ValueError('Fixture executable differs from exact remote artifact')
    if is_windows():
        if a.runtime_dir is None:raise ValueError('Matching Windows CI DLL package required')
        dependencies=runtime_dependencies(a.exe,a.runtime_dir,a.native_sha)
    elif a.runtime_dir is not None:raise ValueError('Linux resolves ELF libraries; no DLL runtime directory')
    output=a.output.resolve()/uuid.uuid4().hex
    run=prepare(a.assets.resolve(),a.bundle.resolve(),'c8598f04bb884ab396d126b8dfbed6a6ce78d2f6afc92e7b366a5e5c11ccc8d5',a.red_bank.resolve(),a.purple_bank.resolve(),a.motion.resolve(),a.pod.resolve(),output)
    (run/'private-save').mkdir()
    env=controlled_environment(os.environ,a.exe,a.runtime_dir,run/'private-save',a.mode)
    admission=None
    if not is_windows():
        dependencies,admission=linux_runtime_inputs(a.exe,root,a.output.resolve(),run,env,a.root_sha,a.native_sha,sha(a.native/'tools/p2_purple_kochappy_runtime.cpp'))
        (run/'admission.json').write_text(json.dumps(admission,indent=2)+'\n')
    inputs=dict(root=a.root_sha,native=a.native_sha,fixture_sha256=sha(a.exe),mode=a.mode,
                stage_inputs_sha256=sha(run/'purple-kochappy-inputs.json'),fresh_private_save=env['NECTAR_SAVE_DIR'],runtime_dependencies=dependencies,
                controlled_environment={k:v for k,v in env.items() if k.startswith(('PIKMIN_','P2_','COOP_','NECTAR_'))},
                source_fixture_sha256=sha(a.native/'tools/p2_purple_kochappy_runtime.cpp'),
                scope='engineering preview natural receiver mechanic; tutorial/AP mixed OPEN',timeout_seconds=60,
                platform='windows' if is_windows() else 'linux',broker_admission=admission)
    (run/'acceptance-inputs.json').write_text(json.dumps(inputs,indent=2)+'\n')
    if a.plan:print(json.dumps(dict(run=str(run),inputs=inputs),indent=2));return 0
    negative=a.mode.endswith('down');marker='P2_FIXTURE_CAPTAIN_DOWN' if negative else 'P2_PURPLE_KOCHAPPY_READY' if a.mode=='ready' else 'P2_PURPLE_KOCHAPPY_MECHANIC_RECOVERY_PASS'
    raw=supervise([str(a.exe.resolve()),'--experimental-pikmin2-room'],run,60,env,[marker])
    log=(run/'native.log').read_text(errors='replace')
    passed=not raw.get('timed_out') and raw.get('exit_code')==(86 if negative else 0) and marker in log
    pauses=re.findall(r'P2_KOCHAPPY_STUN_PAUSE generator=(\d+) source_id=1 state=(\w+) state_time=([0-9.]+)',log)
    resumes=re.findall(r'P2_KOCHAPPY_STUN_RESUME generator=(\d+) source_id=1 state=(\w+) state_time=([0-9.]+)',log)
    # Recovery is an observed equal clock/state pair, not an injected state.
    recovery_clock=any(row in resumes for row in pauses)
    if not is_windows():passed=passed and raw.get('owned_process_group')==raw.get('pid') and raw.get('pid',0)>0
    passed=passed and 'P2_PURPLE_KOCHAPPY_WINDOW size=960x540 centered=1' in log
    if a.mode=='positive':
        passed=passed and recovery_clock and 'accepted=1 reason=red_dwarf' in log and 'live=20 Red=19 Purple=1 SDL_throw_pluck=1 species_writes=0' in log and 'death_during_stun=1' in log
    if negative:passed=passed and 'P2_PURPLE_KOCHAPPY_MECHANIC_RECOVERY_PASS' not in log
    result=dict(passed=bool(passed),raw=raw,inputs_sha256=sha(run/'acceptance-inputs.json'),log_sha256=sha(run/'native.log'),
                observed_pause_clocks=pauses,observed_resume_clocks=resumes,recovery_clock_equal=recovery_clock,
                unit_injection=False,positive_actor_writes=False,engineering_preview=True,ordinary_tutorial_AP_mixed='OPEN',
                owner1128_wholecampaign_Violet_acquisition='UNCLAIMED',human_gamefeel='UNCLAIMED')
    (run/'acceptance-assessment.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(run=str(run),**result),indent=2))
    return 0 if passed else 1

if __name__=='__main__':raise SystemExit(main())
