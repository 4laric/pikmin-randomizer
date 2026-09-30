"""Hand-played P2 smoke seeds: any playable species on any ordinary slot (#944).

Owner ruling (2026-09-29): smoke seeds ignore the committed placement approvals
(root ``docs/PIKMIN2_ADMITTED_PLACEMENT.json`` ``accepted_slot_uids`` and the
native compiled-in slot list). This script builds an *override* placement
document that assigns the requested species round-robin to an area's ordinary
enemy slots, generates and validates the seed with that start area, stages the
content root from a reusable cache (extracting from the ISO only for species
the cache lacks), writes the actor bindings, and emits a PowerShell launcher
that sets ``PIKMIN_P2_SMOKE_ANY_SLOT=1`` so the native side accepts the seed's
bindings on unapproved slots (``pc_port/pc_p2_smoke_any_slot.h``).

Normal seeds are untouched: nothing here changes the committed document, the
bridge, or the native default (env var unset = full enforcement).

Example (PowerShell)::

    py -3.12 scripts/p2_smoke_seed.py --area foh --slots 4 --near-start `
        --species 58,32 --bosses 94:hope_snagret_pit --seed foh-any-1 `
        --out output/smoke-any/foh-any-1 --iso "C:\\...\\PIKMIN2 for GAMECUBE.iso" `
        --content-cache output/p2-content-cache --exe output/smoke-foh/exe-anyslot/nectar.exe
    & output/smoke-any/foh-any-1/play.ps1

Slot coordinates come from the committed catalogs (``randomizer.campaign_data``
``CAMPAIGN_SLOTS`` and ``randomizer.spawn_data`` ``ADULT_SLOTS``/``GROUP_SLOTS``)
and, optionally, ``P2_PLACEMENT_SLOT`` lines from a native log (``--probe-log``).
The landing site is where the captain starts. It is NOT (0, 0): the Forest of Hope start was measured
at about (-464, 1967) from a native log (wave-3 lane 53), so ``LANDING`` records measured starts and
``--landing X,Z`` overrides any area whose start has not been measured. Every start profile begins on
day 2 (``randomizer.catalog.START_AREAS``), so ``--near-start`` slots default to ``first_day <= 2``:
CONTRIBUTING "Playtest seeds" rule 3 (nothing under test behind a later day).
"""

from __future__ import annotations

import argparse
import json
import math
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# area token -> (generate() starting_area, placement stage index, slot label prefix)
AREAS = {
    'foh': ('forest', 1, 'hope'),
    'forest': ('forest', 1, 'hope'),
    'impact': ('impact', 0, 'impact'),
    'navel': ('navel', 2, 'navel'),
    'spring': ('spring', 3, 'spring'),
}
LANDING_XZ = (0.0, 0.0)  # legacy default for areas whose start is not measured
# Measured captain start (x, z), from native logs. Only measured areas are listed.
LANDING = {'foh': (-464.0, 1967.0), 'forest': (-464.0, 1967.0)}
START_DAY = 2  # every START_AREAS profile is '<area>-day2'
DEFAULT_ASSETS = r'C:\Users\alari\bbft\dist\cohesion\pikmin\assets'
DEFAULT_GATES = ['placement.xyz', 'placement.terrain', 'placement.route', 'bridge.spawn']
SMOKE_ENV = 'PIKMIN_P2_SMOKE_ANY_SLOT'


class SmokeSeedError(ValueError):
    pass


# --- placement helpers (pure; unit-tested) ---------------------------------

def load_default_document():
    return json.loads((ROOT / 'docs' / 'PIKMIN2_ADMITTED_PLACEMENT.json').read_text(encoding='utf-8'))


def ordinary_slots(document, area, max_first_day=None):
    """Ordinary enemy slots of ``area``: unprotected, non-boss, not a held-part
    anchor; document order. Native probe evidence is not required (#948: an
    unprobed slot is a to-do, not a restriction)."""
    if area not in AREAS:
        raise SmokeSeedError(f"unknown area {area!r}; expected one of {sorted(AREAS)}")
    _, stage, _ = AREAS[area]
    held = {int(h['uid']) for h in document.get('held_parts', [])}
    out = []
    for slot in document['slots']:
        if slot['stage'] != stage or slot.get('protected') or slot.get('boss_slot'):
            continue
        if slot['uid'] in held:
            continue
        if max_first_day is not None and int(slot.get('first_day', 0)) > max_first_day:
            continue
        out.append(slot)
    return out


def slot_positions(probe_log_text=None):
    """uid -> [x, y, z] from the committed catalogs, plus optional probe lines."""
    positions = {}
    try:
        from randomizer import campaign_data, spawn_data
        for rows in (campaign_data.CAMPAIGN_SLOTS, spawn_data.ADULT_SLOTS, spawn_data.GROUP_SLOTS):
            for row in rows:
                if 'position' in row:
                    positions.setdefault(int(row['uid']), [float(v) for v in row['position']])
    except ImportError:  # pragma: no cover - catalogs always ship with the repo
        pass
    if probe_log_text:
        from randomizer.p2_placement_probe import capture_markers
        slots, _, _ = capture_markers(probe_log_text)
        for probe in slots:
            if probe.get('slot') and probe.get('position'):
                positions[int(probe['slot'])] = list(probe['position'])
    return positions


def distance_xz(position, origin=LANDING_XZ):
    return math.hypot(position[0] - origin[0], position[2] - origin[1])


def pick_slots(slots, count, near_start=False, positions=None, origin=LANDING_XZ):
    """First ``count`` slots ('all' or None = every slot). With ``near_start``
    the slots are ordered by x/z distance from the landing site; slots without
    a known position sort last (stable)."""
    chosen = list(slots)
    if near_start:
        positions = positions or {}
        def key(slot):
            pos = positions.get(int(slot['uid']))
            return (0, distance_xz(pos, origin)) if pos else (1, 0.0)
        chosen.sort(key=key)
    if count in (None, 'all'):
        return chosen
    count = int(count)
    if count <= 0:
        raise SmokeSeedError('--slots must be a positive integer or "all"')
    if count > len(chosen):
        raise SmokeSeedError(f'requested {count} slots but the area has only {len(chosen)} ordinary slots')
    return chosen[:count]


def assign_round_robin(species, slots):
    """{slot uid: source_id}; species cycle over the slots in order."""
    species = list(species)
    if not species:
        raise SmokeSeedError('--species must list at least one source id')
    if len(set(species)) != len(species):
        raise SmokeSeedError(f'duplicate species in --species: {species}')
    if not slots:
        raise SmokeSeedError('no slots to assign')
    if len(species) > len(slots):
        raise SmokeSeedError(
            f'{len(species)} species but only {len(slots)} slots; every species needs its own slot '
            f'(raise --slots or drop species)')
    return {int(slot['uid']): species[i % len(species)] for i, slot in enumerate(slots)}


def parse_bosses(text):
    """'94:hope_snagret_pit,73:impact_goolix' -> {94: 'hope_snagret_pit'}."""
    bosses = {}
    if not text:
        return bosses
    for item in text.split(','):
        item = item.strip()
        if not item:
            continue
        if ':' not in item:
            raise SmokeSeedError(f'--bosses entries are SOURCE_ID:ARENA_ID, got {item!r}')
        sid, arena = item.split(':', 1)
        try:
            sid = int(sid)
        except ValueError:
            raise SmokeSeedError(f'--bosses source id must be an int, got {sid!r}') from None
        if sid in bosses:
            raise SmokeSeedError(f'boss {sid} listed twice in --bosses')
        bosses[sid] = arena.strip()
    return bosses


def parse_landing(text):
    """'X,Z' -> (x, z)."""
    try:
        x, z = (float(v) for v in text.split(','))
    except ValueError:
        raise SmokeSeedError(f'--landing must be X,Z numbers, got {text!r}') from None
    return (x, z)


def parse_species(text):
    try:
        species = [int(x) for x in text.split(',') if x.strip()]
    except ValueError:
        raise SmokeSeedError(f'--species must be comma-separated ints, got {text!r}') from None
    if not species:
        raise SmokeSeedError('--species must list at least one source id')
    return species


def build_override(document, roster, assignments, bosses=None):
    """Override placement document: each assigned species accepts exactly its
    slots (constraints relaxed to the slot), each listed boss accepts exactly
    its arena's primary slot, every other identity accepts nothing.

    An arena boss (73, 94, ...) listed in ``assignments`` is placed on those
    ordinary slots like any other species (#948, CONTRIBUTING placement rule
    4: the footprint/arena rule is relaxed to the slot for a smoke seed); its
    profile drops ``is_boss`` so the bridge fills it in the ordinary pass.
    A boss may not be both in ``assignments`` and ``bosses``.

    ``roster`` is the validated roster list; ``assignments`` {uid: source_id};
    ``bosses`` {source_id: arena_id}.
    """
    from experimental.pikmin2_enemy_roster import by_id
    from experimental.pikmin2_seed_bridge import arena_boss_ids
    bosses = dict(bosses or {})
    by_source = by_id(roster)
    slots_by_uid = {int(s['uid']): s for s in document['slots']}
    arenas = {a['id']: a for a in document.get('arenas', [])}
    boss_ids = arena_boss_ids(document, roster)
    for uid, sid in assignments.items():
        if uid not in slots_by_uid:
            raise SmokeSeedError(f'slot {uid} is not in the placement document')
        if sid not in by_source:
            raise SmokeSeedError(f'source id {sid} is not in the P2 roster')
        if sid in bosses:
            raise SmokeSeedError(
                f'{sid} ({by_source[sid].enum_name}) is both in --species and --bosses; pick one')
    for sid, arena in bosses.items():
        if sid not in by_source:
            raise SmokeSeedError(f'boss source id {sid} is not in the P2 roster')
        if sid not in boss_ids:
            raise SmokeSeedError(f'{sid} ({by_source[sid].enum_name}) has no arena profile; list it in --species instead')
        if arena not in arenas:
            raise SmokeSeedError(f'unknown arena {arena!r}; known: {sorted(arenas)}')
    uids_by_identity = {}
    for uid, sid in assignments.items():
        uids_by_identity.setdefault(by_source[sid].enum_name, []).append(uid)
    arena_by_identity = {by_source[sid].enum_name: arenas[arena] for sid, arena in bosses.items()}
    out = json.loads(json.dumps(document))
    seen = set()
    for profile in out['profiles']:
        identity = profile['identity']
        seen.add(identity)
        if identity in uids_by_identity:
            uids = sorted(uids_by_identity[identity])
            profile['accepted_slot_uids'] = uids
            if profile.get('is_boss'):
                # #948: ordinary-slot boss for a smoke seed; the arena rule
                # is a real-seed data rule, not a cast list.
                profile['is_boss'] = False
                profile['encounter_descriptor'] = None
                profile['notes'] = (profile.get('notes', '') + ' | #948 smoke override: boss on ordinary slot').strip(' |')
            terrains = list(profile.get('terrains') or [])
            for uid in uids:
                terrain = slots_by_uid[uid]['terrain']
                if terrain not in terrains:
                    terrains.append(terrain)
            profile['terrains'] = terrains
            profile['cohort'] = None
            profile['footprint_radius'] = 0
            profile['min_water_depth'] = 0
            profile['helper_budget'] = 0
            profile['min_first_day'] = 0
            for key in ('requires_flight_space', 'requires_burrow_ground', 'requires_home',
                        'requires_projectile_corridor', 'requires_corpse_route',
                        'requires_renewable_slot'):
                profile[key] = False
            if not profile.get('accepted_gates'):
                profile['accepted_gates'] = list(DEFAULT_GATES)
            profile['notes'] = (profile.get('notes', '') + ' | #944 smoke override: any-slot assignment').strip(' |')
        elif identity in arena_by_identity:
            profile['accepted_slot_uids'] = [int(arena_by_identity[identity]['primary_uid'])]
            if not profile.get('accepted_gates'):
                profile['accepted_gates'] = list(DEFAULT_GATES)
            profile['notes'] = (profile.get('notes', '') + ' | #944 smoke override: arena pin').strip(' |')
        else:
            profile['accepted_slot_uids'] = []
    missing = (set(uids_by_identity) | set(arena_by_identity)) - seen
    if missing:
        raise SmokeSeedError(f'placement document has no profile for {sorted(missing)}')
    out['notes'] = f"#944 smoke override of the committed document: {len(assignments)} ordinary slot(s), {len(bosses)} boss arena(s). Not a placement approval."
    return out


def species_pool(assignments, bosses=None):
    return sorted(set(assignments.values()) | set(bosses or {}))


def check_layout(manifest, assignments, bosses, document):
    """Every requested (uid -> species) pair must appear in p2_layout exactly."""
    layout = manifest.get('p2_layout') or {}
    bound = {int(b['target']): int(b['source_id']) for b in layout.get('bindings', [])}
    problems = []
    for uid, sid in sorted(assignments.items()):
        if bound.get(uid) != sid:
            problems.append(f'slot {uid}: wanted {sid}, seed bound {bound.get(uid)}')
    arenas = {a['id']: a for a in document.get('arenas', [])}
    for sid, arena in (bosses or {}).items():
        uid = int(arenas[arena]['primary_uid'])
        if bound.get(uid) != sid:
            problems.append(f'arena {arena} ({uid}): wanted boss {sid}, seed bound {bound.get(uid)}')
    extra = sorted(set(bound) - set(assignments) - {int(arenas[a]['primary_uid']) for a in (bosses or {}).values()})
    if extra:
        problems.append(f'seed bound unrequested targets {extra}')
    if problems:
        raise SmokeSeedError('override placement did not resolve as requested:\n  ' + '\n  '.join(problems))
    return bound


# --- content cache ---------------------------------------------------------

def enum_for(source_id):
    from scripts import p2_prepare_content as prepare
    try:
        return prepare.ENUM_FOR_SOURCE[source_id]
    except KeyError:
        raise SmokeSeedError(f'no content extractor enum for source id {source_id}') from None


def stage_content(manifest, content_dir, cache_dir, iso, prepare_fn=None, copy=shutil.copytree):
    """Populate ``content_dir/<Enum>`` for every bound species: from
    ``content_dir`` itself if present, else from ``cache_dir``, else by
    extracting the missing ids from the ISO (``prepare_fn(iso, out, wanted)``)
    and copying the fresh dirs back into the cache. Returns a summary dict."""
    content_dir = Path(content_dir)
    cache_dir = Path(cache_dir) if cache_dir else None
    content_dir.mkdir(parents=True, exist_ok=True)
    bindings = (manifest.get('p2_layout') or {}).get('bindings', [])
    needed = {}
    for b in bindings:
        needed.setdefault(int(b['source_id']), b['enum_name'])
    reused, cached, missing = [], [], []
    for sid, enum in sorted(needed.items()):
        target = content_dir / enum
        if target.is_dir() and any(target.iterdir()):
            reused.append(enum)
            continue
        source = cache_dir / enum if cache_dir else None
        if source is not None and source.is_dir() and any(source.iterdir()):
            copy(source, target)
            cached.append(enum)
            continue
        missing.append(sid)
    extracted = []
    if missing:
        if iso is None:
            raise SmokeSeedError(
                f'content cache lacks {[needed[s] for s in missing]} and no --iso was given to extract them')
        if prepare_fn is None:
            from scripts import p2_prepare_content as prepare
            def prepare_fn(iso_path, out, wanted):
                return prepare.prepare_content_root(iso_path, out, wanted=wanted)
        summary = prepare_fn(iso, content_dir, missing)
        extracted = list(summary.get('extracted_enums', [])) if isinstance(summary, dict) else []
        for sid in missing:
            enum = needed[sid]
            fresh = content_dir / enum
            if not fresh.is_dir():
                raise SmokeSeedError(f'extraction did not produce {fresh} for source id {sid}')
            if cache_dir is not None:
                cache_dir.mkdir(parents=True, exist_ok=True)
                if not (cache_dir / enum).exists():
                    copy(fresh, cache_dir / enum)
    return {'reused': reused, 'from_cache': cached, 'extracted': extracted,
            'missing_ids': missing, 'needed': {str(k): v for k, v in sorted(needed.items())}}


# --- launcher --------------------------------------------------------------

def parse_env(items):
    """['NAME=VALUE', ...] -> {NAME: VALUE}; names are identifiers, values single-line."""
    env = {}
    for item in items or ():
        if '=' not in item:
            raise SmokeSeedError(f'--env entries are NAME=VALUE, got {item!r}')
        name, value = item.split('=', 1)
        if not name or not (name[0].isalpha() or name[0] == '_') or not all(c.isalnum() or c == '_' for c in name):
            raise SmokeSeedError(f'--env name must be an identifier, got {name!r}')
        if name == SMOKE_ENV:
            raise SmokeSeedError(f'{SMOKE_ENV} is always set by the launcher')
        if '\n' in value or '\r' in value:
            raise SmokeSeedError(f'--env {name} value must be a single line')
        env[name] = value
    return env


def launcher_text(seed_path, content_dir, actors_path, session_root, exe, assets, root=ROOT, extra_env=None):
    def ps(value):
        return "'" + str(value).replace("'", "''") + "'"
    extra_env = dict(extra_env or {})
    set_extra = ''.join(f"$env:{name} = {ps(value)}\n" for name, value in sorted(extra_env.items()))
    clear_extra = ''.join(f" Remove-Item Env:{name} -ErrorAction SilentlyContinue;" for name in sorted(extra_env))
    return f"""# #944/#948 smoke seed launcher: any playable P2 species on any ordinary slot.
# The placement override document is the whole mechanism (#948: native has no
# compiled slot lists). {SMOKE_ENV}=1 is set as the documented smoke marker.
# Dev only; never use for a normal seed.
param([string]$Exe = {ps(exe or '')}, [string]$Assets = {ps(assets)})
if (-not $Exe) {{ throw 'pass -Exe <path to nectar.exe built from claude/p2-placement-constraints or later>' }}
$session = Join-Path {ps(session_root)} ('session-' + (Get-Date -Format 'MMdd-HHmm'))
New-Item -ItemType Directory -Force $session | Out-Null
$env:PYTHONUTF8 = '1'
$env:{SMOKE_ENV} = '1'
{set_extra}Push-Location {ps(root)}
try {{
    py -3.12 -m randomizer run {ps(seed_path)} `
        --p2-content {ps(content_dir)} `
        --p2-actors {ps(actors_path)} `
        --session-dir $session `
        --exe $Exe `
        --assets $Assets
}} finally {{ Pop-Location; Remove-Item Env:{SMOKE_ENV} -ErrorAction SilentlyContinue;{clear_extra} }}
"""


# --- driver ----------------------------------------------------------------

def build(args):
    from randomizer.seed import generate, validate
    from experimental.pikmin2_enemy_roster import load_and_validate
    from scripts import p2_prepare_content as prepare

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    document = json.loads(Path(args.placement).read_text(encoding='utf-8')) if args.placement else load_default_document()
    roster = load_and_validate()
    species = parse_species(args.species)
    bosses = parse_bosses(args.bosses)
    probe_text = Path(args.probe_log).read_text(encoding='utf-8', errors='replace') if args.probe_log else None
    positions = slot_positions(probe_text)
    landing = parse_landing(args.landing) if args.landing else LANDING.get(args.area, LANDING_XZ)
    max_day = None if args.max_first_day < 0 else args.max_first_day
    slots = pick_slots(ordinary_slots(document, args.area, max_day), args.slots, args.near_start, positions,
                       origin=landing)
    assignments = assign_round_robin(species, slots)
    override = build_override(document, roster, assignments, bosses)
    override_path = out / 'placement-override.json'
    override_path.write_text(json.dumps(override, indent=1) + '\n', encoding='utf-8')

    starting_area = AREAS[args.area][0]
    manifest = generate(args.seed, 'solo', 'Player1', starting_area=starting_area,
                        collection_checks=True, starting_flarlic=1, bomb_rock_weight=1,
                        goal_mode='emperor_bulblax', combined_captain=True,
                        p2_enemies=True, p2_placement=override,
                        p2_species=species_pool(assignments, bosses),
                        progressive_maturity=True)
    validate(manifest)
    bound = check_layout(manifest, assignments, bosses, document)
    seed_path = out / f'{args.seed}.json'
    seed_path.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')

    content_dir = out / 'content'
    content = stage_content(manifest, content_dir, args.content_cache, args.iso) if not args.no_content else None
    actors_path = out / 'actors.json'
    prepare.actors_for_manifest_file(seed_path, actors_path)

    exe = str(Path(args.exe).resolve()) if args.exe else ''
    play_path = out / 'play.ps1'
    extra_env = parse_env(args.env)
    play_path.write_text(launcher_text(seed_path.resolve(), content_dir.resolve(), actors_path.resolve(),
                                       out.resolve(), exe, args.assets, extra_env=extra_env), encoding='utf-8')

    slots_by_uid = {int(s['uid']): s for s in document['slots']}
    summary = {
        'issue': 944, 'seed': args.seed, 'area': args.area, 'starting_area': starting_area,
        'near_start': bool(args.near_start), 'landing': list(landing), 'max_first_day': max_day, 'env': {SMOKE_ENV: '1', **extra_env},
        'assignments': [
            {'uid': uid, 'label': slots_by_uid[uid]['label'], 'source_id': sid,
             'enum_name': next(b['enum_name'] for b in manifest['p2_layout']['bindings'] if int(b['target']) == uid),
             'position': positions.get(uid),
             'distance_from_landing': round(distance_xz(positions[uid], landing), 1) if uid in positions else None}
            for uid, sid in sorted(assignments.items(), key=lambda kv: (positions.get(kv[0]) is None,
                                                                         distance_xz(positions[kv[0]], landing) if kv[0] in positions else 0))],
        'bosses': [{'source_id': sid, 'arena': arena} for sid, arena in sorted(bosses.items())],
        'bindings': {str(k): v for k, v in sorted(bound.items())},
        'files': {'seed': str(seed_path), 'placement_override': str(override_path),
                  'actors': str(actors_path), 'content': str(content_dir), 'launcher': str(play_path)},
        'content': content,
    }
    (out / 'smoke.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
    return summary


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--area', required=True, choices=sorted(AREAS), help='start area whose ordinary slots get the species')
    parser.add_argument('--slots', default='all', help="how many ordinary slots to fill: N or 'all' (default all)")
    parser.add_argument('--species', required=True, help='comma-separated P2 source ids, assigned round-robin in this order')
    parser.add_argument('--near-start', action='store_true', help='fill the N slots nearest the landing site (x/z distance from navi_start 0,0)')
    parser.add_argument('--bosses', default='', help="boss pins SOURCE_ID:ARENA_ID[,...] e.g. 94:hope_snagret_pit")
    parser.add_argument('--seed', required=True, help='seed name (also the manifest file name)')
    parser.add_argument('--out', required=True, type=Path, help='output directory (seed, override, content, actors.json, play.ps1, smoke.json)')
    parser.add_argument('--iso', type=Path, default=None, help='P2 retail ISO; only read when the content cache lacks a species')
    parser.add_argument('--content-cache', type=Path, default=ROOT / 'output' / 'p2-content-cache',
                        help='reusable per-enum content cache (default output/p2-content-cache); missing species are extracted and added')
    parser.add_argument('--exe', type=Path, default=None, help='nectar.exe built from claude/p2-smoke-any-slot (baked into play.ps1; overridable with -Exe)')
    parser.add_argument('--assets', default=DEFAULT_ASSETS, help='retail asset root for randomizer run --assets')
    parser.add_argument('--placement', type=Path, default=None, help='base placement document (default docs/PIKMIN2_ADMITTED_PLACEMENT.json)')
    parser.add_argument('--probe-log', type=Path, default=None, help='native log whose P2_PLACEMENT_SLOT lines supply extra slot coordinates')
    parser.add_argument('--no-content', action='store_true', help='skip content staging (seed + override + launcher only)')
    parser.add_argument('--landing', default=None, metavar='X,Z',
                        help='captain start used by --near-start (default: the measured start of the area, else 0,0)')
    parser.add_argument('--max-first-day', type=int, default=START_DAY,
                        help='skip slots whose first_day is later than this (default 2, the start day; -1 keeps every slot)')
    parser.add_argument('--env', action='append', default=[], metavar='NAME=VALUE',
                        help='extra environment variable set by play.ps1 (repeatable), e.g. a species dev override')
    args = parser.parse_args(argv)
    if args.slots != 'all':
        try:
            args.slots = int(args.slots)
        except ValueError:
            parser.error("--slots must be an int or 'all'")
    if args.iso is not None and not args.iso.is_file():
        parser.error(f'ISO not found: {args.iso}')
    try:
        summary = build(args)
    except SmokeSeedError as exc:
        print(f'Error: {exc}', file=sys.stderr)
        return 2
    print(json.dumps(summary, indent=2))
    print(f"\nLaunch: & {summary['files']['launcher']}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
