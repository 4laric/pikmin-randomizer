#include "pc_p2_cave_campaign_party.h"
#include "pc_p2_cave_survivor_permit.h"
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <sstream>

namespace {
unsigned checks=0;
void check(bool value,const char* label){++checks;if(!value){std::cerr<<label<<'\n';std::exit(1);}}
std::string wire(const P2CaveCampaignParty& party){std::ostringstream out;party.write(out);return out.str();}
P2CaveCampaignParty fixture(){
    P2CaveCampaignParty p;p.present=true;p.inside=true;p.nextKey=3;p.surfaceTime=11.625f;
    p.captains.push_back({0,31.25f,50,.75f,{1.125f,2.25f,-3.5f}});
    p.captains.push_back({1,17,50,-.25f,{5,2.25f,0}});
    P2CavePartyBody b;b.species=4;b.growth=2;b.owner=1;b.mode=1;b.key=1;
    b.health=.75f;b.maxHealth=1;b.face=1.5f;b.position={10.125f,2.5f,-11.75f};
    b.originRealm=0;b.originPosition={21.5f,22.25f,23.125f};
    b.sourceKey="source:forest:piki";b.sourceRecord=0;b.sourceAttempt=4;b.sourceActivation=97;
    b.catalogFingerprint=std::string(64,'c');
    p.bodies.push_back(b);p.origins.push_back(b);
    b.key=2;b.species=3;b.sourceAttempt=5;b.position.x+=.125f;
    p.bodies.push_back(b);p.origins.push_back(b);
    P2CavePartyHead h;h.species=4;h.growth=1;h.owner=0;h.timer=.125f;h.frame=7.75f;h.speed=30;
    h.position={31.125f,32.25f,33.5f};p.surfaceHeads.push_back(h);p.floorHeads.push_back(h);
    p.surfaceHomes={P2CavePartyPoint{1,2,3},P2CavePartyPoint{4,5,6}};return p;
}
}
int main(int argc,char** argv){
    auto p=fixture();check(p.valid(),"valid full typed fixture");
    auto unadopted=p;unadopted.origins.clear();
    for(const auto& body:p.bodies)check(unadopted.retainOrigin(body),"unadopted source provenance retains immutable origin");
    check(unadopted.valid()&&wire(unadopted)==wire(p),"unadopted source repeat preserves keys and origin ledger");
    for(const auto& body:p.bodies)check(unadopted.retainOrigin(body),"repeated source origin retained idempotently");
    check(wire(unadopted)==wire(p),"source repeat never duplicates ledger");
    auto conflicting=p.bodies[0];conflicting.originPosition.x+=1;
    const auto retained=wire(unadopted);
    check(!unadopted.retainOrigin(conflicting)&&wire(unadopted)==retained,"conflicting source origin refused without rewriting identity");
    auto generated=p;generated.bodies.resize(1);generated.origins.clear();
    auto& generatedBody=generated.bodies[0];generatedBody.sourceKey.clear();generatedBody.catalogFingerprint.clear();
    generatedBody.sourceRecord=0;generatedBody.sourceAttempt=0;generatedBody.sourceActivation=0;generatedBody.originGenerator=123;
    check(generated.retainOrigin(generatedBody)&&generated.valid(),"unadopted generator provenance retains immutable origin");
    const auto generatedWire=wire(generated);
    check(generated.retainOrigin(generatedBody)&&wire(generated)==generatedWire,"repeated generator origin stable without duplicate");
    P2CaveCampaignParty parsed;std::istringstream input(wire(p));
    check(parsed.read(input),"read typed fixture");check(wire(parsed)==wire(p),"exact float/species/provenance roundtrip");
    auto bad=p;bad.origins[1].sourceAttempt=bad.origins[0].sourceAttempt;bad.origins[1].originPosition.x+=20;
    check(!bad.valid(),"duplicate source at different position refused");
    bad=p;bad.bodies[0].sourceActivation++;check(!bad.valid(),"changed survivor activation refused");
    bad=p;bad.bodies[0].catalogFingerprint[0]='d';check(!bad.valid(),"changed survivor catalog refused");
    bad=p;bad.bodies[0].catalogFingerprint.clear();check(!bad.valid(),"missing survivor catalog refused");
    bad=p;bad.bodies[0].originPosition.z++;check(!bad.valid(),"changed survivor origin position refused");
    bad=p;bad.origins.clear();check(!bad.valid(),"missing origin ledger refused");
    bad=p;bad.origins[0].sourceKey="-";check(!bad.valid(),"wire sentinel cannot be source identity");
    bad=p;bad.bodies.erase(bad.bodies.begin());check(bad.valid(),"lost source retained in ledger");
    bad=p;bad.bodies.clear();check(bad.valid(),"all source deaths retain ledger");
    bad=p;bad.bodies[1].key=bad.bodies[0].key;check(!bad.valid(),"duplicate living logical key refused");
    bad=p;bad.nextKey=2;check(!bad.valid(),"next logical key must follow all records");
    bad=p;bad.bodies[0].species=5;check(!bad.valid(),"unsupported Bulbmin refused");
    bad=p;bad.bodies[0].growth=3;check(!bad.valid(),"invalid growth refused");
    bad=p;bad.bodies[0].health=0;check(!bad.valid(),"dead living record refused");
    bad=p;bad.bodies[0].health=2;check(!bad.valid(),"health exceeds actual maximum refused");
    bad=p;bad.floorHeads[0].state=8;check(!bad.valid(),"transient head growth state refused");
    bad=p;bad.floorHeads[0].timer=std::numeric_limits<float>::infinity();check(!bad.valid(),"nonfinite head timer refused");
    bad=p;bad.captains[1].slot=0;check(!bad.valid(),"duplicate captain slot refused");
    bad=p;bad.captains.resize(1);check(!bad.valid(),"missing actual formation owner refused");
    bad=p;bad.resumeLiving=false;check(!bad.valid(),"floor cannot use surface sunset storage authority");
    bad=p;bad.inside=false;bad.resumeLiving=false;bad.bodies.clear();
    check(bad.valid(),"surface sunset retires living replay while retaining floor head bank");
    bad=p;bad.surfaceTime=24;check(!bad.valid(),"outside clock range refused");
    bad=p;bad.surfaceTime=std::numeric_limits<float>::quiet_NaN();check(!bad.valid(),"nonfinite surface clock refused");
    bad=p;bad.captains.resize(1);
    std::array<std::uint8_t,32> digest{};digest[0]=79;digest[31]=131;
    const auto source=p.bodies[0];std::uint64_t admitted=17;std::uint8_t admittedSha[32]={};
    auto permit=[&](const P2CaveCampaignParty& state,bool scoped,std::uint64_t proof,std::uint64_t active){
        return p2CaveSurvivorPermit(state,scoped,proof,active,digest,source.sourceKey,source.sourceRecord,
            source.sourceAttempt,source.sourceActivation,source.catalogFingerprint,&admitted,admittedSha);};
    check(permit(p,true,8,8),"actual selected source survivor admitted");
    check(admitted==8&&admittedSha[0]==79&&admittedSha[31]==131,"generation and full digest returned");
    check(!permit(p,false,8,8),"ordinary death context cannot use stale saved survivor");
    check(admitted==8&&admittedSha[0]==79,"failed permit preserves output");
    check(!permit(p,true,0,0),"unsaved state has no permit");
    check(!permit(p,true,8,9),"different adopted generation refused");
    check(permit(p,true,3,3),"explicitly selected older valid SAVE admitted");
    bad=p;bad.bodies.erase(bad.bodies.begin());check(!permit(bad,true,8,8),"loss tombstone cannot authorize resurrection");
    bad=p;bad.bodies[0].catalogFingerprint[0]='d';bad.origins[0].catalogFingerprint[0]='d';
    check(!permit(bad,true,8,8),"different immutable source catalog refused");
    bad=p;bad.inside=false;bad.resumeLiving=false;bad.bodies.clear();
    check(!permit(bad,true,8,8),"sunset stock authority cannot authorize living replay");
    digest.fill(0);check(!permit(p,true,8,8),"missing authenticated digest refused");
    bad=p;bad.captains.resize(1);
    const auto before=wire(parsed);auto truncated=wire(p);truncated.resize(truncated.size()/2);
    std::istringstream partial(truncated);check(!parsed.read(partial),"partial record refused");
    check(wire(parsed)==before,"failed read leaves owned state intact");
    std::istringstream invalidWire(wire(bad));check(!parsed.read(invalidWire),"semantic invalidity refused by parser");
    check(wire(parsed)==before,"invalid read leaves owned state intact");
    P2CaveCampaignParty empty;check(empty.valid(),"absent party valid");
    std::istringstream absent(wire(empty));check(parsed.read(absent)&&!parsed.present,"absent party resets state");
    auto flags=fixture();flags.bodies[0].wild=true;flags.bodies[0].wasWild=true;
    check(flags.valid(),"canonical source wild flags valid");
    std::istringstream flagWire(wire(flags));check(parsed.read(flagWire)&&parsed.bodies[0].wild&&parsed.bodies[0].wasWild,"Party3 authentic wild flags roundtrip");
    bad=flags;bad.bodies[0].wasWild=false;check(!bad.valid(),"wild requires wasWild");
    bad=flags;bad.bodies[0].sourceKey.clear();bad.bodies[0].catalogFingerprint.clear();bad.bodies[0].sourceRecord=0;bad.bodies[0].sourceAttempt=0;bad.bodies[0].sourceActivation=0;
    check(!bad.valid(),"P1 mode cannot manufacture source wild flags");
    auto malformed=wire(flags);const auto boundary=malformed.find(" 23.125 1 1");
    check(boundary!=std::string::npos,"flag fixture token found");
    malformed.replace(boundary+8,3,"2 1");const auto flagBefore=wire(parsed);std::istringstream badFlag(malformed);
    check(!parsed.read(badFlag)&&wire(parsed)==flagBefore,"nonboolean flag refused unchanged");
    digest.fill(7);OriginalPikiBodyState selectedFlags{0,false,false};admitted=0;for(auto& byte:admittedSha)byte=0;
    const auto& flagSource=flags.bodies[0];
    check(p2CaveSurvivorBody(flags,true,8,8,digest,flagSource.sourceKey,flagSource.sourceRecord,flagSource.sourceAttempt,flagSource.sourceActivation,flagSource.catalogFingerprint,selectedFlags,&admitted,admittedSha),"selected living body authenticates logical flags");
    check(selectedFlags.species==4&&selectedFlags.wild&&selectedFlags.wasWild&&admitted==8&&admittedSha[31]==7,"selected body outputs exact state and full proof");
    check(!p2CaveSurvivorBody(flags,false,8,8,digest,flagSource.sourceKey,flagSource.sourceRecord,flagSource.sourceAttempt,flagSource.sourceActivation,flagSource.catalogFingerprint,selectedFlags,&admitted,admittedSha),"ordinary context refuses flags");
    check(selectedFlags.species==4&&selectedFlags.wild&&selectedFlags.wasWild&&admitted==8&&admittedSha[31]==7,"false body proof preserves all outputs");
    std::istringstream legacyAbsent(" CAVE_PARTY 2 0");check(parsed.read(legacyAbsent)&&!parsed.present,"legacy absent party compatible");
    std::cout<<"P2 cave campaign party: "<<checks<<" controls passed\n";
    if(argc==3&&std::string(argv[1])=="--write-fixture"){
        std::ofstream out(argv[2]);check(bool(out),"fixture output opened");out<<wire(p)<<'\n';
        check(bool(out),"fixture output written");
    }else check(argc==1,"unexpected arguments");
}
