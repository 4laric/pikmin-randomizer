#include "pc_p2_surface_session.h"
#include <cstdlib>
#include <iostream>
#include <sstream>
#include <limits>
void require(bool ok,const char* why){if(!ok){std::cerr<<why<<'\n';std::exit(1);}}
std::string wire(const P2SurfaceSession& s){std::ostringstream out;s.write(out);return out.str();}
int main(){
    P2SurfaceSession saved;saved.present=true;saved.stage=1;saved.index=2;saved.day=7;saved.file="stages/forest.ini";
    saved.party.present=true;saved.party.surfaceTime=13.123456f;saved.party.active=1;
    saved.party.captains={{0,43,100,1,{1,2,3}},{1,89,100,2,{4,5,6}}};
    saved.party.nextKey=21;
    for(int i=0;i<20;++i){P2CavePartyBody body;body.species=i%3;body.growth=i%3;body.owner=i%2;
        body.player=i%2;body.mode=1;body.key=i+1;body.health=27;body.maxHealth=50;
        body.position={float(i)+.125f,2,3};body.originPosition=body.position;saved.party.bodies.push_back(body);}
    saved.sources={{0,-1,1},{5,7,0},{15,20,1}};
    saved.sources[0].position={123.456789f,-42.1234567f,0.000123456789f};
    saved.sources[0].offset={1.23456789f,9.87654321f,-0.0123456789f};
    require(saved.valid(),"valid native surface descriptor");
    P2SurfaceSession restored;std::istringstream in(wire(saved));require(restored.read(in),"read actual typed state");
    require(saved.sources[0].position.x==restored.sources[0].position.x
        &&saved.sources[0].position.y==restored.sources[0].position.y
        &&saved.sources[0].offset.z==restored.sources[0].offset.z,"literal source floats roundtrip exactly");
    require(wire(saved)==wire(restored),"clock, captain HP/slot and every body round-trip exactly");
    auto original=wire(restored);
    auto bad=saved;bad.file="stages/../forest.ini";std::istringstream hostile(wire(bad));
    require(!restored.read(hostile)&&wire(restored)==original,"hostile descriptor leaves selected state intact");
    for(int day:{-1,30}){bad=saved;bad.day=day;require(!bad.valid(),"day outside native campaign rejected");}
    bad=saved;bad.sources[0].flags=16;require(!bad.valid(),"foreign authored source flags rejected");
    bad=saved;bad.sources[0].aliveCount=2;require(!bad.valid(),"grouped source payload refused");
    bad=saved;bad.sources[0].dayLimit=-2;require(!bad.valid(),"foreign authored source expiry rejected");
    bad=saved;bad.party.inside=true;require(!bad.valid(),"cannot resume cave through surface dispatcher");
    bad=saved;bad.party.surfaceTime=std::numeric_limits<float>::quiet_NaN();require(!bad.valid(),"nonfinite clock rejected");
    bad=saved;bad.party.bodies[1].key=bad.party.bodies[0].key;require(!bad.valid(),"duplicate actor rejected");
    bad=saved;bad.party.captains.erase(bad.party.captains.begin()+1);require(!bad.valid(),"active captain must exist");
    for(std::size_t length=0;length<original.size();++length){P2SurfaceSession next=saved;
        std::istringstream shortRead(original.substr(0,length));
        require(!next.read(shortRead)&&wire(next)==original,"every truncation refuses atomically");}
    require(P2SurfaceSession{}.valid()&&wire(P2SurfaceSession{}).empty(),"legacy card has no extension");
    std::cout<<"P2_SURFACE_SESSION_PASS\n";
}
