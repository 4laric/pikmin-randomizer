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
ALL_BENEFIT_ITEMS = BENEFIT_ITEMS + (BOMBS, CAPTAIN, TRAP)


def benefit_pool(slots, no_heal=False, bomb_weight=0, combined_captain=False, trap_weight=0):
    if slots < 4:
        raise ValueError('not enough locations for captain upgrades')
    # Two upgrades each, then 50% deliveries, 25% flowers and 25% heals.
    repeat = (DELIVERY, FLOWERS, DELIVERY) if no_heal else (DELIVERY, FLOWERS, DELIVERY, HEAL)
    if bomb_weight: repeat = (DELIVERY, DELIVERY, FLOWERS) + (BOMBS,) * bomb_weight
    repeat += (TRAP,) * trap_weight
    return [WHISTLE] * 2 + [CAPTAIN if combined_captain else PLUCK] * 2 + [repeat[i % len(repeat)] for i in range(slots - 4)]


def benefit_state(manifest, inventory):
    if not manifest.get('benefit_items'): return ''
    names = BENEFIT_ITEMS + ((BOMBS,) if manifest.get('bomb_rock_weight') or manifest.get('bomb_trap_weight') else ()) + ((TRAP,) if manifest.get('bomb_trap_weight') else ())
    if manifest.get('combined_captain'): names = tuple(CAPTAIN if n == PLUCK else n for n in names)
    return ' BENEFITS ' + ' '.join(str(min(2, inventory.get(n, 0)) if n in (WHISTLE, PLUCK, CAPTAIN)
                                      else inventory.get(n, 0)) for n in names)



def benefit_lines(manifest, inventory):
    if not manifest.get('benefit_items'): return []
    speed = CAPTAIN if manifest.get("combined_captain") else PLUCK
    label = "MOVE/PLUCK" if manifest.get("combined_captain") else "PLUCK"
    return [f"WHISTLE {100 + 25 * min(2, inventory.get(WHISTLE, 0))}%  {label} {100 + 25 * min(2, inventory.get(speed, 0))}%"]
