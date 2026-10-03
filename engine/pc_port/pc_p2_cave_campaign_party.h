#pragma once
#include <array>
#include <cmath>
#include <iomanip>
#include <istream>
#include <limits>
#include <ostream>
#include <string>
#include <utility>
#include <cstdint>
#include <vector>

struct P2CavePartyPoint {
    float x=0,y=0,z=0;
    bool valid()const{return std::isfinite(x)&&std::isfinite(y)&&std::isfinite(z)
        &&std::fabs(x)<1e7f&&std::fabs(y)<1e7f&&std::fabs(z)<1e7f;}
    bool read(std::istream& in){return bool(in>>x>>y>>z)&&valid();}
    void write(std::ostream& out)const{out<<' '<<x<<' '<<y<<' '<<z;}
};
struct P2CavePartyCaptain {
    int slot=-1;float health=0,maxHealth=0,face=0;P2CavePartyPoint position;
    bool valid()const{return slot>=0&&slot<2&&position.valid()&&std::isfinite(face)
        &&std::isfinite(health)&&std::isfinite(maxHealth)&&maxHealth>0&&maxHealth<=100000
        &&health>0&&health<=maxHealth;}
};
struct P2CavePartyBody {
    int species=-1,growth=-1,owner=-1,player=-1,mode=0;
    bool wild=false,wasWild=false;
    std::uint32_t generator=0;
    std::uint64_t key=0;
    int originRealm=0;
    std::uint32_t originGenerator=0;
    P2CavePartyPoint originPosition;
    std::string sourceKey;
    std::string catalogFingerprint;
    std::uint32_t sourceRecord=0,sourceAttempt=0;
    std::uint64_t sourceActivation=0;
    bool sourceValid()const{
        if(sourceKey.empty())return catalogFingerprint.empty()&&sourceRecord==0&&sourceAttempt==0&&sourceActivation==0;
        if(sourceKey=="-"||sourceKey.size()>256||sourceAttempt>65535||sourceActivation==0)return false;
        if(catalogFingerprint.size()!=64)return false;
        for(char c:catalogFingerprint)if(!((c>='0'&&c<='9')||(c>='a'&&c<='f')))return false;
        for(unsigned char c:sourceKey)if(c<=32||c>=127)return false;
        return true;
    }
    float health=0,maxHealth=0,face=0;P2CavePartyPoint position;
    bool sameOrigin(const P2CavePartyBody& other)const{
        return originRealm==other.originRealm&&originGenerator==other.originGenerator
            &&sourceKey==other.sourceKey&&catalogFingerprint==other.catalogFingerprint&&sourceRecord==other.sourceRecord
            &&sourceAttempt==other.sourceAttempt&&sourceActivation==other.sourceActivation
            &&originPosition.x==other.originPosition.x&&originPosition.y==other.originPosition.y
            &&originPosition.z==other.originPosition.z;
    }
    bool sameSource(const P2CavePartyBody& other)const{
        return !sourceKey.empty()&&sourceKey==other.sourceKey&&catalogFingerprint==other.catalogFingerprint&&sourceRecord==other.sourceRecord
            &&sourceAttempt==other.sourceAttempt&&sourceActivation==other.sourceActivation;
    }
    bool valid()const{return species>=0&&species<=4&&growth>=0&&growth<=2
        &&owner>=-1&&owner<2&&player>=-1&&player<2&&(mode==0||mode==1)
        &&(!wild||wasWild)&&(!(wild||wasWild)||!sourceKey.empty())
        &&(mode==0||owner>=0)&&position.valid()&&std::isfinite(face)&&std::isfinite(health)
        &&key>0&&key<1000000000ULL&&(originRealm==0||originRealm==1)&&originPosition.valid()&&sourceValid()
        &&std::isfinite(maxHealth)&&maxHealth>0&&maxHealth<=100000&&health>0&&health<=maxHealth;}
};
struct P2CavePartyHead {
    int species=-1,growth=-1,owner=-1,parent=-1,state=6,counter=0,motion=0,key=0,previousKey=0,playState=0;
    float timer=0,frame=0,speed=0;
    P2CavePartyPoint position;
    bool valid()const{return species>=0&&species<=4&&growth>=0&&growth<=2
        &&owner>=-1&&owner<2&&parent>=-1&&parent<=2&&state==6&&(counter==0||counter==1)
        &&motion>=0&&motion<7&&key>=-1&&key<=100000&&previousKey>=0&&previousKey<=100000
        &&playState>=0&&playState<=2&&std::isfinite(timer)&&timer>=0&&timer<=100000
        &&std::isfinite(frame)&&frame>=0&&frame<=100000&&std::isfinite(speed)&&speed>=0&&speed<=100000
        &&position.valid();}
};
// Native owned state, separate from P1's two-bit colour fields. Heads stay in
// their own map; living bodies and captain health travel through the boundary.
struct P2CaveCampaignParty {
    bool present=false,inside=false;
    bool resumeLiving=true;
    bool landing=false;
    float surfaceTime=0;
    int active=0;
    std::uint64_t nextKey=1;
    std::vector<P2CavePartyCaptain> captains;
    std::vector<P2CavePartyBody> bodies;
    std::vector<P2CavePartyBody> origins;
    std::vector<P2CavePartyHead> surfaceHeads,floorHeads;
    std::array<P2CavePartyPoint,2> surfaceHomes{};
    bool retainOrigin(const P2CavePartyBody& body){
        if(!body.originGenerator&&body.sourceKey.empty())return true;
        if(!body.valid())return false;
        for(const auto& origin:origins)
            if(origin.key==body.key)return body.sameOrigin(origin);
        origins.push_back(body);return true;
    }
    bool valid()const{
        if(!present)return !inside&&captains.empty()&&bodies.empty()&&origins.empty()&&surfaceHeads.empty()&&floorHeads.empty();
        if(!std::isfinite(surfaceTime)||surfaceTime<0||surfaceTime>=24
            ||(inside&&!resumeLiving)||active<0||active>1||captains.empty()||captains.size()>2||bodies.size()>100
            ||surfaceHeads.size()>100||floorHeads.size()>100||origins.size()>256||nextKey<1||nextKey>=1000000000ULL)return false;
        unsigned slots=0;
        for(const auto& captain:captains){if(!captain.valid()||(slots&(1u<<captain.slot)))return false;
            slots|=1u<<captain.slot;}
        if(!(slots&(1u<<active)))return false;
        for(const auto& body:bodies)if(!body.valid()||(body.owner>=0&&!(slots&(1u<<body.owner))))return false;
        for(std::size_t i=0;i<bodies.size();++i){if(bodies[i].key>=nextKey)return false;
            for(std::size_t j=0;j<i;++j)if(bodies[i].key==bodies[j].key)return false;}
        for(std::size_t i=0;i<origins.size();++i){const auto& origin=origins[i];
            if(!origin.valid()||(origin.originGenerator==0&&origin.sourceKey.empty())||origin.key>=nextKey)return false;
            for(std::size_t j=0;j<i;++j)if(origin.key==origins[j].key
                ||origin.sameSource(origins[j])||origin.sameOrigin(origins[j]))return false;}
        for(const auto& body:bodies){
            const P2CavePartyBody* origin=nullptr;
            for(const auto& candidate:origins)if(candidate.key==body.key)origin=&candidate;
            if(origin&&!body.sameOrigin(*origin))return false;
            if((body.originGenerator||!body.sourceKey.empty())&&!origin)return false;
        }
        for(const auto* heads:{&surfaceHeads,&floorHeads})for(const auto& head:*heads)
            if(!head.valid()||(head.owner>=0&&!(slots&(1u<<head.owner))))return false;
        for(const auto& point:surfaceHomes)if(!point.valid())return false;
        return true;
    }
    bool read(std::istream& in){
        P2CaveCampaignParty parsed;std::string tag,version;int presentFlag,insideFlag,resumeFlag,landingFlag;
        if(!(in>>tag>>version>>presentFlag)||tag!="CAVE_PARTY"||(version!="2"&&version!="3")
            ||(presentFlag!=0&&presentFlag!=1))return false;
        parsed.present=presentFlag==1;
        if(!parsed.present){*this=parsed;return true;}
        unsigned count;
        if(!(in>>insideFlag>>resumeFlag>>landingFlag>>parsed.surfaceTime>>parsed.active>>parsed.nextKey>>count)||(insideFlag!=0&&insideFlag!=1)
            ||(resumeFlag!=0&&resumeFlag!=1)||(landingFlag!=0&&landingFlag!=1)||count<1||count>2)return false;
        parsed.inside=insideFlag==1;
        parsed.resumeLiving=resumeFlag==1;
        parsed.landing=landingFlag==1;
        for(unsigned i=0;i<count;++i){P2CavePartyCaptain c;
            if(!(in>>c.slot>>c.health>>c.maxHealth>>c.face)||!c.position.read(in))return false;
            parsed.captains.push_back(c);}
        for(auto* records:{&parsed.bodies,&parsed.origins}){
            if(!(in>>count)||count>(records==&parsed.bodies?100u:256u))return false;
            for(unsigned i=0;i<count;++i){P2CavePartyBody b;
                if(!(in>>b.species>>b.growth>>b.owner>>b.player>>b.mode>>b.generator>>b.key>>b.originRealm>>b.originGenerator
                    >>b.sourceKey>>b.catalogFingerprint>>b.sourceRecord>>b.sourceAttempt>>b.sourceActivation
                    >>b.health>>b.maxHealth>>b.face)||!b.position.read(in)||!b.originPosition.read(in))return false;
                if(version=="3"){int w=-1,was=-1;if(!(in>>w>>was)||(w!=0&&w!=1)||(was!=0&&was!=1))return false;b.wild=w==1;b.wasWild=was==1;}
                if(b.sourceKey=="-")b.sourceKey.clear();
                // Legacy source records do not authenticate logical body flags.
                if(version=="2"&&!b.sourceKey.empty())return false;
                if(b.catalogFingerprint=="-")b.catalogFingerprint.clear();
                records->push_back(b);}}
        for(auto* heads:{&parsed.surfaceHeads,&parsed.floorHeads}){
            if(!(in>>count)||count>100)return false;
            for(unsigned i=0;i<count;++i){P2CavePartyHead h;
                if(!(in>>h.species>>h.growth>>h.owner>>h.parent>>h.state>>h.counter>>h.motion>>h.key
                    >>h.previousKey>>h.playState>>h.timer>>h.frame>>h.speed)||!h.position.read(in))return false;
                heads->push_back(h);}}
        for(auto& point:parsed.surfaceHomes)if(!point.read(in))return false;
        if(!parsed.valid())return false;
        *this=std::move(parsed);return true;
    }
    void write(std::ostream& out)const{
        out<<std::setprecision(std::numeric_limits<float>::max_digits10)<<" CAVE_PARTY 3 "<<int(present);
        if(!present)return;
        out<<' '<<int(inside)<<' '<<int(resumeLiving)<<' '<<int(landing)<<' '<<surfaceTime<<' '<<active<<' '<<nextKey<<' '<<captains.size();
        for(const auto& c:captains){out<<' '<<c.slot<<' '<<c.health<<' '<<c.maxHealth<<' '<<c.face;c.position.write(out);}
        for(const auto* records:{&bodies,&origins}){out<<' '<<records->size();
            for(const auto& b:*records){out<<' '<<b.species<<' '<<b.growth<<' '<<b.owner<<' '<<b.player<<' '<<b.mode<<' '<<b.generator
                <<' '<<b.key<<' '<<b.originRealm<<' '<<b.originGenerator
                <<' '<<(b.sourceKey.empty()?"-":b.sourceKey)<<' '<<(b.catalogFingerprint.empty()?"-":b.catalogFingerprint)
                <<' '<<b.sourceRecord<<' '<<b.sourceAttempt<<' '<<b.sourceActivation
                <<' '<<b.health<<' '<<b.maxHealth<<' '<<b.face;
                b.position.write(out);b.originPosition.write(out);out<<' '<<int(b.wild)<<' '<<int(b.wasWild);}}
        for(const auto* heads:{&surfaceHeads,&floorHeads}){out<<' '<<heads->size();
            for(const auto& h:*heads){out<<' '<<h.species<<' '<<h.growth<<' '<<h.owner<<' '<<h.parent<<' '<<h.state<<' '<<h.counter<<' '<<h.motion<<' '<<h.key
                <<' '<<h.previousKey<<' '<<h.playState<<' '<<h.timer<<' '<<h.frame<<' '<<h.speed;h.position.write(out);}}
        for(const auto& point:surfaceHomes)point.write(out);
    }
};
