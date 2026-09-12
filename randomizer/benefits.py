"""Useful rewards; none are required by the conservative reachability rules."""
DELIVERY = 'Pikmin Delivery (10)'
FLOWERS = 'Flower Shower'
HEAL = 'Captain Heal'
WHISTLE = 'Progressive Whistle Radius'
PLUCK = 'Progressive Plucking Speed'
BOMBS = 'Bomb Rock Delivery (3)'
BENEFIT_ITEMS = (DELIVERY, FLOWERS, HEAL, WHISTLE, PLUCK)
ALL_BENEFIT_ITEMS = BENEFIT_ITEMS + (BOMBS,)


def benefit_pool(slots, no_heal=False, bomb_weight=0):
    if slots < 4:
        raise ValueError('not enough locations for captain upgrades')
    # Two upgrades each, then 50% deliveries, 25% flowers and 25% heals.
    repeat = (DELIVERY, FLOWERS, DELIVERY) if no_heal else (DELIVERY, FLOWERS, DELIVERY, HEAL)
    if bomb_weight: repeat = (DELIVERY, DELIVERY, FLOWERS) + (BOMBS,) * bomb_weight
    return [WHISTLE] * 2 + [PLUCK] * 2 + [repeat[i % len(repeat)] for i in range(slots - 4)]


def benefit_state(manifest, inventory):
    if not manifest.get('benefit_items'): return ''
    return ' BENEFITS ' + ' '.join(str(min(2, inventory.get(n, 0)) if n in (WHISTLE, PLUCK)
                                      else inventory.get(n, 0)) for n in (ALL_BENEFIT_ITEMS if manifest.get('bomb_rock_weight', 0) else BENEFIT_ITEMS))


def benefit_lines(manifest, inventory):
    if not manifest.get('benefit_items'): return []
    return [f"WHISTLE {100 + 25 * min(2, inventory.get(WHISTLE, 0))}%  PLUCK {100 + 25 * min(2, inventory.get(PLUCK, 0))}%"]
