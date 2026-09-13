"""Mamuta native-binding evidence validators (batch 3, #221).

Validates production-session logs from the native-track binding (native
7faa644, root f9f0839) and material-fidelity profiles of the batch-1 pose
conversions. No P2 planting, population-cap or follower lifecycle claims:
those remain native dependencies.
"""
import json
import math
import re

EXPECTED_GENERATOR = '221001'
EXPECTED_CONTROL = '221002'
EXPECTED_NATIVE_TYPE = '24'  # P1 Miurin proxy, tekimgr.cpp tekiNames[24]
EXPECTED_BIRTH_XYZ = (-150.0, 30.0, 1850.0)
XYZ_TOLERANCE = 0.02

READY_RE = re.compile(
    r'P2_MAMUTA_READY generator=(\d+) native_type=(\d+) '
    r'xyz=([-\d.]+),([-\d.]+),([-\d.]+) P1_proxy_static_anchors_no_P2_planting')

# Poses installed by pikmin2_mamuta_install and accepted unchanged by the binding.
BOUND_POSES = ('miulin_wait.mod', 'miulin_dead.mod', 'miulin_attack1.mod')

# Converter policy limits material fidelity by construction; see
# experimental/pikmin2_convert.py write_model material handling.
EXPECTED_MATERIAL_POLICY = ('vertex color times identifiable UV0 diffuse texture '
                            '(first texture fallback); original TEV not reproduced')


def validate_session_log(text):
    """Production-session evidence: exact identity, Miurin load, zero GX desync."""
    rows = READY_RE.findall(text)
    if len(rows) != 1:
        raise ValueError('Expected exactly one Mamuta binding READY marker')
    generator, native_type, x, y, z = rows[0]
    if generator != EXPECTED_GENERATOR or native_type != EXPECTED_NATIVE_TYPE:
        raise ValueError('Binding identity mismatch')
    xyz = (float(x), float(y), float(z))
    if any(not math.isfinite(a) or abs(a - b) > XYZ_TOLERANCE
           for a, b in zip(xyz, EXPECTED_BIRTH_XYZ)):
        raise ValueError('Binding birth XYZ mismatch')
    if 'DESYNC' in text:
        raise ValueError('GX display list desync detected')
    for resource in ('dataDir/tekipara/miurin.bin', 'dataDir/tekis/miurin/miurin.mod',
                     'dataDir/tekis/miurin/miurin.anm', 'dataDir/tekikeys/miurin.key'):
        if resource not in text:
            raise ValueError(f'Missing native Miurin resource load: {resource}')
    return {'generator': int(generator), 'native_type': int(native_type),
            'birth_xyz': list(xyz), 'gx_desync': 0, 'scope':
            'P1 Miurin proxy with source static anchors; no P2 planting parity'}


def material_profile(conversion):
    """Material-fidelity profile of one converted pose (its .json sidecar)."""
    if conversion.get('textures') != 2 or conversion.get('shapes') != 2:
        raise ValueError('Unexpected Mamuta model texture/shape count')
    policy = conversion.get('material_policy', '')
    if policy != EXPECTED_MATERIAL_POLICY:
        raise ValueError('Unsupported material conversion policy')
    if conversion.get('discarded_attributes'):
        raise ValueError('Unexpected discarded attributes')
    if conversion.get('vertices', 0) <= 0 or conversion.get('triangles', 0) <= 0:
        raise ValueError('Degenerate converted geometry')
    bounds = conversion.get('bounds')
    if not bounds or len(bounds) != 6 or not all(map(math.isfinite, bounds)):
        raise ValueError('Invalid converted bounds')
    return {'textures': 2, 'shapes': 2, 'material_fidelity': 'partial',
            'policy': policy,
            'vertices': conversion['vertices'], 'triangles': conversion['triangles'],
            'finding': 'visible binding yes; body diffuse/TEV approximation; '
                       'ground contact not signed off (feet occluded in capture)'}


def installed_bytes_match(session_room, imported, metadata):
    """Prove a native session's installed poses are byte-identical to the import."""
    import hashlib
    from pathlib import Path
    session_room = Path(session_room)
    imported = Path(imported)
    by_file = {c['file']: c for c in metadata['clips']}
    result = {}
    for clip, index in (('wait.bca', 0), ('dead.bca', -1), ('attack1.bca', 0)):
        poses = by_file.get(clip, {}).get('poses', [])
        if not poses:
            raise ValueError(f'Missing converted clip {clip}')
        pose = poses[index]
        want = pose['sha256']
        got_path = session_room / f'miulin_{clip[:-4]}.mod'
        if not got_path.is_file():
            raise ValueError(f'Missing installed pose {got_path}')
        got = hashlib.sha256(got_path.read_bytes()).hexdigest()
        if got != want:
            raise ValueError(f'Installed pose hash mismatch: {got_path.name}')
        result[got_path.name] = got
    return result
