"""Executable scope requirements for newly published native implementation."""
from pathlib import PurePosixPath
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
