"""Useful rewards; none are required by the conservative reachability rules."""
DELIVERY = 'Pikmin Delivery (10)'
FLOWERS = 'Flower Shower'
HEAL = 'Captain Heal'
WHISTLE = 'Progressive Whistle Radius'
PLUCK = 'Progressive Plucking Speed'
BENEFIT_ITEMS = (DELIVERY, FLOWERS, HEAL, WHISTLE, PLUCK)


def benefit_pool(slots):
    if slots < 4:
        raise ValueError('not enough locations for captain upgrades')
    # Two upgrades each, then 50% deliveries, 25% flowers and 25% heals.
    repeat = (DELIVERY, FLOWERS, DELIVERY, HEAL)
    return [WHISTLE] * 2 + [PLUCK] * 2 + [repeat[i % 4] for i in range(slots - 4)]


def benefit_state(manifest, inventory):
    if not manifest.get('benefit_items'): return ''
    return ' BENEFITS ' + ' '.join(str(min(2, inventory.get(n, 0)) if n in (WHISTLE, PLUCK)
                                      else inventory.get(n, 0)) for n in BENEFIT_ITEMS)


def benefit_lines(manifest, inventory):
    if not manifest.get('benefit_items'): return []
    return [f"WHISTLE {100 + 25 * min(2, inventory.get(WHISTLE, 0))}%  PLUCK {100 + 25 * min(2, inventory.get(PLUCK, 0))}%"]
