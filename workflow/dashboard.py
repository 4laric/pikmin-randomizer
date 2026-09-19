"""Self-contained throughput dashboard; all registry text is escaped."""
from html import escape
import json
import math
from datetime import datetime, timezone

TERMINAL = {'completed', 'superseded', 'released', 'cancelled', 'closed', 'integrated', 'rejected',
            'expired', 'exited', 'failed', 'resolved', 'done'}
STAMPS = ('at', 'created_at', 'queued_at', 'requested_at', 'assigned_at', 'dispatched_at', 'parked_at',
          'completed_at', 'closed_at', 'superseded_at', 'reassigned_at', 'released_at', 'cancelled_at', 'updated_at')
RECENT_SECONDS, RECENT_LIMIT = 6 * 3600, 200


def stamped(value):
    found = [value.get(k) for k in STAMPS if isinstance(value, dict) and type(value.get(k)) in (int, float)
             and math.isfinite(value.get(k))]
    return max(found) if found else None


def bounded(items, now, *, seconds=RECENT_SECONDS, limit=RECENT_LIMIT, related=None):
    """Every active record plus at most `limit` terminal/unstatused records newer than `seconds`.
    related(record) names a linked record whose stamps also date it (a job by its assignment).

    Publication only: the registry keeps every record; (published, total) says what was left out."""
    if not isinstance(items, dict):
        return items, None
    def stamp(value):
        found = [t for t in (stamped(value), stamped(related(value)) if related else None) if t is not None]
        return max(found) if found else None
    def active(value):
        status = value.get('status', value.get('state')) if isinstance(value, dict) else None
        return isinstance(status, str) and status not in TERMINAL
    recent = sorted(((stamp(v), k) for k, v in items.items() if isinstance(v, dict) and not active(v)
                     and stamp(v) is not None and stamp(v) >= now - seconds), reverse=True)[:limit]
    keep = {k for _, k in recent} | {k for k, v in items.items() if active(v)}
    return {k: v for k, v in items.items() if k in keep}, dict(published=len(keep), total=len(items))


def publishable(report, *, seconds=RECENT_SECONDS, limit=RECENT_LIMIT):
    """Bound the historical maps of a status report (jobs, assignments, costs, batches, snapshots,
    dispositions, autofill items) to active and recent records; counts record the omission."""
    now = report.get('at', 0)
    omitted = {}
    throughput = dict(report.get('throughput') or {})
    assignments = throughput.get('assignments') if isinstance(throughput.get('assignments'), dict) else {}
    # Live jobs carry only queued_at; a finished job is dated by its assignment's completion.
    linked = dict(jobs=lambda job: assignments.get(job.get('assignment')) if isinstance(job.get('assignment'), str) else None)
    for name in ('jobs', 'assignments', 'costs', 'batches', 'snapshots', 'dispositions'):
        throughput[name], counts = bounded(throughput.get(name, {}), now, seconds=seconds, limit=limit,
                                           related=linked.get(name))
        if counts: omitted['throughput.' + name] = counts
    autofill = dict(report.get('autofill') or {})
    if 'items' in autofill:
        autofill['items'], counts = bounded(autofill['items'], now, seconds=seconds, limit=limit)
        if counts: omitted['autofill.items'] = counts
    return dict(report, throughput=throughput, autofill=autofill,
                publication=dict(recent_seconds=seconds, recent_limit=limit, maps=omitted,
                                 basis='Active records plus recent terminal ones; the registry keeps every record.'))


def render_stuck(stuck):
    """Needs you and the blocked-lane groups from workflow.inspect (already bounded by the publisher)."""
    if not isinstance(stuck, dict): return ''
    if stuck.get('error') or 'needs_you' not in stuck:  # A failed view is never shown as all-clear.
        return ('<section class="needs-you"><h2>Needs you <span>?</span></h2><p class="warning">Needs you unavailable: ' +
                escape(str(stuck.get('error') or 'no stuck view published')[:400]) +
                '; run <code>workflow_module.py inspect stuck</code>.</p></section>')
    def minutes(value):
        return '?' if type(value) not in (int, float) else '%d min' % (value // 60) if value < 7200 else '%.1f h' % (value / 3600)
    items = list(stuck.get('needs_you') or []) + [dict(r, machine=True) for r in stuck.get('machine') or []]
    html = '<section class="needs-you"><h2>Needs you <span>' + str(len(items)) + '</span></h2>'
    if not items: html += '<p>Nothing waits on you.</p>'
    for r in items:
        who = r.get('lane') or ', '.join(r.get('lanes') or []) or 'machine-wide'
        facts = ' · '.join(s for s in (minutes(r.get('age_seconds')) + ' old' if r.get('age_seconds') is not None else '',
            'asked %dx' % r['asked'] if r.get('asked') else '', '%d downstream' % r['downstream'] if r.get('downstream') else '') if s)
        html += ('<article><div class="item-heading"><strong>' + escape(str(who)) + '</strong><span>' + escape(str(r.get('kind'))) +
                 (' · ' + escape(facts) if facts else '') + '</span></div><p>' + escape(str(r.get('what'))[:400]) +
                 '</p><p class="note">Next: ' + escape(str(r.get('next'))) + '</p></article>')
    omitted = sum((stuck.get('omitted') or {}).get(k) or 0 for k in ('needs_you', 'machine'))
    if omitted: html += '<p class="note">' + str(omitted) + ' more: run <code>workflow_module.py inspect needs-you</code>.</p>'
    groups = stuck.get('groups') or []
    html += ('<details id="stuck-groups"><summary>Blocked lanes by blocker <span>' + escape(str(stuck.get('blocked', '?'))) +
             ' lanes · ' + escape(str(stuck.get('total_groups', len(groups)))) + ' blockers · ' +
             escape(str(len(stuck.get('parked') or []))) + ' parked</span></summary><div class="detail-body">')
    for g in groups:
        owner = (' · owner ' + str(g['owner'])) if g.get('owner') else ''
        html += ('<article><div class="item-heading"><strong>' + escape(str(g.get('label'))) + ' · ' + str(g.get('count')) +
                 ' lanes</strong><span>' + escape(str(g.get('owner_state')) + owner) + '</span></div><p>' +
                 escape(str(g.get('accountable')) + ': ' + str(g.get('next_action'))) + '</p><p class="note">' +
                 escape(', '.join(g.get('lanes') or [])) + '</p></article>')
    if stuck.get('cycles'):
        html += '<p class="warning">Circular waits: ' + escape('; '.join(' -> '.join(c) for c in stuck['cycles'])) + '</p>'
    return html + '<p class="note">Full view: <code>workflow_module.py inspect stuck</code>.</p></div></details></section>'


def render_delivery(delivery):
    """Done work by delivery class per repository (workflow.shipping), bounded; undeclared config is said, not guessed."""
    if not isinstance(delivery, dict): return ''
    if delivery.get('error') or 'repos' not in delivery:
        return ('<section class="delivery"><h2>Delivery</h2><p class="warning">Delivery view unavailable: ' +
                escape(str(delivery.get('error') or 'not published')[:400]) +
                '; run <code>workflow_module.py inspect delivery</code>.</p></section>')
    def hours(value):
        return '?' if type(value) not in (int, float) else '%.1f h' % (value / 3600)
    lanes = delivery.get('lanes') or {}
    html = ('<section class="delivery"><h2>Delivery <span>' + escape(str(lanes.get('done', '?'))) + ' done · ' +
            escape(str(lanes.get('receipts', '?'))) + ' with receipts · ' + escape(str(lanes.get('done-no-code', '?'))) +
            ' done-no-code · ' + escape(str(lanes.get('done-unreceipted', '?'))) + ' done-unreceipted</span></h2>')
    if lanes.get('done-unreceipted'):
        keys = [str(k) for k in (lanes.get('unreceipted_lanes') or [])[:10]]
        html += ('<p class="warning">' + escape(str(lanes['done-unreceipted'])) + ' done lanes carry code no integration '
                 'receipt tracks (not counted as unpushed or unshipped): ' + escape(', '.join(keys)[:400]) +
                 (', …' if lanes['done-unreceipted'] > len(keys) else '') + '</p>')
    html += '<div class="cards">'
    for name, repo in (delivery.get('repos') or {}).items():
        counts = repo.get('counts') or {}
        if not counts and not repo.get('error'): continue
        unpushed, oldest = repo.get('unpushed') or {}, repo.get('oldest_unshipped')
        facts = [', '.join('%s %s' % (k, counts[k]) for k in sorted(counts)[:8]) or 'no receipts']
        if repo.get('error'): facts.append('unverifiable: ' + str(repo['error'])[:200])
        facts.append('unpushed receipts %s%s' % (unpushed.get('count', '?'), ' · oldest ' + hours((unpushed.get('oldest') or {}).get(
            'age_seconds')) if unpushed.get('oldest') else ''))
        facts.append('oldest unshipped: ' + (str(oldest) if not isinstance(oldest, dict) else
                                             '%s (%s, %s)' % (oldest.get('lane'), oldest.get('cls'), hours(oldest.get('age_seconds')))))
        for label in ('line', 'target'):
            value = repo.get(label)
            facts.append('%s %s' % (label, value if not isinstance(value, dict) else '%s at %s' % (value.get('ref'), str(value.get('tip'))[:12])))
        divergence = repo.get('divergence')
        if isinstance(divergence, dict):
            facts.append('line %s ahead / %s behind target · conflicts %s' % (divergence.get('ahead'), divergence.get('behind'),
                         divergence.get('conflicts') if divergence.get('conflicts') is not None else 'skipped'))
        remote = repo.get('remote') or {}
        if remote and not remote.get('off_disk'):
            facts.append('push remote %s is not off-disk: nothing counts as pushed' % remote.get('name'))
        html += ('<div><span>' + escape(name) + '</span><strong>' + escape(str(unpushed.get('count', '?'))) +
                 ' unpushed</strong><p class="note">' + '<br>'.join(escape(f) for f in facts) + '</p></div>')
    return html + '</div><p class="note">Full view: <code>workflow_module.py inspect delivery</code>; choose lines with ' \
                  '<code>inspect delivery-suggest</code>.</p></section>'


def render_dashboard(report):
    def table(items):
        return '<table>' + ''.join('<tr><th>' + escape(str(k).replace('_', ' ')) + '</th><td>' +
            escape(json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else
                   'unavailable' if v is None else str(v)) + '</td></tr>' for k, v in items.items()) + '</table>'
    throughput = report.get('throughput', {})
    metrics = report.get('metrics', {})
    staffing = report.get('staffing', {})
    spend = report.get('hourly_spend', {})
    amount = spend.get('amount')
    spend_label = (f"${amount:.2f} USD" + (' · partial' if spend.get('status') == 'partial' else '')
                   if type(amount) in (int, float) and math.isfinite(amount) else 'Unavailable')
    if spend_label == 'Unavailable':
        subtotal = metrics.get('costs', {}).get('recorded_by_currency', {}).get('USD')
        if type(subtotal) in (int,float) and math.isfinite(subtotal):
            spend_label = f'${subtotal:.2f} USD · partial logs only'
    oldest = metrics.get('oldest_handoff') or {}
    def number(value, suffix=''):
        return f'{value:.1f}{suffix}' if type(value) in (int, float) and math.isfinite(value) else 'Unavailable'
    autofill = report.get('autofill')
    autofill = autofill if isinstance(autofill, dict) else {}
    planning = autofill.get('planner_pool', {})
    admission = report.get('monster_admission', {})
    admitted, total = admission.get('admitted'), admission.get('total')
    known = (type(admitted) is int and type(total) is int and 0 <= admitted <= total and total > 0)
    milestone = '<section class="admission"><div><p class="eyebrow">Monster families admitted</p>'
    milestone += ('<div class="admission-count">' + str(admitted) + '<span> / ' + str(total) + '</span></div>'
                  if known else '<div class="admission-count">Unavailable</div>')
    milestone += '<p>Playable source identities · variants counted separately</p></div><div class="admission-progress">'
    if known:
        milestone += '<progress aria-label="Monster admission progress" value="' + str(admitted) + '" max="' + str(total) + '"></progress>'
        milestone += '<p>' + str(round(100 * admitted / total)) + '% admitted · ' + str(total - admitted) + ' to go</p>'
    else:
        milestone += '<p>Admission records unavailable</p>'
    milestone += '<details id="monster-admission"><summary>Admitted monsters and counting rules</summary><p>'
    milestone += escape(', '.join(admission.get('names', [])) or 'No admitted names available')
    milestone += '</p><p>Counts canonical admission-contract results across source/variant identities. Plants, projectiles, helpers and non-spawnable bases are excluded. Integrated slices do not count as admission.</p><p>Source: ' + escape(str(admission.get('source') or 'Not configured')) + '</p></details></div></section>'
    def count(key):
        value = autofill.get(key)
        return str(value) if type(value) is int and value >= 0 else 'Unavailable'
    cards = [
        ('Verified consumer unblocks / hour', number(metrics.get('consumer_verification', {}).get('verified_unblocks_per_hour'))),
        ('Integrated slices / hour', number(metrics.get('accepted_slices_per_hour'))),
        ('Ready backlog', count('ready_count')),
        ('Oldest handoff', number(oldest['age_seconds'] / 60, ' min') if type(oldest.get('age_seconds')) in (int, float) else 'Unavailable'),
    ]
    audits = report.get('admission_reconciliation', [])
    if audits:
        milestone += '<details><summary>Admitted families with outstanding lane work (' + str(len(audits)) + ')</summary>'
        milestone += table({r['lane']:dict(family=r['family'], status=r['status'],
            reason=r['reason'], next_action=r.get('next_action')) for r in audits}) + '</details>'
    coordinator = report.get('worker_activity', {}).get('acceptance-backlog-planner', {})
    headline = '<div class="cards">' + ''.join('<div><span>' + escape(k) + '</span><strong>' + escape(v) + '</strong></div>' for k, v in cards) + '</div>'
    verification=metrics.get('consumer_verification',{})
    headline += '<p>Pending consumer checks: ' + escape(str(verification.get('pending','Unavailable'))) + ' · Unresolved prerequisite groups: ' + escape(str(verification.get('unresolved_repair_groups','Unavailable'))) + '</p>'
    assistance=planning.get('integration_helpers',{})
    headline += ('<section class="integration-assistance"><h2>Integration helpers: <strong>'+
        escape(str(assistance.get('running',0)))+' running / '+escape(str(assistance.get('target',0)))+
        ' target</strong></h2><p>Uses existing workers · expands to '+escape(str(assistance.get('limit',2)))+
        ' for distinct handoffs · '+escape(str(assistance.get('active',0)))+' reserved ('+
        escape(str(assistance.get('queued',0)))+' queued · '+escape(str(assistance.get('report_ready',0)))+
        ' reports ready · '+escape(str(assistance.get('recovery',0)))+' recovering)</p>'+
        '<details id="integration-helper-work"><summary>What integration helpers are preparing</summary>'+ 
        table({row['lane']:dict(worker=row.get('worker'),status=row['status'],handoffs=row['targets'])
               for row in assistance.get('workers',[])})+'</details></section>')
    timestamp = datetime.fromtimestamp(report.get('at', 0), timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
    status = 'Unavailable: no autofill observation'
    if autofill:
        status = 'Disabled' if autofill.get('enabled') is False else 'Observed'
    queue = report.get('queue_pressure', {})
    integration = queue.get('stages', {}).get('integration', {}) if isinstance(queue, dict) else {}
    runtime = queue.get('stages', {}).get('runtime', {}) if isinstance(queue, dict) else {}
    backlog = {'status': status, 'last_observed': autofill.get('updated_at'),
               'blocked_handoff_repairs': metrics.get('blocked_handoff_repairs', []),
               'parked_no_progress': metrics.get('no_progress_parked', []),
               'planning_waiting_for_changes': planning.get('sleeping_scopes', {}),
               'coordinator_wait_reason': autofill.get('coordinator_wait_reason'),
               'prerequisite_requests': {k:v for k,v in autofill.get('prerequisite_requests', {}).items()
                                        if v.get('status') in ('pending', 'dispatched', 'exhausted')},
               'prerequisite_links': autofill.get('prerequisite_links', {}),
               'prerequisite_errors': autofill.get('prerequisite_errors', {}),
               'integration_depth': integration.get('depth', 0),
               'integration_oldest_seconds': integration.get('oldest_seconds', 0),
               'runtime_depth': runtime.get('depth', 0),
               'runtime_oldest_seconds': runtime.get('oldest_seconds', 0),
               'active_enemy_lanes': autofill.get('active_enemy_lanes', []),
               'planner_helpers': {scope: {'lane': value.get('spec', {}).get('lane', {}).get('lane'),
                    'cycle': value.get('cycle'), 'completed_at': value.get('completed_at'), 'error': value.get('error')}
                    for scope, value in planning.get('scopes', {}).items()},
               'helper_drain': {key: planning.get(key) for key in ('draining', 'excess', 'reclaimable')},
               'manifest_error': autofill.get('last_manifest_error'),
               'last_refill_request': autofill.get('last_refill_request'),
               'last_planner_request': autofill.get('last_planner_request'),
               'planner_error': autofill.get('last_planner_error')}
    items = autofill.get('items', {})
    items = list(items.values()) if isinstance(items, dict) else items if isinstance(items, list) else []
    blocked = [item for item in items if isinstance(item, dict) and item.get('status') == 'blocked']
    def blocked_age(item):
        blocked_at = item.get('blocked_at')
        now = report.get('at', 0)
        return max(0, now - blocked_at) if type(now) in (int, float) and type(blocked_at) in (int, float) else None
    backlog['blocked_items'] = [dict(lane=item.get('lane'), kind=item.get('dependency_kind'),
                                     age_seconds=blocked_age(item),
                                     reason=item.get('reason') or 'Reason unavailable')
                                for item in blocked]
    starving = autofill.get('starvation_seconds')
    warning = ''
    if type(starving) in (int, float) and math.isfinite(starving) and starving > 0 and autofill.get('enabled') is not False:
        warning = '<p class="warning" role="status">Queue starvation: eligible capacity has waited ' + escape(number(starving / 60, ' min')) + ' for prepared work. Prepared backlog refill required.</p>'
    elif autofill.get('last_manifest_error') or autofill.get('last_planner_error'):
        warning = '<p class="warning" role="status">Backlog preparation needs attention. See the recorded reason below.</p>'
    health = report.get('controller_health', {})
    sections = [('Worker spend by model', spend), ('Queue pressure', report.get('queue_pressure', {})), ('Acceptance backlog', backlog),
                ('Stage timing', metrics.get('stage_timing', {})),
                ('Metrics', report.get('metrics', {})), ('Staffing', report.get('staffing', {})),
                ('Controller health', health), ('Worker activity', report.get('worker_activity', {}))]
    sections += [(name.title(), throughput.get(name, {})) for name in
                 ('workstreams', 'workers', 'jobs', 'assignments', 'batches')]
    queue_summary = {
        'Ready awaiting worker': count('awaiting_worker_count'),
        'Active enemy work': count('active_enemy_count'),
        'Waiting for integration': integration.get('depth', 0),
        'Handoffs needing repair': len(metrics.get('blocked_handoff_repairs', [])),
        'Integrator standby reports': len(metrics.get('parked_integration_reports', [])),
        'Parked, no progress': len(metrics.get('no_progress_parked', [])),
    }
    planning_summary = {
        'Waiting for input changes': len(planning.get('sleeping_scopes', {})),
        'Backlog coordinator': coordinator.get('status', 'No active session'),
    }
    if planning.get('draining'):
        planning_summary['Draining / reclaimable'] = str(planning.get('excess', 0)) + ' / ' + str(planning.get('reclaimable', 0))
    capacity_summary = {
        'Worker spend · last 60 min': spend_label,
        'RAM used': number(staffing.get('ram_percent'), '%'),
        'Build leases / limit': str(staffing.get('heavy_leases', 'Unavailable')) + ' / ' + str(staffing.get('heavy_capacity', 'Unavailable')),
        'Build slots available': staffing.get('heavy_slots_available'),
        'Build admission': staffing.get('build_admission_pause_reason') or 'Open',
        'Build lanes preparing': staffing.get('heavy_preparing_lanes'),
        'New build admission': 'Paused' if staffing.get('build_admission_paused') else 'Open',
        'Available workers': autofill.get('available_workers', staffing.get('available_workers')),
        'Workers matching ready work': autofill.get('workers_matching_ready_work', autofill.get('compatible_idle_workers',
            staffing.get('workers_matching_ready_work', staffing.get('compatible_idle_workers')))),
    }
    helper_breakdown = ' &middot; '.join(
        '<span>' + escape(str(planning.get(key, 0))) + ' ' + label + '</span>'
        for key, label in [('running', 'running'), ('queued', 'queued'), ('prepared', 'prepared / awaiting worker'),
                           ('report_ready', 'reports ready'), ('recovery', 'recovering')])
    helper_summary = ('<div class="helper-summary"><strong>Helper reservations: ' +
        escape(str(planning.get('active', 0))) + '</strong><span> / ' +
        escape(str(planning.get('target', 0))) + ' target</span>' +
        '<div class="note">Of that total: ' + helper_breakdown + '</div>' +
        '<details><summary>What is included?</summary><p>Reservations include running and queued sessions, '
        'reports awaiting release, and recovery. These are parts of the total, not additional workers. '
        'Includes ' + escape(str(planning.get('integration_support_active', 0))) +
        ' integration helpers. A report-ready worker is released after verified shutdown.</p></details></div>')
    overview = '<div class="overview">' + ''.join(
        '<section><h2>' + name + '</h2>' + (helper_summary if name == 'Planning' else '') + table(values) +
        ('<p class="note">' + escape(planning.get('target_reason', 'Not yet observed')) + '</p>' if name == 'Planning' else '') +
        ('<p class="note">Provider-reported worker cost estimate; excludes Codex and other account usage. Unpriced messages are not counted as free.</p>' if name == 'Capacity' else '') +
        '</section>' for name, values in [('Queue', queue_summary), ('Planning', planning_summary), ('Capacity', capacity_summary)]) + '</div>'
    roster = report.get('worker_roster')
    workforce = ''
    delivery = report.get('delivery_audit', {})
    if delivery:
        workforce += '<section><h2>Blocking prerequisites</h2><p>' + escape(str(len(delivery.get('unclassified', [])))) + ' blocked lanes still need complete dependency classification.</p>'
        for group in delivery.get('groups', [])[:3]:
            workforce += '<p><strong>' + escape(str(group['producer'])) + '</strong> · ' + str(len(group['consumers'])) + ' consumers · owner: ' + escape(str(group['owner'])) + '<br>' + escape('; '.join(sorted({r['phase'].replace('_', ' ') for r in group['requirements']}))) + '</p>'
        workforce += '</section>'
    if isinstance(roster, dict):
        workforce += '<section class="workforce"><h2>Total workers: ' + escape(str(roster.get('total', 'Unavailable'))) + '</h2><div class="worker-counts">' + ''.join(
            '<span><strong>' + escape(str(value)) + '</strong> ' + escape(str(label)) + '</span>'
            for label, value in roster.get('counts', {}).items()) + '</div>'
        workforce += '<p class="note">Blocked lanes: ' + escape(str(roster.get('blocked_lanes', '?'))) + ' &middot; Parked lanes (capacity released): ' + escape(str(roster.get('parked_lanes', '?'))) + ' &middot; Available workers: ' + escape(str(roster.get('available_workers', '?'))) + '</p>'
        workforce += '<details id="worker-roster"><summary>What each worker is doing</summary><div class="roster-scroll"><table class="roster"><thead><tr><th>Worker</th><th>Status</th><th>Task</th><th>Latest update</th></tr></thead><tbody>'
        for worker in roster.get('workers', []):
            task = str(worker.get('role', 'Unknown'))
            if worker.get('issue'): task += ' · #' + str(worker['issue'])
            lane = str(worker.get('lane', ''))
            observation = str(worker.get('activity', 'Activity unavailable'))
            if worker.get('activity_age_seconds') is not None:
                observation += ' · ' + number(worker['activity_age_seconds'] / 60, ' min ago')
            additional = worker.get('other_unfinished_lanes', 0)
            if additional: observation += ' · ' + str(additional) + ' other unfinished lane(s)'
            workforce += '<tr><td>' + escape(str(worker.get('worker', ''))) + '</td><td>' + escape(str(worker.get('status', 'Unknown'))) + '</td><td>' + escape(task) + '<small>' + escape(lane) + '</small></td><td>' + escape(str(worker.get('detail', ''))) + '<small>' + escape(observation) + '</small></td></tr>'
        workforce += '</tbody></table></div></details><p class="note">One row per registered worker. Queued work is not a running session; activity observations are shown separately.</p></section>'
    attention = []
    export_rows={r['lane']:r for r in report.get('export_preparation',[])}
    for repair in metrics.get('blocked_handoff_repairs', []):
        prep=export_rows.get(repair.get('lane'))
        label=('Export preparation · '+prep['status']+ ' · '+str(prep.get('worker') or prep.get('helper') or 'unassigned')
               if prep else 'Repair · '+str(repair.get('status','blocked')))
        attention.append((repair.get('lane', 'Handoff'), label, repair.get('reason', '')))
    for item in backlog['blocked_items']:
        attention.append((item['lane'] or 'Unnamed lane', str(item['kind'] or 'Blocked'), item['reason']))
    attention_html = ''
    if attention:
        attention_html = '<details class="attention" id="attention"><summary>Needs attention <span>' + str(len(attention)) + ' items</span></summary><div class="detail-body">' + ''.join(
            '<article><div class="item-heading"><strong>' + escape(str(lane)) + '</strong><span>' + escape(str(kind)) + '</span></div><p>' + escape(str(reason)) + '</p></article>'
            for lane, kind, reason in attention) + '</div></details>'
    stuck_html = render_stuck(report.get('stuck')) + render_delivery(report.get('delivery'))
    body = '<div class="diagnostics"><h2>Inspect details</h2><p>Expand a section for individual lanes, evidence, and scheduling decisions.</p>' + ''.join(
        '<details id="detail-' + str(i) + '"><summary>' + escape(name) + '</summary><div class="detail-body">' +
        table(value if isinstance(value, dict) else {'recommendations': value}) + '</div></details>'
        for i, (name, value) in enumerate(sections)) + '</div>'
    return '''<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width"><meta http-equiv="refresh" content="15">
<title>Pikmin workflow throughput</title><style>
*{box-sizing:border-box}body{font:14px/1.5 system-ui;background:#101820;color:#eef4f7;margin:auto;padding:32px;max-width:1400px}
.admission{display:flex;align-items:center;gap:48px;padding:24px 28px;border:1px solid #426c59;border-radius:14px;background:linear-gradient(110deg,#193c30,#172b31);margin-bottom:24px}.admission-count{font-size:clamp(48px,7vw,88px);line-height:1.1;font-weight:750;letter-spacing:-.055em;color:#bdf5ce;font-variant-numeric:tabular-nums}.admission-count span{color:#89a89c;font-size:.6em;font-weight:450}.admission p{margin:8px 0;font-size:12px}.admission-progress{flex:1;min-width:0}.admission progress{display:block;width:100%;height:16px;accent-color:#98e4af;border:0;border-radius:20px;overflow:hidden;background:#293f3b}.admission progress::-webkit-progress-bar{background:#293f3b}.admission progress::-webkit-progress-value{background:#98e4af;border-radius:20px}.admission progress::-moz-progress-bar{background:#98e4af}.admission details{font-size:12px;border:0}@media(max-width:650px){.admission{display:block;padding:20px}.admission-progress{margin-top:20px}}
.integration-assistance{padding:18px 24px;margin:20px 0;border:1px solid #426c80;border-radius:12px;background:#182f3b}.integration-assistance h2{font-size:18px;margin:0}.integration-assistance h2 strong{font-size:32px;color:#b9eaff;font-variant-numeric:tabular-nums}.integration-assistance p{margin:6px 0}.integration-assistance details{border:0}
.workforce{margin:18px 0;padding-bottom:8px;border-bottom:1px solid #344651}.worker-counts{display:flex;flex-wrap:wrap;gap:8px 22px;color:#b8c8d2}.worker-counts strong{color:#eef4f7}.roster-scroll{overflow-x:auto}.roster{min-width:740px}.roster th:nth-child(1){width:13%}.roster th:nth-child(2){width:18%}.roster th:nth-child(3){width:28%}.roster th:nth-child(4){width:41%}.roster small{display:block;color:#8fa5b3;margin-top:5px;font-size:11px}
header{display:flex;align-items:end;justify-content:space-between;gap:24px;margin-bottom:24px}.eyebrow{font-size:11px;letter-spacing:.16em;text-transform:uppercase;color:#90bda9;margin:0 0 5px}h1{font-size:28px;letter-spacing:-.03em;margin:0}header p{margin:0}header small{display:block;color:#8fa5b3}.updated{text-align:right;font-size:12px;color:#adbfca}
.cards{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:1px;background:#344651;border:1px solid #344651;border-radius:12px;overflow:hidden;margin:20px 0}.cards>div{background:#192b30;padding:20px 24px}.cards span{display:block;color:#bdd0cb;font-size:12px}.cards strong{display:block;font-size:30px;font-weight:600;letter-spacing:-.03em;margin-top:4px}
.needs-you{margin:0 0 24px;padding:16px 22px;border:1px solid #8a6a3a;border-radius:12px;background:#231f18}.needs-you h2{color:#efcb92;margin:0 0 8px}.needs-you h2 span{font-size:13px;color:#c7ae83;margin-left:8px}.needs-you article{background:#2b251c}
.delivery{margin:0 0 24px}.delivery h2 span{font-size:13px;color:#92aaa9;margin-left:8px}.delivery .cards{grid-template-columns:repeat(2,minmax(0,1fr));margin:8px 0}.delivery .cards strong{font-size:24px}.delivery .note{margin:6px 0 0}
.warning{border-left:3px solid #efba64;padding:12px 16px;background:#302a21;color:#ffe0a7;border-radius:4px;font-size:13px}.overview{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:24px;border-bottom:1px solid #344651;padding-bottom:20px}.overview section{min-width:0}h2{font-size:16px;font-weight:600;color:#a6dfc5;margin:8px 0 12px}.note{font-size:12px;margin:12px 0;color:#92aaa9}
table{border-collapse:collapse;width:100%;table-layout:fixed}th,td{text-align:left;padding:10px 8px;vertical-align:top;border-bottom:1px solid #293c47;overflow-wrap:anywhere}th{width:28%;font-weight:500;color:#b8c8d2}.overview th{width:65%;padding-left:0;font-size:13px}.overview td{text-align:right;padding-right:0;font-variant-numeric:tabular-nums}.overview tr:last-child th,.overview tr:last-child td{border-bottom:0}p{color:#aebfc9}.diagnostics{margin-top:26px}.diagnostics>p{font-size:12px;margin-top:-6px}
details{border-bottom:1px solid #344651}summary{cursor:pointer;padding:13px 4px;font-weight:500;color:#d8e6ec}summary:hover{color:#a6dfc5}summary:focus-visible{outline:2px solid #a6dfc5;outline-offset:3px}summary span{float:right;color:#c7ae83;font-size:12px}details[open]>summary{color:#a6dfc5}.detail-body{padding:4px 0 18px}.attention{margin-top:10px}.attention summary{color:#efcb92}article{padding:12px 16px;background:#1b2933;margin:8px 0;border-radius:6px}.item-heading{display:flex;justify-content:space-between;gap:12px;overflow-wrap:anywhere}.item-heading span{font-size:12px;color:#efcb92;flex-shrink:0}article p{margin:5px 0 0;font-size:13px}footer{margin-top:24px;font-size:12px;color:#8fa5b3}
@media(max-width:850px){body{padding:20px}.overview{grid-template-columns:1fr;gap:16px}.cards{grid-template-columns:repeat(2,minmax(0,1fr))}.cards>div{padding:16px}.cards strong{font-size:25px}}
@media(max-width:520px){body{padding:16px}header{display:block}.updated{text-align:left;margin-top:10px}.cards{grid-template-columns:repeat(2,minmax(0,1fr))}h1{font-size:24px}.item-heading{display:block}.item-heading span{display:block}th{width:38%}.delivery .cards{grid-template-columns:1fr}}
</style><header><div><p class="eyebrow">Pikmin randomizer · Operations</p><h1>Workflow throughput</h1></div><div class="updated">Updated ''' + timestamp + '''<small>Refreshes every 15 seconds</small></div></header><main>''' + stuck_html + milestone + warning + headline + workforce + overview + attention_html + body + '''</main><footer><details id="reading"><summary>Reading the numbers</summary><p>An accepted slice is not an enemy admission. The headline uses the maintained admission contract; when records cannot be read, enemy ADMIT status is unavailable. Missing prices are unavailable, not free. Provisional QA does not grant admission. Planner reservations include queued work; running helpers are reported separately. Isolated repairs do not count toward actionable integration pressure.</p></details></footer>
<script type="module">
// Preserve expanded diagnostics across the automatic refresh.
for(const panel of document.querySelectorAll('details[id]')){
  try{panel.open=sessionStorage.getItem('workflow-panel:'+panel.id)==='open'}catch{}
  panel.addEventListener('toggle',()=>{try{sessionStorage.setItem('workflow-panel:'+panel.id,panel.open?'open':'closed')}catch{}});
}
</script></html>'''
