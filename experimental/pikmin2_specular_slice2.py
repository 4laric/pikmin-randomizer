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
PASS_LINE = 'PASS ' + MARKER

_INT = re.compile(r'(?P<key>[a-zA-Z_][a-zA-Z0-9_]*)=(?P<value>-?[0-9]+)')


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


def evidence(log):
    """Validate a Frog specular RENDER marker collected from the room fixture.

    Requires one `FROG_SPECULAR_RENDER <k=v>...` line whose specular and visible
    channel counts are strictly positive, and whose replay_equal is 1, followed by
    the `PASS FROG_SPECULAR_RENDER` line. replay_equal is only accepted alongside
    positive specular/visible counts, so a naked literal without a real captured
    frame compare cannot satisfy this gate.
    """
    if not isinstance(log, str):
        raise ValueError('Expected a captured log text')
    marker_line = None
    for line in log.splitlines():
        if line.strip().startswith(MARKER + ' ') or line.strip() == MARKER:
            marker_line = line.strip()
            break
    if marker_line is None:
        raise ValueError('RENDER marker stripped from the captured log')
    fields = {m.group('key'): int(m.group('value')) for m in _INT.finditer(marker_line)}
    required = ('visible_channels', 'specular_channels', 'replay_equal')
    missing = [k for k in required if k not in fields]
    if missing:
        raise ValueError('RENDER marker missing fields: ' + ', '.join(missing))
    if fields['specular_channels'] <= 0:
        raise ValueError('RENDER marker reports no specular contribution')
    if fields['visible_channels'] <= 0:
        raise ValueError('RENDER marker reports no visible pixels for a real compare')
    if fields['replay_equal'] != 1:
        raise ValueError('RENDER marker replay_equal is not a verified compare')
    if PASS_LINE not in log.splitlines():
        raise ValueError('RENDER PASS line stripped from the captured log')
    return fields


if __name__ == '__main__':
    import sys
    print(json.dumps({'lit_control_specular': specular_criterion(LIT_CONTROL),
                      'baby_control_specular': specular_criterion(LIT_CONTROL | VERTEX_COLOR_FLAG),
                      'unlit_specular': specular_criterion(0),
                      'vertex_flag_only_specular': specular_criterion(VERTEX_COLOR_FLAG)}))
