"""Validated transition anchors and optional disc-sourced static visuals."""
import math
import hashlib
import json


def read_visuals(directory):
    """Validate and freeze the optional source-model bundle before a save opens."""
    if directory is None:
        return {}
    manifest_bytes = (directory/'transition-assets.json').read_bytes()
    manifest = json.loads(manifest_bytes)
    if not isinstance(manifest, dict) or manifest.get('schema') != 1:
        raise ValueError('Invalid transition visual manifest')
    models = manifest.get('models')
    if not isinstance(models, dict) or set(models) != {'hole', 'geyser'}:
        raise ValueError('Both transition models are required')
    result = {'transition-assets.json': manifest_bytes}
    for kind in ('hole', 'geyser'):
        model = models[kind]
        name = f'cave_{kind}.mod'
        if (not isinstance(model, dict) or model.get('file') != name
                or model.get('placement') != dict(y_offset=0, scale=1, yaw_degrees=0)):
            raise ValueError('Unsupported transition model or transform')
        data = (directory/name).read_bytes()
        if not data or hashlib.sha256(data).hexdigest() != model.get('sha256'):
            raise ValueError('Transition model hash mismatch')
        result[name] = data
    return result


def install_visuals(visuals, run, floor):
    if not visuals:
        return
    if floor not in (1, 2):
        raise ValueError('Invalid transition floor')
    kind = 'hole' if floor == 1 else 'geyser'
    target = run/'assets/dataDir/courses/pikmin2room'/f'cave_{kind}.mod'
    if not target.resolve().is_relative_to(run.resolve()) or target.exists():
        raise ValueError('Transition model target is not a new private file')
    target.write_bytes(visuals[f'cave_{kind}.mod'])
    (run/'p2-cave-visual.txt').write_text(f'P2_CAVE_VISUAL_1 {kind}\n', encoding='ascii')


def read_transitions(directory):
    """Read once, validate before launch, then hash and stage the same bytes."""
    if directory is None:
        return {}
    result = {}
    for floor, kind in ((1, 'hole'), (2, 'geyser')):
        data = (directory / f'floor{floor}.txt').read_bytes()
        words = data.decode('ascii').split()
        if len(words) != 6 or words[:2] != ['P2_CAVE_TRANSITION_1', kind]:
            raise ValueError(f'Invalid floor {floor} transition header')
        try:
            x, y, z, radius = map(float, words[2:])
        except ValueError as error:
            raise ValueError(f'Invalid floor {floor} transition coordinates') from error
        if (not all(math.isfinite(n) for n in (x, y, z, radius))
                or any(abs(n) > 100000 for n in (x, y, z)) or not 20 <= radius <= 150):
            raise ValueError(f'Invalid floor {floor} transition bounds')
        result[floor] = data
    return result
