#include "pc_p2_original_throw.h"
#include "pc_p2_original_piki_origin.h"
#include "pc_p2_original_source_uid.h"
#include <cassert>
#include <cstdio>
#include <limits>
class Piki { public: int species=1; };
int pc_p2_species(const Piki* p){return p?p->species:-1;}
bool pc_p2_cave_campaign_party_associate_birth(Piki*,const char*,std::uint32_t,std::uint32_t,std::uint64_t,const char*){return true;}
bool pc_p2_cave_campaign_survivor_permit(const std::string&,std::uint32_t,std::uint32_t,std::uint64_t,const std::string&,std::uint64_t*,std::uint8_t[32]){return false;}
bool pc_p2_cave_campaign_survivor_body(const std::string&,std::uint32_t,std::uint32_t,std::uint64_t,const std::string&,OriginalPikiBodyState&,std::uint64_t*,std::uint8_t[32]){return false;}
bool near(float a,float b){return std::fabs(a-b)<0.001f;}
int main(){
    // Compile actual origin registry and trajectory adapter, substituting only
    // body species and the party's notification/save callbacks.
    Piki p;std::string error,fingerprint(64,'a');
    assert(pc_p2_original_rgb_throw_species(nullptr)==-1);
    assert(pc_p2_original_rgb_throw_species(&p)==-1); // ordinary P1
    const std::string key="yakushima/defaultgen.txt#0";
    const unsigned uid=p2original::originalSourceCatalogUid(key);
    assert(pc_p2_original_piki_origin_install(fingerprint,{{key,uid,5,2}},error));
    OriginalPikiBody original{{key,uid,0,1,fingerprint},{2,true,true}};
    p.species=2;
    assert(pc_p2_original_piki_body_associate_birth(&p,original));
    assert(pc_p2_original_rgb_throw_species(&p)==-1); // not recruited
    assert(pc_p2_original_piki_body_recruited(&p));
    assert(pc_p2_original_rgb_throw_species(&p)==2);
    p.species=1;assert(pc_p2_original_rgb_throw_species(&p)==-1); // clamp/tint mismatch
    p.species=2;assert(pc_p2_original_rgb_throw_species(&p)==2);
    pc_p2_original_piki_origin_forget(&p);
    assert(pc_p2_original_rgb_throw_species(&p)==-1); // recycled address
    original.origin.attempt=1;
    assert(pc_p2_original_piki_origin_associate_birth(&p,original.origin));
    assert(pc_p2_original_rgb_throw_species(&p)==-1); // legacy origin has no body flags
    pc_p2_original_piki_origin_scene_exit();
    assert(pc_p2_original_rgb_throw_species(&p)==-1);

    for(float gravity:{300.0f,900.0f})for(float distance:{0.0f,50.0f,150.0f}) {
        p2throw::Velocity red,blue,yellow;
        assert(p2throw::rgbVelocity(0,distance,gravity,blue));
        assert(p2throw::rgbVelocity(1,distance,gravity,red));
        assert(p2throw::rgbVelocity(2,distance,gravity,yellow));
        assert(near(red.vertical,blue.vertical));
        assert(near(red.horizontal,blue.horizontal));
        assert(yellow.vertical>red.vertical);
        for(auto velocity:{red,yellow}) {
            // Independent ballistic control: start at y=0, solve for the later
            // crossing of y=0, then require the cursor's horizontal distance.
            const double landing=2.0*velocity.vertical/gravity;
            assert(near(float(velocity.horizontal*landing),distance));
            const double peak=velocity.vertical*velocity.vertical/(2.0*gravity);
            assert(peak>0.0);
        }
        const float yellowParameter=(yellow.vertical-gravity*0.25f)*0.5f;
        assert(near(yellowParameter,107.0f));
        assert(near((red.vertical-gravity*0.25f)*0.5f,72.5f));
    }
    p2throw::Velocity unchanged{9.0f,8.0f};
    assert(!p2throw::rgbVelocity(3,10,900,unchanged)); // Purple excluded
    assert(!p2throw::rgbVelocity(4,10,900,unchanged));
    assert(!p2throw::rgbVelocity(5,10,900,unchanged));
    assert(!p2throw::rgbVelocity(-1,10,900,unchanged));
    assert(!p2throw::rgbVelocity(2,-1,900,unchanged));
    assert(!p2throw::rgbVelocity(2,1,0,unchanged));
    assert(!p2throw::rgbVelocity(2,std::numeric_limits<float>::infinity(),900,unchanged));
    assert(!p2throw::rgbVelocity(2,1,std::numeric_limits<float>::quiet_NaN(),unchanged));
    assert(unchanged.horizontal==9 && unchanged.vertical==8);
    std::puts("PASS original RGB trajectory authority and ballistic landing");
}
