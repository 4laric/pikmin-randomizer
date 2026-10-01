"""Emit one verified course's native CollisionGrid chunk, not a playable MOD."""
import argparse
import hashlib
import json
from pathlib import Path

from experimental.pikmin2_surface_import import verify_bundle
from experimental.pikmin2_surface_grid import build_grid, encode_grid, decode_grid


def build(bundle, identity, output):
    verify_bundle(bundle, identity)
    if output.exists(): raise ValueError('Output already exists')
    geometry_path = bundle/'surface-geometry.json'
    geometry = json.loads(geometry_path.read_text())
    grid = build_grid(geometry['vertices'], geometry['triangles'])
    data = encode_grid(grid)
    decoded = decode_grid(data, len(geometry['triangles']))
    covered = {i for group in decoded['groups'] for i in group}
    if covered != set(range(len(geometry['triangles']))):
        raise ValueError('Missing source collision face')
    counts = [0 if i == -1 else len(decoded['groups'][i]) for i in decoded['cells']]
    topology = json.loads((bundle/'surface-topology.json').read_text())
    report = dict(schema=1, receipt_identity=identity,
                  source_geometry_sha256=hashlib.sha256(geometry_path.read_bytes()).hexdigest(),
                  grid_sha256=hashlib.sha256(data).hexdigest(), grid_bytes=len(data),
                  source_faces=len(covered), vertices=len(geometry['vertices']),
                  dimensions=[grid['nx'],grid['nz']], unique_groups=len(grid['groups']),
                  max_faces_per_cell=max(counts), mean_faces_per_cell=sum(counts)/len(counts),
                  all_faces_baseline_per_cell=len(geometry['triangles']),
                  broad_phase='triangle AABB intersect native64-unit cell with64-unit border',
                  source_face_indices_preserved=True, no_faces_deleted=True,
                  native_topology_approved=topology['native_conversion_approved'],
                  nonmanifold_edges=len(topology['nonmanifold_edges']),
                  terrain_usable_alone=False, native_runtime_tested=False,
                  remaining=['P1 multi-incident adjacency/traversal policy',
                             'Native water and complete render fidelity',
                             'Retail generators, carry routes and campaign persistence'])
    output.mkdir(parents=True)
    (output/'collision-grid.chunk').write_bytes(data)
    (output/'grid-report.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--bundle',type=Path,required=True)
    p.add_argument('--identity',required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    print(json.dumps(build(a.bundle.resolve(),a.identity,a.output.resolve()),indent=2))
