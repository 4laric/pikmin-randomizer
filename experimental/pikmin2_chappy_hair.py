"""Static bristle hair for the Hairy Bulborb (YellowChappy, source 43).

The retail Hairy Bulborb has no hair geometry in ``enemy.bmd`` (the model is
the shared Chappy body, two shapes, plus a texture swap). Its hair is a
particle effect: ``YellowChappy::Obj::setupEffect`` creates
``efx::TKechappyTest`` (JPA particles 0x283/0x284/0x285, "KechappyTest_1..3")
on the ``body`` joint, ``doUpdateCommon`` fades its global alpha, and
``efx::TKechappyOff`` (``PID_KechappyOff``) sheds it below half health. The
pose converter only bakes model shapes, so the baked poses had a bare body
("hairy bulborb no hair").

The native port has no JPA runtime. This module approximates the effect in
the baked poses: each pose gets one extra untextured shape of thin crossed
bristle spikes rooted on body vertices and pointing along their normals
(JPA shape type 3, directional, colours 0xe7/0xc8/0xff grey-white in the
0x283/0x284/0x285 base-shape blocks). It is an approximation, not the
retail emitter: no per-frame bristle/vibration/length animation
(``EffectAnimator``), no alpha fade and no shed-on-half-health.
Deterministic: roots are picked by vertex index, so every pose of a bank has
the same topology.
"""

import math

HAIR_SPECIES = ('YellowChappy',)
HAIR_RGBA = (236, 232, 214, 255)
STRAND_STRIDE = 2      # every second body vertex roots a strand
STRAND_LENGTH = 7.0    # model units; the adult Bulborb body is ~70 wide, ~85 tall
STRAND_WIDTH = 1.4
MIN_NORMAL_Y = -0.35   # skip the underside


def _norm(v):
    n = math.sqrt(sum(x * x for x in v))
    return tuple(x / n for x in v) if n > 1e-9 else None


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def add_hair(decoded):
    """Return ``decoded`` with one extra bristle shape appended."""
    b, arrays, shapes, mats = decoded
    if 10 not in arrays or not shapes:
        raise ValueError('hair needs normals')
    body = max(range(len(shapes)), key=lambda i: len(shapes[i]))
    roots = sorted({(v[9], v[10]) for tri in shapes[body] for v in tri if 10 in v})
    positions, normals = arrays[9], arrays[10]
    tris = []
    for pi, ni in roots[::STRAND_STRIDE]:
        n = _norm(normals[ni])
        if n is None or n[1] < MIN_NORMAL_Y:
            continue
        p = positions[pi]
        tip = tuple(p[k] + n[k] * STRAND_LENGTH for k in range(3))
        t = _norm(_cross(n, (0.0, 1.0, 0.0)) if abs(n[1]) < 0.95 else _cross(n, (1.0, 0.0, 0.0)))
        s = _cross(n, t)
        for side in (t, s):
            base = [tuple(p[k] - side[k] * STRAND_WIDTH * 0.5 for k in range(3)),
                    tuple(p[k] + side[k] * STRAND_WIDTH * 0.5 for k in range(3)),
                    tip]
            tri = []
            for point in base:
                positions.append(point)
                normals.append(n)
                tri.append({9: len(positions) - 1, 10: len(normals) - 1})
            tris.append(tri)
    if not tris:
        raise ValueError('no hair strands placed')
    index = len(shapes)
    shapes.append(tris)
    mats.append(-1)
    b['_render_states'].append(b['_render_states'][body])
    b['_source_lighting'].append(dict(lit=True, color_vertex=False, alpha_vertex=False, rgba=HAIR_RGBA))
    b['_alpha_stages'].append(None)
    b['_draw_order'].append(index)
    return b, arrays, shapes, mats
