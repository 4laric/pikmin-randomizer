import os
from pathlib import Path
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]

SOURCE = r'''
#include "pc_p2_kochappy_fsm_policy.h"
#include <cassert>
#include <cmath>
#include <sstream>
#include <string>

using namespace p2kochappyfsm;

static bool rejected(const char* text, Params& out)
{
    out = Params{};
    std::istringstream in(text);
    const bool ok = parseConfig(in, out);
    // A rejected config must not partially overwrite the caller's values.
    assert(ok || (out.health == 250.0f && out.moveSpeed == 60.0f));
    return !ok;
}

int main()
{
    Params defaults;
    assert(defaults.health == 250.0f && defaults.moveSpeed == 60.0f && defaults.sight == 95.0f);
    assert(defaults.attackRange == 30.0f && defaults.attackAngle == 20.0f);
    assert(defaults.attackHitRange == 35.0f && defaults.attackDamage == 10.0f);
    assert(defaults.homeRadius == 80.0f && defaults.territory == 500.0f);
    assert(defaults.privateRadius == 70.0f);
    assert(defaults.eatRange == 35.0f && defaults.poisonDamage == 300.0f);

    assert(std::string(stateName(STATE_WAIT)) == "wait");
    assert(std::string(stateName(STATE_DEAD)) == "dead");
    assert(std::string(stateName(STATE_TURN)) == "turn");
    assert(std::string(stateName(STATE_WALK)) == "walk");
    assert(std::string(stateName(STATE_ATTACK)) == "attack");
    assert(std::string(stateName(STATE_FLICK)) == "flick");
    assert(std::string(stateName(STATE_TURN_TO_HOME)) == "turn_to_home");
    assert(std::string(stateName(STATE_GO_HOME)) == "go_home");
    assert(std::string(stateName(STATE_PRESS)) == "press");
    assert(std::string(stateName(static_cast<State>(99))) == "null");
    assert(STATE_COUNT == 9);
    assert(STATE_WAIT == 0 && STATE_DEAD == 1 && STATE_TURN == 2 && STATE_WALK == 3
           && STATE_ATTACK == 4 && STATE_FLICK == 5 && STATE_TURN_TO_HOME == 6
           && STATE_GO_HOME == 7 && STATE_PRESS == 8);

    Params parsed;
    std::istringstream magic("P2_DWARF_ORANGE_FSM_1");
    assert(parseConfig(magic, parsed));
    assert(parsed.health == 250.0f && parsed.sight == 95.0f);

    std::istringstream full("P2_DWARF_ORANGE_FSM_1 health 250 move_speed 60 sight 95"
                            " attack_range 30 attack_angle 20 attack_hit_range 35"
                            " attack_damage 10 home_radius 80 territory 500 private_radius 70"
                            " eat_range 35 poison_damage 300");
    assert(parseConfig(full, parsed));
    assert(parsed.health == 250.0f && parsed.moveSpeed == 60.0f && parsed.sight == 95.0f);
    assert(parsed.attackRange == 30.0f && parsed.attackAngle == 20.0f);
    assert(parsed.attackHitRange == 35.0f && parsed.attackDamage == 10.0f);
    assert(parsed.homeRadius == 80.0f && parsed.territory == 500.0f && parsed.privateRadius == 70.0f);
    assert(parsed.eatRange == 35.0f && parsed.poisonDamage == 300.0f);

    Params scratch;
    for (const char* bad : {
             "",
             "P2_SNOW_POLICY_1 health 250",
             "P2_DWARF_ORANGE_FSM_2 health 250",
             "P2_DWARF_ORANGE_FSM_1 unknown 1",
             "P2_DWARF_ORANGE_FSM_1 health 250 health 250",
             "P2_DWARF_ORANGE_FSM_1 health",
             "P2_DWARF_ORANGE_FSM_1 health nan",
             "P2_DWARF_ORANGE_FSM_1 health -5",
             "P2_DWARF_ORANGE_FSM_1 health 0",
             "P2_DWARF_ORANGE_FSM_1 move_speed 0",
             "P2_DWARF_ORANGE_FSM_1 move_speed -1",
             "P2_DWARF_ORANGE_FSM_1 attack_angle 0",
             "P2_DWARF_ORANGE_FSM_1 attack_angle 181",
             "P2_DWARF_ORANGE_FSM_1 attack_damage -1",
             "P2_DWARF_ORANGE_FSM_1 sight 1e9",
             "P2_DWARF_ORANGE_FSM_1 eat_range 0",
             "P2_DWARF_ORANGE_FSM_1 eat_range -1",
             "P2_DWARF_ORANGE_FSM_1 poison_damage -1",
             "P2_DWARF_ORANGE_FSM_1 poison_damage nan",
             "P2_DWARF_ORANGE_FSM_1 health 250 extra 1",
             "P2_DWARF_ORANGE_FSM_1 sight 95 trailing",
         }) {
        assert(rejected(bad, scratch));
    }
    return 0;
}
'''


@pytest.mark.parametrize('name', ['pc_p2_kochappy_fsm_policy.h'])
def test_compiled_fsm_policy(tmp_path, name):
    compiler = shutil.which('g++') or ('C:/msys64/mingw64/bin/g++.exe'
                                       if Path('C:/msys64/mingw64/bin/g++.exe').exists() else None)
    candidates = [ROOT / 'native' / 'pc_port']
    if os.environ.get('PIKMIN_NATIVE_ROOT'):
        candidates.insert(0, Path(os.environ['PIKMIN_NATIVE_ROOT']) / 'pc_port')
    if os.environ.get('P2_NATIVE_PC_PORT'):
        candidates.insert(0, Path(os.environ['P2_NATIVE_PC_PORT']))
    include = next((c for c in candidates if (c / name).is_file()), None)
    if compiler is None or include is None:
        pytest.skip('reference native pc_port or C++ compiler unavailable')
    source = tmp_path / 'policy.cpp'
    exe = tmp_path / ('policy.exe' if os.name == 'nt' else 'policy')
    source.write_text(SOURCE, encoding='utf-8')
    env = os.environ.copy()
    env['PATH'] = str(Path(compiler).parent) + os.pathsep + env.get('PATH', '')
    subprocess.run([compiler, '-std=c++17', '-I' + str(include), str(source), '-o', str(exe)],
                   check=True, capture_output=True, env=env)
    subprocess.run([str(exe)], check=True, capture_output=True, env=env)
