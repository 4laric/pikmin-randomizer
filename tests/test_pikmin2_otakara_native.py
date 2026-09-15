"""Tests for the lane-22 real actor-bound dweevil FSM (pc_p2_otakara).

These tests pin the source-faithful wiring and parameter facts of the native
module that turns the four elemental dweevils (FireOtakara 59, WaterOtakara 60,
GasOtakara 61, ElecOtakara 62) into real damageable enemies on the batch-2
Chappy placement vehicle, rather than the earlier pc_p2_dweevil sidecar
simulation. They read the lane native worktree (which is a separate repo) and
assert, by source text, that:

  * the FSM module and its per-species parameters (general life fp00 and
    attack fp24 from docs/PIKMIN2_DWEEVIL_ASSETS.md) are registered;
  * the additive hooks are actually wired (update, param_f, draw clip,
    lifetime forget/reset, setup, CMake);
  * BombOtakara (93) is left to the lane-20 Bomb contract and is not bound.

They complement the pure-policy tests in test_pikmin2_dweevil_native.py and
test_pikmin2_elemental_behavior.py; the C++ FSM itself is exercised by the
private runtime fixture, not by this unit suite.
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
    if root and (Path(root) / 'pc_port' / 'pc_p2_otakara.cpp').is_file():
        return Path(root).resolve()
    pc_port = os.environ.get('P2_NATIVE_PC_PORT')
    if pc_port and (Path(pc_port) / 'pc_p2_otakara.cpp').is_file():
        return Path(pc_port).resolve().parent
    candidate = ROOT / 'native' / 'pc_port'
    if (candidate / 'pc_p2_otakara.cpp').is_file():
        return candidate.resolve().parent
    return None


def _read(rel):
    native = _native()
    if native is None:
        return ''
    return (native / rel).read_text(errors='replace')


@unittest.skipUnless(_native(), 'lane native worktree not available')
class OtakaraNativeSourceTests(unittest.TestCase):
    def test_module_source_is_the_actor_fsm(self):
        text = _read('pc_port/pc_p2_otakara.cpp')
        self.assertIn('pc_p2_otakara_setup', text)
        self.assertIn('pc_p2_otakara_update', text)
        self.assertIn('pc_p2_otakara_forget', text)
        self.assertIn('pc_p2_otakara_param_f', text)
        # Actor binding, not the sidecar simulation: it drives the host by
        # generator ID and sets mHealth to the source life.
        self.assertIn('p2-dweevil-actors.txt', text)
        self.assertIn('p2-dweevil-bank.txt', text)
        self.assertIn('mHealth = s.life', text)

    def test_elemental_discharge_uses_real_receivers(self):
        text = _read('pc_port/pc_p2_otakara.cpp')
        for interaction in ('InteractFire', 'InteractBubble', 'InteractGas', 'InteractDenki'):
            self.assertIn(interaction, text)

    def test_immunity_is_lane_11_matrix(self):
        text = _read('pc_port/pc_p2_otakara.cpp')
        self.assertIn('p2_species_immune', text)
        self.assertIn('p2_emitter_accepts', text)

    def test_bombotakara_is_bound_payload_delegating(self):
        text = _read('pc_port/pc_p2_otakara.cpp')
        # Slice 4 binds all five; Bomb (93) maps to its ID but delegates its
        # element to the lane-20 payload (discharge emits P2_OTAKARA_DISCHARGE_NONE).
        self.assertIn('if (name == "BombOtakara") return p2dweevil::BombId;', text)
        self.assertIn('P2_OTAKARA_DISCHARGE_NONE', text)

    def test_source_parameters_match_disc_audit(self):
        text = _read('pc_port/pc_p2_otakara.cpp')
        # fp00 general life: Gas 350, others 150.
        self.assertIn('350.0f', text)
        self.assertIn(': 150.0f', text)
        # fp24 attack: Fire/Elec 10, Water/Gas/Bomb 0.
        self.assertIn('return 10.0f', text)

    def test_damage_attribution_wiring(self):
        text = _read('pc_port/pc_p2_otakara.cpp')
        self.assertIn('void pc_p2_otakara_attack', text)
        self.assertIn('interaction=%s attacker=%s', text)
        btk = _read('src/plugPikiNakata/tekibteki.cpp')
        self.assertIn('pc_p2_otakara_attack(this, attack->mOwner, "InteractAttack");', btk)
        self.assertIn('pc_p2_otakara_forget', _read('pc_port/pc_p2_teki_lifetime.cpp'))

    def test_host_seam_hooks(self):
        text = _read('pc_port/pc_p2_otakara.cpp')
        self.assertIn('void pc_p2_otakara_died', text)
        self.assertIn('bool pc_p2_otakara_receipt', text)
        self.assertIn('P2_OTAKARA_MODULE_DEAD', text)
        self.assertIn('P2_OTAKARA_FORGET generator=%u registered=1 count=%lu', text)
        die = _read('src/plugPikiNakata/tekibteki.cpp')
        self.assertIn('pc_p2_otakara_died(this)', die)
        preview = _read('pc_port/pc_p2_preview.cpp')
        self.assertIn('pc_p2_otakara_receipt(pellet->mPelletView', preview)

    def test_hook_wiring(self):
        teki = _read('include/teki.h')
        self.assertIn('#include "pc_p2_otakara.h"', teki)
        self.assertIn('pc_p2_otakara_param_f(', teki)

        btk = _read('src/plugPikiNakata/tekibteki.cpp')
        self.assertIn('pc_p2_otakara_update(this);', btk)

        batch2 = _read('pc_port/pc_p2_batch2.cpp')
        self.assertIn('pc_p2_otakara_clip(actor, forced, phase)', batch2)

        lifetime = _read('pc_port/pc_p2_teki_lifetime.cpp')
        self.assertIn('pc_p2_otakara_forget(actor);', lifetime)
        self.assertIn('pc_p2_otakara_reset();', lifetime)

        preview = _read('pc_port/pc_p2_preview.cpp')
        self.assertIn('pc_p2_otakara_setup();', preview)

        tekimgr = _read('src/plugPikiNakata/tekimgr.cpp')
        self.assertIn('pc_p2_otakara_reset();', tekimgr)

        cmake = _read('CMakeLists.txt')
        self.assertIn('pc_port/pc_p2_otakara.cpp', cmake)


class OtakaraPolicyConsistencyTests(unittest.TestCase):
    """Python-model / audit cross-checks (no native worktree required)."""
    def test_stimulus_mapping_matches_python_model(self):
        from experimental import pikmin2_elemental_behavior as eb
        expected = {
            59: 'InteractFire', 60: 'InteractBubble',
            61: 'InteractGas', 62: 'InteractDenki', 93: None,
        }
        for species, stimulus in expected.items():
            self.assertEqual(eb.dweevil_stimulus(
                {59: 'FireOtakara', 60: 'WaterOtakara', 61: 'GasOtakara',
                 62: 'ElecOtakara', 93: 'BombOtakara'}[species]), stimulus)

    def test_elemental_species_are_not_fixed_hazards(self):
        from experimental import pikmin2_elemental_behavior as eb
        # The four elemental dweevils are OtakaraBase creatures; Hiba is not.
        for species in ('FireOtakara', 'WaterOtakara', 'GasOtakara', 'ElecOtakara'):
            self.assertEqual(eb.dweevil_stimulus(species),
                             {'FireOtakara': 'InteractFire', 'WaterOtakara': 'InteractBubble',
                              'GasOtakara': 'InteractGas', 'ElecOtakara': 'InteractDenki'}[species])


if __name__ == '__main__':
    unittest.main()
