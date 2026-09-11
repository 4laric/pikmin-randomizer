"""Version-one per-color profiles; integer percentages avoid float drift."""
COLORS = ('red', 'yellow', 'blue')
STAT_VALUES = {'damage': (50, 75, 100, 125, 150), 'movement': (75, 100, 125),
               'attack_rate': (75, 100, 125), 'carry': (1, 2, 3)}


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


def profile_lines(manifest):
    if 'color_stats' not in manifest:
        return []
    return [f"{color.upper():6} DMG {p['damage']}%  MOVE {p['movement']}%  ATK {p['attack_rate']}%  CARRY {p['carry']}"
            for color in COLORS for p in (manifest['color_stats'][color],)]
