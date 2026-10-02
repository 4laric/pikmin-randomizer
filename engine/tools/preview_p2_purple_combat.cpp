// Acceptance additionally requires a production P2_PURPLE_DIRECT stage=hipdrop
// marker for the printed target/source pointers, family=adult_bulborb and
// damage_applied=1 and queued_after-queued_before=50, together with the
// regeneration-compensated 50 HP delta below. Adult accepted=0
// is expected (that flag describes dwarf press). Health alone is NOT acceptance.
// The historical adult_direct mode stages captain/source positions and is not
// ordinary combat acceptance. Natural transport and natural_dayend/resume modes
// remain separate, with no actor relocation or direct stock-helper injection.
#include <SDL2/SDL.h>
#include <GL/gl.h>
#include "Graphics.h"
#include "pc_gfx.h"
#include "pc_purple_collision_trace.h"
#include "pc_purple_sdl_axis_policy.h"
#include "timing/pc_render_phase.h"
#include "pc_diary_observer.h"
#include "p2_purple_save_input.h"
#include "system.h"
#include "App.h"
#include "Node.h"
#include "MoviePlayer.h"
#include "Navi.h"
#include "NaviMgr.h"
#include "NaviState.h"
#include "Piki.h"
#include "PikiMgr.h"
#include "PikiState.h"
#include "PikiHeadItem.h"
#include "Pellet.h"
#include "PelletState.h"
#include "PikiAI.h"
#include "GoalItem.h"
#include "Route.h"
#include "Pom.h"
#include "Boss.h"
#include "ItemMgr.h"
#include "GameStat.h"
#include "MapMgr.h"
#include "Collision.h"
#include "Camera.h"
#include "Controller.h"
#include "Kontroller.h"
#include "CPlate.h"
#include "Stickers.h"
#include "MapCode.h"
#include <vector>
#include <algorithm>
#include <limits>
#include "nlib/System.h"
#include "gameflow.h"
#include "pc_randomizer.h"
#include "pc_p2_purple.h"
#include "pc_p2_ship.h"
#include "pc_p2_ship_store.h"
#include "pc_p2_input_script.h"
#include "FlowController.h"
#include "WorldClock.h"
#include "pc_p2_purple_direct.h"
#include "pc_p2_purple_flight.h"
#include "pc_p2_campaign_actor.h"
#include "pc_p2_chappy.h"
#include "pc_p2_purple_impact.h"
#include "pc_window.h"
#include "pc_gpu_preference.h"
#include "pc_bbft.h"
#include "settings/pc_settings.h"
#include "settings/pc_settings_p2d.h"
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <cerrno>
#include <climits>
#include <chrono>
#include <set>
#include <fstream>
#include <filesystem>
#include <string>

// Fixture controller policy only. The damping estimate is not a collision
// proof: every route still uses current live parts and flat-terrain checks.
static bool sdlPluckMotionValid(float speed,float targetSpeed,float tau,float dt) {
    return std::isfinite(speed) && speed>=0.f && std::isfinite(targetSpeed) && targetSpeed>=0.f
        && std::isfinite(tau) && tau>0.f && std::isfinite(dt) && dt>0.f && dt<=tau;
}
static bool sdlPluckAtRest(float speed,float targetSpeed) {
    return speed<=1.f && targetSpeed<=1.f;
}
static bool sdlPluckBrakeBeforeWaypoint(float distance,float speed,float tau,float dt) {
    return speed>1.f && distance<=speed*(tau+dt)+4.f;
}

// BEGIN SDL PLUCK PULSE POLICY
// Read-only fixture forecast. This is the flat, non-slip specialization of
// Navi::makeVelocity and Creature::updateAI/update, including native fix-position.
// It neither advances the engine nor writes an actor. Runtime observations,
// current collision parts and the unchanged native pluck gate remain authoritative.
struct SdlPluckPoint { float x=0.f,z=0.f; };
static SdlPluckPoint pluckAdd(SdlPluckPoint a,SdlPluckPoint b) {return {a.x+b.x,a.z+b.z};}
static SdlPluckPoint pluckSub(SdlPluckPoint a,SdlPluckPoint b) {return {a.x-b.x,a.z-b.z};}
static SdlPluckPoint pluckScale(SdlPluckPoint a,float s) {return {a.x*s,a.z*s};}
static float pluckLength(SdlPluckPoint a) {return std::hypot(a.x,a.z);}
static bool pluckFinite(SdlPluckPoint a) {return std::isfinite(a.x)&&std::isfinite(a.z);}
struct SdlPluckState { SdlPluckPoint position,velocity,anchor; bool fixed=false; };
struct SdlPluckInputModel {
    float speed=0.f,binDegrees=0.f,clamp=0.f,neutral=0.f,cursor=0.f;
    float cameraX=1.f,cameraZ=0.f;
    int deadZone=0;
};
static bool pluckInputModelValid(const SdlPluckInputModel& m) {
    return std::isfinite(m.speed)&&m.speed>0.f&&std::isfinite(m.binDegrees)&&m.binDegrees>0.f&&m.binDegrees<=180.f
        &&std::isfinite(m.clamp)&&m.clamp>0.f&&m.clamp<=1.f&&std::isfinite(m.neutral)&&m.neutral>=0.f
        &&std::isfinite(m.cursor)&&m.cursor>=m.neutral&&m.cursor<m.clamp
        &&std::isfinite(m.cameraX)&&std::isfinite(m.cameraZ)
        &&std::fabs(std::hypot(m.cameraX,m.cameraZ)-1.f)<.001f
        &&m.deadZone>=0 && m.deadZone<=127;
}
static SdlPluckPoint pluckInputTarget(int x,int y,const SdlPluckInputModel& m) {
    // ordinaryInput(nativeAxisUnits=true) -> strict per-axis loaded SDL dead
    // zone -> SDL axis /256 -> Controller /74.
    // Navi bins the CAMERA-space direction before rotating it into world space.
    const float pi=3.14159265358979323846f,quarter=pi*.25f;
    const float sx=pcPurpleSdlPulseSampleAxis(x,m.deadZone)/74.f;
    const float sz=-pcPurpleSdlPulseSampleAxis(y,m.deadZone)/74.f;
    float magnitude=std::sqrt(sx*sx+sz*sz),theta=std::atan2(sx,sz);
    if(theta<0.f)theta+=2.f*pi;
    const float width=pi/180.f*m.binDegrees;
    const float angle=width*int((theta+width*.5f)/width);
    const float remainder=angle-int(angle/quarter)*quarter;
    const float length=std::sin(quarter)/(std::sin(remainder)+std::sin(quarter-remainder));
    magnitude*=1.f/length;
    if(magnitude>=m.clamp)magnitude=1.f;
    if(magnitude<m.neutral || magnitude<=m.cursor)magnitude=0.f;
    const float localX=magnitude*std::sin(angle),localZ=magnitude*std::cos(angle);
    return {(m.cameraX*localX-m.cameraZ*localZ)*m.speed,
            (m.cameraZ*localX+m.cameraX*localZ)*m.speed};
}
static bool pluckPulseStep(SdlPluckState& s,SdlPluckPoint target,float dt,float tau) {
    if(!pluckFinite(s.position)||!pluckFinite(s.velocity)||!pluckFinite(s.anchor)||!pluckFinite(target)
        ||!std::isfinite(dt)||dt<=0.f||dt>1.f/30.f+.000001f||!std::isfinite(tau)||tau<dt)return false;
    s.velocity=pluckAdd(s.velocity,pluckScale(pluckSub(target,s.velocity),dt/tau));
    s.position=pluckAdd(s.position,pluckScale(s.velocity,dt));
    // Creature::update captures the fixed point AFTER both moveNew passes.
    if(pluckLength(target)<.01f) {
        if(!s.fixed){s.fixed=true;s.anchor=s.position;}
    } else s.fixed=false;
    if(s.fixed) {
        const auto delta=pluckSub(s.anchor,s.position);const float distance=pluckLength(delta);
        if(distance>0.f&&distance<30.f)s.velocity=pluckScale(delta,10.f);
    }
    return pluckFinite(s.position)&&pluckFinite(s.velocity);
}
static bool pluckPulseSettled(const SdlPluckState& s) {
    return s.fixed&&pluckLength(s.velocity)<=1.f&&pluckLength(pluckSub(s.position,s.anchor))<=.1f;
}
// END SDL PLUCK PULSE POLICY

// BEGIN SDL PLUCK FORCE DIAGNOSTIC
// Exactly the existing planar-force/tau admission predicate, separated only
// to identify its failing operand. A queued post-movement collision impulse is
// NOT declared safe or discarded; the original fail-closed policy is retained.
static unsigned pluckForceGuardMask(SdlPluckPoint acceleration, SdlPluckPoint transient, float tau) {
    unsigned mask=0;
    if(!(pluckLength(acceleration)<.0001f)) mask|=1u;
    if(!(pluckLength(transient)<.0001f)) mask|=2u;
    if(!(std::isfinite(tau) && tau>=1.f/30.f)) mask|=4u;
    return mask;
}
struct SdlPluckForceSample {
    float acceleration[3]={},transient[3]={};
    float tau=0.f;
    int tick=-1;
};
// END SDL PLUCK FORCE DIAGNOSTIC


static const auto fixtureStarted=std::chrono::steady_clock::now();
static void milestone(const char* name,int tick) {
    const double seconds=std::chrono::duration<double>(std::chrono::steady_clock::now()-fixtureStarted).count();
    std::printf("P2_PURPLE_TIMING milestone=%s tick=%d wall_seconds=%.3f\n",name,tick,seconds);
}
static void p2_fixture_require_captain(bool present,bool dead,bool managerDead,bool deadState,float hp,int tick,bool missingAllowed) {
    if (!present && missingAllowed && !dead && !managerDead) return;
    if (present && !dead && !managerDead && !deadState && std::isfinite(hp) && hp > 1.0f) return;
    std::printf("P2_FIXTURE_CAPTAIN_DOWN tick=%d hp=%.3f present=%d orima_dead=%d manager_dead=%d dead_state=%d outcome=BLOCKED\n",tick,hp,int(present),int(dead),int(managerDead),int(deadState));
    std::fflush(nullptr); std::_Exit(86);
}
static void require(bool ok, const char* why) {
    if (!ok) { std::printf("P2_PURPLE_COMBAT_FAIL reason=%s\n",why); std::fflush(nullptr); std::_Exit(1); }
}
static SDL_Joystick* ordinaryPad=nullptr;
static void ordinaryCapture(const char* path) {
    pc_gfx_flush_batch();
    auto bind=reinterpret_cast<PFNGLBINDFRAMEBUFFERPROC>(SDL_GL_GetProcAddress("glBindFramebuffer"));
    require(bind!=nullptr,"ordinary capture framebuffer entry point");
    GLint previous=0;glGetIntegerv(GL_FRAMEBUFFER_BINDING,&previous);bind(GL_FRAMEBUFFER,0);
    int width=0,height=0;SDL_GL_GetDrawableSize(SDL_GL_GetCurrentWindow(),&width,&height);
    require(width>0 && height>0,"ordinary capture dimensions");
    std::vector<unsigned char> pixels(size_t(width)*size_t(height)*3);
    glReadBuffer(GL_BACK);glPixelStorei(GL_PACK_ALIGNMENT,1);
    glReadPixels(0,0,width,height,GL_RGB,GL_UNSIGNED_BYTE,pixels.data());bind(GL_FRAMEBUFFER,previous);
    FILE* file=std::fopen(path,"wb");require(file!=nullptr,"ordinary capture file");
    std::fprintf(file,"P6\n%d %d\n255\n",width,height);
    for(int y=height-1;y>=0;--y) std::fwrite(pixels.data()+size_t(y)*width*3,1,size_t(width)*3,file);
    std::fclose(file);
    std::printf("P2_PURPLE_ORDINARY_CAPTURE path=%s width=%d height=%d read_only=1\n",path,width,height);
}
static void ordinaryInput(unsigned buttons=0,int y=0,int x=0,bool nativeAxisUnits=false) {
    require(ordinaryPad!=nullptr,"ordinary SDL controller missing");
    require(std::abs(x)<=74 && std::abs(y)<=74,"ordinary SDL axes out of range");
    const int instance=SDL_JoystickInstanceID(ordinaryPad);int assigned=-1;
    if(pc_window_input_get_assignment(0,&assigned)!=PC_INPUT_DEV_GAMEPAD || assigned!=instance) {
        pc_window_input_assign(0,PC_INPUT_DEV_GAMEPAD,instance);pc_window_input_assign(1,PC_INPUT_DEV_NONE,-1);
    }
    SDL_JoystickSetVirtualButton(ordinaryPad,SDL_CONTROLLER_BUTTON_A,(buttons&KBBTN_A)!=0);
    SDL_JoystickSetVirtualButton(ordinaryPad,SDL_CONTROLLER_BUTTON_B,(buttons&KBBTN_B)!=0);
    SDL_JoystickSetVirtualButton(ordinaryPad,SDL_CONTROLLER_BUTTON_START,(buttons&KBBTN_START)!=0);
    // Native pad conversion divides SDL axes by 256. Preserve acquisition's
    // native stick units; keep the already observed save-menu deflection intact.
    SDL_JoystickSetVirtualAxis(ordinaryPad,SDL_CONTROLLER_AXIS_LEFTX,Sint16(nativeAxisUnits?x*256:x*32767/74));
    SDL_JoystickSetVirtualAxis(ordinaryPad,SDL_CONTROLLER_AXIS_LEFTY,Sint16(nativeAxisUnits?-y*256:-y*32767/74));
    SDL_JoystickUpdate();
}
static void ordinaryController() {
    SDL_SetHint(SDL_HINT_JOYSTICK_ALLOW_BACKGROUND_EVENTS,"1");
    const int device=SDL_JoystickAttachVirtual(SDL_JOYSTICK_TYPE_GAMECONTROLLER,SDL_CONTROLLER_AXIS_MAX,SDL_CONTROLLER_BUTTON_MAX,0);
    require(device>=0,"attach ordinary SDL controller");
    char guid[64];SDL_JoystickGetGUIDString(SDL_JoystickGetDeviceGUID(device),guid,sizeof(guid));
    const std::string mapping=std::string(guid)+",Purple ordinary save pad,a:b0,b:b1,x:b2,y:b3,back:b4,guide:b5,start:b6,leftstick:b7,rightstick:b8,leftshoulder:b9,rightshoulder:b10,dpup:b11,dpdown:b12,dpleft:b13,dpright:b14,leftx:a0,lefty:a1,rightx:a2,righty:a3,lefttrigger:a4,righttrigger:a5,";
    require(SDL_GameControllerAddMapping(mapping.c_str())>=0 && SDL_IsGameController(device),"map ordinary SDL controller");
    ordinaryPad=SDL_JoystickOpen(device);require(ordinaryPad && SDL_JoystickIsVirtual(device),"open actual virtual P1");
    ordinaryInput();
    std::printf("P2_PURPLE_ORDINARY_CONTROLLER instance=%d SDL_virtual=1 menu_input_script=0\n",int(SDL_JoystickInstanceID(ordinaryPad)));
}
static int ordinaryCards() {
    int count=0;const std::filesystem::path directory("../../campaign");
    if(std::filesystem::exists(directory)) for(const auto& file:std::filesystem::directory_iterator(directory))
        if(file.path().extension()==".sav") ++count;
    return count;
}
static void auditTerrain(const char* owner,const Vector3f& centre,float radius) {
    if(!mapMgr || !std::isfinite(radius) || radius<0) return;
    // Observations only: ring samples cannot certify all intervening terrain.
    for(int i=-1;i<16;++i) {
        const float angle=i*6.283185307f/16.f;
        const float x=centre.x+(i<0?0:radius*std::cos(angle));
        const float z=centre.z+(i<0?0:radius*std::sin(angle));
        CollTriInfo* tri=mapMgr->getCurrTri(x,z,true);
        std::printf("P2_PURPLE_TERRAIN owner=%s sample=%d x=%.3f z=%.3f y=%.3f triangle=%d map_code=%u radius=%.3f\n",
            owner,i,x,z,mapMgr->getMinY(x,z,true),int(tri!=nullptr),tri?unsigned(tri->mMapCode):0,radius);
    }
}
static void auditPart(const char* owner,CollPart* part,int depth=0) {
    if(!part) return;
    require(depth<32,"collision audit tree depth");
    std::printf("P2_PURPLE_COLLISION_PART owner=%s depth=%d id=%u type=%u active=%d xyz=%.3f,%.3f,%.3f radius=%.3f\n",
        owner,depth,unsigned(part->getID().mId),unsigned(part->mPartType),int(part->mIsUpdateActive),
        part->mCentre.x,part->mCentre.y,part->mCentre.z,part->mRadius);
    for(int i=0;i<part->getChildCount();++i) auditPart(owner,part->getChildAt(i),depth+1);
}
static void auditBody(const char* owner,Creature* creature) {
    if(!creature || !creature->isAlive()) return;
    const Vector3f centre=creature->getBoundingSphereCentre();
    const float radius=creature->getBoundingSphereRadius();
    std::printf("P2_PURPLE_BODY owner=%s xyz=%.3f,%.3f,%.3f bound=%.3f,%.3f,%.3f radius=%.3f collision_radius=%.3f\n",
        owner,creature->mSRT.t.x,creature->mSRT.t.y,creature->mSRT.t.z,centre.x,centre.y,centre.z,radius,creature->mCollisionRadius);
    if(creature->mCollInfo && creature->mCollInfo->hasInfo()) auditPart(owner,creature->mCollInfo->getBoundingSphere());
    auditTerrain(owner,centre,radius);
}
// Read-only fixture telemetry. Form inherited member pointers in a derived
// scope, then apply them to the actual ActTransport; no layout casts/mutations.
struct PurpleTransportTrace : ActTransport {
    static void emit(ActTransport* action, Piki* piki) {
        const int state=action->*(&PurpleTransportTrace::mState);
        if(state!=STATE_Move && state!=STATE_Guru && state!=STATE_Goal) {
            std::printf("P2_PURPLE_HAUL_ACTION state=%d route_not_started=1\n",state);return;
        }
        const int count=action->*(&PurpleTransportTrace::mNumRoutePoints);
        const int index=action->*(&PurpleTransportTrace::mPathIndex);
        const int next=action->*(&PurpleTransportTrace::mNextPathIndex);
        static bool routeAudited=false;
        if(!routeAudited && routeMgr && count>0) {
            routeAudited=true;
            for(int i=0;i<count;++i) {
                const int id=piki->mPathBuffers[i].mWayPointIdx;
                WayPoint* wp=routeMgr->getWayPoint('test',id);
                if(wp) std::printf("P2_PURPLE_FULL_ROUTE index=%d id=%d xyz=%.3f,%.3f,%.3f open=%d water=%d\n",
                    i,id,wp->mPosition.x,wp->mPosition.y,wp->mPosition.z,int(wp->mIsOpen),int(wp->inWater()));
            }
        }
        std::printf("P2_PURPLE_HAUL_ACTION state=%d route_count=%d path_index=%d next_index=%d path_type=%d slot=%d can_carry=%d stall_timer=%.3f better_pathfinding=%d\n",
            state,count,index,next,
            int(action->*(&PurpleTransportTrace::mPathType)),action->*(&PurpleTransportTrace::mSlotIndex),
            int(action->*(&PurpleTransportTrace::mCanCarry)),action->*(&PurpleTransportTrace::mPcStallTimer),int(pc_settings_get_better_pathfinding()));
        if(routeMgr && index>=0 && index<count) {
            const int id=piki->mPathBuffers[index].mWayPointIdx;
            WayPoint* wp=routeMgr->getWayPoint('test',id);
            if(wp) std::printf("P2_PURPLE_HAUL_WAYPOINT id=%d xyz=%.2f,%.2f,%.2f open=%d flags=%u\n",
                id,wp->mPosition.x,wp->mPosition.y,wp->mPosition.z,int(wp->mIsOpen),unsigned(wp->mFlags));
        }
    }
};
class PurpleCombatApp : public PlugPikiApp {
    struct PluckObstacle { Vector3f centre; float radius; };
    std::vector<PluckObstacle> pluckObstacles;
    std::vector<Vector3f> pluckRoute;
    size_t pluckRouteIndex=0;
    bool sdlPluckBraking=false;
    SdlPluckForceSample sdlPreviousForceSample;
    bool sdlPulseActive=false;
    int sdlPulseFrames=0;
    SdlPluckState sdlPulseBefore;
    SdlPluckPoint sdlPulseCommand;

    PikiHeadItem* routedHead=nullptr;
    Vector3f routedHeadPosition;
    static float planarDistance(const Vector3f& a,const Vector3f& b) {
        const float x=a.x-b.x,z=a.z-b.z;return std::sqrt(x*x+z*z);
    }
    bool pluckSegmentClear(const Vector3f& a,const Vector3f& b) const {
        const float dx=b.x-a.x,dz=b.z-a.z,length2=dx*dx+dz*dz;
        for(const auto& obstacle:pluckObstacles) {
            const float t=length2>0?std::max(0.f,std::min(1.f,((obstacle.centre.x-a.x)*dx+(obstacle.centre.z-a.z)*dz)/length2)):0.f;
            const float x=a.x+t*dx-obstacle.centre.x,z=a.z+t*dz-obstacle.centre.z;
            if(x*x+z*z<obstacle.radius*obstacle.radius) return false;
        }
        return true;
    }
    void collectCaptainParts(CollPart* part,std::vector<CollPart*>& parts,int depth=0) {
        if(!part) return;
        require(depth<32,"captain collision tree depth");
        require(!part->isCylinderType() && !part->isTubeType(),"captain approach needs explicit non-sphere collision support");
        if(part->isCollisionType()) parts.push_back(part);
        for(int i=0;i<part->getChildCount();++i) collectCaptainParts(part->getChildAt(i),parts,depth+1);
    }
    void collectPluckObstacles(CollPart* part,Navi* n,const std::vector<CollPart*>& captainParts,int depth=0) {
        if(!part) return;
        require(depth<32,"pluck collision tree depth");
        require(!part->isCylinderType() && !part->isTubeType(),"Violet approach needs explicit non-sphere collision support");
        if(part->isCollisionType()) {
            for(CollPart* captain:captainParts) {
                // Creature::collisionCheck uses CollInfo pairs, not the ground
                // collision radius. Translate each sphere's actual offset into
                // a forbidden captain-origin circle. An all-yaw radius falsely
                // excluded reachable pluck positions in round05. Refresh every
                // frame as pose/yaw changes; admit only flat sampled terrain.
                const Vector3f offset=captain->mCentre-n->mSRT.t;
                const float sum=part->mRadius+captain->mRadius+1.f;
                const float dy=std::max(0.f,std::fabs(part->mCentre.y-captain->mCentre.y)-.1f);
                if(sdlAcquisitionMode()) {
                    const Vector3f separation=part->mCentre-captain->mCentre;
                    std::printf("P2_PURPLE_PLUCK_PAIR tick=%d captain_id=%u violet_id=%u captain_centre=%.6f,%.6f,%.6f captain_radius=%.6f violet_centre=%.6f,%.6f,%.6f violet_radius=%.6f offset=%.6f,%.6f,%.6f raw_sphere_gap=%.6f padded_sum=%.6f padded_dy=%.6f projected=%d read_only=1\n",
                        ticks,unsigned(captain->getID().mId),unsigned(part->getID().mId),captain->mCentre.x,captain->mCentre.y,captain->mCentre.z,captain->mRadius,
                        part->mCentre.x,part->mCentre.y,part->mCentre.z,part->mRadius,offset.x,offset.y,offset.z,
                        std::sqrt(separation.x*separation.x+separation.y*separation.y+separation.z*separation.z)-part->mRadius-captain->mRadius,sum,dy,int(dy<sum));
                }
                if(dy<sum) pluckObstacles.push_back({Vector3f(part->mCentre.x-offset.x,n->mSRT.t.y,part->mCentre.z-offset.z),
                    std::sqrt(sum*sum-dy*dy)});
            }
        }
        for(int i=0;i<part->getChildCount();++i) collectPluckObstacles(part->getChildAt(i),n,captainParts,depth+1);
    }
    void refreshPluckObstacles(Navi* n,Pom* violet) {
        require(n->mCollInfo && n->mCollInfo->hasInfo(),"live captain collision parts required");
        require(violet && violet->mCollInfo && violet->mCollInfo->hasInfo(),"live Violet collision parts required");
        std::vector<CollPart*> captainParts;
        collectCaptainParts(n->mCollInfo->getBoundingSphere(),captainParts);
        require(!captainParts.empty(),"captain collision parts absent");
        pluckObstacles.clear();
        collectPluckObstacles(violet->mCollInfo->getBoundingSphere(),n,captainParts);
    }
    void pluckTrace(const char* event,Navi* n,PikiHeadItem* head,Pom* violet) {
        if(!sdlAcquisitionMode())return;
        const double seconds=std::chrono::duration<double>(std::chrono::steady_clock::now()-fixtureStarted).count();
        float clearance=std::numeric_limits<float>::infinity();
        for(const auto& obstacle:pluckObstacles)clearance=std::min(clearance,planarDistance(n->mSRT.t,obstacle.centre)-obstacle.radius);
        CollPart* captainPart=nullptr;CollPart* violetPart=nullptr;Vector3f push(0,0,0);
        const bool contact=n->mCollInfo && n->mCollInfo->hasInfo() && violet->mCollInfo && violet->mCollInfo->hasInfo()
            && n->mCollInfo->checkCollision(violet->mCollInfo,&captainPart,&violetPart,push);
        std::printf("P2_PURPLE_PLUCK_TRACE event=%s tick=%d wall_seconds=%.6f dt=%.9f captain=%.6f,%.6f,%.6f head=%p head_xyz=%.6f,%.6f,%.6f can_pull=%d purple_head=%d violet=%p violet_xyz=%.6f,%.6f,%.6f violet_state=%d range=%.6f velocity=%.6f,%.6f,%.6f target_velocity=%.6f,%.6f,%.6f face=%.6f navi_state=%d raw=%d,%d normalized=%.6f,%.6f waypoint=%u route_size=%u obstacles=%u min_start_clearance=%.6f raw_contact=%d captain_part=%u violet_part=%u push=%.6f,%.6f,%.6f captain_atari=%d violet_atari=%d read_only=1\n",
            event,ticks,seconds,gsys->getFrameTime(),n->mSRT.t.x,n->mSRT.t.y,n->mSRT.t.z,static_cast<void*>(head),head->mSRT.t.x,head->mSRT.t.y,head->mSRT.t.z,
            int(head->canPullout()),int(head->mP2Purple),static_cast<void*>(violet),violet->mSRT.t.x,violet->mSRT.t.y,violet->mSRT.t.z,violet->getCurrentState(),C_NAVI_PARM(n,mPluckDistanceOutsideOnyon),
            n->mVelocity.x,n->mVelocity.y,n->mVelocity.z,n->mTargetVelocity.x,n->mTargetVelocity.y,n->mTargetVelocity.z,n->mFaceDirection,n->getCurrState()->getID(),
            n->mKontroller?int(n->mKontroller->mMainStickX):0,n->mKontroller?int(n->mKontroller->mMainStickY):0,
            n->mKontroller?n->mKontroller->getMainStickX():0,n->mKontroller?n->mKontroller->getMainStickY():0,
            unsigned(pluckRouteIndex),unsigned(pluckRoute.size()),unsigned(pluckObstacles.size()),clearance,int(contact),
            captainPart?unsigned(captainPart->getID().mId):0,violetPart?unsigned(violetPart->getID().mId):0,push.x,push.y,push.z,int(n->isAtari()),int(violet->isAtari()));
    }
    void planPluckRoute(Navi* n,PikiHeadItem* head,Pom* violet,float pluckRange) {
        require(violet && violet->mCollInfo && violet->mCollInfo->hasInfo(),"Violet collision data required for ordinary approach");
        pluckObstacles.clear();pluckRoute.clear();pluckRouteIndex=0;
        refreshPluckObstacles(n,violet);
        pluckTrace("plan_begin",n,head,violet);
        auditBody("captain_route",n);
        for(const auto& obstacle:pluckObstacles) std::printf("P2_PURPLE_PLUCK_OBSTACLE xyz=%.3f,%.3f,%.3f radius=%.3f live_part_pairs=1\n",
            obstacle.centre.x,obstacle.centre.y,obstacle.centre.z,obstacle.radius);
        std::vector<Vector3f> nodes{n->mSRT.t};std::vector<bool> goal{false};
        auto addNode=[&](Vector3f p,bool isGoal) {
            // A stopped SDL replan must not select the same nearby corner
            // that required braking. Find a farther strictly clear route or
            // retain the existing bounded no-route refusal; never reverse
            // a minimum-strength walking command across an arrival point.
            if(sdlAcquisitionMode() && !isGoal && planarDistance(n->mSRT.t,p)<=4.f) return;
            if(pluckSegmentClear(p,p)) {nodes.push_back(p);goal.push_back(isGoal);}
        };
        // Choose a reachable position inside the engine's actual pluck range,
        // using the real sprout and current Violet parts. This plans controller
        // inputs only; it never moves actors or edits the game's route graph.
        if(sdlAcquisitionMode()) {
            // The native pluck contract is a disk, not a four-unit arrival ball.
            // At each bearing choose the point with most slack to BOTH the
            // actual pluck gate and every live projected collision pair.
            for(int i=0;i<64;++i) {
                const float angle=i*6.283185307f/64.f;float best=.5f;Vector3f selected;
                for(float radius=.5f;radius<pluckRange-.25f;radius+=.25f) {
                    Vector3f point=head->mSRT.t+Vector3f(radius*std::cos(angle),0,radius*std::sin(angle));
                    float slack=pluckRange-.25f-radius;
                    for(const auto& obstacle:pluckObstacles)slack=std::min(slack,planarDistance(point,obstacle.centre)-obstacle.radius);
                    if(slack>best){best=slack;selected=point;}
                }
                if(best>.5f)addNode(selected,true);
            }
        } else {
            const float goalRadius=pluckRange*.95f;
            for(int i=0;i<32;++i) {
                const float a=i*6.283185307f/32.f;
                addNode(head->mSRT.t+Vector3f(goalRadius*std::cos(a),0,goalRadius*std::sin(a)),true);
            }
        }
        for(const auto& obstacle:pluckObstacles) for(int i=0;i<16;++i) {
            const float a=i*6.283185307f/16.f;
            const float r=obstacle.radius/std::cos(3.141592654f/16.f)+4.f;
            addNode(obstacle.centre+Vector3f(r*std::cos(a),0,r*std::sin(a)),false);
        }
        const size_t count=nodes.size();std::vector<float> cost(count,std::numeric_limits<float>::infinity());
        std::vector<int> parent(count,-1);std::vector<bool> visited(count,false);cost[0]=0;int end=-1;
        for(size_t iteration=0;iteration<count;++iteration) {
            int here=-1;for(size_t i=0;i<count;++i) if(!visited[i] && (here<0 || cost[i]<cost[here])) here=int(i);
            if(here<0 || !std::isfinite(cost[here])) break;
            visited[here]=true;if(goal[here]) {end=here;break;}
            for(size_t next=0;next<count;++next) if(!visited[next] && pluckSegmentClear(nodes[here],nodes[next])) {
                const float candidate=cost[here]+planarDistance(nodes[here],nodes[next]);
                if(candidate<cost[next]) {cost[next]=candidate;parent[next]=here;}
            }
        }
        if(sdlAcquisitionMode()) {
            unsigned goals=0,reachable=0;for(size_t i=0;i<count;++i)if(goal[i]){++goals;if(std::isfinite(cost[i]))++reachable;}
            std::printf("P2_PURPLE_PLUCK_GRAPH tick=%d nodes=%u goals=%u reachable_goals=%u end=%d start_clear=%d read_only=1\n",
                ticks,unsigned(count),goals,reachable,end,int(pluckSegmentClear(n->mSRT.t,n->mSRT.t)));
            if(end<0)pluckTrace("plan_failure",n,head,violet);
        }
        require(end>=0,"no collision-clear controller approach to native pluck range");
        for(int i=end;i>0;i=parent[i]) {require(parent[i]>=0,"invalid pluck route");pluckRoute.push_back(nodes[i]);}
        std::reverse(pluckRoute.begin(),pluckRoute.end());
        Vector3f previous=n->mSRT.t;
        for(size_t i=0;i<pluckRoute.size();++i) {
            Vector3f& next=pluckRoute[i];const int samples=int(std::ceil(planarDistance(previous,next)/5.f))+1;
            for(int j=0;j<=samples;++j) {
                const float t=float(j)/samples,x=previous.x+(next.x-previous.x)*t,z=previous.z+(next.z-previous.z)*t;
                CollTriInfo* tri=mapMgr->getCurrTri(x,z,true);const float y=mapMgr->getMinY(x,z,true);
                require(tri && MapCode::getAttribute(tri)!=ATTR_Water && MapCode::getAttribute(tri)!=ATTR_Hole
                    && std::isfinite(y) && std::fabs(y-n->mSRT.t.y)<.1f,"pluck approach needs flat terrain for live sphere projection");
            }
            next.y=mapMgr->getMinY(next.x,next.z,true);
            std::printf("P2_PURPLE_PLUCK_WAYPOINT index=%u xyz=%.3f,%.3f,%.3f actor_position_injected=0\n",unsigned(i),next.x,next.y,next.z);
            previous=next;
        }
        routedHead=head;routedHeadPosition=head->mSRT.t;
        std::printf("P2_PURPLE_PLUCK_ROUTE length=%.3f waypoints=%u collision_parts=%u loaded_range=%.3f ground_collision_radius=%.3f live_part_pairs=1 scripted_controller_only=1\n",
            cost[end],unsigned(pluckRoute.size()),unsigned(pluckObstacles.size()),pluckRange,n->mCollisionRadius);
    }
    int ticks=0, phase=0, phaseTicks=0, startingField=0, pluckAttempts=0;
    int combatTicks=0, observedTicks=0, throwAttempts=0, throwTick=0;
    bool captainSeen=false, thrown=false, descentStaged=false, isolated=false;
    bool activeSeen=false,guardInjected=false,haulAttached=false;
    Piki* input=nullptr;
    Piki* acquired=nullptr;
    bool manualWithdrawRequested=false;
    BTeki* target=nullptr;
    unsigned targetUid=0;
    float initialHealth=0, maxQueued=0, regeneration=0;
    int regenerationFrames=0;
    Vector3f parkPosition;
    bool sunsetRequested=false, sunsetSeen=false;
    int sunsetTicks=0, sunsetDay=-1, expectedDay=-1, savedMaturity=-1, resumeReady=0;
    int ordinaryMenuFrames=0,ordinaryDiaryFrames=0;
    bool releaseDiaryInput=false,diaryRevealObserved=false,diaryAdvanceObserved=false;
    bool releaseObservedSaveInput=false;
    unsigned observedSaveActions=0;
    int sdlPhase=0,sdlStableAim=0,sdlThrowTicks=0;
    bool sdlStarted=false,sdlThrowObserved=false,sdlGeometryLogged=false;
    bool sdlAimReleasePending=false;
    Piki* sdlTracePiki=nullptr;
    int sdlTracePikiState=-1;
    int diaryActions=0;
    unsigned saveIndexBefore=0;
    bool mode(const char* name) const {
        const char* value=std::getenv("P2_PURPLE_COMBAT_MODE");
        return value && std::strcmp(value,name)==0;
    }
    bool sdlAcquisitionMode() const { return mode("sdl_acquire") || mode("sdl_dayend"); }
    bool ordinarySaveMode() const { return mode("natural_dayend") || mode("sdl_dayend"); }
    void injectInitializedGuard(Navi* n) {
        const char* test=std::getenv("P2_PURPLE_GUARD_CASE");
        if(!test && std::getenv("P2_FIXTURE_FORCE_CAPTAIN_DOWN")) test="health";
        if(!test || guardInjected || !n || !n->getCurrState() || !mapMgr || !pikiMgr) return;
        const int state=n->getCurrState()->getID();
        if(state!=NAVISTATE_Walk && state!=NAVISTATE_Idle) return;
        // Startup briefly exposes a Walk captain before the landing movie and
        // squad exist. Inject only after the required live fixture baseline;
        // the unconditional real guard below still protects every earlier frame.
        if(gameflow.mPauseAll || gameflow.mIsUIOverlayActive
            || (gameflow.mMoviePlayer && gameflow.mMoviePlayer->mIsActive)) return;
        GameStat::update();
        if(int(GameStat::mapPikis)!=20) return;
        guardInjected=true;captainSeen=true;
        std::printf("P2_PURPLE_GUARD_ARMED case=%s initialized=1 tick=%d health_before=%.3f field=%d state=%d\n",test,ticks,n->mHealth,int(GameStat::mapPikis),state);
        milestone("initialized_guard_injection",ticks);
        if(!std::strcmp(test,"health_pause")) gameflow.mPauseAll=true;
        if(!std::strcmp(test,"missing_movie")) {
            require(gameflow.mMoviePlayer!=nullptr,"initialized movie guard requires movie player");
            gameflow.mMoviePlayer->mIsActive=true;
        }
        if(!std::strcmp(test,"missing") || !std::strcmp(test,"missing_movie")) naviMgr=nullptr;
        else if(!std::strcmp(test,"manager")) naviMgr->informOrimaDead(n);
        else if(!std::strcmp(test,"global")) GameStat::orimaDead=true;
        else if(!std::strcmp(test,"dead_state")) n->mStateMachine->transit(n,NAVISTATE_Dead);
        else n->mHealth=0;
        std::printf("P2_PURPLE_GUARD_INJECTED case=%s pause=%d movie=%d manager_present=%d\n",test,int(gameflow.mPauseAll),int(gameflow.mMoviePlayer && gameflow.mMoviePlayer->mIsActive),int(naviMgr!=nullptr));
    }
    bool stockOne() const {
        return savedMaturity>=0 && savedMaturity<3 && p2ship::stock.total()==1
            && p2ship::stock.counts[0][savedMaturity]==1;
    }
    void boundAdult(bool liveRequired=true) {
        require(pc_p2_purple_direct_enabled(),"combat profile missing after save/restart");
        // Restart confirms the map's default Impact Site, where this Hope
        // generator is absent. The saved seed mapping must still be exact;
        // never manufacture an actor merely to validate an absent-stage row.
        require(pc_randomizer_p2_source_for_id(3640055869u)==2,"persisted seed combat mapping mismatch");
        bool found=false;
        Iterator it(tekiMgr);
        CI_LOOP(it) {
            BTeki* actor=static_cast<BTeki*>(*it);
            if (actor && actor->isAlive() && pc_p2_campaign_source(actor)==2
                && pc_p2_purple_direct_adult_registered(actor)) {
                std::printf("P2_PURPLE_PERSIST_BINDING uid=%u source=2 registered=1\n",pc_p2_campaign_token(actor));
                found=true; break;
            }
        }
        std::printf("P2_PURPLE_PERSIST_CATALOG uid=3640055869 source=2 profile_enabled=1 live_registered=%d live_required=%d stage=%d\n",
            int(found),int(liveRequired),gameflow.mCurrentStageID);
        require(!liveRequired || found,"no exact live adult combat binding in persistence fixture");
    }
    void sunsetStep() {
        require(++sunsetTicks<9000,"ordinary day-save timeout");
        require(gameflow.mCurrGameSectionID==SECTION_OnePlayer && flowCont.mGameEndFlag==GAMEEND_None,
            "sunset left ordinary healthy campaign");
        if(gameflow.mIsDayEndActive) sunsetSeen=true;
        require(gameflow.mWorldClock.mCurrentDay<=expectedDay,"unexpected extra day advance");
        if(sunsetSeen && gameflow.mGamePrefs.mHasSaveGame
            && gameflow.mGamePrefs.mMostRecentSaveIndex!=saveIndexBefore) {
            require(gameflow.mWorldClock.mCurrentDay==expectedDay && stockOne(),"day-save identity/maturity/day mismatch");
            pc_p2_input_script_clear(1);
            std::printf("P2_PURPLE_PERSIST_SAVED day_before=%d day=%d maturity=%d stock=1 native_save_index_before=%u native_save_index_after=%u external_CAMPAIGN_SAVED_required=1 identity_injected=0 maturity_injected=0\n",
                sunsetDay,expectedDay,savedMaturity,saveIndexBefore,unsigned(gameflow.mGamePrefs.mMostRecentSaveIndex));
            std::fflush(nullptr); std::_Exit(0);
        }
        const bool confirming=sunsetSeen && gameflow.mWorldClock.mCurrentDay==expectedDay;
        pc_p2_input_script_set(1,confirming && sunsetTicks%20<4?KBBTN_A:0,0,0);
        if(sunsetTicks%120==0) std::printf("P2_PURPLE_PERSIST_PROGRESS ticks=%d day=%d active=%d stock=%d\n",
            sunsetTicks,gameflow.mWorldClock.mCurrentDay,int(gameflow.mIsDayEndActive),p2ship::stock.total());
    }
    void beginPersistence(Navi* n) {
        require(acquired && acquired->isAlive() && pc_p2_is_purple(acquired),"persistence requires naturally acquired Purple");
        require(!pc_randomizer_resumed() && p2ship::stock.total()==0,"day-save requires fresh empty baseline");
        boundAdult(); savedMaturity=acquired->mHappa;
        require(savedMaturity>=0 && savedMaturity<3,"invalid acquired maturity");
        GameStat::update(); const int field=GameStat::mapPikis;
        require(field==20,"fresh conversion must conserve starting20");
        require(pc_p2_ship_deposit(acquired) && stockOne() && int(GameStat::mapPikis)==field-1,"deposit identity/population");
        Piki* restored=pc_p2_ship_withdraw(n,3);
        require(restored && pc_p2_is_purple(restored) && !restored->mP2White
            && restored->mHappa==savedMaturity && pc_piki_carry_strength(restored)==10
            && pc_throw_selection_class(restored)==4 && p2ship::stock.total()==0
            && int(GameStat::mapPikis)==field && restored->mMode==PikiMode::FormationMode,"withdraw identity/population");
        sunsetDay=gameflow.mWorldClock.mCurrentDay; expectedDay=pc_randomizer_next_day(sunsetDay);
        require(expectedDay==sunsetDay+1 && flowCont.mGameEndFlag==GAMEEND_None,"ordinary next day required");
        saveIndexBefore=gameflow.mGamePrefs.mMostRecentSaveIndex;
        sunsetRequested=true; acquired=nullptr; input=nullptr;
        pc_p2_input_script_set(1,0,0,0);
        std::printf("P2_PURPLE_PERSIST_BEGIN day=%d expected_day=%d maturity=%d field=%d stock=0 identity_injected=0 maturity_injected=0 clock_advanced=1 menu_input_scripted=1\n",
            sunsetDay,expectedDay,savedMaturity,field);
        gameflow.mWorldClock.setTime(gameflow.mParameters->mEndHour());
    }
    void beginOrdinarySave(Navi* n) {
        require(acquired && acquired->isAlive() && pc_p2_is_purple(acquired)
            && acquired->mMode==PikiMode::FormationMode && acquired->mNavi==n,"ordinary save requires acquired formation Purple");
        require(!pc_randomizer_resumed() && ordinaryCards()==0 && p2ship::stock.total()==0,"ordinary save fresh checkpoint/stock baseline");
        GameStat::update();require(int(GameStat::mapPikis)==20,"ordinary save acquisition conserves20");
        boundAdult();savedMaturity=acquired->mHappa;
        require(savedMaturity>=0 && savedMaturity<3,"ordinary save maturity");
        sunsetDay=gameflow.mWorldClock.mCurrentDay;expectedDay=pc_randomizer_next_day(sunsetDay);
        require(expectedDay==sunsetDay+1 && flowCont.mGameEndFlag==GAMEEND_None,"ordinary next day");
        sunsetRequested=true;pc_p2_input_script_clear(1);ordinaryInput(KBBTN_START);
        if(mode("sdl_dayend")) releaseObservedSaveInput=true;
        acquired=nullptr;input=nullptr; // Fixture references must not outlive native sunset teardown.
        milestone("ordinary_sunset_menu_requested",ticks);
        std::printf("P2_PURPLE_ORDINARY_SAVE_BEGIN day=%d expected_day=%d maturity=%d field=20 stock=0 direct_stock_helpers=0 clock_advanced=0 SDL_menu_input=1\n",
            sunsetDay,expectedDay,savedMaturity);
    }
    void observedSaveInput(bool confirming) {
        if(confirming) {
            if(++ordinaryDiaryFrames==1) milestone("ordinary_day_advanced",ticks);
        } else ++ordinaryMenuFrames;
        if(releaseObservedSaveInput) {
            ordinaryInput();releaseObservedSaveInput=false;return;
        }
        const PcPauseSnapshot pause=pc_pause_observe();
        const PcDiaryAction diary=pc_diary_observe();
        const PcSaveUiSnapshot save=pc_save_ui_observe();
        const PurpleSaveInput action=purple_save_input(confirming,pause,diary,save);
        require(action!=PurpleSaveInput::Unexpected,"unexpected ordinary save menu/slot/secondary prompt");
        if(action==PurpleSaveInput::Neutral) {ordinaryInput();return;}
        require(++observedSaveActions<240,"bounded observed save input actions");
        if(action==PurpleSaveInput::RevealDiary || action==PurpleSaveInput::AdvanceDiary) {
            ++diaryActions;
            const bool reveal=action==PurpleSaveInput::RevealDiary;
            diaryRevealObserved|=reveal;diaryAdvanceObserved|=!reveal;
            ordinaryInput(reveal?KBBTN_B:KBBTN_A);
            std::printf("P2_PURPLE_ORDINARY_DIARY action=%d input=%s observer=%d SDL_input=1\n",diaryActions,reveal?"B":"A",int(diary));
        } else if(action==PurpleSaveInput::Down || action==PurpleSaveInput::Up) {
            ordinaryInput(0,action==PurpleSaveInput::Down?-65:65,0,true);
        } else ordinaryInput(KBBTN_A);
        releaseObservedSaveInput=true;
        std::printf("P2_PURPLE_OBSERVED_SAVE_INPUT action=%u intent=%d pause=%d main=%d sub=%d results=%d save=%d primary=%d yes=%d slot_ready=%d slot=%d observer_read_only=1 SDL_input=1\n",
            observedSaveActions,int(action),pause.state,pause.mainSelection,pause.subSelection,save.resultState,save.saveState,
            int(save.primaryInputReady),int(save.primaryYes),int(save.cardSlotInputReady),save.cardSlot);
    }
    void ordinarySunsetStep() {
        require(++sunsetTicks<9000,"ordinary SDL day-save timeout");
        require(gameflow.mCurrGameSectionID==SECTION_OnePlayer && flowCont.mGameEndFlag==GAMEEND_None,"ordinary save left healthy campaign");
        if(gameflow.mIsDayEndActive) sunsetSeen=true;
        require(gameflow.mWorldClock.mCurrentDay<=expectedDay,"ordinary save extra day advance");
        const bool confirming=gameflow.mWorldClock.mCurrentDay==expectedDay;
        if(mode("sdl_dayend")) observedSaveInput(confirming);
        else if(!confirming) {
            ++ordinaryMenuFrames;
            if(ordinaryMenuFrames==2) ordinaryInput();
            // Preserve the observed working schedule. The earlier20-frame
            // selection attempt was ignored before menu activation (save10).
            // Panel completion/input eligibility needs more than nominal fade
            // duration; never infer an early input was accepted from a timer.
            else if(ordinaryMenuFrames==45) ordinaryInput(0,-65);
            else if(ordinaryMenuFrames==50 || ordinaryMenuFrames==66 || ordinaryMenuFrames==126) ordinaryInput();
            else if(ordinaryMenuFrames==65 || ordinaryMenuFrames==125) ordinaryInput(KBBTN_A);
        } else {
            ++ordinaryDiaryFrames;
            if(ordinaryDiaryFrames==1) milestone("ordinary_day_advanced",ticks);
            const PcDiaryAction diary=pc_diary_observe();
            // Reuse #1166's reviewed const observer. Ordinary B only reveals an
            // active unrevealed diary page; A advances a revealed page. Never
            // send B into results/card prompts, and release each diary edge.
            if(releaseDiaryInput) {ordinaryInput();releaseDiaryInput=false;}
            else if(diary==PcDiaryAction::RevealPage || diary==PcDiaryAction::AdvancePage) {
                require(++diaryActions<240,"bounded ordinary diary actions");
                const bool reveal=diary==PcDiaryAction::RevealPage;
                diaryRevealObserved|=reveal;diaryAdvanceObserved|=!reveal;
                ordinaryInput(reveal?KBBTN_B:KBBTN_A);releaseDiaryInput=true;
                std::printf("P2_PURPLE_ORDINARY_DIARY action=%d input=%s observer=%d SDL_input=1\n",diaryActions,reveal?"B":"A",int(diary));
            } else ordinaryInput(ordinaryDiaryFrames%6<5?KBBTN_A:0);
            if(ordinaryDiaryFrames%30==0) std::printf("P2_PURPLE_ORDINARY_UI observer=%d diary_frames=%d observer_read_only=1 SDL_input=1\n",int(diary),ordinaryDiaryFrames);
        }
        const int cards=ordinaryCards();require(cards<=1,"ordinary save extra checkpoint generation");
        if(cards==1) {
            require(confirming && sunsetSeen && stockOne(),"ordinary card/day/Purple stock mismatch");
            require(diaryRevealObserved && diaryAdvanceObserved,"actual ordinary diary reveal/advance missing");
            ordinaryInput();milestone("ordinary_checkpoint_committed",ticks);
            std::printf("P2_PURPLE_ORDINARY_SAVE_PASS day_before=%d day=%d maturity=%d stock=1 generations=1 direct_stock_helpers=0 clock_advanced=0 external_checkpoint_validation_required=1\n",
                sunsetDay,expectedDay,savedMaturity);
            std::fflush(nullptr);std::_Exit(0);
        }
        if(sunsetTicks%120==0) std::printf("P2_PURPLE_ORDINARY_SAVE_PROGRESS menu_frames=%d diary_frames=%d day=%d sunset_seen=%d pause=%d overlay=%d stock=%d cards=%d\n",
            ordinaryMenuFrames,ordinaryDiaryFrames,gameflow.mWorldClock.mCurrentDay,int(sunsetSeen),int(gameflow.mPauseAll),int(gameflow.mIsUIOverlayActive),p2ship::stock.total(),cards);
    }
    static int expectedNumber(const char* name,int minimum,int maximum) {
        const char* text=std::getenv(name); require(text && *text,"missing restart expectation");
        char* end=nullptr; errno=0; const long n=std::strtol(text,&end,10);
        require(!errno && end && !*end && n>=minimum && n<=maximum,"invalid restart expectation"); return int(n);
    }
    void resumePersistence(Navi* n) {
        savedMaturity=expectedNumber("P2_PURPLE_EXPECT_MATURITY",0,2);
        expectedDay=expectedNumber("P2_PURPLE_EXPECT_DAY",1,99999);
        require(pc_randomizer_resumed() && gameflow.mWorldClock.mCurrentDay==expectedDay && stockOne(),
            "native restart checkpoint/day/stock/maturity mismatch");
        if(++resumeReady<60) return;
        boundAdult(false); GameStat::update(); const int field=GameStat::mapPikis;
        Iterator bodies(pikiMgr); CI_LOOP(bodies) {
            Piki* p=static_cast<Piki*>(*bodies);
            require(!p || !p->isAlive() || !pc_p2_is_purple(p),"duplicate field Purple before withdrawal");
        }
        Piki* restored=pc_p2_ship_withdraw(n,3);
        require(restored && pc_p2_is_purple(restored) && !restored->mP2White
            && restored->mHappa==savedMaturity && pc_piki_carry_strength(restored)==10
            && pc_throw_selection_class(restored)==4 && p2ship::stock.total()==0
            && int(GameStat::mapPikis)==field+1,"restart withdrawal identity/population");
        require(!pc_p2_ship_withdraw(n,3),"restart duplicated stock");
        require(pc_p2_ship_deposit(restored) && stockOne() && int(GameStat::mapPikis)==field,"restart redeposit conservation");
        pc_p2_input_script_clear(1);
        std::printf("P2_PURPLE_PERSIST_RESUME_PASS day=%d maturity=%d stock=1 field_before=%d field_after=%d checkpoint_resumed=1 identity_injected=0 maturity_injected=0 strength=10 selection=4\n",
            expectedDay,savedMaturity,field,int(GameStat::mapPikis));
        std::fflush(nullptr); std::_Exit(0);
    }

    Pellet* haul=nullptr;
    GoalItem* haulGoal=nullptr;
    Piki* haulRed=nullptr;
    Vector3f haulStart, approachStart;
    int haulPhase=0, haulTicks=0, haulStable=0, rewardBefore=0, expectedReward=0, haulMaturity=-1, haulPopulationBefore=0;
    bool haulMoved=false, haulGoalSeen=false, haulGone=false;
    int haulRecalls=0;
    void keepHaulSquad(Navi* n) {
        // Formation can itself auto-assign transport on pellet contact. Keep
        // non-test squad members gathered throughout the run, including the
        // retired Red control. Never detach an actual helper to hide a failure.
        Iterator squad(pikiMgr); CI_LOOP(squad) {
            Piki* p=static_cast<Piki*>(*squad);
            if(!p || !p->isAlive() || p==acquired || (p==haulRed && haulPhase<=2)) continue;
            if(p->getStickObject()==haul) {
                std::printf("P2_PURPLE_HAUL_EXTRA_CARRIER purple=%d mode=%d state=%d strength=%d\n",
                    int(pc_p2_is_purple(p)),p->mMode,p->getState(),int(haul->mCarrierCounter));
                require(false,"non-test Pikmin attached before fixture recall");
            }
            if(p->getState()==PIKISTATE_Normal && p->mMode!=PikiMode::FormationMode) {
                require(p->mNavi==n,"non-test squad captain changed");
                p->changeMode(PikiMode::FormationMode,n);
                ++haulRecalls;
            }
        }
    }
    void assignHaul(Piki* p) {
        require(p && p->isAlive() && p->getState()==PIKISTATE_Normal && !p->isStickTo(),"carrier not ready for native approach");
        p->mActiveAction->abandon(nullptr);
        p->mActiveAction->mCurrActionIdx=PikiAction::Transport;
        p->mActiveAction->mChildActions[PikiAction::Transport].initialise(haul);
        p->mMode=PikiMode::TransportMode;
        approachStart=p->mSRT.t;
        haulAttached=false;milestone("carrier_assignment",ticks);
        std::printf("P2_PURPLE_HAUL_ASSIGN purple=%d native_approach=1 slot_teleport=0 forced_attachment=0 x=%.2f z=%.2f\n",
            int(pc_p2_is_purple(p)),p->mSRT.t.x,p->mSRT.t.z);
    }
    void transportStep(Navi* n) {
        const bool redOnly=mode("transport_red_control");
        const bool manual=mode("transport_manual");
        const bool staged=mode("transport_staged") || manual;
        const bool positiveOnly=mode("transport_positive") || staged;
        require(++haulTicks<7200,"native transport/delivery timeout");
        require(acquired && acquired->isAlive() && !acquired->mP2White
            && (redOnly ? !pc_p2_is_purple(acquired) && acquired->mColor==Red : pc_p2_is_purple(acquired)),"test carrier identity lost");
        if(!haulPhase) {
            require(std::fabs(pc_settings_get_carry_speed_scale()-1.f)<0.001f,"default production carry speed required");
            haulGoal=itemMgr->getContainer(Red);
            require(haulGoal && haulGoal->mOnionColour==Red,"active Red Onion required");
            if(redOnly) haulRed=acquired;
            else if(!positiveOnly) { Iterator squad(pikiMgr); CI_LOOP(squad) {
                Piki* p=static_cast<Piki*>(*squad);
                if(p && p->isAlive() && !pc_p2_is_purple(p) && !p->mP2White && p->mColor==Red
                    && p->getState()==PIKISTATE_Normal && p->mMode==PikiMode::FormationMode) { haulRed=p; break; }
            } }
            require(positiveOnly || haulRed,"ordinary Red control missing");
            // Plucking may leave nearby non-test Pikmin idle/free. Explicitly
            // gather them before introducing cargo so they cannot invalidate
            // the single-carrier control. No actor position is changed.
            Iterator nonTest(pikiMgr); CI_LOOP(nonTest) {
                Piki* p=static_cast<Piki*>(*nonTest);
                if(p && p->isAlive() && p!=haulRed && p!=acquired) {
                    p->mActiveAction->abandon(nullptr);
                    p->changeMode(PikiMode::FormationMode,n);
                }
            }
            std::puts("P2_PURPLE_HAUL_ISOLATION non_test_squad_formation=1 actor_position_injected=0");
            haul=pelletMgr->newNumberPellet(Red,NUMPEL_TenPellet);
            require(haul && haul->mConfig->mCarryMinPikis()==10,"standard weight10 pellet missing");
            expectedReward=haul->mConfig->mMatchingOnyonSeeds();require(expectedReward>0,"positive matching Onion yield required");
            const char* route=std::getenv("P2_PURPLE_HAUL_ROUTE");
            require(!route || !std::strcmp(route,"east197") || !std::strcmp(route,"west197"),"unknown fixture cargo route");
            const bool west=route && !std::strcmp(route,"west197");
            Vector3f pos=haulGoal->mSRT.t+Vector3f(west?-180:180,0,80);pos.y=mapMgr->getMinY(pos.x,pos.z,true)+5;
            require(std::isfinite(pos.y),"cargo placement terrain invalid");
            std::printf("P2_PURPLE_HAUL_ORIGIN route=%s xyz=%.2f,%.2f,%.2f distance_xz=196.98 violet_unchanged=1\n",west?"west197":"east197",pos.x,pos.y,pos.z);
            haul->init(pos);haul->startAI(TRUE);haulStart=pos;
            milestone("cargo_spawn",ticks);
            GameStat::update();haulPopulationBefore=GameStat::allPikis[Red];
            rewardBefore=GameStat::bornPikis[Red];haulMaturity=acquired->mHappa;haulPhase=1;haulTicks=0;
            std::printf("P2_PURPLE_HAUL_BEGIN injected_cargo=1 weight=10 expected_reward=%d maturity=%d source_identity_injected=%d cargo_position_staged_once=1\n",expectedReward,haulMaturity,int(staged));
            return;
        }
        require(acquired->mHappa==haulMaturity,"carrier maturity changed");
        keepHaulSquad(n);
        bool present=false;Iterator pellets(pelletMgr);CI_LOOP(pellets) if(static_cast<Pellet*>(*pellets)==haul){present=true;break;}
        const bool alive=present && haul->isAlive();
        const int reward=GameStat::bornPikis[Red]-rewardBefore;
        require(reward>=0 && reward<=expectedReward,"unexpected/duplicate Red reward");
        if(haulPhase==1) {
            require(alive,"cargo disappeared before assignment");
            const Vector3f d=haul->mSRT.t-haulStart;const float drift=d.x*d.x+d.z*d.z;
            const bool settling=(!redOnly && !positiveOnly && haulTicks<90)
                || drift>=0.25f || !haul->onGround() || std::fabs(d.y)>0.25f;
            if(settling){haulStart=haul->mSRT.t;haulStable=0;}else ++haulStable;
            if(haulStable>=30 && haul->isVisible() && haul->getState()==PELSTATE_Normal){
                haulStart=haul->mSRT.t;
                if(manual) {
                    approachStart=acquired->mSRT.t;pc_p2_input_script_clear(1);
                    std::puts("P2_PURPLE_MANUAL_READY field=20 purple=1 reds=19 starting_species_injected=1 native_acquisition=0 scripted_transport_assignment=0 actor_position_injected=0 cargo_spawned_once=1 reset=F7_or_Reset_cmd");
                    if(std::getenv("P2_PURPLE_MANUAL_BOOT_ONLY")) { std::fflush(nullptr);std::_Exit(0); }
                } else assignHaul(positiveOnly?acquired:haulRed);
                haulPhase=positiveOnly?3:2;haulTicks=0;haulStable=0;
            }
        } else if(haulPhase==2) {
            require(alive && reward==0,"control consumed cargo or generated reward");
            const Vector3f d=haul->mSRT.t-haulStart;require(d.x*d.x+d.z*d.z<4,"single Red moved weight10 cargo");
            require(haul->mCarrierCounter<=1,"unexpected helper in control");
            if(haulRed->getStickObject()==haul && haul->mCarrierCounter==1) ++haulStable;
            if(haulStable>=90) {
                haulRed->mActiveAction->abandon(nullptr);haulRed->changeMode(PikiMode::FormationMode,n);
                require(haulRed->getStickObject()!=haul,"Red control did not detach");
                std::puts("P2_PURPLE_HAUL_RED_CONTROL_PASS strength=1 attached_observations=90 displacement_under_2=1 reward=0");
                if(redOnly) {
                    GameStat::update();
                    require(GameStat::allPikis[Red]==haulPopulationBefore,"Red control population changed");
                    std::puts("P2_PURPLE_HAUL_RED_ONLY_PASS population_unchanged=1 released=1 source_identity_injected=0");
                    std::fflush(nullptr);std::_Exit(0);
                }
                haulStart=haul->mSRT.t;assignHaul(acquired);haulPhase=3;haulTicks=0;haulStable=0;
            }
        } else {
            if(alive) {
                int attached=0;Iterator bodies(pikiMgr);CI_LOOP(bodies) if(static_cast<Piki*>(*bodies)->getStickObject()==haul) ++attached;
                require(attached<=1 && haul->mCarrierCounter<=10,"extra carrier invalidates single-Purple haul");
                if(!haulAttached && attached==1 && haul->mCarrierCounter==10) {haulAttached=true;milestone("carrier_attached",ticks);}
                const Vector3f d=haul->mSRT.t-haulStart;
                if(!haulMoved && attached==1 && haul->mCarrierCounter==10 && d.x*d.x+d.z*d.z>100) {
                    const Vector3f approach=acquired->mSRT.t-approachStart;
                    require(approach.x*approach.x+approach.z*approach.z>25,"native approach not observed");
                    haulMoved=true;
                    milestone("cargo_moved_ten",ticks);
                    std::printf("P2_PURPLE_HAUL_MOVEMENT_PASS strength=10 attached=1 distance=%.2f native_approach=1 forced_attachment=0 cargo_teleport_after_spawn=0\n",std::sqrt(d.x*d.x+d.z*d.z));
                }
                if(haul->getState()==PELSTATE_Goal) {
                    require(haulMoved && haul->mTargetGoal==static_cast<Suckable*>(haulGoal),"wrong destination or missing native transport");
                    if(!haulGoalSeen) {milestone("onion_uptake",ticks);std::puts("P2_PURPLE_HAUL_ONION_UPTAKE target=red_onion native_goal_state=1");}
                    haulGoalSeen=true;
                }
            } else {
                require(haulGoalSeen && haulMoved,"cargo vanished without observed Onion uptake");haulGone=true;
            }
            if(haulGone && reward==expectedReward && acquired->getStickObject()!=haul && acquired->getState()==PIKISTATE_Normal) {
                if(++haulStable>=90) {
                    GameStat::update();
                    require(GameStat::allPikis[Red]-haulPopulationBefore==expectedReward,"reward counter/population mismatch");
                    milestone("delivery_verified",ticks);
                    std::printf("P2_PURPLE_HAUL_POPULATION before=%d after=%d expected_delta=%d\n",haulPopulationBefore,GameStat::allPikis[Red],expectedReward);
                    std::printf("P2_PURPLE_HAUL_DELIVERY_PASS reward=%d expected_reward=%d purple_alive=1 maturity=%d released=1 stable_ticks=%d duplicate_reward=0 injected_cargo=1 scripted_action_assignment=%d controls_validated=0 scripted_non_test_recalls=%d starting_species_injected=%d\n",reward,expectedReward,haulMaturity,haulStable,int(!manual),haulRecalls,int(staged));
                    std::fflush(nullptr);std::_Exit(0);
                }
            } else haulStable=0;
        }
        if(haulTicks%60==0) {
            std::printf("P2_PURPLE_HAUL_PROGRESS phase=%d ticks=%d cargo_alive=%d cargo_state=%d strength=%d purple_state=%d attached=%d reward=%d expected=%d recalls=%d grounded=%d stable_ticks=%d\n",
                haulPhase,haulTicks,int(alive),alive?haul->getState():-1,alive?int(haul->mCarrierCounter):0,acquired->getState(),int(acquired->getStickObject()==haul),reward,expectedReward,haulRecalls,int(alive && haul->onGround()),haulStable);
            if(alive) {
                const Vector3f goal=haulGoal->getGoalPos();
                std::printf("P2_PURPLE_HAUL_ROUTE cargo=%.2f,%.2f,%.2f velocity=%.2f,%.2f,%.2f goal=%.2f,%.2f,%.2f target_red=%d target_present=%d goal_waypoint=%d computed_speed=%.3f\n",
                    haul->mSRT.t.x,haul->mSRT.t.y,haul->mSRT.t.z,haul->mVelocity.x,haul->mVelocity.y,haul->mVelocity.z,
                    goal.x,goal.y,goal.z,int(haul->mTargetGoal==static_cast<Suckable*>(haulGoal)),
                    int(haul->mTargetGoal!=nullptr),haulGoal->getRouteIndex(),pc_p2_transport_speed(haul,0));
                Piki* carrier=redOnly?haulRed:acquired;
                if(carrier->mMode==PikiMode::TransportMode && carrier->mActiveAction->getCurrAction())
                    PurpleTransportTrace::emit(static_cast<ActTransport*>(carrier->mActiveAction->getCurrAction()),carrier);
            }
        }
    }

    void acquisitionInput(unsigned buttons=0,int x=0,int y=0) {
        if(sdlAcquisitionMode()) ordinaryInput(buttons,y,x,true);
        else pc_p2_input_script_set(1,buttons,x,y);
    }
    static SdlPluckPoint sdlPoint(const Vector3f& p) {return {p.x,p.z};}
    SdlPluckState sdlPulseSnapshot(Navi* n) const {
        return {sdlPoint(n->mSRT.t),sdlPoint(n->mVelocity),sdlPoint(n->mFixedPosition),n->isCreatureFlag(CF_IsPositionFixed)};
    }
    SdlPluckInputModel sdlPulseModel(Navi* n,float tau) {
        require(n->controlCamera() && n->mPlateMgr && n->mKontroller,"pulse controller dependencies");
        const int state=n->getCurrState()->getID();
        require(state==NAVISTATE_Walk || state==NAVISTATE_Idle,"pulse requires ordinary walking state");
        require(n->mGroundTriangle && MapCode::getSlipCode(n->mGroundTriangle)==0
            && std::fabs(n->mGroundTriangle->mTriangle.mNormal.x)<.0001f
            && std::fabs(n->mGroundTriangle->mTriangle.mNormal.z)<.0001f
            && n->mGroundTriangle->mTriangle.mNormal.y>.9999f,"pulse forecast requires flat non-slip ground");
        require(n->isCreatureFlag(CF_AllowFixPosition) && !n->isCreatureFlag(CF_EnableAirDrag)
            && !n->isCreatureFlag(CF_DisableMovement|CF_IsAiDisabled|CF_SkipPhysicsAndCollision|CF_IsFlying|CF_IsClimbing)
            && !n->mIsBeingDamaged && !n->mIsFrozen && !n->mKontroller->mIsControllerFrozen
            && !n->mCollPlatform && !n->mRope && !n->mStickTarget
            && n->mHoldingCreature.isNull(),"pulse forecast unsupported movement state");
        // This sample is after PlugPikiApp::idle: movement and collision
        // postUpdate have both completed. Previous is the preceding model-check
        // sample, NOT a pre-collision measurement. Do not infer impulse origin.
        const unsigned forceMask=pluckForceGuardMask(sdlPoint(n->_B0),sdlPoint(n->mVolatileVelocity),tau);
        const auto& previous=sdlPreviousForceSample;
        std::printf("P2_PURPLE_PLUCK_FORCE_SAMPLE tick=%d auth_tick=%llu captain=%p phase=%s sample=end_idle state=%d "
            "B0=%.9g,%.9g,%.9g volatile=%.9g,%.9g,%.9g tau=%.9g "
            "mask=%u mask_B0=1 mask_volatile=2 mask_tau=4 "
            "previous_tick=%d previous_B0=%.9g,%.9g,%.9g previous_volatile=%.9g,%.9g,%.9g previous_tau=%.9g "
            "velocity=%.9g,%.9g,%.9g target=%.9g,%.9g,%.9g anchor=%.9g,%.9g,%.9g fixed=%d "
            "ground_normal=%.9g,%.9g,%.9g dt=%.9g read_only=1 force_origin_unproven=1\n",
            ticks,static_cast<unsigned long long>(pc_render_tick_serial()),static_cast<void*>(n),sdlPulseActive?"observe":"begin",state,
            n->_B0.x,n->_B0.y,n->_B0.z,n->mVolatileVelocity.x,n->mVolatileVelocity.y,n->mVolatileVelocity.z,tau,
            forceMask,previous.tick,previous.acceleration[0],previous.acceleration[1],previous.acceleration[2],
            previous.transient[0],previous.transient[1],previous.transient[2],previous.tau,
            n->mVelocity.x,n->mVelocity.y,n->mVelocity.z,n->mTargetVelocity.x,n->mTargetVelocity.y,n->mTargetVelocity.z,
            n->mFixedPosition.x,n->mFixedPosition.y,n->mFixedPosition.z,int(n->isCreatureFlag(CF_IsPositionFixed)),
            n->mGroundTriangle->mTriangle.mNormal.x,n->mGroundTriangle->mTriangle.mNormal.y,n->mGroundTriangle->mTriangle.mNormal.z,
            gsys->getFrameTime());
        sdlPreviousForceSample={{n->_B0.x,n->_B0.y,n->_B0.z},
            {n->mVolatileVelocity.x,n->mVolatileVelocity.y,n->mVolatileVelocity.z},tau,ticks};
        require(forceMask==0,"pulse forecast external force or acceleration");
        Stickers stickers(n);const float drag=std::max(.1f,1.f-.08f*stickers.getNumStickers());
        const Vector3f& axis=n->controlCamera()->mViewXAxis;
        const float yaw=std::atan2(axis.z,axis.x);
        SdlPluckInputModel model;
        model.deadZone=pc_window_get_stick_dead_zone();
        model.speed=(n->mPlateMgr->canNaviRunFast()?C_NAVI_PARM(n,mRunSpeed):C_NAVI_PARM(n,mMoveSpeed))
            *drag*pc_randomizer_captain_movement_multiplier()*pc_settings_get_navi_speed_scale();
        model.binDegrees=C_NAVI_PARM(n,mShakePreventionAngle);
        model.clamp=C_NAVI_PARM(n,mClampStickToMaxThreshold);
        model.neutral=C_NAVI_PARM(n,mNeutralStickThreshold);model.cursor=C_NAVI_PARM(n,mCursorMoveStickThreshold);
        model.cameraX=std::cos(yaw);model.cameraZ=std::sin(yaw);
        require(pluckInputModelValid(model),"invalid loaded pulse input model");return model;
    }
    bool sdlPulseSegmentClear(SdlPluckPoint a,SdlPluckPoint b,float margin=0.f) const {
        if(!pluckFinite(a)||!pluckFinite(b)||!std::isfinite(margin)||margin<0.f)return false;
        const auto delta=pluckSub(b,a);const float square=delta.x*delta.x+delta.z*delta.z;
        for(const auto& obstacle:pluckObstacles) {
            if(!sdlFinitePoint(obstacle.centre)||!std::isfinite(obstacle.radius)||obstacle.radius<0.f)return false;
            const auto offset=pluckSub(sdlPoint(obstacle.centre),a);
            const float t=square>0.f?std::max(0.f,std::min(1.f,(offset.x*delta.x+offset.z*delta.z)/square)):0.f;
            if(pluckLength(pluckSub(pluckAdd(a,pluckScale(delta,t)),sdlPoint(obstacle.centre)))<obstacle.radius+margin)return false;
        }
        return true;
    }
    bool sdlNeutralEnvelopeClear(const SdlPluckState& state,float tau) const {
        if(state.fixed) {
            // After native pull starts the qualified recurrence contracts toward
            // the captured anchor; the first overshoot still carries velocity.
            if(pluckLength(pluckSub(state.anchor,state.position))>.00001f) {
                const float discrepancy=pluckLength(pluckSub(state.velocity,pluckScale(pluckSub(state.anchor,state.position),10.f)));
                // Cover the observed velocity discrepancy on the next step;
                // do not infer exact contraction merely from a nonzero offset.
                return std::isfinite(discrepancy) && sdlPulseSegmentClear(state.position,state.anchor,.05f+discrepancy/30.f);
            }
        }
        const float limit=1.f/30.f;
        const float step=std::min(limit,tau*.5f),maximum=step*(1.f-step/tau);
        // First neutral capture plus first drift. All later fixed-position
        // pulls stay between anchor and drift for dt<=1/30 and dt<=tau.
        return sdlPulseSegmentClear(state.position,pluckAdd(state.position,pluckScale(state.velocity,(state.fixed?1.f:2.f)*maximum)),.05f);
    }
    bool sdlPulseTerrainClear(SdlPluckPoint a,SdlPluckPoint b,float height,float margin) const {
        if(!mapMgr||!pluckFinite(a)||!pluckFinite(b)||!std::isfinite(height))return false;
        const auto delta=pluckSub(b,a);const int samples=int(std::ceil(pluckLength(delta)))+1;
        // Same native terrain predicates as route admission, now also covering
        // the selected off-axis pulse and neutral envelope. These finite samples
        // are fixture admission checks, not a continuous terrain proof.
        for(int i=0;i<=samples;++i)for(int side=-1;side<8;++side) {
            auto p=pluckAdd(a,pluckScale(delta,float(i)/samples));
            if(side>=0){p.x+=margin*std::cos(side*6.283185307f/8.f);p.z+=margin*std::sin(side*6.283185307f/8.f);}
            CollTriInfo* tri=mapMgr->getCurrTri(p.x,p.z,true);const float y=mapMgr->getMinY(p.x,p.z,true);
            if(!tri||!sdlFinitePoint(tri->mTriangle.mNormal)||MapCode::getAttribute(tri)==ATTR_Water||MapCode::getAttribute(tri)==ATTR_Hole||MapCode::getSlipCode(tri)!=0
                ||!std::isfinite(y)||std::fabs(y-height)>=.1f||std::fabs(tri->mTriangle.mNormal.x)>=.0001f
                ||std::fabs(tri->mTriangle.mNormal.z)>=.0001f||tri->mTriangle.mNormal.y<=.9999f)return false;
        }
        return true;
    }
    bool sdlCancelOwnedCollision(Navi* n,float tau) {
        const unsigned mask=pluckForceGuardMask(sdlPoint(n->_B0),sdlPoint(n->mVolatileVelocity),tau);
        if(mask==0) return false;
        // The old forecast has been invalidated by a proven ordinary native
        // collision. Never accept it or edit the queued engine force. Unknown
        // forces and acceleration/tau anomalies retain the existing refusal.
        require(mask==2 && pc_purple_collision_owned_queued_force(n,static_cast<std::uint64_t>(ticks)),
            "pulse forecast external force or acceleration");
        acquisitionInput();sdlPulseActive=false;sdlPulseCommand={};sdlPluckBraking=true;pluckRoute.clear();
        std::printf("P2_PURPLE_PLUCK_PULSE_CANCEL tick=%d auth_tick=%llu reason=owned_formation_collision "
            "forecast_accepted=0 SDL_neutral=1 actor_writes=0\n",ticks,
            static_cast<unsigned long long>(pc_render_tick_serial()));
        return true;
    }
    void sdlObservePulse(Navi* n,PikiHeadItem* head,Pom* violet,float tau,float dt) {
        if(sdlCancelOwnedCollision(n,tau)) return;
        (void)head;(void)violet;sdlPulseModel(n,tau);
        SdlPluckState predicted=sdlPulseBefore;require(pluckPulseStep(predicted,sdlPulseCommand,dt,tau),"invalid pulse observation step");
        const SdlPluckState actual=sdlPulseSnapshot(n);
        const float positionError=pluckLength(pluckSub(predicted.position,actual.position));
        const float velocityError=pluckLength(pluckSub(predicted.velocity,actual.velocity));
        const float targetError=pluckLength(pluckSub(sdlPulseCommand,sdlPoint(n->mTargetVelocity)));
        const float anchorError=actual.fixed?pluckLength(pluckSub(predicted.anchor,actual.anchor)):0.f;
        std::printf("P2_PURPLE_PLUCK_PULSE_OBS tick=%d frame=%d dt=%.9f position_error=%.6f velocity_error=%.6f target_error=%.6f anchor_error=%.6f fixed=%d expected_fixed=%d command=%.6f,%.6f actor_writes=0\n",
            ticks,sdlPulseFrames,dt,positionError,velocityError,targetError,anchorError,int(actual.fixed),int(predicted.fixed),sdlPulseCommand.x,sdlPulseCommand.z);
        // Deviations are diagnostic failures, never synthetic corrections.
        require(positionError<.1f && velocityError<1.f && targetError<.5f && anchorError<.1f
            && actual.fixed==predicted.fixed,"native pulse deviated from qualified movement forecast");
        require(sdlNeutralEnvelopeClear(actual,tau),"native pulse neutral envelope crosses live collision bounds");
        const float neutralStep=std::min(1.f/30.f,tau*.5f),neutralMaximum=neutralStep*(1.f-neutralStep/tau);
        const bool pulling=actual.fixed&&pluckLength(pluckSub(actual.anchor,actual.position))>.00001f;
        const auto end=pulling?actual.anchor
            :pluckAdd(actual.position,pluckScale(actual.velocity,(actual.fixed?1.f:2.f)*neutralMaximum));
        const float driftMargin=pulling?pluckLength(pluckSub(actual.velocity,pluckScale(pluckSub(actual.anchor,actual.position),10.f)))/30.f:0.f;
        require(sdlPulseTerrainClear(actual.position,end,n->mSRT.t.y,.05f+driftMargin),"native pulse neutral terrain changed");
        acquisitionInput();sdlPulseCommand={};sdlPulseBefore=actual;
        require(++sdlPulseFrames<=64,"native pulse failed to settle within bounded observation");
        if(sdlPluckAtRest(pluckLength(actual.velocity),pluckLength(sdlPoint(n->mTargetVelocity))) && pluckPulseSettled(actual)) {
            sdlPulseActive=false;
            std::printf("P2_PURPLE_PLUCK_PULSE_SETTLED tick=%d frames=%d native_fixed_position=1 actor_writes=0\n",ticks,sdlPulseFrames);
        }
    }
    bool sdlBeginPulse(Navi* n,PikiHeadItem* head,Pom*,const Vector3f& waypoint,float tau,float dt,float range) {
        const SdlPluckInputModel model=sdlPulseModel(n,tau);const SdlPluckState start=sdlPulseSnapshot(n);
        const float oldDistance=pluckLength(pluckSub(start.position,sdlPoint(waypoint)));
        int bestX=0,bestY=0;float bestScore=std::numeric_limits<float>::infinity();SdlPluckState bestEnd;
        const float limit=1.f/30.f,step=std::min(limit,tau*.5f),maximum=step*(1.f-step/tau);
        for(int bearing=0;bearing<144;++bearing)for(int power=1;power<=74;++power) {
            const float angle=bearing*6.283185307f/144.f;
            const int x=int(std::lround(power*std::cos(angle))),y=int(std::lround(power*std::sin(angle)));
            const SdlPluckPoint target=pluckInputTarget(x,y,model);if(pluckLength(target)<.01f)continue;
            // Qualified prospective bound for one input tick followed by neutral,
            // for any next dt in (0,1/30]. This is CURRENT-pose geometry, not
            // proof about future animation/camera/contact. Observe every tick.
            const float lengthFactor=(limit*limit+2.f*maximum*limit)/tau;
            const auto furthest=pluckAdd(start.position,pluckScale(target,lengthFactor));
            if(!sdlPulseSegmentClear(start.position,furthest,(tau+limit)*pluckLength(start.velocity)+.05f))continue;
            SdlPluckState trial=start;bool clear=true;
            for(int frame=0;frame<64;++frame) {
                const auto before=trial.position;
                if(!pluckPulseStep(trial,frame==0?target:SdlPluckPoint{},dt,tau)
                    ||!sdlPulseSegmentClear(before,trial.position,.05f)){clear=false;break;}
                if(frame>0&&pluckPulseSettled(trial))break;
            }
            if(!clear||!pluckPulseSettled(trial))continue;
            const float distance=pluckLength(pluckSub(trial.position,sdlPoint(waypoint)));
            const bool terminal=pluckLength(pluckSub(trial.position,sdlPoint(head->mSRT.t)))<range-.5f;
            if(!terminal&&distance>=oldDistance-.1f)continue;
            const float score=distance-(terminal?10000.f:0.f);
            if(score<bestScore && sdlPulseTerrainClear(start.position,furthest,n->mSRT.t.y,(tau+limit)*pluckLength(start.velocity)+.05f))
                {bestScore=score;bestX=x;bestY=y;bestEnd=trial;}
        }
        if(!std::isfinite(bestScore))return false;
        sdlPulseBefore=start;sdlPulseCommand=pluckInputTarget(bestX,bestY,model);sdlPulseFrames=0;sdlPulseActive=true;
        acquisitionInput(0,bestX,bestY);
        std::printf("P2_PURPLE_PLUCK_PULSE_BEGIN tick=%d raw=%d,%d target=%.6f,%.6f predicted_landing=%.6f,%.6f dt=%.9f tau=%.6f "
            "dead_zone=%d sampled=%d,%d camera_axis=%.9g,%.9g bin_degrees=%.9g native_fix_position=1 actor_writes=0\n",
            ticks,bestX,bestY,sdlPulseCommand.x,sdlPulseCommand.z,bestEnd.position.x,bestEnd.position.z,dt,tau,
            model.deadZone,pcPurpleSdlPulseSampleAxis(bestX,model.deadZone),pcPurpleSdlPulseSampleAxis(bestY,model.deadZone),
            model.cameraX,model.cameraZ,model.binDegrees);
        return true;
    }

    bool approachAndPluck(Navi* n,PikiHeadItem* head,Pom* violet) {
        // Ordinary controller movement/pluck. Never relocate the captain or
        // sprout, or force a plucking state to satisfy natural acceptance.
        const float dx=head->mSRT.t.x-n->mSRT.t.x,dz=head->mSRT.t.z-n->mSRT.t.z;
        const float distance=std::sqrt(dx*dx+dz*dz);
        const float pluckRange=C_NAVI_PARM(n,mPluckDistanceOutsideOnyon);
        require(std::isfinite(pluckRange) && pluckRange>1.f,"invalid native pluck range");
        const float cursorBand=C_NAVI_PARM(n,mCursorMoveStickThreshold);
        require(std::isfinite(cursorBand) && cursorBand>=0 && cursorBand<.9f,"invalid native cursor-only stick band");
        require(std::fabs(pc_settings_get_navi_speed_scale()-1.f)<.001f,"default captain speed required");
        if(ticks%60==0) std::printf("P2_PURPLE_PLUCK_APPROACH distance=%.3f captain=%.3f,%.3f,%.3f sprout=%.3f,%.3f,%.3f state=%d port=%u observed_stick=%d,%d frozen=%d\n",
            distance,n->mSRT.t.x,n->mSRT.t.y,n->mSRT.t.z,head->mSRT.t.x,head->mSRT.t.y,head->mSRT.t.z,
            n->getCurrState()->getID(),n->mKontroller?n->mKontroller->mPlayerNum:0,
            n->mKontroller?int(n->mKontroller->mMainStickX):0,n->mKontroller?int(n->mKontroller->mMainStickY):0,
            int(n->mKontroller && n->mKontroller->mIsControllerFrozen));
        if(ticks%60==0) std::printf("P2_PURPLE_PLUCK_CONTROL cursor_only_threshold=%.3f normalized_stick=%.3f,%.3f velocity=%.3f,%.3f target_velocity=%.3f,%.3f native_speed_scale=1\n",
            cursorBand,n->mKontroller?n->mKontroller->getMainStickX():0,n->mKontroller?n->mKontroller->getMainStickY():0,
            n->mVelocity.x,n->mVelocity.z,n->mTargetVelocity.x,n->mTargetVelocity.z);
        float pluckSpeed=0.f,pluckTargetSpeed=0.f,pluckTau=0.f,pluckDt=0.f;
        if(sdlAcquisitionMode()) {
            require(n->mProps!=nullptr,"SDL pluck movement properties missing");
            pluckSpeed=std::hypot(n->mVelocity.x,n->mVelocity.z);
            pluckTargetSpeed=std::hypot(n->mTargetVelocity.x,n->mTargetVelocity.z);
            pluckTau=n->mProps->mCreatureProps.mAcceleration();
            pluckDt=gsys->getFrameTime();
            require(sdlPluckMotionValid(pluckSpeed,pluckTargetSpeed,pluckTau,pluckDt)
                && std::isfinite(distance),"invalid SDL pluck motion snapshot");
            refreshPluckObstacles(n,violet);
            pluckTrace("motion_snapshot",n,head,violet);
            require(pluckSegmentClear(n->mSRT.t,n->mSRT.t),"SDL pluck captain starts inside live collision bounds");
            if(sdlPulseActive) {
                sdlObservePulse(n,head,violet,pluckTau,pluckDt);
                return false;
            }
            // The observed failing route began while the ejected sprout was
            // still unpluckable and Violet parts were changing. Let the native
            // head FSM become ready without walking into that opening pose.
            if(!head->canPullout()) {
                acquisitionInput();sdlPluckBraking=true;pluckRoute.clear();
                std::printf("P2_PURPLE_PLUCK_BRAKE tick=%d reason=head_not_ready speed=%.6f target_speed=%.6f tau=%.6f dt=%.9f SDL_neutral=1 actor_writes=0\n",
                    ticks,pluckSpeed,pluckTargetSpeed,pluckTau,pluckDt);
                return false;
            }
            if(sdlPluckBraking) {
                acquisitionInput();
                if(sdlCancelOwnedCollision(n,pluckTau)) return false;
                std::printf("P2_PURPLE_PLUCK_BRAKE tick=%d reason=settling speed=%.6f target_speed=%.6f tau=%.6f dt=%.9f SDL_neutral=1 actor_writes=0\n",
                    ticks,pluckSpeed,pluckTargetSpeed,pluckTau,pluckDt);
                if(!sdlPluckAtRest(pluckSpeed,pluckTargetSpeed)) return false;
                sdlPluckBraking=false;pluckRoute.clear();
            }
            if(distance<pluckRange-.25f && !sdlPluckAtRest(pluckSpeed,pluckTargetSpeed)) {
                acquisitionInput();sdlPluckBraking=true;return false;
            }
        }
        if(distance>=pluckRange-.25f) {
            refreshPluckObstacles(n,violet);
            pluckTrace("approach_refresh",n,head,violet);
            if(sdlAcquisitionMode())std::printf("P2_PURPLE_PLUCK_REPLAN tick=%d new_head=%d empty=%d head_moved=%d segment_blocked=%d read_only=1\n",
                ticks,int(routedHead!=head),int(pluckRoute.empty()),int(routedHead==head && planarDistance(routedHeadPosition,head->mSRT.t)>2.f),
                int(!pluckRoute.empty() && !pluckSegmentClear(n->mSRT.t,pluckRoute[pluckRouteIndex])));
            const bool needsPlan=routedHead!=head || pluckRoute.empty() || planarDistance(routedHeadPosition,head->mSRT.t)>2.f
                || !pluckSegmentClear(n->mSRT.t,pluckRoute[pluckRouteIndex]);
            if(needsPlan && sdlAcquisitionMode() && !sdlPluckAtRest(pluckSpeed,pluckTargetSpeed)) {
                acquisitionInput();sdlPluckBraking=true;
                std::printf("P2_PURPLE_PLUCK_BRAKE tick=%d reason=replan speed=%.6f target_speed=%.6f tau=%.6f dt=%.9f SDL_neutral=1 actor_writes=0\n",
                    ticks,pluckSpeed,pluckTargetSpeed,pluckTau,pluckDt);
                return false;
            }
            if(needsPlan) planPluckRoute(n,head,violet,pluckRange);
            while(pluckRouteIndex+1<pluckRoute.size() && planarDistance(n->mSRT.t,pluckRoute[pluckRouteIndex])<4.f
                && (!sdlAcquisitionMode() || sdlPluckAtRest(pluckSpeed,pluckTargetSpeed))
                && pluckSegmentClear(n->mSRT.t,pluckRoute[pluckRouteIndex+1])) ++pluckRouteIndex;
            const Vector3f& target=pluckRoute[pluckRouteIndex];
            const float tx=target.x-n->mSRT.t.x,tz=target.z-n->mSRT.t.z,d=std::sqrt(tx*tx+tz*tz);
            require(d>.05f,"controller reached approach point outside native pluck range");
            if(sdlAcquisitionMode()) {
                if(!sdlPluckAtRest(pluckSpeed,pluckTargetSpeed)) {
                    acquisitionInput();sdlPluckBraking=true;return false;
                }
                if(!sdlBeginPulse(n,head,violet,target,pluckTau,pluckDt,pluckRange)) {
                    // Quantized movement may stop short of a geometric corner.
                    // Replan ONCE from the observed rest point; the nearby-node
                    // exclusion prevents endlessly selecting that same corner.
                    planPluckRoute(n,head,violet,pluckRange);
                    require(!pluckRoute.empty() && sdlBeginPulse(n,head,violet,pluckRoute[0],pluckTau,pluckDt,pluckRange),
                        "no eligible quantized pulse after stopped route replan");
                }
                return false;
            }

            if(sdlAcquisitionMode() && (d<=4.f || sdlPluckBrakeBeforeWaypoint(d,pluckSpeed,pluckTau,pluckDt))) {
                acquisitionInput();sdlPluckBraking=true;
                std::printf("P2_PURPLE_PLUCK_BRAKE tick=%d reason=waypoint distance=%.6f speed=%.6f target_speed=%.6f tau=%.6f dt=%.9f SDL_neutral=1 actor_writes=0\n",
                    ticks,d,pluckSpeed,pluckTargetSpeed,pluckTau,pluckDt);
                return false;
            }
            require(n->controlCamera()!=nullptr,"natural approach camera missing");
            const Vector3f& axis=n->controlCamera()->mViewXAxis;
            // Classic native controls use small deflections for cursor-only
            // aiming and explicitly zero walking velocity. Keep ordinary pad
            // input above that loaded band; do not change movement parameters.
            const float minimum=std::ceil(74.f*(cursorBand+.05f));
            const float power=std::max(minimum,std::min(65.f,d*2.f));
            acquisitionInput(0,int(std::lround(power*(tx*axis.x+tz*axis.z)/d)),
                int(std::lround(power*(tx*axis.z-tz*axis.x)/d)));
            if(sdlAcquisitionMode())std::printf("P2_PURPLE_PLUCK_COMMAND tick=%d waypoint=%u target=%.6f,%.6f,%.6f distance=%.6f power=%.6f emitted_sdl=%d,%d emitted_a=%d read_only=1\n",
                ticks,unsigned(pluckRouteIndex),target.x,target.y,target.z,d,power,int(SDL_JoystickGetAxis(ordinaryPad,SDL_CONTROLLER_AXIS_LEFTX)),
                int(SDL_JoystickGetAxis(ordinaryPad,SDL_CONTROLLER_AXIS_LEFTY)),int(SDL_JoystickGetButton(ordinaryPad,SDL_CONTROLLER_BUTTON_A)));
            return false;
        }
        require(std::isfinite(head->mSRT.t.y) && std::isfinite(n->mSRT.t.y)
            && std::fabs(head->mSRT.t.y-n->mSRT.t.y)<25.f,"native pluck height gate");
        if(!head->canPullout()) {acquisitionInput();return false;}
        acquisitionInput(KBBTN_A);
        ++pluckAttempts;
        milestone("native_sprout_pluck_requested",ticks);
        std::printf("P2_PURPLE_PLUCK_ATTEMPT attempt=%d captain_position_staged=0 native_input=1 forced_pluck_state=0 distance=%.3f player_controls_validated=0\n",pluckAttempts,distance);
        return true;
    }
    void ordinaryResume(Navi*) {
        savedMaturity=expectedNumber("P2_PURPLE_EXPECT_MATURITY",0,2);
        expectedDay=expectedNumber("P2_PURPLE_EXPECT_DAY",1,99999);
        require(pc_randomizer_resumed() && gameflow.mWorldClock.mCurrentDay==expectedDay && stockOne() && ordinaryCards()==1,
            "ordinary restored checkpoint/day/stock/maturity mismatch");
        if(++resumeReady<60) return;
        boundAdult(false);GameStat::update();
        Iterator bodies(pikiMgr);CI_LOOP(bodies) {
            Piki* p=static_cast<Piki*>(*bodies);
            require(!p || !p->isAlive() || !pc_p2_is_purple(p),"ordinary restore duplicate field Purple");
        }
        require(int(GameStat::allPikis)+p2ship::stock.total()==20,"ordinary saved starting population conservation");
        ordinaryInput();milestone("ordinary_checkpoint_restored",ticks);
        std::printf("P2_PURPLE_ORDINARY_RESUME_PASS day=%d maturity=%d stock=1 field=%d native_population=20 generations=1 checkpoint_resumed=1 direct_stock_helpers=0 withdrawal_ui_validated=0 saved_bytes_injected=0\n",
            expectedDay,savedMaturity,int(GameStat::mapPikis));
        std::fflush(nullptr);std::_Exit(0);
    }
    static bool sdlFinitePoint(const Vector3f& p) {
        return std::isfinite(p.x) && std::isfinite(p.y) && std::isfinite(p.z);
    }
    static bool sdlCursorRangeFeasible(float minimum,float radius,float speed) {
        if(!std::isfinite(minimum) || !std::isfinite(radius) || !std::isfinite(speed)
            || minimum<0.f || radius<=minimum || speed<=0.f)return false;
        const float stand=std::min(100.f,radius/1.4f);
        return stand>0.f && stand*1.2f>=minimum && (stand+5.f)*1.2f<radius;
    }
    void sdlValidateParts(CollPart* part,int depth=0) {
        require(part && depth<32,"SDL collision tree missing or too deep");
        if(!sdlGeometryLogged || ticks%30==0 || !sdlFinitePoint(part->mCentre) || !std::isfinite(part->mRadius) || part->mRadius<0.f)
        std::printf("P2_PURPLE_SDL_BOUND depth=%d id=%u centre=%.6f,%.6f,%.6f radius=%.6f read_only=1\n",
            depth,unsigned(part->getID().mId),part->mCentre.x,part->mCentre.y,part->mCentre.z,part->mRadius);
        require(sdlFinitePoint(part->mCentre) && std::isfinite(part->mRadius) && part->mRadius>=0.f,"SDL invalid raw collision bound");
        for(int i=0;i<part->getChildCount();++i)sdlValidateParts(part->getChildAt(i),depth+1);
    }
    void sdlAimTrace(Navi* n,Pom* violet,const char* decision,float ex,float ez,float tolerance,int ready,int stableBefore) {
        const double seconds=std::chrono::duration<double>(std::chrono::steady_clock::now()-fixtureStarted).count();
        const Vector3f current=n->mCursorPosition+n->mSRT.t;
        Camera* camera=n->controlCamera();
        const Vector3f basis=camera?camera->mViewXAxis:Vector3f(0,0,0);
        const float desiredX=n->mSRT.t.x+(violet->mSRT.t.x-n->mSRT.t.x)*1.2f;
        const float desiredZ=n->mSRT.t.z+(violet->mSRT.t.z-n->mSRT.t.z)*1.2f;
        std::printf("P2_PURPLE_SDL_AIM tick=%d wall_seconds=%.6f decision=%s dt=%.9f desired=%.6f,%.6f rendered=%.6f,%.6f current=%.6f,%.6f error=%.6f,%.6f error_norm=%.6f tolerance=%.6f ready=%d stable_before=%d stable_after=%d raw=%d,%d normalized=%.6f,%.6f emitted_sdl=%d,%d emitted_a=%d camera_present=%d camera_x=%.6f,%.6f,%.6f captain=%.6f,%.6f,%.6f state=%d read_only=1\n",
            ticks,seconds,decision,gsys->getFrameTime(),desiredX,desiredZ,n->mCursorWorldPos.x,n->mCursorWorldPos.z,current.x,current.z,
            ex,ez,std::sqrt(ex*ex+ez*ez),tolerance,ready,stableBefore,sdlStableAim,
            n->mKontroller?int(n->mKontroller->mMainStickX):0,n->mKontroller?int(n->mKontroller->mMainStickY):0,
            n->mKontroller?n->mKontroller->getMainStickX():0,n->mKontroller?n->mKontroller->getMainStickY():0,
            ordinaryPad?int(SDL_JoystickGetAxis(ordinaryPad,SDL_CONTROLLER_AXIS_LEFTX)):0,
            ordinaryPad?int(SDL_JoystickGetAxis(ordinaryPad,SDL_CONTROLLER_AXIS_LEFTY)):0,
            ordinaryPad?int(SDL_JoystickGetButton(ordinaryPad,SDL_CONTROLLER_BUTTON_A)):0,
            int(camera!=nullptr),basis.x,basis.y,basis.z,n->mSRT.t.x,n->mSRT.t.y,n->mSRT.t.z,n->getCurrState()->getID());
    }
    void sdlDirection(Navi* n,float dx,float dz,int power) {
        require(n->controlCamera()!=nullptr,"SDL acquisition camera missing");
        const float distance=std::sqrt(dx*dx+dz*dz);
        require(distance>.01f,"SDL direction missing");
        const Vector3f& axis=n->controlCamera()->mViewXAxis;
        ordinaryInput(0,int(std::lround(power*(dx*axis.z-dz*axis.x)/distance)),
            int(std::lround(power*(dx*axis.x+dz*axis.z)/distance)),true);
    }
    Piki* sdlStep(Navi* n) {
        require(pc_window_get_control_mode()==PC_CONTROL_CLASSIC,"SDL classic cursor controls required");
        require(std::fabs(pc_settings_get_navi_speed_scale()-1.f)<.001f,"SDL default captain speed");
        Pom* violet=nullptr;int flowersFound=0,alive=0,red=0,purple=0,ready=0;
        Piki* follower=nullptr;
        Iterator flowers(bossMgr);CI_LOOP(flowers) {
            Boss* b=static_cast<Boss*>(*flowers);
            if(b && b->isAlive() && b->mObjType==OBJTYPE_Pom && pc_p2_violet(static_cast<Pom*>(b))) {
                violet=static_cast<Pom*>(b);++flowersFound;
            }
        }
        require(flowersFound==1,"SDL original Violet missing or ambiguous");
        Iterator bodies(pikiMgr);CI_LOOP(bodies) {
            Piki* p=static_cast<Piki*>(*bodies);if(!p || !p->isAlive())continue;
            ++alive;
            if(pc_p2_is_purple(p)) {
                ++purple;
                if(p->getState()==PIKISTATE_Normal && p->mMode==PikiMode::FormationMode && p->mNavi==n)follower=p;
            } else if(p->mColor==Red && !p->mP2White) {
                ++red;
                if(p->getState()==PIKISTATE_Normal && p->mMode==PikiMode::FormationMode && !p->isStickTo())++ready;
            }
            if(sdlPhase==2 && (p->getState()==PIKISTATE_Flying || p==sdlTracePiki)) {
                const bool changed=p!=sdlTracePiki || p->getState()!=sdlTracePikiState;
                std::printf("P2_PURPLE_SDL_FLIGHT_TRACE tick=%d piki=%p state=%d transition=%d xyz=%.6f,%.6f,%.6f velocity=%.6f,%.6f,%.6f read_only=1\n",
                    ticks,static_cast<void*>(p),p->getState(),int(changed),p->mSRT.t.x,p->mSRT.t.y,p->mSRT.t.z,p->mVelocity.x,p->mVelocity.y,p->mVelocity.z);
                sdlTracePiki=p;sdlTracePikiState=p->getState();
            }
            if(ticks%30==0 && p->getState()==PIKISTATE_Flying)
                std::printf("P2_PURPLE_SDL_FLIGHT xyz=%.3f,%.3f,%.3f velocity=%.3f,%.3f,%.3f\n",
                    p->mSRT.t.x,p->mSRT.t.y,p->mSRT.t.z,p->mVelocity.x,p->mVelocity.y,p->mVelocity.z);
        }
        if(!sdlStarted) {
            ordinaryInput();if(alive<20)return nullptr;
            require(alive==20 && red==20 && purple==0,"SDL starting twenty Reds");
            Iterator initialHeads(itemMgr->getPikiHeadMgr());CI_LOOP(initialHeads) {
                PikiHeadItem* h=static_cast<PikiHeadItem*>(*initialHeads);
                require(!h || !h->isAlive() || !h->mP2Purple,"SDL pre-existing Purple sprout");
            }
            sdlStarted=true;
            std::puts("P2_PURPLE_SDL_START field=20 red=20 scripted_throw=0 direct_throw_api=0 actor_state_writes=0 starting_withdrawal_fixture=1");
        }
        if(sdlPhase==2 && !sdlThrowObserved && n->getCurrState()->getID()==NAVISTATE_Throw)
            milestone("SDL_native_throw_state_observed",ticks);
        if(sdlPhase==2 && n->getCurrState()->getID()==NAVISTATE_Throw)sdlThrowObserved=true;
        if(ticks%30==0)std::printf("P2_PURPLE_SDL_PROGRESS phase=%d state=%d captain=%.3f,%.3f,%.3f cursor=%.3f,%.3f,%.3f red=%d purple=%d ready=%d violet_state=%d throw_observed=%d\n",
            sdlPhase,n->getCurrState()->getID(),n->mSRT.t.x,n->mSRT.t.y,n->mSRT.t.z,
            n->mCursorWorldPos.x,n->mCursorWorldPos.y,n->mCursorWorldPos.z,red,purple,ready,violet->getCurrentState(),int(sdlThrowObserved));
        if(sdlPhase==3) {
            ordinaryInput();if(!follower)return nullptr;
            GameStat::update();require(alive==20 && red==19 && purple==1 && int(GameStat::mapPikis)==20,"SDL conversion population");
            require(sdlThrowObserved && pc_throw_selection_class(follower)==4 && pc_piki_carry_strength(follower)==10,"SDL native throw and Purple capabilities");
            milestone("SDL_acquisition_verified",ticks);
            std::puts("P2_PURPLE_SDL_ACQUISITION_PASS scripted_throw=0 direct_throw_api=0 actor_state_writes=0 native_throw_state_observed=1 SDL_pluck=1 field=20 red=19 purple=1 selection=4 strength=10");
            return follower;
        }
        Iterator heads(itemMgr->getPikiHeadMgr());CI_LOOP(heads) {
            PikiHeadItem* h=static_cast<PikiHeadItem*>(*heads);
            if(!h || !h->isAlive() || !h->mP2Purple)continue;
            ordinaryInput();
            if(h->mGroundTriangle && std::fabs(h->mSRT.t.y-mapMgr->getMinY(h->mSRT.t.x,h->mSRT.t.z,true))<1.f
                && approachAndPluck(n,h,violet))sdlPhase=3;
            return nullptr;
        }
        const float dx=violet->mSRT.t.x-n->mSRT.t.x,dz=violet->mSRT.t.z-n->mSRT.t.z;
        const float distance=std::sqrt(dx*dx+dz*dz),radius=C_NAVI_PARM(n,mCursorMaxRadius);
        const float minimum=C_NAVI_PARM(n,mCursorMinRadius),speed=C_NAVI_PARM(n,mCursorMoveSpeed);
        const float stand=std::min(100.f,radius/1.4f);
        // Read actual loaded values before any range/geometry rejection. Asset
        // p46 overrides the constructor default; the legal baseline loads 100.
        if(!sdlGeometryLogged || ticks%30==0 || !sdlCursorRangeFeasible(minimum,radius,speed))
        std::printf("P2_PURPLE_SDL_CONTROL tick=%d phase=%d min=%.6f max=%.6f speed=%.6f neutral=%.6f cursor_band=%.6f distance=%.6f stand=%.6f cursor=%.6f,%.6f,%.6f port=%u frozen=%d raw=%d,%d normalized=%.6f,%.6f read_only=1\n",
            ticks,sdlPhase,minimum,radius,speed,C_NAVI_PARM(n,mNeutralStickThreshold),C_NAVI_PARM(n,mCursorMoveStickThreshold),distance,stand,
            n->mCursorWorldPos.x,n->mCursorWorldPos.y,n->mCursorWorldPos.z,
            n->mKontroller?n->mKontroller->mPlayerNum:0,int(n->mKontroller && n->mKontroller->mIsControllerFrozen),
            n->mKontroller?int(n->mKontroller->mMainStickX):0,n->mKontroller?int(n->mKontroller->mMainStickY):0,
            n->mKontroller?n->mKontroller->getMainStickX():0,n->mKontroller?n->mKontroller->getMainStickY():0);
        require(sdlCursorRangeFeasible(minimum,radius,speed),"SDL loaded cursor range cannot fit approach band");
        require(sdlFinitePoint(n->mSRT.t) && sdlFinitePoint(violet->mSRT.t)
            && sdlFinitePoint(n->mCursorWorldPos) && std::isfinite(distance) && distance>.01f,"SDL invalid live geometry");
        if(sdlPhase==0 || sdlPhase==1) {
            require(n->mCollInfo && n->mCollInfo->hasInfo() && violet->mCollInfo && violet->mCollInfo->hasInfo(),"SDL live collision bounds missing");
            sdlValidateParts(n->mCollInfo->getBoundingSphere());
            sdlValidateParts(violet->mCollInfo->getBoundingSphere());
            refreshPluckObstacles(n,violet);
            require(!pluckObstacles.empty(),"SDL projected collision bounds missing");
            for(const auto& obstacle:pluckObstacles)
                require(sdlFinitePoint(obstacle.centre) && std::isfinite(obstacle.radius) && obstacle.radius>0.f,"SDL invalid projected collision bound");
            sdlGeometryLogged=true;
            // These forbidden captain-origin circles include live part-centre
            // offsets and height separation; enclosing radii alone do not.
            Vector3f target=n->mSRT.t;
            if(sdlPhase==0 && distance>stand+5.f) {
                target.x+=dx*(distance-stand)/distance;target.z+=dz*(distance-stand)/distance;
            }
            require(sdlFinitePoint(target) && pluckSegmentClear(target,target)
                && pluckSegmentClear(n->mSRT.t,target),"SDL approach requires clear native route and stopping point");
            if(sdlPhase==0 && distance>stand+5.f) {sdlDirection(n,dx,dz,65);return nullptr;}
            sdlPhase=1;
        }
        if(sdlPhase==1) {
            require(distance*1.2f<radius,"SDL desired reticle outside native range");
            const float ex=n->mSRT.t.x+dx*1.2f-n->mCursorWorldPos.x;
            const float ez=n->mSRT.t.z+dz*1.2f-n->mCursorWorldPos.z;
            const float tolerance=std::max(5.f,C_NAVI_PARM(n,mCursorMoveSpeed)*gsys->getFrameTime()*.75f);
            const int stableBefore=sdlStableAim;
            // The observed reticle trails the live cursor by one tick. End
            // each correction pulse before using the next reticle observation,
            // otherwise a second pulse repeats the already completed movement.
            if(sdlAimReleasePending) {
                ordinaryInput();sdlAimReleasePending=false;sdlStableAim=0;
                sdlAimTrace(n,violet,"release_correction",ex,ez,tolerance,ready,stableBefore);return nullptr;
            }
            if(std::sqrt(ex*ex+ez*ez)>tolerance) {
                sdlStableAim=0;sdlDirection(n,ex,ez,20);sdlAimReleasePending=true;
                sdlAimTrace(n,violet,"correct",ex,ez,tolerance,ready,stableBefore);return nullptr;
            }
            ordinaryInput();if(!ready || ++sdlStableAim<3) {
                sdlAimTrace(n,violet,ready?"wait_stable":"wait_ready",ex,ez,tolerance,ready,stableBefore);return nullptr;
            }
            sdlAimTrace(n,violet,"request_throw",ex,ez,tolerance,ready,stableBefore);
            sdlPhase=2;sdlThrowTicks=0;milestone("SDL_A_throw_requested",ticks);
        }
        if(sdlPhase==2) {
            ordinaryInput(sdlThrowTicks++<18?KBBTN_A:0);
            if(sdlThrowTicks==1 || sdlThrowTicks==19) {
                milestone(sdlThrowTicks==1?"SDL_A_pressed":"SDL_A_released",ticks);
                std::printf("P2_PURPLE_SDL_A_EDGE tick=%d hold_tick=%d emitted_a=%d raw=%d,%d read_only=1\n",ticks,sdlThrowTicks,
                    int(SDL_JoystickGetButton(ordinaryPad,SDL_CONTROLLER_BUTTON_A)),
                    int(SDL_JoystickGetAxis(ordinaryPad,SDL_CONTROLLER_AXIS_LEFTX)),int(SDL_JoystickGetAxis(ordinaryPad,SDL_CONTROLLER_AXIS_LEFTY)));
            }
        }
        return nullptr;
    }
    Piki* naturalStep(Navi* n) {
        ++phaseTicks;
        if(phase==2) pc_p2_input_script_set(1,0);
        Pom* violet = nullptr; int count = 0;
        Iterator flowers(bossMgr);
        CI_LOOP(flowers) {
            Boss* b = static_cast<Boss*>(*flowers);
            if (b && b->isAlive() && b->mObjType == OBJTYPE_Pom && pc_p2_violet(static_cast<Pom*>(b))) { violet = static_cast<Pom*>(b); ++count; }
        }
        if (phase == 0) {
            Iterator existing(pikiMgr);
            CI_LOOP(existing) {
                Piki* p=static_cast<Piki*>(*existing);
                require(!p || !p->isAlive() || !pc_p2_is_purple(p), "pre-existing Purple invalidates natural acquisition");
            }
            require(count == 1, "exact bound Violet missing");
            Iterator bodies(pikiMgr);
            CI_LOOP(bodies) {
                Piki* p = static_cast<Piki*>(*bodies);
                if (p->isAlive() && p->getState() == PIKISTATE_Normal && p->mMode == PikiMode::FormationMode && !pc_p2_is_purple(p)) { input = p; break; }
            }
            if (!input) return nullptr;
            GameStat::update(); startingField = GameStat::mapPikis;
            phase = 1; phaseTicks = 0;
            milestone("natural_input_selected",ticks);
            std::printf("P2_PURPLE_NATURAL_START field=%d violet=%.1f,%.1f,%.1f\n", startingField, violet->mSRT.t.x, violet->mSRT.t.y, violet->mSRT.t.z);
        }
        if (phase == 1) {
            if (input && input->isAlive() && !pc_p2_is_purple(input) && !input->isStickTo() && violet
                && input->getState() == PIKISTATE_Normal && phaseTicks % 60 == 0) {
                input->changeMode(PikiMode::FreeMode,n); input->mFSM->transit(input,PIKISTATE_Flying);
                // Sweep the scripted reticle through the native arc; its nominal
                // endpoint is not the ground intercept when hold height varies.
                const char* fixedAim = std::getenv("P2_PURPLE_AIM_SCALE");
                const float aimScale = fixedAim ? std::atof(fixedAim) : 0.8f + 0.1f * ((phaseTicks / 60) % 9);
                Vector3f aim = n->mSRT.t + (violet->mSRT.t - n->mSRT.t) * aimScale;
                n->throwPiki(input,aim);
                milestone("native_throw",ticks);
                std::printf("P2_PURPLE_SCRIPTED_THROW real_collision=1 aim_scale=%.2f captain=%.1f,%.1f,%.1f velocity=%.1f,%.1f,%.1f\n",
                    aimScale,n->mSRT.t.x,n->mSRT.t.y,n->mSRT.t.z,input->mVelocity.x,input->mVelocity.y,input->mVelocity.z);
            }
            Iterator heads(itemMgr->getPikiHeadMgr());
            CI_LOOP(heads) {
                PikiHeadItem* h = static_cast<PikiHeadItem*>(*heads);
                if (h && h->isAlive() && h->mP2Purple && h->mGroundTriangle
                    && std::fabs(h->mSRT.t.y-mapMgr->getMinY(h->mSRT.t.x,h->mSRT.t.z,true))<1.f) {
                    if(!approachAndPluck(n,h,violet)) break;
                    phase=2; phaseTicks=0; input=nullptr;
                    std::puts("P2_VIOLET_REAL_SPROUT captain_pluck_requested=1 actor_position_injected=0"); break;
                }
            }
        }
        if (phase == 2) {
            Iterator bodies(pikiMgr);
            CI_LOOP(bodies) {
                Piki* p=static_cast<Piki*>(*bodies);
                if (p->isAlive() && pc_p2_is_purple(p) && p->getState()==PIKISTATE_Normal && p->mMode==PikiMode::FormationMode) {
                    GameStat::update(); require(int(GameStat::mapPikis)==startingField,"conversion/pluck population");
                    require(pc_throw_selection_class(p)==4 && pc_piki_carry_strength(p)==10,"selection/strength");
                    milestone("native_acquisition_verified",ticks);
                    std::puts("P2_PURPLE_ACQUISITION_PASS scripted_throw=1 native_conversion=1 captain_pluck=1 selection=4 strength=10");
                    return p;
                }
            }
        }
        if (phase == 2 && phaseTicks > 0 && phaseTicks % 180 == 0) {
            Iterator retryHeads(itemMgr->getPikiHeadMgr());
            CI_LOOP(retryHeads) {
                PikiHeadItem* h = static_cast<PikiHeadItem*>(*retryHeads);
                if (!h || !h->isAlive() || !h->mP2Purple || !h->canPullout()) continue;
                require(pluckAttempts < 3, "native pluck failed after three staged attempts");
                phase=1;phaseTicks=0;
                approachAndPluck(n,h,violet);
                break;
            }
        }
        if(phaseTicks%120==0) std::printf("P2_PURPLE_NATURAL_PROGRESS phase=%d ticks=%d violet_state=%d\n",phase,phaseTicks,violet?violet->getCurrentState():-1);
        require(phaseTicks<1800,"natural acquisition timeout"); return nullptr;
    }

    bool targetPresent() const {
        if (!tekiMgr) return false;
        Iterator it(tekiMgr);
        CI_LOOP(it) {
            BTeki* actor=static_cast<BTeki*>(*it);
            if (actor==target && pc_p2_campaign_source(actor)==2
                && pc_randomizer_generator_id(actor->mGenerator)==targetUid) return true;
        }
        return false;
    }
    void diagnostics(Navi* n) {
        if(n && n->mCollInfo && n->mCollInfo->hasInfo()) auditBody("captain",n);
        if(itemMgr && itemMgr->getPikiHeadMgr()) { Iterator heads(itemMgr->getPikiHeadMgr()); CI_LOOP(heads) {
            PikiHeadItem* head=static_cast<PikiHeadItem*>(*heads);
            if(head && head->isAlive() && head->mP2Purple) std::printf("P2_PURPLE_SPROUT_OBSERVATION xyz=%.3f,%.3f,%.3f pullable=%d\n",
                head->mSRT.t.x,head->mSRT.t.y,head->mSRT.t.z,int(head->canPullout()));
        } }
        if(bossMgr) { Iterator flowers(bossMgr); CI_LOOP(flowers) {
            Boss* b=static_cast<Boss*>(*flowers);
            if(b && b->isAlive() && b->mObjType==OBJTYPE_Pom && pc_p2_violet(static_cast<Pom*>(b))) {
                auditBody("violet",b);
                if(n && n->mCollInfo && b->mCollInfo && n->mCollInfo->hasInfo() && b->mCollInfo->hasInfo()) {
                    CollPart* captainPart=nullptr;CollPart* violetPart=nullptr;Vector3f push;
                    const bool contact=n->mCollInfo->checkCollision(b->mCollInfo,&captainPart,&violetPart,push);
                    std::printf("P2_PURPLE_PLUCK_CONTACT contact=%d captain_part=%u violet_part=%u push=%.3f,%.3f,%.3f read_only=1\n",
                        int(contact),captainPart?unsigned(captainPart->getID().mId):0,violetPart?unsigned(violetPart->getID().mId):0,
                        contact?push.x:0,contact?push.y:0,contact?push.z:0);
                }
            }
        } }
        if(haul && pelletMgr) { Iterator bodies(pelletMgr); CI_LOOP(bodies) {
            if(static_cast<Pellet*>(*bodies)==haul) {auditBody("cargo",haul);break;}
        } }
        const char* state="unavailable"; const char* clip="unavailable"; float clipPhase=0;
        const bool present=target && targetPresent();
        if (present) pc_p2_chappy_probe(target,&state,&clip,&clipPhase);
        if (present && acquired) std::printf("P2_PURPLE_COMBAT_GEOMETRY uid=%u target=%.3f,%.3f,%.3f source=%.3f,%.3f,%.3f source_velocity=%.3f,%.3f,%.3f\n",
            targetUid,target->mSRT.t.x,target->mSRT.t.y,target->mSRT.t.z,
            acquired->mSRT.t.x,acquired->mSRT.t.y,acquired->mSRT.t.z,
            acquired->mVelocity.x,acquired->mVelocity.y,acquired->mVelocity.z);
        const auto flight=pc_p2_purple_flight_sample(acquired);
        std::printf("P2_PURPLE_COMBAT_PROGRESS tick=%d acquisition_phase=%d acquisition_ticks=%d combat_ticks=%d navi=%d pause=%d ui=%d target_present=%d uid=%u source=2 health=%.3f queued=%.3f enemy_state=%s clip=%s clip_phase=%.3f piki_state=%d flight=%d staged=%d isolated=%d\n",
            ticks,phase,phaseTicks,combatTicks,n&&n->getCurrState()?n->getCurrState()->getID():-1,
            int(gameflow.mPauseAll),int(gameflow.mIsUIOverlayActive),int(present),targetUid,
            present?target->mHealth:-1.f,present?target->mStoredDamage:-1.f,state?state:"null",clip?clip:"null",clipPhase,
            acquired?acquired->getState():-1,int(flight.phase),int(descentStaged),int(isolated));
    }
    void combatStep(Navi* n) {
        require(++combatTicks<900,"adult direct contact/damage timeout (see progress)");
        require(acquired->isAlive() && pc_p2_is_purple(acquired),"acquired Purple lost");
        if (!target) {
            require(pc_p2_purple_direct_enabled() && pc_p2_purple_flight_enabled(),"direct/flight profiles disabled");
            unsigned requested=0;
            const char* uidText=std::getenv("P2_PURPLE_COMBAT_UID");
            if (uidText) {
                char* end=nullptr; errno=0;
                const unsigned long value=std::strtoul(uidText,&end,10);
                require(*uidText && *uidText!='-' && end && !*end && !errno && value>0 && value<=UINT_MAX,"invalid decimal target UID");
                requested=static_cast<unsigned>(value);
            }
            Iterator enemies(tekiMgr);
            CI_LOOP(enemies) {
                BTeki* candidate=static_cast<BTeki*>(*enemies);
                if (!candidate || !candidate->isAlive() || pc_p2_campaign_source(candidate)!=2
                    || !pc_p2_chappy_registered(candidate) || !pc_p2_purple_direct_adult_registered(candidate)) continue;
                const unsigned uid=pc_randomizer_generator_id(candidate->mGenerator);
                if (requested && uid!=requested) continue;
                if (!target || uid<targetUid) { target=candidate; targetUid=uid; }
            }
            if (!target) return; // Later generated actors may register after stage entry.
            require(target->mHealth>50.f && std::isfinite(target->mHealth) && target->mStoredDamage==0.f,
                "adult must be alive above 50 HP with no pending damage");
            parkPosition=n->mSRT.t;
            // Park other squad members at the acquisition site and detach them
            // from formation before moving the captain. No enemy is relocated.
            Iterator squad(pikiMgr);
            CI_LOOP(squad) {
                Piki* p=static_cast<Piki*>(*squad);
                if (p && p!=acquired && p->isAlive()) {
                    require(!p->isStickTo(),"other squad member already attached");
                    p->changeMode(PikiMode::FreeMode,n); p->resetPosition(parkPosition);
                }
            }
            initialHealth=target->mHealth;
            std::printf("P2_PURPLE_COMBAT_BASELINE uid=%u target=%p view=%p health=%.3f native_max=%.3f family_max=%.3f regen_rate=%.6f\n",
                targetUid,static_cast<void*>(target),static_cast<void*>(static_cast<PelletView*>(target)),
                initialHealth,target->getMaxLife(),pc_p2_chappy_max_health(target,-1.f),target->getParameterF(TPF_LifeRecoverRate));
            require(std::isfinite(target->getMaxLife()) && std::fabs(initialHealth-target->getMaxLife())<0.01f,
                "adult must start at native maximum health for regeneration accounting");
            std::printf("P2_PURPLE_COMBAT_TARGET uid=%u source=2 target=%p piki=%p health_before=%.3f queued_before=%.3f generated_actor=1 adapter_registered=1 other_squad_parked=1\n",
                targetUid,static_cast<void*>(target),static_cast<void*>(acquired),initialHealth,target->mStoredDamage);
        }
        require(targetPresent() && target->isAlive(),"configured generated adult disappeared/died");
        require(pc_p2_chappy_registered(target) && pc_p2_purple_direct_adult_registered(target),"adult adapter registration lost");
        if (!thrown) {
            const Vector3f pos=target->mSRT.t;
            n->resetPosition(Vector3f(pos.x-90.f,mapMgr->getMinY(pos.x-90.f,pos.z,true),pos.z));
            acquired->changeMode(PikiMode::FreeMode,n);
            acquired->mFSM->transit(acquired,PIKISTATE_Flying);
            n->throwPiki(acquired,Vector3f(pos.x+42.f,pos.y,pos.z));
            require(pc_p2_purple_flight_active(acquired),"native throw did not arm Purple flight");
            thrown=true; throwTick=combatTicks; ++throwAttempts;
            std::printf("P2_PURPLE_COMBAT_THROW attempt=%d uid=%u source=2 target=%p piki=%p native_throw=1 captain_position_staged=1 enemy_modified=0 controls_validated=0\n",
                throwAttempts,targetUid,static_cast<void*>(target),static_cast<void*>(acquired));
            return;
        }
        maxQueued=target->mStoredDamage>maxQueued?target->mStoredDamage:maxQueued;
        const float delta=initialHealth-target->mHealth;
        require(std::isfinite(delta) && std::isfinite(target->mStoredDamage),"nonfinite target damage");
        // BTeki::update applies queued damage through chappy_update, then
        // regenerates dt * (getMaxLife() * LifeRecoverRate). Include the first
        // observed damaged frame. Earlier full-health frames clamp to maximum
        // and contribute nothing. Each subsequent still-damaged frame counts.
        const float dt=NSystem::getFrameTime();
        const float maximum=target->getMaxLife();
        const float rate=target->getParameterF(TPF_LifeRecoverRate);
        const float frameRecovery=dt*(maximum*rate);
        require(std::isfinite(dt) && dt>0.f && dt<=0.5f && std::isfinite(maximum)
            && maximum>0.f && std::fabs(maximum-initialHealth)<0.01f
            && std::isfinite(rate) && rate>=0.f && std::isfinite(frameRecovery),
            "invalid/changing native regeneration parameters");
        if (delta>0.f) {
            regeneration+=frameRecovery; ++regenerationFrames;
            require(regeneration<5.f,"native regeneration exceeds bounded 5 HP observation budget");
            std::printf("P2_PURPLE_COMBAT_REGEN uid=%u frame=%d dt=%.6f max_health=%.3f rate=%.8f frame_recovery=%.6f total_recovery=%.6f raw_delta=%.6f compensated_delta=%.6f\n",
                targetUid,regenerationFrames,dt,maximum,rate,frameRecovery,regeneration,delta,delta+regeneration);
        }
        const auto flight=pc_p2_purple_flight_sample(acquired);
        // Let the native throw reach its descent phase. Stage only the source
        // once; collision traversal and attack dispatch remain engine-owned.
        // This bounded collision setup deliberately does not certify aiming.
        if (!descentStaged && !isolated && delta==0.f && maxQueued==0.f
            && flight.phase==PcP2PurpleFlightPhase::Descent) {
            acquired->resetPosition(target->mSRT.t+Vector3f(0,80,0));
            acquired->mVelocity=Vector3f(0,-100,0);
            acquired->mTargetVelocity=acquired->mVelocity;
            descentStaged=true;
            std::printf("P2_PURPLE_COMBAT_DESCENT_SETUP uid=%u source=2 source_position_staged=1 source_velocity_staged=1 flight_phase_injected=0 enemy_modified=0 collision_injected=0\n",targetUid);
        }
        if (!isolated && (delta>0.f || maxQueued>0.f)) {
            // Stop follow-up ordinary attacks after native collision evidence.
            // Do not touch enemy damage queues, health, or FSM.
            if (acquired->isStickTo()) acquired->endStickObject();
            acquired->changeMode(PikiMode::FreeMode,n);
            acquired->resetPosition(parkPosition);
            n->resetPosition(parkPosition);
            isolated=true;
            std::printf("P2_PURPLE_COMBAT_CONTACT_OBSERVATION uid=%u source=2 target=%p piki=%p health_before=%.3f health_after=%.3f delta=%.3f queued=%.3f flight=%d post_contact_source_isolated=1 production_collision_marker_required=1\n",
                targetUid,static_cast<void*>(target),static_cast<void*>(acquired),initialHealth,target->mHealth,delta,target->mStoredDamage,int(flight.phase));
        }
        // Retry only an undamaging completed throw after native recovery; do
        // not force the Pikmin state/flight to finish or replay a claimed hit.
        if (!isolated && combatTicks-throwTick>=180 && delta==0.f && maxQueued==0.f
            && acquired->getState()==PIKISTATE_Normal && !acquired->isStickTo()
            && !pc_p2_purple_flight_active(acquired)) {
            require(throwAttempts<3,"three completed native throws missed adult direct damage");
            std::printf("P2_PURPLE_COMBAT_RETRY uid=%u source=2 completed_attempt=%d native_recovery=1 health=%.3f queue=%.3f\n",
                targetUid,throwAttempts,target->mHealth,target->mStoredDamage);
            thrown=false; descentStaged=false;
        }
        if (isolated && ++observedTicks>=30 && target->mStoredDamage==0.f) {
            require(delta>45.f && delta<=50.f && std::fabs(delta+regeneration-50.f)<0.05f,
                "adult native health delta plus measured regeneration is not 50");
            require(maxQueued==0.f || std::fabs(maxQueued-50.f)<0.01f,"unexpected observed queued damage");
            std::printf("P2_PURPLE_COMBAT_HEALTH_EVIDENCE mode=adult_direct uid=%u source=2 target=%p piki=%p health_before=%.3f health_after=%.3f delta=%.3f max_observed_queue=%.3f regeneration=%.6f compensated_delta=%.6f regen_frames=%d exact_production_queue_delta_required=50 native_throw=1 injected_damage=0 forced_enemy_state=0 production_collision_marker_required=1 dwarf_quake_pending=1 dwarf_crush_pending=1\n",
                targetUid,static_cast<void*>(target),static_cast<void*>(acquired),initialHealth,target->mHealth,delta,maxQueued,regeneration,delta+regeneration,regenerationFrames);
            std::fflush(nullptr); std::_Exit(0);
        }
    }


public:
    void draw(Graphics& gfx) override {
        PlugPikiApp::draw(gfx);
        if(ordinarySaveMode() && (ordinaryDiaryFrames==30 || ordinaryDiaryFrames==90
            || ordinaryDiaryFrames==180 || ordinaryDiaryFrames==240)) {
            const std::string path="ordinary-diary-"+std::to_string(ordinaryDiaryFrames)+".ppm";
            ordinaryCapture(path.c_str());
        }
    }
    int idle() override {
        // Borrow the actual current captain for this one idle only. The engine
        // trace is explicitly acquisition-only, bounded, and read-only. Arm
        // during an existing pulse so ordinary startup collisions do not fill
        // the trace before the failing approach; retain the force guard below.
        pc_purple_collision_trace_context(naviMgr ? naviMgr->getNavi() : nullptr,
            (sdlPulseActive || sdlPluckBraking) && sdlAcquisitionMode(),static_cast<std::uint64_t>(ticks)+1);
        const int result=PlugPikiApp::idle();
        Navi* n=naviMgr?naviMgr->getNavi():nullptr;
        // Injection modifies the initialized runtime, never an engine-free stand-in.
        // The real guard then executes before diagnostics, pause/movie or any other return.
        injectInitializedGuard(n);
        n=naviMgr?naviMgr->getNavi():nullptr;
        const bool expectedTeardown=sunsetRequested && sunsetSeen
            && gameflow.mCurrGameSectionID==SECTION_OnePlayer && flowCont.mGameEndFlag==GAMEEND_None
            && gameflow.mWorldClock.mCurrentDay==expectedDay && stockOne();
        const bool missingAllowed=!captainSeen || expectedTeardown;
        p2_fixture_require_captain(n!=nullptr,GameStat::orimaDead,naviMgr && n && naviMgr->isNaviDead(n),
            n && n->getCurrState() && n->getCurrState()->getID()==NAVISTATE_Dead,n?n->mHealth:-1.f,ticks,missingAllowed);
        if(n) {
            if(!captainSeen) milestone("initialized_captain_seen",ticks);
            captainSeen=true;
        }
        if (++ticks%120==0) diagnostics(n);
        if(mode("transport_manual") && (SDL_GetKeyboardState(nullptr)[SDL_SCANCODE_F7] || std::ifstream("manual-reset.request").good())) {
            std::puts("P2_PURPLE_MANUAL_RESET_REQUEST fresh_session_required=1");std::fflush(nullptr);std::_Exit(90);
        }
        require(ticks<(sunsetRequested?15000:6000),"global fixture timeout");
        if(mode("persistence_resume")) pc_p2_input_script_set(1,(!n || gameflow.mIsUIOverlayActive) && ticks%20<4?KBBTN_A:0,0,0);
        if(mode("natural_resume")) ordinaryInput(); // No blind A presses into load/title/save UI.
        if(sunsetRequested) {
            if(ordinarySaveMode()) ordinarySunsetStep();else sunsetStep();
            if(gameflow.mMoviePlayer&&gameflow.mMoviePlayer->mIsActive) gameflow.mMoviePlayer->requestSkip();
            return result;
        }
        if(gameflow.mMoviePlayer&&gameflow.mMoviePlayer->mIsActive) { gameflow.mMoviePlayer->requestSkip(); return result; }
        if(!n||!pikiMgr||!itemMgr||!bossMgr||!tekiMgr||!mapMgr||!n->getCurrState()
            ||gameflow.mPauseAll||gameflow.mIsUIOverlayActive) return result;
        if(!activeSeen && (n->getCurrState()->getID()==NAVISTATE_Walk || n->getCurrState()->getID()==NAVISTATE_Idle)) {
            activeSeen=true;milestone("active_gameplay",ticks);
        }
        if(mode("persistence_resume") || mode("natural_resume")) {
            // The restored captain exists during ship/map entry before the
            // playable stage actors are ready. Match the ordinary fixture's
            // active walk/idle gate before checking live combat bindings.
            const int state=n->getCurrState()->getID();
            if(state==NAVISTATE_Walk || state==NAVISTATE_Idle) {
                if(mode("natural_resume")) ordinaryResume(n);else resumePersistence(n);
            }
            return result;
        }
        if (!acquired) {
            if(sdlAcquisitionMode()) {
                if(!activeSeen) {ordinaryInput();return result;}
                acquired=sdlStep(n);return result;
            }
            const int state=n->getCurrState()->getID();
            if(state==NAVISTATE_Walk||state==NAVISTATE_Idle) {
                // Ordinary visible play leaves the starting squad in its Onion.
                // This ready-scene companion explicitly uses native withdrawal.
                if(mode("transport_manual") && !manualWithdrawRequested) {
                    GameStat::update();
                    GoalItem* onion=itemMgr->getContainer(Red);
                    if(int(GameStat::mapPikis)==0 && onion && onion->getTotalStorePikis()>=20) {
                        onion->exitPikis(20);manualWithdrawRequested=true;
                        std::puts("P2_PURPLE_MANUAL_WITHDRAW count=20 native_onion_exit=1 scripted_setup=1");
                    }
                }
                if(mode("transport_red_control") || mode("transport_staged") || mode("transport_manual")) {
                    const bool stagedStart=mode("transport_staged") || mode("transport_manual");
                    if(stagedStart) {
                        GameStat::update();
                        // Native withdrawal creates actors over successive ticks.
                        // Do not stage the first exit while the rest are stored.
                        if(int(GameStat::mapPikis)!=20) return result;
                    }
                    int aliveCount=0,normalCount=0,redCount=0,formationCount=0;
                    Iterator squad(pikiMgr);CI_LOOP(squad) {
                        Piki* p=static_cast<Piki*>(*squad);
                        if(p && p->isAlive()) {
                            ++aliveCount;
                            if(p->getState()==PIKISTATE_Normal) ++normalCount;
                            if(p->mColor==Red && !pc_p2_is_purple(p) && !p->mP2White) ++redCount;
                            if(p->mMode==PikiMode::FormationMode) ++formationCount;
                        }
                        if(p && p->isAlive() && p->mColor==Red && !pc_p2_is_purple(p) && !p->mP2White
                            && p->getState()==PIKISTATE_Normal && !p->isStickTo()
                            && (p->mMode==PikiMode::FormationMode || stagedStart)) { acquired=p;break; }
                    }
                    if(!acquired && ticks%120==0) std::printf("P2_PURPLE_START_WAIT alive=%d normal=%d ordinary_red=%d formation=%d\n",aliveCount,normalCount,redCount,formationCount);
                    if(acquired) {
                        GameStat::update();require(int(GameStat::mapPikis)==20,"ordinary Red control starting squad");
                        if(mode("transport_red_control")) std::puts("P2_PURPLE_HAUL_RED_START field=20 native_red=1 source_identity_injected=0");
                        else {
                            const int previousMode=acquired->mMode;
                            acquired->changeMode(PikiMode::FormationMode,n);
                            std::printf("P2_PURPLE_STAGED_GATHER previous_mode=%d scripted_gather=1 actor_position_injected=0\n",previousMode);
                            pc_p2_make_purple(acquired);
                            require(pc_p2_is_purple(acquired) && pc_piki_carry_strength(acquired)==10,"staged Purple identity/strength");
                            int purpleCount=0,redCount=0;Iterator counted(pikiMgr);CI_LOOP(counted) {
                                Piki* p=static_cast<Piki*>(*counted);if(!p || !p->isAlive()) continue;
                                if(pc_p2_is_purple(p)) ++purpleCount;else if(p->mColor==Red && !p->mP2White) ++redCount;
                            }
                            require(purpleCount==1 && redCount==19,"staged squad identity counts");
                            std::puts("P2_PURPLE_HAUL_STAGED_START field=20 starting_species_injected=1 native_acquisition=0 actor_position_injected=0");
                        }
                    }
                } else acquired=naturalStep(n);
            }
            return result;
        }
        if(mode("sdl_acquire")) {ordinaryInput();std::fflush(nullptr);std::_Exit(0);}
        if(ordinarySaveMode()) beginOrdinarySave(n);
        else if(mode("persistence_dayend")) beginPersistence(n);
        else if(mode("transport_delivery") || mode("transport_positive") || mode("transport_red_control") || mode("transport_staged") || mode("transport_manual")) transportStep(n);
        else combatStep(n);
        return result;
    }
};
int main(int argc,char** argv) {
    setvbuf(stdout,nullptr,_IONBF,0);
    const char* guardCase=std::getenv("P2_PURPLE_GUARD_CASE");
    require(!guardCase || !std::strcmp(guardCase,"health") || !std::strcmp(guardCase,"manager")
        || !std::strcmp(guardCase,"global") || !std::strcmp(guardCase,"dead_state") || !std::strcmp(guardCase,"missing")
        || !std::strcmp(guardCase,"health_pause") || !std::strcmp(guardCase,"missing_movie"),"unknown initialized guard case");
    const char* mode=std::getenv("P2_PURPLE_COMBAT_MODE");
    if(mode && std::strcmp(mode,"sdl_acquire") && std::strcmp(mode,"sdl_dayend") && std::strcmp(mode,"natural_dayend") && std::strcmp(mode,"natural_resume") && std::strcmp(mode,"adult_direct") && std::strcmp(mode,"persistence_dayend") && std::strcmp(mode,"persistence_resume") && std::strcmp(mode,"transport_delivery") && std::strcmp(mode,"transport_positive") && std::strcmp(mode,"transport_red_control") && std::strcmp(mode,"transport_staged") && std::strcmp(mode,"transport_manual")) {
        std::printf("P2_PURPLE_COMBAT_UNIMPLEMENTED mode=%s implemented=sdl_acquire,sdl_dayend,adult_direct,persistence_dayend,persistence_resume,natural_dayend,natural_resume,transport_delivery,transport_positive,transport_red_control,transport_staged,transport_manual\n",mode); return 2;
    }
    SDL_SetMainReady(); pc_gpu_preference_apply(); pc_bbft_init(argc,argv);
    require(pc_randomizer_purple_campaign() && pc_randomizer_p2_bridge(),"ordinary Purple seed campaign required");
    if(!pc_window_init(mode && !std::strcmp(mode,"transport_manual")?"Purple carry smoke - staged Purple - F7 resets":"Purple campaign combat fixture",960,540)) return 3;
    pc_settings_init(); pc_window_set_display_mode(PC_WINDOW_FULLSCREEN_WINDOWED);
    if(mode && (!std::strcmp(mode,"sdl_acquire") || !std::strcmp(mode,"sdl_dayend") || !std::strcmp(mode,"natural_dayend") || !std::strcmp(mode,"natural_resume"))) ordinaryController();
    pc_window_set_window_size(960,540); pc_window_center();
    std::puts("Experimental preview window set to 960x540 windowed and centered");
    int w=0,h=0,x=0,y=0; SDL_Window* window=SDL_GL_GetCurrentWindow();
    SDL_GetWindowSize(window,&w,&h); SDL_GetWindowPosition(window,&x,&y);
    require(w==960&&h==540,"window dimensions");
    std::printf("P2_FIXTURE_WINDOW width=%d height=%d x=%d y=%d\n",w,h,x,y);
    milestone("window_ready",0);
    std::printf("P2_PURPLE_COMBAT_SCOPE mode=%s natural_acquisition=%d player_controls_validated=0 production_collision_marker_required=1\n",
        mode?mode:"adult_direct",int(!mode || (std::strcmp(mode,"natural_resume") && std::strcmp(mode,"persistence_resume") && std::strcmp(mode,"transport_red_control") && std::strcmp(mode,"transport_staged") && std::strcmp(mode,"transport_manual"))));
    gsys->Initialise(); pc_settings_p2d_init(); nodeMgr=new NodeMgr();
    gsys->run(new PurpleCombatApp()); return 0;
}
