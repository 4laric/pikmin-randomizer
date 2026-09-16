"""Muse packaging lane: candidate-only generated-session content staging.

Covers the near-ADMIT candidate identities whose only missing gate is
identity_spawn: Fuefuki (41), Kurage (57), BombSarai (58), MiniHoudai
(78), plus Waterwraith BlackMan (99) with its owned Tyre helper (98).
Parent family/dependency issue #442; wave #491; waterwraith provider
scope #576 (consumer #572).

Design (honest local candidate staging only):

- Candidate-only: every binding in the layout must be one of the
  candidate identities. Anything else fails closed; this command never stages
  ordinary-pool content and never touches admission allowlists/flags.
- Family installers are used as-is, never forked:
  - Source 58 delegates to :func:experimental.pikmin2_family_install.install_layout
    (the existing shared-contract pikmin2_bombsarai_install module, now
    mapped in IDENTITY_FAMILY). Its manifest/pose hash checks stay
    authoritative inside that installer.
  - Sources 41/57/78/99 have no shared-signature family installer (Fuefuki is
    bespoke install(run_dir)-only; the flying installer covers 29/55/77;
    the cannon installer covers 97 FminiHoudai, not 78 MiniHoudai; the
    batch-2 waterwraith installer is bespoke install(imported, run,
    actors)-only and its family runner stays with consumer #572), so they
    stage as hash-verified candidate sidecars: a validated
    <content_root>/<Enum>/identity.json copy plus a generator actors file.
    No asset conversion, no resolve markers, no admission claims.
  - Source 98 (Tyre) is an owned boss helper, never an independent seeded
    identity: a 98 binding stages only alongside a 99 binding on the same
    target with the same generator, and its sidecar records owner linkage.
- Placement contract (shared with muse-placement l52): the seed's
  p2_layout bindings {target, source_id, enum_name} plus
  actor_bindings mapping every target token to its int native
  generator id. Source id and enum name must agree; a missing/non-int
  generator mapping fails closed. No generated slot UID is prescribed
  here: slot acceptance for 99 awaits the placement99 provider contract,
  recorded on the receipt as pending; duplicate generator ids across
  independent actors are refused (helpers share their owner's actor).
- Cache replay mirrors the family binding: cache_dir/p2muse-<plan digest>
  materializes sidecars without re-reading sources; a matching run receipt is
  a replay (cached=True). The 58 subset reuses the family p2bind-
  cache through the delegated install_layout call.

This module never grants ADMIT and never writes admission markers.
"""

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path

from experimental.pikmin2_staging import StagingError

CANDIDATES = {41: 'Fuefuki', 57: 'Kurage', 58: 'BombSarai', 78: 'MiniHoudai',
              99: 'BlackMan'}
CANDIDATE_BY_NAME = {name.lower(): source_id for source_id, name in CANDIDATES.items()}
FULL_INSTALL_IDS = frozenset({58})
SIDECAR_IDS = frozenset({41, 57, 78, 99})

# Owned boss helper (Waterwraith rollers): never an independent seeded
# identity. Staged only as owner linkage under a same-target BlackMan99
# binding (provider scope #576; family runner stays with consumer #572).
HELPER_SOURCE = 98
HELPER_ENUM = 'Tyre'
HELPER_OWNER = {98: 99}

RECEIPT = 'p2-muse-packaging-receipt.json'
CACHE_KEY_PREFIX = 'p2muse-'
CACHE_RECEIPT = 'cache-receipt.json'
# Slot acceptance for 99 is not prescribed by this provider: no accepted
# generated-slot UID exists until the placement99 provider publishes its
# contract. Recorded on receipts that stage 99/98, never a bind claim.
SLOT_ACCEPTANCE_PENDING = 'pending-placement99-provider'


def _actors_header(enum_name):
    return f'P2_MUSE_{enum_name.upper()}_ACTORS_1'


def actors_filename(enum_name):
    return f'p2-candidate-{enum_name.lower()}-actors.txt'


def identity_filename(enum_name):
    return f'p2-candidate-{enum_name.lower()}-identity.json'


def actors_text(enum_name, pairs):
    rows = [f'{_actors_header(enum_name)} {len(pairs)}']
    rows += [f'{generator} {species}' for generator, species in pairs]
    return ('\n'.join(rows) + '\n').encode('ascii')


def _check_candidate_agreement(target, source_id, enum_name):
    if isinstance(enum_name, str):
        enum_key = enum_name.strip().lower()
    else:
        enum_key = None
    by_name = CANDIDATE_BY_NAME.get(enum_key) if enum_key else None
    if by_name is None:
        raise StagingError(f'not a packaging-candidate identity: {enum_name!r}')
    if source_id != by_name:
        raise StagingError(
            f'binding {target!r}: source id {source_id!r} disagrees with '
            f'enum {enum_name!r} (expected {by_name})')
    return by_name


def _check_waterwraith_helper(target, source_id, enum_name):
    if source_id != HELPER_SOURCE:
        return None
    if not isinstance(enum_name, str) or enum_name.strip().lower() != HELPER_ENUM.lower():
        raise StagingError(
            f'binding {target!r}: source id {source_id!r} disagrees with '
            f'enum {enum_name!r} (expected {HELPER_ENUM!r})')
    return HELPER_OWNER[HELPER_SOURCE]


def _read_identity_source(source_dir, source_id, enum_name):
    path = Path(source_dir) / 'identity.json'
    if not path.is_file():
        raise StagingError(f'missing identity source for {enum_name!r}: {path}')
    try:
        metadata = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError, ValueError) as error:
        raise StagingError(f'unreadable identity source for {enum_name!r}: {path}') from error
    if (not isinstance(metadata, dict) or metadata.get('schema') != 1
            or metadata.get('source_id') != source_id
            or metadata.get('enum_name') != enum_name):
        raise StagingError(f'identity source mismatch for {enum_name!r}: {path}')
    return path


def _actor_generator(actor_bindings, target):
    try:
        return int(actor_bindings[target])
    except KeyError:
        raise StagingError(f'no actor generator binding for target {target!r}') from None
    except (TypeError, ValueError):
        raise StagingError(f'actor generator for target {target!r} must be an int') from None


def _plan_digest(bindings, actor_bindings):
    canonical = {
        'bindings': [dict(b) for b in bindings],
        'actor_bindings': {str(t): int(g) for t, g in actor_bindings.items()},
    }
    return hashlib.sha256(
        json.dumps(canonical, sort_keys=True, separators=(',', ':')).encode('utf-8')).hexdigest()


def _snapshot_sidecars(run, relpaths):
    files = {}
    for relpath in sorted(relpaths):
        path = run / relpath
        if not path.is_file():
            raise StagingError(f'packaging sidecar missing after staging: {relpath}')
        with path.open('rb') as stream:
            files[relpath] = hashlib.file_digest(stream, 'sha256').hexdigest()
    return files


def _replay_sidecars(run, cache_root, marker):
    try:
        saved = json.loads(marker.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError, ValueError) as error:
        raise StagingError('corrupt muse packaging cache; clear it and restage') from error
    if (not isinstance(saved, dict) or saved.get('schema') != 1
            or saved.get('mode') != 'muse-candidate-packaging'):
        raise StagingError('conflicting or partial muse packaging cache; clear it and restage')
    files = saved.get('files')
    if not isinstance(files, dict):
        raise StagingError('muse packaging cache is missing its file manifest; clear it and restage')
    tree = cache_root / 'tree'
    run.mkdir(parents=True, exist_ok=True)
    for relpath, digest in files.items():
        source = tree / relpath
        target = run / relpath
        if not source.is_file():
            raise StagingError(f'muse packaging cache missing {relpath}; clear it and restage')
        with source.open('rb') as stream:
            if hashlib.file_digest(stream, 'sha256').hexdigest() != digest:
                raise StagingError(f'muse packaging cache corrupt for {relpath}; clear it and restage')
        if target.is_file():
            with target.open('rb') as stream:
                if hashlib.file_digest(stream, 'sha256').hexdigest() == digest:
                    continue
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    return saved


def stage_candidates(run, layout, content_root, actor_bindings=None,
                     retail_assets=None, cache_dir=None):
    run = Path(run)
    content_root = Path(content_root)
    bindings = (layout or {}).get('bindings')
    if not isinstance(bindings, list) or not bindings:
        raise ValueError('p2_layout has no bindings')
    actor_bindings = dict(actor_bindings or {})
    plan_digest = _plan_digest(bindings, actor_bindings)

    cache_root = Path(cache_dir) / (CACHE_KEY_PREFIX + plan_digest) if cache_dir is not None else None
    if cache_root is not None and (cache_root / CACHE_RECEIPT).is_file():
        full = [b for b in bindings if b.get('source_id') == 58]
        family_receipt = None
        if full:
            from experimental import pikmin2_family_install as family
            subset_actors = {b['target']: actor_bindings[b['target']] for b in full}
            family_receipt = family.install_layout(
                run, {'bindings': full}, content_root, subset_actors,
                retail_assets, cache_dir)
        saved = _replay_sidecars(run, cache_root, cache_root / CACHE_RECEIPT)
        replayed = dict(saved, cached=True,
                        family_receipt=family_receipt if family_receipt is not None
                        else saved.get('family_receipt'))
        (run / RECEIPT).write_text(
            json.dumps(replayed, indent=2, sort_keys=True) + '\n', encoding='utf-8')
        return replayed

    receipt_path = run / RECEIPT
    if cache_root is None and receipt_path.is_file():
        try:
            existing = json.loads(receipt_path.read_text(encoding='utf-8'))
        except (OSError, json.JSONDecodeError, ValueError) as error:
            raise StagingError('unreadable muse packaging receipt; clear the run tree to restage') from error
        if (isinstance(existing, dict) and existing.get('schema') == 1
                and existing.get('mode') == 'muse-candidate-packaging'
                and existing.get('plan_digest') == plan_digest):
            return dict(existing, cached=True)
        raise StagingError('conflicting or partial muse packaging install detected; refusing to restage')

    # Owned-helper pre-pass (Tyre98): collect same-target BlackMan99 owners.
    # Helpers never stage independently; each needs its owner in this layout
    # with the same generator (shared actor, not a second spawn).
    owner_generators = {}
    for binding in bindings:
        if binding.get('source_id') != 99:
            continue
        owner_target = binding.get('target')
        _check_candidate_agreement(owner_target, 99, binding.get('enum_name'))
        owner_generators[owner_target] = _actor_generator(actor_bindings, owner_target)

    # Validate every binding before writing anything.
    full = []
    sidecar_plans = []
    grouped = {}
    helper_targets = []
    helper_generators = []
    helper_info = None
    for binding in bindings:
        target = binding.get('target')
        source_id = binding.get('source_id')
        enum_name = binding.get('enum_name')
        if _check_waterwraith_helper(target, source_id, enum_name) is not None:
            generator = _actor_generator(actor_bindings, target)
            owner = owner_generators.get(target)
            if owner is None:
                raise StagingError(
                    f'Tyre helper for target {target!r} has no same-target '
                    f'BlackMan99 owner; helpers never stage independently')
            if target in helper_targets:
                raise StagingError(f'duplicate Tyre helper binding for target {target!r}')
            helper_source = content_root / HELPER_ENUM
            if not helper_source.is_dir():
                raise StagingError(f'missing content source for {HELPER_ENUM!r}: {helper_source}')
            identity_path = _read_identity_source(helper_source, HELPER_SOURCE, HELPER_ENUM)
            with identity_path.open('rb') as stream:
                helper_sha = hashlib.file_digest(stream, 'sha256').hexdigest()
            if helper_info is None:
                helper_info = {'source': helper_source, 'source_sha': helper_sha}
            elif helper_info['source_sha'] != helper_sha:
                raise StagingError('Tyre helper identity source changed while staging')
            helper_targets.append(target)
            helper_generators.append(generator)
            continue
        resolved = _check_candidate_agreement(target, source_id, enum_name)
        generator = _actor_generator(actor_bindings, target)
        if resolved in FULL_INSTALL_IDS:
            full.append(binding)
        else:
            source = content_root / CANDIDATES[resolved]
            if not source.is_dir():
                raise StagingError(f'missing content source for {CANDIDATES[resolved]!r}: {source}')
            identity_path = _read_identity_source(source, resolved, CANDIDATES[resolved])
            with identity_path.open('rb') as stream:
                source_sha = hashlib.file_digest(stream, 'sha256').hexdigest()
            grouped.setdefault(resolved, {'generators': [], 'source_sha': source_sha,
                                          'source': source})
            grouped[resolved]['generators'].append((generator, CANDIDATES[resolved]))
            sidecar_plans.append((target, resolved))
    # Duplicate generator ids across independent actors are refused: the native
    # generator seam addresses one actor per generator. Helper rows share
    # their owner's actor by construction and are exempt here.
    seen = {}
    for target, resolved in sidecar_plans:
        generator = int(actor_bindings[target])
        if generator in seen:
            raise StagingError(
                f'duplicate actor generator {generator} for targets '
                f'{seen[generator]!r} and {target!r}')
        seen[generator] = target

    run.mkdir(parents=True, exist_ok=True)

    family_receipt = None
    if full:
        from experimental import pikmin2_family_install as family
        subset_actors = {b['target']: actor_bindings[b['target']] for b in full}
        for target in subset_actors:
            if int(subset_actors[target]) in seen:
                raise StagingError(
                    f'duplicate actor generator {subset_actors[target]} for target {target!r}')
            seen[int(subset_actors[target])] = target
        family_receipt = family.install_layout(
            run, {'bindings': full}, content_root, subset_actors,
            retail_assets, cache_dir)

    # Stage sidecars deterministically: identity copy + actors file per
    # identity, then the owned-helper sidecar. Writes happen only after all
    # validation above succeeded.
    sidecars = {}
    written = []
    try:
        for source_id in sorted(grouped):
            enum_name = CANDIDATES[source_id]
            info = grouped[source_id]
            pairs = sorted(info['generators'])
            actors_payload = actors_text(enum_name, pairs)
            actors_rel = actors_filename(enum_name)
            (run / actors_rel).write_bytes(actors_payload)
            written.append(actors_rel)
            identity_src = info['source'] / 'identity.json'
            identity_rel = identity_filename(enum_name)
            (run / identity_rel).write_bytes(identity_src.read_bytes())
            written.append(identity_rel)
            with (run / identity_rel).open('rb') as stream:
                staged_sha = hashlib.file_digest(stream, 'sha256').hexdigest()
            if staged_sha != info['source_sha']:
                raise StagingError(f'identity sidecar changed while staging: {identity_rel}')
            sidecars[enum_name] = {
                'source_id': source_id,
                'generators': [g for g, _ in pairs],
                'actors_file': actors_rel,
                'actors_sha256': hashlib.sha256(actors_payload).hexdigest(),
                'identity_file': identity_rel,
                'identity_sha256': staged_sha,
            }
        helpers = {}
        if helper_targets:
            pairs = sorted((generator, HELPER_ENUM)
                           for generator in helper_generators)
            actors_payload = actors_text(HELPER_ENUM, pairs)
            actors_rel = actors_filename(HELPER_ENUM)
            (run / actors_rel).write_bytes(actors_payload)
            written.append(actors_rel)
            identity_src = helper_info['source'] / 'identity.json'
            identity_rel = identity_filename(HELPER_ENUM)
            (run / identity_rel).write_bytes(identity_src.read_bytes())
            written.append(identity_rel)
            with (run / identity_rel).open('rb') as stream:
                staged_sha = hashlib.file_digest(stream, 'sha256').hexdigest()
            if staged_sha != helper_info['source_sha']:
                raise StagingError(f'identity sidecar changed while staging: {identity_rel}')
            helpers[HELPER_ENUM] = {
                'source_id': HELPER_SOURCE,
                'owner_source_id': 99,
                'owner_targets': sorted(helper_targets),
                'generators': [g for g, _ in pairs],
                'actors_file': actors_rel,
                'actors_sha256': hashlib.sha256(actors_payload).hexdigest(),
                'identity_file': identity_rel,
                'identity_sha256': staged_sha,
            }
    except BaseException:
        for rel in written:
            (run / rel).unlink(missing_ok=True)
        raise

    files = _snapshot_sidecars(run, written)
    aggregate = dict(schema=1, mode='muse-candidate-packaging', candidate_only=True,
                     plan_digest=plan_digest, bindings=list(bindings),
                     candidates={str(k): v for k, v in CANDIDATES.items()},
                     sidecars=sidecars,
                     family_receipt=family_receipt, files=files,
                     admission='none')
    if helpers:
        aggregate['helpers'] = helpers
        aggregate['slot_acceptance'] = SLOT_ACCEPTANCE_PENDING
    receipt_path.write_text(json.dumps(aggregate, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    if cache_root is not None:
        tree = cache_root / 'tree'
        try:
            for relpath in files:
                destination = tree / relpath
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(run / relpath, destination)
        except BaseException:
            shutil.rmtree(cache_root, ignore_errors=True)
            raise
        (cache_root / CACHE_RECEIPT).write_text(
            json.dumps(aggregate, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    return aggregate


def verify_staging(run, layout=None, actor_bindings=None):
    run = Path(run)
    receipt_path = run / RECEIPT
    receipt = json.loads(receipt_path.read_text(encoding='utf-8'))
    if receipt.get('schema') != 1 or receipt.get('mode') != 'muse-candidate-packaging':
        raise StagingError('not a muse candidate packaging receipt')
    if receipt.get('candidate_only') is not True or receipt.get('admission') != 'none':
        raise StagingError('packaging receipt must stay candidate-only with no admission claim')
    files = receipt.get('files')
    if not isinstance(files, dict):
        raise StagingError('packaging receipt is missing its file manifest')
    for relpath, digest in files.items():
        path = run / relpath
        if not path.is_file():
            raise StagingError(f'staged sidecar missing: {relpath}')
        with path.open('rb') as stream:
            if hashlib.file_digest(stream, 'sha256').hexdigest() != digest:
                raise StagingError(f'staged sidecar hash mismatch: {relpath}')
    if layout is not None and actor_bindings is not None:
        bindings = (layout or {}).get('bindings')
        if receipt.get('plan_digest') != _plan_digest(bindings, dict(actor_bindings)):
            raise StagingError('staged plan digest does not match the given layout/bindings')
        for binding in bindings:
            target = binding.get('target')
            source_id = binding.get('source_id')
            if _check_waterwraith_helper(target, source_id,
                                         binding.get('enum_name')) is not None:
                owners = [b for b in bindings
                          if b.get('target') == target and b.get('source_id') == 99]
                if not owners:
                    raise StagingError(
                        f'Tyre helper for target {target!r} has no same-target '
                        f'BlackMan99 owner')
                generator = int(actor_bindings[target])
                tokens = (run / actors_filename(HELPER_ENUM)).read_text(
                    encoding='ascii').split()
                header = _actors_header(HELPER_ENUM)
                if len(tokens) < 2 or tokens[0] != header or int(tokens[1]) != (len(tokens) - 2) // 2:
                    raise StagingError(f'actors sidecar malformed: {actors_filename(HELPER_ENUM)}')
                ids = [int(tokens[i]) for i in range(2, len(tokens), 2)]
                if generator not in ids:
                    raise StagingError(
                        f'helper generator for target {target!r} missing from staged sidecar')
                continue
            resolved = _check_candidate_agreement(target, source_id,
                                                  binding.get('enum_name'))
            if resolved in FULL_INSTALL_IDS:
                continue
            enum_name = CANDIDATES[resolved]
            tokens = (run / actors_filename(enum_name)).read_text(encoding='ascii').split()
            header = _actors_header(enum_name)
            if len(tokens) < 2 or tokens[0] != header or int(tokens[1]) != (len(tokens) - 2) // 2:
                raise StagingError(f'actors sidecar malformed: {actors_filename(enum_name)}')
            ids = [int(tokens[i]) for i in range(2, len(tokens), 2)]
            if int(actor_bindings[target]) not in ids:
                raise StagingError(
                    f'generator binding for target {target!r} missing from staged sidecar')
    return {'verified': sorted(files), 'receipt': RECEIPT}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--layout', type=Path, required=True,
                        help='JSON file holding the p2_layout mapping')
    parser.add_argument('--content-root', type=Path, required=True)
    parser.add_argument('--actor-bindings', type=Path, required=True,
                        help='JSON object mapping target token to generator id')
    parser.add_argument('--retail', type=Path, default=None)
    parser.add_argument('--cache-dir', type=Path, default=None)
    args = parser.parse_args(argv)
    layout = json.loads(args.layout.read_text(encoding='utf-8'))
    actor_bindings = json.loads(args.actor_bindings.read_text(encoding='utf-8'))
    receipt = stage_candidates(args.run, layout, args.content_root, actor_bindings,
                               args.retail, args.cache_dir)
    print(json.dumps(receipt, sort_keys=True, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
