import math
import pytest
from experimental.pikmin2_snow_turn import profile,step,install,TEXT

PARAMS='{\n{s000} 4 1\n{_eof}\n}\n{\n{fp06} 4 50\n{fp08} 4 0.4\n{fp28} 4 10\n{_eof}\n}\n{\n{fp01} 4 2\n{fp03} 4 180\n{_eof}\n}\n'

def test_source_mapping():
    result=profile(PARAMS)
    assert result['source_rotation_end_degrees']==180
    assert result['gain']==0.4
    with pytest.raises(ValueError):profile(PARAMS.replace('{fp03} 4 180','{fp03} 4 2'))

@pytest.mark.parametrize('target,expected',[(90,10),(-90,350),(10,4),(-10,356),(180,350)])
def test_signed_step(target,expected):
    angle,arrived=step(0,math.radians(target),0.01)
    assert math.degrees(angle)==pytest.approx(expected)
    assert not arrived

def test_wrap():
    angle,arrived=step(math.radians(359),math.radians(1),0.001)
    assert math.degrees(angle)==pytest.approx(359.8)

def test_existing_arrival_snap():
    angle,arrived=step(0,0.01,0.02)
    assert angle==0.01 and arrived
    _,arrived=step(0,0.02,0.02)
    assert not arrived

@pytest.mark.parametrize('values',[(0,math.nan,0.1),(math.inf,0,0.1),(0,0,-1),(0,0,math.inf)])
def test_invalid(values):
    with pytest.raises(ValueError):step(*values)

def test_converges_without_overshoot():
    angle=0
    for _ in range(100):
        next_angle,arrived=step(angle,math.pi/2,0.06)
        assert angle<=next_angle<=math.pi/2
        angle=next_angle
        if arrived:break
    assert arrived and angle==pytest.approx(math.pi/2)

def test_install(tmp_path):
    imported=tmp_path/'import';run=tmp_path/'run';imported.mkdir();run.mkdir();(imported/'p2-snow-turn.txt').write_text(TEXT)
    with pytest.raises(ValueError):install(imported,run)
    for name in ('p2-snow.txt','p2-snow-actors.txt'):(run/name).touch()
    install(imported,run);assert (run/'p2-snow-turn.txt').read_text()==TEXT

def test_large_finite_angles_normalize_safely():
    angle,arrived=step(1e308,-1e308,0.06)
    assert math.isfinite(angle) and 0<=angle<2*math.pi

def test_cap_is_per_call_not_time_scaled():
    one,_=step(0,math.pi/2,0.03)
    two,_=step(0,math.pi/2,0.06)
    assert one==two==pytest.approx(math.radians(10))

CPP_PROBE = r'''
#include "pc_p2_snow_turn_policy.h"
#include <cassert>
#include <sstream>
#include <limits>
int main(){
 constexpr float pi=3.14159265358979323846f;
 auto near=[](float a,float b){return std::fabs(a-b)<0.00001f;};
 auto r=P2SnowTurnPolicy::step(0,pi/2,0.06f);assert(r.valid&&!r.arrived&&near(r.direction,pi/18));
 r=P2SnowTurnPolicy::step(0,pi,0.06f);assert(near(r.direction,2*pi-pi/18));
 r=P2SnowTurnPolicy::step(0,pi/18,0.001f);assert(near(r.direction,0.4f*pi/18));
 r=P2SnowTurnPolicy::step(0,0.01f,0.06f);assert(r.arrived&&near(r.direction,0.01f));
 r=P2SnowTurnPolicy::step(0,0.06f,0.06f);assert(!r.arrived);
 r=P2SnowTurnPolicy::step(std::numeric_limits<float>::infinity(),0,0.06f);assert(!r.valid);
 r=P2SnowTurnPolicy::step(0,0,-1);assert(!r.valid);
 P2SnowTurnPolicy p;int snow=0,p1=0;assert(!p.evaluate(&snow,0,pi,0.06f,r));
 std::istringstream input("P2_SNOW_TURN_1 turn_profile source_snow");assert(p.read(input));p.bind(&snow);
 assert(p.evaluate(&snow,0,pi,0.06f,r)&&r.valid);assert(!p.evaluate(&p1,0,pi,0.06f,r));
 p.forget(&snow);assert(!p.evaluate(&snow,0,pi,0.06f,r));p.bind(&snow);p.reset();assert(!p.evaluate(&snow,0,pi,0.06f,r));
 std::istringstream input2("P2_SNOW_TURN_1 turn_profile source_snow");assert(p.read(input2));assert(!p.evaluate(&snow,0,pi,0.06f,r));
 std::istringstream bad("P2_SNOW_TURN_1 turn_profile source_snow extra");assert(!p.read(bad));
}
'''


def test_compiled_registry_and_math(tmp_path):
    import os,shutil,subprocess
    from pathlib import Path
    compiler=shutil.which('g++') or 'C:/msys64/mingw64/bin/g++.exe'
    if not Path(compiler).exists():pytest.skip('C++ compiler unavailable')
    source=tmp_path/'probe.cpp';exe=tmp_path/'probe.exe';source.write_text(CPP_PROBE)
    env=os.environ.copy();env['PATH']=str(Path(compiler).parent)+os.pathsep+env['PATH']
    subprocess.run([compiler,'-std=c++17','-I'+str(Path('native/pc_port').resolve()),str(source),'-o',str(exe)],check=True,capture_output=True,env=env)
    subprocess.run([str(exe)],check=True,capture_output=True,env=env)


def test_receiver_and_registry_wiring():
    from pathlib import Path
    receiver=Path('native/src/plugPikiNakata/tekibteki.cpp').read_text().split('bool BTeki::turnToward',1)[1].split('void BTeki::rotateTeki',1)[0]
    assert 'turnSpeed*NSystem::getFrameTime()' in receiver
    assert receiver.index('pc_p2_snow_turn')<receiver.index('f32 faceDir')
    registry=Path('native/pc_port/pc_p2_enemy.cpp').read_text()
    assert 'turnPolicy.forget(actor)' in registry and 'turnPolicy.reset()' in registry
    assert 'if(!actor->isAlive())return false' in registry
