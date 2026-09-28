"""Lane 05 orchestration for existing family installers (generated-session path).

Family installers stay family-owned and keep their own source/bank formats. This
module is the lane 05 consumer: it resolves a named installer, guarantees the
run's private model destination exists, calls the installer, and returns its
receipt. It never converts or extracts assets and never commits retail data.

Only installers with the shared ``install(source, run, actors) -> receipt`` shape
are registered; families with bespoke signatures (bulblax, breadbug, tank,
qurione, bigtreasure, fuefuki, dwarf, kogane, uji) need an explicit adapter
before they can be consumed here.

The binding layer (:func:`resolve_family`, :func:`install_layout`) maps a seed's
``p2_layout`` bindings (source id / enum name) to a family installer and stages
each identity's content into the run tree. The first real adapters complete the
KochappyBase dwarf family: Kochappy (Dwarf Red Bulborb, source id 1), Dwarf Orange
Bulborb (``BlueKochappy``, source id 44) and Snow Bulborb (``YellowKochappy``,
source id 45); content roots are identity-keyed so the launcher can install a
generated session without per-family manual copying.
"""
import argparse
import hashlib
import itertools
import json
import os
import shutil
import sys
from importlib import import_module
from pathlib import Path

from experimental.pikmin2_staging import StagingError, sha256_file

ROOM = 'dataDir/courses/pikmin2room'
PLACEHOLDER = '.p2-family-install-placeholder'
BINDING_RECEIPT = 'p2-binding-receipt.json'
CACHE_RECEIPT = 'cache-receipt.json'
CACHE_KEY_PREFIX = 'p2bind-'
TEMP_SUFFIX = '.staging'
# Native session files that a fresh NativeRun lays down in the run root; a
# cache snapshot must never treat them as family-installed content.
SESSION_FILES = frozenset({
    'bootstrap.txt', 'state.txt', 'hello.txt', 'checks.txt', 'deaths.txt',
    'emperor.txt', 'overlay-manifest.json', 'native.log',
})
_TEMP = itertools.count()

# Family name -> module exposing ``install(source, run, actors)``.
FAMILY_MODULES = {
    'aquatic': 'experimental.pikmin2_aquatic_install',
    'bombsarai': 'experimental.pikmin2_bombsarai_install',
    'cannon_projectile': 'experimental.pikmin2_cannon_projectile_install',
    'dweevil': 'experimental.pikmin2_dweevil_install',
    'flora': 'experimental.pikmin2_flora_install',
    'flying': 'experimental.pikmin2_flying_install',
    'frog': 'experimental.pikmin2_frog_install',
    'ground_inverts': 'experimental.pikmin2_ground_inverts_install',
    'long_legs': 'experimental.pikmin2_long_legs_install',
    'mamuta': 'experimental.pikmin2_mamuta_install',
    'sheargrub': 'experimental.pikmin2_sheargrub_install',
    'snagret': 'experimental.pikmin2_snagret_install',
    'waterwraith': 'experimental.pikmin2_waterwraith_install',
}
_OVERRIDES = {}

# Identity-to-family mapping for the binding layer. Only identities whose family
# already has a lane 05 installer/adapter are registered; anything else resolves
# to a clear failure instead of silently binding to a P1 analogue.
#
# Muse packaging lane (#493): source 58 (BombSarai) reuses the existing shared-
# contract ``experimental.pikmin2_bombsarai_install`` module as-is through this
# mapping. Source 41 (Fuefuki) has no shared-signature family installer
# (bespoke ``install(run_dir)``-only) and stays candidate-only; Kurage (57)
# and MiniHoudai (78) now also bind here through the #442 adapters below while
# keeping their candidate-only muse_packaging path. See MUSE_CANDIDATE_IDS.
MUSE_CANDIDATE_IDS = frozenset({41, 57, 58, 78})
IDENTITY_FAMILY = {
    44: 'dwarf_orange', 'bluekochappy': 'dwarf_orange',
    45: 'snow', 'yellowkochappy': 'snow',
    1: 'kochappy', 'kochappy': 'kochappy',
    # lane-03 seed/native bridge cohort (directive 012): Sarai (23) and the
    # Otakara species (59-62). The Otakara rows reuse the existing dweevil
    # installer (p2-dweevil-actors.txt) rather than forking it; Sarai gets the
    # new actor-sidecar installer below. Anything else still fails closed.
    23: 'sarai', 'sarai': 'sarai',
    59: 'dweevil', 'fireotakara': 'dweevil',
    60: 'dweevil', 'waterotakara': 'dweevil',
    61: 'dweevil', 'gasotakara': 'dweevil',
    62: 'dweevil', 'elecotakara': 'dweevil',
    # Muse packaging lane (#493): BombSarai (Careening Dirigibug, source 58)
    # reuses the existing shared-contract bombsarai installer as-is.
    58: 'bombsarai', 'bombsarai': 'bombsarai',
    # Admission 2026-09-16 (#530 defect D1): Miulin (Mamuta, source 54) reuses
    # the existing shared-contract mamuta installer.
    54: 'mamuta', 'miulin': 'mamuta',
    # rd-p2ap-installers (#442): Kogane (9), Sokkuri (79), Kurage (57) and
    # MiniHoudai (78) now bind through the adapters below so a layout covering
    # all 11 admitted ids stages without raising. Kurage/MiniHoudai keep their
    # candidate-only muse_packaging path as well; the family path emits the
    # same native teki sidecars the bridge-mode setups read.
    9: 'kogane', 'kogane': 'kogane',
    79: 'sokkuri', 'sokkuri': 'sokkuri',
    57: 'kurage', 'kurage': 'kurage',
    # #888 WP5: 78 stages the native Groink source-FSM inputs (retail parms,
    # clip/key-event/pose/muzzle bank, poses) plus the carcass sidecar; the
    # campaign actor is driven by pc_p2_groink_fsm and delivers onion:p2:78.
    # Still a candidate until the owner's Windows OWN run lands.
    78: 'minihoudai', 'minihoudai': 'minihoudai',
    # #246 OWN: BigTreasure (Titan Dweevil, 73) stages the native source-order
    # core inputs (retail parms, key-event table, pose/joint bank, poses and
    # weapon pellets) through experimental.pikmin2_bigtreasure_campaign. The
    # campaign actor is pc_p2_bigtreasure_teki (hostType 73 -> TEKI_Swallow).
    # Candidate until the owner-reviewed OWN run lands; the proxy row is gone.
    73: 'bigtreasure', 'bigtreasure': 'bigtreasure',
    # inst-misc lane (#871): Catfish (26, Water Dumple) reuses the existing
    # shared-contract aquatic installer (p2-aquatic-actors.txt/bank) rather
    # than forking it; the source dir holds the full aquatic import.
    26: 'aquatic', 'catfish': 'aquatic',
    # Tadpole (27, Wogpole) shares the aquatic installer with Catfish.
    27: 'aquatic', 'tadpole': 'aquatic',
    # Hana (84, Creeping Chrysanthemum) reuses the shared ground installer.
    84: 'ground_inverts', 'hana': 'ground_inverts',
    # BombOtakara (93, Volatile Dweevil) reuses the shared dweevil installer.
    93: 'dweevil', 'bombotakara': 'dweevil',
    # Houdai (66, Man-at-Legs) reuses the shared long-legs installer.
    66: 'long_legs', 'houdai': 'long_legs',
    # FminiHoudai (97, Gatling Groink pedestal) reuses the cannon installer;
    # the cannon adapter also stages the shared Groink source-FSM inputs
    # (FixMiniHoudai: same FSM, no locomotion; delivers onion:p2:97).
    97: 'cannon_projectile', 'fminihoudai': 'cannon_projectile',
    # inst-chappy lane (#871): finished Chappy-family species bind through
    # the own-identity chappy adapter below, one finished species at a time
    # (2 Chappy, then 33 FireChappy, ...); a proxy row and an identity row
    # must never coexist.
    2: 'chappy', 'chappy': 'chappy',
    33: 'chappy', 'firechappy': 'chappy',
    35: 'chappy', 'kumachappy': 'chappy',
    43: 'chappy', 'yellowchappy': 'chappy',
    53: 'chappy', 'kingchappy': 'chappy',
    67: 'chappy', 'leafchappy': 'chappy',
    76: 'chappy', 'kumakochappy': 'chappy',
    # Campaign-identity Uji family (#871): UjiA (Female Sheargrub, 12), UjiB
    # (Male Sheargrub, 13) and Tobi (Shearwig, 14) stage the p2-uji-actors/bank
    # sidecars through experimental.pikmin2_uji_content.
    12: 'uji', 'ujia': 'uji',
    13: 'uji', 'ujib': 'uji',
    14: 'uji', 'tobi': 'uji',
    # Campaign-identity ground invertebrates (#871): ElecBug (Anode Beetle,
    # source 28) and TamagoMushi (Mitite, source 68) stage their rows of the
    # shared p2-ground-actors/bank sidecars through
    # experimental.pikmin2_elecbug_content /
    # experimental.pikmin2_tamago_content, merging with other
    # ground-identity species.
    28: 'elecbug', 'elecbug': 'elecbug',
    68: 'tamago', 'tamagomushi': 'tamago',
    # Campaign-identity snagret family (#871): DangoMushi (Segmented
    # Crawbster, source 94) stages its rows of the p2-snagret-actors/bank
    # sidecars through experimental.pikmin2_dangomushi_content.
    94: 'dangomushi', 'dangomushi': 'dangomushi',
    # Frog lane (inst-frogs #871): Yellow Wollywog (Frog, source 17) and
    # Wollywog (MaroFrog, source 18) stage through the dedicated frog
    # installer (p2-frog.txt + frog_* poses).
    17: 'frog', 'frog': 'frog',
    18: 'frog', 'marofrog': 'frog',
    # Frogs round 2 (inst2-frogs #871): Fiery Blowhog (Tank 24) + Watery
    # Blowhog (Wtank 25) share the tank bank (p2-tank.txt); Cloaking
    # Burrow-nit (Armor 15) stages via the ground family; Armored Cannon
    # Beetle Larva (Kabuto 75) stages via its own bank (p2-kabuto.txt).
    24: 'tank', 'tank': 'tank',
    25: 'tank', 'wtank': 'tank',
    15: 'armor', 'armor': 'armor',
    75: 'kabuto', 'kabuto': 'kabuto',
    # inst-legs lane (#871): Damagumo (56, Beady Long Legs) and BigFoot (69,
    # Raging Long Legs) share the long_legs adapter below (shared installer +
    # bind-mod visual staging); Jigumo (63, Hermit Crawmad) reuses the shared
    # aquatic installer directly (full-family source per species dir, like the
    # dweevil 59-62 precedent). Proxy rows for 56/63/69 are removed; a proxy
    # row coexisting with these rows fails closed via _proxy_family_entries.
    56: 'long_legs', 'damagumo': 'long_legs',
    69: 'long_legs', 'bigfoot': 'long_legs',
    63: 'aquatic', 'jigumo': 'aquatic',
    # inst-worms lane (#871): SnakeCrow (34) + SnakeWhole (70) share the
    # existing shared-contract snagret installer; Imomushi (65) reuses the
    # shared-contract ground_inverts installer; UmiMushi (71) + UmiMushiBlind
    # (101, Blind variant sharing the UmiMushi bank, see aquatic_install)
    # reuse the shared-contract aquatic installer. Anything else still fails
    # closed.
    34: 'snagret', 'snakecrow': 'snagret',
    70: 'snagret', 'snakewhole': 'snagret',
    65: 'ground_inverts', 'imomushi': 'ground_inverts',
    71: 'aquatic', 'umimushi': 'aquatic',
    101: 'aquatic', 'umimushiblind': 'aquatic',
}


def _proxy_family_entries():
    """Proxy ``IDENTITY_FAMILY`` rows derived from ``randomizer/p2_proxy``.

    Each declared species contributes ``<source_id>: 'proxy'`` and
    ``<enum_name.lower()>: 'proxy'``. A derived key that collides with an
    existing non-proxy row fails closed at import.
    """
    from randomizer.p2_proxy import load_rows

    entries = {}
    for row in load_rows():
        keys = (row["source_id"], row["enum_name"].lower())
        for key in keys:
            if key in IDENTITY_FAMILY:
                raise ValueError(
                    f"proxy declaration collides with a non-proxy family path: {key!r}")
            if key in entries:
                raise ValueError(
                    f"proxy declaration duplicate family key: {key!r}")
            entries[key] = "proxy"
    return entries


IDENTITY_FAMILY.update(_proxy_family_entries())


def _validate_dwarf_orange(source):
    """Pre-flight check for the Dwarf Orange identity content (source only).

    Mirrors the source-side requirements of ``pikmin2_dwarf_orange_install.plan``
    (identity + reference binding) so a wrong/missing source is rejected before
    any ``<run>/assets`` destination is prepared; ``install`` re-checks the full
    contract and remains authoritative.
    """
    from experimental import pikmin2_dwarf_orange_install as dwarf
    source = Path(source)
    bank_json = source / 'bank' / 'dwarf-orange-bank.json'
    profile_json = source / 'profile' / 'dwarf-orange-profile.json'
    if not bank_json.is_file():
        raise StagingError(f'Dwarf Orange bank missing for identity content: {bank_json}')
    if not profile_json.is_file():
        raise StagingError(f'Dwarf Orange profile missing for identity content: {profile_json}')
    try:
        metadata = json.loads(bank_json.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError, ValueError) as error:
        raise StagingError(f'Dwarf Orange bank unreadable for identity content: {bank_json}') from error
    if (metadata.get('schema'), metadata.get('species'), metadata.get('source_id'),
            metadata.get('health')) != (1, 'BlueKochappy', 44, 250):
        raise StagingError(f'Dwarf Orange bank identity mismatch for identity content: {bank_json}')
    reference = metadata.get('reference_sha256')
    if not reference or reference != dwarf.sha(profile_json.read_bytes()):
        raise StagingError(f'Dwarf Orange bank bound to a different source import: {bank_json}')


def _adapt_dwarf_orange(source, run, actors):
    """Adapter for the bespoke Dwarf Orange (BlueKochappy) installer.

    ``source`` is the identity content dir laid out as ``<source>/bank`` and
    ``<source>/profile``, matching the family bank builder's two outputs.
    """
    from experimental import pikmin2_dwarf_orange_install as dwarf
    return dwarf.install(Path(source) / 'bank', Path(source) / 'profile', Path(run),
                         [generator for generator, _species in actors])


def _validate_snow(source):
    """Pre-flight check for the Snow (YellowKochappy) identity content.

    Snow uses ``pikmin2_enemy``'s flat bank layout (``snow.json`` + ``p2-snow.txt``
    + ``snow_*.mod``); the identity and bank files must exist and declare Snow.
    """
    source = Path(source)
    snow_json = source / 'snow.json'
    if not snow_json.is_file():
        raise StagingError(f'Snow import missing for identity content: {snow_json}')
    if not (source / 'p2-snow.txt').is_file():
        raise StagingError(f'Snow bank config missing for identity content: {source / "p2-snow.txt"}')
    try:
        metadata = json.loads(snow_json.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError, ValueError) as error:
        raise StagingError(f'Snow import unreadable for identity content: {snow_json}') from error
    if metadata.get('schema') != 1 or metadata.get('species') != 'YellowKochappy':
        raise StagingError(f'Snow import identity mismatch for identity content: {snow_json}')


def _adapt_snow(source, run, actors):
    """Adapter for the Snow (YellowKochappy) installer (flat ``pikmin2_enemy`` bank)."""
    from experimental import pikmin2_enemy as snow
    generators = [generator for generator, _species in actors]
    snow.install(Path(source), Path(run), generators)
    return dict(species='YellowKochappy', source_id=45, generators=generators)


def _validate_kochappy(source):
    """Pre-flight check for the Kochappy (Dwarf Red) identity content.

    Kochappy uses the family bank's flat layout (``kochappy-bank.json`` +
    ``p2-kochappy-profile.txt`` + ``p2-kochappy-bank.txt`` + ``kochappy_*.mod``);
    the import must exist and declare the Kochappy Red identity.
    """
    source = Path(source)
    bank_json = source / 'kochappy-bank.json'
    if not bank_json.is_file():
        raise StagingError(f'Kochappy bank missing for identity content: {bank_json}')
    if not (source / 'p2-kochappy-profile.txt').is_file():
        raise StagingError(f'Kochappy profile missing for identity content: {source / "p2-kochappy-profile.txt"}')
    try:
        metadata = json.loads(bank_json.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError, ValueError) as error:
        raise StagingError(f'Kochappy bank unreadable for identity content: {bank_json}') from error
    if (metadata.get('schema'), metadata.get('species'), metadata.get('source_id'),
            metadata.get('health')) != (1, 'Kochappy', 1, 200):
        raise StagingError(f'Kochappy bank identity mismatch for identity content: {bank_json}')


def _adapt_kochappy(source, run, actors):
    """Adapter for the Kochappy (Dwarf Red) installer (flat ``pikmin2_kochappy_bank``)."""
    from experimental import pikmin2_kochappy_bank as kochappy
    generators = [generator for generator, _species in actors]
    kochappy.install(Path(source), Path(run), generators)
    return dict(species='Kochappy', source_id=1, generators=generators)


SARAI_ACTORS_TXT = 'p2-sarai-actors.txt'
SARAI_ACTORS_HEADER = 'P2_SARAI_ACTORS_1'


def _validate_sarai(source):
    """Pre-flight check for the Sarai (Swooping Snitchbug, source 23) content.

    Sarai is a private visual host (lane 30) staged from the ``sarai-*`` files;
    the identity content must carry the mouth bank the host reads. The native
    selector binds by the seed source, so no sidecar is consumed there; this only
    proves the identity content is present before the run tree is written.
    """
    source = Path(source)
    if not (source / 'sarai-attack-mouths.txt').is_file():
        raise StagingError(f'Sarai mouth bank missing for identity content: {source / "sarai-attack-mouths.txt"}')


def _adapt_sarai(source, run, actors):
    """Adapter for the Sarai (source 23) actor-sidecar install (lane-03 bridge).

    Writes ``p2-sarai-actors.txt`` from the seed's assigned generator ids in the
    batch-2 ``<header> <count>`` + one generator per line shape, so the
    seed-derived binding is recorded for audit; the native Sarai module selects
    by the seed source directly. ``install_layout`` calls this once per binding
    with a SINGLE generator, so the sidecar is accumulated (order-preserving
    union) rather than overwritten when a seed binds Sarai to several generators.
    """
    run = Path(run)
    generators = [int(generator) for generator, _species in actors]
    if not generators:
        raise StagingError('Sarai install requires at least one generator')
    from experimental.pikmin2_sarai_install import stage_sarai_host
    stage_sarai_host(source, run)
    path = run / SARAI_ACTORS_TXT
    existing = []
    if path.is_file():
        tokens = path.read_text(encoding='ascii').split()
        # Format is ``<header> <count>`` then one generator per line.
        if len(tokens) < 2 or tokens[0] != SARAI_ACTORS_HEADER or int(tokens[1]) != len(tokens) - 2:
            raise StagingError(f'existing {SARAI_ACTORS_TXT} is malformed')
        existing = [int(token) for token in tokens[2:]]
    merged = list(dict.fromkeys(existing + generators))  # order-preserving union
    text = f'{SARAI_ACTORS_HEADER} {len(merged)}\n' + '\n'.join(str(g) for g in merged) + '\n'
    path.write_text(text, encoding='ascii')
    return dict(species='Sarai', source_id=23, generators=merged,
                actors_config_sha256=hashlib.sha256(text.encode('ascii')).hexdigest())


KOGANE_NATIVE_TXT = 'p2-kogane-native.txt'
KOGANE_NATIVE_HEADER = 'P2_KOGANE_NATIVE_1'
KURAGE_TEKI_TXT = 'p2-kurage-teki.txt'
KURAGE_TEKI_HEADER = 'P2_KURAGE_TEKI_1'
GROINK_TEKI_TXT = 'p2-groink-teki.txt'
GROINK_TEKI_HEADER = 'P2_GROINK_TEKI_1'


def _validate_kogane(source):
    """Pre-flight check for the Kogane (Iridescent Flint Beetle, source 9) content.

    The source is the kogane bank dir (``beetles.json`` + ``shared/*.mod``)
    consumed as-is by ``experimental.pikmin2_kogane_install``; the full hash
    contract stays authoritative inside that installer.
    """
    source = Path(source)
    bank_json = source / 'beetles.json'
    if not bank_json.is_file():
        raise StagingError(f'Kogane bank missing for identity content: {bank_json}')
    try:
        metadata = json.loads(bank_json.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError, ValueError) as error:
        raise StagingError(f'Kogane bank unreadable for identity content: {bank_json}') from error
    if metadata.get('schema') != 1 or metadata.get('family') != 'Kogane':
        raise StagingError(f'Kogane bank identity mismatch for identity content: {bank_json}')


def _kogane_native_text(generators):
    """Minimal valid ``p2-kogane-native.txt`` for the native policy parser.

    Emits ``karada 0`` with one actor row per generator (species 9) and the
    three required clips (move/wait/damage) in the exact
    ``pc_p2_kogane_policy.h::read`` shape. In bridge mode the native setup
    replaces these ids from the seed (``pc_p2_campaign_ids(9)``), so the filed
    generators are placeholders there; outside bridge mode they bind directly.
    """
    gens = sorted(int(g) for g in generators)
    if not gens or len(set(gens)) != len(gens) or any(not 0 < g <= 0xFFFFFFFF for g in gens):
        raise StagingError('Kogane install requires unique non-zero generators')
    parts = [KOGANE_NATIVE_HEADER, 'karada 0', f'actors {len(gens)}']
    parts += [f'{g} 9' for g in gens]
    parts += ['move 2 12 0 11', 'wait 2 15 0 14', 'damage 2 30 0 29']
    return (' '.join(parts) + '\n').encode('ascii')


def _adapt_kogane(source, run, actors):
    """Adapter for Kogane (source 9): bank install + native sidecar.

    Reuses ``experimental.pikmin2_kogane_install.install`` for the
    ``p2-kogane-*.txt`` configs and ``kogane_*.mod`` visuals, then emits the
    ``p2-kogane-native.txt`` sidecar the native ``pc_p2_kogane_setup`` parses.
    ``install_layout`` groups by family, so this runs once per layout with all
    Kogane generators; direct per-binding repeat calls refuse (like the shared
    batch-2 installers) instead of silently overwriting.
    """
    from experimental import pikmin2_kogane_install as kogane
    run = Path(run)
    generators = [int(generator) for generator, _species in actors]
    for _, species in actors:
        if species != 'Kogane':
            raise StagingError(f'Kogane adapter got non-Kogane species: {species!r}')
    if not generators:
        raise StagingError('Kogane install requires at least one generator')
    try:
        kogane_receipt = kogane.install(Path(source), run, generators)
    except ValueError as error:
        raise StagingError(str(error)) from error
    payload = _kogane_native_text(generators)
    path = run / KOGANE_NATIVE_TXT
    if path.exists():
        raise StagingError(f'Refusing existing/conflicting Kogane native sidecar: {path}')
    path.write_bytes(payload)
    # The sidecar selects the clips, so the host meshes stage after it is written.
    # Without this the run holds p2-kogane-native.txt naming move/wait/damage and no
    # kogane_*.mod at all, and setup logs `P2_SETUP_SKIP Kogane clip_file_missing`
    # while every Kogane slot silently stays its P1 host (measured, probe 2026-09-20).
    from experimental.pikmin2_kogane_content import stage_kogane_host
    staged = stage_kogane_host(source, run)
    return dict(species='Kogane', source_id=9, generators=sorted(generators),
                native_config_sha256=hashlib.sha256(payload).hexdigest(),
                kogane_receipt=kogane_receipt, host_staging=staged)


def _validate_sokkuri(source):
    """Pre-flight check for the Sokkuri (Skitter Leaf, source 79) content.

    Accepts the Sokkuri extraction tree (``sokkuri.json``) staged through
    ``experimental.pikmin2_sokkuri_content``, as well as the legacy
    ground-invertebrate import dir (``ground_inverts.json``) consumed as-is by
    ``experimental.pikmin2_ground_inverts_install``; the full schema/policy
    contract stays authoritative inside the respective installer.
    """
    from experimental import pikmin2_sokkuri_content as sokkuri_content
    source = Path(source)
    if (source / 'sokkuri.json').is_file():
        sokkuri_content.validate_source(source)
        return
    manifest = source / 'ground_inverts.json'
    if not manifest.is_file():
        raise StagingError(f'Sokkuri ground manifest missing for identity content: {manifest}')
    try:
        metadata = json.loads(manifest.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError, ValueError) as error:
        raise StagingError(f'Sokkuri ground manifest unreadable: {manifest}') from error
    species = metadata.get('species', {})
    if metadata.get('policy') != 'P2_GROUND_INVERTS_1' or species.get('Sokkuri') != 79:
        # Manifests key species by name to enemy id in batch-2 shape; also
        # accept the nested ``{'enemy_id': 79}`` shape.
        entry = species.get('Sokkuri')
        enemy_id = entry.get('enemy_id') if isinstance(entry, dict) else entry
        if metadata.get('policy') != 'P2_GROUND_INVERTS_1' or enemy_id != 79:
            raise StagingError(f'Sokkuri ground manifest identity mismatch: {manifest}')


def _adapt_sokkuri(source, run, actors):
    """Adapter for Sokkuri (source 79) via the Sokkuri content stager.

    Writes ``p2-ground-actors.txt`` + ``p2-ground-bank.txt`` (plus profile and
    visuals) in the exact batch-2 shape the native ``pc_p2_sokkuri_setup``
    parses (``P2_GROUND_ACTORS_1`` + ``P2_GROUND_BANK_1``). In bridge mode the
    native setup replaces the filed ids from the seed (``pc_p2_campaign_ids``),
    so filed generators are placeholders there; outside bridge mode they bind.

    A ``sokkuri.json`` tree (what ``extract_sokkuri`` produces) stages through
    ``experimental.pikmin2_sokkuri_content``; a legacy ``ground_inverts.json``
    import dir keeps the shared ground-installer path unchanged. The ground
    file shapes are identical either way.
    """
    from experimental import pikmin2_sokkuri_content as sokkuri_content
    pairs = [(int(generator), species) for generator, species in actors]
    for _, species in pairs:
        if species != 'Sokkuri':
            raise StagingError(f'Sokkuri adapter got non-Sokkuri species: {species!r}')
    if not pairs:
        raise StagingError('Sokkuri install requires at least one generator')
    if (Path(source) / 'sokkuri.json').is_file():
        return sokkuri_content.stage_sokkuri_ground(Path(source), run, pairs)
    from experimental import pikmin2_ground_inverts_install as ground
    try:
        receipt = ground.install(Path(source), run, pairs)
    except ValueError as error:
        raise StagingError(str(error)) from error
    return dict(species='Sokkuri', source_id=79,
                generators=[g for g, _ in pairs], ground_receipt=receipt)


def _uji_content_root(source, actors):
    """Resolve the identity-keyed content root for a Uji install.

    ``install_layout`` groups by family, so this adapter runs once per layout
    with every Uji actor while ``source`` is only the first binding's
    ``<content_root>/<enum>`` species dir. The content root is the directory
    whose per-species children hold every bound species' ``uji.json`` (same
    shape as the proxy adapter's content-root resolution).
    """
    species = {species for _, species in actors}
    candidates = [Path(source), Path(source).parent]
    for candidate in candidates:
        if all((candidate / name / 'uji.json').is_file() for name in species):
            return candidate
    raise StagingError(
        f'Uji content root missing uji.json for {sorted(species)} under {source}')


def _validate_uji(source):
    """Pre-flight check for one Uji species dir (full plan runs at install)."""
    from experimental import pikmin2_uji_content as uji_content
    uji_content.validate_source(source)


def _adapt_uji(source, run, actors):
    """Adapter for the campaign-identity Uji family (sources 12/13/14).

    Stages all Uji actors through ``experimental.pikmin2_uji_content`` in one
    grouped call: the ``p2-uji-actors.txt``/``p2-uji-bank.txt`` sidecars (the
    ``P2_UJI_ACTORS_1``/``P2_UJI_BANK_1`` shape the native ``pc_p2_uji_*``
    module parses) plus every bound species' pose meshes. ``install_layout``
    already groups bindings by family, so this runs once per layout with all
    Uji generators.
    """
    from experimental import pikmin2_uji_content as uji_content
    pairs = [(int(generator), species) for generator, species in actors]
    for _, species in pairs:
        if species not in uji_content.UJI_SPECIES:
            raise StagingError(f'Uji adapter got non-Uji species: {species!r}')
    if not pairs:
        raise StagingError('Uji install requires at least one generator')
    content_root = _uji_content_root(source, pairs)
    return uji_content.stage_uji(content_root, run, pairs)


def _validate_elecbug(source):
    """Pre-flight check for the ElecBug (Anode Beetle, source 28) content.

    Accepts the ElecBug extraction tree (``elecbug.json``) staged through
    ``experimental.pikmin2_elecbug_content``, as well as the legacy
    ground-invertebrate import dir (``ground_inverts.json``) consumed as-is by
    ``experimental.pikmin2_ground_inverts_install``; the full schema/policy
    contract stays authoritative inside the respective installer.
    """
    from experimental import pikmin2_elecbug_content as elecbug_content
    source = Path(source)
    if (source / 'elecbug.json').is_file():
        elecbug_content.validate_source(source)
        return
    manifest = source / 'ground_inverts.json'
    if not manifest.is_file():
        raise StagingError(f'ElecBug ground manifest missing for identity content: {manifest}')
    try:
        metadata = json.loads(manifest.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError, ValueError) as error:
        raise StagingError(f'ElecBug ground manifest unreadable: {manifest}') from error
    species = metadata.get('species', {})
    if metadata.get('policy') != 'P2_GROUND_INVERTS_1' or species.get('ElecBug') != 28:
        # Manifests key species by name to enemy id in batch-2 shape; also
        # accept the nested ``{'enemy_id': 28}`` shape.
        entry = species.get('ElecBug')
        enemy_id = entry.get('enemy_id') if isinstance(entry, dict) else entry
        if metadata.get('policy') != 'P2_GROUND_INVERTS_1' or enemy_id != 28:
            raise StagingError(f'ElecBug ground manifest identity mismatch: {manifest}')


def _adapt_elecbug(source, run, actors):
    """Adapter for ElecBug (source 28) via the ElecBug content stager.

    Writes the ElecBug rows of ``p2-ground-actors.txt`` + ``p2-ground-bank.txt``
    (plus visuals) in the exact batch-2 shape the native ``pc_p2_elecbug_setup``
    parses (``P2_GROUND_ACTORS_1`` + ``P2_GROUND_BANK_1``,
    ``engine/pc_port/pc_p2_elecbug.cpp:460-501``), merging with rows other
    ground-identity species already staged. In bridge mode the native setup
    replaces the filed ids from the seed (``pc_p2_campaign_ids``), so filed
    generators are placeholders there; outside bridge mode they bind.

    An ``elecbug.json`` tree (what ``extract_elecbug`` produces) stages through
    ``experimental.pikmin2_elecbug_content``; a legacy ``ground_inverts.json``
    import dir keeps the shared ground-installer path unchanged.
    """
    from experimental import pikmin2_elecbug_content as elecbug_content
    pairs = [(int(generator), species) for generator, species in actors]
    for _, species in pairs:
        if species != 'ElecBug':
            raise StagingError(f'ElecBug adapter got non-ElecBug species: {species!r}')
    if not pairs:
        raise StagingError('ElecBug install requires at least one generator')
    if (Path(source) / 'elecbug.json').is_file():
        return elecbug_content.stage_elecbug_ground(Path(source), run, pairs)
    from experimental import pikmin2_ground_inverts_install as ground
    try:
        receipt = ground.install(Path(source), run, pairs)
    except ValueError as error:
        raise StagingError(str(error)) from error
    return dict(species='ElecBug', source_id=28,
                generators=[g for g, _ in pairs], ground_receipt=receipt)


def _validate_dangomushi(source):
    """Pre-flight check for the DangoMushi (Segmented Crawbster, source 94) content.

    Accepts the DangoMushi extraction tree (``dangomushi.json``) staged through
    ``experimental.pikmin2_dangomushi_content``, as well as the legacy
    snagret import dir (``snagret.json``) consumed as-is by
    ``experimental.pikmin2_snagret_install``; the full schema/policy contract
    stays authoritative inside the respective installer.
    """
    from experimental import pikmin2_dangomushi_content as dangomushi_content
    source = Path(source)
    if (source / 'dangomushi.json').is_file():
        dangomushi_content.validate_source(source)
        return
    manifest = source / 'snagret.json'
    if not manifest.is_file():
        raise StagingError(f'DangoMushi snagret manifest missing for identity content: {manifest}')
    try:
        metadata = json.loads(manifest.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError, ValueError) as error:
        raise StagingError(f'DangoMushi snagret manifest unreadable: {manifest}') from error
    species = metadata.get('species', {})
    if metadata.get('policy') != 'P2_SNAGRET_1' or species.get('DangoMushi') != 94:
        # Manifests key species by name to enemy id in batch-1 shape; also
        # accept the nested ``{'enemy_id': 94}`` shape.
        entry = species.get('DangoMushi')
        enemy_id = entry.get('enemy_id') if isinstance(entry, dict) else entry
        if metadata.get('policy') != 'P2_SNAGRET_1' or enemy_id != 94:
            raise StagingError(f'DangoMushi snagret manifest identity mismatch: {manifest}')


def _adapt_dangomushi(source, run, actors):
    """Adapter for DangoMushi (source 94) via the DangoMushi content stager.

    Writes the DangoMushi rows of ``p2-snagret-actors.txt`` +
    ``p2-snagret-bank.txt`` (plus visuals) in the exact batch-3 shape the
    native ``pc_p2_dangomushi_setup`` parses
    (``P2_SNAGRET_ACTORS_1`` + ``P2_SNAGRET_BANK_1``,
    ``engine/pc_port/pc_p2_dangomushi.cpp:737-806``), merging with rows other
    snagret-family species already staged.

    A ``dangomushi.json`` tree (what ``extract_dangomushi`` produces) stages
    through ``experimental.pikmin2_dangomushi_content``; a legacy
    ``snagret.json`` import dir keeps the shared snagret-installer path
    unchanged.
    """
    from experimental import pikmin2_dangomushi_content as dangomushi_content
    pairs = [(int(generator), species) for generator, species in actors]
    for _, species in pairs:
        if species != 'DangoMushi':
            raise StagingError(f'DangoMushi adapter got non-DangoMushi species: {species!r}')
    if not pairs:
        raise StagingError('DangoMushi install requires at least one generator')
    if (Path(source) / 'dangomushi.json').is_file():
        return dangomushi_content.stage_dangomushi(Path(source), run, pairs)
    from experimental import pikmin2_snagret_install as snagret
    try:
        receipt = snagret.install(Path(source), run, pairs)
    except ValueError as error:
        raise StagingError(str(error)) from error
    return dict(species='DangoMushi', source_id=94,
                generators=[g for g, _ in pairs], snagret_receipt=receipt)


def _validate_tamago(source):
    """Pre-flight check for the TamagoMushi (Mitite, source 68) content.

    Accepts the TamagoMushi extraction tree (``tamagomushi.json``) staged
    through ``experimental.pikmin2_tamago_content``, as well as the legacy
    ground-invertebrate import dir (``ground_inverts.json``) consumed as-is by
    ``experimental.pikmin2_ground_inverts_install``; the full schema/policy
    contract stays authoritative inside the respective installer.
    """
    from experimental import pikmin2_tamago_content as tamago_content
    source = Path(source)
    if (source / 'tamagomushi.json').is_file():
        tamago_content.validate_source(source)
        return
    manifest = source / 'ground_inverts.json'
    if not manifest.is_file():
        raise StagingError(f'TamagoMushi ground manifest missing for identity content: {manifest}')
    try:
        metadata = json.loads(manifest.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError, ValueError) as error:
        raise StagingError(f'TamagoMushi ground manifest unreadable: {manifest}') from error
    species = metadata.get('species', {})
    if metadata.get('policy') != 'P2_GROUND_INVERTS_1' or species.get('TamagoMushi') != 68:
        # Manifests key species by name to enemy id in batch-2 shape; also
        # accept the nested ``{'enemy_id': 68}`` shape.
        entry = species.get('TamagoMushi')
        enemy_id = entry.get('enemy_id') if isinstance(entry, dict) else entry
        if metadata.get('policy') != 'P2_GROUND_INVERTS_1' or enemy_id != 68:
            raise StagingError(f'TamagoMushi ground manifest identity mismatch: {manifest}')


def _adapt_tamago(source, run, actors):
    """Adapter for TamagoMushi (source 68) via the TamagoMushi content stager.

    Writes the TamagoMushi rows of ``p2-ground-actors.txt`` +
    ``p2-ground-bank.txt`` (plus visuals) in the exact batch-2 shape the
    native ``pc_p2_tamago_setup`` parses (``P2_GROUND_ACTORS_1`` +
    ``P2_GROUND_BANK_1``, ``engine/pc_port/pc_p2_tamago.cpp:378-421``),
    merging with rows other ground-identity species already staged.

    A ``tamagomushi.json`` tree (what ``extract_tamago`` produces) stages
    through ``experimental.pikmin2_tamago_content``; a legacy
    ``ground_inverts.json`` import dir keeps the shared ground-installer path
    unchanged.
    """
    from experimental import pikmin2_tamago_content as tamago_content
    pairs = [(int(generator), species) for generator, species in actors]
    for _, species in pairs:
        if species != 'TamagoMushi':
            raise StagingError(f'TamagoMushi adapter got non-TamagoMushi species: {species!r}')
    if not pairs:
        raise StagingError('TamagoMushi install requires at least one generator')
    if (Path(source) / 'tamagomushi.json').is_file():
        return tamago_content.stage_tamago_ground(Path(source), run, pairs)
    from experimental import pikmin2_ground_inverts_install as ground
    try:
        receipt = ground.install(Path(source), run, pairs)
    except ValueError as error:
        raise StagingError(str(error)) from error
    return dict(species='TamagoMushi', source_id=68,
                generators=[g for g, _ in pairs], ground_receipt=receipt)


# Armor (15) / Imomushi (65) / Hana (84) share the ground_inverts family
# installer. Unlike the shared batch2_core install (which refuses when the run
# already carries ground sidecars from Sokkuri/ElecBug/TamagoMushi), this
# adapter merges its own species rows, so one seed can bind Armor together
# with Sokkuri, ElecBug, Imomushi (or any other ground writer) in either
# family order. Idempotent: a second call over the same run is a no-op
# success when every staged file is byte-identical; a conflicting staged file
# is refused with ``StagingError``.
# frogs4 (#871): Armor used to stage through the legacy all-or-nothing
# ``ground.install`` (``_adapt_armor``), which refused a seed that also bound
# any other ground species; it now rides this merge adapter like 65/84.
_GROUND_INVERTS_SOURCE_IDS = {'Armor': 15, 'Imomushi': 65, 'Hana': 84}


def _validate_ground_inverts(source):
    """Pre-flight check for the shared ground-inverts family content."""
    source = Path(source)
    manifest = source / 'ground_inverts.json'
    if not manifest.is_file():
        raise StagingError(f'Ground-inverts manifest missing for identity content: {manifest}')
    try:
        metadata = json.loads(manifest.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError, ValueError) as error:
        raise StagingError(f'Ground-inverts manifest unreadable: {manifest}') from error
    if metadata.get('policy') != 'P2_GROUND_INVERTS_1':
        raise StagingError(f'Ground-inverts manifest identity mismatch: {manifest}')
    species = metadata.get('species', {})
    if not any(name in species for name in _GROUND_INVERTS_SOURCE_IDS):
        raise StagingError(f'Ground-inverts manifest carries no staged species: {manifest}')


def _adapt_ground_inverts(source, run, actors):
    """Adapter for Armor (15) / Imomushi (65) / Hana (84) with merge semantics."""
    from experimental import pikmin2_ground_inverts_install as ground
    from experimental import pikmin2_ground_species_content as species_content
    pairs = [(int(generator), species) for generator, species in actors]
    for _, species in pairs:
        if species not in _GROUND_INVERTS_SOURCE_IDS:
            raise StagingError(f'Ground-inverts adapter got non-ground-inverts species: {species!r}')
    if not pairs:
        raise StagingError('Ground-inverts install requires at least one generator')
    source, run = Path(source), Path(run)
    if not run.is_dir():
        raise StagingError(f'Ground-inverts run directory missing: {run}')
    room = run / 'assets/dataDir/courses/pikmin2room'
    if not room.is_dir() or room.is_symlink():
        raise StagingError(f'Ground-inverts room directory missing for run staging: {room}')
    try:
        profile_payload, bank_payload, _actors_payload, files, _metadata = ground.plan(source, pairs)
    except ValueError as error:
        raise StagingError(str(error)) from error
    wanted = sorted({species for _, species in pairs})
    own_blocks = {}
    for block in species_content.parse_bank(bank_payload):
        if block[0] in wanted:
            if block[0] in own_blocks:
                raise StagingError(f'Ground-inverts plan carries duplicate bank block: {block[0]}')
            own_blocks[block[0]] = block
    if sorted(own_blocks) != wanted:
        raise StagingError(
            f'Ground-inverts plan carries no bank block for {sorted(set(wanted) - set(own_blocks))}')
    actors_path, bank_file, profile_path = run / ground.ACTORS_TXT, run / ground.BANK_TXT, run / ground.PROFILE_TXT
    wrote = False
    for species in wanted:
        generators = [int(generator) for generator, name in pairs if name == species]
        merged_actors = species_content.merge_actors(
            actors_path.read_bytes() if actors_path.is_file() else None,
            species, generators)
        _name, _enemy_id, own_clips = own_blocks[species]
        merged_bank = species_content.merge_bank(
            bank_file.read_bytes() if bank_file.is_file() else None,
            species, _GROUND_INVERTS_SOURCE_IDS[species], own_clips)
        if not actors_path.is_file() or actors_path.read_bytes() != merged_actors:
            actors_path.write_bytes(merged_actors)
            wrote = True
        if not bank_file.is_file() or bank_file.read_bytes() != merged_bank:
            bank_file.write_bytes(merged_bank)
            wrote = True
    if profile_path.is_file():
        if profile_path.read_bytes() != profile_payload:
            raise StagingError('Refusing conflicting ground-inverts profile staging')
    else:
        profile_path.write_bytes(profile_payload)
        wrote = True
    mesh_conflicts = sorted(
        name for name, payload in files.items()
        if (room / name).is_file()
        and (room / name).read_bytes() != payload)
    if mesh_conflicts:
        raise StagingError(
            'Refusing conflicting ground-inverts staging: ' + ', '.join(mesh_conflicts))
    for name, payload in files.items():
        if not (room / name).is_file():
            (room / name).write_bytes(payload)
            wrote = True
    staged = 'written' if wrote else 'existing_identical'
    return dict(family='ground_inverts', species=wanted, staged=staged,
                generators=[g for g, _ in pairs],
                files=sorted(files))


def _read_identity_source(source, source_id, enum_name):
    path = Path(source) / 'identity.json'
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


def _validate_kurage(source):
    """Pre-flight check for the Kurage (Lesser Spotted Jellyfloat, source 57) content."""
    _read_identity_source(source, 57, 'Kurage')
    from experimental.pikmin2_kurage_content import validate as validate_kurage_host
    validate_kurage_host(source)


def _parse_kurage_sidecar(text):
    tokens = text.split()
    if len(tokens) != 4 or tokens[0] != KURAGE_TEKI_HEADER or tokens[1] != '1':
        raise StagingError(f'existing {KURAGE_TEKI_TXT} is malformed')
    try:
        generator, teki_type = int(tokens[2]), int(tokens[3])
    except ValueError as error:
        raise StagingError(f'existing {KURAGE_TEKI_TXT} is malformed') from error
    if generator <= 0 or teki_type != 0:
        raise StagingError(f'existing {KURAGE_TEKI_TXT} is malformed')
    return generator


def _adapt_kurage(source, run, actors):
    """Adapter for Kurage (source 57): emit ``p2-kurage-teki.txt``.

    Exact native shape (``pc_p2_kurage_teki_policy.h::read``) is
    ``P2_KURAGE_TEKI_1 1 <generator> 0`` (Frog type 0 vehicle). In bridge mode
    the native setup takes the bound actor from the seed
    (``pc_p2_campaign_source == 57``), so the filed generator is a placeholder
    there; outside bridge mode it binds directly. Idempotent: a second call
    with the same run reuses the staged placeholder instead of overwriting.
    """
    _read_identity_source(source, 57, 'Kurage')
    run = Path(run)
    from experimental.pikmin2_kurage_content import stage_kurage_host
    stage_kurage_host(source, run)
    generators = [int(generator) for generator, _species in actors]
    for _, species in actors:
        if species != 'Kurage':
            raise StagingError(f'Kurage adapter got non-Kurage species: {species!r}')
    if not generators:
        raise StagingError('Kurage install requires at least one generator')
    path = run / KURAGE_TEKI_TXT
    if path.is_file():
        _parse_kurage_sidecar(path.read_text(encoding='ascii'))
        existing = path.read_bytes()
        return dict(species='Kurage', source_id=57, generators=sorted(set(generators)),
                    actors_config_sha256=hashlib.sha256(existing).hexdigest(),
                    placeholder_generator=True)
    placeholder = sorted(set(generators))[0]
    payload = f'{KURAGE_TEKI_HEADER} 1 {placeholder} 0\n'.encode('ascii')
    path.write_bytes(payload)
    return dict(species='Kurage', source_id=57, generators=sorted(set(generators)),
                actors_config_sha256=hashlib.sha256(payload).hexdigest(),
                placeholder_generator=True)


def _validate_minihoudai(source):
    """Pre-flight check for MiniHoudai (Gatling Groink, source 78) content."""
    _read_identity_source(source, 78, 'MiniHoudai')


def _stage_groink(source, run):
    """Stage the native Groink OWN inputs (#888 WP5) from an extractor tree.

    Writes ``p2-groink-parms.txt`` / ``p2-groink-fixed-parms.txt`` (verbatim
    retail enemyparm.txt), ``p2-groink-bank.txt`` and the
    ``minihoudai_<clip>_<ii>.mod`` poses through
    ``experimental.pikmin2_groink_stage``. 78 and 97 share one bank.
    """
    from experimental.pikmin2_groink_stage import GroinkStageError, stage_from
    try:
        return stage_from(Path(source), Path(run))
    except (GroinkStageError, OSError, KeyError, ValueError) as error:
        raise StagingError(f'Groink staging failed: {error}') from error


def _adapt_minihoudai(source, run, actors):
    """Adapter for MiniHoudai (source 78): Groink OWN inputs + actor sidecar.

    Stages the native source-FSM inputs (``_stage_groink``: retail parms, the
    clip/key-event/pose/muzzle bank and the pose meshes) and
    ``p2-groink-teki.txt``. The sidecar carries the SOURCE carcass timeline
    (proper fp11 gauge delay, fp12 respawn, general fp00 life from the staged
    retail enemyparm.txt; source defaults when absent), never the 2.0/3.0/1200
    fixture profile. The native campaign (bridge) setup binds actors from the
    seed and takes these values from the parms file, so the filed generator is
    a placeholder there; outside bridge mode it binds directly. The short
    fixture profile stays with the room-preview tools
    (``pikmin2_groink_carcass_teki.sidecar_config_short``). Idempotent across
    repeat calls like the Kurage adapter.
    """
    from experimental.pikmin2_groink_carcass_teki import sidecar_config
    from experimental.pikmin2_groink_stage import GroinkStageError, gauge_profile
    _read_identity_source(source, 78, 'MiniHoudai')
    run = Path(run)
    generators = [int(generator) for generator, _species in actors]
    for _, species in actors:
        if species != 'MiniHoudai':
            raise StagingError(f'MiniHoudai adapter got non-MiniHoudai species: {species!r}')
    if not generators:
        raise StagingError('MiniHoudai install requires at least one generator')
    groink = _stage_groink(source, run)
    path = run / GROINK_TEKI_TXT
    if path.is_file():
        existing = path.read_bytes()
        try:
            text = existing.decode('ascii')
        except UnicodeDecodeError as error:
            raise StagingError(f'existing {GROINK_TEKI_TXT} is malformed') from error
        tokens = text.split()
        if len(tokens) < 5 or tokens[0] != GROINK_TEKI_HEADER:
            raise StagingError(f'existing {GROINK_TEKI_TXT} is malformed')
        return dict(species='MiniHoudai', source_id=78, generators=sorted(set(generators)),
                    actors_config_sha256=hashlib.sha256(existing).hexdigest(),
                    placeholder_generator=True, groink=groink)
    placeholder = sorted(set(generators))[0]
    parm = Path(source) / 'enemyparm.txt'
    try:
        gauge, recovery, health = gauge_profile(parm.read_bytes() if parm.is_file() else None)
        payload = sidecar_config(placeholder, 0, gauge, recovery, health).encode('ascii')
    except (GroinkStageError, ValueError) as error:
        raise StagingError(str(error)) from error
    path.write_bytes(payload)
    return dict(species='MiniHoudai', source_id=78, generators=sorted(set(generators)),
                actors_config_sha256=hashlib.sha256(payload).hexdigest(),
                placeholder_generator=True, carcass_profile=[gauge, recovery, health],
                groink=groink)


def _validate_bigtreasure(source):
    """Pre-flight check for BigTreasure (Titan Dweevil, source 73) content."""
    _read_identity_source(source, 73, 'BigTreasure')
    from experimental.pikmin2_bigtreasure_campaign import BigTreasureStageError, plan
    try:
        plan(source)
    except (BigTreasureStageError, OSError, KeyError, ValueError) as error:
        raise StagingError(f'BigTreasure content invalid: {error}') from error


def _adapt_bigtreasure(source, run, actors):
    """Adapter for BigTreasure (source 73): the native campaign core inputs.

    Stages ``p2-bigtreasure-parms.txt`` (verbatim retail enemyparm.txt),
    ``p2_bigtreasure_events.txt`` (29-clip key-event table), the
    ``p2-bigtreasure-bank.txt`` pose/joint/leg bank and the pose + weapon
    pellet meshes into the private model room. The native bridge setup binds
    every seed actor whose source is 73; no generator sidecar is needed.
    """
    from experimental.pikmin2_bigtreasure_campaign import BigTreasureStageError, stage_from
    _read_identity_source(source, 73, 'BigTreasure')
    generators = [int(generator) for generator, _species in actors]
    for _, species in actors:
        if species != 'BigTreasure':
            raise StagingError(f'BigTreasure adapter got non-BigTreasure species: {species!r}')
    if not generators:
        raise StagingError('BigTreasure install requires at least one generator')
    try:
        receipt = stage_from(Path(source), Path(run))
    except (BigTreasureStageError, OSError, KeyError, ValueError) as error:
        raise StagingError(f'BigTreasure staging failed: {error}') from error
    return dict(species='BigTreasure', source_id=73, generators=sorted(set(generators)), bigtreasure=receipt)


def _adapt_cannon_projectile(source, run, actors):
    """Cannon/projectile family (#350) plus the FminiHoudai (97) Groink inputs.

    Runs the shared-contract cannon installer unchanged, then, when a
    FminiHoudai actor is bound, stages the native Groink OWN inputs from the
    cannon extraction's FminiHoudai bank (``p2-groink-fixed-parms.txt`` and,
    unless a MiniHoudai install already staged them, the shared bank + poses).
    """
    from experimental import pikmin2_cannon_projectile_install as cannon
    receipt = cannon.install(Path(source), Path(run), list(actors))
    if any(species == 'FminiHoudai' for _generator, species in actors):
        groink = _stage_groink(source, run)
        if isinstance(receipt, dict):
            receipt = dict(receipt, groink=groink)
    return receipt


def _chappy_content_root(source, actors):
    """Resolve the identity-keyed content root for a Chappy-family install.

    ``install_layout`` groups by family, so this adapter runs once per layout
    with every Chappy-family actor while ``source`` is only the first
    binding's ``<content_root>/<enum>`` species dir. The content root is the
    directory whose per-species children hold every bound species'
    ``proxy.json`` (the Chappy extractor output).
    """
    species = {species for _, species in actors}
    candidates = [Path(source), Path(source).parent]
    for candidate in candidates:
        if all((candidate / name / 'proxy.json').is_file() for name in species):
            return candidate
    raise StagingError(
        f'Chappy content root missing proxy.json for {sorted(species)} under {source}')


def _validate_chappy(source):
    """Pre-flight check for one Chappy-family species dir (full plan at install)."""
    from experimental import pikmin2_chappy_content as chappy_content
    chappy_content.validate_source(source)


def _adapt_chappy(source, run, actors):
    """Adapter for the own-identity Chappy family (source 2, Chappy, first).

    Stages all Chappy-family actors through
    ``experimental.pikmin2_chappy_content`` in one grouped call: one shared
    actors/bank file plus every bound species' pose meshes.
    ``install_layout`` already groups bindings by family, so this runs once
    per layout with all Chappy-family generators.
    """
    from experimental import pikmin2_chappy_content as chappy_content
    pairs = [(int(generator), species) for generator, species in actors]
    for _, species in pairs:
        if species not in chappy_content.ID_FOR_SPECIES:
            raise StagingError(f'Chappy adapter got non-Chappy species: {species!r}')
    if not pairs:
        raise StagingError('Chappy install requires at least one generator')
    content_root = _chappy_content_root(source, pairs)
    return chappy_content.stage_chappy(content_root, run, pairs)


def _validate_frog(source):
    """Pre-flight check for the Frog (Yellow Wollywog, source 17) content.

    The source is the frog bank dir (``frogs.json`` + ``Frog/`` + ``MaroFrog/``
    pose banks) produced by ``extract_frog``; the full manifest contract stays
    authoritative inside ``experimental.pikmin2_frog_install``.
    """
    source = Path(source)
    if not (source / 'frogs.json').is_file():
        raise StagingError(f'Frog bank missing for identity content: {source / "frogs.json"}')


def _adapt_frog(source, run, actors):
    """Adapter for Frog (source 17): stage ``p2-frog.txt`` + pose meshes.

    Reuses ``experimental.pikmin2_frog_install.install`` for the
    ``p2-frog.txt`` protocol and ``frog_*`` visuals. In bridge mode the native
    setup takes the bound actor from the seed (``pc_p2_campaign_ids(17)``), so
    the filed generators are placeholders there; outside bridge mode they bind
    directly. ``install_layout`` groups by family, so this runs once per layout
    with all Frog generators. Accepts MaroFrog actors as well because the bank
    carries both species (the 18 row lands next).
    """
    from experimental import pikmin2_frog_install as frog
    pairs = [(int(generator), species) for generator, species in actors]
    for _, species in pairs:
        if species not in ('Frog', 'MaroFrog'):
            raise StagingError(f'Frog adapter got non-Frog species: {species!r}')
    if not pairs:
        raise StagingError('Frog install requires at least one generator')
    try:
        return frog.install(Path(source), Path(run), pairs)
    except ValueError as error:
        raise StagingError(str(error)) from error


def _proxy_content_root(source, actors):
    """Resolve the identity-keyed content root for a proxy install.

    ``install_layout`` groups by family, so this adapter runs once per layout
    with every proxy actor while ``source`` is only the first binding's
    ``<content_root>/<enum>`` species dir. The content root is the directory
    whose per-species children hold every bound species' ``proxy.json``.
    """
    species = {species for _, species in actors}
    candidates = [Path(source), Path(source).parent]
    for candidate in candidates:
        if all((candidate / name / 'proxy.json').is_file() for name in species):
            return candidate
    raise StagingError(
        f'Proxy content root missing proxy.json for {sorted(species)} under {source}')


def _validate_proxy(source):
    """Pre-flight check for one proxy species dir (full plan runs at install)."""
    from experimental import pikmin2_proxy_content as proxy_content
    proxy_content.validate_species_dir(source)


def _adapt_proxy(source, run, actors):
    """Adapter for the data-driven proxy family (sources 2, 17, ...).

    Stages all proxy actors through ``experimental.pikmin2_proxy_content``
    in one grouped call: one shared campaign/actors/bank file plus every
    bound species' pose meshes. ``install_layout`` already groups bindings
    by family, so this runs once per layout with all proxy generators.
    """
    from experimental import pikmin2_proxy_content as proxy_content
    from randomizer.p2_proxy import load_rows
    pairs = [(int(generator), species) for generator, species in actors]
    rows = {row['enum_name']: row for row in load_rows()}
    for _, species in pairs:
        if species not in rows:
            raise StagingError(f'Proxy adapter got non-proxy species: {species!r}')
    if not pairs:
        raise StagingError('Proxy install requires at least one generator')
    content_root = _proxy_content_root(source, pairs)
    return proxy_content.stage_proxy(content_root, run, pairs)


def _validate_tank(source):
    """Pre-flight check for the Tank/Wtank bank (tank.json + Tank/ + Wtank/)."""
    source = Path(source)
    if not (source / 'tank.json').is_file():
        raise StagingError(f'Tank bank missing for identity content: {source / "tank.json"}')


def _adapt_tank(source, run, actors):
    """Adapter for Tank (24) + Wtank (25): stage p2-tank.txt + poses."""
    from experimental import pikmin2_tank_identity_install as tank
    pairs = [(int(generator), species) for generator, species in actors]
    for _, species in pairs:
        if species not in ('Tank', 'Wtank'):
            raise StagingError(f'Tank adapter got non-Tank species: {species!r}')
    if not pairs:
        raise StagingError('Tank install requires at least one generator')
    try:
        return tank.install(Path(source), Path(run), pairs)
    except ValueError as error:
        raise StagingError(str(error)) from error


def _validate_kabuto(source):
    """Pre-flight check for the Kabuto bank (cannon_projectile.json)."""
    source = Path(source)
    if not (source / 'cannon_projectile.json').is_file():
        raise StagingError(f'Kabuto bank missing for identity content: {source / "cannon_projectile.json"}')


def _adapt_kabuto(source, run, actors):
    """Adapter for Kabuto (75): stage p2-kabuto.txt + poses."""
    from experimental import pikmin2_kabuto_identity_install as kabuto
    pairs = [(int(generator), species) for generator, species in actors]
    for _, species in pairs:
        if species != 'Kabuto':
            raise StagingError(f'Kabuto adapter got non-Kabuto species: {species!r}')
    if not pairs:
        raise StagingError('Kabuto install requires at least one generator')
    try:
        return kabuto.install(Path(source), Path(run), pairs)
    except ValueError as error:
        raise StagingError(str(error)) from error


def _validate_long_legs(source):
    """Pre-flight check for the Long Legs identity content (56/69, plus 66).

    The source is the long-legs import dir (``long-legs-family.json`` for
    Houdai 66 + BigFoot 69, plus ``damagumo-family.json`` + ``Demon/enemy.bmd``
    when a Damagumo actor is staged). The full contract stays authoritative
    inside ``experimental.pikmin2_long_legs_install.plan``; this only proves
    the identity manifests are present before the run tree is written.
    """
    from experimental.pikmin2_long_legs_install import MANIFEST as _LL_MANIFEST
    from experimental.pikmin2_long_legs_install import DAMAGUMO_MANIFEST as _DM_MANIFEST
    source = Path(source)
    manifest_path = source / _LL_MANIFEST
    if not manifest_path.is_file():
        raise StagingError(f'Long Legs manifest missing for identity content: {manifest_path}')
    try:
        manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError, ValueError) as error:
        raise StagingError(f'Long Legs manifest unreadable: {manifest_path}') from error
    if manifest.get('schema') != 1 or manifest.get('family') != 'Long Legs':
        raise StagingError(f'Long Legs manifest identity mismatch: {manifest_path}')
    if set(manifest.get('profiles', {})) != {'66', '69'}:
        raise StagingError(f'Long Legs profile set mismatch: {manifest_path}')


def _adapt_long_legs(source, run, actors):
    """Adapter for Long Legs (Damagumo 56 / Houdai 66 / BigFoot 69).

    Reuses ``experimental.pikmin2_long_legs_install.install`` for the
    profile/bank/actor configs plus the ``*_enemy.bmd`` meshes, then stages
    the native bind shapes (``longlegs_<species>_bind_00.mod``) the
    ``pc_p2_long_legs`` draw path opens: Houdai/BigFoot via
    ``experimental.pikmin2_long_legs_visual.convert``, Damagumo via the same
    bind conversion applied to the staged ``Damagumo_enemy.bmd``.
    ``install_layout`` groups by family, so this runs once per layout with all
    Long Legs actors.
    """
    from experimental import pikmin2_long_legs_install as long_legs
    from experimental import pikmin2_long_legs_visual as long_visual
    pairs = [(int(generator), species) for generator, species in actors]
    for _, species in pairs:
        if species not in ('Damagumo', 'Houdai', 'BigFoot'):
            raise StagingError(f'Long Legs adapter got non-Long-Legs species: {species!r}')
    if not pairs:
        raise StagingError('Long Legs install requires at least one generator')
    # The shared installer refuses an unused Damagumo source mesh, but the
    # identity content dirs carry the full family tree (so a grouped
    # Damagumo+BigFoot layout stages from either source). Prune the Demon
    # files via a temp source when no Damagumo actor is staged.
    import shutil as _shutil
    import tempfile as _tempfile
    staged_names = {species for _, species in pairs}
    _tmpdir = None
    try:
        effective_source = Path(source)
        if 'Damagumo' not in staged_names:
            demon_manifest = Path(source) / 'damagumo-family.json'
            demon_mesh = Path(source) / 'Demon' / 'enemy.bmd'
            if demon_manifest.is_file() or demon_mesh.is_file():
                _tmpdir = _tempfile.TemporaryDirectory()
                _tmp = Path(_tmpdir.name)
                for _child in Path(source).iterdir():
                    if _child.name == 'damagumo-family.json':
                        continue
                    if _child.name == 'Demon':
                        continue
                    if _child.is_dir():
                        _shutil.copytree(_child, _tmp / _child.name)
                    else:
                        _shutil.copyfile(_child, _tmp / _child.name)
                effective_source = _tmp
        try:
            receipt = long_legs.install(effective_source, Path(run), pairs)
        except ValueError as error:
            raise StagingError(str(error)) from error
    finally:
        if _tmpdir is not None:
            _tmpdir.cleanup()
    # Stage the native bind shapes from the just-installed meshes. The shared
    # visual converter covers Houdai/BigFoot only and rejects a Damagumo mesh
    # as stray, so a Damagumo mesh is parked aside for the shared conversion,
    # then restored and converted via the identical bind bake.
    run = Path(run)
    room = run / 'assets/dataDir/courses/pikmin2room'
    staged = {species for _, species in pairs}
    parked = None
    if 'Damagumo' in staged:
        mesh_path = room / 'Damagumo_enemy.bmd'
        if mesh_path.is_file():
            parked = room / 'Damagumo_enemy.bmd.parked'
            mesh_path.rename(parked)
    try:
        try:
            long_visual.convert(room)
        except ValueError as error:
            raise StagingError(str(error)) from error
    finally:
        if parked is not None and parked.is_file():
            parked.rename(room / 'Damagumo_enemy.bmd')
    if 'Damagumo' in staged:
        mesh_path = room / 'Damagumo_enemy.bmd'
        mod_path = room / 'longlegs_Damagumo_bind_00.mod'
        if not mesh_path.is_file():
            raise StagingError(f'Damagumo staged mesh missing for bind conversion: {mesh_path}')
        if mod_path.is_file():
            raise StagingError(f'Refusing existing/conflicting Damagumo bind mod: {mod_path}')
        # Damagumo bind bake (pinned #727 policy): explicit bind matrices via
        # joint_matrices(model, None) + rigid bake. The shared visual
        # _conversion uses the skinning draw-matrices path, which the strict
        # decoder rejects for the Damagumo mesh (unsupported display-list
        # attribute); the joint-matrices path is the model's own bind pose.
        from experimental.pikmin2_convert import blocks as _blocks
        from experimental.pikmin2_convert import decode as _decode
        from experimental.pikmin2_convert import write_model as _write_model
        from experimental.pikmin2_rigid import joint_matrices as _joint_matrices
        import tempfile
        model = mesh_path.read_bytes()
        try:
            matrices = _joint_matrices(_blocks(model), None)
            decoded = _decode(model, True, bake_rigid=True, draw_matrices=matrices)
            with tempfile.TemporaryDirectory() as _tmp:
                _target = Path(_tmp) / 'bind.mod'
                _write_model(decoded, _target, 'enemy.bmd')
                data = _target.read_bytes()
        except (ValueError, KeyError, ArithmeticError) as error:
            raise StagingError(f'Damagumo bind conversion failed: {error}') from error
        if not data:
            raise StagingError('Damagumo bind conversion produced no bytes')
        mod_path.write_bytes(data)
    return dict(receipt, bind_mods=sorted(
        (room / name).name for name in (
            [f'longlegs_{s}_bind_00.mod' for s in staged
             if (room / f'longlegs_{s}_bind_00.mod').is_file()])))


# Bespoke-family adapters, exposed alongside the shared-contract installers.
# Each adapter carries an optional ``validate(source)`` pre-flight hook run by
# ``install_layout`` before any destination write.
def _snagret_content_root(source, actors):
    """Resolve the identity-keyed content root for a snagret-pair install.

    ``install_layout`` groups by family, so this adapter runs once per layout
    with every snagret actor while ``source`` is only the first binding's
    ``<content_root>/<enum>`` species dir. Each enum dir carries the full
    shared import tree (``snagret.json`` plus per-species meshes, see
    ``scripts/p2_prepare_content`` ``extract_snagret``), so the first
    binding's dir suffices; fall back to its parent when it does not.
    """
    from experimental.pikmin2_snagret_content import validate_source
    species = {species for _, species in actors}
    for candidate in (Path(source), Path(source).parent):
        try:
            validate_source(candidate)
            return candidate
        except Exception:
            continue
    raise StagingError(
        f"Snagret content root missing snagret.json for {sorted(species)} under {source}")


def _validate_snagret(source):
    """Pre-flight check for the snagret-pair content tree."""
    from experimental import pikmin2_snagret_content as snagret_content
    snagret_content.validate_source(source)


def _adapt_snagret(source, run, actors):
    """Adapter for SnakeCrow (34) / SnakeWhole (70) with merge semantics.

    Stages both species' rows of ``p2-snagret-actors.txt`` +
    ``p2-snagret-bank.txt`` (plus pose meshes) through
    ``experimental.pikmin2_snagret_content``, merging with rows other
    snagret-family species (DangoMushi) already staged -- the snagret
    counterpart of the ``_adapt_ground_inverts`` co-install fix. The legacy
    shared installer stages actors + meshes but no bank, so 34/70-only
    bindings drew without their own model; this adapter always stages the
    bank. Idempotent across repeat calls and independent of family order.
    """
    from experimental import pikmin2_snagret_content as snagret_content
    pairs = [(int(generator), species) for generator, species in actors]
    for _, species in pairs:
        if species not in snagret_content.SPECIES_IDS:
            raise StagingError(f"Snagret adapter got non-snagret species: {species!r}")
    if not pairs:
        raise StagingError("Snagret install requires at least one generator")
    content_root = _snagret_content_root(source, pairs)
    return snagret_content.stage_snagret(content_root, run, pairs)


ADAPTERS = {
    'dwarf_orange': {'install': _adapt_dwarf_orange, 'validate': _validate_dwarf_orange},
    'snow': {'install': _adapt_snow, 'validate': _validate_snow},
    'kochappy': {'install': _adapt_kochappy, 'validate': _validate_kochappy},
    'sarai': {'install': _adapt_sarai, 'validate': _validate_sarai},
    'kogane': {'install': _adapt_kogane, 'validate': _validate_kogane},
    'sokkuri': {'install': _adapt_sokkuri, 'validate': _validate_sokkuri},
    'elecbug': {'install': _adapt_elecbug, 'validate': _validate_elecbug},
    'tamago': {'install': _adapt_tamago, 'validate': _validate_tamago},
    'ground_inverts': {'install': _adapt_ground_inverts, 'validate': _validate_ground_inverts},
    'dangomushi': {'install': _adapt_dangomushi, 'validate': _validate_dangomushi},
    'uji': {'install': _adapt_uji, 'validate': _validate_uji},
    'kurage': {'install': _adapt_kurage, 'validate': _validate_kurage},
    'minihoudai': {'install': _adapt_minihoudai, 'validate': _validate_minihoudai},
    'bigtreasure': {'install': _adapt_bigtreasure, 'validate': _validate_bigtreasure},
    'cannon_projectile': {'install': _adapt_cannon_projectile},
    'chappy': {'install': _adapt_chappy, 'validate': _validate_chappy},
    'frog': {'install': _adapt_frog, 'validate': _validate_frog},
    'tank': {'install': _adapt_tank, 'validate': _validate_tank},
    'armor': {'install': _adapt_ground_inverts, 'validate': _validate_ground_inverts},
    'kabuto': {'install': _adapt_kabuto, 'validate': _validate_kabuto},
    'long_legs': {'install': _adapt_long_legs, 'validate': _validate_long_legs},
    'snagret': {'install': _adapt_snagret, 'validate': _validate_snagret},
    'proxy': {'install': _adapt_proxy, 'validate': _validate_proxy},
}


def available():
    """Sorted family names this module can install."""
    return sorted(FAMILY_MODULES | ADAPTERS | _OVERRIDES)


def register(name, installer):
    """Register (or override) a family installer with the shared signature."""
    if not isinstance(name, str) or not name:
        raise ValueError('family name must be a non-empty string')
    if not callable(installer):
        raise ValueError('installer must be callable')
    _OVERRIDES[name] = installer


def _installer(name):
    if name in _OVERRIDES:
        return _OVERRIDES[name]
    if name in ADAPTERS:
        return ADAPTERS[name]['install']
    if name not in FAMILY_MODULES:
        raise ValueError(f'unknown family installer: {name!r}')
    module = import_module(FAMILY_MODULES[name])
    return module.install


def _validator(name):
    if name in _OVERRIDES:
        return None
    if name in ADAPTERS:
        return ADAPTERS[name].get('validate')
    return None


def prepare_private_destination(run, retail_assets, room=ROOM, *, campaign=False):
    """Build ``<run>/assets`` with the model room real and the rest retail-linked.

    Reuses the room-overlay scheme: untouched directories stay junctions and
    files are hardlinked, but the family model room is materialized as a real
    directory so an installer can write into it without touching retail assets.
    """
    from scripts.preview_pikmin2_room import overlay
    assets = Path(run) / 'assets'
    if assets.exists():
        raise ValueError(f'run assets already prepared: {assets}')
    sentinel = f'{room}/{PLACEHOLDER}'
    overrides = {sentinel: b''}
    if campaign:
        from experimental.pikmin2_campaign_assets import campaign_overrides
        overrides.update(campaign_overrides(retail_assets))
    overlay(Path(retail_assets), assets, overrides)
    placeholder = assets / room / PLACEHOLDER
    if not placeholder.is_file():
        raise ValueError('room overlay did not materialize the private destination')
    placeholder.unlink()
    return assets


def install_family(name, source, run, actors, retail_assets=None):
    """Install a named family into ``run`` and return its receipt.

    When ``retail_assets`` is given the private model destination is prepared
    first; otherwise the caller must already have a private room tree.
    """
    run = Path(run)
    if retail_assets is not None:
        prepare_private_destination(run, Path(retail_assets))
    room = run / 'assets' / ROOM
    if not room.is_dir() or not room.resolve().is_relative_to(run.resolve()):
        raise ValueError('family install requires a private model destination; pass retail_assets')
    receipt = _installer(name)(Path(source), run, list(actors))
    if receipt is not None:
        (run / f'{name}-family-install-receipt.json').write_text(
            json.dumps(receipt, sort_keys=True, indent=2) + '\n', encoding='utf-8')
    return receipt


def resolve_family(identity):
    """Resolve a P2 source id or enum name to a lane 05 family key.

    ``identity`` is an ``int`` source id or a ``str`` enum name (case-insensitive).
    Unknown identities raise ``ValueError`` rather than silently falling back to a
    P1 analogue, so an untracked identity never receives wrong content.
    """
    if isinstance(identity, bool):
        raise ValueError(f'unknown P2 identity: {identity!r}')
    if isinstance(identity, int):
        key = identity
    elif isinstance(identity, str):
        key = identity.strip().lower()
        if not key:
            raise ValueError(f'unknown P2 identity: {identity!r}')
    else:
        raise ValueError(f'unknown P2 identity: {identity!r}')
    family = IDENTITY_FAMILY.get(key)
    if family is None:
        raise ValueError(f'no family installer for P2 identity: {identity!r}')
    return family


def _resolve_binding_family(target, source_id, enum_name):
    """Resolve a binding's family, requiring its source id and enum name to agree.

    Both the source id and the enum name must resolve to the same family, so a
    binding like ``{"source_id": 999, "enum_name": "BlueKochappy"}`` fails closed
    instead of silently installing by name alone.
    """
    try:
        family = resolve_family(enum_name)
    except ValueError as exc:
        raise StagingError(f'no family installer for P2 enum {enum_name!r}') from exc
    if source_id is not None:
        try:
            family_by_id = resolve_family(source_id)
        except ValueError as exc:
            raise StagingError(
                f'no family installer for P2 source id {source_id!r}; disagrees with enum {enum_name!r}') from exc
        if family_by_id != family:
            raise StagingError(
                f'binding {target!r}: source id {source_id} ({family_by_id!r}) disagrees with enum {enum_name!r} ({family!r})')
    return family


def _installer_sidecar(path):
    """True when ``path`` is a run-root regular file an installer produced.

    Excludes the native session machinery (``SESSION_FILES``) and the binding
    receipt (written by this module only after every install succeeds).
    """
    return path.is_file() and path.name not in SESSION_FILES and path.name != BINDING_RECEIPT


def _content_files(run):
    """Snapshot the family-installed files in a run tree as ``{relpath: sha256}``.

    Captures only regular files the installer produced: run-root files (excluding
    the native session machinery and the binding receipt) and every file under the
    private model room. The assets overlay's retail junctions/hardlinks are never
    walked, so this is cheap and content-only.
    """
    files = {}
    for path in sorted(run.iterdir()):
        if _installer_sidecar(path):
            files[path.name] = sha256_file(path)
    room = run / 'assets' / ROOM
    if room.is_dir():
        for path in sorted(room.rglob('*')):
            if path.is_file():
                files[path.relative_to(run).as_posix()] = sha256_file(path)
    return files


def _populate_cache(cache_root, run, files, aggregate):
    """Copy the just-installed content into a session-level cache keyed by plan.

    The marker (``cache-receipt.json``) is written last. An interrupt mid-copy
    removes the whole partial ``p2bind-<digest>`` tree (never a half-written cache)
    and re-raises, so the next launch seeds a fresh install rather than reusing a
    partial tree.
    """
    tree = cache_root / 'tree'
    try:
        for relpath, digest in files.items():
            source = run / relpath
            destination = tree / relpath
            if not source.is_file() or sha256_file(source) != digest:
                raise StagingError(f'p2 content snapshot changed for {relpath}')
            destination.parent.mkdir(parents=True, exist_ok=True)
            temp = destination.parent / f'{destination.name}.{os.getpid()}.{next(_TEMP)}{TEMP_SUFFIX}'
            try:
                shutil.copyfile(source, temp)
                os.replace(temp, destination)
            finally:
                if temp.exists():
                    temp.unlink()
    except BaseException:
        shutil.rmtree(cache_root, ignore_errors=True)
        raise
    marker = cache_root / CACHE_RECEIPT
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(json.dumps(aggregate, indent=2, sort_keys=True) + '\n', encoding='utf-8')


def _replay_from_cache(run, cache_root, marker, retail_assets):
    """Materialize cached content into a fresh run without re-reading sources."""
    try:
        saved = json.loads(marker.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError, ValueError) as error:
        raise StagingError('corrupt p2 content cache; clear it and restage') from error
    if not isinstance(saved, dict) or saved.get('schema') != 1 or saved.get('mode') != 'identity-binding':
        raise StagingError('conflicting or partial p2 content cache; clear it and restage')
    files = saved.get('files')
    if not isinstance(files, dict):
        raise StagingError('p2 content cache is missing its file manifest; clear it and restage')
    if (run / 'assets').exists():
        raise StagingError('run assets already exist; conflicting p2 binding install')
    run.mkdir(parents=True, exist_ok=True)
    if retail_assets is not None:
        prepare_private_destination(run, Path(retail_assets), campaign=True)
    tree = cache_root / 'tree'
    for relpath, digest in files.items():
        source = tree / relpath
        target = run / relpath
        if not source.is_file() or sha256_file(source) != digest:
            raise StagingError(f'p2 content cache missing or corrupt for {relpath}; clear it and restage')
        if target.is_file() and sha256_file(target) == digest:
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        temp = target.parent / f'{target.name}.{os.getpid()}.{next(_TEMP)}{TEMP_SUFFIX}'
        try:
            shutil.copyfile(source, temp)
            os.replace(temp, target)
        finally:
            if temp.exists():
                temp.unlink()
    receipt = dict(saved, cached=True)
    (run / BINDING_RECEIPT).write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    return receipt


def install_layout(run, layout, content_root, actor_bindings=None, retail_assets=None, cache_dir=None):
    """Stage each bound identity's family content into a generated-session run.

    ``layout`` is the seed's ``p2_layout`` mapping with ``bindings`` entries
    ``{"target", "source_id", "enum_name"}``. ``content_root`` is an identity-keyed
    content root; the source for a binding is ``content_root/<enum_name>``.
    ``actor_bindings`` maps every ``target`` token to its int native generator id
    (the runtime seam owned by lane 03/04 + native ``ENEMY_P2``); a missing mapping
    fails closed rather than installing untargeted content.

    ``cache_dir`` (optional) is a session-level cache directory. When supplied the
    staged content is keyed there (``p2bind-<plan digest>``), so a later launch into
    a fresh run dir materializes from the cache without re-reading sources and
    reports ``cached=True``. Without ``cache_dir``, the receipt remains at
    ``<run>/p2-binding-receipt.json`` and a matching receipt is a cached replay.

    Acceptance: fresh install, cached replay from the session cache, and fail-closed
    on unknown identities, source-id/enum disagreement, missing/wrong sources, the
    family pre-flight check, missing actor bindings, or a conflicting/partial tree.
    """
    run = Path(run)
    bindings = (layout or {}).get('bindings')
    if not isinstance(bindings, list) or not bindings:
        raise ValueError('p2_layout has no bindings')
    actor_bindings = dict(actor_bindings or {})

    # The plan digest identifies the bindings + actor map, so a matching receipt
    # or cache marker is a cached replay even after the content root is gone.
    canonical = {
        'bindings': [dict(b) for b in bindings],
        'actor_bindings': {str(t): int(g) for t, g in actor_bindings.items()},
    }
    plan_digest = hashlib.sha256(
        json.dumps(canonical, sort_keys=True, separators=(',', ':')).encode('utf-8')).hexdigest()

    # Cached-replay detection happens before any source/binding validation, so a
    # replay never re-reads the content root (its sources may already be gone).
    cache_root = Path(cache_dir) / (CACHE_KEY_PREFIX + plan_digest) if cache_dir is not None else None
    if cache_root is not None and (cache_root / CACHE_RECEIPT).is_file():
        return _replay_from_cache(run, cache_root, cache_root / CACHE_RECEIPT, retail_assets)

    receipt_path = run / BINDING_RECEIPT
    if cache_root is None and receipt_path.is_file():
        try:
            existing = json.loads(receipt_path.read_text(encoding='utf-8'))
        except (OSError, json.JSONDecodeError, ValueError) as error:
            raise StagingError('unreadable p2 binding receipt; clear the run tree to restage') from error
        if (isinstance(existing, dict) and existing.get('schema') == 1
                and existing.get('mode') == 'identity-binding'
                and existing.get('plan_digest') == plan_digest):
            return dict(existing, cached=True)
        raise StagingError('conflicting or partial p2 binding install detected; refusing to restage')

    # Validate every binding (identity resolution + agreement, source presence,
    # family pre-flight and actor binding) before creating or writing anything.
    plans = []
    for binding in bindings:
        target = binding.get('target')
        source_id = binding.get('source_id')
        enum_name = binding.get('enum_name')
        family = _resolve_binding_family(target, source_id, enum_name)
        source = Path(content_root) / enum_name
        if not source.is_dir():
            raise StagingError(f'missing content source for {enum_name!r}: {source}')
        validator = _validator(family)
        if validator is not None:
            validator(source)
        try:
            generator = int(actor_bindings[target])
        except KeyError:
            raise StagingError(f'no actor generator binding for target {target!r}') from None
        except (TypeError, ValueError):
            raise StagingError(f'actor generator for target {target!r} must be an int') from None
        plans.append((target, enum_name, family, source, generator))

    if (run / 'assets').exists():
        raise StagingError('run assets already exist; conflicting p2 binding install')

    run.mkdir(parents=True, exist_ok=True)
    if retail_assets is not None:
        prepare_private_destination(run, Path(retail_assets), campaign=True)
    # A family installer owns its run-root sidecars and refuses a second install, and
    # seeds repeat families (several Otakara, Mamuta, ...), so install each family once
    # with every actor bound to it. Each family source holds the whole family import.
    by_family = {}
    for target, enum_name, family, source, generator in plans:
        entry = by_family.setdefault(family, dict(source=source, actors=[], targets=[]))
        entry['actors'].append((generator, enum_name))
        entry['targets'].append(target)
    receipts = {}
    try:
        for family, entry in by_family.items():
            receipt = _installer(family)(entry['source'], run, entry['actors'])
            for target in entry['targets']:
                receipts[target] = receipt
    except BaseException:
        # A family installer that fails mid-copy must not leave a partial asset
        # tree or run-root sidecars (e.g. p2-snow.txt copied by the Snow adapter):
        # remove the private overlay (its retail junctions are not followed) plus
        # every adapter-produced run-root file, preserving only the native session
        # files and the (not-yet-written) binding receipt, then re-raise so the
        # next launch performs a fresh install.
        if (run / 'assets').exists():
            shutil.rmtree(run / 'assets', ignore_errors=True)
        if run.is_dir():
            for path in run.iterdir():
                if _installer_sidecar(path):
                    path.unlink(missing_ok=True)
        raise
    files = _content_files(run)
    aggregate = dict(schema=1, mode='identity-binding', plan_digest=plan_digest,
                     bindings=list(bindings), receipts=receipts, files=files)
    receipt_path.write_text(json.dumps(aggregate, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    if cache_root is not None:
        _populate_cache(cache_root, run, files, aggregate)
    return aggregate


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--family', required=True, choices=available())
    parser.add_argument('--source', type=Path, required=True,
                        help='family bank/imported source directory')
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--retail', type=Path, default=None,
                        help='retail assets root; required to prepare a private destination')
    parser.add_argument('--actor', action='append', default=[],
                        help='generator_id:Species, repeatable')
    args = parser.parse_args(argv)
    actors = [(int(value.split(':', 1)[0]), value.split(':', 1)[1]) for value in args.actor]
    receipt = install_family(args.family, args.source, args.run, actors, retail_assets=args.retail)
    print(json.dumps(receipt, sort_keys=True, indent=2) if receipt is not None else '{}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
