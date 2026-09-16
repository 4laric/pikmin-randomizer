"""Self-contained throughput dashboard; all registry text is escaped."""
from html import escape
import json
import math
from datetime import datetime, timezone


def render_dashboard(report):
    def table(items):
        return '<table>' + ''.join('<tr><th>' + escape(str(k).replace('_', ' ')) + '</th><td>' +
            escape(json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else
                   'unavailable' if v is None else str(v)) + '</td></tr>' for k, v in items.items()) + '</table>'
    throughput = report.get('throughput', {})
    metrics = report.get('metrics', {})
    staffing = report.get('staffing', {})
    oldest = metrics.get('oldest_handoff') or {}
    def number(value, suffix=''):
        return f'{value:.1f}{suffix}' if type(value) in (int, float) and math.isfinite(value) else 'Unavailable'
    cards = [
        ('Integrated slices / hour', number(metrics.get('accepted_slices_per_hour'))),
        ('Oldest handoff', number(oldest['age_seconds'] / 60, ' min') if type(oldest.get('age_seconds')) in (int, float) else 'Unavailable'),
        ('RAM used', number(staffing.get('ram_percent'), '%')),
        ('Heavy build utilization', number(metrics.get('heavy_build', {}).get('utilization_percent'), '%')),
        ('Heavy slots available', number(staffing.get('heavy_slots_available'))),
        ('Build leases held', number(staffing.get('heavy_leases'))),
        ('Build concurrency limit', number(staffing.get('heavy_capacity'))),
        ('Build lanes preparing', number(staffing.get('heavy_preparing_lanes'))),
        ('New build admission', 'Paused' if staffing.get('build_admission_paused') else 'Open'),
    ]
    autofill = report.get('autofill')
    autofill = autofill if isinstance(autofill, dict) else {}
    planning = autofill.get('planner_pool', {})
    cards.append(('Planning helpers active / target',
                  str(planning.get('active', 0)) + ' / ' + str(planning.get('target', 0))))
    for label, key in (('Ready backlog', 'ready_count'), ('Active enemy work', 'active_enemy_count'),
                       ('Idle authorized workers', 'idle_workers_count')):
        value = autofill.get(key)
        cards.append((label, str(value) if type(value) is int and value >= 0 else 'Unavailable'))
    headline = '<div class="cards">' + ''.join('<div><span>' + escape(k) + '</span><strong>' + escape(v) + '</strong></div>' for k, v in cards) + '</div>'
    timestamp = datetime.fromtimestamp(report.get('at', 0), timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
    status = 'Unavailable: no autofill observation'
    if autofill:
        status = 'Disabled' if autofill.get('enabled') is False else 'Observed'
    backlog = {'status': status, 'last_observed': autofill.get('updated_at'),
               'planner_helpers': {scope: {'lane': value.get('spec', {}).get('lane', {}).get('lane'),
                    'cycle': value.get('cycle'), 'completed_at': value.get('completed_at'), 'error': value.get('error')}
                    for scope, value in planning.get('scopes', {}).items()},
               'manifest_error': autofill.get('last_manifest_error'),
               'last_refill_request': autofill.get('last_refill_request'),
               'last_planner_request': autofill.get('last_planner_request'),
               'planner_error': autofill.get('last_planner_error')}
    items = autofill.get('items', {})
    items = list(items.values()) if isinstance(items, dict) else items if isinstance(items, list) else []
    blocked = [item for item in items if isinstance(item, dict) and item.get('status') == 'blocked']
    backlog['blocked_items'] = [dict(lane=item.get('lane'), reason=item.get('reason') or 'Reason unavailable')
                                for item in blocked[:10]]
    if len(blocked) > 10:
        backlog['additional_blocked_items'] = len(blocked) - 10
    starving = autofill.get('starvation_seconds')
    warning = ''
    if type(starving) in (int, float) and math.isfinite(starving) and starving > 0 and autofill.get('enabled') is not False:
        warning = '<p class="warning" role="status">Queue starvation: eligible capacity has waited ' + escape(number(starving / 60, ' min')) + ' for prepared work. Prepared backlog refill required.</p>'
    elif autofill.get('last_manifest_error') or autofill.get('last_planner_error'):
        warning = '<p class="warning" role="status">Backlog preparation needs attention. See the recorded reason below.</p>'
    sections = [('Queue pressure', report.get('queue_pressure', {})), ('Acceptance backlog', backlog), ('Metrics', report.get('metrics', {})), ('Staffing', report.get('staffing', {}))]
    sections += [(name.title(), throughput.get(name, {})) for name in
                 ('workstreams', 'workers', 'jobs', 'assignments', 'batches')]
    body = ''.join('<section><h2>' + escape(name) + '</h2>' +
                   table(value if isinstance(value, dict) else {'recommendations': value}) + '</section>'
                   for name, value in sections)
    return '''<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width"><meta http-equiv="refresh" content="15">
<title>Pikmin workflow throughput</title><style>
body{font:15px system-ui;background:#101820;color:#eef4f7;margin:auto;padding:28px;max-width:1400px}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px}.cards div{background:#234138;padding:18px;border-radius:12px}.cards span{display:block;color:#b6d7c8;font-size:13px}.cards strong{display:block;font-size:29px;margin-top:8px}
.warning{border-left:4px solid #efba64;padding:12px;background:#3a3022;color:#ffe0a7}h1{font-size:28px}h2{font-size:19px;color:#a6dfc5}section{background:#1b2933;padding:18px;margin:18px 0;border-radius:12px}
table{border-collapse:collapse;width:100%;table-layout:fixed}th,td{text-align:left;padding:10px;vertical-align:top;border-bottom:1px solid #344651;overflow-wrap:anywhere}th{width:25%}p{color:#b7c8d2}
</style><h1>Pikmin workflow throughput</h1><p>Integrated implementation slices, queue delays, staffing, and provider-reported cost estimates. An accepted slice is not an enemy admission; enemy ADMIT status is unavailable in this dashboard. Missing prices are unavailable, not free. Provisional QA does not grant admission. Refreshes every 15 seconds.</p>''' + '<p>Updated ' + timestamp + '</p>' + headline + warning + body + '</html>'
