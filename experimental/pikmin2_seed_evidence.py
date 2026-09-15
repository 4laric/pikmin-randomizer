"""Lane 05 seed→native evidence markers and toolchain discovery (no lane paths).

Pure helpers shared by the cohort/generated-seed probes and their flip tests. The
marker predicates are byte-substring tests over the native log so a stripped bank
or ``P2_ENEMY_READY`` line flips the corresponding check.
"""
import os
import re
from pathlib import Path


def find_mingw():
    """MinGW runtime dir (SDL2.dll + gcc runtime) from env, PATH, or a fallback."""
    env = os.environ.get('MINGW_BIN')
    if env and (Path(env) / 'SDL2.dll').exists():
        return str(Path(env))
    for entry in os.environ.get('PATH', '').split(os.pathsep):
        if entry and (Path(entry) / 'SDL2.dll').exists():
            return entry
    fallback = Path(r'C:/msys64/mingw64/bin')
    return str(fallback) if (fallback / 'SDL2.dll').exists() else None


def cohort_markers(text):
    """Checks that the engine loaded the staged banks/sidecars with no fallback."""
    roster = re.search(r'default: read (\d+) generators', text)
    return {
        'window_960x540': '960x540' in text,
        'roster_read': roster is not None,
        'roster_curated': roster is not None and int(roster.group(1)) < 80,
        'dwarf_bank': 'P2_DWARF_ORANGE_BANK poses=' in text,
        'dwarf_ready': 'P2_ENEMY_READY species=BlueKochappy source_id=44' in text,
        'snow_bank': 'P2_SNOW_BANK poses=' in text,
        'snow_ready': 'P2_ENEMY_READY species=YellowKochappy' in text,
        'no_missing_room': 'FAILED to open assets/dataDir/courses/pikmin2room/' not in text,
        'no_duplicate_treasure': 'duplicate treasure' not in text,
    }


def ready_species(text):
    """Every ``species=`` token emitted by a ``P2_ENEMY_READY`` line, in order."""
    return [m.group(1) for m in re.finditer(r'P2_ENEMY_READY species=(\S+)', text)]


READY_TOKEN = {44: 'BlueKochappy', 45: 'YellowKochappy'}


def resolve_markers(text, cohort, generator_for_source, ready_token=None):
    """Wave-native resolve markers: the lane-03 seed bridge + lane-04 placement join.

    ``cohort`` is the seed's source ids; ``generator_for_source`` maps a source id
    to its arena generator id. For each in-cohort identity this requires the native
    seed bridge (``P2_SEED_RESOLVE source_id=<n> target=<uid>``) and the lane-04
    placement reader (``P2_PLACEMENT_SLOT generator=<g> slot=<uid>``) to agree on
    the SAME uid for the identity's generator, alongside the family
    ``P2_ENEMY_READY species=…`` line; an out-of-cohort identity must emit neither.
    """
    ready = ready_token or READY_TOKEN
    checks = {'placement_probe': 'P2_PLACEMENT_PROBE actors=' in text}
    cohort = set(cohort or ())
    for source_id, gid in generator_for_source.items():
        token = ready.get(source_id)
        if token is None:
            continue
        resolve_prefix = f'P2_SEED_RESOLVE source_id={source_id}'
        slot_generator = f'P2_PLACEMENT_SLOT generator={gid}'
        if source_id not in cohort:
            checks[f'no_seed_resolve_{token}'] = resolve_prefix not in text
            checks[f'no_placement_slot_{token}'] = slot_generator not in text
            continue
        match = re.search(rf'P2_SEED_RESOLVE source_id={source_id} target=(\d+)', text)
        checks[f'seed_resolve_{token}'] = match is not None
        if match:
            uid = match.group(1)
            checks[f'slot_agree_{token}'] = (
                f'P2_PLACEMENT_SLOT generator={gid} slot={uid}' in text
                and f'P2_ENEMY_READY species={token}' in text)
        else:
            checks[f'slot_agree_{token}'] = False
    return checks
