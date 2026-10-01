"""Execute the production first-pass gate with a recording movement receiver."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


class CargoMovementGateTests(unittest.TestCase):
    def test_production_gate_preserves_ordinary_and_impulse_passes(self):
        root = Path(__file__).resolve().parents[1]
        native = Path(os.environ.get('PIKMIN_NATIVE_SOURCE', root/'engine'))
        text = (native/'src/plugPikiKando/creature.cpp').read_text()
        start = text.index('\tVector3f originalVel(mVelocity);', text.index('// Apply movement in two passes'))
        end = text.index('\n\t// Handle fixed position', start)
        normal_start = text.index('\tmVelocity = originalVel;', end)
        normal_end = text.index('\n\t// Update the fixed position', normal_start)
        production = text[start:end] + text[normal_start:normal_end]
        compiler = shutil.which('g++') or ('C:/msys64/mingw64/bin/g++.exe' if Path('C:/msys64/mingw64/bin/g++.exe').exists() else None)
        if not compiler:
            self.skipTest('C++ compiler unavailable')
        harness = r'''
#include <cassert>
struct Vector3f {float x=0,y=0,z=0;};
struct Config {int mCarryMinPikis(){return 100;}};
struct Map {void* mMapModel=(void*)1;} map;
Map* mapMgr=&map;
bool purple=true,registered=true;
enum {OBJTYPE_Pellet=1};
struct Creature {
  Vector3f mVelocity,mVolatileVelocity,temporary;
  int mObjType=OBJTYPE_Pellet, moves=0,gravityCalls=0;
  void* mGroundTriangle=(void*)2;
  void* mCollPlatform=nullptr;
  void* mCurrCollisionModel=(void*)1;
  bool piki=true;
  bool isPiki(){return piki;}
  void moveNew(float,bool applyGravity=true){if(moves==0)temporary=mVelocity;++moves;gravityCalls+=applyGravity;}
  void firstPass();
};
struct Pellet:Creature {
  Creature* mPikiCarrier=nullptr;
  int mCarrierCounter=110;
  Config config;
  Config* mConfig=&config;
  float offset=-8;
  float getPickOffset(){return offset;}
};
bool pc_p2_purples_enabled(){return purple;}
void* pc_p2_preview_cargo_shape(Pellet*){return registered?(void*)3:nullptr;}
void Creature::firstPass(){float deltaTime=1.f/30;
PRODUCTION
}
int main(){
  Creature piki;
  auto cargo=[&](){Pellet p;p.mPikiCarrier=&piki;return p;};
  auto check=[](Pellet& p,int expected){
    p.moves=p.gravityCalls=0;p.firstPass();assert(p.moves==2);assert(p.gravityCalls==expected+1);
    assert(p.temporary.x==p.mVolatileVelocity.x && p.temporary.y==p.mVolatileVelocity.y && p.temporary.z==p.mVolatileVelocity.z);
  };
  {auto p=cargo();check(p,0);}
  {auto p=cargo();purple=false;check(p,1);purple=true;}
  {auto p=cargo();registered=false;check(p,1);registered=true;}
  {auto p=cargo();p.mObjType=2;check(p,1);}
  {auto p=cargo();p.mPikiCarrier=nullptr;check(p,1);}
  {auto p=cargo();piki.piki=false;check(p,1);piki.piki=true;}
  {auto p=cargo();p.offset=0;check(p,1);}
  {auto p=cargo();p.mCarrierCounter=99;check(p,1);p.mCarrierCounter=100;check(p,0);}
  {auto p=cargo();p.mGroundTriangle=nullptr;check(p,1);}
  {auto p=cargo();p.mCollPlatform=(void*)4;check(p,1);}
  {auto p=cargo();p.mCurrCollisionModel=(void*)5;check(p,1);}
  for(int axis=0;axis<3;++axis)for(float impulse:{-1.f,0.000001f,1.f}){
    auto p=cargo();
    if(axis==0)p.mVolatileVelocity.x=impulse;
    if(axis==1)p.mVolatileVelocity.y=impulse;
    if(axis==2)p.mVolatileVelocity.z=impulse;
    check(p,0);
  }
}
'''.replace('#include <cassert>', '#include <cassert>\n#include <initializer_list>').replace('PRODUCTION', production)
        with tempfile.TemporaryDirectory() as temp:
            cpp = Path(temp)/'gate.cpp'
            exe = Path(temp)/('gate.exe' if os.name == 'nt' else 'gate')
            cpp.write_text(harness)
            env = dict(os.environ, PATH=str(Path(compiler).parent)+os.pathsep+os.environ.get('PATH',''))
            build = subprocess.run([compiler, '-std=c++17', '-O2', str(cpp), '-o', str(exe)], env=env, capture_output=True, text=True)
            self.assertEqual(build.returncode, 0, build.stdout+build.stderr)
            subprocess.run([str(exe)], check=True, env=env, capture_output=True)


if __name__ == '__main__':
    unittest.main()
