"""Dev-console session support (issue #942).

The native port's in-game dev console (``PIKMIN_DEV_CONSOLE=1``) spawns ported
Pikmin 2 species next to the captain through the same per-family bind path a
seed placement uses. That path keys everything (seed binding, family sidecars,
delivery receipts) on a generator uid, so a dev session's seed binds every
staged species to a synthetic *dev target uid* that no real generator carries:

    dev_target(source_id) == 0xDE000000 + source_id

Normal play never resolves such a uid; ``spawn <id>`` creates a runtime
generator registered under it. The native mirror of this scheme is
``pc_port/pc_dev_console_parser.h`` (``devconsole::devTargetUid``).

This module builds the dev seed manifest (a plain Forest of Hope solo seed with
a ``p2_layout`` whose bindings are the dev targets of the species whose content
is staged) and the matching ``{target: generator_id}`` actor map, and exposes
the environment the launcher sets for the native process.
"""
from __future__ import annotations

import json
from pathlib import Path

from .seed import PLAYABLE_P2_SPECIES, generate, validate

DEV_TARGET_BASE = 0xDE000000
DEV_TARGET_SPAN = 0x10000
DEV_CONSOLE_ENV = "PIKMIN_DEV_CONSOLE"
DEV_CONSOLE_SCRIPT_ENV = "PIKMIN_DEV_CONSOLE_SCRIPT"
DEFAULT_SCRIPT_NAME = "dev-console.txt"


def dev_target(source_id: int) -> str:
    """Return the dev target token (decimal uid string) for a P2 source id."""
    if type(source_id) is not int or not 0 < source_id < DEV_TARGET_SPAN:
        raise ValueError(f"bad P2 source id: {source_id!r}")
    return str(DEV_TARGET_BASE + source_id)


def is_dev_target(target) -> bool:
    try:
        uid = int(target)
    except (TypeError, ValueError):
        return False
    return DEV_TARGET_BASE < uid < DEV_TARGET_BASE + DEV_TARGET_SPAN


def dev_target_source(target) -> int:
    if not is_dev_target(target):
        raise ValueError(f"not a dev target: {target!r}")
    return int(target) - DEV_TARGET_BASE


def staged_species(content_root: Path, species=None) -> list[int]:
    """Playable species whose content is present under ``content_root``.

    Reads ``<content_root>/prepared.json`` (written by
    ``scripts/p2_prepare_content.py``) and keeps every extracted playable id,
    then confirms its enum directory exists. ``species`` narrows the pool.
    """
    content_root = Path(content_root)
    prepared = content_root / "prepared.json"
    if not prepared.is_file():
        raise FileNotFoundError(f"no prepared.json under {content_root}; run scripts/p2_prepare_content.py first")
    summary = json.loads(prepared.read_text(encoding="utf-8"))
    extracted = {int(i) for i in summary.get("extracted", [])}
    wanted = list(PLAYABLE_P2_SPECIES) if species is None else [int(i) for i in species]
    from scripts.p2_prepare_content import ENUM_FOR_SOURCE
    return [i for i in wanted
            if i in extracted and i in ENUM_FOR_SOURCE and (content_root / ENUM_FOR_SOURCE[i]).is_dir()]


def build_dev_layout(species_ids, roster=None) -> dict:
    """A ``p2_layout`` binding each species to its dev target, validated."""
    from experimental.pikmin2_enemy_roster import load_and_validate
    from experimental.pikmin2_seed_bridge import (DENSITY_LEGACY, LAYOUT_VERSION, ROSTER_SCHEMA,
                                                  eligible_identity, roster_revision, validate_layout)
    roster = roster if roster is not None else load_and_validate()
    ids = []
    for source_id in species_ids:
        if type(source_id) is not int or source_id in ids:
            raise ValueError(f"bad or duplicate species id: {source_id!r}")
        ids.append(source_id)
    if not ids:
        raise ValueError("dev layout needs at least one species")
    bindings = [dict(target=dev_target(i), source_id=i, enum_name=eligible_identity(roster, i).enum_name)
                for i in ids]
    layout = dict(version=LAYOUT_VERSION, roster_schema=ROSTER_SCHEMA, roster_revision=roster_revision(roster),
                  density=DENSITY_LEGACY, bindings=bindings)
    validate_layout(layout, roster)
    return layout


def actor_bindings(layout: dict) -> dict[str, int]:
    """``{target: generator_id}`` for ``install_layout``: the dev uid itself."""
    return {b["target"]: int(b["target"]) for b in layout["bindings"]}


def build_dev_manifest(species_ids, seed_name="dev-console", *, starting_color="red", roster=None) -> dict:
    """A Forest of Hope solo seed whose only P2 content is the dev bindings.

    Nothing in the P1 field changes (no enemy shuffle, no P1 layouts); the
    ``p2_layout`` only makes the native bridge resolve dev targets and makes
    the launcher stage every listed species' content.
    """
    manifest = generate(seed_name, starting_area="forest", starting_color=starting_color,
                        collection_checks=True)
    manifest["p2_layout"] = build_dev_layout(species_ids, roster)
    manifest["capabilities"].append("p2-enemy-bridge-v1")
    validate(manifest)
    return manifest


def native_environment(script_path) -> dict[str, str]:
    """Environment variables that switch the native console on."""
    return {DEV_CONSOLE_ENV: "1", DEV_CONSOLE_SCRIPT_ENV: str(Path(script_path).resolve())}
