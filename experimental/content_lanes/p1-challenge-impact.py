"""P0 import contract for P1 Challenge Impact (issue #565, lane p1-challenge-impact).

Isolated metadata adapter over the retail P1 Challenge Impact source entry
(stages/chal0.ini plus its generator closure). It decodes actual stage
definitions, validates resource closure with pinned SHA-256 hashes, and
summarizes generator framing WITHOUT emitting runtime placements: weighted
definition rows stay definitions, never actor counts.

Reuse, not duplication: generator record framing comes from the existing
scripts.preview_pikmin2_room.records splitter, and destination identity is
cross-checked against experimental.levels. No global parser, schema, species
or other-lane edits. Missing sources raise MissingPrerequisite naming the
exact absent files; nothing is invented.
"""
import hashlib
import re
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from experimental.levels import BY_KEY
from scripts.preview_pikmin2_room import records as split_gen_records

LEVEL_KEY = 'challenge:impact'
SOURCE_STAGE_FILE = 'stages/chal0.ini'
NATIVE_AREA_ID = 0
STAGE_INFO_INDEX = 16
GENERATOR_FILES = ('default.gen', 'plants.gen')


class MissingPrerequisite(Exception):
    """Raised when a required source file is absent; carries the exact rel paths."""


def _read_stage_text(path):
    try:
        data = Path(path).read_bytes()
    except OSError:
        raise MissingPrerequisite('Missing stage definition: ' + str(path))
    return data.decode('shift_jis', errors='replace')


def decode_stage_ini(path):
    """Decode navi_start, map_file, day_multiply, timesetting and room counts.

    Raises MissingPrerequisite when the file is absent, ValueError when a
    required definition is missing or malformed.
    """
    text = _read_stage_text(path)
    navi = re.search(r'^navi_start\s+(\S+)\s+(\S+)', text, re.M)
    if not navi:
        raise ValueError('Missing navi_start: ' + str(path))
    try:
        navi_start = (float(navi[1]), float(navi[2]))
    except ValueError:
        raise ValueError('Malformed navi_start: ' + str(path))
    mapping = re.search(r'^map_file\s+(\S+)', text, re.M)
    if not mapping:
        raise ValueError('Missing map file: ' + str(path))
    clock = re.search(r'^day_multiply\s+(\S+)', text, re.M)
    if not clock:
        raise ValueError('Missing day_multiply: ' + str(path))
    try:
        day_multiply = float(clock[1])
    except ValueError:
        raise ValueError('Malformed day_multiply: ' + str(path))
    settings = re.search(r'^dayMgr\s*\{\s*numsettings\s+(\d+)', text, re.M)
    timesettings = len(re.findall(r'^timesetting\s+\d+', text, re.M))
    if not settings or int(settings[1]) != timesettings:
        raise ValueError('dayMgr timesetting coverage mismatch: ' + str(path))
    return {'navi_start': navi_start, 'map_file': mapping[1],
            'day_multiply': day_multiply, 'timesettings': timesettings,
            'rooms': len(re.findall(r'^new_room\s*\{', text, re.M))}


def _hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def resource_closure(assets):
    """Hash the full source closure: ini, generator files, referenced geometry.

    Returns file entries with repository-independent rel paths, hashes and
    sizes. Raises MissingPrerequisite listing every absent rel path.
    """
    root = Path(assets)
    ini_rel = 'dataDir/' + SOURCE_STAGE_FILE
    candidates = [ini_rel] + ['dataDir/stages/chal0/' + name for name in GENERATOR_FILES]
    missing = [rel for rel in candidates if not (root / rel).is_file()]
    if missing:
        raise MissingPrerequisite('Missing source files: ' + ', '.join(missing))
    try:
        geometry = decode_stage_ini(root / ini_rel)['map_file']
    except ValueError as exc:
        raise ValueError(str(exc))
    geo_rel = 'dataDir/' + geometry
    if not (root / geo_rel).is_file():
        raise MissingPrerequisite('Missing source files: ' + geo_rel)
    entries = []
    for rel in candidates + [geo_rel]:
        full = root / rel
        entries.append({'rel': rel, 'sha256': _hash(full), 'bytes': full.stat().st_size})
    return entries


def summarize_generator(path):
    """Frame-level summary of one .gen file: record count, bytes, type-tag histogram.

    Type tags are raw 4-byte record fields; no semantic actor counts are
    derived. Malformed framing raises the existing splitter's ValueError.
    """
    blobs = split_gen_records(Path(path))
    tags = {}
    for blob in blobs:
        tag = bytes(blob[72:76]).decode('ascii', errors='replace') if len(blob) >= 76 else '<short>'
        tags[tag] = tags.get(tag, 0) + 1
    return {'records': len(blobs), 'bytes': Path(path).stat().st_size, 'tags': tags}


def audit(assets):
    """Full P0 packet: definitions, closure, generator framing, identity cross-check.

    Identity is verified against experimental.levels (challenge:impact must be
    native area 0 served by stages/chal0.ini); shared practice terrain is
    reported as-is so level keys stay qualified downstream. Raises
    MissingPrerequisite/ValueError instead of inventing values.
    """
    root = Path(assets)
    if not root.is_dir():
        raise MissingPrerequisite('Missing source assets root: ' + str(root))
    level = BY_KEY.get(LEVEL_KEY)
    if level is None or level.area_id != NATIVE_AREA_ID or level.stage_file != SOURCE_STAGE_FILE:
        raise ValueError('Destination identity drift for ' + LEVEL_KEY)
    ini_rel = 'dataDir/' + SOURCE_STAGE_FILE
    definitions = decode_stage_ini(root / ini_rel)
    closure = resource_closure(root)
    by_rel = {entry['rel']: entry for entry in closure}
    generators = {}
    for name in GENERATOR_FILES:
        rel = 'dataDir/stages/chal0/' + name
        summary = summarize_generator(root / rel)
        summary.update(by_rel[rel])
        generators[name] = summary
    return {'level_key': LEVEL_KEY, 'native_area_id': NATIVE_AREA_ID,
            'stage_info_index': STAGE_INFO_INDEX, 'source': SOURCE_STAGE_FILE,
            'definitions': definitions, 'closure': closure, 'generators': generators,
            'floors': [{'course': 'challenge:impact', 'generator_files': list(GENERATOR_FILES)}]}
