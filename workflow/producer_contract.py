"""Executable scope requirements for newly published native implementation."""
from pathlib import PurePosixPath
import re
from .handoff import require


INSTRUCTION = (
    ' New native implementation/repair proposals require producer_contract: '
    '{kind: engine_change|diagnosis|runtime_check, callsites: [{file,symbol}], '
    'build_membership: [file], consumers: [{lane,command,expected}], deliverable: string}. '
    'For engine_change reserve actual callsite and build-membership files in owned_files; '
    'name the real consumer command and expected behavior. If membership already exists, '
    'still identify and reserve its verification scope. Diagnosis requires concrete pin/ownership '
    'deliverables and is never an engine unblock. Runtime checks identify existing callsites and '
    'membership without claiming to change them. Use canonical scripts/workflow_native_build.py '
    'for leased private builds and scripts/run_pikmin2_fixture.py for bounded staged game runs. '
    'Contract publication is scope validation, not implementation or gameplay acceptance. '
    'Write acceptance criteria the lane itself can pass: a #186 decision belongs in the handoff shared_reviews, '
    'integrator landing and maintained export in remaining_work; criteria requiring them are flagged as circular waits. '
)


def validate(spec, required=False):
    contract = spec.get('producer_contract')
    native_work = spec['lane'].get('native') and spec.get('role') in ('implementation','repair','qa')
    require(not (required and native_work) or contract is not None,
            'New native producer requires producer_contract with real callsites, build membership and consumer check')
    if contract is None: return
    require(isinstance(contract,dict) and contract.get('kind') in ('engine_change','diagnosis','runtime_check'),
            'Explicit producer contract kind required')
    require(isinstance(contract.get('deliverable'),str) and contract['deliverable'].strip(), 'Concrete deliverable required')
    consumers = contract.get('consumers')
    require(isinstance(consumers,list) and consumers, 'Named consuming checks required')
    for consumer in consumers:
        require(isinstance(consumer,dict) and all(isinstance(consumer.get(k),str) and consumer[k].strip()
                for k in ('lane','command','expected')), 'Consumer lane, command and expected behavior required')
    if contract['kind'] == 'diagnosis': return
    calls, builds = contract.get('callsites'), contract.get('build_membership')
    require(isinstance(calls,list) and calls and isinstance(builds,list) and builds,
            'Real engine callsites and build membership required')
    files = list(builds)
    for call in calls:
        require(isinstance(call,dict) and isinstance(call.get('symbol'),str) and call['symbol'].strip(), 'Callsite symbol required')
        files.append(call.get('file'))
    for file in files:
        require(isinstance(file,str) and file.startswith('native/') and '\\' not in file and ':' not in file
                and '..' not in PurePosixPath(file).parts, 'Canonical native scope path required')
        if contract['kind'] == 'engine_change':
            require(file in spec['lane']['owned_files'], 'Engine callsite/build membership must be owned: '+file)


# Acceptance criteria that only another owner can satisfy: a slice holding one can never pass, so it can never
# present a truthful handoff for that owner to act on (a circular wait). They belong in the handoff's
# shared_reviews (a #186 decision) or remaining_work (integrator landing, maintained export).
FOREIGN = (
    (re.compile(r'#\s*186(?:[\s/-]+(?:owner|shared|hook|shared-hook|integrator|landing|wiring|explicit)){0,2}[\s/-]+'
                r'(decisions?|decided|reviews?|reviewed|approvals?|approved|sign-?off|granted)\b|'
                r'\b(decisions?|approvals?|sign-?off)\s+(on|for|of|from|under)\s+#\s*186\b', re.I),
     'shared_reviews', 'requires the #186 shared-hook decision, which a reviewer records'),
    (re.compile(r'\b(is|are|be|been|was|were|gets?|got)\s+landed\b|\blanded\s+(with|on|onto|in|into|by|under)\b|'
                r'\bintegrator\b[^.;]{0,30}?\b(lands?|landing|merges?|integrates?)\b', re.I),
     'remaining_work', 'requires an integrator landing, which only the integration owner performs after a passing handoff'),
    (re.compile(r'\bmaintained (native )?exports?\b|\bexport(ed)? (in)?to (the )?maintained\b|\bfinal(-owner)? export\b', re.I),
     'remaining_work', 'requires the maintained export, which only the integration lead performs'),
)
NEGATED = re.compile(r'\b(no|not|never|without|nor)\b[^.;,]{0,25}$', re.I)


def acceptance_lint(acceptance):
    """Criteria requiring another owner's action, as [{index, criterion, reason, move_to}]. Advisory only."""
    found = []
    for index, text in enumerate(acceptance if isinstance(acceptance, list) else []):
        if not isinstance(text, str): continue
        for pattern, target, reason in FOREIGN:
            hit = next((m for m in pattern.finditer(text) if not NEGATED.search(text[:m.start()])), None)
            if hit:
                found.append(dict(index=index, criterion=text, match=hit.group(0), reason=reason, move_to=target))
                break
    return found
