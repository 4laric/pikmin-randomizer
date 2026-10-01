"""Capture or compare native Snow animation performance without inferring FPS from assets."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import statistics
import subprocess
import time

from experimental.pikmin2_animation import parse_bank, validate_files

NUMBER = r'(\d+(?:\.\d+)?)'
PERF = re.compile(r'\[PERF\] '+NUMBER+r' fps '+NUMBER+r' ms \| '+NUMBER+r' draws')
GPU = re.compile(r'\[PERF GPU\] scene '+NUMBER+r' ms blit '+NUMBER+r' ms \((\d+) async samples\)')
TEXTURES = re.compile(r'\[PC Port\] Textures: (\d+) live, (\d+) MB \(peak (\d+) MB\)')
TICK_HEADER = re.compile(r'\[PC tick\] last (\d+) ticks, budget '+NUMBER+r' ms')
TICK_ROW = re.compile(r'^\s*(.*?)\s+mean\s+'+NUMBER+r'\s+p50\s+'+NUMBER+r'\s+p95\s+'+NUMBER+r'\s+p99\s+'+NUMBER+r'\s+worst\s+'+NUMBER+r'\s*$')


def parse_log(text, warmup_windows=1, start_marker=None):
    if warmup_windows < 0:
        raise ValueError('warmup_windows must be nonnegative')
    windows, gpu, textures, banks, ticks = [], [], [], [], []
    snow_draw = {'live_observed':False, 'corpse_observed':False}
    active = start_marker is None
    current_tick = None
    malformed = []
    for line_number, line in enumerate(text.splitlines(), 1):
        if start_marker and start_marker in line:
            active = True
        if not active:
            continue
        if 'P2_SNOW_DRAW corpse=0' in line:snow_draw['live_observed']=True
        if 'P2_SNOW_DRAW corpse=1' in line:snow_draw['corpse_observed']=True
        if 'P2_SNOW_BANK ' in line:
            fields = dict(re.findall(r'(\w+)=([^\s]+)', line))
            try:
                row = {k:int(fields[k]) for k in ('poses', 'mod_bytes', 'texture_attach_calls')}
                row['load_seconds'] = float(fields['load_seconds'])
                if any(v < 0 or not math.isfinite(v) for v in row.values()):
                    raise ValueError()
                banks.append(row)
            except (ValueError, KeyError):
                malformed.append(line_number)
        match = PERF.search(line)
        if match:
            fps, ms, draws = map(float, match.groups())
            if fps > 0 and ms > 0 and all(math.isfinite(x) for x in (fps, ms, draws)):
                windows.append({'reported_fps':fps, 'mean_frame_ms':ms, 'draws_per_frame':draws})
            else:
                malformed.append(line_number)
        elif '[PERF] ' in line:
            malformed.append(line_number)
        match = GPU.search(line)
        if match:
            scene, blit, count = match.groups()
            gpu.append({'scene_ms':float(scene), 'blit_ms':float(blit), 'samples':int(count)})
        match = TEXTURES.search(line)
        if match:
            live, size, peak = map(int, match.groups())
            textures.append({'live':live, 'mib_rounded_down':size, 'peak_mib_rounded_down':peak})
        match = TICK_HEADER.search(line)
        if match:
            current_tick = {'samples':int(match[1]), 'budget_ms':float(match[2]), 'regions':{}}
            ticks.append(current_tick)
        elif current_tick:
            match = TICK_ROW.match(line)
            if match:
                name, *values = match.groups()
                # Native gl:/gx: rows mix counts and milliseconds. Keep them
                # separate rather than labelling every profiler row as time.
                unit = 'ms' if name in ('update','renderall','doneRender','tick','gl:uniforms','gl:vbo','gl:draw') else 'count_or_percent'
                current_tick['regions'][name] = dict(zip(('mean','p50','p95','p99','worst'), map(float, values)), unit=unit)
    retained = windows[warmup_windows:]
    presentation = None
    if retained:
        mean_ms = statistics.mean(w['mean_frame_ms'] for w in retained)
        presentation = {'window_count':len(retained), 'frames_per_window':120,
                        'mean_frame_ms':mean_ms, 'effective_fps_from_window_means':1000/mean_ms,
                        'slowest_window_mean_ms':max(w['mean_frame_ms'] for w in retained),
                        'mean_draws_per_frame':statistics.mean(w['draws_per_frame'] for w in retained),
                        'per_frame_p95_ms':None, 'per_frame_p99_ms':None}
    complete_ticks = [x for x in ticks if 'tick' in x['regions']]
    return {'presentation':presentation, 'perf_windows_seen':len(windows),
            'warmup_windows_discarded':min(warmup_windows,len(windows)),
            'last_tick_window':complete_ticks[-1] if complete_ticks else None,
            'last_gpu_window':gpu[-1] if gpu else None,
            'texture_memory':{'last':textures[-1], 'maximum_reported_mib':max(x['mib_rounded_down'] for x in textures)} if textures else None,
            'bank_loads':banks, 'snow_draw':snow_draw, 'malformed_line_numbers':malformed,
            'start_marker_found':active}


def asset_metrics(imported):
    bank = parse_bank((imported/'p2-snow.txt').read_text())
    _, size = validate_files(imported, bank)
    metadata = json.loads((imported/'snow.json').read_text())
    return {'pose_count':sum(row['poses'] for row in bank.values()), 'mod_bytes':size,
            'extract_seconds':metadata.get('cost',{}).get('extract_seconds'),
            'sha256':hashlib.sha256((imported/'p2-snow.txt').read_bytes()).hexdigest(),
            'note':'Offline extraction cost and sample density; neither measures runtime FPS or heap usage.'}


def report(log, imported=None, warmup_windows=1, start_marker=None, capture=None):
    result = {'schema':1, 'log':str(log.resolve()),
              'runtime':parse_log(log.read_text(errors='replace'),warmup_windows,start_marker),
              'assets':asset_metrics(imported) if imported else None,
              'capture':json.loads(capture.read_text()) if capture else None,
              'limitations':['PERF values are 120-frame window means, not individual frame samples.',
                             'CPU tick reports overlap; only the last complete rolling window is shown.',
                             'Texture MB logs are rounded-down MiB tracked by the renderer, not total process RAM.',
                             'No controlled camera/input/scene equivalence is established by this tool.']}
    runtime=result['runtime']
    result['unmeasured'] = []
    for name,key in (('presentation FPS/frame time','presentation'),('CPU tick timing','last_tick_window'),
                     ('GPU timing','last_gpu_window'),('tracked texture memory','texture_memory')):
        if runtime[key] is None:result['unmeasured'].append(name)
    if not runtime['bank_loads']:result['unmeasured'].append('Snow native bank load time')
    result['unmeasured'] += ['total process RAM','per-frame presentation percentiles']
    if not runtime['snow_draw']['live_observed']:
        result['limitations'].append('No Snow live draw marker: FPS describes this room workload, not demonstrated Snow rendering.')
    if result['assets'] and runtime['bank_loads']:
        result['bank_identity_matches'] = all(x['poses']==result['assets']['pose_count'] and x['mod_bytes']==result['assets']['mod_bytes'] for x in runtime['bank_loads'])
    else:
        result['bank_identity_matches'] = None
    return result


def compare(baseline, candidate):
    comparisons = {}
    for name,path in {'presentation_mean_ms':('runtime','presentation','mean_frame_ms'),
                      'effective_fps':('runtime','presentation','effective_fps_from_window_means'),
                      'texture_mib':('runtime','texture_memory','maximum_reported_mib'),
                      'asset_bytes':('assets','mod_bytes')}.items():
        def get(obj):
            for key in path:
                if obj is None:return None
                obj=obj.get(key)
            return obj
        old,new=get(baseline),get(candidate)
        comparisons[name]={'baseline':old,'candidate':new,'delta':new-old if old is not None and new is not None else None}
    loads=[r['runtime']['bank_loads'] for r in (baseline,candidate)]
    values=[statistics.mean(x['load_seconds'] for x in rows) if rows else None for rows in loads]
    comparisons['bank_load_seconds']={'baseline':values[0],'candidate':values[1],
                                      'delta':values[1]-values[0] if all(v is not None for v in values) else None}
    return {'schema':1,'baseline':baseline,'candidate':candidate,'comparison':comparisons,
            'causality':'Descriptive only. Match executable, room, camera, squad, settings and capture duration before attributing a change to animation density.'}


def capture_command(command, cwd, output, seconds):
    """Explicit owned child only; never attach to or terminate a running playtest."""
    if not command or not 0 < seconds <= 3600:
        raise ValueError('Expected command and capture duration between 0 and 3600 seconds')
    output.mkdir(parents=True,exist_ok=False)
    env=dict(os.environ,PIKMIN_PERF_STATS='1',PIKMIN_TICK_STATS='1')
    executable=Path(command[0])
    try:
        executable_sha256=hashlib.sha256(executable.read_bytes()).hexdigest() if executable.is_file() else None
    except OSError:
        # Windows App Execution Aliases may launch but cannot be read as files.
        executable_sha256=None
    started=time.monotonic()
    with (output/'native.log').open('w') as stream:
        process=subprocess.Popen(command,cwd=cwd,env=env,stdout=stream,stderr=subprocess.STDOUT)
        timed_out=False
        try:
            code=process.wait(timeout=seconds)
        except subprocess.TimeoutExpired:
            timed_out=True
            process.terminate()
            try:code=process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill();code=process.wait()
    metadata={'command':command,'cwd':str(cwd.resolve()),'elapsed_seconds':time.monotonic()-started,
              'executable_sha256':executable_sha256,
              'exit_code':code,'timed_out':timed_out,'profiler_environment':{'PIKMIN_PERF_STATS':'1','PIKMIN_TICK_STATS':'1'},
              'note':'Wall time includes startup. This is not a gameplay FPS measurement.'}
    (output/'capture.json').write_text(json.dumps(metadata,indent=2))
    return metadata


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    commands=parser.add_subparsers(dest='mode',required=True)
    analyze=commands.add_parser('analyze')
    analyze.add_argument('--log',type=Path,required=True)
    analyze.add_argument('--bank',type=Path)
    analyze.add_argument('--capture',type=Path)
    analyze.add_argument('--warmup-windows',type=int,default=1)
    analyze.add_argument('--start-marker')
    analyze.add_argument('--output',type=Path,required=True)
    diff=commands.add_parser('compare')
    diff.add_argument('--baseline',type=Path,required=True)
    diff.add_argument('--candidate',type=Path,required=True)
    diff.add_argument('--output',type=Path,required=True)
    capture=commands.add_parser('capture')
    capture.add_argument('--cwd',type=Path,required=True)
    capture.add_argument('--output',type=Path,required=True)
    capture.add_argument('--seconds',type=float,default=90)
    capture.add_argument('command',nargs=argparse.REMAINDER)
    args=parser.parse_args()
    if args.mode=='capture':
        command=args.command[1:] if args.command[:1]==['--'] else args.command
        print(json.dumps(capture_command(command,args.cwd,args.output,args.seconds),indent=2));return
    if args.mode=='analyze':
        result=report(args.log,args.bank,args.warmup_windows,args.start_marker,args.capture)
    else:
        result=compare(json.loads(args.baseline.read_text()),json.loads(args.candidate.read_text()))
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2,allow_nan=False))
    print(args.output.resolve())


if __name__=='__main__':main()
