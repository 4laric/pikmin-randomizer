import math
import pytest
from experimental.pikmin2_snow_chase import profile,steer,install,TEXT

PARAMS='{\n{s000} 4 1\n{_eof}\n}\n{\n{fp06} 4 50\n{fp08} 4 0.4\n{fp28} 4 10\n{_eof}\n}\n{\n{fp03} 4 180\n{_eof}\n}\n'

def test_source_profile():
    assert profile(PARAMS)['speed']==50
    with pytest.raises(ValueError):profile(PARAMS.replace('4 50','4 60'))

def test_turn_before_velocity():
    angle,velocity=steer(0,math.pi/2,7)
    assert angle==pytest.approx(math.radians(10))
    assert velocity==pytest.approx((8.682408883,7,49.24038765))
    assert velocity[0]!=50 # P1's immediate direct-to-target heading.

@pytest.mark.parametrize('facing,target',[(0,0),(0,10),(0,180),(359,1),(10,350),(-90,90)])
def test_constant_horizontal_speed_and_y(facing,target):
    _,(x,y,z)=steer(math.radians(facing),math.radians(target),-13)
    assert math.hypot(x,z)==pytest.approx(50)
    assert y==-13

def test_chase_does_not_use_arrival_snap():
    angle,_=steer(0,0.01,0)
    assert angle==pytest.approx(0.004)

def test_per_update_sequence():
    angle=0
    for _ in range(3):angle,_=steer(angle,math.pi/2,0)
    assert math.degrees(angle)==pytest.approx(30)

@pytest.mark.parametrize('values',[(math.nan,0,0),(0,math.inf,0),(0,0,math.nan)])
def test_invalid(values):
    with pytest.raises(ValueError):steer(*values)

def test_install(tmp_path):
    imported=tmp_path/'import';run=tmp_path/'run';imported.mkdir();run.mkdir();(imported/'p2-snow-chase.txt').write_text(TEXT)
    with pytest.raises(ValueError):install(imported,run)
    for name in ('p2-snow.txt','p2-snow-actors.txt'):(run/name).touch()
    install(imported,run);assert (run/'p2-snow-chase.txt').read_text()==TEXT

CPP_PROBE=r'''
#include "pc_p2_snow_chase_policy.h"
#include <cassert>
#include <sstream>
#include <limits>
int main(){
 constexpr float pi=3.14159265358979323846f;
 auto near=[](float a,float b){return std::fabs(a-b)<0.0001f;};
 auto r=P2SnowChasePolicy::steer(0,pi/2,7);
 assert(r.valid && near(r.direction,pi/18) && near(r.x,8.6824089f) && near(r.z,49.2403877f) && r.y==7);
 assert(near(std::hypot(r.x,r.z),50));
 r=P2SnowChasePolicy::steer(0,0.01f,-13);assert(r.valid && near(r.direction,0.004f) && r.y==-13);
 r=P2SnowChasePolicy::steer(0,pi,0);assert(r.valid && r.x<0);
 r=P2SnowChasePolicy::steer(0,0,std::numeric_limits<float>::infinity());assert(!r.valid);
 r=P2SnowChasePolicy::steer(std::numeric_limits<float>::quiet_NaN(),0,0);assert(!r.valid);
 P2SnowChasePolicy p;int snow=0,other=0;assert(!p.evaluate(&snow,0,pi/2,0,r));
 std::istringstream config("P2_SNOW_CHASE_1 chase_profile source_snow");assert(p.read(config));p.bind(&snow);
 assert(p.evaluate(&snow,0,pi/2,7,r) && r.valid);assert(!p.evaluate(&other,0,pi/2,0,r));
 p.bind(&other);p.forget(&snow);assert(!p.contains(&snow) && p.contains(&other));
 p.reset();assert(!p.contains(&other));
 std::istringstream reload("P2_SNOW_CHASE_1 chase_profile source_snow");assert(p.read(reload));assert(!p.contains(&snow));
 p.bind(&snow);std::istringstream bad("P2_SNOW_CHASE_1 chase_profile source_snow extra");assert(!p.read(bad));assert(!p.contains(&snow));
}
'''

def test_compiled_policy(tmp_path):
    import os,shutil,subprocess
    from pathlib import Path
    compiler=shutil.which('g++') or 'C:/msys64/mingw64/bin/g++.exe'
    if not Path(compiler).exists():pytest.skip('C++ compiler unavailable')
    source=tmp_path/'probe.cpp';exe=tmp_path/'probe.exe';source.write_text(CPP_PROBE)
    env=os.environ.copy();env['PATH']=str(Path(compiler).parent)+os.pathsep+env['PATH']
    subprocess.run([compiler,'-std=c++17','-I'+str(Path('native/pc_port').resolve()),str(source),'-o',str(exe)],check=True,capture_output=True,env=env)
    subprocess.run([str(exe)],check=True,capture_output=True,env=env)

def test_native_receiver_guards_and_cleanup():
    from pathlib import Path
    source=Path('native/src/plugPikiNakata/taimoveactions.cpp').read_text().split('bool TaiTracingAction::act',1)[1].split('void TaiGoingHomeAction::finish',1)[0]
    assert source.index('motionStarted')<source.index('if (!target)')<source.index('pc_p2_snow_chase')<source.index('teki.moveToward')
    registry=Path('native/pc_port/pc_p2_enemy.cpp').read_text()
    assert 'if(!actor->isAlive() || !chasePolicy.contains(actor))return false' in registry
    assert 'chasePolicy.reset()' in registry and 'chasePolicy.forget(actor)' in registry
    assert 'actor->mTargetVelocity.y,result' in registry
