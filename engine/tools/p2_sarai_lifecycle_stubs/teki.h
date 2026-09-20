#pragma once
// Engine-free double for the Sarai lifecycle test: actor roster walk plus the
// damage/lifetime anchor surface pc_p2_sarai_manager.cpp touches (type,
// health, transform, aliveness, position). PelletView is the delivery-seam
// base so the manager's static_casts compile exactly as in production.
#include "Generator.h"
#include "Vector.h"
#include <cstddef>
#include <vector>

struct PelletView {
    virtual ~PelletView() = default;
};

class BTeki : public PelletView {
public:
    Generator* mGenerator = nullptr;
    int mTekiType = 0;
    float mHealth = 0.0f;
    SRT mSRT;
    bool alive = true;
    bool isAlive() const { return alive; }
    Vector3f getPosition() const { return mSRT.t; }
};

struct TekiMgr {
    std::vector<BTeki*> actors;
};
extern TekiMgr* tekiMgr;

class Iterator {
    TekiMgr* mgr;
    std::size_t index = 0;
public:
    explicit Iterator(TekiMgr* value) : mgr(value) {}
    void first() { index = 0; }
    bool isDone() const { return !mgr || index >= mgr->actors.size(); }
    void next() { ++index; }
    BTeki* operator*() const { return mgr->actors[index]; }
};
#define CI_LOOP(iterator) for ((iterator).first(); !(iterator).isDone(); (iterator).next())
