#ifdef NDEBUG
#undef NDEBUG
#endif
#include "pc_p2_captain.h"
#include "pc_p2_captain_switch_policy.h"
#include <cassert>
#include <cstdio>
#include <vector>

struct Actor { unsigned id; int owner; };
struct Scene {
    float health[2] = {100,100};
    std::vector<Actor*> actors;
    int writes = 0;
    bool badEnumeration = false;
};
static void* captain(void* c,int n) { return &static_cast<Scene*>(c)->health[n]; }
static float health(void*,void* p) { return *static_cast<float*>(p); }
static void setHealth(void*,void* p,float v) { *static_cast<float*>(p)=v; }
static unsigned identity(void*,void* p) { return static_cast<Actor*>(p)->id; }
static int owner(void*,void* p) { return static_cast<Actor*>(p)->owner; }
static void setOwner(void* c,void* p,int v) { ++static_cast<Scene*>(c)->writes; static_cast<Actor*>(p)->owner=v; }
static bool prepare(void*,void*) { return true; }
static int enumerate(void* c,void** out,int cap) {
    auto& s=*static_cast<Scene*>(c);
    if(s.badEnumeration) return cap+1;
    int n=0; for(auto* actor:s.actors) { if(n==cap) break; out[n++]=actor; } return n;
}
static P2CaptainHostOps ops(Scene& s) {
    P2CaptainHostOps o; o.context=&s; o.captainAt=captain; o.getHealth=health;
    o.setHealth=setHealth; o.actorId=identity; o.ownerSlot=owner;
    o.setOwnerSlot=setOwner; o.prepareCapture=prepare; o.enumerate=enumerate; return o;
}
int main() {
    assert(p2_captain_needs_survivor_takeover(1.0f));
    assert(p2_captain_needs_survivor_takeover(-400.0f));
    assert(!p2_captain_needs_survivor_takeover(1.001f));
    assert(!p2_captain_needs_survivor_takeover(NAN));
    assert(!p2_captain_needs_survivor_takeover(INFINITY));
    // A late birth and a changed whistle owner must be read before a capture.
    {
        Actor a{1,0}, late{2,1}, unrelated{3,-1}; Scene s; s.actors={&a};
        P2CaptainAdapter p; assert(p.bind(ops(s)) && p.setup());
        a.owner=1; s.actors={&a,&late,&unrelated};
        assert(p.captureCaptain(1,77));
        assert(a.owner==0 && late.owner==0 && unrelated.owner==-1);
        assert(p.ownerOfActor(1)==0 && p.ownerOfActor(2)==0);
    }
    // Intentional knockout releases remain visible, including new actors.
    {
        Actor a{1,0}, late{2,0}, other{3,1}; Scene s; s.actors={&a};
        P2CaptainAdapter p; assert(p.bind(ops(s)) && p.setup());
        s.actors={&a,&late,&other}; assert(p.damageCaptain(0,100));
        assert(a.owner==-1 && late.owner==-1 && other.owner==1);
    }
    // A captor's epoch wins over conflicting live ownership until release.
    {
        Actor a{1,0}, b{2,1}; Scene s; s.actors={&a,&b};
        P2CaptainAdapter p; assert(p.bind(ops(s)) && p.setup());
        assert(p.captureActor(88,&a)); a.owner=1;
        assert(p.captureCaptain(1,99)); assert(a.owner==1 && p.isCaptiveFor(88,&a));
        assert(!p.releaseActor(87,&a,0)); assert(p.releaseActor(88,&a,0));
        assert(a.owner==0 && !p.isCaptiveFor(88,&a));
    }
    // Sync must not rewrite actors first encountered after the policy mutation.
    {
        Actor a{1,0}, late{2,1}; Scene s; s.actors={&a};
        P2CaptainAdapter p; assert(p.bind(ops(s)) && p.setup());
        s.actors.push_back(&late); assert(p.syncOwnership());
        assert(late.owner==1 && s.writes==0);
        a.owner=1; assert(p.adoptSquad()==2);
        const unsigned ids[]={1,2}; assert(p.transferSquad(1,0,ids,2)==2);
        assert(a.owner==0 && late.owner==0);
        a.owner=-1; assert(p.adoptSquad()==1 && p.ownerOfActor(1)==-1);
    }
    {
        Actor a{1,0}; Scene s; s.actors={&a}; P2CaptainAdapter p;
        assert(p.bind(ops(s)) && p.setup()); s.badEnumeration=true;
        assert(p.adoptSquad()==-1 && !p.syncOwnership());
        assert(!p.captureCaptain(0,77) && a.owner==0);
    }
    std::puts("PASS P2_CAPTAIN_RECONCILIATION");
}
