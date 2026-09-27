"""Host-AI suppression wiring for 26 Catfish, 84 Hana, 27 Tadpole (#871).

Proves the rev6-misc5 Finding 1 fix: each of the three FSM modules exposes a
``pc_p2_<mod>_suppress_ai`` predicate (frog pattern: registered actor owns the
tick) and ``BTeki::doAI`` (src/plugPikiNakata/tekibteki.cpp) early-returns on
it, so the P1 host strategy ``act()`` never runs once the P2 FSM owns the
actor. Also pins that the host-blinding ``param_f`` hooks were already wired
through ``BTeki::getParameterF`` (include/teki.h) -- the review's "no caller"
claim missed that include seam -- and that the per-frame ``pc_p2_*_update``
drive hooks are wired in ``BTeki::update``.

They read the lane native worktree (a separate repo) by source text and skip
when it is absent; the C++ behavior itself is exercised by the private runtime
fixture (bot power campaign tag suppress-hosts), not by this unit suite.
"""
import os
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


def _native():
    """Return the lane native repo root, or None when no worktree is present.

    Discovery order: ``PIKMIN_NATIVE_ROOT`` (a native repo root, probed via its
    ``pc_port/`` subdir), ``P2_NATIVE_PC_PORT`` (pointing directly at a
    ``pc_port/`` dir), then ``ROOT/native/pc_port``.
    """
    root = os.environ.get('PIKMIN_NATIVE_ROOT')
    if root and (Path(root) / 'pc_port' / 'pc_p2_catfish.cpp').is_file():
        return Path(root).resolve()
    pc_port = os.environ.get('P2_NATIVE_PC_PORT')
    if pc_port and (Path(pc_port) / 'pc_p2_catfish.cpp').is_file():
        return Path(pc_port).resolve().parent
    candidate = ROOT / 'native' / 'pc_port'
    if (candidate / 'pc_p2_catfish.cpp').is_file():
        return candidate.resolve().parent
    return None


def _read(rel):
    native = _native()
    if native is None:
        return ''
    return (native / rel).read_text(errors='replace')


MODULES = ('catfish', 'hana', 'tadpole')


@unittest.skipUnless(_native(), 'lane native worktree not available')
class SuppressHostsWiringTests(unittest.TestCase):
    def test_suppress_predicates_declared(self):
        for mod in MODULES:
            header = _read(f'pc_port/pc_p2_{mod}.h')
            self.assertIn(f'pc_p2_{mod}_suppress_ai', header,
                          f'pc_p2_{mod}.h must declare the suppress predicate')

    def test_suppress_predicates_defined_frog_pattern(self):
        for mod in MODULES:
            text = _read(f'pc_port/pc_p2_{mod}.cpp')
            self.assertIn(f'bool pc_p2_{mod}_suppress_ai(const BTeki*', text,
                          f'pc_p2_{mod}.cpp must define the suppress predicate')
            # Frog pattern: suppression is exactly "registered actor owns the
            # tick" -- ready and present in the module's actor registry.
            self.assertIn('return ready && actors.count(', text,
                          f'pc_p2_{mod}_suppress_ai must mirror the frog pattern')

    def test_doai_early_return_chain(self):
        doai = _read('src/plugPikiNakata/tekibteki.cpp')
        for mod in MODULES:
            self.assertIn(f'if (pc_p2_{mod}_suppress_ai(this)) {{', doai,
                          f'doAI must early-return on pc_p2_{mod}_suppress_ai')

    def test_param_blinding_still_wired(self):
        teki = _read('include/teki.h')
        for mod in MODULES:
            self.assertIn(f'pc_p2_{mod}_param_f(', teki,
                          f'getParameterF must still chain pc_p2_{mod}_param_f')

    def test_update_drive_hooks_wired(self):
        update = _read('src/plugPikiNakata/tekibteki.cpp')
        for mod in MODULES:
            self.assertIn(f'pc_p2_{mod}_update(this);', update,
                          f'BTeki::update must drive pc_p2_{mod}_update')

    def test_update_drains_stored_damage(self):
        # State-machine-owns-actor assertion: the P1 TAI reaction path
        # (TaiDamagingAction) normally applies mStoredDamage through
        # makeDamaged(), but doAI is suppressed for registered actors, so
        # each source FSM must drain pending damage itself (frog pattern).
        for mod in MODULES:
            text = _read(f'pc_port/pc_p2_{mod}.cpp')
            self.assertIn('if (actor->mStoredDamage > 0.0f) {', text,
                          f'pc_p2_{mod}_update must drain pending damage')
            self.assertIn('actor->makeDamaged();', text,
                          f'pc_p2_{mod}_update must apply damage via makeDamaged')


if __name__ == '__main__':
    unittest.main()
