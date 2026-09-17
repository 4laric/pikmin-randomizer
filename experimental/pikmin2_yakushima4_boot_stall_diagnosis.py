"""Boot-stall classifier for the yakushima4 guarded cave runs (#671).

Reads one native boot log and reports which failure mode it shows, with
line numbers, so the silent pre-stage stall can be told apart from the
later entry refusal and the historical font crash. Nothing here runs a
binary, touches assets, or claims gameplay: pure read-only log
observation with fail-closed unknowns.
"""
import argparse
import json
import re
from pathlib import Path

GUARDED_WINDOW = 'P2_CAVE_GUARDED_WINDOW'
AUDIO_TAIL = 'NextOS DSP'
DVD_READ = 'DVDOpen('
DVD_FAILED = 'FAILED to open'
MEMSTAT = 'memStat:'
GAMEFLOW_BURST = 'took 0.2 secs'
CAVE_READY = 'P2_CAVE_READY'
GENERATE_PASS = 'P2_CAVE_GENERATE_PASS'
GUARDED_PASS = 'PASS CAVE_GUARDED_BOOT'
ENTRY_REFUSAL = 'Invalid P2 cave entry:'
SEGFAULT_FONT = 'Font::setTexture'
WIN_ERROR = 'WinError'

VERDICTS = ('silent-stall-post-audio', 'entry-refused', 'crash-font-segfault',
            'progressed', 'no-boot-markers', 'unknown')


def _lines(text):
    if not isinstance(text, str):
        raise ValueError('Boot log text required')
    return text.splitlines()


def last_marker_line(lines, token):
    """1-based line number of the last line containing token, else None."""
    found = None
    for number, line in enumerate(lines, 1):
        if token in line:
            found = number
    return found


def failed_reads(lines):
    """(line_number, line) for DVD FAILED and WinError read failures."""
    hits = []
    for number, line in enumerate(lines, 1):
        if DVD_FAILED in line or WIN_ERROR in line:
            hits.append((number, line.strip()[:200]))
    return hits


def entry_refusal_detail(lines):
    """Parse an Invalid P2 cave entry refusal, else None."""
    for number, line in enumerate(lines, 1):
        if ENTRY_REFUSAL in line:
            reason = line.split(ENTRY_REFUSAL, 1)[1].strip()[:160]
            return {'line': number, 'reason': reason,
                    'text': line.strip()[:200]}
    return None


def stall_bracket(lines):
    """Bound the silent region: last audio marker vs first missing stage."""
    audio = last_marker_line(lines, AUDIO_TAIL)
    dvd_after = None
    if audio is not None:
        for number in range(audio + 1, len(lines) + 1):
            if DVD_READ in lines[number - 1]:
                dvd_after = number
                break
    return {'audio_tail_line': audio,
            'first_dvd_read_after_audio': dvd_after,
            'memstat_line': last_marker_line(lines, MEMSTAT),
            'gameflow_burst_line': last_marker_line(lines, 'free : '),
            'cave_ready_line': last_marker_line(lines, CAVE_READY)}


def check_asset_record(entry):
    """Validate a pinned asset-input record shape (no ISO touched)."""
    if not isinstance(entry, dict):
        raise ValueError('Asset record must be a mapping')
    for field in ('member', 'offset', 'size', 'sha256'):
        if field not in entry:
            raise ValueError('Asset record lacks ' + field)
    if not isinstance(entry['member'], str) or not entry['member'].strip():
        raise ValueError('Asset member path required')
    for field in ('offset', 'size'):
        value = entry[field]
        if not isinstance(value, int) or value < 0:
            raise ValueError('Asset ' + field + ' must be a nonnegative int')
    digest = entry['sha256']
    if (not isinstance(digest, str)
            or not re.fullmatch(r'[0-9a-f]{64}', digest)):
        raise ValueError('Asset sha256 must be 64 hex chars')
    return True


def classify_boot_log(text):
    """Classify one boot log; never invents a verdict for unknown input."""
    lines = _lines(text)
    if not any(GUARDED_WINDOW in line for line in lines):
        return {'verdict': 'no-boot-markers',
                'detail': 'no guarded-window marker; not a guarded boot log'}
    if (any(SEGFAULT_FONT in line for line in lines) and any('SIGSEGV' in line for line in lines)):
        return {'verdict': 'crash-font-segfault',
                'detail': 'GDB stop in Font::setTexture during initialise'}
    refusal = entry_refusal_detail(lines)
    if refusal is not None:
        return {'verdict': 'entry-refused',
                'detail': 'cave entry validation refused execution',
                'refusal': refusal}
    ready = last_marker_line(lines, CAVE_READY) is not None
    generate = last_marker_line(lines, GENERATE_PASS) is not None
    passed = last_marker_line(lines, GUARDED_PASS) is not None
    if ready or generate or passed:
        return {'verdict': 'progressed',
                'detail': 'stage markers observed; not the silent stall',
                'ready': ready, 'generate': generate, 'passed': passed}
    bracket = stall_bracket(lines)
    if bracket['audio_tail_line'] is not None:
        return {'verdict': 'silent-stall-post-audio',
                'detail': 'boot ends after audio init with no DVD burst, '
                          'no memstat/gameflow stage and no cave markers',
                'bracket': bracket,
                'failed_reads': failed_reads(lines)}
    return {'verdict': 'unknown',
            'detail': 'guarded window present but no classifiable tail'}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--log', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        text = args.log.read_text(encoding='utf-8', errors='replace')
    except OSError:
        raise SystemExit('cannot read log: ' + str(args.log))
    print(json.dumps(classify_boot_log(text), indent=1))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
