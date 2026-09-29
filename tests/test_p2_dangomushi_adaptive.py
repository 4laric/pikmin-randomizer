"""#897 DangoMushi asset fixes: adaptive key poses, pose-frame bank rows,
TEV-register body colour and the staged retail carcass row.

Engine-free: synthetic vertex tracks and bank text only (no disc needed).
"""
import math

import pytest

from experimental.pikmin2_dangomushi_assets import (
    ADAPTIVE_FLOOR,
    adaptive_frames,
    carcass_row,
)
from experimental.pikmin2_dangomushi_content import (
    CARCASS_HEADER,
    _merge_bank,
    _parse_bank,
    _render_bank,
    carcass_text,
)
from experimental.pikmin2_staging import StagingError


def _rolling_ball(frames=101, radius=60.0, turns=2.0):
    """One vertex on a ball spinning `turns` revolutions: linear blending of
    far-apart samples collapses it toward the axis (the r4 'ball' failure)."""
    track = []
    for f in range(frames):
        a = 2 * math.pi * turns * f / (frames - 1)
        track.append([(radius * math.sin(a), radius * math.cos(a), 0.0)])
    return track


def _max_blend_error(track, keys):
    worst = 0.0
    for i, j in zip(keys, keys[1:]):
        for k in range(i + 1, j):
            w = (k - i) / (j - i)
            a, b, c = track[i][0], track[j][0], track[k][0]
            d = math.sqrt(sum(((1 - w) * a[q] + w * b[q] - c[q]) ** 2 for q in range(3)))
            worst = max(worst, d)
    return worst


def test_adaptive_keys_bound_the_blend_error_where_uniform_fails():
    track = _rolling_ball()
    uniform = [round(i * 100 / 2) for i in range(3)]          # the old 3-pose bank
    assert _max_blend_error(track, uniform) > 50.0
    keys = adaptive_frames(track, 40)
    assert keys[0] == 0 and keys[-1] == 100 and keys == sorted(set(keys))
    assert len(keys) <= 40
    assert _max_blend_error(track, keys) <= ADAPTIVE_FLOOR


def test_adaptive_keys_keep_event_anchors_and_skip_static_clips():
    static = [[(1.0, 2.0, 3.0)] for _ in range(40)]
    assert adaptive_frames(static, 40, anchors=[13, 39, 99]) == [0, 13, 39]
    with pytest.raises(ValueError):
        adaptive_frames(static, 2, anchors=[5, 9])


def test_bank_rows_carry_pose_frames_and_merge_with_snagret_rows():
    dango = [('attack', 140, '23:4', 3, 'converted', (0, 70, 139)),
             ('wait', 40, '-', 2, 'converted')]
    text = _merge_bank(None, 'DangoMushi', 94, dango)
    assert b'clip DangoMushi attack 140 23:4 poses 3 status converted frames 0,70,139' in text
    snake = [('wait1', 30, '-', 2, 'converted')]
    merged = _merge_bank(text, 'SnakeCrow', 34, snake)
    blocks = {species: clips for species, _identity, clips in _parse_bank(merged)}
    assert blocks['DangoMushi'] == dango and blocks['SnakeCrow'] == snake
    assert _render_bank(_parse_bank(merged)) == merged
    # Restaging the same rows is idempotent; a changed frame list refuses.
    assert _merge_bank(merged, 'DangoMushi', 94, dango) == merged
    with pytest.raises(StagingError):
        _merge_bank(merged, 'DangoMushi', 94,
                    [('attack', 140, '23:4', 3, 'converted', (0, 71, 139))] + dango[1:])


@pytest.mark.parametrize('frames', [(0, 70), (1, 70, 139), (0, 70, 138), (0, 70, 70)])
def test_bank_rejects_frame_lists_the_native_parser_refuses(frames):
    rows = [('attack', 140, '-', len(frames), 'converted', frames)]
    with pytest.raises(StagingError):
        _merge_bank(None, 'DangoMushi', 94, rows)


CARCASS = """{
\tname\t\t\tKingChappy
\tmin\t\t\t20
\tmax\t\t\t30
\tpikicountmax\t\t15
\tpikicountmin\t\t15
\tmoney\t\t\t15
\tend
}
{
\tname\t\t\tDangoMushi
\tarchive\t\t\tnull
\tradius\t\t\t45
\tmin\t\t\t20
\tmax\t\t\t30
\tpikicountmax\t\t30
\tpikicountmin\t\t30
\tdynamics\t\tlod
\tmoney\t\t\t15
\tend
}
"""


def test_carcass_row_reads_the_dangomushi_block_and_stages_the_sidecar():
    row = carcass_row(CARCASS.encode('shift_jis'))
    assert (row['min'], row['max'], row['pikicount'], row['money']) == (20, 30, 30, 15)
    text = carcass_text({'carcass': row})
    assert text == f'{CARCASS_HEADER} 20 30 30\n'.encode('ascii')
    assert carcass_text({}) is None
    with pytest.raises(StagingError):
        carcass_text({'carcass': dict(row, max=10)})
    with pytest.raises(ValueError):
        carcass_row(CARCASS.replace('DangoMushi', 'Other'))
