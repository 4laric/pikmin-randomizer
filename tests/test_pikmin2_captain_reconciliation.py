"""Compile the production captain adapter and owner callback against doubles.

Set P2_CAPTAIN_SOURCE to the private native worktree. This does not launch gameplay.
"""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path(os.environ.get("P2_CAPTAIN_SOURCE", ROOT / "engine"))
COMPILER = shutil.which("g++") or "C:/msys64/mingw64/bin/g++.exe"

HOST = r'''
#include "pc_p2_captain.h"
#include <cassert>
#include <cstdio>
#include <cstdint>
#include <unordered_map>
struct Navi {};
namespace PikiMode { enum {FormationMode=1,FreeMode=2}; }
namespace PikiAction { enum {Crowd=1,NOACTION=2}; }
struct Piki;
struct Action { int mCurrActionIdx=PikiAction::Crowd; Piki* p; void abandon(void*); };
struct Piki {
    Navi* mNavi; int mMode=PikiMode::FormationMode; Action action; Action* mActiveAction=&action;
    bool alive=true; int cleanup=0,form=0,free=0; Navi* oldOwner=nullptr;
    Piki(Navi* n):mNavi(n) {action.p=this;}
    bool isAlive() {return alive;}
    void changeMode(int m,Navi* n) {
        assert(action.mCurrActionIdx==PikiAction::NOACTION);
        assert(n==mNavi); mMode=m; if(n) ++form; else ++free;
    }
};
static P2CaptainAdapter adapterValue;
static bool reenter=false,kill=false,recapture=false,forget=false;
static std::unordered_map<void*,std::uint32_t> g_actorIds;
static std::uint32_t actor_id_for(void* p) {return g_actorIds[p];}
void Action::abandon(void*) {
    assert(p->mNavi==p->oldOwner); ++p->cleanup; mCurrActionIdx=PikiAction::NOACTION;
    if(reenter) {p->mNavi=nullptr; adapterValue.policy().abandon(1,1);}
    if(kill) p->alive=false;
    if(recapture) adapterValue.policy().captureActor(99,1);
    if(forget) adapterValue.forgetActor(p);
}
struct Mgr {Navi navis[2]; Navi* getNavi(int n) {return &navis[n];}} manager;
static Mgr* naviMgr=&manager;
namespace pc_p2_captain { P2CaptainAdapter* adapter() {return &adapterValue;} }
static float hp=100;
static void* captain(void*,int n) {return &manager.navis[n];}
static float health(void*,void*) {return hp;}
static void setHealth(void*,void*,float) {}
static unsigned identity(void*,void* p) {return actor_id_for(p);}
static int owner(void*,void*) {return 0;}
static void setOwner(void*,void*,int) {}
static int enumerate(void*,void**,int) {return 0;}
'''

CASES = r'''
int main() {
    P2CaptainHostOps ops; ops.captainAt=captain; ops.getHealth=health; ops.setHealth=setHealth;
    ops.actorId=identity; ops.ownerSlot=owner; ops.setOwnerSlot=setOwner; ops.enumerate=enumerate;
    assert(adapterValue.bind(ops) && adapterValue.setup());
    Piki p(&manager.navis[0]); p.oldOwner=p.mNavi; g_actorIds[&p]=1;
    assert(adapterValue.policy().claim(1,1));
    live_set_owner_slot(nullptr,&p,1);
    assert(p.cleanup==1 && p.form==1 && p.mNavi==&manager.navis[1]);
    live_set_owner_slot(nullptr,&p,1); assert(p.cleanup==1);
    adapterValue.policy().abandon(1,1); p.oldOwner=p.mNavi;
    p.action.mCurrActionIdx=PikiAction::Crowd;
    live_set_owner_slot(nullptr,&p,-1); assert(p.cleanup==2 && p.free==1 && !p.mNavi);
    for(int scenario=0;scenario<4;++scenario) {
        adapterValue.policy().forgetActor(1); assert(adapterValue.policy().claim(1,1));
        p.mNavi=&manager.navis[0]; p.oldOwner=p.mNavi; p.alive=true;
        p.mMode=PikiMode::FormationMode; p.action.mCurrActionIdx=PikiAction::Crowd;
        reenter=scenario==0; kill=scenario==1; recapture=scenario==2; forget=scenario==3;
        const int before=p.form; live_set_owner_slot(nullptr,&p,1);
        assert(p.form==before); // stale cleanup cannot reform a replacement owner/lifetime
    }
    std::puts("PASS P2_CAPTAIN_OWNER_CALLBACK");
}
'''

SURVIVOR_HOST = r'''
#include "pc_p2_captain_switch_policy.h"
#include <cassert>
#include <cstdio>
struct Controller {
    unsigned mCurrentInput=0,mPrevInput=0,mInputPressed=0,mInputReleased=0;
    unsigned mInputDoublePressed=0,mDoublePressMask=0,mInputDelay=0;
    float mMainStickX=0,mMainStickY=0,mSubStickX=0,mSubStickY=0;
    float mAnalogA=0,mAnalogB=0,mTriggerL=0,mTriggerR=0;
    bool keyDown(unsigned k) {return mCurrentInput&k;}
};
constexpr unsigned KBBTN_DPAD_UP=1;
struct Velocity {void set(float,float,float){}};
struct Navi {int id; float mHealth=100; bool mIsCursorVisible=true,safe=true;
    Controller control; Controller* mKontroller=&control; Velocity mTargetVelocity;
    int getNaviIndex(){return id;}
};
struct Manager {Navi a{0},b{1}; int active=0; bool otherPresent=true;
    Navi* getActiveNavi(){return active?&b:&a;}
    Navi* getOtherNavi(Navi* n){return otherPresent?(n==&a?&b:&a):nullptr;}
} manager;
static Manager* naviMgr=&manager;
struct Camera {Controller* mController=nullptr; Navi* target=nullptr;
    void startCamera(Navi* n){target=n;}
} camera;
static Camera* cameraMgr=&camera;
struct Policy {bool targetControllable=true; bool controllable(int){return targetControllable;}};
struct P2CaptainAdapter {Policy value; Policy& policy(){return value;} bool refresh(){return false;}} live;
static bool enabled=true, g_switchHintShown=true;
static P2CaptainSwitchPress g_switchPress;
struct {unsigned mDemoFlags=0;} gameflow;
namespace CinePlayerFlags {constexpr unsigned NaviNoAI=1;}
static bool single_player_switch_enabled(){return enabled;}
static bool safe_to_switch(Navi* n){return n && n->safe && n->mHealth>1;}
static P2CaptainAdapter* adapter(){return &live;}
static bool switch_active(int n){manager.active=n;return true;}
'''

SURVIVOR_CASES = r'''
int main() {
    manager.a.mHealth=-400;manager.a.control.mCurrentInput=0;
    manager.b.control.mCurrentInput=8;
    update_player_switch();
    assert(manager.active==1 && camera.target==&manager.b && camera.mController==manager.b.mKontroller);
    assert(manager.a.mHealth==-400 && !manager.a.mIsCursorVisible && manager.b.mIsCursorVisible);
    assert(manager.a.control.mCurrentInput==0 && manager.b.control.mCurrentInput==0);
    // Single/co-op/VS are represented by the production entrypoint's enabled
    // predicate. No other, unsafe/captive target, nonfinite health and cinematic
    // exclusions must not manufacture a healthy/dead state or input takeover.
    for(int reason=0;reason<7;++reason) {
        manager.active=0;manager.a.mHealth=0;manager.b.mHealth=100;
        manager.otherPresent=true;manager.b.safe=true;live.value.targetControllable=true;
        enabled=true;gameflow.mDemoFlags=0;
        if(reason==0)enabled=false;
        if(reason==1)manager.otherPresent=false;
        if(reason==2)manager.b.safe=false;
        if(reason==3)live.value.targetControllable=false;
        if(reason==4)manager.a.mHealth=NAN;
        if(reason==5)manager.b.mHealth=1;
        if(reason==6)gameflow.mDemoFlags=CinePlayerFlags::NaviNoAI;
        update_player_switch();assert(manager.active==0);
    }
    std::puts("PASS P2_CAPTAIN_SURVIVOR_CALLBACK");
}
'''


@unittest.skipIf(not os.environ.get("P2_CAPTAIN_SOURCE")
                 and not (SOURCE / "tools/test_p2_captain_reconciliation.cpp").is_file(),
                 "Requires the paired native candidate or its maintained source export")
class CaptainReconciliationTests(unittest.TestCase):
    def compile_run(self, source_text=None, source_path=None):
        output = ROOT / "output"
        output.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="captain-reconcile-", dir=output) as folder:
            folder = Path(folder)
            if source_text is not None:
                source_path = folder / "test.cpp"
                source_path.write_text(source_text, encoding="utf-8")
            exe = folder / "test.exe"
            compiled = subprocess.run([COMPILER, "-std=c++17", "-O0", "-I", str(SOURCE / "pc_port"),
                                       str(source_path), "-o", str(exe)], capture_output=True, text=True)
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            result = subprocess.run([str(exe)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            return result.stdout

    def test_live_reconciliation(self):
        self.assertIn("PASS P2_CAPTAIN_RECONCILIATION", self.compile_run(
            source_path=SOURCE / "tools/test_p2_captain_reconciliation.cpp"))

    def test_production_formation_callback(self):
        text = (SOURCE / "pc_port/pc_p2_captain.cpp").read_text(encoding="utf-8")
        start = text.index("void live_set_owner_slot(")
        end = text.index("\n// Abandon the squad action", start)
        self.assertIn("PASS P2_CAPTAIN_OWNER_CALLBACK", self.compile_run(HOST + text[start:end] + CASES))

    def test_production_survivor_callback(self):
        text = (SOURCE / "pc_port/pc_p2_captain.cpp").read_text(encoding="utf-8")
        start = text.index("void update_player_switch()")
        end = text.index("\nbool reload()", start)
        self.assertIn("PASS P2_CAPTAIN_SURVIVOR_CALLBACK",
                      self.compile_run(SURVIVOR_HOST + text[start:end] + SURVIVOR_CASES))


if __name__ == "__main__":
    unittest.main()
