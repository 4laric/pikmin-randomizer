"""Strict, deterministic identity-placement milestone; no unproven relocation."""
import hashlib
import json
import os
from collections import Counter
from pathlib import Path
from .catalog import (GAME, NAMES, PART_IDS, LOCATION_IDS, UNLOCKS,
                      REPAIR, REPAIR_COUNT, CHECK_REQUIREMENTS, active_names, ALL_LOCATION_IDS,
                      can_reach, can_reach_manifest, progression_pool, item_pool, START_AREAS, ALL_AREA_LOCATION_IDS, ALL_PART_IDS, COLLECTION_LOCATION_IDS, PERMANENT_LOCATION_IDS, MODERN_LOCATION_IDS, modern_names)

EXPANDED_CAPABILITIES = ["flarlic-v1", "population-v1", "bestiary-v1", "exploration-v1"]

CAPABILITIES = ["identity-placement-v1", "foh-day2-v1", "repair-goal-v1", "repeat-day29-v1"]

ADMITTED_PLACEMENT_FILENAME = "PIKMIN2_ADMITTED_PLACEMENT.json"


def _default_admitted_placement():
    """Committed lane 04 accepted-placement document for the admitted cohort.

    Admitted P2 enemies are eligible for placement behind the ``p2_enemies`` /
    AP ``p2_enemy_randomizer`` option. When no explicit document is supplied this
    finds the committed accepted-placement document (repo ``docs/``, a
    ``PIKMIN2_ADMITTED_PLACEMENT`` path override, or the packaged apworld data
    file). It is deliberately fail-closed: an empty or unaccepted admitted set is
    still rejected by ``resolve_placement_layout``.
    """
    candidates = []
    override = os.environ.get("PIKMIN2_ADMITTED_PLACEMENT")
    if override:
        candidates.append(Path(override))
    try:
        candidates.append(Path(__file__).resolve().parents[1] / "docs" / ADMITTED_PLACEMENT_FILENAME)
    except (NameError, OSError):
        pass
    candidates.append(Path.cwd() / "docs" / ADMITTED_PLACEMENT_FILENAME)
    for candidate in candidates:
        if candidate.is_file():
            return json.loads(candidate.read_text(encoding="utf-8"))
    try:
        from importlib.resources import files
        package = __package__ or ""
        if package.startswith("pikmin_randomizer"):
            resource = files(package) / "data" / ADMITTED_PLACEMENT_FILENAME
            return json.loads(resource.read_text(encoding="utf-8"))
    except (ImportError, ModuleNotFoundError, FileNotFoundError, TypeError):
        pass
    raise ValueError(
        "P2 enemies require the committed admitted-placement document "
        f"(docs/{ADMITTED_PLACEMENT_FILENAME}); set PIKMIN2_ADMITTED_PLACEMENT to override")


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


# Admitted P2 species the current launcher and native campaign path can actually run:
# each has a family installer (experimental/pikmin2_family_install.IDENTITY_FAMILY) and
# a bridge-mode campaign setup. Excluded until fixed: 9 Kogane, 79 Sokkuri, 57 Kurage,
# 78 MiniHoudai (no installer) and 23 Sarai (campaign setup needs a fixed generator).
PLAYABLE_P2_SPECIES = (44, 54, 59, 60, 61, 62)


def generate(seed, mode="solo", slot="Player1", *, expanded=False, starting_area="forest", starting_color="red", all_areas=False, enemy_shuffle=False, collection_checks=False, starting_flarlic=None, randomize_color_stats=False, progressive_color_stats=False, permanent_checks=False, legacy_checks=False, per_spawn_enemies=False, group_spawn_enemies=False, miniboss_enemies=False, campaign_enemies=False, initial_stat_bounds=None, stat_upgrade_counts=None, random_start_areas=None, bomb_rock_weight=0, goal_mode="repairs", combined_captain=False, bomb_trap_weight=0, progg_trap_weight=0, prerelease_trap_weight=0, death_link=False, death_link_pikmin=10, p2_enemies=False, p2_placement=None, p2_species=None):
    if type(bomb_rock_weight) is not int or not 0 <= bomb_rock_weight <= 10: raise ValueError("bomb_rock_weight must be 0..10")
    if type(bomb_trap_weight) is not int or not 0 <= bomb_trap_weight <= 10: raise ValueError("bomb_trap_weight must be 0..10")
    if type(progg_trap_weight) is not int or not 0 <= progg_trap_weight <= 10: raise ValueError("progg_trap_weight must be 0..10")
    if type(prerelease_trap_weight) is not int or not 0 <= prerelease_trap_weight <= 10: raise ValueError("prerelease_trap_weight must be 0..10")
    if type(death_link) is not bool: raise ValueError("invalid death_link")
    if type(death_link_pikmin) is not int or not 1 <= death_link_pikmin <= 100: raise ValueError("death_link_pikmin must be 1..100")
    if death_link:
        if legacy_checks: raise ValueError("death link requires modern checks")
        collection_checks = True
    if bomb_rock_weight or bomb_trap_weight or progg_trap_weight or prerelease_trap_weight:
        if legacy_checks: raise ValueError("bomb deliveries require modern checks")
        collection_checks = True
    from .stats import validate_roll_bounds, validate_upgrade_limits
    if initial_stat_bounds is not None: validate_roll_bounds(initial_stat_bounds)
    if stat_upgrade_counts is not None: validate_upgrade_limits(stat_upgrade_counts)
    area_names = ('impact', 'forest', 'navel', 'spring')
    if random_start_areas is not None:
        if not isinstance(random_start_areas, (list, tuple, set, frozenset)) or not random_start_areas or any(a not in area_names for a in random_start_areas):
            raise ValueError('random_start_areas must be a nonempty subset of impact, forest, navel, spring')
    if group_spawn_enemies or miniboss_enemies: per_spawn_enemies = True
    if per_spawn_enemies:
        if legacy_checks: raise ValueError('per-spawn enemies require modern checks')
        collection_checks = True
        enemy_shuffle = False
    if campaign_enemies:
        if legacy_checks: raise ValueError("campaign enemies require modern checks")
        per_spawn_enemies = group_spawn_enemies = enemy_shuffle = False
        collection_checks = miniboss_enemies = True
    if type(combined_captain) is not bool: raise ValueError("invalid combined_captain")
    if combined_captain: collection_checks = True
    if type(p2_enemies) is not bool: raise ValueError("invalid p2_enemies")
    if p2_species is not None and not p2_enemies: raise ValueError("p2_species requires p2_enemies")
    if p2_species == "playable": p2_species = PLAYABLE_P2_SPECIES
    if p2_species is not None and (not isinstance(p2_species, (list, tuple, set, frozenset)) or not p2_species
                                   or any(type(i) is not int for i in p2_species)):
        raise ValueError("p2_species must be 'playable' or a nonempty list of admitted source ids")
    if p2_placement is not None and type(p2_placement) is not dict:
        raise ValueError("p2_placement must be a placement document mapping")
    if p2_enemies:
        if legacy_checks: raise ValueError("P2 enemies require modern checks")
        if enemy_shuffle or per_spawn_enemies or group_spawn_enemies or miniboss_enemies or campaign_enemies:
            raise ValueError("P2 enemies are mutually exclusive with P1 enemy layouts")
        collection_checks = True
    if goal_mode not in ("repairs", "emperor_bulblax"): raise ValueError("invalid goal_mode")
    if goal_mode == "emperor_bulblax": collection_checks = True
    if progressive_color_stats: permanent_checks = True  # 36 upgrades need the larger check pool.
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
        eligible = tuple(p for p in START_AREAS if p != 'trial-day2' and (random_start_areas is None or ('forest' if p == 'foh-day2' else p.removesuffix('-day2')) in random_start_areas))
        profile = eligible[SeedRandom(str(seed) + '/all-areas-v2/' + slot).below(len(eligible))] if starting_area == 'random' else ('foh-day2' if starting_area == 'forest' else starting_area + '-day2')
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
        result.update(schema=9, catalog='gameplay-checks-v9', permanent_checks=bool(permanent_checks), no_exploration=True, color_population=True, compact_population=True, no_sticks=True,
                      locations={n: MODERN_LOCATION_IDS[n] for n in modern_names(permanent_checks, True, True, True, True)})
        result['capabilities'] = [c for c in result['capabilities'] if c not in ('permanent-checks-v1', 'check-set-v1')]
        result['capabilities'] += (['permanent-checks-v1'] if permanent_checks else []) + ['check-set-v1', 'bestiary-v2', 'no-exploration-v1', 'color-population-v1', 'compact-population-v1']
    if starting_flarlic is not None:
        result["starting_flarlic"] = starting_flarlic
        result["capabilities"].append("starting-flarlic-v1")
    if randomize_color_stats:
        from .stats import roll_profiles
        result["color_stats"] = roll_profiles(SeedRandom(str(seed) + "/color-stats-v3/" + slot), initial_stat_bounds)
        result["capabilities"].append("color-stats-v3")
    if progressive_color_stats:
        result['progressive_color_stats'] = True
        result['capabilities'].append('progressive-color-stats-v2')
        if stat_upgrade_counts is not None:
            result['stat_upgrade_counts'] = dict(stat_upgrade_counts)
    if result['schema'] == 9:
        from .enemies import resolve_layout
        result['enemy_layout'] = resolve_layout(result['enemy_mask'])
        result['benefit_items'] = True
        result['repair_pool_count'] = 30
        result['capabilities'].append('benefit-items-v1')
        if combined_captain:
            result['combined_captain'] = True
            result['capabilities'].append('combined-captain-v1')
        if bomb_rock_weight:
            result['bomb_rock_weight'] = bomb_rock_weight
            result['capabilities'].append('bomb-delivery-v1')
        if bomb_trap_weight:
            result['bomb_trap_weight'] = bomb_trap_weight
            result['capabilities'].append('bomb-ambush-v1')
        if progg_trap_weight:
            result['progg_trap_weight'] = progg_trap_weight
            result['capabilities'].append('progg-ambush-v1')
        if prerelease_trap_weight:
            result['prerelease_trap_weight'] = prerelease_trap_weight
            result['capabilities'].append('prerelease-trap-v1')
        if per_spawn_enemies:
            from .enemy_slots import resolve_spawn_layout, spawn_sources
            result['spawn_layout'] = resolve_spawn_layout(result['seed'], slot, miniboss_enemies)
            result['enemy_layout'] = spawn_sources(result['spawn_layout'])
            result['enemy_shuffle'] = 'adult-slots-v1'
            result['capabilities'].append('enemy-slots-v1')
    if group_spawn_enemies:
        from .enemy_slots import resolve_group_layout, spawn_sources
        result["group_layout"] = resolve_group_layout(result["seed"], slot)
        result["enemy_layout"] = spawn_sources(result["spawn_layout"], result["group_layout"])
        result["capabilities"].append("enemy-groups-v1")
    if campaign_enemies:
        from .campaign_enemies import resolve_campaign, campaign_sources
        result['campaign_layout'] = resolve_campaign(result['seed'], slot)
        result['enemy_layout'] = campaign_sources(result['campaign_layout'])
        result['enemy_shuffle'] = 'campaign-v1'
        result['capabilities'].append('enemy-campaign-v1')
    if miniboss_enemies:
        result['miniboss_enemies'] = True
        result['capabilities'].append('miniboss-slots-v1')
    if goal_mode == "emperor_bulblax":
        result["goal_mode"] = goal_mode
        result["capabilities"].append("emperor-goal-v1")
    if death_link:
        # One unit sets both the outgoing threshold and incoming casualties.
        result["death_link"] = True
        result["death_link_pikmin"] = death_link_pikmin
        result["capabilities"].append("death-link-v1")
    if p2_enemies:
        # Opt-in experimental bridge: the admitted cohort comes from lane 02, the
        # ordered binding targets from lane 04. Fail closed while nothing is
        # admitted. Kept behind a lazy import so ordinary seeds never load the
        # experimental roster.
        from experimental.pikmin2_enemy_roster import load_and_validate
        # Product path: legal targets come only from the lane 04 placement contract.
        # Explicit-cohort binding stays a diagnostic bridge API, not a seed option.
        from experimental.pikmin2_seed_bridge import resolve_placement_layout
        if result['schema'] != 9:
            raise ValueError("P2 enemies require the modern schema-9 catalog")
        if p2_placement is None:
            # Admitted enemies are eligible for placement behind the p2_enemies
            # option; the committed accepted-placement document supplies the legal
            # targets and resolve_placement_layout still fails closed.
            p2_placement = _default_admitted_placement()
        result['p2_layout'] = resolve_placement_layout(result['seed'], slot, p2_placement, load_and_validate(),
                                                       species=None if p2_species is None else sorted(set(p2_species)))
        result['capabilities'].append('p2-enemy-bridge-v1')
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
        if 'compact_population' in m:
            expected.add('compact_population')
            if m['compact_population'] is not True or not m.get('color_population'): raise ValueError('invalid compact_population')
        if 'benefit_items' in m:
            expected.add('benefit_items')
            if m['benefit_items'] is not True or not m.get('color_population'): raise ValueError('invalid benefit_items')
        if 'color_population' in m:
            expected.add('color_population')
            if m['color_population'] is not True or not m.get('no_exploration'): raise ValueError('invalid color_population')
        if 'no_exploration' in m:
            expected.add('no_exploration')
            if m['no_exploration'] is not True: raise ValueError('invalid no_exploration')
        if type(m.get('permanent_checks')) is not bool: raise ValueError('invalid permanent_checks')
    if type(m) is dict and 'miniboss_enemies' in m:
        expected.add('miniboss_enemies')
        if m['miniboss_enemies'] is not True or not ('spawn_layout' in m or 'campaign_layout' in m): raise ValueError('invalid miniboss_enemies')
    if type(m) is dict and 'campaign_layout' in m:
        from .campaign_enemies import resolve_campaign
        expected.add('campaign_layout')
        if m.get('schema') != 9 or m.get('enemy_mask') != 0 or not m.get('miniboss_enemies') or 'spawn_layout' in m or 'group_layout' in m:
            raise ValueError('invalid campaign enemy mode')
        if canonical(m['campaign_layout']) != canonical(resolve_campaign(m.get('seed',''),m.get('slot',''))):
            raise ValueError('invalid campaign enemy layout')
    if type(m) is dict and 'spawn_layout' in m:
        expected.add('spawn_layout')
        from .enemy_slots import resolve_spawn_layout
        if m.get('schema') != 9 or m.get('enemy_mask') != 0 or 'enemy_layout' not in m:
            raise ValueError('per-spawn layout requires modern zero-mask seed')
        if canonical(m['spawn_layout']) != canonical(resolve_spawn_layout(m.get('seed', ''), m.get('slot', ''), m.get('miniboss_enemies',False))):
            raise ValueError('invalid per-spawn layout or source catalog')
    if type(m) is dict and 'group_layout' in m:
        expected.add('group_layout')
        from .enemy_slots import resolve_group_layout
        if 'spawn_layout' not in m or canonical(m['group_layout']) != canonical(resolve_group_layout(m.get('seed',''),m.get('slot',''))):
            raise ValueError('invalid grouped enemy layout')
    if type(m) is dict and 'enemy_layout' in m:
        expected.add('enemy_layout')
        from .enemies import resolve_layout, sources_for
        from .catalog import BESTIARY_TARGETS
        if m.get('schema') != 9 or type(m.get('enemy_mask')) is not int or not 0 <= m['enemy_mask'] <= 7:
            raise ValueError('enemy layout requires schema 9 and a valid seed mask')
        from .enemy_slots import spawn_sources
        from .campaign_enemies import campaign_sources
        expected_sources = campaign_sources(m['campaign_layout']) if 'campaign_layout' in m else spawn_sources(m['spawn_layout'], m.get('group_layout')) if 'spawn_layout' in m else resolve_layout(m['enemy_mask'])
        if canonical(m['enemy_layout']) != canonical(expected_sources):
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
        validate_profiles(m["color_stats"], wide="color-stats-v2" in m.get("capabilities", []), balanced="color-stats-v3" in m.get("capabilities", []))
        if type(m.get("schema")) is not int or m["schema"] < 5:
            raise ValueError("color stats require the all-area catalog")
    if type(m) is dict and 'progressive_color_stats' in m:
        expected.add('progressive_color_stats')
        if m['progressive_color_stats'] is not True or m.get('schema') not in (7, 8, 9):
            raise ValueError('invalid progressive color stats mode')
    if type(m) is dict and 'bomb_rock_weight' in m:
        expected.add('bomb_rock_weight')
        if type(m['bomb_rock_weight']) is not int or not 1 <= m['bomb_rock_weight'] <= 10 or not m.get('benefit_items'):
            raise ValueError('invalid bomb delivery weight')
    if type(m) is dict and 'bomb_trap_weight' in m:
        expected.add('bomb_trap_weight')
        if type(m['bomb_trap_weight']) is not int or not 1 <= m['bomb_trap_weight'] <= 10 or not m.get('benefit_items'):
            raise ValueError('invalid bomb_trap_weight')
    if type(m) is dict and 'progg_trap_weight' in m:
        expected.add('progg_trap_weight')
        if type(m['progg_trap_weight']) is not int or not 1 <= m['progg_trap_weight'] <= 10 or not m.get('benefit_items'):
            raise ValueError('invalid progg_trap_weight')
    if type(m) is dict and 'prerelease_trap_weight' in m:
        expected.add('prerelease_trap_weight')
        if type(m['prerelease_trap_weight']) is not int or not 1 <= m['prerelease_trap_weight'] <= 10 or not m.get('benefit_items'):
            raise ValueError('invalid prerelease_trap_weight')
    if type(m) is dict and 'combined_captain' in m:
        expected.add('combined_captain')
        if m['combined_captain'] is not True or not m.get('benefit_items'): raise ValueError('invalid combined_captain')
    if type(m) is dict and 'goal_mode' in m:
        expected.add('goal_mode')
        if m.get('schema') != 9 or m['goal_mode'] != 'emperor_bulblax': raise ValueError('invalid goal_mode')
    if type(m) is dict and ('death_link' in m or 'death_link_pikmin' in m):
        expected.update(('death_link', 'death_link_pikmin'))
        if m.get('schema') != 9 or m.get('death_link') is not True or type(m.get('death_link_pikmin')) is not int \
                or not 1 <= m['death_link_pikmin'] <= 100:
            raise ValueError('invalid death_link')
    if type(m) is dict and 'no_sticks' in m:
        expected.add('no_sticks')
        if m.get('schema') != 9 or m['no_sticks'] is not True:
            raise ValueError('invalid no_sticks')
    if type(m) is dict and 'repair_pool_count' in m:
        expected.add('repair_pool_count')
        if type(m['repair_pool_count']) is not int or m['repair_pool_count'] != 30 or not m.get('benefit_items'):
            raise ValueError('invalid repair pool count')
    if type(m) is dict and 'stat_upgrade_counts' in m:
        from .stats import validate_upgrade_limits
        expected.add('stat_upgrade_counts')
        validate_upgrade_limits(m['stat_upgrade_counts'])
        if not m.get('progressive_color_stats') or 'progressive-color-stats-v2' not in m.get('capabilities', []):
            raise ValueError('custom upgrade counts require progressive stats v2')
    if type(m) is dict and 'p2_layout' in m:
        expected.add('p2_layout')
        from experimental.pikmin2_enemy_roster import load_and_validate
        from experimental.pikmin2_seed_bridge import (SeedBridgeError, admitted_ids,
                                                      validate_layout as validate_p2_layout)
        if (m.get('schema') != 9 or m.get('enemy_mask') != 0
                or any(key in m for key in ('spawn_layout', 'group_layout', 'campaign_layout'))):
            raise ValueError('p2_layout is mutually exclusive with P1 enemy layouts and requires schema 9')
        if 'p2-enemy-bridge-v1' not in m.get('capabilities', []):
            raise ValueError('p2_layout requires the p2-enemy-bridge-v1 capability')
        try:
            roster = load_and_validate()
            # Product path: a loaded seed must still satisfy the *current* admission set.
            validate_p2_layout(m['p2_layout'], roster, admitted=admitted_ids(roster))
        except SeedBridgeError as exc:
            raise ValueError(f'invalid p2_layout: {exc}')
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
        fixed.update(catalog='gameplay-checks-v7', enemy_shuffle='campaign-v1' if 'campaign_layout' in m else 'adult-slots-v1' if 'spawn_layout' in m else 'families-v1' if m['enemy_mask'] else 'none',
                     capabilities=[c for c in fixed['capabilities'] if c not in ('population-v1', 'bestiary-v1')] + ['total-population-v1', 'corpse-delivery-v1'])
    if m['schema'] == 8:
        fixed.update(catalog='gameplay-checks-v8', capabilities=fixed['capabilities'] + ['permanent-checks-v1', 'check-set-v1'])
    if m['schema'] == 9:
        fixed.update(catalog='gameplay-checks-v9', capabilities=fixed['capabilities']
            + (['permanent-checks-v1'] if m['permanent_checks'] else []) + ['check-set-v1', 'bestiary-v2', 'no-exploration-v1' if m.get('no_exploration') else 'landing-only-v1'])
    if m.get('color_population'):
        fixed['capabilities'] += ['color-population-v1']
    if m.get('compact_population'):
        fixed['capabilities'] += ['compact-population-v1']
    if "starting_flarlic" in m:
        fixed["capabilities"] = fixed["capabilities"] + ["starting-flarlic-v1"]
    if "color_stats" in m:
        fixed["capabilities"] = fixed["capabilities"] + ["color-stats-v3" if "color-stats-v3" in m["capabilities"] else "color-stats-v2" if "color-stats-v2" in m["capabilities"] else "color-stats-v1"]
    if m.get('progressive_color_stats'):
        fixed['capabilities'] += ['progressive-color-stats-v2' if 'progressive-color-stats-v2' in m['capabilities'] else 'progressive-color-stats-v1']
    if m.get('benefit_items'):
        fixed['capabilities'] += ['benefit-items-v1']
        if m.get('combined_captain'): fixed['capabilities'] += ['combined-captain-v1']
        if m.get('bomb_rock_weight'): fixed['capabilities'] += ['bomb-delivery-v1']
        if m.get('bomb_trap_weight'): fixed['capabilities'] += ['bomb-ambush-v1']
        if m.get('progg_trap_weight'): fixed['capabilities'] += ['progg-ambush-v1']
        if m.get('prerelease_trap_weight'): fixed['capabilities'] += ['prerelease-trap-v1']
    if 'spawn_layout' in m:
        fixed['capabilities'] += ['enemy-slots-v1']
    if 'group_layout' in m:
        fixed['capabilities'] += ['enemy-groups-v1']
    if 'campaign_layout' in m:
        fixed['capabilities'] += ['enemy-campaign-v1']
    if m.get('miniboss_enemies'):
        fixed['capabilities'] += ['miniboss-slots-v1']
    if m.get("goal_mode") == "emperor_bulblax": fixed["capabilities"].append("emperor-goal-v1")
    if m.get("death_link"): fixed["capabilities"].append("death-link-v1")
    if m.get('p2_layout'): fixed['capabilities'].append('p2-enemy-bridge-v1')
    for key, value in fixed.items():
        if type(m[key]) is not type(value) or m[key] != value:
            raise ValueError(f"unsupported {key}: {m[key]!r}")
    for key in ("seed", "slot"):
        if type(m[key]) is not str or not 1 <= len(m[key]) <= 128 or any(ord(c) < 32 for c in m[key]):
            raise ValueError(f"invalid {key}")
    if m["mode"] not in ("solo", "ap"):
        raise ValueError("mode must be solo or ap")
    for key, value in (("assignments", ALL_PART_IDS if m['schema'] >= 5 else PART_IDS), ("locations", {n: MODERN_LOCATION_IDS[n] for n in modern_names(m["permanent_checks"], m.get("no_exploration", False), m.get("color_population", False), m.get("compact_population", False), m.get("no_sticks", False))} if m["schema"] == 9 else PERMANENT_LOCATION_IDS if m['schema'] >= 8 else COLLECTION_LOCATION_IDS if m['schema'] >= 7 else ALL_AREA_LOCATION_IDS if m['schema'] >= 5 else ALL_LOCATION_IDS if expanded else LOCATION_IDS)):
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
    remaining = Counter(item_pool(manifest)) - Counter(rewards.values())
    filler = rng.shuffle(list(remaining.elements())) if manifest.get('benefit_items') else [REPAIR] * sum(remaining.values())
    rewards.update(zip((n for n in names if n not in rewards), filler))
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
