"""Version-one per-color profiles; integer percentages avoid float drift."""
COLORS = ('red', 'yellow', 'blue')
STAT_VALUES = {'damage': (50, 75, 100, 125, 150), 'movement': (75, 100, 125),
               'attack_rate': (75, 100, 125), 'carry': (1, 2, 3)}
WIDE_STAT_VALUES = {'damage': tuple(range(25, 201, 25)), 'movement': tuple(range(50, 151, 25)),
                    'attack_rate': tuple(range(50, 151, 25)), 'carry': (1, 2, 3, 4, 5)}
UPGRADE_TIERS = {'damage': (100, 125, 150), 'movement': (100, 125),
                 'attack_rate': (100, 125), 'carry': (1, 2, 3)}
BALANCED_STAT_VALUES = {'damage': (25,50,75,100), 'movement': (25,50,75,100),
                        'attack_rate': (25,50,75,100), 'carry': (1,)}
DOUBLE_UPGRADE_TIERS = {'damage': (100,125,150,175,200), 'movement': (100,125,150),
                        'attack_rate': (100,125,150), 'carry': (1,2,3,4,5)}

def upgrade_tiers(manifest=None):
    return DOUBLE_UPGRADE_TIERS if manifest and 'progressive-color-stats-v2' in manifest.get('capabilities', ()) else UPGRADE_TIERS

UPGRADE_ITEMS = {f'Progressive {color.title()} {label}': (color, stat)
                 for color in COLORS for stat, label in
                 (('damage', 'Damage'), ('movement', 'Movement'), ('attack_rate', 'Attack Rate'), ('carry', 'Carry Strength'))}


def upgrade_pool(manifest=None):
    return [name for name, (_, stat) in UPGRADE_ITEMS.items() for _ in upgrade_tiers(manifest)[stat][1:]]


def current_profiles(manifest, inventory=None):
    if not manifest.get('progressive_color_stats'):
        return manifest.get('color_stats', {})
    inventory = inventory or {}
    profiles = {color: {} for color in COLORS}
    for name, (color, stat) in UPGRADE_ITEMS.items():
        tiers = upgrade_tiers(manifest)[stat]
        base = manifest.get('color_stats', {}).get(color, {}).get(stat, tiers[0])
        profiles[color][stat] = base + tiers[min(len(tiers)-1, inventory.get(name, 0))] - tiers[0]
    return profiles


def upgrade_counts(manifest, inventory):
    if not manifest.get('progressive_color_stats'): return ''
    names = {(color, stat): name for name, (color, stat) in UPGRADE_ITEMS.items()}
    return ' UPGRADES ' + ' '.join(str(min(len(upgrade_tiers(manifest)[stat])-1, inventory.get(names[color, stat], 0)))
        for color in ('blue', 'red', 'yellow') for stat in UPGRADE_TIERS)


def roll_profiles(rng):
    return {color: {stat: values[rng.below(len(values))] for stat, values in BALANCED_STAT_VALUES.items()}
            for color in COLORS}


def validate_profiles(profiles, wide=False, balanced=False):
    allowed = BALANCED_STAT_VALUES if balanced else WIDE_STAT_VALUES if wide else STAT_VALUES
    if type(profiles) is not dict or set(profiles) != set(COLORS):
        raise ValueError('invalid color stat profiles')
    for profile in profiles.values():
        if type(profile) is not dict or set(profile) != set(STAT_VALUES):
            raise ValueError('invalid color stat fields')
        for stat, value in profile.items():
            if type(value) is not int or value not in allowed[stat]:
                raise ValueError(f'invalid {stat} stat')


def bootstrap_stats(manifest):
    if 'color_stats' not in manifest:
        return ''
    return ('COLOR_STATS_BALANCED ' if 'color-stats-v3' in manifest['capabilities'] else 'COLOR_STATS_WIDE ' if 'color-stats-v2' in manifest['capabilities'] else 'COLOR_STATS ') + ' '.join(color + ' ' + ' '.join(
        str(manifest['color_stats'][color][stat]) for stat in STAT_VALUES)
        for color in ('blue', 'red', 'yellow')) + '\n'


def profile_lines(manifest, inventory=None):
    # Import here because catalog uses the gameplay profile helpers above.
    from .catalog import color_inventory, RED, YELLOW, BLUE

    profiles = current_profiles(manifest, inventory)
    if not profiles:
        return []
    owned = color_inventory(inventory or {}, manifest)
    return [f"{color.upper():6} DMG {p['damage']}%  MOVE {p['movement']}%  ATK {p['attack_rate']}%  CARRY {p['carry']}"
            if owned.get(onion, 0) > 0 else f"{color.upper():6} ??? (undiscovered)"
            for color, onion in zip(COLORS, (RED, YELLOW, BLUE)) for p in (profiles[color],)]
