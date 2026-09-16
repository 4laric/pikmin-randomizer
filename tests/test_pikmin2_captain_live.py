"""Live-source seam gate for the lane 12 slot-0 captain/squad adapter.

Reads the native tree sources (pc_port/ and src/plugPikiKando/) without
compiling, so CI catches a missing LIVE seam that the exported engine/ mirror
may not yet carry. A marker is only a failure when its file is present in some
tree but the marker is absent; if the file is absent everywhere, we skip.
"""
import os
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _tree_roots():
    roots = []
    env_root = os.environ.get('PIKMIN_NATIVE_ROOT', '')
    if env_root:
        roots.append(Path(env_root))
    for candidate in (ROOT / 'native', ROOT / 'engine'):
        if candidate.is_dir():
            roots.append(candidate)
    seen = set()
    ordered = []
    for root in roots:
        key = str(root.resolve())
        if key not in seen:
            seen.add(key)
            ordered.append(root)
    return ordered


def test_captain_live_hooks_present():
    roots = _tree_roots()
    checks = [
        ('pc_port/pc_p2_captain.cpp', [
            'setup_from_navi_mgr(', 'capture_captain(', 'capture_actor(',
            'drop_captured(', 'captain_handle(', 'pc_p2_captain_forget_piki(']),
        ('pc_port/pc_p2_captain.h', [
            'captain_handle(', 'captive_count(', 'navi_dead(',
            'pc_p2_captain_forget_piki(']),
        ('src/plugPikiKando/pikiMgr.cpp', [
            'pc_p2_captain_forget_piki(']),
        ('src/plugPikiKando/naviState.cpp', [
            'informOrimaDead(', 'getAliveOrima']),
        ('src/plugPikiKando/gameCoreSection.cpp', [
            'setup_from_navi_mgr(']),
    ]
    groups = []
    for rel, markers in checks:
        copies = [root / rel for root in roots if (root / rel).is_file()]
        if copies:
            groups.append((rel, markers, [c.read_text(errors='replace') for c in copies]))
    if not groups:
        pytest.skip('live captain/squad hook sources not present in any tree')
    for rel, markers, texts in groups:
        for marker in markers:
            assert any(marker in text for text in texts), (
                f'{rel}: missing live seam {marker!r}')


def test_live_adapter_setup_is_idempotent_source_check():
    roots = _tree_roots()
    headers = [root / 'pc_port' / 'pc_p2_captain.h'
               for root in roots if (root / 'pc_port' / 'pc_p2_captain.h').is_file()]
    sources = [root / 'pc_port' / 'pc_p2_captain.cpp'
               for root in roots if (root / 'pc_port' / 'pc_p2_captain.cpp').is_file()]
    if not headers or not sources:
        pytest.skip('native captain adapter idempotency sources not present')
    assert any('bound()' in h.read_text(errors='replace') for h in headers)
    assert any('if (adapter.bound()) return true;' in c.read_text(errors='replace')
               for c in sources)
