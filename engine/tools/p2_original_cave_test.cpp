#include "pc_p2_original_cave.h"
#include "netplay/pc_netplay_sha256.h"
#include <cassert>
#include <limits>
#include <sstream>
#include <iostream>
using namespace p2original;
static CaveRecord source(){
    CaveRecord r;r.sourceKey="tutorial/defaultgen.txt#6";r.sourceSha="64d283dc22622fc928e11423ed0b8f7a400f89251fd6c204974315ff1e998ce7";
    unsigned char b[32];pc_netplay_sha::sha256(r.sourceKey.data(),r.sourceKey.size(),b);
    r.uid=0x52000000u|(unsigned(b[0])<<16)|(unsigned(b[1])<<8)|b[2];
    r.caveFile="tutorial_1.txt";r.unitsFile="units.txt";r.caveId="t_01";
    r.position={-190,80,1160};r.rotation={0,-45,0};
    r.parameterTypes={4,4,4,4,1,1,1,4,4,4};r.parameters={1,1500,1.5f,2,62,77,65,6000,200,205};return r;
}
static std::string manifest(const CaveRecord& r){std::ostringstream s;s<<"P2_ORIGINAL_CAVE_1 1\n"<<r.uid<<' '<<r.sourceKey<<' '<<r.sourceSha<<" 0002 0002 "<<r.reserved<<' '<<r.resurrectionDays<<' '<<r.dayLimit<<' '<<r.caveFile<<' '<<r.unitsFile<<' '<<r.caveId;
    for(const auto* a:{&r.position,&r.offset,&r.rotation})for(float f:*a)s<<' '<<f;
    for(unsigned i=0;i<10;++i)s<<' '<<r.parameterTypes[i]<<' '<<r.parameters[i];
    return s.str()+"\n";
}
int main(int argc,char** argv){std::string e;auto r=source();assert(validateCave(r,e));assert(r.uid==1387550288u);
    std::vector<CaveRecord> rows;const auto bytes=manifest(r);assert(parseCaves(bytes,rows,e));assert(rows.size()==1&&caveDigest(rows[0])==caveDigest(r));
    const auto stable=caveDigest(rows[0]);assert(!parseCaves(bytes+"junk",rows,e));assert(rows.size()==1&&caveDigest(rows[0])==stable);
    assert(!parseCaves(bytes.substr(0,bytes.size()-8),rows,e));assert(!parseCaves("P2_ORIGINAL_CAVE_1 0",rows,e));
    auto bad=r;bad.uid++;assert(!validateCave(bad,e));bad=r;bad.unitsFile="../units.txt";assert(!validateCave(bad,e));
    bad=r;bad.position[0]=std::numeric_limits<float>::infinity();assert(!validateCave(bad,e));
    bad=r;bad.position[0]=100001;bad.offset[0]=-100001;assert(!validateCave(bad,e));
    bad=r;bad.rotation[0]=std::numeric_limits<float>::quiet_NaN();assert(!validateCave(bad,e));
    bad=r;bad.resurrectionDays=1;assert(!validateCave(bad,e));bad=r;bad.reserved=1;assert(!validateCave(bad,e));
    bad=r;bad.parameterTypes[4]=4;assert(!validateCave(bad,e));bad=r;bad.parameters[4]=62.5f;assert(!validateCave(bad,e));
    bad=r;bad.parameters[6]=256;assert(!validateCave(bad,e));
    std::vector<std::uint8_t> cache;assert(caveCache(r,cache,e));assert(cache.size()==104&&caveRestore(r,cache,e));
    for(std::size_t i=0;i<cache.size();++i){auto corrupt=cache;corrupt[i]^=1;assert(!caveRestore(r,corrupt,e));}
    for(unsigned i=0;i<10;++i){bad=r;bad.parameters[i]+=1;assert(validateCave(bad,e));assert(!caveRestore(bad,cache,e));}
    bad=r;bad.position[0]+=1;assert(!caveRestore(bad,cache,e));bad=r;bad.dayLimit=5;assert(!caveRestore(bad,cache,e));
    if(argc==2){assert(readCaves(argv[1],rows,e));assert(rows.size()==3);assert(rows[0].uid==r.uid&&caveDigest(rows[0])==caveDigest(r));}
    std::cout<<"P2 original Cave literal/cache tests PASS\n";
}
