"""Strict, deterministic identity-placement milestone; no unproven relocation."""
import hashlib
import json
from collections import Counter
from .catalog import (GAME, NAMES, PART_IDS, LOCATION_IDS, UNLOCKS,
                      REPAIR, REPAIR_COUNT, CHECK_REQUIREMENTS, active_names, ALL_LOCATION_IDS,
                      can_reach, can_reach_manifest, progression_pool, item_pool)

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


def generate(seed, mode="solo", slot="Player1", *, expanded=False, starting_area="forest", starting_color="red"):
    result = dict(schema=1, game=GAME, seed=str(seed), slot=slot, mode=mode,
                  profile="foh-day2", catalog="vanilla-sites-v1", rng="sha256-counter-v1",
                  placement="identity-v1", assignments=dict(PART_IDS),
                  locations=dict(LOCATION_IDS), goal=REPAIR_COUNT, day_policy="repeat-day29-v1",
                  capabilities=list(CAPABILITIES))
    if expanded:
        result.update(schema=2, catalog="gameplay-checks-v2", locations=dict(ALL_LOCATION_IDS),
                      capabilities=CAPABILITIES + EXPANDED_CAPABILITIES)
    if starting_area != "forest":
        if starting_area not in ("random", "navel"):
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
    validate(result)
    return result


def validate(m):
    expected = {"schema", "game", "seed", "slot", "mode", "profile", "catalog", "rng", "placement",
                "assignments", "locations", "goal", "day_policy", "capabilities"}
    if type(m) is dict and m.get('schema') == 4:
        expected.add('starting_color')
    if type(m) is not dict or set(m) != expected:
        raise ValueError("manifest fields do not match schema 1")
    if type(m["schema"]) is not int or m["schema"] not in (1, 2, 3, 4):
        raise ValueError("unsupported manifest schema")
    expanded = m["schema"] >= 2
    fixed = dict(schema=m["schema"], game=GAME, profile="foh-day2", catalog="vanilla-sites-v1",
                 rng="sha256-counter-v1", placement="identity-v1", goal=REPAIR_COUNT,
                 day_policy="repeat-day29-v1", capabilities=CAPABILITIES)
    if expanded:
        fixed.update(catalog="gameplay-checks-v2", capabilities=CAPABILITIES + EXPANDED_CAPABILITIES)
    if m['schema'] >= 3:
        if m['profile'] not in ('foh-day2', 'navel-day2'):
            raise ValueError('unsupported start profile')
        fixed.update(profile=m['profile'], catalog='gameplay-checks-v3',
                     capabilities=['identity-placement-v1', 'random-start-v1', 'repair-goal-v1', 'repeat-day29-v1'] + EXPANDED_CAPABILITIES)
    if m['schema'] == 4:
        if m['starting_color'] not in ('red', 'yellow', 'blue'):
            raise ValueError('unsupported starting color')
        fixed.update(catalog='gameplay-checks-v4', capabilities=fixed['capabilities'] + ['starting-color-v1'])
    for key, value in fixed.items():
        if type(m[key]) is not type(value) or m[key] != value:
            raise ValueError(f"unsupported {key}: {m[key]!r}")
    for key in ("seed", "slot"):
        if type(m[key]) is not str or not 1 <= len(m[key]) <= 128 or any(ord(c) < 32 for c in m[key]):
            raise ValueError(f"invalid {key}")
    if m["mode"] not in ("solo", "ap"):
        raise ValueError("mode must be solo or ap")
    for key, value in (("assignments", PART_IDS), ("locations", ALL_LOCATION_IDS if expanded else LOCATION_IDS)):
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
