"""Prepare isolated opt-in cave navigation diagnostics; never edits native source."""
import argparse
import difflib
import hashlib
import json
from pathlib import Path

HEADER=r'''#pragma once
#include <cstdint>
struct P2CaveNavRate {
    bool enabled=false;
    unsigned count=0;
    std::uint32_t last=0;
    void reset(bool on){enabled=on;count=0;last=0;}
    bool due(std::uint32_t now){
        if(!enabled || count>=120 || (count && std::uint32_t(now-last)<2000))return false;
        last=now;++count;return true;
    }
};
'''

TICK=r'''
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
'''


def instrument(source):
    changes=[('#include "pc_p2_cave.h"','#include "pc_p2_cave.h"\n#include "pc_p2_cave_nav_diagnostics.h"'),
      ('Shape* transitionShape=nullptr;','Shape* transitionShape=nullptr;\nP2CaveNavRate navRate;\nunsigned navDrawCalls=0;\nbool navMarkerLogged=false;'),
      ('void notice(const char* text)',TICK+'\nvoid notice(const char* text)'),
      ('void pc_p2_cave_setup(){','void pc_p2_cave_setup(){\n    const char* opt=std::getenv("PIKMIN_CAVE_NAV_DIAGNOSTICS");\n    navRate.reset(opt && opt[0]==49 && opt[1]==0);navDrawCalls=0;navMarkerLogged=false;'),
      ('void pc_p2_cave_tick(){','void pc_p2_cave_tick(){\n    navigationDiagnostic();'),
      ('    static bool logged=false;\n    if(!logged){std::puts("P2_CAVE_MARKER_DRAW");logged=true;}','    if(navRate.enabled)++navDrawCalls;\n    if(!navMarkerLogged){std::puts("P2_CAVE_MARKER_DRAW");navMarkerLogged=true;}')]
    if 'PIKMIN_CAVE_NAV_DIAGNOSTICS' in source:raise ValueError('Already instrumented')
    for old,new in changes:
        if source.count(old)!=1:raise ValueError('Unexpected cave source anchor: '+old)
        source=source.replace(old,new)
    return source


def prepare(source,output):
    raw=source.read_bytes();text=raw.decode('utf-8');result=instrument(text)
    output.mkdir(parents=True,exist_ok=False)
    (output/'pc_p2_cave.cpp').write_text(result,encoding='utf-8');(output/'pc_p2_cave_nav_diagnostics.h').write_text(HEADER)
    diff=''.join(difflib.unified_diff(text.splitlines(True),result.splitlines(True),fromfile='a/pc_port/pc_p2_cave.cpp',tofile='b/pc_port/pc_p2_cave.cpp'))
    diff+=''.join(difflib.unified_diff([],HEADER.splitlines(True),fromfile='/dev/null',tofile='b/pc_port/pc_p2_cave_nav_diagnostics.h'))
    (output/'navigation.patch').write_text(diff,encoding='utf-8');(output/'provenance.json').write_text(json.dumps(dict(source=str(source.resolve()),sha256=hashlib.sha256(raw).hexdigest(),scope='isolated patch only',enabled_by='PIKMIN_CAVE_NAV_DIAGNOSTICS=1',limit='at most120rows per stage, minimum2seconds interval'),indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();prepare(a.source,a.output)
