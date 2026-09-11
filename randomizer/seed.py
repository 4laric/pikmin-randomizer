"""Strict, deterministic identity-placement milestone; no unproven relocation."""
import hashlib
import json
from collections import Counter
from .catalog import (GAME, NAMES, PART_IDS, LOCATION_IDS, UNLOCKS,
                      REPAIR, REPAIR_COUNT, CHECK_REQUIREMENTS, active_names, ALL_LOCATION_IDS,
                      can_reach, can_reach_manifest, progression_pool, item_pool, START_AREAS, ALL_AREA_LOCATION_IDS, ALL_PART_IDS, COLLECTION_LOCATION_IDS, PERMANENT_LOCATION_IDS, MODERN_LOCATION_IDS, modern_names)

EXPANDED_CAPABILITIES = ["flarlic-v1", "population-v1", "bestiary-v1", "exploration-v1"]

CAPABILITIES = ["identity-placement-v1", "foh-day2-v1", "repair-goal-v1", "repeat-day29-v1"]


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def fingerprint(manifest):
    validate(manifest)
    return hashlib.sha256(canonical(manifest)).hexdigest()


class SeedRandom:
    """SHA256 counter stream, rejection sampling; independent of Python random."""
    def __init__(self, seed):
        self.seed = seed.encode()
        self.counter = 0

    def below(self, n):
        limit = (1 << 256) - ((1 << 256) % n)
        while True:
            value = int.from_bytes(hashlib.sha256(self.seed + b"\0" + self.counter.to_bytes(8, "big")).digest(), "big")
            self.counter += 1
            if value < limit:
                return value % n

    def shuffle(self, values):
        values = list(values)
        for i in range(len(values) - 1, 0, -1):
            j = self.below(i + 1)
            values[i], values[j] = values[j], values[i]
        return values


def generate(seed, mode="solo", slot="Player1", *, expanded=False, starting_area="forest", starting_color="red", all_areas=False, enemy_shuffle=False, collection_checks=False, starting_flarlic=None, randomize_color_stats=False, progressive_color_stats=False, permanent_checks=False, legacy_checks=False):
    collection_checks = collection_checks or progressive_color_stats or permanent_checks
    result = dict(schema=1, game=GAME, seed=str(seed), slot=slot, mode=mode,
                  profile="foh-day2", catalog="vanilla-sites-v1", rng="sha256-counter-v1",
                  placement="identity-v1", assignments=dict(PART_IDS),
                  locations=dict(LOCATION_IDS), goal=REPAIR_COUNT, day_policy="repeat-day29-v1",
                  capabilities=list(CAPABILITIES))
    if starting_flarlic is not None:
        if type(starting_flarlic) is not int or not 1 <= starting_flarlic <= 10:
            raise ValueError("starting_flarlic must be an integer from 1 to 10")
        expanded = True
    if expanded:
        result.update(schema=2, catalog="gameplay-checks-v2", locations=dict(ALL_LOCATION_IDS),
                      capabilities=CAPABILITIES + EXPANDED_CAPABILITIES)
    if starting_area != "forest":
        if starting_area not in ("random", "navel", "impact", "spring", "trial"):
            raise ValueError("unsupported starting area")
        selected = ("foh-day2", "navel-day2")[SeedRandom(str(seed) + "/start/" + slot).below(2)] if starting_area == "random" else "navel-day2"
        result.update(schema=3, profile=selected, catalog="gameplay-checks-v3", locations=dict(ALL_LOCATION_IDS),
                      capabilities=["identity-placement-v1", "random-start-v1", "repair-goal-v1", "repeat-day29-v1"] + EXPANDED_CAPABILITIES)
    if starting_color != 'red':
        if starting_color not in ('yellow', 'blue', 'random'):
            raise ValueError('unsupported starting color')
        color = ('red', 'yellow', 'blue')[SeedRandom(str(seed) + '/color/' + slot).below(3)] if starting_color == 'random' else starting_color
        result.update(schema=4, starting_color=color, catalog='gameplay-checks-v4', locations=dict(ALL_LOCATION_IDS),
                      capabilities=['identity-placement-v1', 'random-start-v1', 'repair-goal-v1', 'repeat-day29-v1'] + EXPANDED_CAPABILITIES + ['starting-color-v1'])
    if all_areas or enemy_shuffle or collection_checks or randomize_color_stats or starting_area in ('random', 'impact', 'spring', 'trial'):
        profile = tuple(START_AREAS)[SeedRandom(str(seed) + '/all-areas/' + slot).below(5)] if starting_area == 'random' else ('foh-day2' if starting_area == 'forest' else starting_area + '-day2')
        result.update(schema=5, profile=profile, starting_color=result.get('starting_color', 'red'),
                      catalog='gameplay-checks-v5', assignments=dict(ALL_PART_IDS), locations=dict(ALL_AREA_LOCATION_IDS),
                      capabilities=['identity-placement-v1', 'random-start-v1', 'repair-goal-v1', 'repeat-day29-v1'] + EXPANDED_CAPABILITIES + ['starting-color-v1', 'all-areas-v1'])
    if enemy_shuffle:
        result.update(schema=6, catalog='gameplay-checks-v6', enemy_shuffle='families-v1',
                      enemy_mask=1 + SeedRandom(str(seed) + '/enemies/' + slot).below(7),
                      capabilities=result['capabilities'] + ['enemy-families-v1'])
    if collection_checks:
        result.update(schema=7, catalog='gameplay-checks-v7', locations=dict(COLLECTION_LOCATION_IDS),
                      enemy_shuffle=result.get('enemy_shuffle', 'none'), enemy_mask=result.get('enemy_mask', 0))
        result['capabilities'] = [c for c in result['capabilities'] if c not in ('population-v1', 'bestiary-v1', 'enemy-families-v1')] + ['enemy-families-v1', 'total-population-v1', 'corpse-delivery-v1']
    if permanent_checks:
        from .catalog import PERMANENT_LOCATION_IDS
        result.update(schema=8, catalog='gameplay-checks-v8', locations=dict(PERMANENT_LOCATION_IDS))
        result['capabilities'] += ['permanent-checks-v1', 'check-set-v1']
    if collection_checks and not legacy_checks:
        result.update(schema=9, catalog='gameplay-checks-v9', permanent_checks=bool(permanent_checks), no_exploration=True,
                      locations={n: MODERN_LOCATION_IDS[n] for n in modern_names(permanent_checks, True)})
        result['capabilities'] = [c for c in result['capabilities'] if c not in ('permanent-checks-v1', 'check-set-v1')]
        result['capabilities'] += (['permanent-checks-v1'] if permanent_checks else []) + ['check-set-v1', 'bestiary-v2', 'no-exploration-v1']
    if starting_flarlic is not None:
        result["starting_flarlic"] = starting_flarlic
        result["capabilities"].append("starting-flarlic-v1")
    if randomize_color_stats:
        from .stats import roll_profiles
        result["color_stats"] = roll_profiles(SeedRandom(str(seed) + "/color-stats-v2/" + slot))
        result["capabilities"].append("color-stats-v2")
    if progressive_color_stats:
        result['progressive_color_stats'] = True
        result['capabilities'].append('progressive-color-stats-v1')
    if result['schema'] == 9:
        from .enemies import resolve_layout
        result['enemy_layout'] = resolve_layout(result['enemy_mask'])
    validate(result)
    return result


def validate(m):
    expected = {"schema", "game", "seed", "slot", "mode", "profile", "catalog", "rng", "placement",
                "assignments", "locations", "goal", "day_policy", "capabilities"}
    if type(m) is dict and m.get('schema', 0) in (4, 5, 6, 7, 8, 9):
        expected.add('starting_color')
    if type(m) is dict and m.get('schema') in (6, 7, 8, 9):
        expected.update(('enemy_shuffle', 'enemy_mask'))
    if type(m) is dict and m.get('schema') == 9:
        expected.add('permanent_checks')
        if 'no_exploration' in m:
            expected.add('no_exploration')
            if m['no_exploration'] is not True: raise ValueError('invalid no_exploration')
        if type(m.get('permanent_checks')) is not bool: raise ValueError('invalid permanent_checks')
    if type(m) is dict and 'enemy_layout' in m:
        expected.add('enemy_layout')
        from .enemies import resolve_layout, sources_for
        from .catalog import BESTIARY_TARGETS
        if m.get('schema') != 9 or type(m.get('enemy_mask')) is not int or not 0 <= m['enemy_mask'] <= 7:
            raise ValueError('enemy layout requires schema 9 and a valid seed mask')
        if canonical(m['enemy_layout']) != canonical(resolve_layout(m['enemy_mask'])):
            raise ValueError('enemy layout disagrees with seeded permutation/source catalog')
        if any(not sources_for(m['enemy_layout'], species) for species, _ in BESTIARY_TARGETS.values()):
            raise ValueError('bestiary species has no source in enemy layout')
    if type(m) is dict and "starting_flarlic" in m:
        expected.add("starting_flarlic")
        if type(m["starting_flarlic"]) is not int or not 1 <= m["starting_flarlic"] <= 10 or m.get("schema", 0) < 2:
            raise ValueError("invalid starting_flarlic")
    if type(m) is dict and "color_stats" in m:
        from .stats import validate_profiles
        expected.add("color_stats")
        validate_profiles(m["color_stats"], wide="color-stats-v2" in m.get("capabilities", []))
        if type(m.get("schema")) is not int or m["schema"] < 5:
            raise ValueError("color stats require the all-area catalog")
    if type(m) is dict and 'progressive_color_stats' in m:
        expected.add('progressive_color_stats')
        if m['progressive_color_stats'] is not True or m.get('schema') not in (7, 8, 9):
            raise ValueError('invalid progressive color stats mode')
    if type(m) is not dict or set(m) != expected:
        raise ValueError("manifest fields do not match schema 1")
    if type(m["schema"]) is not int or m["schema"] not in (1, 2, 3, 4, 5, 6, 7, 8, 9):
        raise ValueError("unsupported manifest schema")
    expanded = m["schema"] >= 2
    fixed = dict(schema=m["schema"], game=GAME, profile="foh-day2", catalog="vanilla-sites-v1",
                 rng="sha256-counter-v1", placement="identity-v1", goal=REPAIR_COUNT,
                 day_policy="repeat-day29-v1", capabilities=CAPABILITIES)
    if expanded:
        fixed.update(catalog="gameplay-checks-v2", capabilities=CAPABILITIES + EXPANDED_CAPABILITIES)
    if m['schema'] >= 3:
        if m['profile'] not in (START_AREAS if m['schema'] >= 5 else ('foh-day2', 'navel-day2')):
            raise ValueError('unsupported start profile')
        fixed.update(profile=m['profile'], catalog='gameplay-checks-v3',
                     capabilities=['identity-placement-v1', 'random-start-v1', 'repair-goal-v1', 'repeat-day29-v1'] + EXPANDED_CAPABILITIES)
    if m['schema'] >= 4:
        if m['starting_color'] not in ('red', 'yellow', 'blue'):
            raise ValueError('unsupported starting color')
        fixed.update(catalog='gameplay-checks-v4', capabilities=fixed['capabilities'] + ['starting-color-v1'])
    if m['schema'] >= 5:
        fixed.update(catalog='gameplay-checks-v5', capabilities=fixed['capabilities'] + ['all-areas-v1'])
    if m['schema'] >= 6:
        if type(m['enemy_mask']) is not int or not (0 if m['schema'] >= 7 else 1) <= m['enemy_mask'] <= 7:
            raise ValueError('unsupported enemy permutation')
        fixed.update(catalog='gameplay-checks-v6', enemy_shuffle='families-v1', capabilities=fixed['capabilities'] + ['enemy-families-v1'])
    if m['schema'] >= 7:
        fixed.update(catalog='gameplay-checks-v7', enemy_shuffle='families-v1' if m['enemy_mask'] else 'none',
                     capabilities=[c for c in fixed['capabilities'] if c not in ('population-v1', 'bestiary-v1')] + ['total-population-v1', 'corpse-delivery-v1'])
    if m['schema'] == 8:
        fixed.update(catalog='gameplay-checks-v8', capabilities=fixed['capabilities'] + ['permanent-checks-v1', 'check-set-v1'])
    if m['schema'] == 9:
        fixed.update(catalog='gameplay-checks-v9', capabilities=fixed['capabilities']
            + (['permanent-checks-v1'] if m['permanent_checks'] else []) + ['check-set-v1', 'bestiary-v2', 'no-exploration-v1' if m.get('no_exploration') else 'landing-only-v1'])
    if "starting_flarlic" in m:
        fixed["capabilities"] = fixed["capabilities"] + ["starting-flarlic-v1"]
    if "color_stats" in m:
        fixed["capabilities"] = fixed["capabilities"] + ["color-stats-v2" if "color-stats-v2" in m["capabilities"] else "color-stats-v1"]
    if m.get('progressive_color_stats'):
        fixed['capabilities'] += ['progressive-color-stats-v1']
    for key, value in fixed.items():
        if type(m[key]) is not type(value) or m[key] != value:
            raise ValueError(f"unsupported {key}: {m[key]!r}")
    for key in ("seed", "slot"):
        if type(m[key]) is not str or not 1 <= len(m[key]) <= 128 or any(ord(c) < 32 for c in m[key]):
            raise ValueError(f"invalid {key}")
    if m["mode"] not in ("solo", "ap"):
        raise ValueError("mode must be solo or ap")
    for key, value in (("assignments", ALL_PART_IDS if m['schema'] >= 5 else PART_IDS), ("locations", {n: MODERN_LOCATION_IDS[n] for n in modern_names(m["permanent_checks"], m.get("no_exploration", False))} if m["schema"] == 9 else PERMANENT_LOCATION_IDS if m['schema'] >= 8 else COLLECTION_LOCATION_IDS if m['schema'] >= 7 else ALL_AREA_LOCATION_IDS if m['schema'] >= 5 else ALL_LOCATION_IDS if expanded else LOCATION_IDS)):
        if type(m[key]) is not dict or m[key] != value or any(type(v) is not int for v in m[key].values()):
            raise ValueError(f"unsupported {key}; relocation is not implemented")


def solo_rewards(manifest):
    validate(manifest)
    rng = SeedRandom(manifest["seed"])
    rewards, inventory = {}, set()
    # Constructive progression fill: place each unlock at an already reachable
    # unfilled check, then advance the simulated inventory. Requirements are
    # deliberately the inherited conservative rules, pending route audit.
    names = active_names(manifest)
    expanded = manifest["schema"] == 2
    order = rng.shuffle(progression_pool(manifest))
    if manifest.get('progressive_color_stats'):
        from .stats import UPGRADE_ITEMS
        order.sort(key=lambda item: item in UPGRADE_ITEMS and UPGRADE_ITEMS[item][1] != 'carry')
    def place(remaining, owned, placed):
        if not remaining:
            return placed
        available = [n for n in names if n not in placed and can_reach_manifest(n, owned, manifest)]
        if not available:
            return None
        location = available[rng.below(len(available))]
        for item in dict.fromkeys(remaining):
            next_items = list(remaining); next_items.remove(item)
            next_owned = Counter(owned); next_owned[item] += 1
            result = place(next_items, next_owned, {**placed, location: item})
            if result is not None:
                return result
        return None
    rewards = place(order, Counter(), {})
    if rewards is None:
        raise ValueError("cannot place progression without a self-lock")
    rewards.update({n: REPAIR for n in names if n not in rewards})
    if Counter(rewards.values()) != Counter(item_pool(manifest)):
        raise ValueError("item pool does not match location count")
    return rewards


def spheres(rewards, manifest=None):
    expanded = len(rewards) > len(NAMES)
    names = tuple(rewards)
    inventory, remaining, result = Counter(), set(names), []
    while remaining:
        reachable = [n for n in names if n in remaining and (can_reach_manifest(n, inventory, manifest) if manifest else can_reach(n, inventory, expanded))]
        if not reachable:
            raise ValueError("unreachable checks: " + ", ".join(sorted(remaining)))
        result.append(reachable)
        inventory.update(rewards[n] for n in reachable)
        remaining.difference_update(reachable)
    return result
