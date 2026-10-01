#include "pc_p2_captain.h"
#include "pc_p2_captain_switch_policy.h"
#include <cassert>
#include <cstdio>

struct Input {
    unsigned mCurrentInput=255, mPrevInput=255, mInputPressed=255, mInputReleased=255;
    unsigned mInputDoublePressed=255, mDoublePressMask=255, mInputDelay=10;
    int mMainStickX=74, mMainStickY=-74, mSubStickX=40, mSubStickY=-40;
    int mAnalogA=255, mAnalogB=255, mTriggerL=255, mTriggerR=255;
    int mPlayerNum=2;
    bool mIsControllerFrozen=true;
};

struct Scene {
    float health[2] = {100, 100};
    int owner[2] = {0, 1};
    int active=0, ownershipWrites=0;
};

struct CameraNavi { Input* mKontroller; bool mIsCursorVisible = false; };
struct Camera {
    Input* mController;
    CameraNavi* target = nullptr;
    void startCamera(CameraNavi* navi) {
        // Binding the target alone is insufficient: camera update polls this.
        assert(mController == navi->mKontroller);
        target = navi;
    }
};

int main() {
    P2CaptainSwitchPress edge;
    assert(!edge.update(false, true));
    assert(edge.update(true, true));
    // Holding the same binding across a controller change never switches back.
    assert(!edge.update(true, true));
    assert(!edge.update(true, false));
    assert(edge.update(true, true));
    edge.reset();
    assert(edge.update(true, true));
    assert(p2_captain_switch_safe(true,true,false,false,false,true));
    assert(!p2_captain_switch_safe(false,true,false,false,false,true));
    assert(!p2_captain_switch_safe(true,false,false,false,false,true));
    assert(!p2_captain_switch_safe(true,true,true,false,false,true));
    assert(!p2_captain_switch_safe(true,true,false,true,false,true));
    assert(!p2_captain_switch_safe(true,true,false,false,true,true));
    assert(!p2_captain_switch_safe(true,true,false,false,false,false));

    Input old;
    p2_captain_neutral_input(old);
    assert(!(old.mCurrentInput | old.mPrevInput | old.mInputPressed | old.mInputReleased
        | old.mInputDoublePressed | old.mDoublePressMask | old.mInputDelay));
    assert(!(old.mMainStickX | old.mMainStickY | old.mSubStickX | old.mSubStickY
        | old.mAnalogA | old.mAnalogB | old.mTriggerL | old.mTriggerR));
    assert(old.mPlayerNum==2 && old.mIsControllerFrozen);
    Input selected;
    CameraNavi first{&old}, second{&selected};
    Camera camera{&old};
    p2_captain_bind_camera(camera,second);
    assert(camera.target==&second && camera.mController->mMainStickX==74);
    assert(second.mIsCursorVisible); // live whistle entry requires this
    // Reconciliation is equally valid for the automatic survivor transition.
    p2_captain_bind_camera(camera,first);
    assert(camera.target==&first && camera.mController==&old);

    Scene scene;
    P2CaptainHostOps ops;
    ops.context=&scene;
    ops.captainAt=[](void* c,int i)->void* {return &static_cast<Scene*>(c)->health[i];};
    ops.getHealth=[](void*,void* n) {return *static_cast<float*>(n);};
    ops.setHealth=[](void*,void* n,float hp) {*static_cast<float*>(n)=hp;};
    ops.actorId=[](void* c,void* p)->std::uint32_t {
        return p==&static_cast<Scene*>(c)->owner[0] ? 1 : 2;
    };
    ops.ownerSlot=[](void*,void* p) {return *static_cast<int*>(p);};
    ops.setOwnerSlot=[](void* c,void* p,int owner) {
        ++static_cast<Scene*>(c)->ownershipWrites; *static_cast<int*>(p)=owner;
    };
    ops.enumerate=[](void* c,void** out,int capacity) {
        assert(capacity>=2); auto* s=static_cast<Scene*>(c);
        out[0]=&s->owner[0]; out[1]=&s->owner[1]; return 2;
    };
    ops.notifyActive=[](void* c,int slot) {static_cast<Scene*>(c)->active=slot;};
    P2CaptainAdapter adapter;
    assert(adapter.bind(ops) && adapter.setup());
    assert(p2_captain_input_owner(true,0,scene.active,0));
    assert(!p2_captain_input_owner(true,1,scene.active,0));
    assert(adapter.switchActive(1) && scene.active==1);
    // Right-stick drag and mouse/touch remain in physical stream zero when
    // captain 1 becomes the camera target. Co-op must still use stream one.
    const float dragStreams[2] = {0.75f, -0.25f};
    assert(dragStreams[p2_captain_camera_drag_player(true,scene.active)]==0.75f);
    assert(dragStreams[p2_captain_camera_drag_player(false,scene.active)]==-0.25f);
    // Mouse/wheel/global queues now belong to captain 1 although the device
    // remains assigned to player 0. Inactive captain 0 cannot consume them.
    assert(!p2_captain_input_owner(true,0,scene.active,0));
    assert(p2_captain_input_owner(true,1,scene.active,0));
    // Without the opt-in pair, preserve assigned keyboard/gamepad ownership.
    assert(p2_captain_input_owner(false,0,scene.active,0));
    assert(!p2_captain_input_owner(false,1,scene.active,0));
    assert(p2_captain_input_owner(false,1,0,1));
    assert(adapter.switchActive(0) && scene.active==0);
    assert(dragStreams[p2_captain_camera_drag_player(true,scene.active)]==0.75f);
    assert(scene.owner[0]==0 && scene.owner[1]==1 && scene.ownershipWrites==0);
    scene.health[1]=0;
    assert(adapter.refresh());
    // Raw health refresh does not mark a policy slot Down. The live input
    // boundary must reject zero health independently of policy phase.
    assert(adapter.health(1)==0);
    assert(!p2_captain_switch_safe(true, adapter.health(1)>1, false,false,false,true));
    scene.health[1]=100;
    assert(adapter.refresh());
    assert(adapter.captureCaptain(1,42));
    assert(!adapter.switchActive(1));
    assert(adapter.releaseCaptain(1,42));
    assert(adapter.switchActive(1));
    assert(adapter.policy().damage(0,100));
    assert(!adapter.switchActive(0));
    assert(!adapter.switchActive(7));
    std::puts("PASS P2_CAPTAIN_SWITCH");
}
