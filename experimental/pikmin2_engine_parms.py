"""Engine-lane (#128) retail disc parameter extraction for #244/#245/#246.

Reads the user-supplied US GPVE01 rev 0 disc copy and records, as structured
local data, the enemy parm values, animation-bank clip lists, pellet
configurations, cave spawn cargo and global constants consumed by the
BombSarai (#244), Fuefuki (#245) and BigTreasure (#246) family lanes.

Parse functions are pure text parsers (unit-testable without the disc); disc
and archive access goes through experimental.pikmin2_assets, which this lane
does not modify. Generated JSON stays in the local output directory and is
not committed, per repository policy.
"""
import argparse
import json
import math
from pathlib import Path
import re
import struct

from experimental.pikmin2_assets import archive_files, disc_files, u32

PARM_ARCHIVE = 'enemy/parm/enemyParms.szs'
AI_CONSTANTS = 'user/Kando/aiConstants.txt'
OTAKARA_CONFIG = 'user/Abe/Pellet/us/otakara_config.txt'
MESSAGE_ARCHIVE = 'message/mesRes_eng.szs'
DREAM_DEN_FLOORS = 'user/Mukki/mapunits/caveinfo/last_3.txt'
CHALLENGE_FLOORS = 'user/Mukki/mapunits/caveinfo/ch_MUKI_oootakara.txt'
FAMILIES = {
    'bombsarai': 'enemy/data/BombSarai',
    'bomb': 'enemy/data/Bomb',
    'fuefuki': 'enemy/data/Fuefuki',
    'bigtreasure': 'enemy/data/BigTreasure',
}
WEAPON_PELLETS = ('elec', 'fire', 'gas', 'water', 'loozy')

PARM_LINE = re.compile(r'^\t\{([A-Za-z0-9_]+)\} (\S+) (\S+) ?\t# (.+)$')
KEYEVENT_LINE = re.compile(r'^\t(\d+) (\d+)\s*$')


def parse_parm_text(text):
    """Parse one enemyparm.txt into a list of (section_name, {tag: (value, comment)}).

    The retail format repeats the '# EnemyParmsBase' header for both the
    general and the proper parm blocks, so sections are order-preserving and
    duplicate names are kept.
    """
    sections = []
    section = None
    params = None
    for raw in text.splitlines():
        line = raw.rstrip('\r')
        if line.startswith('#') and line != '#':
            name = line[1:].strip()
            if name and not name.startswith('\t'):
                section = name
                continue
        if line == '{':
            if section is not None:
                params = {}
                sections.append((section, params))
            continue
        if line == '}':
            params = None
            continue
        if '{_eof}' in line:
            section = None
            continue
        match = PARM_LINE.match(line)
        if match:
            if params is None:
                raise ValueError('Parameter outside a section')
            tag, kind, value, comment = match.groups()
            if kind not in ('-1', '4'):
                raise ValueError('Unsupported parameter kind: ' + kind)
            if tag in params:
                # Retail bigtreasure block repeats fg99 (pattern check) with
                # the same value; identical repeats are tolerated, conflicting
                # values still fail closed.
                if params[tag] != (value.strip(), comment.strip()):
                    raise ValueError('Conflicting duplicate parameter tag: ' + tag)
                continue
            params[tag] = (value.strip(), comment.strip())
            continue
        raise ValueError('Malformed parameter line: ' + repr(line))
    if not sections:
        raise ValueError('No parameter sections found')
    return sections


def parse_anim_mgr(text):
    """Parse one enemyanimmgr.txt into {'count': n, 'clips': [...]}.

    Each clip: {'file', 'events': [(frame, keyevent), ...]} preserving order.
    """
    lines = [line.rstrip('\r') for line in text.splitlines()]
    index = 0
    count = None
    clips = []
    while index < len(lines):
        line = lines[index]
        index += 1
        match = re.fullmatch(r'\t(\d+) \t# number of animations', line)
        if match:
            if count is not None:
                raise ValueError('Duplicate animation count')
            count = int(match.group(1))
            continue
        if not line or line.startswith('#'):
            continue
        if line != '{':
            raise ValueError('Malformed anim manager line: ' + repr(line))
        block = []
        while index < len(lines) and lines[index] != '}':
            block.append(lines[index])
            index += 1
        if index >= len(lines) or len(block) < 2:
            raise ValueError('Unterminated animation block')
        index += 1
        events = []
        seen_terminator = False
        for entry in block[2:]:
            if entry.strip() == '-1':
                if seen_terminator:
                    raise ValueError('Duplicate block terminator')
                seen_terminator = True
                continue
            if seen_terminator:
                raise ValueError('Event after block terminator')
            match = KEYEVENT_LINE.match(entry)
            if not match:
                raise ValueError('Malformed key event line: ' + repr(entry))
            frame, code = int(match.group(1)), int(match.group(2))
            if events and frame < events[-1][0]:
                raise ValueError('Key events out of frame order')
            events.append((frame, code))
        if not seen_terminator:
            raise ValueError('Animation block missing terminator')
        clips.append({'file': block[1].strip(), 'events': events})
    if count is None or count != len(clips):
        raise ValueError('Animation count mismatch: declared %r, found %d' % (count, len(clips)))
    return {'count': count, 'clips': clips}


def parse_otakara_config(text, wanted):
    """Parse otakara_config.txt blocks for the requested pellet names."""
    found = {}
    for block in re.findall(r'\{([^{}]*)\}', text):
        fields = {}
        for line in block.splitlines():
            line = line.rstrip('\r')
            if line == '\tend':
                fields['end'] = 'end'
                continue
            match = re.fullmatch(r'\t(\w+)\t+(\S+)', line)
            if match:
                key, value = match.groups()
                if key in fields:
                    raise ValueError('Duplicate pellet field: ' + key)
                fields[key] = value
        name = fields.get('name')
        if name in wanted:
            if name in found:
                raise ValueError('Duplicate pellet config: ' + name)
            if fields.get('end') != 'end':
                raise ValueError('Pellet block missing end marker: ' + name)
            required = ('archive', 'bmd', 'radius', 'p_radius', 'height',
                        'inertiascaling', 'friction', 'min', 'max', 'money',
                        'unique', 'code', 'dictionary')
            missing = [key for key in required if key not in fields]
            if missing:
                raise ValueError('Pellet %s missing fields: %s' % (name, missing))
            for numeric in ('radius', 'p_radius', 'height', 'inertiascaling',
                            'friction', 'min', 'max', 'money', 'code', 'dictionary'):
                value = float(fields[numeric])
                if not math.isfinite(value):
                    raise ValueError('Invalid numeric pellet field: ' + numeric)
            found[name] = fields
    missing = [name for name in wanted if name not in found]
    if missing:
        raise ValueError('Pellet configs not found: ' + ','.join(missing))
    return found


def parse_ai_constants(text):
    """Parse user/Kando/aiConstants.txt into {name: float}."""
    result = {}
    for line in text.splitlines():
        line = line.rstrip('\r').strip()
        if not line or line.startswith('#') or line == 'end':
            continue
        match = re.fullmatch(r'(\w+)\t+(\S+)', line)
        if not match:
            raise ValueError('Malformed aiConstants line: ' + repr(line))
        key, value = match.groups()
        number = float(value)
        if not math.isfinite(number):
            raise ValueError('Invalid aiConstants value: ' + key)
        if key in result:
            raise ValueError('Duplicate aiConstants key: ' + key)
        result[key] = number
    if 'gravity' not in result:
        raise ValueError('aiConstants missing gravity')
    return result


def parse_teki_tokens(text, enemy_name):
    """Return every TekiInfo token in a caveinfo file matching enemy_name.

    Tokens follow TekiInfo::read: an underscore suffix after a known enemy
    name is carried-cargo data (parsedBuffer -> mOtakaraItemCode). A plain
    token with no suffix means a null otakara code.
    """
    tokens = []
    for match in re.finditer(
            r'(?ms)^# TekiInfo\s*\n\{\s*\n\s*(\d+)\s+# num\s*\n(.*?)^\}', text):
        declared = int(match.group(1))
        rows = re.findall(r'^\t(\S+) (\d+) \t# weight\s*\r?\n\t(\d+) \t# type',
                          match.group(2), re.M)
        if len(rows) != declared:
            raise ValueError('TekiInfo count mismatch')
        for token, weight, kind in rows:
            base = token.split('_', 1)[0] if '_' in token else token
            if base == enemy_name or token == enemy_name:
                tokens.append({'token': token, 'weight': int(weight),
                               'type': int(kind),
                               'carried': token.split('_', 1)[1] if token != enemy_name and token.startswith(enemy_name + '_') else None})
    return tokens


def bmg_find_strings(bmg, needles):
    """Locate raw (escape-stripped) ASCII strings inside a GameCube BMG.

    Returns {needle: [offsets]} with offsets relative to the DAT1 payload.
    """
    if bmg[:4] != b'MESG':
        raise ValueError('Expected BMG message data')
    position = 0x20
    dat = None
    while position < len(bmg):
        tag, size = bmg[position:position + 4], u32(bmg, position + 4)
        if tag == b'DAT1':
            dat = bmg[position + 8:position + size]
        position += size
    if dat is None:
        raise ValueError('BMG missing DAT1 section')
    result = {}
    for needle in needles:
        raw = needle.encode('ascii')
        offsets = []
        start = 0
        while True:
            index = dat.find(raw, start)
            if index < 0:
                break
            if index == 0 or dat[index - 1] == 0:
                end = index + len(raw)
                if end >= len(dat) or dat[end] == 0:
                    offsets.append(index)
            start = index + 1
        if not offsets:
            raise ValueError('BMG string not found: ' + needle)
        result[needle] = offsets
    return result


def extract(iso_path, output_dir):
    iso_path = Path(iso_path)
    output_dir = Path(output_dir)
    catalog = disc_files(iso_path)

    def fetch(path):
        offset, length = catalog[path]
        with iso_path.open('rb') as file:
            file.seek(offset)
            return file.read(length)

    parms = archive_files(fetch(PARM_ARCHIVE))
    report = {'disc': {'gamecode': 'GPVE01', 'revision': 0,
                       'note': 'identity verified by disc_files header check'},
              'families': {}}
    for family in ('bombsarai', 'bomb', 'fuefuki', 'bigtreasure'):
        entry = {}
        parm_name = family + '/enemyparm.txt'
        if parm_name in parms:
            entry['parm'] = parse_parm_text(parms[parm_name].decode('shift_jis'))
        anim_name = family + '/enemyanimmgr.txt'
        if anim_name in parms:
            entry['anim_mgr'] = parse_anim_mgr(
                parms[anim_name].decode('shift_jis'))
        data_root = FAMILIES[family]
        for archive_name in ('model.szs', 'anim.szs'):
            if data_root + '/' + archive_name in catalog:
                members = archive_files(fetch(data_root + '/' + archive_name))
                entry[archive_name.replace('.szs', '') + '_members'] = sorted(
                    (name, len(data)) for name, data in members.items())
        report['families'][family] = entry

    report['ai_constants'] = parse_ai_constants(
        fetch(AI_CONSTANTS).decode('shift_jis'))
    report['weapon_pellets'] = parse_otakara_config(
        fetch(OTAKARA_CONFIG).decode('shift_jis'), WEAPON_PELLETS)
    report['bigtreasure_spawns'] = {
        'story_dream_den_floor14': parse_teki_tokens(
            fetch(DREAM_DEN_FLOORS).decode('shift_jis'), 'BigTreasure'),
        'challenge_mode': parse_teki_tokens(
            fetch(CHALLENGE_FLOORS).decode('shift_jis'), 'BigTreasure'),
    }
    bmg = archive_files(fetch(MESSAGE_ARCHIVE))['pikmin2.bmg']
    report['treasure_names'] = bmg_find_strings(bmg, [
        'Shock\nTherapist', 'Flare\nCannon', 'Comedy\nBomb', 'Monster\nPump',
        'King of Bugs'])

    output_dir.mkdir(parents=True, exist_ok=True)
    target = output_dir / 'engine_disc_parms.json'
    target.write_text(json.dumps(report, indent=1, ensure_ascii=False),
                      encoding='utf-8')
    return target


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iso', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(extract(args.iso, args.output))
