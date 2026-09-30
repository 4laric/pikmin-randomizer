"""Compiled input/policy/adapter regression; not a rendered gameplay claim."""
import subprocess

from test_pikmin2_captain_adapter import _compiler, _compile_env, _source_root


def test_captain_switch_controls(tmp_path):
    port, sources = _source_root('pc_p2_captain_switch_policy.h', 'test_p2_captain_switch.cpp')
    assert port is not None, 'captain switch candidate must be present'
    compiler = _compiler()
    assert compiler is not None, 'g++ is required for this acceptance check'
    exe = tmp_path / 'captain-switch.exe'
    subprocess.run([str(compiler), '-std=c++17', '-Wall', '-Wextra', '-Werror',
                    '-I', str(port), str(sources / 'test_p2_captain_switch.cpp'),
                    '-o', str(exe)], check=True, capture_output=True, text=True,
                   env=_compile_env(compiler))
    result = subprocess.run([str(exe)], capture_output=True, text=True, timeout=30,
                            env=_compile_env(compiler))
    assert result.returncode == 0, result.stderr
    assert 'PASS P2_CAPTAIN_SWITCH' in result.stdout


def test_live_switch_reconciles_camera_after_roster_update():
    port, _ = _source_root('pc_p2_captain_switch_policy.h', 'test_p2_captain_switch.cpp')
    assert port is not None
    glue = (port / 'pc_p2_captain.cpp').read_text(encoding='utf-8')
    manager = (port.parent / 'src/plugPikiKando/naviMgr.cpp').read_text(encoding='utf-8')
    update = manager.split('void NaviMgr::update()', 1)[1].split('\n}', 1)[0]
    assert update.index('MonoObjectMgr::update()') < update.index('update_player_switch()')
    reconcile = glue.split('void update_player_switch()', 1)[1].split('\nbool reload()', 1)[0]
    assert reconcile.index('p2_captain_bind_camera(*cameraMgr, *current)') < reconcile.index('if (!pressed')
    assert 'p2_captain_bind_camera(*cameraMgr, *next)' in reconcile
    navi = (port.parent / 'src/plugPikiKando/navi.cpp').read_text(encoding='utf-8')
    assert 'const bool mouseIsMine = pcCaptainOwnsInput(this, pc_window_get_keyboard_owner())' in navi
    assert 'const bool keyboardOwner = pcCaptainOwnsInput(navi, pc_window_get_keyboard_owner())' in navi
    lock = navi.split('void Navi::pcUpdateLockOn()', 1)[1]
    assert lock.index('!pcCaptainOwnsInput(this, 0)') < lock.index('pc_window_take_lockon_press()')
    camera = (port.parent / 'src/plugPikiNakata/pcamcamera.cpp').read_text(encoding='utf-8')
    assert 'p2_captain_camera_drag_player(pc_p2_captain::single_player_switch_enabled(), targetCaptain)' in camera
    assert 'pc_window_take_camera_drag_player(dragPlayer)' in camera


def test_ship_admission_uses_live_selected_survivor(tmp_path):
    """Compile the actual updateAI prefix, including its ship tick invocation."""
    port, _ = _source_root('pc_p2_captain_switch_policy.h', 'test_p2_captain_switch.cpp')
    assert port is not None
    source = (port.parent / 'src/plugPikiKando/gameCoreSection.cpp').read_text(encoding='utf-8')
    prefix = source[source.index('void GameCoreSection::updateAI()'):]
    prefix = prefix.split('    if (pc_randomizer_expanded())', 1)[0] + '}\n'
    harness = r'''
#include <cassert>
#include <cstdio>
struct Navi { float mHealth; };
struct NaviMgr { Navi* selected; Navi* getActiveNavi(){return selected;} };
NaviMgr* naviMgr;
struct Movie { bool mIsActive=false; } movie;
struct Flow { Movie* mMoviePlayer=&movie; bool mPauseAll=false, mIsUIOverlayActive=false; } gameflow;
struct Player { bool mInDayEnd=false; } player;
Player* playerState=&player;
void pc_p2_cave_tick(){} void pc_p2_giant_breadbug_actor_tick(){} void pc_p2_breadbug_actor_tick(){}
Navi* observed=nullptr; bool admitted=false;
void pc_p2_ship_tick(Navi* n,bool active){observed=n;admitted=active;}
struct GameCoreSection { Navi* mNavi; void updateAI(); };
''' + prefix + r'''
int main(){
    Navi primary{0},survivor{100};NaviMgr manager{&survivor};naviMgr=&manager;
    GameCoreSection section{&primary};section.updateAI();assert(observed==&survivor && admitted);
    primary.mHealth=1;section.updateAI();assert(admitted); // native down threshold
    survivor.mHealth=1;section.updateAI();assert(!admitted);
    survivor.mHealth=100;
    movie.mIsActive=true;section.updateAI();assert(!admitted);movie.mIsActive=false;
    gameflow.mPauseAll=true;section.updateAI();assert(!admitted);gameflow.mPauseAll=false;
    gameflow.mIsUIOverlayActive=true;section.updateAI();assert(!admitted);gameflow.mIsUIOverlayActive=false;
    player.mInDayEnd=true;section.updateAI();assert(!admitted);player.mInDayEnd=false;
    primary.mHealth=100;manager.selected=&primary;section.updateAI();assert(observed==&primary && admitted);
    naviMgr=nullptr;section.updateAI();assert(!observed && !admitted);
    std::puts("PASS selected survivor ship admission");
}
'''
    cpp = tmp_path / 'ship-admission.cpp'
    cpp.write_text(harness, encoding='utf-8')
    compiler = _compiler()
    assert compiler is not None
    exe = tmp_path / 'ship-admission.exe'
    subprocess.run([str(compiler), '-std=c++17', '-Wall', '-Wextra', '-Werror', str(cpp), '-o', str(exe)],
                   check=True, capture_output=True, text=True, env=_compile_env(compiler))
    result = subprocess.run([str(exe)], capture_output=True, text=True, timeout=30, env=_compile_env(compiler))
    assert result.returncode == 0, result.stderr
    assert 'PASS selected survivor ship admission' in result.stdout
