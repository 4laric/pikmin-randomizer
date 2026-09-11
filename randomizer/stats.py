"""Version-one per-color profiles; integer percentages avoid float drift."""
COLORS = ('red', 'yellow', 'blue')
STAT_VALUES = {'damage': (50, 75, 100, 125, 150), 'movement': (75, 100, 125),
               'attack_rate': (75, 100, 125), 'carry': (1, 2, 3)}
UPGRADE_TIERS = {'damage': (100, 125, 150), 'movement': (100, 125),
                 'attack_rate': (100, 125), 'carry': (1, 2, 3)}
UPGRADE_ITEMS = {f'Progressive {color.title()} {label}': (color, stat)
                 for color in COLORS for stat, label in
                 (('damage', 'Damage'), ('movement', 'Movement'), ('attack_rate', 'Attack Rate'), ('carry', 'Carry Strength'))}


def upgrade_pool():
    return [name for name, (_, stat) in UPGRADE_ITEMS.items() for _ in UPGRADE_TIERS[stat][1:]]


def current_profiles(manifest, inventory=None):
    if not manifest.get('progressive_color_stats'):
        return manifest.get('color_stats', {})
    inventory = inventory or {}
    profiles = {color: {} for color in COLORS}
    for name, (color, stat) in UPGRADE_ITEMS.items():
        tiers = UPGRADE_TIERS[stat]
        profiles[color][stat] = tiers[min(len(tiers)-1, inventory.get(name, 0))]
    return profiles


def upgrade_counts(manifest, inventory):
    if not manifest.get('progressive_color_stats'): return ''
    names = {(color, stat): name for name, (color, stat) in UPGRADE_ITEMS.items()}
    return ' UPGRADES ' + ' '.join(str(min(len(UPGRADE_TIERS[stat])-1, inventory.get(names[color, stat], 0)))
        for color in ('blue', 'red', 'yellow') for stat in UPGRADE_TIERS)


def roll_profiles(rng):
    return {color: {stat: values[rng.below(len(values))] for stat, values in STAT_VALUES.items()}
            for color in COLORS}


def validate_profiles(profiles):
    if type(profiles) is not dict or set(profiles) != set(COLORS):
        raise ValueError('invalid color stat profiles')
    for profile in profiles.values():
        if type(profile) is not dict or set(profile) != set(STAT_VALUES):
            raise ValueError('invalid color stat fields')
        for stat, value in profile.items():
            if type(value) is not int or value not in STAT_VALUES[stat]:
                raise ValueError(f'invalid {stat} stat')


def bootstrap_stats(manifest):
    if 'color_stats' not in manifest:
        return ''
    return 'COLOR_STATS ' + ' '.join(color + ' ' + ' '.join(
        str(manifest['color_stats'][color][stat]) for stat in STAT_VALUES)
        for color in ('blue', 'red', 'yellow')) + '\n'


def profile_lines(manifest, inventory=None):
    profiles = current_profiles(manifest, inventory)
    if not profiles:
        return []
    return [f"{color.upper():6} DMG {p['damage']}%  MOVE {p['movement']}%  ATK {p['attack_rate']}%  CARRY {p['carry']}"
            for color in COLORS for p in (profiles[color],)]
