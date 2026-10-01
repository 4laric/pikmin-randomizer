"""Canonical configured private build preflight and leased execution."""
import os
from pathlib import Path
import subprocess
import time
from .handoff import require, digest
from .runner import write


def preflight(root, source, build, expected_head):
    root, source, build = (Path(p).resolve() for p in (root, source, build))
    require(source.is_relative_to(root/'output') and build.is_relative_to(root/'output'),
            'Source and build must be private under canonical output/')
    require(source != build and not build.is_relative_to(source), 'Separate private build directory required')
    cache_path = build/'CMakeCache.txt'
    require(cache_path.is_file(), 'Configure a private Ninja build first; CMakeCache.txt is missing')
    cache = {}
    for line in cache_path.read_text(encoding='utf-8').splitlines():
        if line and not line.startswith(('#','//')) and '=' in line:
            key,value = line.split('=',1); cache[key.split(':')[0]] = value
    require(cache.get('CMAKE_GENERATOR') == 'Ninja', 'Configured Ninja generator required')
    require(Path(cache.get('CMAKE_HOME_DIRECTORY','')).resolve() == source, 'Configured source differs')
    tools = {}
    for name,key in [('compiler','CMAKE_CXX_COMPILER'),('ninja','CMAKE_MAKE_PROGRAM')]:
        value = Path(cache.get(key,''))
        path = (value if value.is_absolute() else build/value).resolve()
        require(path.is_file(), 'Configured '+name+' missing: '+str(path))
        tools[name] = dict(path=str(path), sha256=digest(path))
    observed = subprocess.run(['git','-C',str(source),'rev-parse','HEAD'], capture_output=True,text=True,check=True).stdout.strip()
    require(observed == expected_head, 'Native source HEAD changed')
    dirty = subprocess.run(['git','-C',str(source),'status','--porcelain'],capture_output=True,text=True,check=True).stdout
    return dict(source=str(source),build=str(build),native_head=observed,dirty=dirty,
                cache_sha256=digest(cache_path), tools=tools)


def execute(reg, lane, generation, source, build, expected_head, executable, output, jobs=6, wait_seconds=300):
    require(type(jobs) is int and 1 <= jobs <= 6, 'Build parallelism must be 1-6')
    require(type(wait_seconds) in (int,float) and 0 <= wait_seconds <= 3600, 'Queue timeout must be 0-3600 seconds')
    record = preflight(reg.root,source,build,expected_head)
    output, executable = Path(output).resolve(), Path(executable).resolve()
    require(output.is_relative_to(reg.root/'output') and not output.exists(), 'Fresh private evidence directory required')
    require(executable.is_relative_to(Path(record['build'])), 'Executable must belong to this private build')
    current = reg.snapshot()['lanes'][lane]
    require(current['generation'] == generation and current['state'] in ('running','integrating'), 'Current active lane required')
    require(Path((current.get('native') or {}).get('worktree','')).resolve() == Path(record['source']), 'Build source is not owned by lane')
    output.mkdir(parents=True)
    write(output/'preflight.json', record)
    resource = 'build:'+record['build']
    deadline = time.monotonic()+wait_seconds
    while True:
        acquired = reg.acquire(lane,generation,resource,os.getpid(),ttl=3600)
        if acquired['acquired']: break
        if time.monotonic() >= deadline:
            reg.cancel_request(lane,generation,acquired['request']['id'])
            result = dict(passed=False,launched=False,reason='Build capacity wait timed out',preflight=record)
            write(output/'build-result.json',result);return result
        time.sleep(min(5,max(0,deadline-time.monotonic())))
    # This process remains alive and waits for Ninja and all its build children.
    # Its lease is reclaimed only after actual process death, never by TTL alone.
    before = preflight(reg.root,source,build,expected_head)
    require(before == record, 'Build inputs changed during capacity wait')
    current = reg.snapshot()['lanes'][lane]
    require(current['generation'] == generation and current['state'] in ('running','integrating'), 'Lane changed during capacity wait')
    ninja = record['tools']['ninja']['path']
    env = dict(os.environ)
    env['PATH'] = str(Path(record['tools']['compiler']['path']).parent)+os.pathsep+env.get('PATH','')
    command = [ninja,'-j',str(jobs),'pikmin_pc']
    with (output/'build.log').open('w',encoding='utf-8') as log:
        build_result = subprocess.run(command,cwd=build,env=env,stdout=log,stderr=subprocess.STDOUT)
    dry = subprocess.run([ninja,'-n','pikmin_pc'],cwd=build,env=env,capture_output=True,text=True)
    (output/'dry-run.log').write_text(dry.stdout+dry.stderr,encoding='utf-8')
    after = preflight(reg.root,source,build,expected_head)
    result = dict(passed=build_result.returncode == 0 and dry.returncode == 0 and
                  dry.stdout.strip() == 'ninja: no work to do.' and before == after and executable.is_file(),
                  launched=True,command=command,exit_code=build_result.returncode,
                  source_identity_unchanged=before == after,preflight=record,
                  historical_build_certified=False,
                  executable=dict(path=str(executable),sha256=digest(executable)) if executable.is_file() else None,
                  build_log=dict(path=str(output/'build.log'),sha256=digest(output/'build.log')),
                  dry_run=dict(path=str(output/'dry-run.log'),sha256=digest(output/'dry-run.log')),
                  gameplay_accepted=False)
    write(output/'build-result.json',result)
    return result
