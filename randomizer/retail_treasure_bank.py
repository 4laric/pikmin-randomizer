"""Prepare a private aggregate asset source; no campaign or actor activation."""
import hashlib
import json
from pathlib import Path

from experimental.pikmin2_assets import archive_files
from experimental.pikmin2_campaign_treasures import source_profiles, POD_SHA256
from experimental.pikmin2_cave import safe_name
from experimental.pikmin2_treasure_catalog import RETAIL_DIGEST
from .campaign_treasures import bounded_model, verified_entries
from .held_treasures import prepare as prepare_held


def prepare(bank, catalog, original, onyons, campaign, held_requests, selected, *, pod_model):
    """Return exact selected-input roles and one master SOURCE, without writes.

    Asset availability does not authenticate a loose placement or floor birth.
    The original floor owner must independently provide those identities.
    """
    bank = Path(bank)
    entries = verified_entries(catalog)
    if not 1 <= len(selected) <= 201 or len(set(selected)) != len(selected) or any(
            identity not in entries for identity in selected):
        raise ValueError('Explicit unique retail asset identities required')
    configs = {kind: bounded_model(bank / 'source/user/Abe/Pellet/us' / f'{kind}_config.txt')
               for kind in ('otakara', 'item')}
    profiles = source_profiles(configs, entries, selected)
    facts_bytes = bounded_model(bank / 'treasure-bank.json')
    if len(facts_bytes) > 4 * 1024 * 1024:
        raise ValueError('Oversized source bank metadata')
    facts = json.loads(facts_bytes.decode('utf-8'))
    if facts.get('schema') != 2:
        raise ValueError('Original profile/provenance bank required')
    roles, rows, models = {}, [], {}
    base = 'p2-original/retail-cargo/'
    digest = lambda data: hashlib.sha256(data).hexdigest()
    for kind, data in configs.items():
        roles[base + f'source/user/Abe/Pellet/us/{kind}_config.txt'] = data
    for name, expected_hash in POD_SHA256.items():
        path = (bank / 'source/user/Kando/pod' / name if name.endswith('.szs') else
                bank / ('pod' if name == 'pot.bmd' else 'pod-texts') / name)
        data = bounded_model(path)
        if digest(data) != expected_hash:
            raise ValueError('Original Pod selected input differs from pinned source')
        roles[base + 'pod/' + name] = data
    receiver_model = bounded_model(pod_model)
    if digest(receiver_model) != 'f562fb2926cc54be8875afb07d2d0effe2f2af7469f9d4ab5c7940917eb8b595':
        raise ValueError('Qualified original Pod conversion required')
    roles['assets/dataDir/courses/pikmin2retailpod/pod.mod'] = receiver_model
    for identity in selected:
        entry, source = entries[identity], profiles[identity]['source']
        source_path = 'user/Abe/Pellet/us/' + safe_name(source['archive'])
        archive = bounded_model(bank / 'source' / source_path)
        original_model = archive_files(archive)[safe_name(source['bmd'])]
        if not 0 < len(original_model) <= 32 * 1024 * 1024:
            raise ValueError('Empty or oversized original model')
        model = bounded_model(bank / (identity + '.mod'))
        fact = facts['selected'][identity]
        if (facts['source_sha256'][source_path] != digest(archive)
                or fact['original_profile'] != source or fact['profile'] != entry
                or fact['original_member_sha256'][source['bmd']] != digest(original_model)
                or fact['converted_sha256'] != digest(model)):
            raise ValueError('Original bank bytes/provenance changed')
        roles[base + identity + '/arc.szs'] = archive
        roles[base + identity + '/original.bmd'] = original_model
        roles['assets/dataDir/courses/pikmin2treasures/' + identity + '.mod'] = model
        models[identity] = bank / (identity + '.mod')
        rows.append(f'{identity} {entry["kind"]} {entry["index"]} {digest(model)} {digest(archive)} {digest(original_model)}')
    if any(request['id'] not in models for request in held_requests):
        raise ValueError('Aggregate bank must include all literal held assets')
    held = prepare_held(original, onyons, campaign, held_requests, catalog, models, bank / 'pod.mod')
    # Bind each leaf model to the same buffer emitted by the aggregate.
    for identity, data in held['models'].items():
        if data != roles['assets/dataDir/courses/pikmin2treasures/' + identity + '.mod']:
            raise ValueError('Held model changed during aggregate staging')
    roles[base + 'held.txt'] = held['descriptor']
    roles['assets/dataDir/courses/pikmin2treasures/pod.mod'] = held['pod']
    roles['p2-original/tutorial.p2c'] = original
    roles['p2-original/tutorial.p2on'] = onyons
    roles['p2-treasure-catalog.txt'] = bounded_model(catalog)
    if digest(roles['p2-treasure-catalog.txt']) != RETAIL_DIGEST:
        raise ValueError('Retail catalogue changed during aggregate staging')
    header = f'P2_TREASURE_RETAIL_1 {RETAIL_DIGEST} {campaign} {held["source_digest"]} {len(rows)}'
    descriptor = ('\n'.join([header, *rows]) + '\n').encode('ascii')
    if len(descriptor) > 65536:
        raise ValueError('Oversized aggregate asset descriptor')
    roles['p2-treasure-placements.txt'] = descriptor
    return dict(roles=roles, descriptor=descriptor, source_digest=digest(descriptor),
                held_digest=held['source_digest'], activated=False)
