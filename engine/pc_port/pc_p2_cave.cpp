#include "pc_p2_cave.h"
#include "pc_p2_cave_visible.h"
#include "pc_p2_cave_generate.h"
#include "pc_p2_cave_nav_diagnostics.h"
#include "pc_p2_cave_anchor.h"
#include "pc_p2_cave_entry_policy.h"
#include "pc_p2_cave_readiness_policy.h"
#include "pc_p2_beasts_failure_policy.h"
#include "Graphics.h"
#include "Camera.h"
#include "Shape.h"
#include "pc_p2_preview.h"
#include "pc_p2_purple.h"
#include "pc_p2_white.h"
#include "pc_p2_species.h"
#include "pc_p2_species_schema.h"
#include "pc_p2_cave_transfer.h"
#include "pc_p2_cave_route_policy.h"
#include "pc_p2_teki_lifetime.h"
#include "pc_randomizer.h"
#include "pc_p2_ship_store.h"
#include "pc_p2_bulbmin.h"
#include "pc_p2_cave_generator.h"  // lane 41 (#480) runtime generator hook
#include "pc_p2_cave_rooms_engine.h"  // lane 44 (#482) proxy room/unit instantiation
#include "pc_p2_cave_geometry_engine.h"  // lane 45 (#483) real unit geometry + elec gate
#include "pc_p2_cave_items_engine.h"  // lane 46 (#484) physical cave-item placement
#include "pc_p2_cave_bud_actor.h"  // lane 48 (#486) real seeded Candypop bud actor
#include "pc_p2_cave_carry_engine.h"  // lane 50 (#488) carry blocking at hazards
#include "pc_bbft.h"
#include "Piki.h"
#include "PikiMgr.h"
#include "PikiState.h"
#include "PikiHeadItem.h"
#include "Navi.h"
#include "NaviMgr.h"
#include "NaviState.h"
#include "ItemMgr.h"
#include "GoalItem.h"
#include "MoviePlayer.h"
#include "PlayerState.h"
#include "gameflow.h"
#include "FlowController.h"
#include "OnePlayerSection.h"
#include "system.h"
#include <SDL2/SDL.h>
#include "pc_p2_cave_dialog_window.h"
#if defined(_WIN32)
#include <process.h>
#else
#include <unistd.h>
#endif
#include <cstdio>
#include <cstdlib>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <sstream>
#include <vector>

__attribute__((weak)) bool pc_netplay_session_active(void);

namespace {
int floorId=0;
bool beasts=false;
bool cargoTerminal=false;
int checkpointSchema=1;
std::string token;
bool requested=false;
bool tutorialEntry=false;
bool boundedForestCheckpoint=false;
bool completed=false;
float titleTimer=0;
P2CaveAnchor anchor;
Shape* transitionShape=nullptr;
P2CaveNavRate navRate;
unsigned navDrawCalls=0;
bool navMarkerLogged=false;
P2CaveSurfaceRoute surfaceRoute;
bool surfaceRouteLoaded=false;
bool surfaceWfgDestination=false;
unsigned long surfaceContextScene=0;
unsigned routeSpeciesMask=0;
std::set<std::string> activatedSurfaceTokens;
bool bodyContextReady=false;
unsigned long bodyContextScene=0;
void resetRouteSpecies(){routeSpeciesMask=0;}
bool online(){return pc_netplay_session_active && pc_netplay_session_active();}
bool tutorialSurfaceStage(){
    const char* surface=pc_pikipelago_surface_course();
    return surface && std::string(surface)=="tutorial" && flowCont.mCurrentStage
        && flowCont.mCurrentStage->mFileName
        && std::string(flowCont.mCurrentStage->mFileName)=="stages/p2_tutorial.ini";
}
using Survivor = P2CaveSurvivor;
void invalid(const char* reason){resetRouteSpecies();std::fprintf(stderr,"Invalid P2 cave entry: %s\n",reason);std::abort();}
bool routeFile(const std::string& path,std::string& bytes){
    std::ifstream in(path,std::ios::binary|std::ios::ate);if(!in)return false;
    const auto size=in.tellg();if(size<=0 || size>64*1024*1024)return false;
    bytes.resize(static_cast<size_t>(size));in.seekg(0);
    return bool(in.read(&bytes[0],static_cast<std::streamsize>(bytes.size())));
}
unsigned authorizeRouteSpecies(const P2CaveSurfaceRoute& route,const std::string& routeBytes){
    unsigned mask=0;for(const auto& p:route.party.squad)
        if(p.species==P2SpeciesPurple || p.species==P2SpeciesWhite)mask|=1u<<p.species;
    if(!mask)return 0; // Retained wire2 alone never activates a species.
    std::ifstream in("p2-cave-route-species.txt");P2CaveRouteActivation request;
    if(!in || !p2_cave_route_activation_read(in,request))invalid("species authorization");
    std::map<std::string,std::string> bytes;size_t total=0;
    for(const auto& file:request.files){std::string content;
        if(!routeFile(file.first,content))invalid("species bank missing or oversized");
        total+=content.size();if(total>256u*1024u*1024u)invalid("species bank aggregate size");
        bytes.emplace(file.first,std::move(content));}
    if(!p2_cave_route_activation_valid(request,route,routeBytes,bytes))invalid("species bank or route identity");
    return mask;
}
bool surfaceSafe(){
    Navi* n=naviMgr?naviMgr->getNavi():nullptr;
    return surfaceRouteLoaded && !completed && n && n->getCurrState() && playerState
        && p2_cave_surface_route_eligible(surfaceRoute.entrance,n->mSRT.t.x,n->mSRT.t.y,n->mSRT.t.z,
            n->getCurrState()->getID()==NAVISTATE_Walk,gameflow.mPauseAll,gameflow.mIsUIOverlayActive,
            gameflow.mMoviePlayer && gameflow.mMoviePlayer->mIsActive,playerState->mInDayEnd,online(),n->mHealth);
}
void loadSurfaceRoute(){
    const auto scene=pc_p2_scene_generation();
    if(surfaceContextScene!=scene){
        const bool oldSurface=surfaceRouteLoaded;
        resetRouteSpecies();surfaceRoute=P2CaveSurfaceRoute{};surfaceRouteLoaded=false;surfaceWfgDestination=false;
        if(oldSurface){completed=false;requested=false;anchor=P2CaveAnchor{};}
        surfaceContextScene=scene;
    }
    if(!tutorialSurfaceStage() || online()){resetRouteSpecies();return;}
    if(surfaceRouteLoaded || !naviMgr || !pikiMgr)return;
    Navi* n=naviMgr->getNavi();if(!n || !n->getCurrState())return;
    // Restoring a staged checkpoint must never revive an already dead captain.
    if(n->getCurrState()->getID()!=NAVISTATE_Walk || !std::isfinite(n->mHealth)
        || n->mHealth<=1 || naviMgr->isNaviDead(n) || gameflow.mPauseAll
        || gameflow.mIsUIOverlayActive || (gameflow.mMoviePlayer && gameflow.mMoviePlayer->mIsActive))return;
    std::ifstream present("p2-cave-route-surface.txt");if(!present)return;
    std::string routeBytes;if(!routeFile("p2-cave-route-surface.txt",routeBytes))invalid("surface route unreadable");
    std::istringstream in(routeBytes);
    P2CaveSurfaceRoute route;if(!p2_cave_surface_route_read(in,route))invalid("surface route");
    std::error_code destinationError;
    const bool destinationPresent=std::filesystem::exists("p2-cave-route-destination.txt",destinationError);
    if(destinationError)invalid("surface destination unreadable");
    bool wfgDestination=false;
    if(destinationPresent){
        std::ifstream destination("p2-cave-route-destination.txt");
        std::string magic,boundary,cave,extra;
        if(!(destination>>magic>>boundary>>cave) || magic!="P2_CAVE_ROUTE_DESTINATION_1"
            || boundary!=route.party.token || cave!="forest_2/f_02"
            || (destination>>extra) || !destination.eof())invalid("surface destination");
        wfgDestination=true;
    }
    // A scene reload may not treat the old staged boundary as fresh stock.
    // Ordinary return/reentry starts a new bounded process with a new token.
    if(activatedSurfaceTokens.count(route.party.token))invalid("surface token reused across scenes");
    std::vector<Piki*> actors;Iterator it(pikiMgr);
    CI_LOOP(it){Piki* p=static_cast<Piki*>(*it);if(p->isAlive())actors.push_back(p);}
    if(actors.size()!=route.party.squad.size())invalid("surface roster differs from staged actors");
    if(C_NAVI_PARM(n,mHealth)<=0)invalid("surface captain unavailable");
    // No typed species, maturity or captain-health write occurs before this
    // complete authorization/hash/model-set gate and actual native shape setup.
    resetRouteSpecies();routeSpeciesMask=authorizeRouteSpecies(route,routeBytes);
    if(routeSpeciesMask&(1u<<P2SpeciesPurple))pc_p2_purple_setup();
    if(routeSpeciesMask&(1u<<P2SpeciesWhite))pc_p2_white_setup();
    for(const auto& saved:route.party.squad)
        if((saved.species==P2SpeciesPurple && !pc_p2_purples_enabled())
            || (saved.species==P2SpeciesWhite && !pc_p2_whites_enabled()))invalid("surface species assets unavailable");
    activatedSurfaceTokens.insert(route.party.token);
    for(size_t i=0;i<actors.size();++i){
        const auto& saved=route.party.squad[i];Piki* p=actors[i];
        if((saved.species==3 && !pc_p2_purples_enabled()) || (saved.species==4 && !pc_p2_whites_enabled()))invalid("surface species assets unavailable");
        if(!pc_p2_set_species(p,saved.species))invalid("surface species");
        p->mHappa=saved.maturity;
        if(saved.species==3)pc_p2_make_purple(p);
        if(saved.species==4)pc_p2_make_white(p);
    }
    n->mHealth=C_NAVI_PARM(n,mHealth)*route.party.health;
    surfaceRoute=route;surfaceRouteLoaded=true;surfaceWfgDestination=wfgDestination;anchor=route.entrance;
    std::printf("P2_CAVE_SURFACE_READY token=%s survivors=%zu health=%.9g x=%.3f y=%.3f z=%.3f radius=%.3f\n",
        route.party.token.c_str(),actors.size(),route.party.health,anchor.x,anchor.y,anchor.z,anchor.radius);std::fflush(stdout);
}

// Output-only #1154 dialog-evidence candidate. These observations never select
// a button. The external OS consumer must corroborate mapped dialog/title,
// WM_TRANSIENT_FOR(parent_x11_window), modality, and the parent's _NET_WM_PID.
unsigned long dialogEvidenceSequence=0;
long dialogEvidencePid(){
#if defined(_WIN32)
    return static_cast<long>(_getpid());
#else
    return static_cast<long>(getpid());
#endif
}
std::string dialogEvidenceString(const char* text){
    std::string out="\"";
    if(text)for(const unsigned char* p=reinterpret_cast<const unsigned char*>(text);*p;++p){
        if(*p=='"' || *p=='\\'){out+='\\';out+=static_cast<char>(*p);}
        else if(*p<32){char escaped[7];std::snprintf(escaped,sizeof(escaped),"\\u%04x",unsigned(*p));out+=escaped;}
        else out+=static_cast<char>(*p);
    }
    return out+'"';
}
unsigned long dialogEvidenceBefore(const SDL_MessageBoxData& data,const char* phase,const char* action,
        const std::string& boundary,const char* cave,int floor){
    const unsigned long sequence=++dialogEvidenceSequence;
    int x=0,y=0,width=0,height=0;
    if(data.window){SDL_GetWindowPosition(data.window,&x,&y);SDL_GetWindowSize(data.window,&width,&height);}
    const PcP2CaveDialogWindow wm = pc_p2_cave_dialog_window(data.window);
    std::ostringstream out;
    out<<"{\"event\":\"begin\",\"sequence\":"<<sequence<<",\"pid\":"<<dialogEvidencePid()
       <<",\"phase\":"<<dialogEvidenceString(phase)<<",\"action\":"<<dialogEvidenceString(action)<<",\"token\":"<<dialogEvidenceString(boundary.c_str())
       <<",\"cave\":"<<dialogEvidenceString(cave)<<",\"floor\":"<<floor
       <<",\"title\":"<<dialogEvidenceString(data.title)<<",\"message\":"<<dialogEvidenceString(data.message)
       <<",\"flags\":"<<data.flags<<",\"video_driver\":"<<dialogEvidenceString(SDL_GetCurrentVideoDriver())
       <<",\"parent_sdl_window\":"<<(data.window?SDL_GetWindowID(data.window):0)
       <<",\"parent_title\":"<<dialogEvidenceString(data.window?SDL_GetWindowTitle(data.window):nullptr)
       <<",\"parent_flags\":"<<(data.window?SDL_GetWindowFlags(data.window):0)
       <<",\"parent_x\":"<<x<<",\"parent_y\":"<<y<<",\"parent_w\":"<<width<<",\"parent_h\":"<<height
       <<",\"syswm_available\":"<<(wm.available?"true":"false")
       <<",\"syswm_subsystem\":"<<wm.subsystem
       <<",\"parent_x11_window\":"<<wm.x11Window
       <<",\"parent_net_wm_pid_verification\":\"external_OS_required\""
       <<",\"button_disabled_state_supported\":false,\"buttons\":[";
    for(int i=0;i<data.numbuttons;++i){const auto& b=data.buttons[i];if(i)out<<',';
        out<<"{\"id\":"<<b.buttonid<<",\"text\":"<<dialogEvidenceString(b.text)<<",\"flags\":"<<b.flags
           <<",\"return_default\":"<<((b.flags&SDL_MESSAGEBOX_BUTTON_RETURNKEY_DEFAULT)?"true":"false")
           <<",\"escape_default\":"<<((b.flags&SDL_MESSAGEBOX_BUTTON_ESCAPEKEY_DEFAULT)?"true":"false")<<'}';}
    out<<"]}";
    std::printf("P2_CAVE_NATIVE_DIALOG %s\n",out.str().c_str());std::fflush(stdout);
    return sequence;
}
void dialogEvidenceAfter(unsigned long sequence,const SDL_MessageBoxData& data,
        const char* phase,const char* action,const std::string& boundary,const char* cave,int floor,int result,int choice){
    const std::string error=result?SDL_GetError():"";
    const char* selected=nullptr;
    if(result==0)for(int i=0;i<data.numbuttons;++i)
        if(data.buttons[i].buttonid==choice)selected=data.buttons[i].text;
    std::ostringstream out;
    out<<"{\"event\":\"end\",\"sequence\":"<<sequence<<",\"pid\":"<<dialogEvidencePid()
       <<",\"phase\":"<<dialogEvidenceString(phase)<<",\"action\":"<<dialogEvidenceString(action)<<",\"token\":"<<dialogEvidenceString(boundary.c_str())
       <<",\"cave\":"<<dialogEvidenceString(cave)<<",\"floor\":"<<floor
       <<",\"title\":"<<dialogEvidenceString(data.title)<<",\"rc\":"<<result<<",\"choice\":"<<choice
       <<",\"known_button_selected\":"<<(selected?"true":"false")
       <<",\"selected_label\":"<<dialogEvidenceString(selected)<<",\"sdl_error\":"<<dialogEvidenceString(error.c_str())<<'}';
    std::printf("P2_CAVE_NATIVE_DIALOG %s\n",out.str().c_str());std::fflush(stdout);
}

bool enterSurfaceCave(){
    if(!surfaceSafe() || pc_p2_cave_bud_pending())return false;
    P2CaveEntry party=surfaceRoute.party;party.squad.clear();
    Iterator it(pikiMgr);CI_LOOP(it){
        Piki* p=static_cast<Piki*>(*it);if(!p->isAlive())continue;
        const int state=p->getState(),species=pc_p2_species(p);
        if(state==PIKISTATE_Dying || state==PIKISTATE_Dead || state==PIKISTATE_Swallowed
            || state==PIKISTATE_Bury || state==PIKISTATE_Grow || p->getStickObject()
            || species<0 || species>(surfaceRoute.wireVersion==2?P2SpeciesWhite:P2SpeciesYellow))return false;
        party.squad.push_back({species,p->mHappa});
    }
    Iterator heads(itemMgr->getPikiHeadMgr());CI_LOOP(heads){if(static_cast<PikiHeadItem*>(*heads)->isAlive())return false;}
    Navi* n=naviMgr->getNavi();party.health=n->mHealth/C_NAVI_PARM(n,mHealth);
    const std::string text=p2_cave_surface_route_transfer(party,n->mSRT.t.x,n->mSRT.t.y,n->mSRT.t.z,surfaceRoute.wireVersion);
    if(text.empty())return false;
    const char* destination=surfaceWfgDestination?"White Flower Garden":"Emergence Cave";
    const std::string message=std::string("Enter ")+destination+" with all "+std::to_string(party.squad.size())+" surviving Pikmin?";
    const SDL_MessageBoxButtonData buttons[]={{SDL_MESSAGEBOX_BUTTON_ESCAPEKEY_DEFAULT,0,"Stay"},{SDL_MESSAGEBOX_BUTTON_RETURNKEY_DEFAULT,1,"Enter cave"}};
    SDL_MessageBoxData data={SDL_MESSAGEBOX_INFORMATION,SDL_GL_GetCurrentWindow(),destination,message.c_str(),2,buttons,nullptr};int choice=0;
    const unsigned long dialogSequence=dialogEvidenceBefore(data,"surface","enter",party.token,
        surfaceWfgDestination?"forest_2/f_02":"forest_1",0);
    const int dialogResult=SDL_ShowMessageBox(&data,&choice);
    dialogEvidenceAfter(dialogSequence,data,"surface","enter",party.token,
        surfaceWfgDestination?"forest_2/f_02":"forest_1",0,dialogResult,choice);
    if(dialogResult!=0 || choice!=1)return false;
    if(!surfaceSafe())return false;
    FILE* f=std::fopen("p2-cave-surface-transfer.tmp","wb");if(!f)return false;
    bool ok=std::fwrite(text.data(),1,text.size(),f)==text.size() && std::fflush(f)==0;
    if(std::fclose(f)!=0)ok=false;
    if(!ok || std::rename("p2-cave-surface-transfer.tmp","p2-cave-surface-transfer.txt")!=0)return false;
    completed=true;resetRouteSpecies();std::printf("P2_CAVE_SURFACE_TRANSFER token=%s survivors=%zu health=%.9g\n",party.token.c_str(),party.squad.size(),party.health);
    std::fflush(nullptr);std::_Exit(42);
}
// Tutorial later-floors entry admission (lanes tutorial2-descend-policy-native
// #757 + tutorial2-floor9-descend #807; consumer #747). NEW version admission
// (not a port): the shared header pc_p2_cave_entry_policy.h knows no
// P2_CAVE_ENTRY_4 version, so this TU-local mapping newly admits ENTRY_4 for
// tutorial staged floors 3-9 under the 32-hex token contract. Floors 3-8 are
// admitted here alongside floor 9 because the staged tutorial_2 floors 3-9
// uniformly carry ENTRY_4 headers (pins #757/#805) and the engine must accept
// the whole chain to reach floor 9; previously Invalid (version, floor) pairs
// outside this mapping still refuse exactly as before. The shared header
// stays read-only.
P2CaveEntryProfile p2_tutorial2_entry_profile(const std::string& version, int floor, const std::string& token){
    if(version=="P2_CAVE_ENTRY_4" && floor>=3 && floor<=9 && token.size()==32
        && token.find_first_not_of("0123456789abcdef")==std::string::npos)
        return P2CaveEntryProfile::Tutorial;
    return P2CaveEntryProfile::Invalid;
}
// Tutorial descend range: floors 1-8 transition downward (BulbminDescendFloor);
// floor 9 exits terminal (no floor 10).
// Beasts behavior is untouched (separate arms below).
bool p2_tutorial_descends(int floor){return floor>=1 && floor<=8;}
bool active(){return floorId && !completed && p2CavePreviewReady(beasts,floorId,pc_p2_preview_cargo_free_ready(),pc_p2_preview_ready(),pc_p2_preview_goal()!=nullptr,pc_p2_preview_cargo_count(),pc_p2_preview_pokos(),cargoTerminal) && naviMgr && naviMgr->getNavi() && naviMgr->getNavi()->getCurrState();}
bool safeTime(){return active() && !gameflow.mPauseAll && !gameflow.mIsUIOverlayActive
    && (!gameflow.mMoviePlayer || !gameflow.mMoviePlayer->mIsActive) && !playerState->mInDayEnd && !online();}

void navigationDiagnostic(){
    if(!floorId || !navRate.due(SDL_GetTicks()))return;
    Navi* n=naviMgr?naviMgr->getNavi():nullptr;
    const int state=n && n->getCurrState()?n->getCurrState()->getID():-1;
    const float x=n?n->mSRT.t.x:0,y=n?n->mSRT.t.y:0,z=n?n->mSRT.t.z:0;
    const float dx=anchor.x-x,dz=anchor.z-z;
    const bool inside=n && anchor.contains(x,y,z),safe=safeTime();
    const bool movie=gameflow.mMoviePlayer && gameflow.mMoviePlayer->mIsActive;
    const char* path=!anchor.enabled?"none":transitionShape?"model":"fallback_ring";
    std::printf("P2_CAVE_NAV seq=%u floor=%d captain=%d x=%.3f y=%.3f z=%.3f heading_rad=%.4f anchor_x=%.3f anchor_y=%.3f anchor_z=%.3f dx=%.3f dz=%.3f horizontal=%.3f vertical=%.3f radius=%.3f inside=%d state=%d walk=%d safe=%d pause=%d ui=%d movie=%d day_end=%d completed=%d pod=%d interaction_eligible=%d marker=%s draws=%u\n",
        navRate.count,floorId,int(n!=nullptr),x,y,z,n?n->mFaceDirection:0,anchor.x,anchor.y,anchor.z,dx,dz,std::hypot(dx,dz),std::fabs(y-anchor.y),anchor.radius,int(inside),state,int(state==NAVISTATE_Walk),int(safe),int(gameflow.mPauseAll),int(gameflow.mIsUIOverlayActive),int(movie),int(playerState && playerState->mInDayEnd),int(completed),int(pc_p2_preview_goal()!=nullptr),int(safe && inside && state==NAVISTATE_Walk),path,navDrawCalls);
    std::fflush(stdout);
}

const char* caveName(){return beasts?"Beasts Cave":bodyContextReady?"White Flower Garden":"Emergence Cave";}
void notice(const char* text){SDL_ShowSimpleMessageBox(SDL_MESSAGEBOX_INFORMATION,caveName(),text,SDL_GL_GetCurrentWindow());}
bool writeTransfer(const std::string& text){
    FILE* file=std::fopen("p2-cave-transfer.tmp","wb");
    if(!file)return false;
    bool ok=std::fwrite(text.data(),1,text.size(),file)==text.size() && std::fflush(file)==0;
    if(std::fclose(file)!=0)ok=false;
    return ok && std::rename("p2-cave-transfer.tmp","p2-cave-transfer.txt")==0;
}
}
int pc_p2_cave_floor(){return floorId;}
bool pc_p2_cave_surface_route_active(){return surfaceRouteLoaded && tutorialSurfaceStage() && pc_p2_scene_generation()==surfaceContextScene;}
bool pc_p2_cave_route_species_requested(int species){
    if(completed || online() || !tutorialSurfaceStage()
        || pc_p2_scene_generation()!=surfaceContextScene){resetRouteSpecies();return false;}
    return (species==P2SpeciesPurple || species==P2SpeciesWhite) && (routeSpeciesMask&(1u<<species));
}
bool pc_p2_cave_body_profile_context(unsigned long long seed,const std::string& cave,
        int floor,const std::string& boundaryToken){
    if(!bodyContextReady || completed || online() || pc_p2_scene_generation()!=bodyContextScene
        || !pc_pikipelago_room_preview() || !flowCont.mCurrentStage || !flowCont.mCurrentStage->mFileName
        || std::string(flowCont.mCurrentStage->mFileName)!="stages/chal0.ini"
        || pc_randomizer_enabled() || pc_randomizer_purple_campaign() || p2ship::stock.total()!=0)return false;
    const auto* layout=pc_p2_cave_rooms_layout();
    return layout && cave=="forest_2" && layout->cave==cave && layout->seed==seed
        && layout->floor==floor && floorId==floor && floor==1 && checkpointSchema==2
        && token==boundaryToken && !beasts && !tutorialEntry
        && pc_p2_purples_enabled() && pc_p2_whites_enabled();
}
bool pc_p2_cave_is_beasts(){return beasts;}
std::string pc_p2_cave_boundary_token(){return token;}
std::string pc_p2_cave_receipt_prefix(){return floorId?"floor"+std::to_string(floorId)+":":"";}
// Non-aborting entry-header validator (external linkage for the fixture;
// defined at file scope outside the anonymous namespace). C stdio only
// (no iostream sentries) so the engine-free --check-entry diagnostic cannot
// fault on runtime init. Same mapping + header rules as pc_p2_cave_setup
// (shared profile, tutorial2 extension incl. floor 9, health/count/trailing
// checks) without touching engine state and never aborting.
bool pc_p2_tutorial2_entry_check(const char* path, int* floorOut){
    if(!path || !path[0])return false;
    FILE* fh=std::fopen(path,"rb");
    if(!fh)return false;
    char version[64]={0},token[256]={0},extra[256]={0};
    int floor=0,count=0;float health=0;
    int ok=std::fscanf(fh,"%63s %255s %d %f %d",version,token,&floor,&health,&count)==5;
    if(ok){
        std::string vs(version),tk(token);
        P2CaveEntryProfile profile=p2_cave_entry_profile(vs,floor,tk);
        if(profile==P2CaveEntryProfile::Invalid)profile=p2_tutorial2_entry_profile(vs,floor,tk);
        ok=(profile!=P2CaveEntryProfile::Invalid && health>0 && health<=1 && count>=1 && count<=100);
    }
    for(int i=0;ok && i<count;++i){int species=0,maturity=0;
        if(std::fscanf(fh,"%d %d",&species,&maturity)!=2)ok=0;}
    if(ok && std::fscanf(fh,"%255s",extra)==1)ok=0;
    std::fclose(fh);
    if(ok && floorOut)*floorOut=floor;
    return ok!=0;
}
void pc_p2_cave_setup(){
    bodyContextReady=false;bodyContextScene=0;
    resetRouteSpecies();surfaceContextScene=pc_p2_scene_generation();
    surfaceRoute=P2CaveSurfaceRoute{};surfaceRouteLoaded=false;surfaceWfgDestination=false;
    const char* opt=std::getenv("PIKMIN_CAVE_NAV_DIAGNOSTICS");
    navRate.reset(opt && opt[0]==49 && opt[1]==0);navDrawCalls=0;navMarkerLogged=false;
    pc_p2_cave_rooms_shutdown();
    pc_p2_cave_geometry_shutdown();  // lane 45 (#483)
    pc_p2_cave_items_shutdown();  // lane 46 (#484)
    pc_p2_cave_bud_shutdown();  // lane 48 (#486)
    pc_p2_cave_carry_shutdown();  // lane 50 (#488)
    floorId=0;checkpointSchema=1;beasts=false;cargoTerminal=false;token.clear();requested=false;tutorialEntry=false;boundedForestCheckpoint=false;completed=false;titleTimer=0;anchor=P2CaveAnchor{};transitionShape=nullptr;
    // Lane 41 (#480) runtime generator hook: opt-in only, so a normal cave entry
    // is unchanged. Reads a host-written canonical floor table and writes the
    // engine-generated observed layout for lane 40's checker.
    if(const char* table=std::getenv("PIKMIN_CAVE_GENERATOR_TABLE");table && table[0]){
        std::string layoutJson,marker,error;
        if(pc_p2_cave_generate_file(table,8,layoutJson,marker,error)){
            const char* requested=std::getenv("PIKMIN_CAVE_GENERATOR_OUT");
            const std::string path=requested && requested[0]?requested:"p2-cave-generated.json";
            std::ofstream file(path,std::ios::binary|std::ios::trunc);
            if(file){file.write(layoutJson.data(),static_cast<std::streamsize>(layoutJson.size()));file.close();}
            std::printf("%s\n",marker.c_str());
        }else{
            std::printf("P2_CAVE_GEN source=engine FAILED reason=%s\n",error.c_str());
        }
        std::fflush(stdout);
    }
    // Lane 44 (#482) proxy room/unit instantiation: opt-in only, so a normal run
    // is unchanged. Reads the host bridge's P2_CAVE_ROOMS_1 config and draws the
    // proxy floor; the geometry is explicitly labelled proxy.
    pc_p2_cave_rooms_setup();
    // Lane 45 (#483) real unit geometry + electric gate: opt-in only, reads the
    // host bridge's P2_CAVE_GEOMETRY_1 plan and instantiates real converted unit
    // models in place of the proxy squares for choke/leaf/gate nodes.
    pc_p2_cave_geometry_setup();
    // Lane 46 (#484) physical cave-item placement: opt-in only. Validates the
    // host bridge's P2_CAVE_ITEMS_1 config against the live rooms layout and
    // spawns one real Pellet per item. Proxy geometry/model, never a generation PASS.
    if (!pc_randomizer_generated_cave()) pc_p2_cave_items_setup();
    // Lane 48 (#486) real seeded Candypop bud actor: opt-in only, reads the live
    // lane-44 rooms layout so the bud sits at the seeded bud node's segment and
    // the ordinary throw/convert path grants the colour naturally.
    if (!pc_randomizer_generated_cave()) pc_p2_cave_bud_setup();
    // Lane 50 (#488) carry blocking: opt-in only. Reads the host bridge's
    // P2_CAVE_GATES_1 plan and places one hazard volume per blocking door so a
    // non-immune carrier cannot cross a closed electric gate / water pool.
    pc_p2_cave_carry_setup();
    // yakushima4 boot-stall fix (#673): the pre-stage stall was a SILENT return.
    // Emit an explicit fail-closed marker naming the exact blocked precondition so
    // the guarded boot cannot stall without evidence before any stage load.
    const bool roomPreview=pc_pikipelago_room_preview();
    std::printf("P2_CAVE_SETUP_PROBE room_preview=%d\n",int(roomPreview));std::fflush(stdout);
    if(!roomPreview){std::printf("P2_CAVE_SETUP_BLOCK reason=room_preview_unavailable\n");std::fflush(stdout);return;}
    std::ifstream in("p2-cave-entry.txt");
    if(!in){std::printf("P2_CAVE_SETUP_BLOCK reason=entry_file_missing path=p2-cave-entry.txt\n");std::fflush(stdout);return;}
    std::string version,extra;int floor,count;float health;
    if(!(in>>version>>token>>floor>>health>>count))invalid("header");
    const P2CaveEntryProfile profile=p2_cave_entry_profile(version,floor,token);
    const P2CaveEntryProfile admitted=profile==P2CaveEntryProfile::Invalid
        ?p2_tutorial2_entry_profile(version,floor,token):profile;
    beasts=admitted==P2CaveEntryProfile::BeastsFloor2 || admitted==P2CaveEntryProfile::BeastsFloor3 || admitted==P2CaveEntryProfile::BeastsFloor4;
    if(admitted==P2CaveEntryProfile::Invalid || !std::isfinite(health) || health<=0 || health>1 || count<1 || count>100)
        invalid("header");
    tutorialEntry=(profile==P2CaveEntryProfile::Invalid && admitted!=P2CaveEntryProfile::Invalid);
    // Bud setup above validates its checkpoint against the live room layout.
    // A stray bud sidecar cannot identify an otherwise unrelated legacy cave.
    const P2CaveRoomLayout* checkpointLayout=pc_p2_cave_rooms_layout();
    boundedForestCheckpoint=!beasts && !tutorialEntry && (floor==1 || floor==2)
        && checkpointLayout && checkpointLayout->cave=="forest_1"
        && checkpointLayout->floor==floor;
    std::vector<Survivor> squad;
    checkpointSchema=version=="P2_CAVE_ENTRY_3"?3:(version=="P2_CAVE_ENTRY_2"?2:1);
    for(int i=0;i<count;++i){Survivor s;if(!(in>>s.species>>s.maturity) || !p2_schema_supports(checkpointSchema,s.species) || s.maturity<0 || s.maturity>2)invalid("Pikmin");squad.push_back(s);}
    if(in>>extra || !in.eof())invalid("trailing data");
    std::vector<Piki*> spawned;Iterator it(pikiMgr);CI_LOOP(it){Piki* p=static_cast<Piki*>(*it);if(p->isAlive())spawned.push_back(p);}
    if(spawned.size()!=squad.size())invalid("spawn count differs from checkpoint");
    const bool bodyProfile=pc_p2_cave_bud_body_profile();
    if(bodyProfile){
        if(!checkpointLayout || checkpointLayout->cave!="forest_2" || checkpointLayout->floor!=floor
            || floor!=1 || checkpointSchema!=2 || beasts || tutorialEntry || online()
            || !flowCont.mCurrentStage || !flowCont.mCurrentStage->mFileName
            || std::string(flowCont.mCurrentStage->mFileName)!="stages/chal0.ini"
            || pc_randomizer_enabled() || pc_randomizer_purple_campaign() || p2ship::stock.total()!=0
            || !pc_p2_purples_enabled() || !pc_p2_whites_enabled())invalid("WFG body context");
        // This bounded standalone profile does not impersonate campaign stock
        // or first-meeting flags. With empty real ship storage, staying below
        // either source species cap admits both met/unmet WFG branches.
        int purple=0,white=0;
        for(const auto& survivor:squad){purple+=survivor.species==3;white+=survivor.species==4;}
        if(purple>=20 || white>=20)invalid("WFG source species cap");
    }
    for(const auto& survivor:squad){
        if(survivor.species==3 && !pc_p2_purples_enabled())invalid("Purple assets unavailable");
        if(survivor.species==4 && !pc_p2_whites_enabled())invalid("White assets unavailable");
    }
    Navi* n=naviMgr->getNavi();if(!n || C_NAVI_PARM(n,mHealth)<=0)invalid("captain unavailable");
    for(size_t i=0;i<squad.size();++i){
        Piki* p=spawned[i];p->mHappa=squad[i].maturity;
        if(squad[i].species==3 && !pc_p2_purples_enabled())invalid("Purple assets unavailable");
        if(squad[i].species==4 && !pc_p2_whites_enabled())invalid("White assets unavailable");
        if(!pc_p2_set_species(p,squad[i].species))invalid("Pikmin species");
        if(squad[i].species==3)pc_p2_make_purple(p);
        if(squad[i].species==4)pc_p2_make_white(p);
        if(squad[i].species==5)pc_p2_make_bulbmin(p);
        std::printf("P2_CAVE_RESTORE species=%d maturity=%d\n",squad[i].species,squad[i].maturity);
    }
    n->mHealth=C_NAVI_PARM(n,mHealth)*health;
    floorId=floor;
    // Seed-owned items require the validated entry boundary; token is parsed
    // after room setup. Historical standalone setup keeps its original order.
    if (pc_randomizer_generated_cave()) {
        pc_p2_cave_bud_setup();
        pc_p2_cave_items_setup();
    }
    if(!beasts && tutorialEntry){
        // In-band descend-policy proof (#757/#807): emitted from the engine
        // on tutorial-admitted entries only; floors 1-8 descend, floor 9
        // exits terminal.
        std::printf("P2_TUTORIAL2_DESCEND_POLICY floor=%d descend=%d\n",
                    floor,p2_tutorial_descends(floor)?1:0);
        std::fflush(stdout);
    }
    std::ifstream terminal("p2-beasts-cargo-terminal.txt");
    if(terminal){
        if(!p2CargoTerminalOptIn(terminal,beasts,floor,token) || !pc_p2_preview_ready() || !pc_p2_preview_goal() || pc_p2_preview_cargo_count()!=1 || pc_p2_preview_pokos()!=0)
            invalid("pre-receipt cargo terminal opt-in");
        cargoTerminal=true;
        std::printf("P2_BEASTS_CARGO_TERMINAL_READY floor=3 token=%s cargo=1 pokos=0 diagnostic=1\n",token.c_str());
    }
    std::ifstream location("p2-cave-transition.txt");
    if(beasts && floor==2 && !location)invalid("Beasts floor2 requires a hole anchor");
    if(beasts && floor>=3 && location)invalid("Beasts next-floor descent is unavailable");
    // Reuse the hole geometry validator; this does not change source floorId.
    if(location && !p2_cave_read_anchor(location,beasts?1:floor,anchor))invalid("transition anchor");
    if(anchor.enabled)std::printf("P2_CAVE_ANCHOR kind=%s x=%.3f y=%.3f z=%.3f radius=%.3f\n",anchor.kind.c_str(),anchor.x,anchor.y,anchor.z,anchor.radius);
    std::ifstream visual("p2-cave-visual.txt");
    if(visual){
        std::string header,kind,trailing;
        if(!(visual>>header>>kind) || header!="P2_CAVE_VISUAL_1" || !anchor.enabled
                || kind!=anchor.kind || (visual>>trailing) || !visual.eof())invalid("transition visual");
        const std::string path="courses/pikmin2room/cave_"+kind+".mod";
        transitionShape=gameflow.loadShape(path.c_str(),true);
        if(!transitionShape)invalid("missing transition model");
        for(int i=0;i<transitionShape->mTexAttrCount;++i)
            if(transitionShape->mTexAttrList[i].mTexture)transitionShape->mTexAttrList[i].mTexture->attach();
        std::printf("P2_CAVE_VISUAL_READY kind=%s vertices=%d\n",kind.c_str(),transitionShape->mVertexCount);
    }
    std::printf("P2_CAVE_READY floor=%d survivors=%d health=%.9g\n",floor,count,health);std::fflush(stdout);
    if(bodyProfile){
        // GameCoreSection finalSetup advances the scene after preview/cave setup.
        // Bodies arm on their first ordinary tick, never in bootstrap callbacks.
        bodyContextScene=pc_p2_scene_generation()+1;bodyContextReady=true;
    }
    pc_p2_cave_generate_run(); // lane cave-generate-provider (#129): opt-in manifest sidecar only; reviewed hook, pending #186
    if(beasts && floor>=3){std::printf("P2_BEASTS_ENTRY_READY floor=%d token=%s descent=disabled\n",floor,token.c_str());std::fflush(stdout);}
}
void pc_p2_cave_request(){if(!online() && ((surfaceRouteLoaded && !completed) || (active() && !(beasts && floorId>=3))))requested=true;}
bool pc_p2_cave_interact(float x,float y,float z){
    if(beasts && floorId>=3)return false;
    if(!safeTime() || !anchor.contains(x,y,z))return false;
    Navi* n=naviMgr->getNavi();
    if(!anchor.contains(n->mSRT.t.x,n->mSRT.t.y,n->mSRT.t.z)
        || n->getCurrState()->getID()!=NAVISTATE_Walk)return false;
    requested=true;return true;
}
bool pc_p2_cave_checkpoint(bool confirm){
    if(beasts && floorId==4)return false; // Both terminal persistence and floor5 descent are unavailable.
    if(!safeTime())return false;
    if(beasts && floorId==3){
        bool livingPikmin=false,livingSprouts=false;
        Iterator pikis(pikiMgr);CI_LOOP(pikis){if(static_cast<Piki*>(*pikis)->isAlive())livingPikmin=true;}
        Iterator heads(itemMgr->getPikiHeadMgr());CI_LOOP(heads){if(static_cast<PikiHeadItem*>(*heads)->isAlive())livingSprouts=true;}
        const char* reason=p2_beasts_failure_reason(beasts,floorId,naviMgr->getNavi()->mHealth,livingPikmin,livingSprouts);
        if(!reason)return false; // Successful floor4 descent remains unavailable.
        const std::string text="P2_BEASTS_FAILURE_1\n"+token+"\n3 0 0 0\n"+reason+"\n";
        if(!writeTransfer(text)){if(confirm)notice("Could not record the terminal checkpoint. The supervisor has not accepted this failure.");return false;}
        completed=true;
        std::printf("P2_BEASTS_FAILURE floor=3 destination=0 reason=%s survivors=0 health=0\n",reason);std::fflush(stdout);
        return true;
    }
    Navi* n=naviMgr->getNavi();std::vector<Piki*> alive;
    bool busy=pc_p2_cave_bud_pending();
    Iterator it(pikiMgr);CI_LOOP(it){
        Piki* p=static_cast<Piki*>(*it);if(!p->isAlive())continue;
        const int state=p->getState();
        if(state==PIKISTATE_Dying || state==PIKISTATE_Dead) {busy=true;continue;}
        // Do not preserve an actor half-swallowed, converting or becoming a sprout.
        if(state==PIKISTATE_Swallowed || state==PIKISTATE_Bury || state==PIKISTATE_Grow
            || (p->getStickObject() && p->getStickObject()->mObjType!=OBJTYPE_Pellet))busy=true;
        const int species=pc_p2_species(p);
        if(species<0 || !p2_cave_bounded_live_species_supported(checkpointSchema,species,
                boundedForestCheckpoint,pc_p2_whites_enabled()))invalid("runtime Pikmin species");
        alive.push_back(p);
    }
    Iterator heads(itemMgr->getPikiHeadMgr());CI_LOOP(heads){if(static_cast<PikiHeadItem*>(*heads)->isAlive())busy=true;}
    if(busy && n->mHealth>1){if(confirm)notice("Pluck all sprouts and whistle Pikmin out of flowers or combat before leaving.");return false;}
    float health=C_NAVI_PARM(n,mHealth)>0?n->mHealth/C_NAVI_PARM(n,mHealth):0;
    health=std::fmax(0.f,std::fmin(1.f,health));
    if(n->mHealth<=1){health=0;alive.clear();}
    const bool failed=alive.empty();
    Suckable* pod=pc_p2_preview_goal();
    if(!pod)return false;
    float dx=n->mSRT.t.x-pod->mSRT.t.x,dz=n->mSRT.t.z-pod->mSRT.t.z;
    const bool nearExit=anchor.enabled?anchor.contains(n->mSRT.t.x,n->mSRT.t.y,n->mSRT.t.z):dx*dx+dz*dz<=150.f*150.f;
    if(!failed && (!nearExit || n->getCurrState()->getID()!=NAVISTATE_Walk)){
        if(confirm)notice(anchor.enabled?"Stand at the hole/geyser to descend or leave the cave.":"Return to the Research Pod to descend or leave the cave.");return false;
    }
    if(confirm && !failed){
        const char* action=(beasts || (!bodyContextReady && !tutorialEntry && floorId==1) || (tutorialEntry && p2_tutorial_descends(floorId)))?"Descend":"Leave cave";
        std::string message=std::string(action)+" with all "+std::to_string(alive.size())+" surviving Pikmin?\n"
            "Uncollected treasure stays behind. Your squad and delivered treasure will be saved together.";
        const SDL_MessageBoxButtonData buttons[]={{SDL_MESSAGEBOX_BUTTON_ESCAPEKEY_DEFAULT,0,"Stay"},{SDL_MESSAGEBOX_BUTTON_RETURNKEY_DEFAULT,1,action}};
        SDL_MessageBoxData data={SDL_MESSAGEBOX_INFORMATION,SDL_GL_GetCurrentWindow(),caveName(),message.c_str(),2,buttons,nullptr};int choice=0;
        const char* dialogAction=std::string(action)=="Descend"?"descend":"leave";
        const auto* dialogLayout=pc_p2_cave_rooms_layout();
        const unsigned long dialogSequence=dialogEvidenceBefore(data,"floor",dialogAction,token,
            dialogLayout?dialogLayout->cave.c_str():caveName(),floorId);
        const int dialogResult=SDL_ShowMessageBox(&data,&choice);
        dialogEvidenceAfter(dialogSequence,data,"floor",dialogAction,token,
            dialogLayout?dialogLayout->cave.c_str():caveName(),floorId,dialogResult,choice);
        if(dialogResult!=0 || choice!=1)return false;
    }
    // Apply the source cave save filter (pikiMgr::caveSaveAllPikmins, pikiMgr.cpp
    // :723) and build the persisted squad. Wild Bulbmin dependents are dropped on
    // a descent; every tracked Bulbmin is dropped on a cave exit. The drop set is
    // computed non-mutatingly so a failed write can retry without leaking bodies;
    // the ledger is committed only after the transfer file is written.
    const bool exiting=!beasts && !p2_tutorial_descends(floorId);
    const P2BulbminCaveTransition move=exiting?P2BulbminExitCave:P2BulbminDescendFloor;
    // Leader-down (alive cleared) saves an empty squad; do not touch the Bulbmin ledger then.
    const std::vector<Piki*> dropped=alive.empty()?std::vector<Piki*>{}:pc_p2_bulbmin_transition_removes(move);
    std::vector<Survivor> squad;
    squad.reserve(alive.size());
    for(Piki* p:alive){
        bool isDropped=false;
        for(Piki* d:dropped){if(d==p){isDropped=true;break;}}
        if(!isDropped) squad.push_back({pc_p2_species(p),p->mHappa});
    }
    int writeSchema=checkpointSchema;
    for(const auto& s:squad){const int required=p2_schema_required_for_species(s.species);if(required>writeSchema)writeSchema=required;}
    std::ostringstream out;out.precision(9);
    if(beasts)out<<"P2_BEASTS_TRANSFER_1\n"<<token<<"\n2 3 "<<health<<' '<<squad.size()<<'\n';
    else out<<"P2_CAVE_TRANSFER_"<<writeSchema<<'\n'<<token<<'\n'<<floorId<<' '<<health<<' '<<squad.size()<<'\n';
    for(const auto& s:squad)out<<s.species<<' '<<s.maturity<<'\n';
    if(!pc_p2_cave_bud_save("p2-cave-bud-transfer.txt"))return false;
    if(!writeTransfer(out.str())){if(confirm)notice("Could not prepare the checkpoint. Stay on this floor and retry.");return false;}
    // Commit the ledger mutation only now that the transfer file is durable, so a
    // retry after a failed write still tracks every removed dependent.
    if(!dropped.empty()) pc_p2_bulbmin_transition(move);
    if(!alive.empty()) std::printf("P2_CAVE_BULBMIN_TRANSITION move=%s removed=%zu kept=%zu exiting=%d\n",
                exiting?"exit":"descend",dropped.size(),squad.size(),int(exiting));
    completed=true;
    std::printf("P2_CAVE_TRANSFER floor=%d survivors=%zu health=%.9g failed=%d\n",floorId,squad.size(),health,int(squad.empty()));std::fflush(stdout);
    return true;
}
bool pc_p2_cave_exit_after_checkpoint(){
    if(!completed)return false;
    std::fflush(nullptr);std::_Exit(42);
}
void pc_p2_cave_tick(){
    loadSurfaceRoute();
    if(surfaceRouteLoaded){
        const bool attempt=requested;requested=false;
        if(attempt)enterSurfaceCave();
        return;
    }
    pc_p2_cave_carry_tick();  // lane 50 (#488) carry blocking at hazards
    pc_p2_cave_geometry_tick();  // lane 45 (#483) live electric-gate actor
    pc_p2_cave_bud_tick();  // lane 48 (#486) ordinary bud conversion path
    navigationDiagnostic();
    if(!safeTime()){requested=false;return;}
    gameflow.mWorldClock.setTime(gameflow.mParameters->mStartHour());
    bool attempt=requested;requested=false;
    // Extinction/knockout must not silently restore a fresh squad on the next launch.
    bool any=false;Iterator it(pikiMgr);CI_LOOP(it){if(static_cast<Piki*>(*it)->isAlive()){any=true;break;}}
    Iterator heads(itemMgr->getPikiHeadMgr());CI_LOOP(heads){if(static_cast<PikiHeadItem*>(*heads)->isAlive()){any=true;break;}}
    if(!any || naviMgr->getNavi()->mHealth<=1)attempt=true;
    // The supervisor owns the next process and the atomic campaign commit.
    // Exit after closing the transfer file; do not run P1 day-end/save teardown.
    if(attempt && pc_p2_cave_checkpoint(true))pc_p2_cave_exit_after_checkpoint();
    titleTimer+=gsys->getFrameTime();
    if(titleTimer>=1.f){
        titleTimer=0;
        int count=0,purples=0,whites=0;Iterator squad(pikiMgr);CI_LOOP(squad){Piki* p=static_cast<Piki*>(*squad);if(p->isAlive()){++count;if(pc_p2_is_purple(p))++purples;if(pc_p2_is_white(p))++whites;}}
        const std::string transition=beasts && floorId>=3?" | Floor "+std::to_string(floorId+1)+" descent unavailable":
            " | F6 at "+(anchor.enabled?anchor.kind:std::string("Pod"))+": "+((beasts || (!bodyContextReady && !tutorialEntry && floorId==1) || (tutorialEntry && p2_tutorial_descends(floorId)))?"descend":"leave cave")+" | Saves at floor boundaries";
        std::string title=std::string("Pikipelago - ")+caveName()+" | Floor "+std::to_string(floorId)+" | "+std::to_string(count)+" Pikmin ("+std::to_string(purples)+" Purple, "+std::to_string(whites)+" White) | "+std::to_string(pc_p2_preview_pokos())+" Pokos"+transition;
        if(SDL_Window* w=SDL_GL_GetCurrentWindow())SDL_SetWindowTitle(w,title.c_str());
    }
}

void pc_p2_cave_draw_transition(Graphics& gfx){
    if(gfx.mCamera && pc_p2_cave_rooms_active())pc_p2_cave_rooms_draw(gfx);
    if(gfx.mCamera && pc_p2_cave_geometry_active())pc_p2_cave_geometry_draw(gfx);  // lane 45 (#483)
    // Keep room geometry; the legacy solid anchor model covers the authored mouth.
    if(pc_p2_cave_visible_active())return;
    if((!active() && !surfaceRouteLoaded) || !anchor.enabled || !gfx.mCamera)return;
    if(navRate.enabled)++navDrawCalls;
    if(!navMarkerLogged){std::puts("P2_CAVE_MARKER_DRAW");navMarkerLogged=true;}
    // Map post-effects may leave an orthographic projection/material active.
    gfx.setPerspective(gfx.mCamera->mPerspectiveMatrix.mMtx,gfx.mCamera->mFov,
        gfx.mCamera->mAspectRatio,gfx.mCamera->mNear,gfx.mCamera->mFar,1.f);
    gfx.useMaterial(nullptr);
    gfx.setDepth(true);
    if(transitionShape){
        Matrix4f world,view;
        world.makeSRT(Vector3f(1,1,1),Vector3f(0,0,0),Vector3f(anchor.x,anchor.y,anchor.z));
        gfx.mCamera->mLookAtMtx.multiplyTo(world,view);
        transitionShape->updateAnim(gfx,view,nullptr,nullptr);
        transitionShape->drawshape(gfx,*gfx.mCamera,nullptr);
        return;
    }
    // Honest engineering marker, not an imported P2 actor. Ring + down/up arrow.
    // The caller is a world-overlay boundary and resets the matrix for subsequent UI.
    const Colour oldColour=gfx.mPrimaryColour;
    const Colour oldAux=gfx.mAuxiliaryColour;
    const int oldBlend=gfx.setCBlending(BLEND_Alpha);
    Texture* oldTexture=gfx.mActiveTexture[0];
    const bool oldLight=gfx.setLighting(false,nullptr);
    const float oldWidth=gfx.setLineWidth(3.f);
    gfx.useTexture(nullptr,0);gfx.useMatrix(gfx.mCamera->mLookAtMtx,0);
    gfx.setColour(anchor.kind=="hole"?Colour(255,185,65,255):Colour(75,235,255,255),true);
    const float y=anchor.y+4.f;
    for(int i=0;i<32;++i){
        const float a=i*6.28318530718f/32.f,b=(i+1)*6.28318530718f/32.f;
        gfx.drawLine(Vector3f(anchor.x+std::cos(a)*anchor.radius,y,anchor.z+std::sin(a)*anchor.radius),
                     Vector3f(anchor.x+std::cos(b)*anchor.radius,y,anchor.z+std::sin(b)*anchor.radius));
    }
    const float tip=anchor.kind=="hole"?y+8.f:y+75.f;
    const float tail=anchor.kind=="hole"?y+75.f:y+8.f;
    const float wing=anchor.kind=="hole"?tip+20.f:tip-20.f;
    gfx.drawLine(Vector3f(anchor.x,tail,anchor.z),Vector3f(anchor.x,tip,anchor.z));
    gfx.drawLine(Vector3f(anchor.x-18.f,wing,anchor.z),Vector3f(anchor.x,tip,anchor.z));
    gfx.drawLine(Vector3f(anchor.x+18.f,wing,anchor.z),Vector3f(anchor.x,tip,anchor.z));
    gfx.setLineWidth(oldWidth);gfx.setColour(oldColour,true);gfx.mAuxiliaryColour=oldAux;
    gfx.setCBlending(oldBlend);gfx.useTexture(oldTexture,0);gfx.setLighting(oldLight,nullptr);
}


// ---- Authored yakushima_4 floor-1 room graph (#682) ----
//
// Decoded from user/Mukki/mapunits/caveinfo/yakushima_4.txt floor 1
// (f008 2_units_gw_l_conc.txt) and
// user/Mukki/mapunits/units/2_units_gw_l_conc.txt, both read from the local
// US GPVE01 disc via experimental.pikmin2_assets.disc_files.
//   caveinfo sha256 3e3fc04e1131673e22063eb2e395e22e7ac3d4252d2db9223400632696272de0
//   units    sha256 742624fd2cae25ad6a3bab04a5d4440e721875f25a2185809324a59c25fc867e
// 8 rooms / 19 doors / 36 door links, baked verbatim from the decode.
// Higher floors, triangle-mesh collision and regrowth schedules are
// explicitly OPEN (not decoded here); coverage is room/door/link topology
// plus route reachability (see the lane harness, which re-decodes the real
// files and diffs the emitted table).
struct P2Yakushima4Room { const char *name; int cells[2]; int kind; int doors; };
struct P2Yakushima4Link {
    int room;
    int door;
    int waypoint;
    int peer;
    int distMilli;
    int enemyFlag;
};
static const P2Yakushima4Room kYakushima4Rooms[] = {
    {"item_cap_conc", 1, 1, 0, 1},
    {"way3_conc", 1, 1, 2, 3},
    {"way4_conc", 1, 1, 2, 4},
    {"wayl_conc", 1, 1, 2, 2},
    {"way2_conc", 1, 1, 2, 2},
    {"way2x2_conc", 1, 2, 2, 2},
    {"room_4x4g_water_4_conc", 4, 4, 1, 4},
    {"room_north4x4l_1_conc", 4, 4, 1, 1},
};
static const P2Yakushima4Link kYakushima4Links[] = {
    {1, 0, 0, 1, 170005, 1},
    {1, 0, 0, 2, 170005, 1},
    {1, 1, 1, 0, 170005, 1},
    {1, 1, 1, 2, 170005, 1},
    {1, 2, 2, 0, 170005, 1},
    {1, 2, 2, 1, 170005, 1},
    {2, 0, 0, 1, 170005, 1},
    {2, 0, 0, 2, 170005, 1},
    {2, 0, 0, 3, 170005, 1},
    {2, 1, 1, 0, 170005, 1},
    {2, 1, 1, 2, 170005, 1},
    {2, 1, 1, 3, 170005, 1},
    {2, 2, 2, 0, 170005, 1},
    {2, 2, 2, 1, 170005, 1},
    {2, 2, 2, 3, 170005, 1},
    {2, 3, 3, 0, 170005, 1},
    {2, 3, 3, 1, 170005, 1},
    {2, 3, 3, 2, 170005, 1},
    {3, 0, 0, 1, 136007, 1},
    {3, 1, 1, 0, 136007, 1},
    {4, 0, 0, 1, 170005, 1},
    {4, 1, 1, 0, 170005, 1},
    {5, 0, 0, 1, 340009, 1},
    {5, 1, 1, 0, 340009, 1},
    {6, 0, 0, 1, 850046, 1},
    {6, 0, 0, 2, 997832, 1},
    {6, 0, 0, 3, 680015, 1},
    {6, 1, 1, 0, 850046, 1},
    {6, 1, 1, 2, 707838, 1},
    {6, 1, 1, 3, 1020044, 1},
    {6, 2, 2, 0, 997832, 1},
    {6, 2, 2, 1, 707838, 1},
    {6, 2, 2, 3, 827848, 1},
    {6, 3, 3, 0, 680015, 1},
    {6, 3, 3, 1, 1020044, 1},
    {6, 3, 3, 2, 827848, 1},
};
static const int kYakushima4RoomCount = 8;
static const int kYakushima4DoorCount = 19;
static const int kYakushima4LinkCount = 36;

int pc_p2_yakushima4_room_count() { return kYakushima4RoomCount; }

bool pc_p2_yakushima4_validate()
{
    int doors = 0;
    for (int r = 0; r < kYakushima4RoomCount; ++r) {
        if (!kYakushima4Rooms[r].name || kYakushima4Rooms[r].doors < 0) return false;
        doors += kYakushima4Rooms[r].doors;
    }
    if (doors != kYakushima4DoorCount) return false;
    int links = 0;
    for (int i = 0; i < kYakushima4LinkCount; ++i) {
        const P2Yakushima4Link &link = kYakushima4Links[i];
        if (link.room < 0 || link.room >= kYakushima4RoomCount) return false;
        if (link.door < 0 || link.door >= kYakushima4Rooms[link.room].doors) return false;
        if (link.peer < 0 || link.peer >= kYakushima4Rooms[link.room].doors) return false;
        if (link.door == link.peer || link.distMilli <= 0) return false;
        bool symmetric = false;
        for (int j = 0; j < kYakushima4LinkCount; ++j) {
            const P2Yakushima4Link &back = kYakushima4Links[j];
            if (back.room == link.room && back.door == link.peer && back.peer == link.door) {
                symmetric = true;
                break;
            }
        }
        if (!symmetric) return false;
        ++links;
    }
    return links == kYakushima4LinkCount;
}

int pc_p2_yakushima4_emit_nav()
{
    if (!pc_p2_yakushima4_validate()) {
        std::printf("P2_YAKUSHIMA4_AUTHORED valid=0\n");
        std::fflush(stdout);
        return -1;
    }
    for (int i = 0; i < kYakushima4LinkCount; ++i) {
        const P2Yakushima4Link &link = kYakushima4Links[i];
        std::printf("P2_CAVE_NAV authored=1 room=%d door=%d waypoint=%d peer=%d dist_mm=%d enemy_flag=%d\n",
                    link.room, link.door, link.waypoint, link.peer, link.distMilli, link.enemyFlag);
    }
    std::printf("P2_YAKUSHIMA4_AUTHORED valid=1 rooms=%d doors=%d links=%d\n",
                kYakushima4RoomCount, kYakushima4DoorCount, kYakushima4LinkCount);
    std::fflush(stdout);
    return kYakushima4LinkCount;
}
