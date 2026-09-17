"""Waterwraith99 placement/bind carrier landing helpers (issue #657).

Recovery producer for exhausted provider-placement-catalog request 1f85c9b6.
Additive stdlib-only checks that verify the three exact carrier pins are
present at exact bytes and consistent with each other. Root-only tooling: no
builds, no runtime, no shared-file edits, no ADMIT. All six arena gates stay
UNTESTED. The native carrier pin is recorded for the integrator and is never
merged by this slice.
"""
import hashlib
import subprocess

SCHEMA = 1

CATALOG_PIN = '7a21ce6af09dcc6d4807a7f09cbec333f1e6b088'
CATALOG_BLOB = '96ddeb89b11e678de1365856db3f5317cc6e5258'
CATALOG_PATH = 'randomizer/p2_placement_catalog.py'
CATALOG_MARKERS = ('WATERWRAITH_CANDIDATE_SPEC', '568677317')

PACKAGING_PIN = '04d58d33af3336ba5190d49ca4856a7d96c4b0f2'
PACKAGING_BLOB = '7f45258825a3dfa0cb7f8dc2cc9b53f91627528e'
PACKAGING_PATH = 'experimental/pikmin2_muse_packaging.py'
PACKAGING_MARKERS = ('BlackMan99', 'Tyre98')

NATIVE_PIN = 'e2aa476ec7795cdbec69083d3d6e6a9329c4743b'
NATIVE_FILES = {
    'pc_port/pc_p2_generated_placement.cpp':
        '1cf80986f5725425b704f7c95af191734e14346a',
    'pc_port/pc_p2_generated_placement.h':
        '1a58c002b9a379f779c021ace09e3577f91219b7',
    'tools/p2_waterwraith_placement_provider_test.cpp':
        '886857fa3a3eacace4367f3f80ac6d923678ed95',
}

CANDIDATE_BASE = '36b868391e62cccf37d992aa2f796f3cc9c6dc31'


class CarrierRejected(ValueError):
    """Missing or divergent carrier evidence; never a placement."""


def sha256_bytes(data):
    if not isinstance(data, (bytes, bytearray)) or not data:
        raise CarrierRejected('nonempty bytes required')
    return hashlib.sha256(bytes(data)).hexdigest()


def check_markers(text, markers, label):
    """Require every marker substring; fail closed on missing/divergent text."""
    if not isinstance(text, str) or not text:
        raise CarrierRejected(label + ': text required')
    missing = [m for m in markers if m not in text]
    if missing:
        raise CarrierRejected(label + ': missing markers: ' + ', '.join(missing))
    return dict(label=label, markers=list(markers), present=True)


def check_carrier_text(path, text, expected_blob, markers):
    """Verify exact bytes plus consistency markers for one carrier file."""
    digest = sha256_bytes(text.encode('utf-8') if isinstance(text, str) else text)
    if digest != expected_blob:
        raise CarrierRejected('%s: blob %s differs from pinned %s' % (path, digest, expected_blob))
    _ng = check_markers(text if isinstance(text, str) else text.decode('utf-8', 'replace'), markers, path)
    return dict(path=path, sha256=digest, pinned=True, markers=_ng['markers'])


def check_catalog_packaging_consistency(catalog_text, packaging_text):
    """Cross-check the two root carriers reference the same slot 99 scope."""
    for text, markers, label in ((catalog_text, CATALOG_MARKERS, 'catalog'),
                                 (packaging_text, PACKAGING_MARKERS, 'packaging')):
        check_markers(text, markers, label)
    if '99' not in catalog_text or '99' not in packaging_text:
        raise CarrierRejected('carriers do not share the slot-99 scope')
    return dict(scope='slot-99', consistent=True)


def git_blob(repo, rev, path):
    """Read one exact blob hash; fail closed on missing objects."""
    proc = subprocess.run(['git', '-C', repo, 'rev-parse', rev + ':' + path],
                          capture_output=True, text=True)
    if proc.returncode != 0:
        raise CarrierRejected('missing object %s:%s' % (rev, path))
    return proc.stdout.strip()


def check_ancestry(repo, ancestor, descendant):
    """Require ancestor history; fail closed instead of assuming lineage."""
    proc = subprocess.run(['git', '-C', repo, 'merge-base', '--is-ancestor', ancestor, descendant],
                          capture_output=True, text=True)
    if proc.returncode != 0:
        raise CarrierRejected('%s is not an ancestor of %s' % (ancestor, descendant))
    return True


def landable_packet(candidate_commits, candidate_head):
    """Assemble the integrator packet skeleton with exact pins."""
    return dict(schema=SCHEMA, candidate_base=CANDIDATE_BASE,
                candidate_commits=list(candidate_commits), candidate_head=candidate_head,
                carriers={'catalog': {'pin': CATALOG_PIN, 'blob': CATALOG_BLOB, 'path': CATALOG_PATH},
                          'packaging': {'pin': PACKAGING_PIN, 'blob': PACKAGING_BLOB,
                                        'path': PACKAGING_PATH},
                          'native_recorded_only': {'pin': NATIVE_PIN, 'files': dict(NATIVE_FILES)}},
                downstream=['#572', 'recovery f42ecca0', '#575/#576'],
                limitations=['Root-only slice: the native carrier pin is recorded, never merged.',
                             'No runtime claim; all six arena gates UNTESTED.'])
