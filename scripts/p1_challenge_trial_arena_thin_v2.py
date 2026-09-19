"""Trial-arena sprout-thinning feasibility gate for P1 Challenge Trial chal4 (#792).

Executes #770 Option A (thin buried sprouts so the birth-cap total stays under
the pikiheadItem.cpp:143 cap) as a BOUNDED root-only slice. Consumes the
blocked #567 driver, the landed #649 guarded fixture and the #741
INITSTAGE-CREATE-FINALSETUP order fix READ-ONLY; owns no native/shared files
and performs no engine change.

Reality recorded by this gate (fail-closed): the retail chal4 buried sprouts
come from binary `GenObjectPiki` records inside the staged `default.gen` /
`plants.gen` (native generator.cpp:1173 births a PikiHeadItem for spawn
state 0, and pikiheadItem.cpp:143 increments mePikis into the birth cap).
No repository utility parses or rewrites the retail `.gen` binary format, and
the canonical challenge inputs builder stages those gens verbatim with sha256
pins. Therefore a correct, divergence-safe thinning cannot be produced from
inside the three owned root files: it needs a generator/placement-provider
gen rewriter or a native staging hook (owner route), exactly the brief's
fallback. This module proves that and emits the exact blocker instead of
fabricating a thinned arena.

Engine-free, hermetic, fail-closed. No runtime world boot, no ADMIT.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import sys
from pathlib import Path

SCHEMA = "p1-challenge-trial-arena-thin-v2-1"
ISSUE = 792
STAGE = "chal4"
CAP_ME_PIKIS = 100
SQUAD_TARGET = 20
RETAIL_GENS = ("default.gen", "plants.gen")
DRIVER_REL = ("output/workflow/autofill/planning-shards/p1-challenge/prepared/"
              "p1-challenge-trial-runtime-acceptance-root/scripts/"
              "p1_challenge_trial_runtime_acceptance.py")
THIN_TOOL_REL = ("output/workflow/autofill/prerequisites/trial-arena-gen-thinning-tool-root/"
                   "scripts/p1_challenge_gen_record_thinner.py")
THIN_TOOL_COMMIT = "72149cbea61d5dbb203ba84825369a5836c5b46a"
OWNER_B = ("#770 owner B: engine counting fix (pikiheadItem.cpp:143 and/or "
           "pikiMgr birth arm) with #186 review + #52 campaign contract")
OWNER_PROVIDER = ("generator/placement provider (binary .gen rewriter) or a "
                  "native staging hook, outside this lane's three owned files")
CAP_SOURCE = "src/plugPikiKando/pikiheadItem.cpp:143 (mePikis inc) -> gameStat.cpp:70 -> PikiMgr::birth cap"
BIRTH_SOURCE = "src/plugPikiKando/generator.cpp:1173 (spawn state 0 -> PikiHeadItem)"


class ThinError(ValueError):
    """Fail-closed refusal: unreadable input or unsafe thinning request."""


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def classify_gen_bytes(data):
    """Classify staged generator bytes; unknown formats are never rewritten."""
    if not data:
        raise ThinError("empty-generator-bytes")
    if b"\x00" in data:
        return "retail-binary"
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return "retail-binary"
    if re.fullmatch(r"\s*", text):
        return "retail-binary"
    return "text-unknown"


def thinning_plan(gen_bytes, cap=CAP_ME_PIKIS, observed_me=None, squad=SQUAD_TARGET):
    """Feasibility plan for thinning; never invents a rewritable format."""
    kind = classify_gen_bytes(gen_bytes)
    me = cap if observed_me is None else int(observed_me)
    headroom = cap - me
    required = max(0, squad - headroom)
    plan = {
        "format": kind,
        "cap": int(cap),
        "observed_me": me,
        "headroom": headroom,
        "required_reduction": required,
        "feasible": False,
        "blocker": None,
        "owner": None,
    }
    if kind == "retail-binary":
        plan["blocker"] = "retail-binary-gen-needs-provider"
        plan["owner"] = OWNER_PROVIDER
    else:
        plan["blocker"] = "unrecognized-gen-format"
        plan["owner"] = OWNER_PROVIDER
    return plan


def _read(path, label):
    try:
        return Path(path).read_bytes()
    except OSError as exc:
        raise ThinError("unreadable-%s: %s" % (label, exc)) from exc


def assess(gen_dir, package_path=None, observed_me=CAP_ME_PIKIS):
    """Fail-closed assessment record for the staged chal4 arena."""
    gen_dir = Path(gen_dir)
    plans, gen_hashes = {}, {}
    for name in RETAIL_GENS:
        path = gen_dir / name
        if not path.is_file():
            raise ThinError("missing-generator-file: %s" % path)
        data = _read(path, name)
        gen_hashes[name] = {"sha256": _sha(data), "bytes": len(data)}
        plans[name] = thinning_plan(data, observed_me=observed_me)
    feasible = all(p["feasible"] for p in plans.values())
    record = {
        "schema": SCHEMA,
        "issue": ISSUE,
        "stage": STAGE,
        "cap_me_pikis": CAP_ME_PIKIS,
        "observed_me": int(observed_me),
        "squad_target": SQUAD_TARGET,
        "cap_source": CAP_SOURCE,
        "birth_source": BIRTH_SOURCE,
        "generators": gen_hashes,
        "plans": plans,
        "feasible": feasible,
        "verdict": "thinnable" if feasible else "blocked",
        "blocker": None if feasible else "retail-binary-gen-needs-provider",
        "owner": None if feasible else OWNER_B,
        "package_path": str(package_path) if package_path else None,
        "engine_change": False,
    }
    if not feasible:
        record["note"] = ("Buried sprouts are binary GenObjectPiki records in the "
                          "staged retail gens; no repository gen rewriter exists.")
    return record




def load_thin_tool(root=None):
    """Load the landed #795 gen-record thinner READ-ONLY (never edited)."""
    base = Path(root) if root is not None else Path("C:/Users/alari/pikmin-randomizer")
    path = base / THIN_TOOL_REL
    if not path.is_file():
        raise ThinError("thinning-tool-unreadable: %s" % path)
    spec = importlib.util.spec_from_file_location(
        "p1_challenge_gen_record_thinner_adopted", str(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for name in ("assess", "thin", "ThinError"):
        if name == "ThinError":
            if not (isinstance(getattr(module, name, None), type)
                    and issubclass(getattr(module, name), Exception)):
                raise ThinError("thinning-tool-lacks-api: %s" % name)
        elif not callable(getattr(module, name, None)):
            raise ThinError("thinning-tool-lacks-api: %s" % name)
    return module


def stage_thinned_arena(tool, retail_assets, out_dir, cap=CAP_ME_PIKIS, squad=SQUAD_TARGET):
    """Mirror the retail assets with symlinks and overlay thinned chal4 gens.

    Returns (arena_dir, manifest). Only buried-sprout generator records are
    removed (largest first) until headroom fits the squad; every kept byte
    stays identical to retail. Refuses (ThinError) when the tool cannot parse
    the staged gens.
    """
    import shutil
    retail = Path(retail_assets)
    arena = Path(out_dir) / "thin-arena-assets"
    chal4 = Path("dataDir/stages/chal4")
    if not (retail / chal4 / "default.gen").is_file():
        raise ThinError("missing-generator-file: %s" % (retail / chal4 / "default.gen"))
    if arena.exists():
        shutil.rmtree(str(arena))
    shutil.copytree(str(retail), str(arena), symlinks=True)
    manifest = {"schema": SCHEMA, "issue": ISSUE, "stage": STAGE,
                "tool": {"path": THIN_TOOL_REL, "commit": THIN_TOOL_COMMIT},
                "cap": int(cap), "squad": int(squad), "gens": {}}
    for name in RETAIL_GENS:
        src = retail / chal4 / name
        if not src.is_file():
            raise ThinError("missing-generator-file: %s" % src)
        data = src.read_bytes()
        try:
            out_bytes, packet = tool.thin(data, cap=int(cap), squad=int(squad))
        except tool.ThinError as exc:
            raise ThinError("thinning-tool-refused %s: %s" % (name, exc)) from exc
        dest = arena / chal4 / name
        if dest.is_symlink() or dest.is_file():
            dest.unlink()
        dest.write_bytes(out_bytes)
        manifest["gens"][name] = {
            "input_sha256": packet["input"]["sha256"],
            "output_sha256": packet["output"]["sha256"],
            "buried_before": packet["buried_before"],
            "buried_after": packet["buried_after"],
            "removed": packet["removed"],
        }
    (Path(out_dir) / "thin-manifest.json").write_text(
        json.dumps(manifest, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return arena, manifest


def build_thin_package(out_dir, manifest):
    """Write the thinned stage package and verify it on the #567 path."""
    package = {
        "schema": 1,
        "stages": [{
            "slot": STAGE,
            "challenge_level": 4,
            "argv": ["nectar.exe", "--experimental-challenge-level", "4"],
            "thin_manifest": "thin-manifest.json",
            "buried_after": manifest["gens"]["default.gen"]["buried_after"],
        }],
    }
    path = Path(out_dir) / "challenge-runtime-inputs-thin.json"
    path.write_text(json.dumps(package, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return path

def load_driver(path=None):
    """Load the blocked #567 driver READ-ONLY for its check/parse helpers."""
    path = Path(path) if path else Path("C:/Users/alari/pikmin-randomizer") / DRIVER_REL
    if not path.is_file():
        raise ThinError("blocked-driver-unreadable: %s" % path)
    spec = importlib.util.spec_from_file_location("p1_challenge_trial_acceptance_adopted", str(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for name in ("check_stage_package", "parse_run_log", "birth_limitation_record"):
        if not callable(getattr(module, name, None)):
            raise ThinError("blocked-driver-lacks-api: %s" % name)
    return module


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gen-dir", required=True)
    parser.add_argument("--package", default="")
    parser.add_argument("--observed-me", type=int, default=CAP_ME_PIKIS)
    args = parser.parse_args(argv)
    try:
        record = assess(args.gen_dir, args.package or None, args.observed_me)
    except ThinError as exc:
        print("FAIL P1_CHALLENGE_TRIAL_ARENA_THIN_V2 %s" % exc)
        return 1
    print(json.dumps(record, indent=1))
    if record["verdict"] != "thinnable":
        print("BLOCKED P1_CHALLENGE_TRIAL_ARENA_THIN_V2 %s owner=%s"
              % (record["blocker"], record["owner"]))
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
