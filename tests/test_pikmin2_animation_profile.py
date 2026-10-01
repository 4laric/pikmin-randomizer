import json
from pathlib import Path
import sys

import pytest

from experimental.pikmin2_animation_profile import capture_command, compare, parse_log, report


def perf(ms):
    return f'[PERF] {1000/ms:.1f} fps {ms:.2f} ms | 45 draws (50 source, 4 fast) 200 verts 1 DL (0.01 MiB) 0.00 tex uploads/frame\n'


def test_window_means_are_not_frame_percentiles_or_arithmetic_fps():
    parsed=parse_log(perf(100)+perf(10)+perf(30))
    assert parsed['warmup_windows_discarded']==1
    assert parsed['presentation']['mean_frame_ms']==20
    assert parsed['presentation']['effective_fps_from_window_means']==50
    assert parsed['presentation']['per_frame_p95_ms'] is None
    assert parsed['presentation']['slowest_window_mean_ms']==30


def test_tick_counts_and_time_units_remain_separate():
    text='''[PC tick] last 500 ticks, budget 16.7 ms
           tick             mean 20.00 p50 15.00 p95 30.00 p99 80.00 worst 100.00
             gl:draws/frame mean 60.00 p50 50.00 p95 70.00 p99 80.00 worst 100.00
[PC tick] last 700 ticks, budget 16.7 ms
           tick             mean 22.00 p50 16.00 p95 35.00 p99 90.00 worst 110.00
'''
    parsed=parse_log(text)
    assert parsed['last_tick_window']['samples']==700
    assert parsed['last_tick_window']['regions']['tick']['p99']==90
    parsed=parse_log(text.split('[PC tick] last 700')[0])
    assert parsed['last_tick_window']['regions']['gl:draws/frame']['unit']=='count_or_percent'
    assert parsed['last_tick_window']['regions']['tick']['unit']=='ms'


def test_empty_partial_malformed_and_missing_marker_are_explicit():
    assert parse_log('')['presentation'] is None
    assert parse_log(perf(30),start_marker='MISSING')['start_marker_found'] is False
    text=perf(10)+'P2_SNOW_BANK poses=120 mod_bytes=NaN\n[PERF] nan fps -1 ms\n'
    parsed=parse_log(text)
    assert parsed['malformed_line_numbers']==[2,3]
    assert parsed['bank_loads']==[]
    assert parsed['presentation'] is None
    with pytest.raises(ValueError):parse_log('',-1)


def test_marker_and_warmup_exclude_startup():
    parsed=parse_log(perf(500)+'READY\n'+perf(200)+perf(20),1,'READY')
    assert parsed['perf_windows_seen']==2
    assert parsed['presentation']['mean_frame_ms']==20


def test_draw_markers_do_not_confuse_loaded_assets_with_visible_actors():
    parsed=parse_log('P2_SNOW_DRAW corpse=0\nP2_SNOW_DRAW corpse=1\n')
    assert parsed['snow_draw']=={'live_observed':True,'corpse_observed':True}
    assert parsed['presentation'] is None


def test_gpu_texture_and_load_metrics_have_independent_sources(tmp_path):
    log=tmp_path/'native.log'
    log.write_text('''P2_SNOW_BANK poses=120 mod_bytes=1920000 texture_attach_calls=1 load_seconds=0.125 load_budget_seconds=5 budget_exceeded=0
[PC Port] Textures: 250 live, 80 MB (peak 90 MB), 1000 made / 750 freed
[PERF GPU] scene 3.20 ms blit 0.20 ms (120 async samples)
''')
    result=report(log)
    assert result['runtime']['bank_loads'][0]['load_seconds']==.125
    assert result['runtime']['last_gpu_window']['scene_ms']==3.2
    assert result['runtime']['texture_memory']['maximum_reported_mib']==80
    assert 'total process RAM' in result['unmeasured']
    assert 'presentation FPS/frame time' in result['unmeasured']
    assert result['bank_identity_matches'] is None
    compared=compare(result,result)
    assert compared['comparison']['bank_load_seconds']['delta']==0
    assert compared['comparison']['effective_fps']['delta'] is None


def test_capture_runs_owned_explicit_command_and_enables_existing_profiler(tmp_path):
    code="import os;print('[fixture]',os.environ['PIKMIN_PERF_STATS'],os.environ['PIKMIN_TICK_STATS'])"
    metadata=capture_command([sys.executable,'-c',code],tmp_path,tmp_path/'capture',5)
    assert metadata['exit_code']==0 and metadata['timed_out'] is False
    assert '[fixture] 1 1' in (tmp_path/'capture/native.log').read_text()
    assert json.loads((tmp_path/'capture/capture.json').read_text())['elapsed_seconds']>0
    with pytest.raises(FileExistsError):capture_command([sys.executable],tmp_path,tmp_path/'capture',1)


def test_capture_timeout_is_recorded_not_a_successful_gameplay_claim(tmp_path):
    metadata=capture_command([sys.executable,'-c','import time;time.sleep(10)'],tmp_path,tmp_path/'capture',.1)
    assert metadata['timed_out'] is True
