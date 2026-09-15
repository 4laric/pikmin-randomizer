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
