"""Compile the actual transport methods against small receiver/actor stand-ins.

This tests function placement and ordinary destination fallback, not game physics.
No rewritten copy of either transport method is used.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess


def method(source, signature):
    start = source.index(signature)
    brace = source.index('{', start)
    depth = 1
    end = brace + 1
    while depth:
        if source[end] == '{': depth += 1
        if source[end] == '}': depth -= 1
        end += 1
    return source[start:end]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, default=Path(__file__).resolve().parents[1] / 'src/plugPikiKando/aiTransport.cpp')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--compiler', default='g++')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    source = args.source.read_text(encoding='utf-8')
    methods = '\n'.join(method(source, s) for s in
                        ('void ActTransport::initWait()', 'void ActTransport::decideGoal(Creature* cargo)'))
    setup = r'''
#include <cassert>
#include <cstdio>
#include <cstdlib>
#include <vector>
#undef assert
#define assert(expression) do {if(!(expression)){std::fprintf(stderr,"failed: %s\n",#expression);return 1;}} while(0)
#define PIKI_PC_PORT 1
#define PRINT(...) do {} while(0)
#define PRINT_KANDO(...) do {} while(0)
#define ERROR(...) std::abort()
#define STACK_PAD_VAR(...) do {} while(0)
using f32 = float;
enum {Blue, Red, Yellow, PikiColorCount};
enum {PELTYPE_UfoPart=1, PIKIANIM_Wait=7};
constexpr int TRUE=1;
struct Position{};
struct Suckable{};
struct Creature{virtual bool isPiki(){return false;} std::vector<Creature*> carriers;};
struct Navi{int mNaviID=0;};
struct PaniMotionInfo{explicit PaniMotionInfo(int){}};
struct Piki:Creature {
 int mColor=Red,mPlayerId=0,looks=0,motions=0; Navi* mNavi=nullptr;
 bool isPiki() override{return true;}
 void startLook(Position*){++looks;}
 void startMotion(PaniMotionInfo,PaniMotionInfo){++motions;}
};
struct Config{int type=0; struct {const char* mStringID="test";} mModelId;
 int mPelletType(){return type;} int mPelletColor(){return Red;}};
struct Pellet:Creature{Config* mConfig=nullptr;Suckable* mTargetGoal=nullptr;struct{Position t;}mSRT;};
struct PelletRef{Pellet* mPtr=nullptr;Pellet* getPtr(){return mPtr;}};
struct Stickers{Creature* cargo;explicit Stickers(Creature*c):cargo(c){}};
struct Iterator{Stickers* list;unsigned idx=0;explicit Iterator(Stickers*s):list(s){}
 Creature* operator*(){return list->cargo->carriers[idx];}};
#define CI_LOOP(it) for(;(it).idx<(it).list->cargo->carriers.size();++(it).idx)
struct ItemMgr{Suckable ship,onions[3];Suckable* getUfo(){return &ship;}
 Suckable* pcGetUfo(int){return &ship;}
 Suckable* getContainer(int color){return &onions[color];}
 Suckable* pcGetContainer(int color,int){return getContainer(color);}};
ItemMgr manager;ItemMgr* itemMgr=&manager;
struct{int mIsVersusMode=0;}flowCont;
bool pc_vs_active(){return false;}
struct System{float getRand(float){return 0;}}systemState;System* gsys=&systemState;
Suckable cavePod,legacyPod;Pellet* ownedCargo=nullptr;bool caveReady=true,legacy=false;
Suckable* pc_p2_cave_items_goal_for(Pellet*p){return caveReady&&p&&p==ownedCargo?&cavePod:nullptr;}
Suckable* pc_p2_preview_goal(){return legacy?&legacyPod:nullptr;}
struct ActTransport{
 enum{STATE_Wait=2};PelletRef mPellet;Piki* mPiki=nullptr;Suckable* mGoal=nullptr;
 int mState=99;float mWaitTimer=-1;
 void initWait();void decideGoal(Creature* cargo);
};
'''
    controls = r'''
int main(){
 Config config;Pellet owned,other;owned.mConfig=other.mConfig=&config;
 Piki carrier,blue1,blue2,red;blue1.mColor=blue2.mColor=Blue;
 other.carriers={&blue1,&blue2,&red};
 ActTransport a;a.mPiki=&carrier;a.mPellet.mPtr=&owned;a.mGoal=&manager.ship;
 ownedCargo=&owned;
 // The earlier misplaced hook returned before all four wait initializations.
 a.initWait();assert(a.mState==ActTransport::STATE_Wait);
 assert(carrier.looks==1&&carrier.motions==1&&a.mWaitTimer==3.0f);
 assert(a.mGoal==&manager.ship);
 a.decideGoal(&owned);assert(a.mGoal==&cavePod&&owned.mTargetGoal==&cavePod);
 assert(a.mState==ActTransport::STATE_Wait&&carrier.motions==1);
 // An unrelated actor sharing its config retains ordinary majority routing.
 a.mPellet.mPtr=&other;a.decideGoal(&other);
 assert(a.mGoal==&manager.onions[Blue]&&other.mTargetGoal==a.mGoal);
 config.type=PELTYPE_UfoPart;a.decideGoal(&other);
 assert(a.mGoal==&manager.ship&&other.mTargetGoal==&manager.ship);
 // Historical preview routing and its wait animation remain intact.
 legacy=true;a.initWait();assert(carrier.looks==2&&carrier.motions==2);
 a.decideGoal(&other);assert(a.mGoal==&legacyPod);
 legacy=false;caveReady=false;a.mPellet.mPtr=&owned;a.decideGoal(&owned);
 assert(a.mGoal==&manager.ship);
 ownedCargo=nullptr;caveReady=true;a.decideGoal(&owned);assert(a.mGoal==&manager.ship);
 std::puts("PASS actual initWait initialization and decideGoal routing controls");
}
'''
    cpp = args.output / 'transport-methods.cpp'
    cpp.write_text(setup + methods + controls, encoding='utf-8', newline='\n')
    binary = args.output / 'transport-methods'
    compiled = subprocess.run([args.compiler, '-std=c++17', '-Wall', '-Wextra',
        '-Werror', '-Wno-unused-parameter', str(cpp), '-o', str(binary)], capture_output=True)
    (args.output / 'compile.stdout').write_bytes(compiled.stdout)
    (args.output / 'compile.stderr').write_bytes(compiled.stderr)
    result = {'source_sha256': hashlib.sha256(args.source.read_bytes()).hexdigest(),
              'extracted_methods_sha256': hashlib.sha256(methods.encode()).hexdigest(),
              'compile_exit': compiled.returncode, 'actual_game': False}
    if compiled.returncode == 0:
        run = subprocess.run([str(binary)], capture_output=True, timeout=10)
        (args.output / 'run.stdout').write_bytes(run.stdout)
        (args.output / 'run.stderr').write_bytes(run.stderr)
        result['run_exit'] = run.returncode
    (args.output / 'result.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result))
    return int(compiled.returncode != 0 or result.get('run_exit') != 0)


if __name__ == '__main__':
    raise SystemExit(main())
