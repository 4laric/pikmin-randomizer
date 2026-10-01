#include "pc_p2_purple_flight.h"
#include "pc_p2_purple_feedback.h"
#include "Piki.h"
#include "teki.h"
#include <cassert>
#include <cstdio>

TekiMgr manager;TekiMgr* tekiMgr=&manager;
static bool purpleFeature=true,impactFeature=true;static int feedbackCancel=0;
bool pc_p2_purples_enabled(){return purpleFeature;}
bool pc_p2_is_purple(const Piki* p){return purpleFeature&&p&&p->purple;}
bool pc_p2_purple_impact_enabled(){return impactFeature;}
void pc_p2_purple_feedback_entry(Piki*){}
void pc_p2_purple_feedback_update(Piki*,float){}
void pc_p2_purple_feedback_land(Piki*,bool){}
void pc_p2_purple_feedback_cancel(Piki*){++feedbackCancel;}
void pc_p2_purple_feedback_reset(){}

static void enable(){FILE* f=std::fopen("p2-purple-flight.txt","wb");std::fputs("P2_PURPLE_FLIGHT_1\n",f);std::fclose(f);pc_p2_purple_flight_setup();}
static void disable(){std::remove("p2-purple-flight.txt");pc_p2_purple_flight_setup();}

int main(){
    Piki p;disable();pc_p2_purple_flight_arm(&p);assert(!pc_p2_purple_flight_active(&p));
    enable();p.purple=false;pc_p2_purple_flight_arm(&p);assert(!pc_p2_purple_flight_active(&p));p.purple=true;
    p.mVelocity.y=7;assert(!pc_p2_purple_flight_update(&p,.3f,100));assert(p.mVelocity.y==7&&!pc_p2_purple_flight_active(&p));
    p.alive=false;pc_p2_purple_flight_arm(&p);assert(!pc_p2_purple_flight_active(&p));p.alive=true;
    pc_p2_purple_flight_arm(&p);assert(pc_p2_purple_flight_sample(&p).phase==PcP2PurpleFlightPhase::Ascent);
    p.mVelocity.y=0;assert(!pc_p2_purple_flight_update(&p,.01f,100));assert(pc_p2_purple_flight_sample(&p).phase==PcP2PurpleFlightPhase::EntryPause);assert(p.isCreatureFlag(CF_IgnoreGravity));
    assert(!pc_p2_purple_flight_update(&p,.24f,100));assert(pc_p2_purple_flight_sample(&p).phase==PcP2PurpleFlightPhase::EntryPause);
    BTeki far,near,dead,prop;far.mSRT.t={40,0,0};far.mCollisionRadius=20;near.mSRT.t={0,0,20};near.mCollisionRadius=20;dead.mSRT.t={1,0,0};dead.alive=false;dead.mCollisionRadius=20;prop.mSRT.t={2,0,0};prop.organic=false;prop.mCollisionRadius=20;manager.actors={&far,&dead,&prop,&near};
    assert(!pc_p2_purple_flight_update(&p,.01f,100));assert(pc_p2_purple_flight_sample(&p).phase==PcP2PurpleFlightPhase::Descent);assert(std::fabs(p.mVelocity.z-120)<.01f&&std::fabs(p.mVelocity.x)<.01f);
    assert(pc_p2_purple_flight_land(&p,false));assert(pc_p2_purple_flight_sample(&p).phase==PcP2PurpleFlightPhase::Recovery);
    assert(!pc_p2_purple_flight_update(&p,.29f,100));assert(pc_p2_purple_flight_update(&p,.02f,100));
    pc_p2_purple_flight_cancel(&p);assert(!pc_p2_purple_flight_active(&p));assert(!p.isCreatureFlag(CF_IgnoreGravity)&&!p.isCreatureFlag(CF_UsePriorityFaceDir));
    p.flags=CF_IgnoreGravity|CF_UsePriorityFaceDir;pc_p2_purple_flight_arm(&p);p.mVelocity.y=0;pc_p2_purple_flight_update(&p,.01f,100);pc_p2_purple_flight_reset();assert(p.flags==(CF_IgnoreGravity|CF_UsePriorityFaceDir));
    enable();p.flags=0;p.mVelocity.y=1;pc_p2_purple_flight_arm(&p);pc_p2_purple_flight_arm(&p);assert(pc_p2_purple_flight_active(&p));pc_p2_purple_flight_cancel(&p);assert(!pc_p2_purple_flight_active(&p));
    p.mSRT.t={0,0,0};near.mSRT.t={0,0,0};manager.actors={&near};pc_p2_purple_flight_arm(&p);p.mVelocity.y=0;pc_p2_purple_flight_update(&p,.01f,100);pc_p2_purple_flight_update(&p,.25f,100);assert(std::isfinite(p.mVelocity.x)&&std::isfinite(p.mVelocity.z)&&p.mVelocity.x==0&&p.mVelocity.z==0);
    pc_p2_purple_flight_cancel(&p);disable();std::puts("PASS actual Purple flight module policy");

    // Regression: reset/rearm must clear flags introduced by the old flight,
    // even when it is interrupted during the pause or spinning descent.
    enable();p.flags=0;pc_p2_purple_flight_arm(&p);p.mVelocity.y=0;
    pc_p2_purple_flight_update(&p,.01f,100);assert(p.isCreatureFlag(CF_IgnoreGravity));
    pc_p2_purple_flight_reset();assert(p.flags==0&&!pc_p2_purple_flight_active(&p));
    enable();pc_p2_purple_flight_arm(&p);p.mVelocity.y=0;pc_p2_purple_flight_update(&p,.01f,100);
    pc_p2_purple_flight_arm(&p);assert(p.flags==0&&pc_p2_purple_flight_sample(&p).phase==PcP2PurpleFlightPhase::Ascent);
    p.mVelocity.y=0;pc_p2_purple_flight_update(&p,.01f,100);pc_p2_purple_flight_update(&p,.25f,100);
    assert(p.isCreatureFlag(CF_UsePriorityFaceDir));pc_p2_purple_flight_arm(&p);assert(p.flags==0);
    pc_p2_purple_flight_cancel(&p);assert(!pc_p2_purple_flight_active(&p));
    p.mVelocity.y=3;pc_p2_purple_flight_update(&p,.1f,100);assert(p.mVelocity.y==3);
    disable();std::puts("PASS Purple pause/descent reset and rearm regressions");
}
