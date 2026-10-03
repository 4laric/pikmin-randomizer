#include "pc_p2_retail_treasure_policy.h"
#include <cassert>
#include <iostream>
int main() {
    // Synthetic full numeric catalog and receipts exercise policy only.
    p2treasure::Catalog catalog;
    for(int i=1;i<=201;++i) {
        p2treasure::Entry e;e.id="synthetic_"+std::to_string(i);e.kind="otakara";
        e.classification=p2treasure::Classification::Campaign;e.index=i-1;e.dictionary=i;e.value=1;
        e.strength=1;e.slots=1;e.unique=true;catalog.entries.push_back(e);
    }
    auto& map=catalog.entries[183];map.id="map01";map.kind="item";map.index=10;
    map.value=200;map.strength=101;map.slots=101;
    const auto* cave=p2retail::descriptor("tutorial_1");assert(cave);
    const auto* floor=p2retail::definition(*cave,2);assert(floor);
    p2retail::BirthIdentity birth{5,0,4,p2retail::instanceKey(*cave,2,floor->rows[5],0),6};
    p2retail::SceneIdentity scene{"synthetic-seed","synthetic-visit",std::string(64,'a'),7};
    auto selectedScene=scene;selectedScene.seed=std::string(64,'f');
    assert(p2retailtreasure::selectedScene(selectedScene,std::string(64,'f')));
    assert(!p2retailtreasure::selectedScene(selectedScene,""));
    assert(!p2retailtreasure::selectedScene(selectedScene,std::string(64,'e')));
    selectedScene.seed="process-token";
    assert(!p2retailtreasure::selectedScene(selectedScene,"process-token"));
    p2retail::Snapshot expected{cave->cave,cave->source,cave->sourceSha256,cave->catalogSha256,2,cave->maxFloor,scene,true,true};
    auto source=p2retailtreasure::looseSource(catalog,*cave,2,birth,scene,expected,birth);
    assert(source&&source->id=="map01"&&source->strength==101&&source->slots==101);
    p2treasurestate::State state;const std::string selected(64,'b');assert(state.bind(selected));
    assert(!p2retailtreasure::consumed(catalog,state,selected,*cave,2,birth,scene,expected,birth,"map01"));
    assert(state.credit(catalog,"map01",200)==p2treasurestate::Credit::Added);
    const auto before=state.snapshot();
    assert(p2retailtreasure::consumed(catalog,state,selected,*cave,2,birth,scene,expected,birth,"map01"));
    assert(state.snapshot().bits==before.bits);
    assert(!p2retailtreasure::consumed(catalog,state,std::string(64,'c'),*cave,2,birth,scene,expected,birth,"map01"));
    assert(!p2retailtreasure::consumed(catalog,state,selected,*cave,2,birth,scene,expected,birth,"synthetic_1"));
    auto stale=scene;stale.serial++;
    assert(!p2retailtreasure::looseSource(catalog,*cave,2,birth,stale,expected,birth));
    stale=scene;stale.visit="other";
    assert(!p2retailtreasure::looseSource(catalog,*cave,2,birth,stale,expected,birth));
    auto bad=birth;bad.ordinal=1;
    assert(!p2retailtreasure::looseSource(catalog,*cave,2,bad,scene,expected,birth));
    bad=birth;bad.row=1;
    assert(!p2retailtreasure::looseSource(catalog,*cave,2,bad,scene,expected,birth));
    bad=birth;bad.instance="engineering-map01";
    assert(!p2retailtreasure::looseSource(catalog,*cave,2,bad,scene,expected,birth));
    bad=birth;bad.epoch++;
    assert(!p2retailtreasure::looseSource(catalog,*cave,2,bad,scene,expected,birth));
    bad=birth;bad.activation++;
    assert(!p2retailtreasure::looseSource(catalog,*cave,2,bad,scene,expected,birth));
    auto wrongFloor=expected;wrongFloor.floor=1;
    assert(!p2retailtreasure::looseSource(catalog,*cave,2,birth,scene,wrongFloor,birth));
    wrongFloor=expected;wrongFloor.cave="tutorial_2";
    assert(!p2retailtreasure::looseSource(catalog,*cave,2,birth,scene,wrongFloor,birth));
    auto forged=*cave;forged.sourceSha256=std::string(64,'d');
    assert(!p2retailtreasure::looseSource(catalog,forged,2,birth,scene,expected,birth));
    assert(!p2retailtreasure::looseSource(catalog,*cave,1,birth,scene,expected,birth));
    assert(!p2retailtreasure::looseSource(catalog,*cave,3,birth,scene,expected,birth));
    std::cout<<"PASS literal loose source/101 profile/scene/ordinal/receipt refusal policy\n";
}
