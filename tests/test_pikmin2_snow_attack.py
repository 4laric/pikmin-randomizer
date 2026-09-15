import math
import os
from pathlib import Path
import shutil
import subprocess
import pytest
from experimental.pikmin2_snow_attack import profile,eligible,install,TEXT

PARAMS='{\n{s000} 4 1\n{_eof}\n}\n{\n{fp20} 4 30\n{fp21} 4 20\n{_eof}\n}\n{\n{fp20} 4 99\n{_eof}\n}\n'
EVENTS='1\n{\nZ:\\source\\attack.bca\nattack.bca\n8 2\n88 3\n-1\n}\n'

def test_source_profile():
    assert profile(PARAMS,EVENTS)['range']==30
    with pytest.raises(ValueError):profile(PARAMS.replace('4 30','4 31'),EVENTS)
    with pytest.raises(ValueError):profile(PARAMS,EVENTS.replace('88 3','87 3'))

@pytest.mark.parametrize('distance,angle,expected',[(899.9,0,True),(900,0,False),(901,0,False),(0,20,True),(0,-20,True),(0,20.001,False),(0,340,True),(0,180,False),(float('nan'),0,False),(0,float('nan'),False),(-1,0,False)])
def test_geometry(distance,angle,expected):
    assert eligible(distance,math.radians(angle)) is expected

def test_vertical_distance():
    assert eligible(20**2+20**2,0)
    assert not eligible(20**2+23**2,0)

def test_install(tmp_path):
    imported=tmp_path/'import';run=tmp_path/'run';imported.mkdir();run.mkdir();(imported/'p2-snow-attack.txt').write_text(TEXT)
    with pytest.raises(ValueError):install(imported,run)
    for name in ('p2-snow.txt','p2-snow-actors.txt'):(run/name).touch()
    install(imported,run);assert (run/'p2-snow-attack.txt').read_text()==TEXT
    (imported/'p2-snow-attack.txt').write_text(TEXT+'extra')
    with pytest.raises(ValueError):install(imported,run)

def test_native_receiver_preserves_stick_and_p1_order():
    source=Path('native/src/plugPikiNakata/tekibteki.cpp').read_text().split('bool BTeki::attackableCreature',1)[1].split('f32 BTeki::calcTargetAngle',1)[0]
    assert source.index('getStickObject()')<source.index('pc_p2_snow_attackable')<source.index('contactCreature(target)')
    receiver=Path('native/pc_port/pc_p2_enemy.cpp').read_text()
    assert 'recognition.satisfy(&target)' in receiver
    assert 'delta.y*delta.y' in receiver
    assert 'attackPolicy.forget(actor)' in receiver

def test_compiled_policy(tmp_path):
    compiler=shutil.which('g++') or 'C:/msys64/mingw64/bin/g++.exe'
    if not Path(compiler).exists():pytest.skip('C++ compiler unavailable')
    source=tmp_path/'probe.cpp';exe=tmp_path/'probe.exe'
    source.write_text(r'''
#include "pc_p2_snow_attack_policy.h"
#include <sstream>
#include <cassert>
#include <limits>
int main(){
 P2SnowAttackPolicy p;int snow=0,ordinary=0;bool result=true;
 assert(!p.evaluate(&snow,0,0,true,result) && result);
 std::istringstream config("P2_SNOW_ATTACK_1 range 30 half_angle 20");assert(p.read(config));p.bind(&snow);
 assert(!p.evaluate(&ordinary,0,0,true,result));
 assert(p.evaluate(&snow,899.9f,0,true,result)&&result);
 assert(p.evaluate(&snow,900,0,true,result)&&!result);
 assert(p.evaluate(&snow,0,0,false,result)&&!result);
 constexpr float pi=3.14159265358979323846f;
 assert(p.geometry(0,20.f*(pi/180.f)));
 assert(p.geometry(0,-20.f*(pi/180.f)));
 assert(!p.geometry(0,20.001f*(pi/180.f)));
 assert(p.geometry(0,2*pi));
 assert(!p.geometry(0,pi));
 assert(!p.geometry(20*20+23*23,0));
 assert(!p.geometry(0,std::numeric_limits<float>::quiet_NaN()));
 assert(!p.geometry(std::numeric_limits<float>::infinity(),0));
 p.forget(&snow);assert(!p.evaluate(&snow,0,0,true,result));
 p.bind(&snow);p.reset();assert(!p.evaluate(&snow,0,0,true,result));
 std::istringstream reload("P2_SNOW_ATTACK_1 range 30 half_angle 20");assert(p.read(reload));
 assert(!p.evaluate(&snow,0,0,true,result));p.bind(&snow);
 std::istringstream bad("P2_SNOW_ATTACK_1 range 31 half_angle 20");assert(!p.read(bad));assert(!p.contains(&snow));
}
''')
    env=os.environ.copy();env['PATH']=str(Path(compiler).parent)+os.pathsep+env['PATH']
    subprocess.run([compiler,'-std=c++17','-I'+str(Path('native/pc_port').resolve()),str(source),'-o',str(exe)],check=True,capture_output=True,env=env)
    subprocess.run([str(exe)],check=True,capture_output=True,env=env)
