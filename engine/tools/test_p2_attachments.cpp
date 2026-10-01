#include "pc_p2_attachments.h"
#include <cassert>
#include <fstream>
#include <iostream>
#include <iomanip>
#include <limits>
using namespace p2attach;
static bool near(float a,float b){return std::fabs(a-b)<.0001f;}
static const char* source=R"(P2_ATTACHMENTS_1 2 1
root -1
mouth 0
attack 11 2
0 10
0 0 0 0 0 0 1 2 1 1
1 0 0 0 0 0 1 1 1 1
10 0 0 0 0 0 1 2 1 1
1 0 0 0 0 .707106781 .707106781 1 1 1
)";
int main(int argc,char** argv){
    std::istringstream input(source);auto bank=read(input);assert(bank&&checked(*bank));
    Instance actor,sibling;const auto token=actor.bind(bank),other=sibling.bind(bank);assert(token&&other&&token!=other);
    Affine root;root.m[0][3]=100;assert(actor.sample(token,0,5,root,1));
    Affine mouth;assert(actor.socket(token,1,mouth));assert(near(mouth.m[0][3],107));
    // Parent nonuniform scale is composed AFTER child rotation, preserving shear.
    assert(near(mouth.m[0][0],std::sqrt(2.f)));assert(near(mouth.m[1][0],std::sqrt(.5f)));
    Affine old=mouth;assert(sibling.sample(other,0,10,Affine{},1));assert(actor.socket(token,1,mouth));assert(near(mouth.m[0][3],old.m[0][3]));
    assert(!actor.socket(other,1,mouth));assert(!actor.socket(token,2,mouth));
    DamageVolume volume;const Vec inside=point(old,{0,0,0});
    assert(volume.contact(actor,token,1,0,1,{0,0,0},2,4,6,101,inside));
    assert(!volume.contact(actor,token,1,0,1,{0,0,0},2,4,6,101,inside));
    assert(!volume.contact(actor,token,1,0,1,{0,0,0},2,4,6,102,{500,0,0}));
    assert(actor.sample(token,0,10,Affine{},2,true));assert(actor.socket(token,1,mouth));assert(near(mouth.m[0][3],107));
    assert(!volume.contact(actor,token,2,0,1,{0,0,0},2,0,11,102,inside));
    assert(actor.sample(token,0,10,root,3));assert(actor.socket(token,1,mouth));assert(near(mouth.m[0][3],112));
    assert(!volume.contact(actor,token,2,0,1,{0,0,0},2,4,6,102,point(mouth,{0,0,0})));
    assert(actor.sample(token,0,5,root,4));assert(volume.contact(actor,token,2,0,1,{0,0,0},2,4,6,101,inside));
    assert(!volume.contact(actor,token,1,0,1,{0,0,0},2,4,6,103,inside));
    // Endpoint is excluded; the beginning is included. Caller owns attack serials.
    assert(actor.sample(token,0,6,root,5));assert(!volume.contact(actor,token,3,0,1,{0,0,0},100,4,6,103,inside));
    assert(actor.sample(token,0,4,root,6));assert(volume.contact(actor,token,3,0,1,{0,0,0},100,4,6,103,inside));
    // Contact storage is bounded and fails closed at capacity.
    for(Token i=1;i<=MaxContacts;++i)assert(volume.contact(actor,token,4,0,1,{0,0,0},100,0,11,i,inside));
    assert(!volume.contact(actor,token,4,0,1,{0,0,0},100,0,11,MaxContacts+1,inside));
    assert(actor.sample(token,0,4,root,7,false,true));assert(!actor.socket(token,1,mouth));
    assert(!volume.contact(actor,token,5,0,1,{0,0,0},100,0,11,1000,inside));assert(!actor.sample(token,0,4,root,8));
    auto next=actor.bind(bank);assert(next!=token);assert(!actor.socket(token,1,mouth));assert(actor.sample(next,0,4,root,1));
    assert(!actor.sample(next,0,std::numeric_limits<float>::quiet_NaN(),root,2));assert(!actor.socket(next,1,mouth));
    assert(actor.sample(next,0,4,root,3));assert(!actor.sample(next,0,4,root,2));
    actor.reset();assert(!actor.socket(next,1,mouth));
    Quat q=slerp({0,0,0,1},{0,0,0,-1},.5f);assert(near(q.w,1));
    for(auto bad:{std::string(source)+"junk",std::string("P2_ATTACHMENTS_1 129 1"),std::string("P2_ATTACHMENTS_1 1 1\nroot 0\n")}){std::istringstream in(bad);assert(!read(in));}
    std::string invalid=source;invalid.replace(invalid.find("mouth 0"),7,"mouth 1");std::istringstream broken(invalid);assert(!read(broken));
    auto mutableBank=std::make_shared<Bank>();assert(!actor.bind(mutableBank));
    if(argc>=2){std::ofstream dump;if(argc==3){dump.open(argv[2]);dump<<std::setprecision(9);}std::ifstream file(argv[1]);auto real=read(file);assert(real&&checked(*real));auto id=actor.bind(real);size_t count=0;
        for(size_t c=0;c<real->clips.size();++c)for(int frame:real->clips[c].frames){assert(actor.sample(id,int(c),float(frame),Affine{},++count));assert(actor.socket(id,real->joint("kamu"),mouth));if(dump.is_open())for(size_t j=0;j<real->joints.size();++j){assert(actor.socket(id,int(j),mouth));dump<<c<<" "<<frame<<" "<<j;for(auto& row:mouth.m)for(float v:row)dump<<" "<<v;dump<<"\n";}}
        std::cout<<"REAL_BANK joints="<<real->joints.size()<<" samples="<<count<<"\n";}
    std::cout<<"PASS attachments: hierarchy, quaternion, isolation, pause/death, windows, dedupe, bounds, generations\n";
}
