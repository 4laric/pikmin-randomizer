"""Lane-09 slice 2: a second consumer of the corrected specular half-vector path.

The native GL specular branch (pc_port/gl/pc_gfx.cpp) computes the ``N.H``
ratio-of-quadratics highlight only when a material's color channel 1 has
attnFn == GX_AF_SPEC. dgxGraphics.cpp sets channel 1 to GX_AF_SPEC whenever the
material lighting control carries ``LightingControlFlags::EnableSpecular``
(``1 << 1`` in include/PVW.h), and it binds light mask 0x80 (light 7) whose
direction field holds the half-vector written by ``pc_gfx_init_specular_dir``
via ``p2specular::halfVector`` (pc_port/pc_p2_specular_dir.h).

The Frog / Bulblax material audits restore that specular channel with control
0x93 (diffuse CLAMP + specular SIGN, register sources): ``0x93 & 0x2`` is set,
so apart from the Queen's prepared two-stage path a second, independently
profiled family material flows through the same corrected uniform path. This
module locks that criterion and the runtime RENDER marker that proves it.
"""
import json
import re

# The audited "lit" control used by the Frog material profile and the Bulblax
# KingChappy/Baby material profiles (experimental/pikmin2_frog_material_profile.py,
# experimental/pikmin2_bulblax_material.py). Its bit 1 is EnableSpecular.
LIT_CONTROL = 0x93
VERTEX_COLOR_FLAG = 0x1800
ENABLE_SPECULAR_BIT = 1 << 1  # LightingControlFlags::EnableSpecular (include/PVW.h)

MARKER = 'FROG_SPECULAR_RENDER'
WINDOW_MARKER = 'FROG_SPECULAR_WINDOW'
PASS_LINE = 'PASS ' + MARKER

_INT = re.compile(r'(?P<key>[a-zA-Z_][a-zA-Z0-9_]*)=(?P<value>-?[0-9]+)')
_HEX = re.compile(r'control=0x(?P<value>[0-9a-fA-F]+)')
_FLAGS = re.compile(r'flags=(?P<value>SHOWN|HIDDEN)')


def specular_criterion(control):
    """True when a PVW lighting-control word selects the specular COLOR1 channel.

    Mirrors the native guard ``mLightingInfo.mCtrlFlag & LightingControlFlags::
    EnableSpecular`` in src/sysDolphin/dgxGraphics.cpp (thence GXSetChanCtrl
    GX_COLOR1 with GX_AF_SPEC). Only the enable bit matters; the diffuse/ambient
    source bits do not affect whether the half-vector uniform path runs.
    """
    if not isinstance(control, int) or control < 0:
        raise ValueError('Expected a non-negative lighting control word')
    return bool(control & ENABLE_SPECULAR_BIT)


def _line(log, prefix):
    for line in log.splitlines():
        if line.strip().startswith(prefix + ' ') or line.strip() == prefix:
            return line.strip()
    raise ValueError('%s marker stripped from the captured log' % prefix)


def evidence(log):
    """Validate the four real Frog specular markers from the room fixture.

    Window visibility (SHOWN, not HIDDEN), the readback viewport and the real
    ``control`` (whose EnableSpecular bit is re-checked), and the renderer's own
    counters (``specular_dir_calls``/``specular_channel_draws``) must all be
    present and positive; ``replay_equal`` must be 1. A stripped, hidden, or
    zero-count marker flips the gate.
    """
    if not isinstance(log, str):
        raise ValueError('Expected a captured log text')

    window = _line(log, WINDOW_MARKER)
    wflags = _FLAGS.search(window)
    if not wflags:
        raise ValueError('window marker does not report the real SDL flag (SHOWN or HIDDEN)')
    if wflags.group('value') != 'SHOWN':
        raise ValueError('window is not visible (flags=HIDDEN); the acceptance window must be SHOWN')
    wfield = {m.group('key'): int(m.group('value')) for m in _INT.finditer(window)}
    if wfield.get('w') != 960 or wfield.get('h') != 540 or wfield.get('centered') != 1:
        raise ValueError('window is not the centred 960x540 acceptance window')

    render = _line(log, MARKER)
    fields = {m.group('key'): int(m.group('value')) for m in _INT.finditer(render)}
    control = _HEX.search(render)
    if not control:
        raise ValueError('RENDER marker missing the real control word')
    control = int(control.group('value'), 16)
    missing = [k for k in ('viewport_w', 'viewport_h', 'specular_dir_calls',
                           'specular_channel_draws', 'specular_draw_delta', 'replay_equal')
               if k not in fields]
    if missing:
        raise ValueError('RENDER marker missing fields: ' + ', '.join(missing))
    if fields['viewport_w'] <= 0 or fields['viewport_h'] <= 0:
        raise ValueError('RENDER marker reports no readback viewport')
    if fields['specular_dir_calls'] < 1:
        raise ValueError('ordinary draw did not reach pc_gfx_init_specular_dir')
    if fields['specular_channel_draws'] < 1:
        raise ValueError('ordinary draw did not activate the specular channel')
    if fields['specular_draw_delta'] < 1:
        raise ValueError('single ordinary draw did not activate the specular channel (specular_draw_delta)')
    if fields['replay_equal'] != 1:
        raise ValueError('RENDER marker replay_equal is not a verified compare')
    if not specular_criterion(control):
        raise ValueError('RENDER marker control does not select the specular channel')
    if PASS_LINE not in log.splitlines():
        raise ValueError('RENDER PASS line stripped from the captured log')
    return dict(fields, control=control)

if __name__ == '__main__':
    import sys
    print(json.dumps({'lit_control_specular': specular_criterion(LIT_CONTROL),
                      'baby_control_specular': specular_criterion(LIT_CONTROL | VERTEX_COLOR_FLAG),
                      'unlit_specular': specular_criterion(0),
                      'vertex_flag_only_specular': specular_criterion(VERTEX_COLOR_FLAG)}))
