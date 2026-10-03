#pragma once
// Engine-free double for the Sarai campaign bridge test: actor roster walk.
#include "Generator.h"
#include <cstddef>
#include <vector>

class Creature {
public:
    Generator* mGenerator = nullptr;
};
class BTeki : public Creature {};

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
