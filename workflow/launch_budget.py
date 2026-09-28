"""Durable, bounded launch bursts; provider cooldowns remain independent."""
from .handoff import require


def reserve(reg, action, model, *, burst=1, spacing=15):
    burst = min(4, max(1, int(burst)))
    spacing = max(0, float(spacing))
    with reg.transaction() as state:
        c = reg.control(state)
        item = c['launches'][action]
        if item.get('burst_reservation', {}).get('model') == model:
            return  # Crash replay retains its original token.
        now = reg.clock()
        require(c['providers'].get(model.split('/')[0], 0) <= now and
                c.get('model_limits', {}).get(model, {}).get('until', 0) <= now,
                'Provider/model cooldown active')
        require(c.get('model_launch_after', {}).get(model, 0) <= now, 'Launch burst exhausted')
        windows = c.setdefault('model_launch_windows', {})
        window = windows.get(model, {})
        if window.get('until', 0) <= now:
            window = dict(until=now + spacing, used=0)
            windows[model] = window
        require(window['used'] < burst, 'Launch burst exhausted')
        window['used'] += 1
        c.setdefault('model_launch_after', {})[model] = window['until'] if window['used'] >= burst else 0
        item['model'] = model
        item['burst_reservation'] = dict(model=model, at=now, window_until=window['until'])
        reg.event(state, 'launch_token_reserved', item['lane'], action=action, model=model,
                  used=window['used'], burst=burst, window_until=window['until'])
