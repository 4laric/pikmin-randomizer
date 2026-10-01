"""Opt-in local waypoint grounding and source-preserving Beasts navigation audits."""
import copy
import math

from experimental.pikmin2_cave import route_audit
from experimental.pikmin2_collision import ground_height, route_ini

POLICY = 'P2_BEASTS_LOCAL_NAVIGATION_1'


def interpret(room, definition):
    """Zero-rotation isolated room only; no inverse links or actor relocation."""
    route_ini(room['routes'])  # Reject missing destinations and duplicate IDs.
    ids = {p['id'] for p in room['routes']}
    if not ids or any(type(i) is not int or i < 0 for i in ids):
        raise ValueError('Invalid route IDs')
    doors = [d['waypoint'] for d in definition['doors']]
    if not doors or any(type(i) is not int or i not in ids for i in doors):
        raise ValueError('Invalid door waypoint')
    result = copy.deepcopy(room)
    changes = []
    for point in result['routes']:
        if len(point['position']) != 3 or not all(math.isfinite(v) for v in point['position']):
            raise ValueError('Invalid waypoint coordinates')
        x, y, z = point['position']
        # RoomMapMgr materialization uses y=0 at doors and getMinY elsewhere.
        ground = ground_height(room['vertices'], room['triangles'], x, z)
        if ground is None:
            raise ValueError('Waypoint has no offline floor support')
        target = 0.0 if point['id'] in doors else ground
        point['position'][1] = target
        changes.append(dict(waypoint=point['id'], source_y=y, floor_y=ground,
                            staged_y=target, is_door=point['id'] in doors))
    audit = route_audit(room)
    door_routes = [p for p in audit if p['destination'] in doors]
    spawns = []
    for i, spawn in enumerate(room['spawns']):
        x, y, z = spawn['position']
        floor = ground_height(room['vertices'], room['triangles'], x, z)
        spawns.append(dict(source_slot=i, source_position=list(spawn['position']), source_type=spawn['type'],
                           floor_y=floor, has_floor_support=floor is not None,
                           delta_y=None if floor is None else floor-y,
                           exact_height_match=floor is not None and abs(floor-y) <= .1,
                           source_position_changed=False, actor_birth_position_selected=False))
    return result, dict(policy=POLICY, source_edges_preserved=True, inverse_links_added=False,
        all_pairs_connected=not any(p['unreachable_sources'] for p in audit),
        all_sources_reach_every_door=not any(p['unreachable_sources'] for p in door_routes),
        door_route_audit=door_routes, source_route_audit=audit, waypoint_grounding=changes,
        spawn_height_audit=spawns, native_validated=False,
        limitations=['Offline floor queries are not native getCurrTri validation.',
                     'Raw from-link graph retained; P2 inverse links require linkable and TwoWayPathing.',
                     'Door reachability is graph evidence, not physical carrying or a capped-door exit.',
                     'Spawn center support does not certify radius/footprint or item cylinder offset.'])
