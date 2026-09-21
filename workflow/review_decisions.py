"""Bounded sole-integrator disposition for shared reviews (reduced mode).

When delegated review workers are disabled, the configured sole
integration owner records each per-file shared-review decision
explicitly through the single fenced dispose_review writer. Decisions
are never inferred or auto-approved, and gameplay acceptance is never
promoted by this path.
"""
from .handoff import nonempty, require


def delegated_review_enabled(config):
    """True while a delegated review worker still owns shared decisions."""
    config = config or {}
    if config.get('shared_review_routing', {}).get('enabled'):
        return True
    throughput = config.get('throughput', {})
    autofill = throughput.get('autofill', {})
    if autofill.get('delegate_shared_reviews'):
        return True
    if autofill.get('planner_pool', {}).get('delegate_shared_reviews'):
        return True
    if config.get('delegate_shared_reviews'):
        return True
    return False


def sole_integrator(config):
    """Explicitly configured sole integration owner, or '' when unset."""
    value = (config or {}).get('sole_integrator', '')
    return value if isinstance(value, str) else ''


def require_sole_authority(config, reviewer):
    """Gate the reviewer identity; delegated mode keeps existing behavior."""
    if delegated_review_enabled(config):
        require(nonempty(reviewer), 'Version, reviewer and explicit review disposition required')
        return 'delegated'
    owner = sole_integrator(config)
    require(nonempty(owner), 'Sole integrator not configured (set sole_integrator)')
    require(reviewer == owner, 'Reviewer is not the configured sole integrator')
    return 'sole'


def check_source_pins(lane, generation, source):
    """Exact producer generation/source pins before touching the writer."""
    require(lane is not None, 'Unknown producer lane')
    require(lane['generation'] == generation, 'Stale producer generation')
    if source is None:
        return
    require(isinstance(source, dict), 'Source pins required')
    if 'root' in source:
        require(source['root'] == lane['root'], 'Producer root source changed')
    if 'native' in source:
        require(source['native'] == lane['native'], 'Producer native source changed')


def apply_sole_disposition(registry, config, key, generation, revision, version,
                           handoff_sha256, file, status, reviewer, evidence, source=None):
    """Record one explicit per-file decision into a new immutable handoff."""
    require(status in ('approved', 'rejected'), 'Explicit per-file disposition required; never inferred')
    require(nonempty(version), 'Disposition version required')
    require_sole_authority(config, reviewer)
    check_source_pins(registry.status()['lanes'].get(key), generation, source)
    record = registry.dispose_review(key, generation, revision, version, handoff_sha256,
                                     file, status, reviewer, evidence)
    lane = registry.status()['lanes'][key]
    require(lane['handoff']['result']['gameplay_accepted'] is False,
            'Disposition must never promote gameplay acceptance')
    return record
