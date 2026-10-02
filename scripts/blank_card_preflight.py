"""Read-only checks for native-created blank cards; never writes card bytes."""
from pathlib import Path
import hashlib
import json
import math
import stat
import struct

MARKER = 'PASS P2_BLANK_CARD_UI slots_fresh=3 campaign_generations=0 field_entered=0 actors=0 native_ui=1'
DATA_NAME = 'Pikmin dataFile'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def checked_path(path):
    """Reject aliases before resolving, including Windows junction ancestors."""
    path = Path(path).absolute()
    for part in (path, *path.parents):
        require(not part.is_symlink() and not part.is_junction(), f'Link/junction forbidden: {part}')
    return path.resolve()


def paths(canonical, session):
    canonical = checked_path(canonical)
    session = checked_path(session)
    output = checked_path(canonical / 'output')
    require(session != output and session.is_relative_to(output), 'Private output session required')
    card = checked_path(session / 'campaign' / 'card')
    require(card.is_relative_to(session), 'Card escaped session')
    return session, card


def preflight_new(canonical, session):
    session, card = paths(canonical, session)
    require(not session.exists(), 'New blank-card phase requires a nonexistent session')
    return session, card


def regular(path):
    path = checked_path(path)
    info = path.stat()
    require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1, f'Single-link regular file required: {path}')
    return path


def checksum(data):
    require(len(data) % 4 == 0, 'Checksum word alignment')
    total = 0x32546532
    for i, (word,) in enumerate(struct.iter_unpack('>I', data)):
        j = i & 255
        salt = (j << 24) | (((j + 1) & 255) << 16) | (((j - 1) & 255) << 8) | ((j + 2) & 255)
        total = (total + salt + word) & 0xffffffff
    return (0x32546532 - total) & 0xffffffff


def parse_blank(data):
    # Exact native layout: banner 0x2000, two option blocks, four game blocks.
    require(len(data) == 0x26000, 'Unexpected native card size')
    segments = [(0, 0x1ffc)] + [(0x2000 + i * 0x2000, 0x1ff8) for i in range(2)]
    segments += [(0x6000 + i * 0x8000, 0x7ff8) for i in range(4)]
    for offset, length in segments:
        checksum_offset = offset + length + (0 if offset == 0 else 4)
        require(checksum(data[offset:offset + length]) == struct.unpack_from('>I', data, checksum_offset)[0],
                f'Native checksum mismatch at {offset:#x}')
    headers = []
    for i, slot in enumerate((0, 1, 2, 0)):
        offset = 0x6000 + i * 0x8000
        status, actual_slot, day, parts = data[offset:offset + 4]
        require((status, actual_slot, day, parts) == (1, slot, 1, 0), 'Native slot is not Fresh')
        counts = struct.unpack_from('>iii', data, offset + 4)
        require(all(count in (-1, 0) for count in counts), 'Blank card has populated stock')
        headers.append(dict(status=status, slot=actual_slot, day=day, parts=parts, counts=list(counts)))
    return headers


def inventory(canonical, session):
    session, card = paths(canonical, session)
    campaign = checked_path(session / 'campaign')
    require(campaign.is_dir() and card.is_dir(), 'Native card backing missing')
    require(set(p.name for p in campaign.iterdir()) == {'card'}, 'Campaign state/checkpoint exists before SAVE')
    files = {}
    for entry in card.rglob('*'):
        checked_path(entry)
        if entry.is_dir():
            require(entry.relative_to(card).as_posix() in ('card0', 'card1'), 'Unexpected card subdirectory')
            continue
        regular(entry)
        files[entry.relative_to(card).as_posix()] = {'sha256': digest(entry), 'bytes': entry.stat().st_size}
    expected = {'card0/' + DATA_NAME, 'card0/.meta_' + DATA_NAME}
    require(set(files) == expected, 'Unexpected/missing native card files')
    require(0 < files['card0/.meta_' + DATA_NAME]['bytes'] <= 4096, 'Invalid native card metadata size')
    headers = parse_blank((card / 'card0' / DATA_NAME).read_bytes())
    return dict(card_root=str(card), files=files, physical_fresh=4, logical_fresh=3, headers=headers)


def completion(result, log):
    require(result.get('passed') is True and result.get('launched', True) is True, 'Initialization did not pass')
    require(type(result.get('exit_code')) is int and result['exit_code'] == 0
            and result.get('timed_out') is False, 'Initialization failed/timed out')
    require(type(result.get('timeout_seconds')) is int and result['timeout_seconds'] == 60, 'Wrong initialization time bound')
    elapsed = result.get('elapsed_seconds')
    require(type(elapsed) in (int, float) and math.isfinite(elapsed) and 0 < elapsed <= 60,
            'Initialization elapsed time outside bound')
    require(log.splitlines().count(MARKER) == 1, 'Exactly one anchored native completion required')
    require(sum(line.startswith('PASS P2_BLANK_CARD_UI') for line in log.splitlines()) == 1,
            'Ambiguous native completion')
    require('FAIL P2_BLANK_CARD_UI' not in log and 'P2_FIXTURE_CAPTAIN_DOWN' not in log,
            'Native refusal present')


def verify_prepared(canonical, session, receipt_path):
    session, card = paths(canonical, session)
    receipt_path = regular(receipt_path)
    require(receipt_path == session / 'blank-card-verified.json', 'Receipt must belong to exact session')
    receipt = json.loads(receipt_path.read_text(encoding='utf-8'))
    require(receipt.get('schema') == 'native-blank-card-v1' and receipt.get('accepted') is True, 'Unaccepted initialization')
    require(receipt.get('session') == str(session) and receipt.get('card_root') == str(card), 'Wrong backing path')
    require(receipt.get('campaign_generations') == 0 and receipt.get('native_ui') is True, 'Invalid initialization provenance')
    run = checked_path(session / 'blank-card-run')
    require(receipt.get('run') == str(run), 'Wrong initialization run')
    for name, expected in receipt['evidence'].items():
        require(name in {'native.log', 'run-result.json', 'run-inputs.json', 'blank-card-inputs.json'}, 'Unexpected evidence path')
        require(digest(regular(run / name)) == expected, 'Initialization evidence changed')
    require(set(receipt['evidence']) == {'native.log', 'run-result.json', 'run-inputs.json', 'blank-card-inputs.json'}, 'Incomplete evidence')
    result = json.loads((run / 'run-result.json').read_text())
    completion(result, (run / 'native.log').read_text(errors='replace'))
    inputs = json.loads((run / 'blank-card-inputs.json').read_text())
    require(inputs.get('session_absent_at_preflight') is True and inputs.get('card_root') == str(card), 'Missing fresh-path proof')
    environment = inputs.get('effective_private_environment', {})
    require(environment.get('NECTAR_SAVE_DIR') == str(card) and environment.get('PIKMIN_SHADER_CACHE') == '0',
            'Wrong card/shader-cache environment')
    require(inputs.get('argv') == [receipt['exe'], '--blank-card-root', str(card)], 'Wrong initialization argv')
    require(result.get('argv') == inputs['argv'], 'Observed argv differs from initialization plan')
    provenance = json.loads((run / 'run-inputs.json').read_text())
    require(provenance.get('exe') == receipt['exe'] and provenance.get('exe_sha256') == receipt.get('exe_sha256')
            and provenance.get('cwd') == str(run), 'Wrong native provenance')
    actual = inventory(canonical, session)
    require(actual == receipt['inventory'], 'Native blank card changed before SAVE')
    require(not (session / 'manifest.json').exists() and not (session / 'saved-observation.json').exists(), 'Session already started')
    require(not (session / 'prepared-card-consumed.json').exists(), 'Blank-card handoff already consumed')
    return receipt
