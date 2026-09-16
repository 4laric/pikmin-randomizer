"""Source-presence gate for the lane 12 slice-3b captain acceptance markers.

Reads the native tree sources without compiling. A marker is only a failure
when its file is present in some tree but the marker is absent; if the file is
absent everywhere, we skip.
"""
import os
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _native_roots():
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


def _function_body(text, signature):
    """Return the text from the line holding ``signature`` through its body.

    Brace matching delimits the definition, so a marker inside the function
    is caught even when a later function reuses the same identifier.
    """
    lines = text.splitlines()
    start = None
    for index, line in enumerate(lines):
        if signature in line:
            start = index
            break
    if start is None:
        return None
    depth = 0
    seen_open = False
    for index in range(start, len(lines)):
        depth += lines[index].count('{') - lines[index].count('}')
        if '{' in lines[index]:
            seen_open = True
        if seen_open and depth <= 0:
            return '\n'.join(lines[start:index + 1])
    return '\n'.join(lines[start:])


def test_second_captain_render_open():
    roots = _native_roots()
    copies = [root / 'src' / 'plugPikiKando' / 'navi.cpp' for root in roots
              if (root / 'src' / 'plugPikiKando' / 'navi.cpp').is_file()]
    if not copies:
        pytest.skip('navi.cpp not present in any tree')
    # Only the preferred tree (PIKMIN_NATIVE_ROOT first); the exported engine/
    # mirror may lag until lane 01 re-exports.
    for path in copies[:1]:
        body = _function_body(path.read_text(errors='replace'),
                              'void Navi::refresh(')
        assert body is not None, f'{path}: Navi::refresh definition not found'
        assert 'mNaviID != 0' not in body, (
            f'{path}: Navi::refresh still defers the second captain render '
            f'(mNaviID != 0 guard present)')


def test_live_gate_default_on():
    roots = _native_roots()
    copies = [root / 'pc_port' / 'pc_p2_second_captain.cpp' for root in roots
              if (root / 'pc_port' / 'pc_p2_second_captain.cpp').is_file()]
    if not copies:
        pytest.skip('pc_p2_second_captain.cpp not present in any tree')
    # Only the preferred tree (PIKMIN_NATIVE_ROOT first).
    for path in copies[:1]:
        body = _function_body(path.read_text(errors='replace'),
                              'second_captain_live_allowed(')
        assert body is not None, (
            f'{path}: second_captain_live_allowed definition not found')
        assert 'return true;' in body, (
            f'{path}: second_captain_live_allowed does not default the live '
            f'gate on')
        assert 'second_captain_live_requested()' not in body, (
            f'{path}: second_captain_live_allowed still returns '
            f'second_captain_live_requested()')


def test_mamuta_natural_bury_integrated():
    roots = _native_roots()
    navi = [root / 'src' / 'plugPikiKando' / 'navi.cpp' for root in roots
            if (root / 'src' / 'plugPikiKando' / 'navi.cpp').is_file()]
    rules = [root / 'pc_port' / 'pc_p2_mamuta_rules.cpp' for root in roots
             if (root / 'pc_port' / 'pc_p2_mamuta_rules.cpp').is_file()]
    if not navi and not rules:
        pytest.skip('mamuta bury integration sources not present in any tree')
    for path in navi[:1]:
        text = path.read_text(errors='replace')
        assert 'InteractBury::actNavi' in text, (
            f'{path}: missing InteractBury::actNavi')
        assert 'pc_p2_mamuta_bury_navi(' in text, (
            f'{path}: missing pc_p2_mamuta_bury_navi call')
    for path in rules[:1]:
        text = path.read_text(errors='replace')
        assert 'pc_p2_mamuta_bury_navi' in text, (
            f'{path}: missing pc_p2_mamuta_bury_navi')
