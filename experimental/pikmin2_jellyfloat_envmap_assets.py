"""Build a source-bound two-stage envmap MOD package for both Jellyfloats."""
import argparse
import hashlib
import json
from pathlib import Path

from experimental.pikmin2_kurage_envmap import prepare
from experimental.pikmin2_kurage_material_patch import SOURCES


FAMILIES = ('Kurage', 'OniKurage')
BASELINE_HEAD = '5e09abe1dd5f14cd8456e395d9b1107f5b327fca'
ENVMAP_ENGINE_HEAD = '92e5b37c6feeeb6163393927897a2e2c16666c8a'
ENGINE_OWNER_TASK_ID = '01a08d46-d7ee-7c11-b2e0-f853596d7346'


def sha_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_json(path):
    try:
        return json.loads(Path(path).read_text())
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError('Invalid manifest: '+str(path)) from error


def checked_inputs(assets, converted):
    assets = Path(assets).resolve(); converted = Path(converted).resolve()
    asset_manifest_path = assets/'manifest.json'; converted_manifest_path = converted/'manifest.json'
    asset_manifest = load_json(asset_manifest_path); converted_manifest = load_json(converted_manifest_path)
    if Path(converted_manifest.get('source', '')).resolve() != assets:
        raise ValueError('Converted manifest is not bound to the supplied extracted assets')
    result = []
    for species in FAMILIES:
        family = asset_manifest.get('families', {}).get(species, {})
        clips = converted_manifest.get('families', {}).get(species, {}).get('clips')
        model = assets/species/'enemy.bmd'
        expected = family.get('files', {}).get('enemy.bmd')
        actual = sha_file(model) if model.is_file() else None
        if actual != expected or SOURCES.get(actual) != species:
            raise ValueError('Unaudited '+species+' source model')
        if not isinstance(clips, list) or not clips:
            raise ValueError('No converted '+species+' clips')
        names = set()
        for clip in clips:
            name = clip.get('output') if isinstance(clip, dict) else None
            mod = converted/species/str(name)
            if not name or name in names or not name.endswith('.mod') or not mod.is_file():
                raise ValueError('Invalid '+species+' converted clip')
            names.add(name)
            result.append((species, family.get('enemy_id'), model, mod, clip))
    return asset_manifest_path, converted_manifest_path, result


def build(assets, converted, output, exporter=prepare):
    assets = Path(assets).resolve(); converted = Path(converted).resolve(); output = Path(output)
    asset_manifest_path, converted_manifest_path, inputs = checked_inputs(assets, converted)
    output.mkdir(parents=True, exist_ok=False)
    rows = []
    for species, enemy_id, model, mod, clip in inputs:
        destination = output/species/Path(clip['output']).stem
        report = exporter(model, mod, destination)
        patched = destination/'patched.mod'
        rows.append(dict(species=species, enemy_id=enemy_id, source_clip=clip['source'],
                         source_mod=clip['output'], frames=clip.get('frames'), source_mod_sha256=sha_file(mod),
                         model_sha256=sha_file(model), patched_mod=str(patched.relative_to(output)),
                         patched_mod_sha256=sha_file(patched), patch_report=str((destination/'patch.json').relative_to(output)),
                         material_report=report))
    manifest = dict(
        schema='pikmin2-jellyfloat-envmap-assets-v1',
        baseline_head=BASELINE_HEAD,
        envmap_engine_head=ENVMAP_ENGINE_HEAD,
        envmap_engine_owner_task_id=ENGINE_OWNER_TASK_ID,
        source_assets=str(assets), source_assets_manifest_sha256=sha_file(asset_manifest_path),
        source_iso_sha256=load_json(asset_manifest_path).get('source_iso_sha256'),
        source_revision=load_json(asset_manifest_path).get('source_revision'),
        source_converted=str(converted), source_converted_manifest_sha256=sha_file(converted_manifest_path),
        exporter='experimental.pikmin2_kurage_envmap.prepare',
        models=rows,
        runtime_artifact=False,
        full_material_fidelity=False,
        limitations=['Static source SRT and sampled geometry only.',
                     'Source lighting, BTK, and animated texture transforms are not translated.',
                     'This package has no native receiver, installer, build, or runtime validation.'])
    (output/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--assets', type=Path, required=True)
    parser.add_argument('--converted', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.assets, args.converted, args.output), indent=2))
