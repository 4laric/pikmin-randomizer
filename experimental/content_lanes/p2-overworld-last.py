'''P0 import-contract adapter for P2 overworld course last (Wistful Wild).

Lane p2-overworld-last-p0-real-source, issue 151. Decodes the REAL legal
user/Abe/stages.txt for course last with byte-exact source hashing and a
resource-closure manifest. Corrects synthetic-only assumptions against
observed retail bytes (stages.txt sha256
4de9008c99e799b99b2746c0156846eeb7ad50895ad110fc7f2070db6de1fff8):
5 courses in brace blocks; # starts an end-of-line comment; no farm keyword;
brace-wrapped cave ids; literal end trailer after startangle.
Generator rows stay definitions, never actor counts or placements.
No native build, no runtime run, no shared edits, no ADMIT.'''

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from dataclasses import dataclass, field
from pathlib import Path

SOURCE_PATH = 'user/Abe/stages.txt'
COURSE_ID = 'last'
EXPECTED_COURSE_COUNT = 5
EXPECTED_COURSE_INDEX = 3

PATH_KEYWORDS = ('folder', 'abe_folder', 'model', 'collision', 'waterbox',
    'mapcode', 'route')

REQUIRED_INVENTORY = (
    'terrain/collision/water',
    'generator day schedules and regrowth',
    'buried/enemy-held treasure',
    'Onions/ship/bridges/gates',
    'all cave entrances and return anchors',)

RUNTIME_PREREQUISITES = (
    '#128 actor/assets/species and hazards',
    '#130 actor/assets/species and hazards',
    '#131 actor/assets/species and hazards',
    '#132 surface days, saves and progression',
    '#140 actor/assets/species and hazards',
    '#144 actor/assets/species and hazards',
    '#145 actor/assets/species and hazards',
    '#146 actor/assets/species and hazards',)


class StagesDecodeError(ValueError):
    '''Raised for any malformed stages.txt content; message names the defect.'''


class SourceMissingError(FileNotFoundError):
    '''Raised when the legal retail source file is unavailable.'''


def prerequisite_message(source=SOURCE_PATH):
    return (
        'missing prerequisite: legal retail file ' + source + ' is not staged; '
        'extract it read-only from a legally owned P2 disc ('
        'C:/Users/alari/Downloads/PIKMIN2 for GAMECUBE.iso) into the lane output '
        'directory and rerun with --source <path>; no values are invented when '
        'the source is absent.'
    )


@dataclass
class LimitRow:
    name: str
    minimum_day: int
    maximum_day: int
    day_limit: int


@dataclass
class CaveRow:
    cave_id: str
    otakara_count: int
    filename: str


@dataclass
class Course:
    name: str
    index: int
    paths: dict = field(default_factory=dict)
    start: tuple = (0.0, 0.0, 0.0)
    start_angle: float = 0.0
    limit_gen: list = field(default_factory=list)
    loop_gen: list = field(default_factory=list)
    caves: list = field(default_factory=list)
    ground_otakara_max: int = 0


class _Tokens:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0
    def take(self, what):
        if self.pos >= len(self.tokens):
            raise StagesDecodeError('truncated file while reading ' + what)
        token = self.tokens[self.pos]
        self.pos += 1
        return token
    def take_int(self, what):
        token = self.take(what)
        try:
            return int(token)
        except ValueError:
            raise StagesDecodeError('bad integer for ' + what + ': ' + token)
    def take_float(self, what):
        token = self.take(what)
        try:
            value = float(token)
        except ValueError:
            raise StagesDecodeError('bad float for ' + what + ': ' + token)
        if not math.isfinite(value):
            raise StagesDecodeError('non-finite float for ' + what + ': ' + token)
        return value
    def expect(self, want, what):
        token = self.take(what)
        if token != want:
            raise StagesDecodeError(what + ': expected ' + want + ', found ' + token)
        return token
    def remaining(self):
        return len(self.tokens) - self.pos

def _tokenize(text):
    words = []
    for line in text.splitlines():
        cut = line.find(chr(35))
        if cut >= 0:
            line = line[:cut]
        words.extend(line.split())
    return words


def _read_gen_table(tokens, what):
    count = tokens.take_int(what + ' count')
    if count < 0 or count > 4096:
        raise StagesDecodeError('implausible ' + what + ' count: ' + str(count))
    rows = []
    for _ in range(count):
        name = tokens.take(what + ' name')
        minimum = tokens.take_int(what + ' minimum_day')
        maximum = tokens.take_int(what + ' maximum_day')
        limit = tokens.take_int(what + ' day_limit')
        rows.append(LimitRow(name, minimum, maximum, limit))
    return rows


def _read_cave_table(tokens):
    count = tokens.take_int('cave count')
    if count < 0 or count > 4096:
        raise StagesDecodeError('implausible cave count: ' + str(count))
    rows = []
    for _ in range(count):
        raw = tokens.take('cave id')
        if len(raw) < 3 or not raw.startswith(chr(123)) or not raw.endswith(chr(125)):
            raise StagesDecodeError('cave id must be brace-wrapped, found ' + raw)
        otakara = tokens.take_int('cave otakara_count')
        filename = tokens.take('cave filename')
        rows.append(CaveRow(raw[1:-1], otakara, filename))
    return rows

def _read_course(tokens, index):
    course = Course(name='', index=index)
    for keyword in ('name',) + PATH_KEYWORDS:
        tokens.expect(keyword, 'course ' + str(index) + ' keyword')
        course.paths[keyword] = tokens.take('course ' + str(index) + ' ' + keyword)
    course.name = course.paths.pop('name')
    tokens.expect('start', 'course ' + str(index) + ' start keyword')
    course.start = (tokens.take_float('start x'), tokens.take_float('start y'),
                    tokens.take_float('start z'))
    tokens.expect('startangle', 'course ' + str(index) + ' startangle keyword')
    course.start_angle = tokens.take_float('start angle')
    tokens.expect('end', 'course ' + str(index) + ' end trailer')
    course.limit_gen = _read_gen_table(tokens, 'limit_gen')
    course.loop_gen = _read_gen_table(tokens, 'loop_gen')
    course.caves = _read_cave_table(tokens)
    course.ground_otakara_max = tokens.take_int('ground_otakara_max')
    return course


def parse_stages(text):
    tokens = _Tokens(_tokenize(text))
    if not tokens.tokens:
        raise StagesDecodeError('empty stages.txt')
    count = tokens.take_int('course count')
    if count != EXPECTED_COURSE_COUNT:
        raise StagesDecodeError('expected ' + str(EXPECTED_COURSE_COUNT) + ' courses, found ' + str(count))
    courses = []
    for i in range(count):
        tokens.expect(chr(123), 'course ' + str(i) + ' block open')
        courses.append(_read_course(tokens, i))
        tokens.expect(chr(125), 'course ' + str(i) + ' block close')
    if tokens.remaining():
        raise StagesDecodeError('trailing tokens after ' + str(count) + ' courses: ' + str(tokens.remaining()))
    return courses


def select_course(courses, course_id=COURSE_ID):
    for course in courses:
        if course.name == course_id:
            return course
    raise StagesDecodeError('course ' + course_id + ' not present')

def validate_course(course):
    defects = []
    for keyword in PATH_KEYWORDS:
        value = course.paths.get(keyword, '')
        if not value:
            defects.append('course ' + course.name + ': empty path for ' + keyword)
        elif value.startswith('/') or chr(92) in value:
            defects.append('course ' + course.name + ': non-retail path shape for ' + keyword)
    ok = True
    for axis in course.start + (course.start_angle,):
        if not math.isfinite(axis):
            ok = False
    if not ok:
        defects.append('course ' + course.name + ': non-finite start')
    for table, what in ((course.limit_gen, 'limit_gen'), (course.loop_gen, 'loop_gen')):
        for row in table:
            if not row.name:
                defects.append('course ' + course.name + ': empty ' + what + ' row name')
            if row.minimum_day < 0 or row.maximum_day < 0 or row.day_limit < 0:
                defects.append('course ' + course.name + ': negative ' + what + ' schedule')
            if row.minimum_day > row.maximum_day:
                defects.append('course ' + course.name + ': inverted ' + what + ' day range')
    seen = set()
    for row in course.caves:
        if not row.cave_id:
            defects.append('course ' + course.name + ': empty cave id')
        if row.cave_id in seen:
            defects.append('course ' + course.name + ': duplicate cave id ' + row.cave_id)
        seen.add(row.cave_id)
        if not row.filename:
            defects.append('course ' + course.name + ': empty cave filename')
        if row.otakara_count < 0:
            defects.append('course ' + course.name + ': negative otakara count')
    if course.ground_otakara_max < 0:
        defects.append('course ' + course.name + ': negative ground_otakara_max')
    return defects


def resource_closure(course):
    folder = course.paths.get('folder', '')
    abe = course.paths.get('abe_folder', '')
    return dict(model=folder + '/' + course.paths.get('model', ''),
                collision=folder + '/' + course.paths.get('collision', ''),
                waterbox=folder + '/' + course.paths.get('waterbox', ''),
                mapcode=folder + '/' + course.paths.get('mapcode', ''),
                route=abe + '/' + course.paths.get('route', ''))


def load_source_bytes(path):
    candidate = Path(path)
    if not candidate.is_file():
        raise SourceMissingError(prerequisite_message(str(path)))
    data = candidate.read_bytes()
    if not data:
        raise StagesDecodeError('source file is empty')
    return data, hashlib.sha256(data).hexdigest()

def build_manifest(course, source, sha256):
    manifest = {}
    manifest['schema'] = 'p2-overworld-p0-1'
    manifest['lane'] = 'p2-overworld-last'
    manifest['issue'] = 151
    manifest['source'] = source
    manifest['source_sha256'] = sha256
    manifest['course'] = course.name
    manifest['course_index'] = course.index
    manifest['expected_course_count'] = EXPECTED_COURSE_COUNT
    manifest['expected_course_index'] = EXPECTED_COURSE_INDEX
    manifest['start'] = list(course.start)
    manifest['start_angle_deg'] = course.start_angle
    manifest['resource_closure'] = resource_closure(course)
    manifest['limit_gen'] = [dict(name=r.name, minimum_day=r.minimum_day, maximum_day=r.maximum_day, day_limit=r.day_limit) for r in course.limit_gen]
    manifest['loop_gen'] = [dict(name=r.name, minimum_day=r.minimum_day, maximum_day=r.maximum_day, day_limit=r.day_limit) for r in course.loop_gen]
    manifest['caves'] = [dict(cave_id=r.cave_id, otakara_count=r.otakara_count, filename=r.filename) for r in course.caves]
    manifest['ground_otakara_max'] = course.ground_otakara_max
    manifest['required_inventory_coverage'] = {
        'terrain/collision/water': ['collision', 'waterbox', 'mapcode', 'model'],
        'generator day schedules and regrowth': ['limit_gen', 'loop_gen'],
        'buried/enemy-held treasure': ['caves', 'ground_otakara_max'],
        'Onions/ship/bridges/gates': ['route'],
        'all cave entrances and return anchors': ['caves'],
    }
    manifest['runtime_prerequisites'] = list(RUNTIME_PREREQUISITES)
    manifest['placements_emitted'] = False
    for item in REQUIRED_INVENTORY:
        if item not in manifest['required_inventory_coverage']:
            raise StagesDecodeError('coverage gap for required item ' + item)
    return manifest


def decode_course_file(path, course_id=COURSE_ID):
    data, digest = load_source_bytes(path)
    try:
        text = data.decode('utf-8')
    except UnicodeDecodeError as exc:
        raise StagesDecodeError('source is not UTF-8 text') from exc
    courses = parse_stages(text)
    course = select_course(courses, course_id)
    if course.index != EXPECTED_COURSE_INDEX:
        raise StagesDecodeError('course ' + course_id + ' at index ' + str(course.index) + ', expected ' + str(EXPECTED_COURSE_INDEX))
    defects = validate_course(course)
    if defects:
        raise StagesDecodeError('course defects: ' + '; '.join(defects))
    return course, digest

def main(argv):
    parser = argparse.ArgumentParser(description='P0 decode of user/Abe/stages.txt course last')
    parser.add_argument('--source', required=True)
    parser.add_argument('--course', default=COURSE_ID)
    parser.add_argument('--manifest-out', required=True)
    args = parser.parse_args(argv)
    try:
        course, digest = decode_course_file(args.source, args.course)
    except (SourceMissingError, StagesDecodeError) as exc:
        print('ERROR ' + str(exc), file=sys.stderr)
        return 1
    manifest = build_manifest(course, args.source, digest)
    Path(args.manifest_out).write_text(json.dumps(manifest, indent=1), encoding='utf-8')
    print('course=' + course.name + ' index=' + str(course.index) + ' caves=' + str(len(course.caves)) + ' sha256=' + digest)
    print('manifest=' + args.manifest_out + ' placements_emitted=False')
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
