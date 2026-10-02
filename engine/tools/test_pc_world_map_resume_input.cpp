#include "pc_world_map_observer.h"
#include <cstdio>
#define CHECK(x) do {if(!(x)){std::fprintf(stderr,"worldmap check failed line%d: %s\n",__LINE__,#x);return __LINE__;}}while(false)
struct TestNode {
    virtual ~TestNode()=default;
    const char* name=nullptr;TestNode* child=nullptr;TestNode* next=nullptr;TestNode* parent=nullptr;
    TestNode* Child(){return child;} TestNode* Next(){return next;} TestNode* Parent(){return parent;}
    const char* Name(){return name;}
};
struct TestMap:TestNode{};
struct TestSetup:TestNode{};
PcWorldMapSnapshot ready(std::uint64_t frame=1) {
    PcWorldMapSnapshot s;s.available=true;s.contextReady=true;s.courseOpen=true;
    s.coursePointOperation=true;s.cursorMoveReady=true;s.mode=2;s.returnStatus=5;s.selectedCourse=0;
    s.sectionIdentity=11;s.setupIdentity=12;s.menuIdentity=13;s.observedFrame=frame;return s;
}
int main() {
    using I=PcWorldMapInput;
    for(int mode=-1;mode<=1;++mode) {
        PcWorldMapResumeInput initial;auto fresh=ready();fresh.mode=mode;fresh.selectedCourse=-1;fresh.courseOpen=false;fresh.returnStatus=-1;
        CHECK(initial.observe(fresh,1)==I::Neutral && initial.keyEdges()==0);
        fresh=ready(2);CHECK(initial.observe(fresh,2)==I::Confirm && initial.keyEdges()==1);
        PcWorldMapResumeInput operational;fresh=ready();fresh.selectedCourse=-1;fresh.courseOpen=false;fresh.returnStatus=-1;
        CHECK(operational.observe(fresh,1)==I::Refuse && operational.keyEdges()==0);
        PcWorldMapResumeInput blocked;fresh.mode=mode;fresh.contextReady=false;
        CHECK(blocked.observe(fresh,1)==I::Refuse);
    }
    PcWorldMapResumeInput prefix;auto prefixState=ready();prefixState.mode=-1;prefixState.returnStatus=-1;prefixState.selectedCourse=-1;prefixState.courseOpen=false;
    CHECK(prefix.observe(prefixState,1)==I::Neutral);
    prefixState.mode=0;prefixState.observedFrame=2;CHECK(prefix.observe(prefixState,2)==I::Neutral);
    prefixState.mode=1;prefixState.observedFrame=3;CHECK(prefix.observe(prefixState,3)==I::Neutral);
    prefixState=ready(4);CHECK(prefix.observe(prefixState,4)==I::Confirm && prefix.keyEdges()==1);
    prefixState.mode=-1;prefixState.observedFrame=5;CHECK(prefix.observe(prefixState,5)==I::Refuse);
    TestMap typedMap;TestSetup typedSetup;TestNode impostor;
    TestMap* checkedMap=nullptr;TestSetup* checkedSetup=nullptr;
    PcWorldMapLiveOwner<TestNode> typed{&typedMap,&typedSetup};
    CHECK(pc_world_map_typed_owner(typed,checkedMap,checkedSetup));
    CHECK(checkedMap==&typedMap && checkedSetup==&typedSetup);
    typed.map=&impostor;
    CHECK(!pc_world_map_typed_owner(typed,checkedMap,checkedSetup));
    CHECK(!checkedMap && !checkedSetup);
    typed.map=&typedMap;typed.setup=&impostor;
    CHECK(!pc_world_map_typed_owner(typed,checkedMap,checkedSetup));
    CHECK(!checkedMap && !checkedSetup);
    typed.setup=nullptr;CHECK(!pc_world_map_typed_owner(typed,checkedMap,checkedSetup));
    TestNode root,map,setup;
    map.name="<MapSelectSection>";setup.name="MapSelect section";
    root.child=&map;map.parent=&root;map.child=&setup;setup.parent=&map;
    CHECK(pc_world_map_live_owner(&root).setup==&setup);
    CHECK(!pc_world_map_live_owner<TestNode>(nullptr).map);
    root.child=nullptr;CHECK(!pc_world_map_live_owner(&root).map);root.child=&map;
    // Exact current owner/name/parent chains are required; no prefix or cached adoption.
    for(int kind=0;kind<5;++kind) {
        if(kind==0)map.name="<MapSelectSection>foreign";
        if(kind==1)setup.name="MapSelect section foreign";
        if(kind==2)setup.parent=&root;
        if(kind==3)map.parent=&setup;
        if(kind==4)map.child=nullptr;
        CHECK(!pc_world_map_live_owner(&root).setup);
        map.name="<MapSelectSection>";setup.name="MapSelect section";
        map.parent=&root;setup.parent=&map;map.child=&setup;
    }
    TestNode duplicate;duplicate.name=map.name;duplicate.parent=&root;
    map.next=&duplicate;CHECK(!pc_world_map_live_owner(&root).map);map.next=nullptr;
    duplicate.name=setup.name;duplicate.parent=&map;
    setup.next=&duplicate;CHECK(!pc_world_map_live_owner(&root).setup);setup.next=nullptr;
    // A cyclic live sibling chain hits the fixed budget and cannot hang a query.
    duplicate.name="unrelated";duplicate.next=&duplicate;
    map.next=&duplicate;CHECK(!pc_world_map_live_owner(&root).map);map.next=nullptr;
    setup.next=&duplicate;CHECK(!pc_world_map_live_owner(&root).setup);setup.next=nullptr;
    duplicate.next=nullptr;
    PcWorldMapResumeInput flow;auto s=ready();
    CHECK(flow.observe(s,1)==I::Confirm && flow.keyEdges()==1);
    CHECK(flow.observe(s,1)==I::Neutral && flow.keyEdges()==1); // Same native frame cannot emit another edge.
    s.observedFrame=2;s.mode=4;CHECK(flow.observe(s,2)==I::Neutral); // Mandatory key-up, even at next prompt.
    s.observedFrame=3;CHECK(flow.observe(s,3)==I::Neutral); // Confirm is still appearing.
    s.observedFrame=4;s.confirmationActive=true;s.confirmationYes=true;
    CHECK(flow.observe(s,4)==I::Confirm && flow.keyEdges()==2);
    s.observedFrame=5;CHECK(flow.observe(s,5)==I::Neutral);
    s.observedFrame=6;s.confirmationActive=false;CHECK(flow.observe(s,6)==I::Neutral);
    s.observedFrame=7;s.mode=2;s.cursorMoveReady=false;CHECK(flow.observe(s,7)==I::Neutral);
    s.observedFrame=8;s.mode=8;s.returnStatus=0;CHECK(flow.observe(s,8)==I::Neutral); // Actual landed course return.
    s.available=false;CHECK(flow.observe(s,9)==I::Neutral && flow.keyEdges()==2); // Owner retired normally.
    CHECK(flow.observe(s,8)==I::Refuse); // Native frame cannot move backwards.

    for(int kind=0;kind<12;++kind) {
        PcWorldMapResumeInput control;auto invalid=ready();
        switch(kind) {
        case 0:invalid.contextReady=false;break; // Foreign overlay/challenge/invalid owner prefix.
        case 1:invalid.sectionIdentity=0;break;
        case 2:invalid.setupIdentity=0;break;
        case 3:invalid.menuIdentity=0;break;
        case 4:invalid.selectedCourse=-1;break;
        case 5:invalid.selectedCourse=1;break; // No guessing a different stage.
        case 6:invalid.courseOpen=false;break;
        case 7:invalid.returnStatus=0;break; // Premature landed status is not input-ready.
        case 8:invalid.mode=3;break; // Pause overlay.
        case 9:invalid.mode=6;break; // Diary overlay.
        case 10:invalid.mode=4;invalid.confirmationActive=true;invalid.confirmationYes=true;break;
        case 11:invalid.observedFrame=0;break; // Cached/stale snapshot.
        }
        CHECK(control.observe(invalid,1)==I::Refuse && control.keyEdges()==0);
    }
    for(int kind=0;kind<3;++kind) {
        PcWorldMapResumeInput control;auto changed=ready();CHECK(control.observe(changed,1)==I::Confirm);
        changed.observedFrame=2;
        if(kind==0)++changed.sectionIdentity;
        if(kind==1)++changed.setupIdentity;
        if(kind==2)++changed.menuIdentity;
        CHECK(control.observe(changed,2)==I::Refuse); // Actual owner/menu lifetime change even during key-up.
    }
    for(int kind=0;kind<4;++kind) {
        PcWorldMapResumeInput control;auto blocked=ready();
        if(kind==0)blocked.available=false;
        if(kind==1)blocked.coursePointOperation=false;
        if(kind==2)blocked.cursorMoveReady=false;
        if(kind==3)blocked.mode=0;
        CHECK(control.observe(blocked,1)==I::Neutral && control.keyEdges()==0);
    }
    PcWorldMapResumeInput no;auto confirm=ready();CHECK(no.observe(confirm,1)==I::Confirm);
    confirm.observedFrame=2;CHECK(no.observe(confirm,2)==I::Neutral);
    confirm.observedFrame=3;confirm.mode=4;confirm.confirmationActive=true;confirm.confirmationYes=false;
    CHECK(no.observe(confirm,3)==I::Refuse && no.keyEdges()==1);
    std::puts("PC_WORLD_MAP_RESUME_INPUT_PASS source_policy_controls=1 actual_worldmap_gameplay=unexecuted");
}
