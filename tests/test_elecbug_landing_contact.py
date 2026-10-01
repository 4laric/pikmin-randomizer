"""Compile the actual family probe with controlled engine collision responses.

Set PIKMIN_NATIVE_SOURCE to the exact native checkout under test and CXX to g++.
This tests dispatch/guards, not engine geometry or natural throw acceptance.
"""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


def extract_probe(source):
    start = source.index("void pc_p2_elecbug_check_landing_press(BTeki* actor)")
    brace = source.index("{", start)
    depth = 1
    end = brace + 1
    while depth:
        depth += (source[end] == "{") - (source[end] == "}")
        end += 1
    return source[start:end]


STUBS = r'''
#include <cassert>
#include <cmath>
#include <cstdio>
#include <vector>
struct Vector3f { float x=0,y=0,z=0; };
struct Piki {
    Vector3f pos, mVelocity;
    bool alive=true, collides=false;
    int species=0;
    bool isAlive() const { return alive; }
    Vector3f getPosition() const { return pos; }
};
struct CollInfo {
    bool available=true;
    int queries=0;
    bool hasInfo() const { return available; }
    void* checkCollision(Piki* p, Vector3f& push) {
        ++queries;
        push={999,999,999}; // query result must never move the Pikmin
        return p->collides ? this : nullptr;
    }
};
struct BTeki {
    CollInfo* mCollInfo;
    Vector3f getPosition() const { return {}; }
};
enum { ELEC_WAIT, ELEC_CHARGE, ELEC_DISCHARGE, ELEC_CHILDCHARGE,
       ELEC_CHILDDISCHARGE, ELEC_DEAD, ELEC_REVERSE, ELEC_RETURN };
struct ElecBug { int state=ELEC_WAIT; } bug;
std::vector<Piki*> squad;
std::vector<Piki*>* pikiMgr=&squad;
bool ready=true, registered=true;
ElecBug* lookup(BTeki*) { return registered ? &bug : nullptr; }
struct Iterator {
    std::vector<Piki*>* values; size_t index=0;
    explicit Iterator(std::vector<Piki*>* v):values(v){}
    Piki* operator*() { return values->at(index); }
};
#define CI_LOOP(it) for ((it).index=0; (it).index<(it).values->size(); ++(it).index)
float distXZ(Vector3f a,Vector3f b) { return std::hypot(a.x-b.x,a.z-b.z); }
unsigned genOf(BTeki*) { return 1; }
int pc_p2_species(Piki* p) { return p->species; }
const char* stateName(int) { return "test"; }
int presses=0;
Piki* pressed=nullptr;
void pc_p2_elecbug_pressed(BTeki*,Piki* p) { ++presses; pressed=p; bug.state=ELEC_REVERSE; }
'''

SCENARIOS = r'''
int main() {
    CollInfo collision;
    BTeki actor{&collision};
    Piki p;
    squad={&p};
    // Same XZ, descending but no collision: old code flips at any height.
    for (float height : {500.f,-500.f,30.f,0.f}) {
        p.pos={0,height,0}; p.mVelocity.y=-100; p.collides=false;
        bug.state=ELEC_WAIT; presses=0;
        pc_p2_elecbug_check_landing_press(&actor);
        assert(presses==0);
    }
    // Contact is necessary but not sufficient: ascent/grounded/dead excluded.
    p.pos={0,12,0}; p.collides=true;
    for (float velocity : {100.f,0.f,-0.001f}) {
        p.mVelocity.y=velocity; presses=0;
        pc_p2_elecbug_check_landing_press(&actor); assert(presses==0);
    }
    p.mVelocity.y=-100; p.alive=false;
    pc_p2_elecbug_check_landing_press(&actor); assert(presses==0);
    p.alive=true;
    for (int state : {ELEC_DEAD,ELEC_REVERSE,ELEC_RETURN}) {
        bug.state=state;
        pc_p2_elecbug_check_landing_press(&actor); assert(presses==0);
    }
    bug.state=ELEC_WAIT;
    actor.mCollInfo=nullptr;
    pc_p2_elecbug_check_landing_press(&actor); assert(presses==0);
    actor.mCollInfo=&collision; collision.available=false;
    pc_p2_elecbug_check_landing_press(&actor); assert(presses==0);
    collision.available=true;
    // Every color, including Purple, shares the contact gate.
    for (int color=0;color<6;++color) {
        p.species=color; bug.state=ELEC_WAIT; presses=0;
        pc_p2_elecbug_check_landing_press(&actor);
        assert(presses==1 && pressed==&p && bug.state==ELEC_REVERSE);
        assert(p.pos.x==0 && p.pos.y==12 && p.pos.z==0);
        pc_p2_elecbug_check_landing_press(&actor); assert(presses==1);
    }
    // A non-contact candidate must not mask a later contacting candidate.
    Piki missed=p; missed.collides=false; missed.pos.y=500;
    squad={nullptr,&missed,&p}; presses=0; bug.state=ELEC_DISCHARGE;
    pc_p2_elecbug_check_landing_press(&actor);
    assert(presses==1 && pressed==&p);
    registered=false; presses=0; bug.state=ELEC_WAIT;
    pc_p2_elecbug_check_landing_press(&actor); assert(presses==0);
    registered=true; ready=false;
    pc_p2_elecbug_check_landing_press(&actor); assert(presses==0);
    std::puts("PASS: production ElecBug landing contact dispatch and guards");
}
'''


class LandingContactTest(unittest.TestCase):
    @unittest.skipUnless(os.environ.get("PIKMIN_NATIVE_SOURCE"),
                         "explicit native checkout required for source-pin regression")
    def test_actual_production_probe(self):
        native = Path(os.environ["PIKMIN_NATIVE_SOURCE"])
        compiler = os.environ.get("CXX") or shutil.which("g++")
        self.assertTrue(compiler, "CXX/g++ required")
        source = (native / "pc_port/pc_p2_elecbug.cpp").read_text()
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            cpp = directory / "probe.cpp"
            exe = directory / ("probe.exe" if os.name == "nt" else "probe")
            cpp.write_text(STUBS + extract_probe(source) + SCENARIOS)
            subprocess.run([compiler, "-std=c++17", "-UNDEBUG", str(cpp), "-o", str(exe)], check=True)
            subprocess.run([str(exe)], check=True)


if __name__ == "__main__":
    unittest.main()
