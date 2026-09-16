"""Self-contained throughput dashboard; all registry text is escaped."""
from html import escape
import json
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
        return 'Unavailable' if value is None else f'{value:.1f}{suffix}'
    cards = [
        ('Accepted / hour', number(metrics.get('accepted_slices_per_hour'))),
        ('Oldest handoff', number(oldest.get('age_seconds', 0) / 60, ' min')),
        ('RAM used', number(staffing.get('ram_percent'), '%')),
        ('Heavy build utilization', number(metrics.get('heavy_build', {}).get('utilization_percent'), '%')),
        ('Heavy slots available', str(staffing.get('heavy_slots_available', 'Unavailable'))),
    ]
    headline = '<div class="cards">' + ''.join('<div><span>' + escape(k) + '</span><strong>' + escape(v) + '</strong></div>' for k, v in cards) + '</div>'
    timestamp = datetime.fromtimestamp(report.get('at', 0), timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
    sections = [('Metrics', report.get('metrics', {})), ('Staffing', report.get('staffing', {}))]
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
h1{font-size:28px}h2{font-size:19px;color:#a6dfc5}section{background:#1b2933;padding:18px;margin:18px 0;border-radius:12px}
table{border-collapse:collapse;width:100%;table-layout:fixed}th,td{text-align:left;padding:10px;vertical-align:top;border-bottom:1px solid #344651;overflow-wrap:anywhere}th{width:25%}p{color:#b7c8d2}
</style><h1>Pikmin workflow throughput</h1><p>Accepted results, queue delays, staffing, and provider-reported cost estimates. Missing prices are unavailable, not free. Provisional QA does not grant admission. Refreshes every 15 seconds.</p>''' + '<p>Updated ' + timestamp + '</p>' + headline + body + '</html>'
