"""Campaign identity serialization and production C++ parser acceptance."""
import os
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from randomizer.purple_campaign import combat_profile

class CombatBindingsTests(unittest.TestCase):
    def test_actual_purple_state_entry_preserves_receiver_impulse(self):
        native = Path(os.environ.get('PIKMIN_NATIVE_SOURCE', Path(__file__).resolve().parents[1] / 'native'))
        compiler = shutil.which('g++')
        source = native / 'src/plugPikiNakata/taichappy.cpp'
        if not compiler or not source.exists():
            self.skipTest('Set PIKMIN_NATIVE_SOURCE and provide g++')
        text = source.read_text(encoding='utf-8')
        begin = text.index('// Dedicated Purple receiver:')
        end = text.index('setState(CHAPPYSTATE_P2PurpleImpact, state);', begin)
        factory = text[begin:end]
        # Compile the production action list and state-entry loop. The test
        # models only motion storage; live gravity/landing remain runtime gates.
        tai = (native/'src/plugPikiNakata/tai.cpp').read_text(encoding='utf-8')
        begin = tai.index('void TaiState::start(')
        entry = tai[begin:tai.index('\n}', begin)+2].replace('\r', '')
        move = (native/'src/plugPikiNakata/taimoveactions.cpp').read_text(encoding='utf-8')
        begin = move.index('void TaiStopMoveAction::start(')
        stop = move[begin:move.index('\n}', begin)+2]
        code = '''#include <cassert>
#include <vector>
struct Teki { float vy=245.f, driveY=245.f; void stopMove(){vy=driveY=0.f;} };
struct TaiAction { virtual void start(Teki&){}; virtual ~TaiAction()=default; };
struct TaiStopMoveAction: TaiAction { void start(Teki&) override; };
struct TaiState {
    int mCount; std::vector<TaiAction*> mActions;
    TaiState(int count):mCount(count),mActions(count,nullptr){}
    void setAction(int index,TaiAction* action){mActions.at(index)=action;}
    void start(Teki&);
};
''' + entry + '\n' + stop + '''
int main(){
    TaiAction damage, death, press, smash, purple;
    TaiStopMoveAction stopAction;
    TaiAction *simDamage=&damage, *dead1=&death, *pressed=&press,
              *chappySmashed=&smash, *purpleImpact=&purple, *stopMove=&stopAction;
    (void)stopMove;
    TaiState* state=nullptr; int j=0;
''' + factory + '''
    assert(j==state->mCount);
    Teki actor; state->start(actor);
    assert(actor.vy==245.f && actor.driveY==245.f);
    assert(state->mCount==5);
    assert(state->mActions[0]==simDamage && state->mActions[1]==dead1);
    assert(state->mActions[2]==pressed && state->mActions[3]==chappySmashed);
    assert(state->mActions[4]==purpleImpact);
    delete state;
}
'''
        with tempfile.TemporaryDirectory() as tmp:
            probe = Path(tmp)/'entry.cpp'
            exe = Path(tmp)/'entry.exe'
            probe.write_text(code, encoding='utf-8')
            subprocess.run([compiler, '-std=c++17', '-Wall', '-Wextra', '-Werror', str(probe), '-o', str(exe)], check=True, capture_output=True)
            subprocess.run([str(exe)], check=True, capture_output=True)

    def test_production_health_accessors_adjust_registered_base_pointer(self):
        native = Path(os.environ.get('PIKMIN_NATIVE_SOURCE', Path(__file__).resolve().parents[1] / 'native'))
        compiler = shutil.which('g++')
        source = native / 'pc_port/pc_p2_chappy.cpp'
        if not compiler or not source.exists():
            self.skipTest('Set PIKMIN_NATIVE_SOURCE and provide g++')
        # Execute the actual production accessor bodies, rather than a copied
        # lookup. The small model isolates C++ multiple-inheritance adjustment;
        # real BTeki engine behavior remains a separate runtime fixture gate.
        text = source.read_text(encoding='utf-8')
        bodies = []
        for name in ('pc_p2_chappy_max_health', 'pc_p2_chappy_param_f'):
            start = text.index('float ' + name + '(')
            end = text.index('\n}', start) + 2
            bodies.append(text[start:end])
        accessors = '\n'.join(bodies)
        params = sorted(set(re.findall(r'\bTPF_\w+', accessors)))
        code = '''#include "pc_p2_chappy_policy.h"
#include <cassert>
struct Creature { virtual ~Creature()=default; int payload=1; };
struct PelletView { virtual ~PelletView()=default; int payload=2; };
struct BTeki : Creature, PelletView {};
p2chappy::Health health;
std::map<PelletView*, int> actors;
bool bankLoaded=true;
enum { ''' + ','.join(params) + ' };\n' + accessors + '''
int main() {
    BTeki actor, unregistered;
    auto* view=static_cast<PelletView*>(&actor);
    assert(static_cast<const void*>(&actor)!=static_cast<const void*>(view));
    assert(health.bind(view,750.f)); actors.emplace(view,1);
    assert(pc_p2_chappy_max_health(&actor,1100.f)==750.f);
    assert(pc_p2_chappy_param_f(&actor,TPF_Life,1200.f)==750.f);
    assert(pc_p2_chappy_param_f(&actor,TPF_LifeRecoverRate,.25f)==0.f);
    assert(pc_p2_chappy_max_health(&unregistered,1300.f)==1300.f);
    assert(pc_p2_chappy_param_f(&unregistered,TPF_Life,1400.f)==1400.f);
    health.forget(view); actors.erase(view);
    assert(pc_p2_chappy_max_health(&actor,1500.f)==1500.f);
    assert(pc_p2_chappy_param_f(&actor,TPF_Life,1600.f)==1600.f);
    assert(pc_p2_chappy_param_f(&actor,TPF_LifeRecoverRate,.25f)==.25f);
}
'''
        with tempfile.TemporaryDirectory() as tmp:
            probe = Path(tmp) / 'health.cpp'
            exe = Path(tmp) / 'health.exe'
            probe.write_text(code, encoding='utf-8')
            subprocess.run([compiler, '-std=c++17', '-Wall', '-Wextra', '-Werror', '-I', str(native/'pc_port'), str(probe), '-o', str(exe)], check=True, capture_output=True)
            subprocess.run([str(exe)], check=True, capture_output=True)

    def test_exact_species_deterministic_uid_order(self):
        rows = [dict(target='300', source_id=33, enum_name='FireChappy'),
                dict(target='200', source_id=2, enum_name='Chappy'),
                dict(target='100', source_id=1, enum_name='Kochappy')]
        expected = b'P2_PURPLE_DIRECT_2\nbindings 2\n100 1\n200 2\n'
        self.assertEqual(combat_profile({'p2_layout': {'bindings': rows}}), expected)
        self.assertEqual(combat_profile({'p2_layout': {'bindings': rows[::-1]}}), expected)
        self.assertEqual(combat_profile({'p2_layout': {'bindings': []}}), b'P2_PURPLE_DIRECT_2\nbindings 0\n')

    def test_reject_ambiguous_or_wrong_identity(self):
        good = dict(target='10', source_id=2, enum_name='Chappy')
        for change in [dict(target='010'), dict(target='0'), dict(target='4294967296'),
                       dict(target=10), dict(target='-1'), dict(source_id=True), dict(enum_name='FireChappy')]:
            with self.subTest(change=change), self.assertRaises(ValueError):
                combat_profile({'p2_layout': {'bindings': [dict(good, **change)]}})
        with self.assertRaises(ValueError):
            combat_profile({'p2_layout': {'bindings': [good, good]}})

    def test_production_binding_policy(self):
        native = Path(os.environ.get('PIKMIN_NATIVE_SOURCE', Path(__file__).resolve().parents[1] / 'native'))
        compiler = shutil.which('g++')
        source = native / 'tools/test_p2_purple_combat_bindings.cpp'
        if not compiler or not source.exists():
            self.skipTest('Set PIKMIN_NATIVE_SOURCE and provide g++')
        with tempfile.TemporaryDirectory() as tmp:
            exe = Path(tmp) / 'bindings.exe'
            subprocess.run([compiler, '-std=c++17', '-Wall', '-Wextra', '-Werror', '-I', str(native/'pc_port'), str(source), '-o', str(exe)], check=True, capture_output=True)
            subprocess.run([str(exe)], check=True, capture_output=True)
