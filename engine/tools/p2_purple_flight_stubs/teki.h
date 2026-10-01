#pragma once
#include "Piki.h"
#include <vector>
class BTeki {
public:
    bool alive=true,organic=true;float mCollisionRadius=0;SRT mSRT;
    bool isAlive()const{return alive;} bool isOrganic()const{return organic;}
};
struct TekiMgr { std::vector<BTeki*> actors; };
extern TekiMgr* tekiMgr;
class Iterator {
    TekiMgr* mgr;size_t index=0;
public:
    explicit Iterator(TekiMgr* value):mgr(value){} void first(){index=0;} bool isDone()const{return !mgr||index>=mgr->actors.size();}
    void next(){++index;} BTeki* operator*()const{return mgr->actors[index];}
};
#define CI_LOOP(iterator) for((iterator).first();!(iterator).isDone();(iterator).next())
