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
* 9 Kogane: ``pikmin2_kogane_assets.extract`` -> ``<out>/Kogane/``
  (``beetles.json`` plus the pose meshes flattened beside it); the Kogane
  adapter stages the room meshes through ``pikmin2_kogane_content``.
* 57 Kurage: ``pikmin2_kurage_assets.extract`` -> ``<out>/Kurage/``; the Kurage
  adapter stages the visual files through ``pikmin2_kurage_content``.
* 79 Sokkuri: ``pikmin2_sokkuri_assets.extract`` -> ``<out>/Sokkuri/``
  (``sokkuri.json`` + ``ginv_Sokkuri_<clip>_<ii>.mod``); the Sokkuri adapter
  stages the batch-2 ground files through ``pikmin2_sokkuri_content``. A legacy
  ``ground_inverts.json`` import dir still stages through the shared ground
  installer unchanged.

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

PLAYABLE_SOURCE_IDS = (44, 54, 59, 60, 61, 62)

ENUM_FOR_SOURCE = {
    1: "Kochappy",
    9: "Kogane",
    23: "Sarai",
    44: "BlueKochappy",
    45: "YellowKochappy",
    54: "Miulin",
    57: "Kurage",
    58: "BombSarai",
    59: "FireOtakara",
    60: "WaterOtakara",
    61: "GasOtakara",
    62: "ElecOtakara",
    78: "MiniHoudai",
    79: "Sokkuri",
}

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


def extract_kogane(iso, dest):
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
        result = kogane.extract(iso, tmp)
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
    if type(pose_limit) is not int or not 2 <= pose_limit <= 8:
        raise ValueError(f"pose limit must be 2..8: {pose_limit!r}")
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


EXTRACTORS = {
    44: "extract_bluekochappy",
    54: "extract_miulin",
    59: "extract_dweevil",
    60: "extract_dweevil",
    61: "extract_dweevil",
    62: "extract_dweevil",
    23: "extract_sarai",
    9: "extract_kogane",
    57: "extract_kurage",
    79: "extract_sokkuri",
}


def prepare_content_root(iso, out, research=None, pose_limit=3, wanted=None):
    """Extract the identity-keyed content root for the wanted source ids."""
    iso = Path(iso)
    out = Path(out)
    if not iso.is_file():
        raise ValueError(f"ISO not found: {iso}")
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
    for source_id in supported:
        if source_id == 44:
            extract_bluekochappy(iso, research, out, pose_limit=pose_limit)
            extracted.append(source_id)
        elif source_id == 54:
            extract_miulin(iso, out, pose_limit=pose_limit)
            extracted.append(source_id)
        elif source_id in (59, 60, 61, 62):
            if not dweevil_done:
                extract_dweevil(iso, ROOT, out, pose_limit=pose_limit)
                dweevil_done = True
            extracted.append(source_id)
        elif source_id == 23:
            extract_sarai(iso, out)
            extracted.append(source_id)
        elif source_id == 57:
            extract_kurage(iso, out)
            extracted.append(source_id)
        elif source_id == 9:
            extract_kogane(iso, out)
            extracted.append(source_id)
        elif source_id == 79:
            extract_sokkuri(iso, out, pose_limit=pose_limit)
            extracted.append(source_id)
        else:
            # Supported by the family map but with no extractor wired here
            # (e.g. Kochappy 1 / Snow 45 / BombSarai 58): report, don't invent.
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
    parser.add_argument("--pose-limit", type=int, default=3,
                        help="sampled poses per clip for mamuta/dweevil/dwarf banks (default 3)")
    parser.add_argument("--species", default=None,
                        help="'playable', 'admitted', or comma-separated source ids "
                             "(default: admitted)")
    args = parser.parse_args(argv)

    if (args.seed_manifest is None) != (args.actors_out is None):
        parser.error("--seed-manifest and --actors-out must be given together")
    if not 2 <= args.pose_limit <= 8:
        parser.error("--pose-limit must be 2..8")

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

    summary = prepare_content_root(args.iso, args.out,
                                   research=args.research,
                                   pose_limit=args.pose_limit,
                                   wanted=wanted)
    print(json.dumps(summary, indent=2))
    if args.seed_manifest is not None:
        bindings = actors_for_manifest_file(args.seed_manifest, args.actors_out)
        print(f"wrote {len(bindings)} actor bindings to {args.actors_out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
