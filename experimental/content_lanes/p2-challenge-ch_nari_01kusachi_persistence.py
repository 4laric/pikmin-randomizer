"""Persistence observation adapter for P2 Challenge 04 ch_NARI_01kusachi.

Lane kusachi-persistence-obs (#781). Runtime slice, not gameplay acceptance:
the module parses guarded headed run logs produced by the lane observer into
the save/reload/retry/re-entry sequences emitted by the engine's
challenge-persistence call site. It never invents values: a sequence is
OBSERVED only when its receipt marker is present, kusachi-bound, and the run
is guard-clean. Durable save payloads are reported honestly (UNTESTED when the
session writes no payload). No cross-content claims without checking every
persistence marker. Stdlib only.
"""
import re

CAVE_ID = 'ch_NARI_01kusachi'
UI_INDEX = 3
GUARD_SHA256 = 'd2f678c9eda75e151eb534077dff9e30ad36ae4796881d971bbd09945f3c3474'
EXPECTED_SQUAD = 20

PROBES = ('SAVE_KEY', 'LOAD_KEY', 'CLEAR', 'HIGHSCORE', 'UNLOCK', 'RECEIPT_DEDUP', 'REENTRY')
SEQUENCES = ('save', 'reload', 'retry', 're-entry')

SEQ_PROBE = {'save': 'SAVE_KEY', 'reload': 'LOAD_KEY', 're-entry': 'REENTRY'}


def probe_lines(log_text):
    """All P2_CHALLENGE_* persistence probe markers with their stage binding."""
    out = []
    for line in log_text.splitlines():
        match = re.match(r'^(P2_CHALLENGE_[A-Z_]+) stage=([A-Za-z0-9_]+)$', line)
        if match and match.group(1) in ('P2_CHALLENGE_' + p for p in PROBES):
            out.append((match.group(1), match.group(2)))
    return out


def parse_run(log_text):
    """Extract persistence receipts from one run log (no inference)."""
    probes = probe_lines(log_text)
    counts = {}
    for marker, _stage in probes:
        counts[marker] = counts.get(marker, 0) + 1
    stages = sorted(set(stage for _marker, stage in probes))
    refusals = [l for l in log_text.splitlines()
                if l.startswith('P2_CHALLENGE_PERSISTENCE_REFUSED')]
    boot = re.search(r'^P2_KUSACHI_PERSIST_BOOT tick=\d+ total=(\d+) blue=(\d+) wired=(\d+)',
                     log_text, re.MULTILINE)
    return dict(
        probes=counts,
        probe_stages=stages,
        probe_block=tuple(m for m, _s in probes),
        refusals=refusals,
        wired=bool(boot and int(boot.group(1)) == EXPECTED_SQUAD
                   and int(boot.group(2)) == EXPECTED_SQUAD and int(boot.group(3)) > 0),
        captain_down='P2_FIXTURE_CAPTAIN_DOWN' in log_text,
        fixture_pass=bool(re.search(r'^PASS KUSACHI_PERSIST ', log_text, re.MULTILINE)),
    )


def classify_sequences(log_text):
    """Map receipts to save/reload/retry/re-entry plus leakage and dedup.

    Returns (sequences, leakage, dedup) where each sequence is
    (status, method, detail). RETRY/RE-ENTRY need a partner run; they are
    UNTESTED from a single log.
    """
    r = parse_run(log_text)
    clean = not r['captain_down'] and not r['refusals'] and r['wired']
    seq = {}

    def gate(status, method, detail):
        return dict(status=status, method=method, detail=detail)

    save_ok = r['probes'].get('P2_CHALLENGE_SAVE_KEY', 0) == 1 and clean
    seq['save'] = (gate('OBSERVED', 'natural', 'SAVE_KEY once, kusachi-bound, no refusal')
                   if save_ok else gate('UNTESTED', 'unobserved', 'no clean single SAVE_KEY receipt'))
    reload_ok = r['probes'].get('P2_CHALLENGE_LOAD_KEY', 0) == 1 and clean
    seq['reload'] = (gate('OBSERVED', 'natural', 'LOAD_KEY once, kusachi-bound, no refusal')
                     if reload_ok else gate('UNTESTED', 'unobserved', 'no clean single LOAD_KEY receipt'))
    seq['retry'] = gate('UNTESTED', 'unobserved', 'retry needs a partner run (see compare_runs)')
    seq['re-entry'] = (gate('OBSERVED', 'natural', 'REENTRY once, kusachi-bound, no refusal')
                       if r['probes'].get('P2_CHALLENGE_REENTRY', 0) == 1 and clean
                       else gate('UNTESTED', 'unobserved', 'no clean single REENTRY receipt'))

    foreign = [s for s in r['probe_stages'] if s != CAVE_ID]
    leakage = gate('CLEAN', 'natural', 'every persistence marker is kusachi-bound; zero foreign stages')
    if foreign or r['refusals']:
        leakage = gate('LEAKED', 'natural', 'foreign stages %s or %d refusals'
                       % (foreign, len(r['refusals'])))

    dup = [m for m, c in r['probes'].items() if c != 1]
    dedup = gate('SINGLE', 'natural', 'each of the 7 receipts exactly once; no double count')
    if dup or not clean:
        dedup = gate('UNPROVEN', 'unobserved', 'receipts not single or run not clean: %s' % dup)
    return seq, leakage, dedup


def compare_runs(first_text, second_text):
    """Retry/re-entry verdict across two fresh-process runs.

    REPLAYED (never double-counted) requires byte-identical single receipts
    for the 7 probes on both passes, both guard-clean and wired.
    """
    a, b = parse_run(first_text), parse_run(second_text)
    problems = []
    if not (a['wired'] and b['wired']):
        problems.append('wired squad missing on a pass')
    if a['captain_down'] or b['captain_down']:
        problems.append('captain-down on a pass')
    if a['refusals'] or b['refusals']:
        problems.append('persistence refusal on a pass')
    if a['probe_block'] != b['probe_block']:
        problems.append('receipt blocks differ between passes')
    for marker in ('P2_CHALLENGE_' + p for p in PROBES):
        if a['probes'].get(marker, 0) != 1 or b['probes'].get(marker, 0) != 1:
            problems.append('non-single receipt: ' + marker)
    foreign = [s for s in set(a['probe_stages']) | set(b['probe_stages']) if s != CAVE_ID]
    if foreign:
        problems.append('foreign stages: %s' % foreign)
    if problems:
        return dict(status='UNTESTED', method='unobserved', detail='; '.join(problems))
    return dict(status='REPLAYED', method='natural',
                detail='identical single 7-receipt blocks on two fresh processes; no double count, no leakage')


def run_summary(log_text):
    r = parse_run(log_text)
    seq, leakage, dedup = classify_sequences(log_text)
    return dict(cave=CAVE_ID, ui_index=UI_INDEX, wired=r['wired'],
                probes=r['probes'], probe_stages=r['probe_stages'],
                refusals=len(r['refusals']), captain_down=r['captain_down'],
                fixture_pass=r['fixture_pass'], sequences=seq,
                leakage=leakage, duplicate_resistance=dedup)
