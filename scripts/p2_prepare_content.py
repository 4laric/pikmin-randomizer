"""ISO to P2 content root, actor bindings and staged playable seed helper.

Single step from the P2 ISO to what ``randomizer run --p2-content --p2-actors``
needs (``randomizer/runner.py`` ``launch`` -> ``experimental/pikmin2_family_install``
``install_layout``):

* ``--iso <iso> --out <dir>`` extracts, from the ISO, an identity-keyed content
  root (``<out>/<enum_name>/...``, the layout ``install_layout`` reads) for the
  playable families first (dwarf_orange 44, mamuta 54, dweevil 59-62), then as
  many of the other admitted ids as the existing installers support.
* ``--seed-manifest <m.json> --actors-out <json>`` writes the
  ``{target: generator_id}`` actor bindings for that seed.

Existing per-family extractors are reused as-is; nothing here rewrites them:

* 44 BlueKochappy: ``pikmin2_dwarf_orange_profile.extract`` + 
  ``pikmin2_dwarf_orange_bank.build`` -> ``<out>/BlueKochappy/{bank,profile}/``.
* 54 Miulin: ``pikmin2_mamuta_assets.extract`` -> ``<out>/Miulin/`` directly
  (``mamuta.json`` + ``Miulin/`` pose bank, the layout the mamuta installer reads).
* 59-62 Otakara: ``pikmin2_dweevil_assets.extract`` once, then the full import
  tree (``dweevils.json`` + per-species banks) is placed under each of
  ``<out>/FireOtakara`` etc., because the shared-contract dweevil installer
  validates the whole five-species manifest per install.
* 23 Sarai: ``pikmin2_sarai_assets.extract`` for the source poses, then the
  validator-required ``sarai-attack-mouths.txt`` mouth bank is derived from that
  extraction result (mouth joints + sampled pose files + sha256); the Sarai
  adapter stages the eight native host files through ``pikmin2_sarai_install``.
* 32 Demon: ``pikmin2_sarai_assets.extract_species`` over ``enemy/data/Demon``
  (Demon::Obj is a Sarai::Obj subclass) -> ``<out>/Demon/`` (``demon.json``,
  all twelve clips as ``demon_<clip>_<frame>.mod``, the retail parm files); the
  Demon adapter stages the native host files through ``pikmin2_demon_install``.
* 9 Kogane: ``pikmin2_kogane_assets.extract`` -> ``<out>/Kogane/``
  (``beetles.json`` plus the pose meshes flattened beside it); the Kogane
  adapter stages the room meshes through ``pikmin2_kogane_content``.
* 57 Kurage: ``pikmin2_kurage_assets.extract`` -> ``<out>/Kurage/``; the Kurage
  adapter stages the visual files through ``pikmin2_kurage_content``.
* 72 OniKurage (#960): ``pikmin2_onikurage_assets.extract`` -> ``<out>/OniKurage/``;
  the OniKurage adapter stages ``pikmin2_onikurage_content``.
* 78 MiniHoudai: ``pikmin2_minihoudai_assets.extract`` -> ``<out>/MiniHoudai/``
  (``minihoudai.json`` + ``identity.json`` + ``minihoudai_<clip>_<ii>.mod``);
  the MiniHoudai adapter stages the native Groink source-FSM inputs through
  ``experimental.pikmin2_groink_stage`` (retail ``p2-groink-parms.txt`` /
  ``p2-groink-fixed-parms.txt``, ``p2-groink-bank.txt`` and the poses into
  the private model room) plus the ``p2-groink-teki.txt`` carcass sidecar
  (source timeline). Poses are sampled per clip
  (``pikmin2_groink_stage.POSE_LIMITS``), not by the global pose limit.
* 38 PanModoki: ``pikmin2_breadbug_own_assets.extract`` -> ``<out>/PanModoki/``
  (``breadbug.json`` + ``identity.json`` + ``breadbug_<clip>_<ii>.mod``);
  the Breadbug adapter stages exactly the native OWN inputs through
  ``experimental.pikmin2_breadbug_stage`` (retail ``p2-breadbug-parms.txt``,
  ``p2-breadbug-bank.txt`` and the poses into the private model room).
* 79 Sokkuri: ``pikmin2_sokkuri_assets.extract`` -> ``<out>/Sokkuri/``
  (``sokkuri.json`` + ``ginv_Sokkuri_<clip>_<ii>.mod``); the Sokkuri adapter
  stages the batch-2 ground files through ``pikmin2_sokkuri_content``. A legacy
  ``ground_inverts.json`` import dir still stages through the shared ground
  installer unchanged.
* 34 SnakeCrow: ``pikmin2_snagret_assets.extract`` once, then
  the full import tree is placed under ``<out>/SnakeCrow`` and
  ``<out>/SnakeWhole``, because the shared-contract snagret installer
  validates the whole three-species manifest per install.
* 70 SnakeWhole: same shared snagret import tree as 34 (see above).
* 65 Imomushi: ``pikmin2_ground_inverts_assets.extract`` -> ``<out>/Imomushi/``
  (full six-species tree); the shared-contract ground installer validates the
  whole manifest per install.
* 71 UmiMushi: ``pikmin2_aquatic_assets.extract`` once, then the full import
  tree is placed under ``<out>/UmiMushi`` and ``<out>/UmiMushiBlind``.
* 101 UmiMushiBlind: same shared aquatic import tree as 71 (see above);
  Blind reuses the UmiMushi bank as a visual stand-in.
* 2 Chappy (inst-chappy #871): ``pikmin2_chappy_assets.extract`` ->
  ``<out>/Chappy/`` (``proxy.json`` + ``px_Chappy_<clip>_<ii>.mod``,
  byte-identical to the retired proxy extraction); the Chappy adapter stages
  the identity sidecars through ``pikmin2_chappy_content``.
* 33 FireChappy (inst-chappy #871): same own-identity Chappy-family path as
  Chappy (``<out>/FireChappy/``).
* 35 KumaChappy (inst-chappy #871): same own-identity Chappy-family path
  (``<out>/KumaChappy/``).
* 43 YellowChappy (inst-chappy #871): same own-identity Chappy-family path
  (``<out>/YellowChappy/``).
* 53 KingChappy (inst-chappy #871): same own-identity Chappy-family path
  (``<out>/KingChappy/``).
* 67 LeafChappy (inst-chappy #871): same own-identity Chappy-family path
  (``<out>/LeafChappy/``).
* 76 KumaKochappy (inst-chappy #871): same own-identity Chappy-family path
  (``<out>/KumaKochappy/``). The family lane is complete.
* 28 ElecBug: ``pikmin2_elecbug_assets.extract`` -> ``<out>/ElecBug/``
  (``elecbug.json`` + ``ginv_ElecBug_<clip>_<ii>.mod``); the ElecBug adapter
  stages its rows of the shared batch-2 ground files through
  ``pikmin2_elecbug_content`` (merging with other ground-identity species'
  rows). A legacy ``ground_inverts.json`` import dir still stages through the
  shared ground installer unchanged.
* 68 TamagoMushi: ``pikmin2_tamago_assets.extract`` -> ``<out>/TamagoMushi/``
  (``tamagomushi.json`` + ``ginv_TamagoMushi_<clip>_<ii>.mod``); the
  TamagoMushi adapter stages its rows of the shared batch-2 ground files
  through ``pikmin2_tamago_content`` (merging with other ground-identity
  species' rows). A legacy ``ground_inverts.json`` import dir still stages
  through the shared ground installer unchanged.
* 94 DangoMushi: ``pikmin2_dangomushi_assets.extract`` -> ``<out>/DangoMushi/``
  (``dangomushi.json`` + ``snake_DangoMushi_<clip>_<ii>.mod``); the DangoMushi
  adapter stages its rows of the shared snagret files through
  ``pikmin2_dangomushi_content`` (merging with other snagret-family rows). A
  legacy ``snagret.json`` import dir still stages through the shared snagret
  installer unchanged.
* 12-14 UjiA/UjiB/Tobi: ``pikmin2_uji_assets.extract`` once, then each Uji
  species tree (``uji.json`` + ``uji_<Species>_<clip>_<ii>.mod``) is placed
  under ``<out>/UjiA`` etc.; the Uji adapter stages the
  ``p2-uji-actors.txt`` / ``p2-uji-bank.txt`` sidecars plus the pose meshes
  through ``pikmin2_uji_content``.
* 17 Frog: ``pikmin2_frog_assets.extract`` -> ``<out>/Frog/``
  (``frogs.json`` + ``Frog/`` + ``MaroFrog/`` pose banks, the layout the frog
  installer reads); the Frog adapter stages ``p2-frog.txt`` through
  ``pikmin2_frog_install``.
* 18 MaroFrog: shares the Frog extraction (``<out>/MaroFrog/`` carries the same
  ``frogs.json`` bank); the Frog adapter stages both species together.
* 24 Tank: ``pikmin2_tank_assets.extract`` -> ``<out>/Tank/``
  (``tank.json`` + ``Tank/`` + ``Wtank/`` pose banks); the Tank adapter stages
  ``p2-tank.txt`` through ``pikmin2_tank_identity_install``.
* 25 Wtank: shares the Tank extraction (``<out>/Wtank/`` carries the same
  ``tank.json`` bank); the Tank adapter stages both species together.
* 15 Armor: ``pikmin2_ground_inverts_assets.extract`` -> ``<out>/Armor/``
  (``ground_inverts.json`` + per-species banks); the Armor adapter stages the
  ground files through ``pikmin2_ground_inverts_install``.
* 75 Kabuto: ``pikmin2_cannon_projectile_assets.extract`` -> ``<out>/Kabuto/``
  (``cannon_projectile.json`` + per-species banks); the Kabuto adapter stages
  ``p2-kabuto.txt`` through ``pikmin2_kabuto_identity_install``.
* 56 Damagumo: ``pikmin2_long_legs_assets.extract`` (66/69 manifest) +
  ``pikmin2_damagumo_profile_convert.convert_profile`` (56 manifest from the
  Damagumo disc rows) -> ``<out>/Damagumo/`` (``long-legs-family.json`` +
  ``damagumo-family.json`` + ``Demon/enemy.bmd``); the Long Legs adapter stages
  the configs plus the native bind shapes through ``pikmin2_long_legs_install``
  + ``pikmin2_long_legs_visual``.
* 63 Jigumo: ``pikmin2_aquatic_assets.extract`` (full 26/27/63/71 family import)
  copied under ``<out>/Jigumo/`` (``aquatic.json`` + per-species pose banks);
  the shared aquatic installer stages the Jigumo actors/bank/poses.
* 69 BigFoot: ``pikmin2_long_legs_assets.extract`` -> ``<out>/BigFoot/``
  (``long-legs-family.json`` + ``BigFoot/enemy.bmd``); the Long Legs adapter
  stages the configs plus the native bind shape as for Damagumo.
* 26 Catfish: ``pikmin2_aquatic_assets.extract`` -> ``<out>/Catfish/``
  (``aquatic.json`` + per-species pose banks); the shared-contract aquatic
  installer stages ``p2-aquatic-actors.txt``/``p2-aquatic-bank.txt``.
* 27 Tadpole: same aquatic family import under ``<out>/Tadpole/``.
* 84 Hana: ``pikmin2_ground_inverts_assets.extract`` -> ``<out>/Hana/``;
  the shared ground installer stages ``p2-ground-*.txt``.
* 93 BombOtakara: ``pikmin2_dweevil_assets.extract`` -> ``<out>/BombOtakara/``;
  the shared dweevil installer stages ``p2-dweevil-*.txt``.
* 66 Houdai: ``pikmin2_long_legs_assets.extract`` -> ``<out>/Houdai/``.
* 97 FminiHoudai: ``pikmin2_cannon_projectile_assets.extract`` ->
  ``<out>/FminiHoudai/``.
* 58 BombSarai (#244 OWN): ``pikmin2_bombsarai_assets.extract`` ->
  ``<out>/BombSarai/`` (``bombsarai.json`` + ``identity.json`` + the
  ``BombSarai/`` carrier and ``Bomb/`` payload pose banks, retail parms and
  bca clips); the BombSarai adapter runs the shared
  ``pikmin2_bombsarai_install`` and stages the native OWN inputs through
  ``pikmin2_bombsarai_stage`` (``p2-bombsarai-parms.txt``,
  ``p2-bombsarai-bomb-parms.txt``, ``p2-bombsarai-own-bank.txt``, the Bomb
  meshes and ``p2-bombsarai-teki.txt``).
* 41 Fuefuki (#245 OWN): ``pikmin2_fuefuki_assets.extract`` -> ``<out>/Fuefuki/``
  (``fuefuki.json`` + ``identity.json`` + retail parms/animmgr, the ten BCA
  clips incl. landing/landfail under the singular-scale policy, and
  ``fuefuki_Fuefuki_<clip>_<ii>.mod`` poses); the Fuefuki adapter stages the
  native source-FSM inputs through ``pikmin2_fuefuki_campaign_stage``.
* 73 BigTreasure (#246 OWN): ``pikmin2_bigtreasure_assets.extract`` ->
  ``<out>/BigTreasure/`` (the full import tree plus ``identity.json``); the
  BigTreasure adapter stages the native campaign core inputs through
  ``experimental.pikmin2_bigtreasure_campaign``.
Proxy species declared under ``randomizer/p2_proxy`` (one JSON file per
species, e.g. Chappy and Frog today) extract through the generic
``pikmin2_proxy_assets.extract`` into ``<out>/<Enum>/`` (``proxy.json`` plus
the ``px_<Enum>_<clip>_<ii>.mod`` pose meshes) and stage the shared
campaign/actors/bank sidecars plus the pose files through
``pikmin2_proxy_content``. Adding a species is one new declaration file;
the ``ENUM_FOR_SOURCE``/``EXTRACTORS`` rows and the dispatch arm below derive
from ``randomizer.p2_proxy.load_rows()`` instead of naming any species.
When ``--seed-manifest`` is given, every proxy id its ``p2_layout``
bindings actually bind (and its ``p2_proxy_tier`` covers) joins the
extraction set automatically; manifests without proxy bindings extract
exactly today's default list.

Extraction alone is not enough, and the difference is invisible from the native
side: a species whose assets extract but whose adapter does not stage what the
native loader opens boots as its P1 host with no error. That is how Sarai and
Kogane both failed (``bound=0 reason=host``, ``P2_SETUP_SKIP Kogane
clip_file_missing``). Wire the adapter with the extractor, and prove it with a
launch, not a unit test.

An id with a family installer but no extractor wired here is reported as
skipped, never fabricated -- the skip reason names which of the two is missing,
because they send you to different files. That set is not enumerated in prose:
it is ``set(ENUM_FOR_SOURCE) - set(EXTRACTORS)``, and it shrinks every time a
species is wired. ``test_docstring_bullets_match_extractors`` keeps the bullet
list above honest; twice now this docstring has gone stale the same day a
species landed.

Actor bindings map every ``p2_layout`` binding ``target`` (a slot-uid token
from ``docs/PIKMIN2_ADMITTED_PLACEMENT.json`` via
``randomizer/p2_placement_catalog.py``) to its int native generator id. The
derivation is deterministic and documented: ``generator_id = int(target)``.
Targets already are unique slot uids that fit in uint32, so the mapping is
bijective and every family sidecar gets distinct generator ids.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from experimental.pikmin2_animation import (  # noqa: E402  pose-density policy (#895)
    DEFAULT_POSE_LIMIT,
    LEGACY_POSE_LIMIT,
    POSE_LIMIT_MAX,
)

PLAYABLE_SOURCE_IDS = (44, 54, 59, 60, 61, 62)

ENUM_FOR_SOURCE = {
    1: "Kochappy",
    73: "BigTreasure",
    2: "Chappy",
    33: "FireChappy",
    35: "KumaChappy",
    43: "YellowChappy",
    53: "KingChappy",
    67: "LeafChappy",
    76: "KumaKochappy",
    9: "Kogane",
    12: "UjiA",
    13: "UjiB",
    14: "Tobi",
    15: "Armor",
    17: "Frog",
    18: "MaroFrog",
    23: "Sarai",
    32: "Demon",
    24: "Tank",
    25: "Wtank",
    26: "Catfish",
    27: "Tadpole",
    28: "ElecBug",
    34: "SnakeCrow",
    38: "PanModoki",
    68: "TamagoMushi",
    94: "DangoMushi",
    44: "BlueKochappy",
    45: "YellowKochappy",
    54: "Miulin",
    56: "Damagumo",
    57: "Kurage",
    72: "OniKurage",
    58: "BombSarai",
    59: "FireOtakara",
    60: "WaterOtakara",
    61: "GasOtakara",
    62: "ElecOtakara",
    63: "Jigumo",
    65: "Imomushi",
    66: "Houdai",
    69: "BigFoot",
    70: "SnakeWhole",
    71: "UmiMushi",
    75: "Kabuto",
    78: "MiniHoudai",
    79: "Sokkuri",
    84: "Hana",
    93: "BombOtakara",
    97: "FminiHoudai",
    101: "UmiMushiBlind",
    41: "Fuefuki",
}


def _proxy_declarations():
    """Proxy species declarations driving the data-driven wiring below."""
    from randomizer.p2_proxy import load_rows

    return load_rows()


_PROXY_ROWS = _proxy_declarations()
PROXY_SOURCE_IDS = frozenset(row["source_id"] for row in _PROXY_ROWS)
for _row in _PROXY_ROWS:
    ENUM_FOR_SOURCE[_row["source_id"]] = _row["enum_name"]




TARGET_RE = re.compile(r"[A-Za-z0-9_.:/-]+")

DEFAULT_RESEARCH = Path("C:/Users/alari/pikmin-randomizer/native/pikmin2-research")


def admitted_source_ids():
    """Admitted P2 source ids from the lane-02 roster, with a static fallback."""
    try:
        from experimental.pikmin2_enemy_roster import admitted_ids, load_and_validate

        return sorted(admitted_ids(load_and_validate()))
    except Exception:
        return [9, 23, 44, 54, 57, 59, 60, 61, 62, 78, 79]


def order_source_ids(wanted):
    """Playable families first, then the rest in numeric order."""
    wanted = list(dict.fromkeys(wanted))
    playable = [i for i in PLAYABLE_SOURCE_IDS if i in wanted]
    rest = sorted(i for i in wanted if i not in PLAYABLE_SOURCE_IDS)
    return playable + rest


def split_supported(wanted):
    """Split ids into (supported, unsupported) via the existing family map."""
    from experimental.pikmin2_family_install import resolve_family

    supported, unsupported = [], []
    for source_id in order_source_ids(wanted):
        try:
            resolve_family(source_id)
            supported.append(source_id)
        except ValueError:
            unsupported.append(source_id)
    return supported, unsupported


def content_dir_for(out, source_id):
    enum_name = ENUM_FOR_SOURCE.get(source_id)
    if enum_name is None:
        raise ValueError(f"unknown enum name for source id {source_id!r}")
    return Path(out) / enum_name


def proxy_ids_for_manifest(manifest_path):
    """Proxy source ids a seed manifest binds that the tier covers.

    Reads ``p2_layout.bindings`` from the manifest and returns the bound
    proxy source ids (see ``PROXY_SOURCE_IDS``) in binding order, failing
    closed when a bound proxy id is not covered by the manifest's
    ``p2_proxy_tier``. Manifests without proxy bindings return ``[]`` so
    today's default extraction list is unchanged byte-for-byte.
    """
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    layout = manifest.get("p2_layout")
    if not isinstance(layout, dict):
        return []
    bound = []
    for binding in layout.get("bindings", []):
        if isinstance(binding, dict) and binding.get("source_id") in PROXY_SOURCE_IDS:
            if binding["source_id"] not in bound:
                bound.append(binding["source_id"])
    if not bound:
        return []
    tier = manifest.get("p2_proxy_tier")
    if tier is None:
        raise ValueError(
            f"seed manifest binds proxy species {bound} without a "
            f"p2_proxy_tier key; regenerate with --p2-proxy-tier")
    from randomizer.p2_proxy import tier_ids
    covered = set(tier_ids(tier))
    uncovered = [source_id for source_id in bound if source_id not in covered]
    if uncovered:
        raise ValueError(
            f"seed manifest binds proxy species {uncovered} outside the "
            f"{tier!r} tier; regenerate with a covering --p2-proxy-tier")
    return bound


def extract_bluekochappy(iso, research, dest, pose_limit=3):
    """Build <dest>/BlueKochappy/{bank,profile}/ via the existing extractors."""
    from experimental import pikmin2_dwarf_orange_bank as bank_mod
    from experimental import pikmin2_dwarf_orange_profile as profile_mod

    iso, research, dest = Path(iso), Path(research), Path(dest)
    if not iso.is_file():
        raise ValueError(f"ISO not found: {iso}")
    if not research.is_dir():
        raise ValueError(f"research checkout not found: {research}")
    target = dest / "BlueKochappy"
    if target.exists():
        raise ValueError(f"content dir already exists: {target}")
    tmp_profile = dest / ".tmp-dwarf-profile"
    tmp_bank = dest / ".tmp-dwarf-bank"
    for tmp in (tmp_profile, tmp_bank):
        if tmp.exists():
            shutil.rmtree(tmp, ignore_errors=True)
    try:
        profile_mod.extract(iso, research, tmp_profile)
        bank_mod.build(tmp_profile, tmp_bank, pose_limit=pose_limit)
        bank_dst = target / "bank"
        profile_dst = target / "profile"
        bank_dst.mkdir(parents=True)
        profile_dst.mkdir(parents=True)
        for name in ("dwarf-orange-bank.json", "p2-dwarf-orange-bank.txt",
                     "p2-dwarf-orange-profile.txt"):
            shutil.copyfile(tmp_bank / name, bank_dst / name)
        for mod in sorted(tmp_bank.glob("dwarf_orange_*.mod")):
            shutil.copyfile(mod, bank_dst / mod.name)
        shutil.copyfile(tmp_profile / "dwarf-orange-profile.json",
                        profile_dst / "dwarf-orange-profile.json")
    finally:
        for tmp in (tmp_profile, tmp_bank):
            shutil.rmtree(tmp, ignore_errors=True)
    return target


def extract_miulin(iso, dest, pose_limit=3):
    """Build <dest>/Miulin/ via the existing mamuta extractor."""
    from experimental import pikmin2_mamuta_assets as mamuta

    iso, dest = Path(iso), Path(dest)
    if not iso.is_file():
        raise ValueError(f"ISO not found: {iso}")
    target = dest / "Miulin"
    if target.exists():
        raise ValueError(f"content dir already exists: {target}")
    dest.mkdir(parents=True, exist_ok=True)
    mamuta.extract(iso, target, pose_limit=pose_limit)
    return target


def extract_dweevil(iso, source_repo, dest, pose_limit=3):
    """Build <dest>/{Fire,Water,Gas,Elec}Otakara/ via the existing extractor.

    The shared-contract dweevil installer validates the whole five-species
    ``dweevils.json`` manifest on every install, so the full import tree is
    placed under each of the four enum dirs.
    """
    from experimental import pikmin2_dweevil_assets as dweevil

    iso, dest = Path(iso), Path(dest)
    if not iso.is_file():
        raise ValueError(f"ISO not found: {iso}")
    enums = ["FireOtakara", "WaterOtakara", "GasOtakara", "ElecOtakara"]
    for enum_name in enums:
        if (dest / enum_name).exists():
            raise ValueError(f"content dir already exists: {dest / enum_name}")
    tmp = dest / ".tmp-dweevil"
    if tmp.exists():
        shutil.rmtree(tmp, ignore_errors=True)
    try:
        dweevil.extract(iso, Path(source_repo), tmp, pose_limit=pose_limit)
        for enum_name in enums:
            shutil.copytree(tmp, dest / enum_name)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return [dest / e for e in enums]


def extract_sarai(iso, dest):
    """Build <dest>/Sarai/ via the existing sarai extractor plus a derived bank.

    ``pikmin2_sarai_assets.extract`` produces the source poses (``sarai.json``
    + ``*.mod``); the lane-05 Sarai validator additionally requires
    ``sarai-attack-mouths.txt``. That mouth bank is derived here from the
    extraction result (mouth joints + sampled pose files + sha256) and the
    derivation is recorded in ``sarai-mouths-provenance.json``.
    """
    from experimental import pikmin2_sarai_assets as sarai

    iso, dest = Path(iso), Path(dest)
    if not iso.is_file():
        raise ValueError(f"ISO not found: {iso}")
    target = dest / "Sarai"
    if target.exists():
        raise ValueError(f"content dir already exists: {target}")
    tmp = dest / ".tmp-sarai"
    if tmp.exists():
        shutil.rmtree(tmp, ignore_errors=True)
    try:
        result = sarai.extract(iso, tmp)
        target.mkdir(parents=True)
        (target / "sarai.json").write_text(json.dumps(result, indent=2) + "\n",
                                           encoding="utf-8")
        pose_files = []
        for clip in result.get("clips", []):
            for pose in clip.get("poses", []):
                name = pose.get("file")
                if not name:
                    continue
                src = tmp / name
                if src.is_file():
                    shutil.copyfile(src, target / name)
                    pose_files.append(name)
        mouths = ["rkamujnt", "lkamujnt"]
        lines = ["P2_SARAI_MOUTHS_1",
                 f"species Sarai enemy_id 23 mouths {' '.join(mouths)}",
                 f"poses {len(pose_files)}"]
        for name in sorted(pose_files):
            digest = hashlib.sha256((target / name).read_bytes()).hexdigest()
            lines.append(f"pose {name} {digest}")
        (target / "sarai-attack-mouths.txt").write_text(
            "\n".join(lines) + "\n", encoding="ascii")
        (target / "sarai-mouths-provenance.json").write_text(json.dumps(
            {"derived_from": "experimental.pikmin2_sarai_assets.extract",
             "joints": result.get("joints", []),
             "mouth_joints": mouths,
             "pose_files": sorted(pose_files)}, indent=2) + "\n",
            encoding="utf-8")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return target


def extract_demon(iso, dest):
    """Build <dest>/Demon/ (Bumbling Snitchbug, source 32) from the retail disc.

    Demon::Obj is a Sarai::Obj subclass (pikmin2 Demon.h) with its own model,
    animations and parms (``enemy/data/Demon``, ``enemyParms.szs`` ``demon/``).
    ``pikmin2_sarai_assets.extract_species`` is parameterised over that data
    directory: it writes ``demon.json`` (every clip of ``demon/enemyanimmgr.txt``
    with its key events, the ``rkamujnt``/``lkamujnt`` mouth matrices per sampled
    pose and the parsed ``demon/enemyparm.txt`` blocks) plus the sampled pose
    meshes, named ``demon_<clip>_<frame>.mod`` so they never collide with
    Sarai's ``<clip>_<frame>.mod`` in the shared model room. Clips are sampled
    every third frame (up to the 32-pose budget) so the looping flight clips
    read as motion, and attack1 is sampled on every frame of the Attack
    hunt/catch window (10..30) so the jaw sweep the retail catchTarget() tests
    is frame-exact. ``demon-provenance.json`` records the derivation. The
    native banks (poses, mouths, retail events, parms) are derived at install
    time by ``experimental.pikmin2_demon_install``.
    """
    from experimental import pikmin2_sarai_assets as sarai

    iso, dest = Path(iso), Path(dest)
    if not iso.is_file():
        raise ValueError(f"ISO not found: {iso}")
    target = dest / "Demon"
    if target.exists():
        raise ValueError(f"content dir already exists: {target}")
    tmp = dest / ".tmp-demon"
    if tmp.exists():
        shutil.rmtree(tmp, ignore_errors=True)
    try:
        result = sarai.extract_species(iso, tmp, data_dir="Demon", parm_key="demon",
                                       species="Demon", enemy_id=32, file_prefix="demon_",
                                       stride=3, windows={"attack1.bca": (10, 30)})
        target.mkdir(parents=True)
        (target / "demon.json").write_text(json.dumps(result, indent=2) + "\n",
                                           encoding="utf-8")
        pose_files = []
        for clip in result.get("clips", []):
            for pose in clip.get("poses", []):
                name = pose.get("file")
                if name and (tmp / name).is_file():
                    shutil.copyfile(tmp / name, target / name)
                    pose_files.append(name)
        for name in ("enemyparm.txt", "enemycoll.txt", "enemyanimmgr.txt"):
            if (tmp / name).is_file():
                shutil.copyfile(tmp / name, target / name)
        (target / "demon-provenance.json").write_text(json.dumps(
            {"derived_from": "experimental.pikmin2_sarai_assets.extract_species",
             "disc": {"model": "enemy/data/Demon/model.szs", "anim": "enemy/data/Demon/anim.szs",
                      "parms": "enemy/parm/enemyParms.szs:demon/enemyparm.txt"},
             "source_sha256": result.get("source_sha256", {}),
             "mouth_joints": ["rkamujnt", "lkamujnt"],
             "clips": [dict(file=c.get("file"), status=c.get("status"), poses=len(c.get("poses", [])))
                       for c in result.get("clips", [])],
             "pose_files": sorted(pose_files)}, indent=2) + "\n", encoding="utf-8")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return target


def extract_kogane(iso, dest, pose_limit=DEFAULT_POSE_LIMIT):
    """Build <dest>/Kogane/ via the existing kogane extractor plus a flat bank.

    ``pikmin2_kogane_assets.extract`` produces the source bank
    (``beetles.json`` + ``shared/*.mod`` sampled pose meshes); the Kogane
    host stager (``experimental.pikmin2_kogane_content.stage_kogane_host``)
    consumes ``beetles.json`` plus the pose meshes flattened next to it, so
    both are copied out of the temp tree. No poses or events are fabricated.
    """
    from experimental import pikmin2_kogane_assets as kogane

    iso, dest = Path(iso), Path(dest)
    if not iso.is_file():
        raise ValueError(f"ISO not found: {iso}")
    target = dest / "Kogane"
    if target.exists():
        raise ValueError(f"content dir already exists: {target}")
    tmp = dest / ".tmp-kogane"
    if tmp.exists():
        shutil.rmtree(tmp, ignore_errors=True)
    try:
        result = kogane.extract(iso, tmp, pose_limit=min(pose_limit, kogane.MAX_POSES))
        target.mkdir(parents=True)
        (target / "beetles.json").write_text(json.dumps(result, indent=2) + "\n",
                                             encoding="utf-8")
        for clip in result.get("shared", {}).get("clips", []):
            for pose in clip.get("poses", []):
                name = pose.get("file")
                if not name:
                    continue
                src = tmp / "shared" / name
                if src.is_file():
                    shutil.copyfile(src, target / name)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return target


def extract_kurage(iso, dest):
    """Build <dest>/Kurage/ via the kurage extractor (identity + manifest + poses).

    ``experimental.pikmin2_kurage_assets.extract`` writes ``identity.json`` (the
    family installer's pre-flight identity source), ``kurage.json`` (schema-1
    manifest naming each native loader file) and the sampled pose meshes the
    manifest hashes; ``experimental.pikmin2_kurage_content.stage_kurage_host``
    carries them into the run. Nothing is derived here beyond the extraction
    result.
    """
    from experimental import pikmin2_kurage_assets as kurage

    iso, dest = Path(iso), Path(dest)
    if not iso.is_file():
        raise ValueError(f"ISO not found: {iso}")
    target = dest / "Kurage"
    if target.exists():
        raise ValueError(f"content dir already exists: {target}")
    kurage.extract(iso, target)
    return target


def extract_onikurage(iso, dest):
    """Build <dest>/OniKurage/ via the onikurage extractor (identity + manifest + poses).

    Wave 3 flyers (#960): same layout as :func:`extract_kurage` for the Greater
    Spotted Jellyfloat (source 72); ``experimental.pikmin2_onikurage_content``
    carries the poses into the run.
    """
    from experimental import pikmin2_onikurage_assets as onikurage

    iso, dest = Path(iso), Path(dest)
    if not iso.is_file():
        raise ValueError(f"ISO not found: {iso}")
    target = dest / "OniKurage"
    if target.exists():
        raise ValueError(f"content dir already exists: {target}")
    onikurage.extract(iso, target)
    return target


def extract_minihoudai(iso, dest, pose_limit=None):
    """Build <dest>/MiniHoudai/ via the MiniHoudai extractor.

    ``pose_limit=None`` (the default, and what ``prepare_content_root`` uses)
    samples each clip per ``pikmin2_groink_stage.POSE_LIMITS`` so the native
    draw animates attack/walk/dead; an int forces a uniform limit.
    """
    from experimental import pikmin2_minihoudai_assets as minihoudai_assets

    iso, dest = Path(iso), Path(dest)
    if not iso.is_file():
        raise ValueError(f"ISO not found: {iso}")
    if pose_limit is not None and (type(pose_limit) is not int or not 2 <= pose_limit <= POSE_LIMIT_MAX):
        raise ValueError(f"pose limit must be 2..{POSE_LIMIT_MAX} or None: {pose_limit!r}")
    target = dest / "MiniHoudai"
    if target.exists():
        raise ValueError(f"content dir already exists: {target}")
    tmp = dest / ".tmp-minihoudai"
    if tmp.exists():
        shutil.rmtree(tmp, ignore_errors=True)
    try:
        minihoudai_assets.extract(iso, tmp, pose_limit=pose_limit)
        shutil.copytree(tmp, target)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return target


def extract_bombsarai(iso, dest, pose_limit=DEFAULT_POSE_LIMIT):
    """Build <dest>/BombSarai/ via the BombSarai extractor (#244 OWN).

    ``experimental.pikmin2_bombsarai_assets.extract`` writes ``bombsarai.json``
    (schema-1 ``P2_BOMBSARAI_IMPORT_1``) plus the ``BombSarai/`` carrier and
    ``Bomb/`` payload trees (retail parms, bca clips, sampled pose meshes); this
    wrapper adds the ``identity.json`` the family installer pre-flights. The
    BombSarai adapter stages what the native OWN port opens from this tree.
    """
    from experimental import pikmin2_bombsarai_assets as bombsarai_assets

    iso, dest = Path(iso), Path(dest)
    if not iso.is_file():
        raise ValueError(f"ISO not found: {iso}")
    target = dest / "BombSarai"
    if target.exists():
        raise ValueError(f"content dir already exists: {target}")
    tmp = dest / ".tmp-bombsarai"
    if tmp.exists():
        shutil.rmtree(tmp, ignore_errors=True)
    try:
        bombsarai_assets.extract(iso, tmp, pose_limit=min(pose_limit, bombsarai_assets.MAX_POSES))
        (tmp / "identity.json").write_text(
            json.dumps(dict(schema=1, source_id=58, enum_name="BombSarai"), indent=2) + "\n",
            encoding="utf-8")
        shutil.copytree(tmp, target)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return target


def extract_breadbug(iso, dest):
    """Build <dest>/PanModoki/ via the Breadbug OWN extractor (#898).

    Poses are sampled per clip (``pikmin2_breadbug_own_assets.POSE_LIMITS``
    plus every key-event frame), not by the global pose limit.
    """
    from experimental import pikmin2_breadbug_own_assets as breadbug

    iso, dest = Path(iso), Path(dest)
    if not iso.is_file():
        raise ValueError(f"ISO not found: {iso}")
    target = dest / "PanModoki"
    if target.exists():
        raise ValueError(f"content dir already exists: {target}")
    tmp = dest / ".tmp-breadbug"
    if tmp.exists():
        shutil.rmtree(tmp, ignore_errors=True)
    try:
        breadbug.extract(iso, tmp)
        shutil.copytree(tmp, target)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return target


def extract_sokkuri(iso, dest, pose_limit=6):
    """Build <dest>/Sokkuri/ via the Sokkuri extractor.

    ``pikmin2_sokkuri_assets.extract`` produces the source poses
    (``sokkuri.json`` + ``ginv_Sokkuri_<clip>_<ii>.mod``); the Sokkuri
    adapter stages the batch-2 ground files from that tree via
    ``experimental.pikmin2_sokkuri_content.stage_sokkuri_ground``.
    """
    from experimental import pikmin2_sokkuri_assets as sokkuri

    iso, dest = Path(iso), Path(dest)
    if not iso.is_file():
        raise ValueError(f"ISO not found: {iso}")
    if type(pose_limit) is not int or not 2 <= pose_limit <= POSE_LIMIT_MAX:
        raise ValueError(f"pose limit must be 2..{POSE_LIMIT_MAX}: {pose_limit!r}")
    target = dest / "Sokkuri"
    if target.exists():
        raise ValueError(f"content dir already exists: {target}")
    tmp = dest / ".tmp-sokkuri"
    if tmp.exists():
        shutil.rmtree(tmp, ignore_errors=True)
    try:
        sokkuri.extract(iso, tmp, pose_limit=pose_limit)
        shutil.copytree(tmp, target)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return target


def extract_catfish(iso, research, dest, pose_limit=6):
    """Build <dest>/Catfish/ via the aquatic extractor (full family import).

    ``pikmin2_aquatic_assets.extract`` produces the family import
    (``aquatic.json`` + per-species ``<Species>/`` pose banks); the shared-
    contract aquatic installer validates the whole four-species manifest on
    every install, so the full import tree is placed under ``<dest>/Catfish``.
    When Tadpole (27) is also wired it carries its own full copy under
    ``<dest>/Tadpole``; ``install_layout`` groups by family and installs once
    from the first binding's source.
    """
    from experimental import pikmin2_aquatic_assets as aquatic

    iso, dest = Path(iso), Path(dest)
    research = Path(research)
    if not iso.is_file():
        raise ValueError(f"ISO not found: {iso}")
    if not research.is_dir():
        raise ValueError(f"research checkout not found: {research}")
    if type(pose_limit) is not int or not 2 <= pose_limit <= POSE_LIMIT_MAX:
        raise ValueError(f"pose limit must be 2..{POSE_LIMIT_MAX}: {pose_limit!r}")
    target = dest / "Catfish"
    if target.exists():
        raise ValueError(f"content dir already exists: {target}")
    tmp = dest / ".tmp-catfish"
    if tmp.exists():
        shutil.rmtree(tmp, ignore_errors=True)
    try:
        aquatic.extract(iso, research, tmp, pose_limit=pose_limit)
        shutil.copytree(tmp, target)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return target


def extract_tadpole(iso, research, dest, pose_limit=6):
    """Build <dest>/Tadpole/ via the aquatic extractor (full family import)."""
    from experimental import pikmin2_aquatic_assets as aquatic

    iso, dest = Path(iso), Path(dest)
    research = Path(research)
    if not iso.is_file():
        raise ValueError(f"ISO not found: {iso}")
    if not research.is_dir():
        raise ValueError(f"research checkout not found: {research}")
    if type(pose_limit) is not int or not 2 <= pose_limit <= POSE_LIMIT_MAX:
        raise ValueError(f"pose limit must be 2..{POSE_LIMIT_MAX}: {pose_limit!r}")
    target = dest / "Tadpole"
    if target.exists():
        raise ValueError(f"content dir already exists: {target}")
    tmp = dest / ".tmp-tadpole"
    if tmp.exists():
        shutil.rmtree(tmp, ignore_errors=True)
    try:
        aquatic.extract(iso, research, tmp, pose_limit=pose_limit)
        shutil.copytree(tmp, target)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return target


def extract_hana(iso, research, dest, pose_limit=6):
    """Build <dest>/Hana/ via the ground-inverts extractor (full family import)."""
    from experimental import pikmin2_ground_inverts_assets as ground

    iso, dest = Path(iso), Path(dest)
    research = Path(research)
    if not iso.is_file():
        raise ValueError(f"ISO not found: {iso}")
    if not research.is_dir():
        raise ValueError(f"research checkout not found: {research}")
    if type(pose_limit) is not int or not 2 <= pose_limit <= POSE_LIMIT_MAX:
        raise ValueError(f"pose limit must be 2..{POSE_LIMIT_MAX}: {pose_limit!r}")
    target = dest / "Hana"
    if target.exists():
        raise ValueError(f"content dir already exists: {target}")
    tmp = dest / ".tmp-hana"
    if tmp.exists():
        shutil.rmtree(tmp, ignore_errors=True)
    try:
        ground.extract(iso, research, tmp, pose_limit=pose_limit)
        shutil.copytree(tmp, target)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return target


def extract_bombotakara(iso, source_repo, dest, pose_limit=6):
    """Build <dest>/BombOtakara/ via the dweevil extractor (full family import)."""
    from experimental import pikmin2_dweevil_assets as dweevil

    iso, dest = Path(iso), Path(dest)
    if not iso.is_file():
        raise ValueError(f"ISO not found: {iso}")
    if type(pose_limit) is not int or not 2 <= pose_limit <= POSE_LIMIT_MAX:
        raise ValueError(f"pose limit must be 2..{POSE_LIMIT_MAX}: {pose_limit!r}")
    target = dest / "BombOtakara"
    if target.exists():
        raise ValueError(f"content dir already exists: {target}")
    tmp = dest / ".tmp-bombotakara"
    if tmp.exists():
        shutil.rmtree(tmp, ignore_errors=True)
    try:
        dweevil.extract(iso, Path(source_repo), tmp, pose_limit=pose_limit)
        shutil.copytree(tmp, target)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return target


def extract_houdai(iso, dest):
    """Build <dest>/Houdai/ via the long-legs extractor (full family import)."""
    from experimental import pikmin2_long_legs_assets as longlegs

    iso, dest = Path(iso), Path(dest)
    if not iso.is_file():
        raise ValueError(f"ISO not found: {iso}")
    target = dest / "Houdai"
    if target.exists():
        raise ValueError(f"content dir already exists: {target}")
    tmp = dest / ".tmp-houdai"
    if tmp.exists():
        shutil.rmtree(tmp, ignore_errors=True)
    try:
        longlegs.extract(iso, tmp)
        shutil.copytree(tmp, target)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return target


def extract_bigtreasure(iso, research, dest, pose_limit=DEFAULT_POSE_LIMIT):
    """Build <dest>/BigTreasure/ via the BigTreasure import (#246 OWN).

    ``pikmin2_bigtreasure_assets.extract`` produces the disc import tree
    (``bigtreasure.json``, ``BigTreasure/`` model/clips/metadata/poses and
    ``pellets/``); an ``identity.json`` marks it as the source-73 identity.
    """
    from experimental import pikmin2_bigtreasure_assets as bigtreasure

    iso, dest = Path(iso), Path(dest)
    research = Path(research)
    if not iso.is_file():
        raise ValueError(f"ISO not found: {iso}")
    if not research.is_dir():
        raise ValueError(f"research checkout not found: {research}")
    if type(pose_limit) is not int or not 2 <= pose_limit <= POSE_LIMIT_MAX:
        raise ValueError(f"pose limit must be 2..{POSE_LIMIT_MAX}: {pose_limit!r}")
    pose_limit = min(pose_limit, bigtreasure.MAX_POSES)
    target = dest / "BigTreasure"
    if target.exists():
        raise ValueError(f"content dir already exists: {target}")
    tmp = dest / ".tmp-bigtreasure"
    if tmp.exists():
        shutil.rmtree(tmp, ignore_errors=True)
    try:
        bigtreasure.extract(iso, research, tmp, pose_limit=pose_limit)
        (tmp / "identity.json").write_text(
            json.dumps({"schema": 1, "source_id": 73, "enum_name": "BigTreasure"}, indent=2) + "\n",
            encoding="utf-8")
        shutil.copytree(tmp, target)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return target


def extract_fminihoudai(iso, research, dest, pose_limit=6):
    """Build <dest>/FminiHoudai/ via the cannon extractor (full family import)."""
    from experimental import pikmin2_cannon_projectile_assets as cannon

    iso, dest = Path(iso), Path(dest)
    research = Path(research)
    if not iso.is_file():
        raise ValueError(f"ISO not found: {iso}")
    if not research.is_dir():
        raise ValueError(f"research checkout not found: {research}")
    if type(pose_limit) is not int or not 2 <= pose_limit <= POSE_LIMIT_MAX:
        raise ValueError(f"pose limit must be 2..{POSE_LIMIT_MAX}: {pose_limit!r}")
    target = dest / "FminiHoudai"
    if target.exists():
        raise ValueError(f"content dir already exists: {target}")
    tmp = dest / ".tmp-fminihoudai"
    if tmp.exists():
        shutil.rmtree(tmp, ignore_errors=True)
    try:
        cannon.extract(iso, research, tmp, pose_limit=pose_limit)
        shutil.copytree(tmp, target)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return target


def extract_damagumo(iso, dest):
    """Build <dest>/Damagumo/ for the Long Legs adapter.

    Combines ``pikmin2_long_legs_assets.extract`` (66/69
    ``long-legs-family.json`` + owned meshes, kept whole so a grouped
    Damagumo+BigFoot layout still finds its base meshes) with
    ``pikmin2_damagumo_profile_convert.convert_profile`` over the Damagumo
    disc rows (56 ``damagumo-family.json`` + ``Demon/enemy.bmd``). The Long
    Legs adapter stages the configs plus the native bind shapes from this
    tree via ``pikmin2_long_legs_install`` + ``pikmin2_long_legs_visual``.
    """
    from experimental import pikmin2_long_legs_assets as long_legs
    from experimental import pikmin2_damagumo_profile_convert as damagumo_convert
    from experimental.pikmin2_assets import archive_files, disc_files

    iso, dest = Path(iso), Path(dest)
    if not iso.is_file():
        raise ValueError(f"ISO not found: {iso}")
    target = dest / "Damagumo"
    if target.exists():
        raise ValueError(f"content dir already exists: {target}")
    tmp = dest / ".tmp-damagumo"
    if tmp.exists():
        shutil.rmtree(tmp, ignore_errors=True)
    try:
        long_legs.extract(iso, tmp)
        # Damagumo disc rows (audit: enemy/data/{Damagumo,Houdai,BigFoot}).
        index = disc_files(iso)
        with iso.open("rb") as disc:
            def _read(path):
                try:
                    at, size = index[path]
                except KeyError:
                    raise ValueError(f"Disc entry missing: {path}") from None
                disc.seek(at)
                raw = disc.read(size)
                if len(raw) != size:
                    raise ValueError(f"Truncated disc entry: {path}")
                return raw
            model_szs = _read(damagumo_convert.DAMAGUMO_MODEL)
            anim_szs = _read(damagumo_convert.DAMAGUMO_ANIM)
        manifest, mesh, _slot = damagumo_convert.convert_profile(model_szs, anim_szs)
        (tmp / damagumo_convert.PROFILE_NAME).write_text(
            json.dumps(manifest, indent=1, sort_keys=True), encoding="utf-8")
        folder = tmp / damagumo_convert.FOLDER
        folder.mkdir(parents=True, exist_ok=True)
        (folder / damagumo_convert.MESH_NAME).write_bytes(mesh)
        shutil.copytree(tmp, target)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return target


def extract_bigfoot(iso, dest):
    """Build <dest>/BigFoot/ for the Long Legs adapter.

    Full family tree (66/69 manifest + owned meshes + 56 Damagumo manifest +
    Demon mesh), identical to the Damagumo tree, so a grouped Damagumo+BigFoot
    layout stages from either source. The adapter prunes the Demon files via
    a temp source when no Damagumo actor is staged (the shared installer
    refuses an unused Damagumo source mesh).
    """
    from experimental import pikmin2_long_legs_assets as long_legs
    from experimental import pikmin2_damagumo_profile_convert as damagumo_convert
    from experimental.pikmin2_assets import disc_files

    iso, dest = Path(iso), Path(dest)
    if not iso.is_file():
        raise ValueError(f"ISO not found: {iso}")
    target = dest / "BigFoot"
    if target.exists():
        raise ValueError(f"content dir already exists: {target}")
    tmp = dest / ".tmp-bigfoot"
    if tmp.exists():
        shutil.rmtree(tmp, ignore_errors=True)
    try:
        long_legs.extract(iso, tmp)
        index = disc_files(iso)
        with iso.open("rb") as disc:
            def _read(path):
                try:
                    at, size = index[path]
                except KeyError:
                    raise ValueError(f"Disc entry missing: {path}") from None
                disc.seek(at)
                raw = disc.read(size)
                if len(raw) != size:
                    raise ValueError(f"Truncated disc entry: {path}")
                return raw
            model_szs = _read(damagumo_convert.DAMAGUMO_MODEL)
            anim_szs = _read(damagumo_convert.DAMAGUMO_ANIM)
        manifest, mesh, _slot = damagumo_convert.convert_profile(model_szs, anim_szs)
        (tmp / damagumo_convert.PROFILE_NAME).write_text(
            json.dumps(manifest, indent=1, sort_keys=True), encoding="utf-8")
        folder = tmp / damagumo_convert.FOLDER
        folder.mkdir(parents=True, exist_ok=True)
        (folder / damagumo_convert.MESH_NAME).write_bytes(mesh)
        shutil.copytree(tmp, target)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return target


def extract_jigumo(iso, dest, research=None, pose_limit=6):
    """Build <dest>/Jigumo/ via the aquatic extractor (full family import).

    ``pikmin2_aquatic_assets.extract`` produces the 26/27/63/71
    ``aquatic.json`` + per-species pose banks; the whole tree is placed under
    ``<dest>/Jigumo/`` because the shared aquatic installer validates the
    whole four-species manifest per install (dweevil 59-62 precedent).
    """
    from experimental import pikmin2_aquatic_assets as aquatic

    iso, dest = Path(iso), Path(dest)
    if not iso.is_file():
        raise ValueError(f"ISO not found: {iso}")
    if type(pose_limit) is not int or not 2 <= pose_limit <= aquatic.MAX_POSES:
        raise ValueError(f"pose limit must be 2..{aquatic.MAX_POSES}: {pose_limit!r}")
    target = dest / "Jigumo"
    if target.exists():
        raise ValueError(f"content dir already exists: {target}")
    tmp = dest / ".tmp-jigumo"
    if tmp.exists():
        shutil.rmtree(tmp, ignore_errors=True)
    try:
        source = Path(research) if research is not None else DEFAULT_RESEARCH
        aquatic.extract(iso, source, tmp, pose_limit=pose_limit)
        shutil.copytree(tmp, target)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return target


def extract_snagret(iso, source_repo, dest, pose_limit=6):
    """Build <dest>/{SnakeCrow,SnakeWhole}/ via the shared snagret extractor.

    The shared-contract snagret installer validates the whole three-species
    ``snagret.json`` manifest on every install, so the full import tree is
    placed under each of the two worm-lane enum dirs (like the dweevil
    four-way copy). Actors staged per install are the single bound species.
    """
    from experimental import pikmin2_snagret_assets as snagret

    iso, dest = Path(iso), Path(dest)
    if not iso.is_file():
        raise ValueError(f"ISO not found: {iso}")
    if type(pose_limit) is not int or not 2 <= pose_limit <= POSE_LIMIT_MAX:
        raise ValueError(f"pose limit must be 2..{POSE_LIMIT_MAX}: {pose_limit!r}")
    enums = ["SnakeCrow", "SnakeWhole"]
    for enum_name in enums:
        if (dest / enum_name).exists():
            raise ValueError(f"content dir already exists: {dest / enum_name}")
    tmp = dest / ".tmp-snagret"
    if tmp.exists():
        shutil.rmtree(tmp, ignore_errors=True)
    try:
        snagret.extract(iso, Path(source_repo), tmp, pose_limit=pose_limit)
        for enum_name in enums:
            shutil.copytree(tmp, dest / enum_name)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return [dest / e for e in enums]


def extract_ground(iso, source_repo, dest, pose_limit=6):
    """Build <dest>/Imomushi/ via the shared ground-inverts extractor.

    The shared-contract ground installer validates the whole six-species
    ``ground_inverts.json`` manifest on every install, so the full import
    tree is placed under the Imomushi enum dir; actors staged per install
    are the single bound species.
    """
    from experimental import pikmin2_ground_inverts_assets as ground

    iso, dest = Path(iso), Path(dest)
    if not iso.is_file():
        raise ValueError(f"ISO not found: {iso}")
    if type(pose_limit) is not int or not 2 <= pose_limit <= POSE_LIMIT_MAX:
        raise ValueError(f"pose limit must be 2..{POSE_LIMIT_MAX}: {pose_limit!r}")
    target = dest / "Imomushi"
    if target.exists():
        raise ValueError(f"content dir already exists: {target}")
    tmp = dest / ".tmp-ground"
    if tmp.exists():
        shutil.rmtree(tmp, ignore_errors=True)
    try:
        ground.extract(iso, Path(source_repo), tmp, pose_limit=pose_limit)
        shutil.copytree(tmp, target)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return target


def extract_aquatic(iso, source_repo, dest, pose_limit=6):
    """Build <dest>/{UmiMushi,UmiMushiBlind}/ via the shared aquatic extractor.

    The shared-contract aquatic installer validates the whole four-species
    ``aquatic.json`` manifest on every install, so the full import tree is
    placed under each of the two worm-lane enum dirs. UmiMushiBlind reuses
    the UmiMushi bank as a visual stand-in (see aquatic_install
    UmiMushiBlind handling); actors staged per install keep the Blind
    species name for the native Blind path.
    """
    from experimental import pikmin2_aquatic_assets as aquatic

    iso, dest = Path(iso), Path(dest)
    if not iso.is_file():
        raise ValueError(f"ISO not found: {iso}")
    if type(pose_limit) is not int or not 2 <= pose_limit <= POSE_LIMIT_MAX:
        raise ValueError(f"pose limit must be 2..{POSE_LIMIT_MAX}: {pose_limit!r}")
    enums = ["UmiMushi", "UmiMushiBlind"]
    for enum_name in enums:
        if (dest / enum_name).exists():
            raise ValueError(f"content dir already exists: {dest / enum_name}")
    tmp = dest / ".tmp-aquatic"
    if tmp.exists():
        shutil.rmtree(tmp, ignore_errors=True)
    try:
        aquatic.extract(iso, Path(source_repo), tmp, pose_limit=pose_limit)
        for enum_name in enums:
            shutil.copytree(tmp, dest / enum_name)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return [dest / e for e in enums]


def extract_uji(iso, dest, pose_limit=4):
    """Build <dest>/{UjiA,UjiB,Tobi}/ via the shared Uji extractor.

    ``pikmin2_uji_assets.extract`` produces one source tree per Uji species
    (``uji.json`` + ``uji_<Species>_<clip>_<ii>.mod``); the Uji adapter stages
    the ``p2-uji-actors.txt`` / ``p2-uji-bank.txt`` sidecars from the bound
    species' trees via ``experimental.pikmin2_uji_content.stage_uji``. All
    three trees are staged together (one ISO read), mirroring ``extract_dweevil``;
    a ``wanted`` list mixing identity UjiA (12) with still-proxy UjiB/Tobi
    (13/14) collides fail-closed on the already-written species dir.
    """
    from experimental import pikmin2_uji_assets as uji

    iso, dest = Path(iso), Path(dest)
    if not iso.is_file():
        raise ValueError(f"ISO not found: {iso}")
    if type(pose_limit) is not int or not 2 <= pose_limit <= POSE_LIMIT_MAX:
        raise ValueError(f"pose limit must be 2..{POSE_LIMIT_MAX}: {pose_limit!r}")
    enums = ["UjiA", "UjiB", "Tobi"]
    for enum_name in enums:
        if (dest / enum_name).exists():
            raise ValueError(f"content dir already exists: {dest / enum_name}")
    tmp = dest / ".tmp-uji"
    if tmp.exists():
        shutil.rmtree(tmp, ignore_errors=True)
    try:
        uji.extract(iso, tmp, pose_limit=pose_limit)
        for enum_name in enums:
            shutil.copytree(tmp / enum_name, dest / enum_name)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return [dest / e for e in enums]


def extract_elecbug(iso, dest, pose_limit=6):
    """Build <dest>/ElecBug/ via the ElecBug extractor.

    ``pikmin2_elecbug_assets.extract`` produces the source poses
    (``elecbug.json`` + ``ginv_ElecBug_<clip>_<ii>.mod``); the ElecBug
    adapter stages its rows of the shared batch-2 ground files from that tree
    via ``experimental.pikmin2_elecbug_content.stage_elecbug_ground``.
    """
    from experimental import pikmin2_elecbug_assets as elecbug

    iso, dest = Path(iso), Path(dest)
    if not iso.is_file():
        raise ValueError(f"ISO not found: {iso}")
    if type(pose_limit) is not int or not 2 <= pose_limit <= POSE_LIMIT_MAX:
        raise ValueError(f"pose limit must be 2..{POSE_LIMIT_MAX}: {pose_limit!r}")
    target = dest / "ElecBug"
    if target.exists():
        raise ValueError(f"content dir already exists: {target}")
    tmp = dest / ".tmp-elecbug"
    if tmp.exists():
        shutil.rmtree(tmp, ignore_errors=True)
    try:
        elecbug.extract(iso, tmp, pose_limit=pose_limit)
        shutil.copytree(tmp, target)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return target


def extract_frog(iso, research, dest, pose_limit=6):
    """Build <dest>/Frog/ + <dest>/MaroFrog/ via the Frog extractor.

    ``pikmin2_frog_assets.extract`` produces the source bank
    (``frogs.json`` + ``Frog/`` + ``MaroFrog/`` pose meshes); the full bank is
    placed under both enum dirs because the shared-contract frog installer
    validates the whole two-species manifest per install (like the dweevil
    four-species bank). The Frog adapter stages ``p2-frog.txt`` from either
    tree via ``experimental.pikmin2_frog_install``.
    """
    from experimental import pikmin2_frog_assets as frog

    iso, research, dest = Path(iso), Path(research), Path(dest)
    if not iso.is_file():
        raise ValueError(f"ISO not found: {iso}")
    if not research.is_dir():
        raise ValueError(f"research checkout not found: {research}")
    if type(pose_limit) is not int or not 2 <= pose_limit <= POSE_LIMIT_MAX:
        raise ValueError(f"pose limit must be 2..{POSE_LIMIT_MAX}: {pose_limit!r}")
    for enum_name in ("Frog", "MaroFrog"):
        if (dest / enum_name).exists():
            raise ValueError(f"content dir already exists: {dest / enum_name}")
    tmp = dest / ".tmp-frog"
    if tmp.exists():
        shutil.rmtree(tmp, ignore_errors=True)
    try:
        frog.extract(iso, research, tmp, limit=pose_limit)
        for enum_name in ("Frog", "MaroFrog"):
            shutil.copytree(tmp, dest / enum_name)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return [dest / e for e in ("Frog", "MaroFrog")]


def extract_tank(iso, research, dest, pose_limit=3):
    """Build <dest>/Tank/ + <dest>/Wtank/ via the Tank extractor.

    ``pikmin2_tank_assets.extract`` produces the source bank (``tank.json`` +
    ``Tank/`` + ``Wtank/`` pose meshes); the full bank is placed under both
    enum dirs because the tank installer validates the whole two-species
    manifest per install (like frog/dweevil).
    """
    from experimental import pikmin2_tank_assets as tank

    iso, research, dest = Path(iso), Path(research), Path(dest)
    if not iso.is_file():
        raise ValueError(f"ISO not found: {iso}")
    if not research.is_dir():
        raise ValueError(f"research checkout not found: {research}")
    if type(pose_limit) is not int or not 2 <= pose_limit <= POSE_LIMIT_MAX:
        raise ValueError(f"pose limit must be 2..{POSE_LIMIT_MAX}: {pose_limit!r}")
    for enum_name in ("Tank", "Wtank"):
        if (dest / enum_name).exists():
            raise ValueError(f"content dir already exists: {dest / enum_name}")
    tmp = dest / ".tmp-tank"
    if tmp.exists():
        shutil.rmtree(tmp, ignore_errors=True)
    try:
        tank.extract(iso, tmp, research, pose_limit=pose_limit)
        for enum_name in ("Tank", "Wtank"):
            shutil.copytree(tmp, dest / enum_name)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return [dest / e for e in ("Tank", "Wtank")]


def extract_armor(iso, research, dest, pose_limit=6):
    """Build <dest>/Armor/ via the ground-invertebrate extractor."""
    from experimental import pikmin2_ground_inverts_assets as ground

    iso, research, dest = Path(iso), Path(research), Path(dest)
    if not iso.is_file():
        raise ValueError(f"ISO not found: {iso}")
    if not research.is_dir():
        raise ValueError(f"research checkout not found: {research}")
    target = dest / "Armor"
    if target.exists():
        raise ValueError(f"content dir already exists: {target}")
    tmp = dest / ".tmp-armor"
    if tmp.exists():
        shutil.rmtree(tmp, ignore_errors=True)
    try:
        ground.extract(iso, research, tmp, pose_limit=pose_limit)
        shutil.copytree(tmp, target)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return target


def extract_tamago(iso, dest, pose_limit=6):
    """Build <dest>/TamagoMushi/ via the TamagoMushi extractor.

    ``pikmin2_tamago_assets.extract`` produces the source poses
    (``tamagomushi.json`` + ``ginv_TamagoMushi_<clip>_<ii>.mod``); the
    TamagoMushi adapter stages its rows of the shared batch-2 ground files
    from that tree via
    ``experimental.pikmin2_tamago_content.stage_tamago_ground``.
    """
    from experimental import pikmin2_tamago_assets as tamago

    iso, dest = Path(iso), Path(dest)
    if not iso.is_file():
        raise ValueError(f"ISO not found: {iso}")
    if type(pose_limit) is not int or not 2 <= pose_limit <= POSE_LIMIT_MAX:
        raise ValueError(f"pose limit must be 2..{POSE_LIMIT_MAX}: {pose_limit!r}")
    target = dest / "TamagoMushi"
    if target.exists():
        raise ValueError(f"content dir already exists: {target}")
    tmp = dest / ".tmp-tamago"
    if tmp.exists():
        shutil.rmtree(tmp, ignore_errors=True)
    try:
        tamago.extract(iso, tmp, pose_limit=pose_limit)
        shutil.copytree(tmp, target)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return target


def extract_dangomushi(iso, dest, pose_limit=None):
    """Build <dest>/DangoMushi/ via the DangoMushi extractor.

    ``pikmin2_dangomushi_assets.extract`` produces the source poses
    (``dangomushi.json`` + ``snake_DangoMushi_<clip>_<ii>.mod``); the
    DangoMushi adapter stages its rows of the shared snagret files from that
    tree via ``experimental.pikmin2_dangomushi_content.stage_dangomushi``.
    ``pose_limit=None`` (what ``prepare_content_root`` uses) samples adaptive
    key poses up to ``ADAPTIVE_MAX_POSES`` per clip (#897); an int keeps the
    historical uniform sampling (2..8).
    """
    from experimental import pikmin2_dangomushi_assets as dangomushi

    iso, dest = Path(iso), Path(dest)
    if not iso.is_file():
        raise ValueError(f"ISO not found: {iso}")
    if pose_limit is not None and (type(pose_limit) is not int or not 2 <= pose_limit <= POSE_LIMIT_MAX):
        raise ValueError(f"pose limit must be 2..{POSE_LIMIT_MAX} or None: {pose_limit!r}")
    target = dest / "DangoMushi"
    if target.exists():
        raise ValueError(f"content dir already exists: {target}")
    tmp = dest / ".tmp-dangomushi"
    if tmp.exists():
        shutil.rmtree(tmp, ignore_errors=True)
    try:
        if pose_limit is None:
            dangomushi.extract(iso, tmp, pose_limit=dangomushi.ADAPTIVE_MAX_POSES,
                               sampling="adaptive")
        else:
            dangomushi.extract(iso, tmp, pose_limit=pose_limit)
        shutil.copytree(tmp, target)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return target


def extract_kabuto(iso, research, dest, pose_limit=6):
    """Build <dest>/Kabuto/ via the cannon-projectile extractor."""
    from experimental import pikmin2_cannon_projectile_assets as cannon

    iso, research, dest = Path(iso), Path(research), Path(dest)
    if not iso.is_file():
        raise ValueError(f"ISO not found: {iso}")
    if not research.is_dir():
        raise ValueError(f"research checkout not found: {research}")
    target = dest / "Kabuto"
    if target.exists():
        raise ValueError(f"content dir already exists: {target}")
    tmp = dest / ".tmp-kabuto"
    if tmp.exists():
        shutil.rmtree(tmp, ignore_errors=True)
    try:
        cannon.extract(iso, research, tmp, pose_limit=pose_limit)
        shutil.copytree(tmp, target)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return target


def extract_fuefuki(iso, dest, pose_limit=DEFAULT_POSE_LIMIT):
    """Build <dest>/Fuefuki/ via the Fuefuki extractor (#245 OWN).

    ``pikmin2_fuefuki_assets.extract`` writes the import directory (retail
    parms, animmgr, ten BCA clips, sampled poses) plus ``fuefuki.json``; both
    land in ``<dest>/Fuefuki`` with an ``identity.json`` (schema 1, 41,
    ``Fuefuki``) for the family pre-flight. ``pose_limit`` defaults to 12 per
    clip (the native bank allows 24) so the draw animates every clip.
    """
    from experimental import pikmin2_fuefuki_assets as fuefuki

    iso, dest = Path(iso), Path(dest)
    if not iso.is_file():
        raise ValueError(f"ISO not found: {iso}")
    if type(pose_limit) is not int or not 2 <= pose_limit <= POSE_LIMIT_MAX:
        raise ValueError(f"pose limit must be 2..{POSE_LIMIT_MAX}: {pose_limit!r}")
    pose_limit = min(pose_limit, fuefuki.MAX_POSES)
    target = dest / "Fuefuki"
    if target.exists():
        raise ValueError(f"content dir already exists: {target}")
    tmp = dest / ".tmp-fuefuki"
    if tmp.exists():
        shutil.rmtree(tmp, ignore_errors=True)
    try:
        fuefuki.extract(iso, tmp, pose_limit=pose_limit)
        shutil.copytree(tmp / fuefuki.ENEMY, target)
        shutil.copy2(tmp / "fuefuki.json", target / "fuefuki.json")
        (target / "identity.json").write_text(
            json.dumps(dict(schema=1, source_id=41, enum_name="Fuefuki"), indent=2) + "\n",
            encoding="utf-8")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return target


def extract_proxy(iso, dest, source_id, pose_limit=None):
    """Build <dest>/<Enum>/ for one proxy species via the generic extractor.

    ``pikmin2_proxy_assets.extract`` produces the source poses (``proxy.json``
    + ``px_<Enum>_<clip>_<ii>.mod``); the proxy adapter stages the
    campaign/actors/bank sidecars plus the pose files from that tree via
    ``experimental.pikmin2_proxy_content.stage_proxy``. The species (enum
    name, host vehicle, pose default) comes from ``randomizer/p2_proxy/``:
    a ``None`` pose limit takes the declaration's ``pose_limit`` so editing
    the row JSON changes the extraction.
    """
    from experimental import pikmin2_proxy_assets as proxy

    iso, dest = Path(iso), Path(dest)
    if not iso.is_file():
        raise ValueError(f"ISO not found: {iso}")
    if type(source_id) is not int or isinstance(source_id, bool):
        raise ValueError(f"proxy source id must be an int: {source_id!r}")
    from randomizer.p2_proxy import load_rows
    declared = {row["source_id"]: row for row in load_rows()}
    if pose_limit is None:
        if source_id not in declared:
            raise ValueError(f"source id {source_id!r} is not a declared proxy species")
        pose_limit = declared[source_id]["pose_limit"]
    if type(pose_limit) is not int or not 2 <= pose_limit <= POSE_LIMIT_MAX:
        raise ValueError(f"pose limit must be 2..{POSE_LIMIT_MAX}: {pose_limit!r}")
    enum_name = ENUM_FOR_SOURCE.get(source_id)
    if enum_name is None:
        raise ValueError(f"unknown enum name for source id {source_id!r}")
    if source_id not in declared or declared[source_id]["enum_name"] != enum_name:
        raise ValueError(f"source id {source_id!r} is not a declared proxy species")
    target = dest / enum_name
    if target.exists():
        raise ValueError(f"content dir already exists: {target}")
    tmp = dest / f".tmp-proxy-{source_id}"
    if tmp.exists():
        shutil.rmtree(tmp, ignore_errors=True)
    try:
        # The declaration row travels with the call: override species
        # (asset_dir/param_dir/clips/param_files/missing_normals) extract
        # from the wrong disc paths without it.
        proxy.extract(iso, enum_name, source_id, tmp, pose_limit=pose_limit,
                      row=declared[source_id])
        shutil.copytree(tmp, target)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return target


def extract_chappy(iso, dest, source_id, pose_limit=None):
    """Build <dest>/<Enum>/ for one Chappy-family species via its extractor.

    ``pikmin2_chappy_assets.extract`` produces the source poses
    (``proxy.json`` + ``px_<Enum>_<clip>_<ii>.mod``, byte-identical to the
    retired proxy extraction); the Chappy adapter stages the identity
    actors/bank sidecars plus the pose files from that tree via
    ``experimental.pikmin2_chappy_content.stage_chappy``. A ``None`` pose
    limit takes the family row's ``pose_limit``.
    """
    from experimental import pikmin2_chappy_assets as chappy

    iso, dest = Path(iso), Path(dest)
    if not iso.is_file():
        raise ValueError(f"ISO not found: {iso}")
    if type(source_id) is not int or isinstance(source_id, bool):
        raise ValueError(f"chappy source id must be an int: {source_id!r}")
    if source_id not in chappy.CHAPPY_ROWS:
        raise ValueError(f"source id {source_id!r} is not a Chappy-family species")
    enum_name = ENUM_FOR_SOURCE.get(source_id)
    if enum_name != chappy.CHAPPY_ROWS[source_id]["enum_name"]:
        raise ValueError(f"unknown enum name for source id {source_id!r}")
    target = dest / enum_name
    if target.exists():
        raise ValueError(f"content dir already exists: {target}")
    tmp = dest / f".tmp-chappy-{source_id}"
    if tmp.exists():
        shutil.rmtree(tmp, ignore_errors=True)
    try:
        chappy.extract(iso, enum_name, source_id, tmp, pose_limit=pose_limit)
        shutil.copytree(tmp, target)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return target


EXTRACTORS = {
    2: "extract_chappy",
    73: "extract_bigtreasure",
    33: "extract_chappy",
    35: "extract_chappy",
    43: "extract_chappy",
    53: "extract_chappy",
    67: "extract_chappy",
    76: "extract_chappy",
    44: "extract_bluekochappy",
    54: "extract_miulin",
    59: "extract_dweevil",
    60: "extract_dweevil",
    61: "extract_dweevil",
    62: "extract_dweevil",
    23: "extract_sarai",
    32: "extract_demon",
    9: "extract_kogane",
    17: "extract_frog",
    18: "extract_frog",
    24: "extract_tank",
    25: "extract_tank",
    15: "extract_armor",
    75: "extract_kabuto",
    57: "extract_kurage",
    72: "extract_onikurage",
    78: "extract_minihoudai",
    38: "extract_breadbug",
    79: "extract_sokkuri",
    26: "extract_catfish",
    27: "extract_tadpole",
    84: "extract_hana",
    93: "extract_bombotakara",
    66: "extract_houdai",
    97: "extract_fminihoudai",
    58: "extract_bombsarai",
    12: "extract_uji",
    13: "extract_uji",
    14: "extract_uji",
    28: "extract_elecbug",
    68: "extract_tamago",
    94: "extract_dangomushi",
    56: "extract_damagumo",
    63: "extract_jigumo",
    69: "extract_bigfoot",
    34: "extract_snagret",
    70: "extract_snagret",
    65: "extract_ground",
    71: "extract_aquatic",
    101: "extract_aquatic",
    41: "extract_fuefuki",
}
for _row in _PROXY_ROWS:
    # An own-identity extractor (e.g. Chappy) wins over the generic proxy
    # path; a proxy row and an identity row must never coexist, so a
    # surviving proxy declaration for an EXTRACTORS id is a fail-closed
    # import error via IDENTITY_FAMILY, not a silent overwrite here.
    EXTRACTORS.setdefault(_row["source_id"], "extract_proxy")
del _row


def prepare_content_root(iso, out, research=None, pose_limit=DEFAULT_POSE_LIMIT, wanted=None,
                         proxy_pose_limit=None, legacy_pose_limit=None):
    """Extract the identity-keyed content root for the wanted source ids.

    ``pose_limit`` applies to every non-proxy family bank (#895: default
    DEFAULT_POSE_LIMIT poses per clip, cap POSE_LIMIT_MAX). Every native
    pose-bank loader, including the dedicated Blue Kochappy, Miulin, Frog,
    Tank and Kabuto loaders, now goes through pc_p2_pose_loader.h (a few full
    Shapes per clip plus decoded vectors), so there is no sparser legacy
    tier. ``legacy_pose_limit`` is kept only as an explicit override for those
    five families (``None`` = ``pose_limit``). Proxy species use
    ``proxy_pose_limit`` when given, otherwise each row's own ``pose_limit``
    (``extract_proxy`` with ``pose_limit=None`` takes the declaration), so a
    product run without an explicit ``--pose-limit`` stages what the rows
    declare instead of silently sampling 3 poses/clip.
    """
    iso = Path(iso)
    out = Path(out)
    if not iso.is_file():
        raise ValueError(f"ISO not found: {iso}")
    if type(pose_limit) is not int or not 2 <= pose_limit <= POSE_LIMIT_MAX:
        raise ValueError(f"pose limit must be 2..{POSE_LIMIT_MAX}: {pose_limit!r}")
    if proxy_pose_limit is not None and (
            type(proxy_pose_limit) is not int or not 2 <= proxy_pose_limit <= POSE_LIMIT_MAX):
        raise ValueError(f"proxy pose limit must be 2..{POSE_LIMIT_MAX}: {proxy_pose_limit!r}")
    if legacy_pose_limit is None:
        legacy_pose_limit = pose_limit
    if type(legacy_pose_limit) is not int or not 2 <= legacy_pose_limit <= POSE_LIMIT_MAX:
        raise ValueError(f"legacy pose limit must be 2..{POSE_LIMIT_MAX}: {legacy_pose_limit!r}")
    if wanted is None:
        wanted = admitted_source_ids()
    wanted = order_source_ids(wanted)
    supported, unsupported = split_supported(wanted)
    if out.exists() and any(out.iterdir()):
        raise ValueError(f"output dir already exists and is not empty: {out}")
    out.mkdir(parents=True, exist_ok=True)
    research = Path(research) if research is not None else DEFAULT_RESEARCH
    extracted = []
    no_extractor = []
    dweevil_done = False
    uji_done = False
    frog_done = False
    tank_done = False
    snagret_done = False
    aquatic_done = False
    for source_id in supported:
        if source_id == 44:
            extract_bluekochappy(iso, research, out, pose_limit=legacy_pose_limit)
            extracted.append(source_id)
        elif source_id == 54:
            extract_miulin(iso, out, pose_limit=legacy_pose_limit)
            extracted.append(source_id)
        elif source_id in (59, 60, 61, 62):
            if not dweevil_done:
                extract_dweevil(iso, ROOT, out, pose_limit=pose_limit)
                dweevil_done = True
            extracted.append(source_id)
        elif source_id == 23:
            extract_sarai(iso, out)
            extracted.append(source_id)
        elif source_id == 32:
            extract_demon(iso, out)
            extracted.append(source_id)
        elif source_id == 57:
            extract_kurage(iso, out)
            extracted.append(source_id)
        elif source_id == 72:
            extract_onikurage(iso, out)
            extracted.append(source_id)
        elif source_id == 9:
            extract_kogane(iso, out, pose_limit=pose_limit)
            extracted.append(source_id)
        elif source_id == 78:
            # Per-clip pose limits (native Groink bank), not the global limit.
            extract_minihoudai(iso, out)
            extracted.append(source_id)
        elif source_id == 38:
            # Per-clip pose limits (native Breadbug bank), not the global limit.
            extract_breadbug(iso, out)
            extracted.append(source_id)
        elif source_id == 79:
            extract_sokkuri(iso, out, pose_limit=pose_limit)
            extracted.append(source_id)
        elif source_id == 26:
            extract_catfish(iso, research, out, pose_limit=pose_limit)
            extracted.append(source_id)
        elif source_id == 27:
            extract_tadpole(iso, research, out, pose_limit=pose_limit)
            extracted.append(source_id)
        elif source_id == 84:
            extract_hana(iso, research, out, pose_limit=pose_limit)
            extracted.append(source_id)
        elif source_id == 93:
            extract_bombotakara(iso, ROOT, out, pose_limit=pose_limit)
            extracted.append(source_id)
        elif source_id == 66:
            extract_houdai(iso, out)
            extracted.append(source_id)
        elif source_id == 97:
            extract_fminihoudai(iso, research, out, pose_limit=pose_limit)
            extracted.append(source_id)
        elif source_id == 58:
            # Per-clip pose bank for the native OWN draw, not the global limit.
            extract_bombsarai(iso, out, pose_limit=pose_limit)
            extracted.append(source_id)
        elif source_id == 41:
            # Per-clip pose bank for the native draw, not the global limit.
            extract_fuefuki(iso, out, pose_limit=pose_limit)
            extracted.append(source_id)
        elif source_id == 73:
            extract_bigtreasure(iso, research, out, pose_limit=pose_limit)
            extracted.append(source_id)
        elif source_id in (34, 70):
            if not snagret_done:
                extract_snagret(iso, ROOT, out, pose_limit=pose_limit)
                snagret_done = True
            extracted.append(source_id)
        elif source_id == 65:
            extract_ground(iso, ROOT, out, pose_limit=pose_limit)
            extracted.append(source_id)
        elif source_id in (71, 101):
            if not aquatic_done:
                extract_aquatic(iso, ROOT, out, pose_limit=pose_limit)
                aquatic_done = True
            extracted.append(source_id)
        elif source_id == 56:
            extract_damagumo(iso, out)
            extracted.append(source_id)
        elif source_id == 63:
            extract_jigumo(iso, out, research=research, pose_limit=pose_limit)
            extracted.append(source_id)
        elif source_id == 69:
            extract_bigfoot(iso, out)
            extracted.append(source_id)
        elif source_id == 2:
            extract_chappy(iso, out, source_id, pose_limit=proxy_pose_limit)
            extracted.append(source_id)
        elif source_id == 33:
            extract_chappy(iso, out, source_id, pose_limit=proxy_pose_limit)
            extracted.append(source_id)
        elif source_id == 35:
            extract_chappy(iso, out, source_id, pose_limit=proxy_pose_limit)
            extracted.append(source_id)
        elif source_id == 43:
            extract_chappy(iso, out, source_id, pose_limit=proxy_pose_limit)
            extracted.append(source_id)
        elif source_id == 53:
            extract_chappy(iso, out, source_id, pose_limit=proxy_pose_limit)
            extracted.append(source_id)
        elif source_id == 67:
            extract_chappy(iso, out, source_id, pose_limit=proxy_pose_limit)
            extracted.append(source_id)
        elif source_id == 76:
            extract_chappy(iso, out, source_id, pose_limit=proxy_pose_limit)
            extracted.append(source_id)
        elif source_id == 28:
            extract_elecbug(iso, out, pose_limit=pose_limit)
            extracted.append(source_id)
        elif source_id == 68:
            extract_tamago(iso, out, pose_limit=pose_limit)
            extracted.append(source_id)
        elif source_id == 94:
            # #897: the boss draws from adaptive key poses (its own cap), not
            # the global uniform pose limit (like 78's POSE_LIMITS).
            extract_dangomushi(iso, out, pose_limit=None)
            extracted.append(source_id)
        elif source_id == 12:
            if not uji_done:
                extract_uji(iso, out, pose_limit=pose_limit)
                uji_done = True
            extracted.append(source_id)
        elif source_id == 13:
            if not uji_done:
                extract_uji(iso, out, pose_limit=pose_limit)
                uji_done = True
            extracted.append(source_id)
        elif source_id == 14:
            if not uji_done:
                extract_uji(iso, out, pose_limit=pose_limit)
                uji_done = True
            extracted.append(source_id)
        elif source_id == 17:
            if not frog_done:
                extract_frog(iso, research, out, pose_limit=max(legacy_pose_limit, 6))
                frog_done = True
            extracted.append(source_id)
        elif source_id == 18:
            if not frog_done:
                extract_frog(iso, research, out, pose_limit=max(legacy_pose_limit, 6))
                frog_done = True
            extracted.append(source_id)
        elif source_id == 24:
            if not tank_done:
                extract_tank(iso, research, out, pose_limit=legacy_pose_limit)
                tank_done = True
            extracted.append(source_id)
        elif source_id == 25:
            if not tank_done:
                extract_tank(iso, research, out, pose_limit=legacy_pose_limit)
                tank_done = True
            extracted.append(source_id)
        elif source_id == 15:
            extract_armor(iso, research, out, pose_limit=pose_limit)
            extracted.append(source_id)
        elif source_id == 75:
            extract_kabuto(iso, research, out, pose_limit=legacy_pose_limit)
            extracted.append(source_id)
        elif source_id in PROXY_SOURCE_IDS:
            extract_proxy(iso, out, source_id, pose_limit=proxy_pose_limit)
            extracted.append(source_id)
        else:
            # Supported by the family map but with no extractor wired here
            # (e.g. Kochappy 1 / Snow 45): report, don't invent.
            if source_id not in unsupported:
                no_extractor.append(source_id)
    # Two distinct causes, and conflating them sends people to the wrong file:
    # no installer means IDENTITY_FAMILY cannot lay the content down; no
    # extractor means the installer exists but nothing produces what it installs.
    skipped = [{"source_id": i,
                "enum_name": ENUM_FOR_SOURCE.get(i),
                "reason": "no family installer; staged through no shared-contract path"}
               for i in unsupported]
    skipped += [{"source_id": i,
                 "enum_name": ENUM_FOR_SOURCE.get(i),
                 "reason": "family installer exists but no ISO extractor is wired "
                           "here; add one to EXTRACTORS before this species can "
                           "be staged"}
                for i in no_extractor]
    skipped.sort(key=lambda row: row["source_id"])
    # Keep extractor-wired-but-unrequested ids out of the skipped list noise.
    summary = {"iso": str(iso),
               "out": str(out),
               "playable": list(PLAYABLE_SOURCE_IDS),
               "extracted": sorted(extracted),
               "extracted_enums": sorted(ENUM_FOR_SOURCE[i] for i in extracted),
               "pose_limit": pose_limit,
               "proxy_pose_limit": proxy_pose_limit,
               "legacy_pose_limit": legacy_pose_limit,
               "skipped": skipped}
    (out / "prepared.json").write_text(json.dumps(summary, indent=2) + "\n",
                                       encoding="utf-8")
    return summary


def actor_bindings_for_manifest(manifest):
    """Return the {target: generator_id} actor bindings for a seed manifest.

    Derivation (documented, deterministic): ``generator_id = int(target)``.
    Binding targets are slot-uid tokens (``docs/PIKMIN2_ADMITTED_PLACEMENT.json``
    via ``randomizer/p2_placement_catalog.py``); they are unique per binding and
    fit in uint32, so the uid value itself is a bijective generator assignment
    giving every family sidecar distinct generator ids.
    """
    if not isinstance(manifest, dict):
        raise ValueError("seed manifest must be a JSON object")
    layout = manifest.get("p2_layout")
    if not isinstance(layout, dict) or not layout.get("bindings"):
        raise ValueError("seed manifest has no p2_layout bindings "
                         "(generate with --p2-enemies)")
    bindings = {}
    for binding in layout["bindings"]:
        target = binding.get("target")
        if not isinstance(target, str) or not TARGET_RE.fullmatch(target):
            raise ValueError(f"invalid binding target: {target!r}")
        try:
            generator = int(target)
        except ValueError:
            raise ValueError(f"binding target is not a numeric slot uid: {target!r}")
        if not 0 <= generator <= 0xFFFFFFFF:
            raise ValueError(f"generator id out of uint32 range: {target!r}")
        if target in bindings and bindings[target] != generator:
            raise ValueError(f"duplicate binding target: {target!r}")
        bindings[target] = generator
    if len(set(bindings.values())) != len(bindings):
        raise ValueError("derived generator ids are not unique")
    return bindings


def actors_for_manifest_file(manifest_path, actors_out):
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    bindings = actor_bindings_for_manifest(manifest)
    actors_out = Path(actors_out)
    actors_out.parent.mkdir(parents=True, exist_ok=True)
    actors_out.write_text(json.dumps(bindings, indent=2, sort_keys=True) + "\n",
                          encoding="utf-8")
    return bindings


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--iso", type=Path, required=True,
                        help="P2 retail ISO (e.g. 'PIKMIN2 for GAMECUBE.iso')")
    parser.add_argument("--out", type=Path, required=True,
                        help="identity-keyed content root to build (<out>/<enum_name>/...)")
    parser.add_argument("--seed-manifest", type=Path, default=None,
                        help="seed manifest JSON; with --actors-out writes {target: generator_id}")
    parser.add_argument("--actors-out", type=Path, default=None,
                        help="output JSON for the actor bindings")
    parser.add_argument("--research", type=Path, default=None,
                        help="native/pikmin2-research checkout (default: %(default)s)")
    parser.add_argument("--pose-limit", type=int, default=None,
                        help="sampled poses per clip for the compact-loader family banks "
                             f"(default {DEFAULT_POSE_LIMIT}, max {POSE_LIMIT_MAX}; proxy and Chappy "
                             "species use their row pose_limit unless this flag is given explicitly)")
    parser.add_argument("--legacy-pose-limit", type=int, default=None,
                        help="optional override of the poses per clip for Blue Kochappy, Miulin, Frog, "
                             "Tank and Kabuto (default: the --pose-limit value; their native loaders "
                             "are on the compact loader since #895)")
    parser.add_argument("--species", default=None,
                        help="'playable', 'admitted', or comma-separated source ids "
                             "(default: admitted)")
    args = parser.parse_args(argv)

    if (args.seed_manifest is None) != (args.actors_out is None):
        parser.error("--seed-manifest and --actors-out must be given together")
    if args.pose_limit is not None and not 2 <= args.pose_limit <= POSE_LIMIT_MAX:
        parser.error(f"--pose-limit must be 2..{POSE_LIMIT_MAX}")
    if args.legacy_pose_limit is not None and not 2 <= args.legacy_pose_limit <= POSE_LIMIT_MAX:
        parser.error(f"--legacy-pose-limit must be 2..{POSE_LIMIT_MAX}")

    if args.species is None or args.species == "admitted":
        wanted = admitted_source_ids()
    elif args.species == "playable":
        wanted = list(PLAYABLE_SOURCE_IDS)
    else:
        try:
            wanted = [int(x) for x in args.species.split(",") if x.strip()]
        except ValueError:
            parser.error("--species must be 'playable', 'admitted' or comma-separated ints")
        if not wanted or any(type(i) is not int for i in wanted):
            parser.error("--species must be a nonempty list of source ids")

    if args.seed_manifest is not None:
        # The manifest's proxy bindings join the extraction set so no manual
        # extract_proxy call is needed. Proxy species sample their row
        # pose_limit unless --pose-limit was given explicitly.
        # Manifests without proxy bindings add nothing: the default
        # extraction list is unchanged byte-for-byte.
        for source_id in proxy_ids_for_manifest(args.seed_manifest):
            if source_id not in wanted:
                wanted.append(source_id)

    summary = prepare_content_root(args.iso, args.out,
                                   research=args.research,
                                   pose_limit=DEFAULT_POSE_LIMIT if args.pose_limit is None else args.pose_limit,
                                   legacy_pose_limit=args.legacy_pose_limit,
                                   proxy_pose_limit=args.pose_limit,
                                   wanted=wanted)
    print(json.dumps(summary, indent=2))
    if args.seed_manifest is not None:
        bindings = actors_for_manifest_file(args.seed_manifest, args.actors_out)
        print(f"wrote {len(bindings)} actor bindings to {args.actors_out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
