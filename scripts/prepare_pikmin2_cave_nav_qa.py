"""Machine-local #193 diagnostic QA package; never starts gameplay while preparing/checking."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys

SCHEMA='P2_CAVE_NAV_QA_1'
DIAGNOSTIC_ENV={'PIKMIN_CAVE_NAV_DIAGNOSTICS':'1','PYTHONDONTWRITEBYTECODE':'1'}


def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def ordinary(path):
    path=Path(path).absolute()
    if path.resolve()!=path or path.is_symlink():raise ValueError('Linked path forbidden: '+str(path))
    return path


def protected_snapshot(root):
    """Hash ordinary files without following any stage asset junctions."""
    root=ordinary(root);result={}
    def walk(directory):
        for item in sorted(directory.iterdir()):
            info=item.lstat();name=item.relative_to(root).as_posix()
            if stat.S_ISLNK(info.st_mode) or getattr(info,'st_file_attributes',0)&0x400:
                result[name]={'link':os.readlink(item)}
            elif item.is_dir():walk(item)
            elif item.is_file():result[name]={'sha256':digest(item),'size':info.st_size}
            else:raise ValueError('Unsupported preserved entry')
    walk(root);return result


def frozen_tools(source=None):
    if source is not None:sys.path.insert(0,str(source))
    from scripts.prepare_pikmin2_manual_qa import inventory,source_inventory
    from scripts.compare_pikmin2_extractions import manifest
    return inventory,source_inventory,manifest


def seed_state(entry_raw,ledger_raw):
    from experimental.pikmin2_surface_ledger import validate
    entry=json.loads(entry_raw);state=validate(json.loads(ledger_raw))
    if state['phase']!='cave' or state['revision']!=2 or state['trip']['checkpoint']['floor']!=2:
        raise ValueError('Expected preserved revision2 floor2 checkpoint')
    if entry['campaign']!=state['campaign'] or entry['content']!=state['content'] or entry['trip']!=state['trip']['id']:
        raise ValueError('Entry/ledger identity mismatch')
    return state


def make_command(root,record):
    args=[record['python']['path'],'-B','-m','scripts.play_pikmin2_surface']
    for key,value in record['assets'].items():args += ['--'+key.replace('_','-'),value]
    for role in ('surface','cave'):args += ['--'+role+'-exe',str(root/role/record['executables'][role])]
    return args+['--output',str(root/'session')]


def prepare(fixed_manifest,cave_runtime,output,native_revision,expected_exe_sha256,build_log):
    from scripts.bundle_pikmin2_fixture import sha256
    fixed_manifest=ordinary(fixed_manifest);fixed=json.loads(fixed_manifest.read_bytes());origin=fixed_manifest.parent
    output=ordinary(output);cave_runtime=ordinary(cave_runtime)
    if output.exists() or not output.parent.is_dir():raise ValueError('Fresh package under existing directory required')
    inventory,source_inventory,manifest=frozen_tools()
    if fixed.get('schema')!=1 or source_inventory(Path(fixed['source']))!=fixed['source_files']:raise ValueError('Fixed launcher source changed')
    if any(inventory(fixed['assets'][k])!=v for k,v in fixed['inputs'].items()):raise ValueError('Fixed asset content changed')
    if any(manifest(origin/role)!=value for role,value in fixed['runtime'].items()):raise ValueError('Fixed runtime changed')
    preserved=protected_snapshot(origin)
    session=ordinary(fixed['session']);entry_raw=(session/'entry-command.json').read_bytes();ledger_raw=(session/'session/surface-ledger.json').read_bytes()
    for rel in ('failed-entry.json','failed-return.json','session/pending-handoff.json'):
        if (session/rel).exists():raise ValueError('Pending/failed original session cannot be cloned by this bounded tool')
    state=seed_state(entry_raw,ledger_raw)
    runtime=json.loads((cave_runtime/'runtime-provenance.json').read_bytes())
    if digest(cave_runtime/runtime['executable'])!=expected_exe_sha256:raise ValueError('Unexpected diagnostic executable')
    for row in runtime['files']:
        if Path(row['name']).name!=row['name'] or digest(cave_runtime/row['name'])!=row['sha256']:raise ValueError('Diagnostic DLL/exe mismatch')
    raw=(cave_runtime/runtime['executable']).read_bytes()
    if b'PIKMIN_CAVE_NAV_DIAGNOSTICS' not in raw or b'P2_CAVE_NAV' not in raw:raise ValueError('Executable lacks diagnostic contract strings')
    output.mkdir();source=output/'launcher-source';source.mkdir()
    for rel,expected in fixed['source_files'].items():
        target=source/rel
        if Path(rel).is_absolute() or '..' in Path(rel).parts:raise ValueError('Unsafe source name')
        data=(Path(fixed['source'])/rel).read_bytes()
        if hashlib.sha256(data).hexdigest()!=expected:raise ValueError('Source changed while copying')
        target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
    # Copy only declared immutable runtime files; never copy old sessions or asset junctions.
    for role,location in [('surface',origin/'surface'),('cave',cave_runtime)]:
        (output/role).mkdir()
        names=manifest(location)
        for name in names:
            p=Path(name)
            if p.name!=name:raise ValueError('Runtime must be flat')
            (output/role/name).write_bytes((location/name).read_bytes())
    clone=output/'session';(clone/'session').mkdir(parents=True)
    (clone/'entry-command.json').write_bytes(entry_raw);(clone/'session/surface-ledger.json').write_bytes(ledger_raw)
    (output/'diagnostic-launcher.py').write_bytes(Path(__file__).read_bytes())
    build_log=ordinary(build_log);(output/'production-build.log').write_bytes(build_log.read_bytes())
    (output/'origin-qa-launch.json').write_bytes(fixed_manifest.read_bytes())
    (output/'clone-seed-ledger.json').write_bytes(ledger_raw)
    executables={role:json.loads((output/role/'runtime-provenance.json').read_bytes())['executable'] for role in ('surface','cave')}
    record=dict(schema=SCHEMA,version=output.name,origin=str(origin),origin_manifest_sha256=digest(fixed_manifest),
      protected=preserved,source_files=fixed['source_files'],python=fixed['python'],assets=fixed['assets'],inputs=fixed['inputs'],
      runtime={r:manifest(output/r) for r in executables},executables=executables,environment=DIAGNOSTIC_ENV,
      clone=dict(campaign=state['campaign'],content=state['content'],origin=state['origin'],revision=2,
                 entry_sha256=hashlib.sha256(entry_raw).hexdigest(),ledger_sha256=hashlib.sha256(ledger_raw).hexdigest(),
                 policy='Byte-identical authoritative checkpoint; no old run directories, leases, native saves or transfers copied. Historical entry.run is inert because this guard requires an existing cloned ledger.'),
      built_native_revision=native_revision,expected_cave_sha256=expected_exe_sha256,build_log_sha256=digest(build_log),
      launcher_sha256=digest(output/'diagnostic-launcher.py'),gameplay_validated=False)
    record['command']=make_command(output,record)
    if source_inventory(source)!=record['source_files'] or protected_snapshot(origin)!=preserved:raise ValueError('Original package/source changed during preparation')
    for role,value in record['runtime'].items():
        if manifest(output/role)!=value:raise ValueError('Copied runtime changed')
    if (clone/'session/surface-ledger.json').read_bytes()!=ledger_raw:raise ValueError('Clone differs')
    (output/'diagnostic-qa.json').write_bytes((json.dumps(record,indent=2)+'\n').encode())
    (output/'Check.cmd').write_bytes(b'@echo off\r\npy -3.12 "%~dp0diagnostic-launcher.py" check "%~dp0diagnostic-qa.json"\r\n')
    (output/'Resume-Diagnostics.cmd').write_bytes(b'@echo off\r\necho NEW cloned diagnostic session. Original manual-qa-02 is preserved.\r\npy -3.12 "%~dp0diagnostic-launcher.py" launch "%~dp0diagnostic-qa.json"\r\n')
    return record


def check(path,probe=True):
    path=ordinary(path);root=path.parent;record=json.loads(path.read_bytes())
    inventory,source_inventory,manifest=frozen_tools(root/'launcher-source')
    if record.get('schema')!=SCHEMA or record['environment']!=DIAGNOSTIC_ENV:raise ValueError('Unsupported diagnostic protocol/environment')
    if digest(root/'diagnostic-launcher.py')!=record['launcher_sha256']:raise ValueError('Diagnostic launcher changed')
    if source_inventory(root/'launcher-source')!=record['source_files']:raise ValueError('Frozen launcher source changed')
    if digest(record['python']['binary'])!=record['python']['sha256']:raise ValueError('Python binary changed')
    for key,value in record['inputs'].items():
        if inventory(record['assets'][key])!=value:raise ValueError('Asset input changed: '+key)
    for role,value in record['runtime'].items():
        if manifest(root/role)!=value:raise ValueError('Runtime bundle changed: '+role)
    if record['command']!=make_command(root,record):raise ValueError('Command differs from declared package')
    if record['expected_cave_sha256']!=digest(root/'cave'/record['executables']['cave']):raise ValueError('Wrong diagnostic executable')
    if protected_snapshot(record['origin'])!=record['protected']:raise ValueError('Original fixed QA package changed since clone; investigate before resuming')
    ledger=ordinary(root/'session/session/surface-ledger.json');entry=ordinary(root/'session/entry-command.json')
    if not ledger.is_file() or digest(entry)!=record['clone']['entry_sha256']:raise ValueError('Missing cloned checkpoint or altered entry; never follow historical entry.run')
    from experimental.pikmin2_surface_ledger import validate
    state=validate(json.loads(ledger.read_bytes()))
    if any(state[k]!=record['clone'][k] for k in ('campaign','content','origin')) or state['revision']<record['clone']['revision']:raise ValueError('Cloned ledger identity/revision regressed')
    if probe:
        code="import json,sys;from pathlib import Path;from experimental.pikmin2_surface_runner import NativeContent;m=json.loads(Path(sys.argv[1]).read_bytes());a={k:Path(v) for k,v in m['assets'].items()};c=NativeContent(a['assets'],a['imported'],[a['pod1'],a['pod2']],a['purple'],a['treasure'],a.get('transitions'),a.get('snow'),a.get('roster'),a.get('transition_assets'),source_import=a['source_import'],pocket=a['pocket']);print(c.identity)"
        env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1')
        result=subprocess.run([record['python']['path'],'-B','-c',code,str(path)],cwd=root/'launcher-source',env=env,text=True,capture_output=True)
        if result.returncode:raise ValueError('Frozen content probe failed: '+result.stderr.strip())
        if result.stdout.strip()!=state['content']:raise ValueError('Frozen source content identity differs from cloned ledger')
    return record


def launch(path,process=subprocess.run):
    path=ordinary(path);record=check(path);env=dict(os.environ,**record['environment'])
    env['PATH']=str(path.parent/'cave')+os.pathsep+str(path.parent/'surface')+os.pathsep+str(Path(os.environ.get('SystemRoot','C:/Windows'))/'System32')
    print('Diagnostic clone only: '+str(path.parent/'session'),flush=True)
    print('PIKMIN_CAVE_NAV_DIAGNOSTICS=1; floor2 geyser target X=-550 Y=25 Z=520, radius45.',flush=True)
    return process(record['command'],cwd=path.parent/'launcher-source',env=env).returncode


def main():
    p=argparse.ArgumentParser(description=__doc__);s=p.add_subparsers(dest='mode',required=True);a=s.add_parser('prepare')
    for name in ('fixed-manifest','cave-runtime','output','build-log'):a.add_argument('--'+name,type=Path,required=True)
    a.add_argument('--native-revision',required=True);a.add_argument('--expected-exe-sha256',required=True)
    for mode in ('check','launch'):s.add_parser(mode).add_argument('manifest',type=Path)
    args=p.parse_args()
    if args.mode=='prepare':prepare(args.fixed_manifest,args.cave_runtime,args.output,args.native_revision,args.expected_exe_sha256,args.build_log);print('Prepared; no game launched')
    elif args.mode=='check':r=check(args.manifest);print(json.dumps(dict(checked=True,environment=r['environment'],command=r['command'],gameplay_validated=False)))
    else:return launch(args.manifest)
    return 0

if __name__=='__main__':raise SystemExit(main())
