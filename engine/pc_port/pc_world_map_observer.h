#ifndef PC_WORLD_MAP_OBSERVER_H
#define PC_WORLD_MAP_OBSERVER_H
#include <cstdint>
#include <cstring>

// Uses only nodes belonging to the current live root; never searches cached UI
// addresses. Shared by the production query and bounded synthetic owner tests.
template<class Node> struct PcWorldMapLiveOwner { Node* map=nullptr;Node* setup=nullptr; };
template<class Node> PcWorldMapLiveOwner<Node> pc_world_map_live_owner(Node* root) {
    PcWorldMapLiveOwner<Node> owner;
    if (!root) return owner;
    unsigned count=0;
    for (Node* p=root->Child();p && count++<16;p=p->Next()) {
        if (p->Name() && !std::strcmp(p->Name(),"<MapSelectSection>")) {
            if (owner.map) return {};
            owner.map=p;
        }
    }
    if (!owner.map || count>=16) return {};
    count=0;
    for (Node* p=owner.map->Child();p && count++<16;p=p->Next()) {
        if (p->Name() && !std::strcmp(p->Name(),"MapSelect section")) {
            if (owner.setup) return {};
            owner.setup=p;
        }
    }
    if (!owner.setup || count>=16 || owner.setup->Parent()!=owner.map || owner.map->Parent()!=root) return {};
    return owner;
}
// Call only after current live tree membership/parent checks. Exact names do
// not imply a concrete dynamic type; both owners must pass RTTI together.
template<class Map,class Setup,class Node> bool pc_world_map_typed_owner(
    const PcWorldMapLiveOwner<Node>& owner,Map*& map,Setup*& setup) {
    map=nullptr;setup=nullptr;
    if (!owner.map || !owner.setup) return false;
    auto* liveMap=dynamic_cast<Map*>(owner.map);
    auto* liveSetup=dynamic_cast<Setup*>(owner.setup);
    if (!liveMap || !liveSetup) return false;
    map=liveMap;setup=liveSetup;return true;
}

// Values only, queried on the engine thread from the current live section tree.
// No UI pointer or cached snapshot escapes; no scene/selection/card mutation.
struct PcWorldMapSnapshot {
    bool available=false, contextReady=false, courseOpen=false;
    bool coursePointOperation=false, cursorMoveReady=false;
    bool confirmationActive=false, confirmationYes=false;
    int mode=-1, returnStatus=-1, selectedCourse=-1;
    std::uint64_t sectionIdentity=0, setupIdentity=0, menuIdentity=0, observedFrame=0;
};
PcWorldMapSnapshot pc_world_map_observe();

enum class PcWorldMapInput { Neutral, Confirm, Refuse };
class PcWorldMapResumeInput {
    std::uint64_t section=0, setup=0, menu=0, lastFrame=0;
    unsigned phase=0, edges=0;
    bool sampled=false, release=false;
public:
    unsigned keyEdges() const { return edges; }
    PcWorldMapInput observe(const PcWorldMapSnapshot& s,std::uint64_t currentFrame) {
        if (s.available && (s.observedFrame!=currentFrame || !s.contextReady
            || !s.sectionIdentity || !s.setupIdentity || !s.menuIdentity)) return PcWorldMapInput::Refuse;
        if (sampled && currentFrame<lastFrame) return PcWorldMapInput::Refuse;
        if (sampled && currentFrame==lastFrame) return PcWorldMapInput::Neutral;
        sampled=true;lastFrame=currentFrame;
        if (s.available) {
            if (!section) {section=s.sectionIdentity;setup=s.setupIdentity;menu=s.menuIdentity;}
            if (section!=s.sectionIdentity || setup!=s.setupIdentity || menu!=s.menuIdentity
                || s.selectedCourse!=0 || !s.courseOpen
                || !(s.returnStatus==5 || (phase==2 && s.mode==8 && s.returnStatus==0)))
                return PcWorldMapInput::Refuse;
        }
        if (release) {release=false;return PcWorldMapInput::Neutral;}
        if (!s.available) return PcWorldMapInput::Neutral;
        // Native DrawWorldMap: Start0/Appear1, Operation2, Confirm4, End8.
        // Operation requires the actual course-point Operation and cursor gate.
        if (s.mode==2) {
            if (phase==0 && s.coursePointOperation && s.cursorMoveReady) {
                ++edges;phase=1;release=true;return PcWorldMapInput::Confirm;
            }
            return PcWorldMapInput::Neutral;
        }
        if (s.mode==4) {
            if (phase==0) return PcWorldMapInput::Refuse;
            if (!s.confirmationActive) return PcWorldMapInput::Neutral;
            if (!s.confirmationYes || phase!=1 || edges!=1) return PcWorldMapInput::Refuse;
            ++edges;phase=2;release=true;return PcWorldMapInput::Confirm;
        }
        if (((s.mode==0 || s.mode==1) && phase==0) || (s.mode==8 && phase==2)) return PcWorldMapInput::Neutral;
        // Paused/diary/unknown modes are outside this ordinary resume route.
        return PcWorldMapInput::Refuse;
    }
};
#endif
