"""Useful rewards and optional traps; none are required by reachability rules."""
DELIVERY = 'Pikmin Delivery (10)'
FLOWERS = 'Flower Shower'
HEAL = 'Captain Heal'
WHISTLE = 'Progressive Whistle Radius'
PLUCK = 'Progressive Plucking Speed'
BOMBS = 'Bomb Rock Delivery (3)'
BENEFIT_ITEMS = (DELIVERY, FLOWERS, HEAL, WHISTLE, PLUCK)
CAPTAIN = 'Progressive Olimar Speed'
TRAP = 'Bomb Ambush'
PROGG = 'Smoky Progg Ambush'
PRERELEASE = 'Faithful to Prerelease'
TRAP_ITEMS = (TRAP, PROGG, PRERELEASE)
# Per-color maturity replaces Flower Shower in new seeds; Flower Shower keeps its
# item ID so older manifests still run. Tier 1 raises that color to bud, 2 to flower.
MATURITY = {color: f'Progressive {color.title()} Maturity' for color in ('red', 'yellow', 'blue')}
DAY_LENGTH = 'Progressive Day Length'
MATURITY_TIERS = 2
DAY_LENGTH_LIMIT = 10
# Unlocks the Whistle Pluck mod: holding the whistle over sprouts plucks them.
WHISTLE_PLUCK = 'Whistle Pluck'
# Append only: item IDs are assigned by position.
ALL_BENEFIT_ITEMS = BENEFIT_ITEMS + (BOMBS, CAPTAIN, TRAP, PROGG, PRERELEASE) + tuple(MATURITY.values()) + (DAY_LENGTH, WHISTLE_PLUCK)


def benefit_pool(slots, no_heal=False, bomb_weight=0, combined_captain=False, trap_weight=0, progg_weight=0, prerelease_weight=0, maturity=False, day_length=0, whistle_pluck=False):
    fixed = [WHISTLE] * 2 + [CAPTAIN if combined_captain else PLUCK] * 2
    if maturity: fixed += [name for name in MATURITY.values() for _ in range(MATURITY_TIERS)]
    fixed += [DAY_LENGTH] * day_length
    if whistle_pluck: fixed.append(WHISTLE_PLUCK)
    if slots < len(fixed):
        raise ValueError('not enough locations for captain, maturity, day-length and whistle-pluck upgrades')
    # Fixed upgrades first, then 50% deliveries, 25% flowers and 25% heals.
    repeat = (DELIVERY, FLOWERS, DELIVERY) if no_heal else (DELIVERY, FLOWERS, DELIVERY, HEAL)
    if bomb_weight: repeat = (DELIVERY, DELIVERY, FLOWERS) + (BOMBS,) * bomb_weight
    # Maturity seeds drop Flower Shower from the filler mix.
    if maturity: repeat = tuple(n for n in repeat if n != FLOWERS)
    repeat += (TRAP,) * trap_weight + (PROGG,) * progg_weight + (PRERELEASE,) * prerelease_weight
    return fixed + [repeat[i % len(repeat)] for i in range(slots - len(fixed))]


def benefit_state(manifest, inventory):
    if not manifest.get('benefit_items'): return ''
    names = BENEFIT_ITEMS + ((BOMBS,) if manifest.get('bomb_rock_weight') or manifest.get('bomb_trap_weight') or manifest.get('progg_trap_weight') or manifest.get('prerelease_trap_weight') else ()) + ((TRAP,) if manifest.get('bomb_trap_weight') or manifest.get('progg_trap_weight') or manifest.get('prerelease_trap_weight') else ()) + ((PROGG,) if manifest.get('progg_trap_weight') or manifest.get('prerelease_trap_weight') else ())
    if manifest.get('prerelease_trap_weight'): names += (PRERELEASE,)
    if manifest.get('combined_captain'): names = tuple(CAPTAIN if n == PLUCK else n for n in names)
    state = ' BENEFITS ' + ' '.join(str(min(2, inventory.get(n, 0)) if n in (WHISTLE, PLUCK, CAPTAIN)
                                       else inventory.get(n, 0)) for n in names)
    if manifest.get('progressive_maturity'):
        # Native color order: blue, red, yellow.
        state += ' MATURITY ' + ' '.join(str(min(MATURITY_TIERS, inventory.get(MATURITY[c], 0))) for c in ('blue', 'red', 'yellow'))
    if manifest.get('progressive_day_length'):
        state += f" DAYLENGTH {min(manifest['progressive_day_length'], inventory.get(DAY_LENGTH, 0))}"
    if manifest.get('whistle_pluck_item'):
        state += f" WHISTLEPLUCK {min(1, inventory.get(WHISTLE_PLUCK, 0))}"
    return state


def day_length_percent(manifest, inventory):
    return 100 + manifest.get('day_length_step', 0) * min(manifest.get('progressive_day_length', 0), inventory.get(DAY_LENGTH, 0))



def benefit_lines(manifest, inventory):
    if not manifest.get('benefit_items'): return []
    speed = CAPTAIN if manifest.get("combined_captain") else PLUCK
    label = "MOVE/PLUCK" if manifest.get("combined_captain") else "PLUCK"
    lines = [f"WHISTLE {100 + 25 * min(2, inventory.get(WHISTLE, 0))}%  {label} {100 + 25 * min(2, inventory.get(speed, 0))}%"]
    if manifest.get('progressive_maturity'):
        stage = ('LEAF', 'BUD', 'FLOWER')
        lines.append('MATURITY ' + '  '.join(f"{c.upper()} {stage[min(MATURITY_TIERS, inventory.get(MATURITY[c], 0))]}" for c in MATURITY))
    if manifest.get('progressive_day_length'):
        lines.append(f"DAY LENGTH {day_length_percent(manifest, inventory)}%  ({min(manifest['progressive_day_length'], inventory.get(DAY_LENGTH, 0))}/{manifest['progressive_day_length']})")
    if manifest.get('whistle_pluck_item'):
        lines.append('WHISTLE PLUCK ' + ('ON' if inventory.get(WHISTLE_PLUCK, 0) else 'LOCKED'))
    return lines
