#pragma once
#include "pc_p2_cave_campaign_party.h"

// An optional living surface checkpoint inside the native campaign envelope.
// Existing day-boundary saves have no extension. The card's hash authenticates
// this descriptor and the shared typed party together with its cache/stock.
struct P2SurfaceSource {
    unsigned flags=0;
    int dayLimit=-1, aliveCount=0, latestSpawnDay=-1, respawnInterval=0;
    P2CavePartyPoint position,offset;
    bool valid() const{return flags<=15&&dayLimit>=-1&&dayLimit<=32767&&(aliveCount==0||aliveCount==1)
        &&latestSpawnDay>=-1&&latestSpawnDay<30&&respawnInterval>=-1&&respawnInterval<=32767
        &&position.valid()&&offset.valid();}
};
struct P2SurfaceSession {
    bool present=false;
    int stage=-1, index=-1, day=-1;
    std::string file;
    P2CaveCampaignParty party;
    std::vector<P2SurfaceSource> sources;
    bool valid() const {
        if (!present) return stage==-1 && index==-1 && day==-1 && file.empty() && !party.present && sources.empty();
        if (stage<0 || stage>=5 || index<0 || index>=5 || day<0 || day>=30
            || file.size()>255 || file.rfind("stages/",0)!=0 || file.find("..")!=std::string::npos
            || file.find('\\')!=std::string::npos || !party.present || party.inside
            || !party.resumeLiving || party.landing || !party.valid()) return false;
        if(sources.size()>4096)return false;
        for(const auto& source:sources)if(!source.valid())return false;
        for (unsigned char c:file) if (c<=32 || c>=127) return false;
        return true;
    }
    bool read(std::istream& in) {
        P2SurfaceSession next; std::string marker,version;
        if (!(in>>marker>>version>>next.stage>>next.index>>next.day>>next.file)
            || marker!="SURFACE_SESSION" || (version!="1"&&version!="2")) return false;
        if(version=="2"){
            unsigned count=0;
            if(!(in>>count)||count>4096)return false;
            next.sources.resize(count);
            for(auto& source:next.sources)if(!(in>>source.flags>>source.dayLimit>>source.aliveCount>>source.latestSpawnDay>>source.respawnInterval)
                ||!source.position.read(in)||!source.offset.read(in)||!source.valid())return false;
        }
        if(!next.party.read(in))return false;
        next.present=true;
        if (!next.valid()) return false;
        *this=std::move(next); return true;
    }
    void write(std::ostream& out) const {
        if (!present) return;
        out<<std::setprecision(std::numeric_limits<float>::max_digits10)<<" SURFACE_SESSION 2 "<<stage<<' '<<index<<' '<<day<<' '<<file
           <<' '<<sources.size();
        for(const auto& source:sources){out<<' '<<source.flags<<' '<<source.dayLimit<<' '<<source.aliveCount
            <<' '<<source.latestSpawnDay<<' '<<source.respawnInterval;
            source.position.write(out);source.offset.write(out);}
        party.write(out);
    }
};
