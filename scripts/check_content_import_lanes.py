"""Validate the exhaustive preparatory content-lane plan; never dispatch work."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from experimental.levels import LEVELS


class InvalidPlan(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise InvalidPlan(message)


def text(value):
    return isinstance(value, str) and bool(value.strip())


def strings(value, label):
    require(isinstance(value, list) and value and all(text(v) for v in value), label + ' must be nonempty strings')
    require(len(value) == len(set(value)), label + ' contains duplicates')


def same(left, right):
    return json.dumps(left, sort_keys=True, allow_nan=False) == json.dumps(right, sort_keys=True, allow_nan=False)


def canonical_path(value):
    require(text(value) and '\\' not in value and ':' not in value, 'Owned path must be repository-relative')
    path = PurePosixPath(value)
    require(not path.is_absolute() and '..' not in path.parts and str(path) == value, 'Noncanonical owned path')
    return tuple(p.casefold() for p in path.parts)


def floor_count(floors):
    require(isinstance(floors, list) and floors, 'Missing cave floor definitions')
    covered = set()
    for floor in floors:
        require(isinstance(floor, dict), 'Invalid cave floor')
        first, last = floor.get('first'), floor.get('last')
        require(type(first) is int and type(last) is int and 1 <= first <= last <= 128, 'Invalid floor range')
        selected = set(range(first, last + 1))
        require(not covered.intersection(selected), 'Overlapping cave floor ranges')
        covered.update(selected)
    require(covered == set(range(1, max(covered) + 1)), 'Cave floor gap')
    return len(covered)


def validate_plan(plan, inventory, inventory_sha256):
    require(isinstance(plan, dict) and type(plan.get('schema')) is int and plan['schema'] == 1, 'Plan schema must be 1')
    require(set(plan) == {'schema', 'parent_issue', 'policy', 'inventory', 'inventory_sha256', 'limits', 'exclusions', 'lanes'}, 'Unexpected or missing plan fields')
    require(type(plan['parent_issue']) is int and plan['parent_issue'] > 0, 'Parent issue required')
    require(plan['policy'] == 'existing > expansion > idle', 'Existing work must precede expansion and idle')
    require(plan['inventory'] == 'docs/PIKMIN2_CONTENT_INVENTORY.json', 'Unexpected canonical inventory')
    require(isinstance(inventory_sha256, str) and re.fullmatch('[0-9a-f]{64}', inventory_sha256) and
            plan['inventory_sha256'] == inventory_sha256, 'Canonical inventory hash mismatch')
    require(same(plan['limits'], {'ram_high': 90, 'ram_low': 87, 'max_heavy_builds': 2}), 'Resource budgets changed')
    strings(plan['exclusions'], 'Exclusions')
    require(isinstance(inventory, dict) and inventory.get('schema') == 'p2-content-roadmap-1', 'Unknown source inventory schema')
    expected = {}
    for category, records, id_key in (
            ('p2-cave', inventory['story_caves'], 'id'),
            ('p2-overworld', inventory['surfaces'], 'id'),
            ('p2-challenge', inventory['challenge']['stages'], 'cave_id')):
        for item in records:
            key = (category, item[id_key])
            require(key not in expected, 'Duplicate source in canonical inventory')
            expected[key] = item
    for level in LEVELS:
        if level.layout == 'challenge':
            expected[('p1-challenge', level.key.split(':')[1])] = level
    counts = Counter(category for category, _ in expected)
    require(counts == {'p2-cave': 14, 'p2-overworld': 4, 'p2-challenge': 30, 'p1-challenge': 5}, 'Canonical source counts changed')
    lanes = plan['lanes']
    require(isinstance(lanes, list) and len(lanes) == 53, 'Exactly 53 content lanes required')
    seen_sources, seen_lanes, seen_issues, seen_paths = set(), set(), set(), []
    totals = {'p2-cave': 0, 'p2-challenge': 0}
    fields = {'lane', 'category', 'source_id', 'label', 'issue', 'work_class', 'state', 'owner',
              'source', 'source_sha256', 'status_basis', 'details', 'preparation_dependencies',
              'runtime_dependencies', 'owned_files', 'shared_files_policy', 'phases', 'acceptance', 'dispatch'}
    for lane in lanes:
        require(isinstance(lane, dict) and fields <= set(lane) <= fields | {'parent_issue'}, 'Unexpected or missing lane fields; completion claims are prohibited')
        key = (lane['category'], lane['source_id'])
        require(key in expected and key not in seen_sources, 'Unknown or duplicate source identity: ' + str(key))
        seen_sources.add(key)
        require(isinstance(lane['lane'], str) and re.fullmatch('[a-z0-9][a-z0-9_-]*', lane['lane']) and
                lane['lane'] not in seen_lanes, 'Invalid or duplicate lane ID')
        seen_lanes.add(lane['lane'])
        issue = lane['issue']
        require(type(issue) is int and issue > 0 and issue not in seen_issues, 'Invalid or duplicate issue claim')
        seen_issues.add(issue)
        require(lane['work_class'] == 'expansion' and lane['state'] == 'planned', 'Plan must remain expansion work, not completed runtime')
        for name in ('label', 'owner', 'status_basis', 'shared_files_policy', 'dispatch'):
            require(text(lane[name]), name + ' required')
        for name in ('preparation_dependencies', 'acceptance', 'owned_files'):
            strings(lane[name], name)
        deps = lane['runtime_dependencies']
        require(isinstance(deps, list) and deps and all(type(v) is int and v > 0 for v in deps) and
                len(deps) == len(set(deps)) and issue not in deps, 'Invalid runtime dependencies')
        for name in lane['owned_files']:
            parts = canonical_path(name)
            require(not any(parts[:len(other)] == other or other[:len(parts)] == parts for other in seen_paths), 'Owned paths overlap')
            seen_paths.append(parts)
        phases = lane['phases']
        require(isinstance(phases, list) and len(phases) == 3, 'Exactly P0/P1/P2 phases required')
        for phase, phase_id in zip(phases, ('P0', 'P1', 'P2')):
            require(isinstance(phase, dict) and set(phase) == {'id', 'name', 'ready', 'acceptance'} and
                    phase['id'] == phase_id and text(phase['name']) and type(phase['ready']) is bool, 'Invalid phase')
            strings(phase['acceptance'], 'Phase acceptance')
            require(phase_id == 'P0' or phase['ready'] is False, 'Runtime phases cannot be marked ready by this plan')
        item = expected[key]
        category = lane['category']
        details = lane['details']
        require(isinstance(details, dict), 'Source details required')
        if category == 'p2-cave':
            count = floor_count(item['floors'])
            require(same(details, {'floors': item['floors'], 'floor_count': count}), 'Cave source details differ from canonical inventory')
            require(issue == item['issue'], 'Existing cave issue must be reused')
            source = item['source']
            totals[category] += count
        elif category == 'p2-overworld':
            require(set(details) == {'course', 'required_inventory'} and details['course'] == item['id'], 'Surface source course differs')
            strings(details['required_inventory'], 'Surface inventory obligations')
            require(issue == item['issue'] and lane['label'] == item['name'], 'Existing surface identity/issue must be reused')
            source = item['source']
        elif category == 'p2-challenge':
            require(same(details, item), 'Challenge source details differ from canonical inventory')
            require(lane.get('parent_issue') == item['issue'], 'Challenge content parent differs')
            source = item['cave_path']
            totals[category] += item['floors']
        else:
            require(set(details) == {'level_key', 'native_area_id', 'stage_info_index', 'tracks'} and
                    details['level_key'] == item.key and type(details['native_area_id']) is int and
                    details['native_area_id'] == item.area_id and type(details['stage_info_index']) is int and
                    details['stage_info_index'] == 16 + item.area_id, 'P1 Challenge destination identity differs')
            strings(details['tracks'], 'P1 Challenge tracks')
            require({52, 100} <= set(deps) and lane.get('parent_issue') == 52, 'Separate P1 Challenge/story tracks required')
            source = item.stage_file
        require(lane['source'] == source, 'Source path differs from canonical inventory')
        require(lane['source_sha256'] == inventory.get('source_sha256', {}).get(source), 'Source hash differs; absent source hashes must stay unknown')
    require(seen_sources == set(expected), 'Missing source lanes')
    require(totals == {'p2-cave': 105, 'p2-challenge': 59}, 'Canonical floor totals differ')
    return dict(lanes=len(lanes), categories=dict(counts), floors=totals)


def read_json(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, 'Duplicate JSON object key: ' + key)
            result[key] = value
        return result
    return json.loads(path.read_text(encoding='utf-8-sig'), object_pairs_hook=unique,
                      parse_constant=lambda value: (_ for _ in ()).throw(InvalidPlan('Nonfinite JSON number: ' + value)))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, default=ROOT / 'docs/PIKMIN_CONTENT_IMPORT_LANES.json')
    parser.add_argument('--inventory', type=Path, default=ROOT / 'docs/PIKMIN2_CONTENT_INVENTORY.json')
    args = parser.parse_args(argv)
    try:
        result = validate_plan(read_json(args.plan), read_json(args.inventory), hashlib.sha256(args.inventory.read_bytes()).hexdigest())
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print('FAIL: ' + str(exc), file=sys.stderr)
        return 1
    print('PASS: 53 lanes (14 P2 caves / 105 floors, 4 P2 overworld, 30 P2 Challenge / 59 floors, 5 P1 Challenge); source pins and ownership validated')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
