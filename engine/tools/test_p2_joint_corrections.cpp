#include "pc_p2_skin.h"
#include <cassert>
#include <fstream>
#include <iostream>
#include <iomanip>
using namespace p2attach;
static bool near(float a,float b){return std::fabs(a-b)<1e-4f;}
int main(int argc,char** argv){
    auto bank=std::make_shared<Bank>();bank->joints={{"root",-1},{"aim",0},{"tip",1},{"sibling",0}};
    Clip clip;clip.name="idle";clip.duration=1;clip.frames={0};clip.samples.resize(4);
    clip.samples[1].translation={2,0,0};clip.samples[2].translation={3,0,0};clip.samples[3].translation={0,5,0};bank->clips.push_back(clip);
    Instance actor,other;auto token=actor.bind(bank),otherToken=other.bind(bank);assert(token&&otherToken);
    TRS rotation;rotation.rotation={0,0,.707106781f,.707106781f};JointCorrection correction{1,matrix(rotation)};
    Affine socket;uint64_t tick=0;
    for(int i=0;i<100;++i){assert(actor.sample(token,0,0,Affine{},++tick,false,false,&correction,1));assert(actor.socket(token,2,socket));assert(near(socket.m[0][3],2)&&near(socket.m[1][3],3));}
    assert(actor.socket(token,3,socket)&&near(socket.m[0][3],0)&&near(socket.m[1][3],5));
    assert(other.sample(otherToken,0,0,Affine{},1)&&other.socket(otherToken,2,socket)&&near(socket.m[0][3],5));
    Affine ownerWorld;ownerWorld.m[0][3]=7;
    assert(actor.sample(token,0,0,ownerWorld,++tick,false,false,&correction,1)&&actor.socket(token,2,socket)&&near(socket.m[0][3],9));
    JointCorrection pair[2]={{2,Affine{}},correction};pair[0].delta.m[0][3]=1;
    assert(actor.sample(token,0,0,Affine{},++tick,false,false,pair,2)&&actor.socket(token,2,socket)&&near(socket.m[1][3],4));
    assert(actor.sample(token,0,0,Affine{},++tick,false,false,&correction,1));
    p2skin::Mesh mesh;mesh.joints=4;mesh.positions={{2,{1,0,0}}};mesh.normals={{2,{1,0,0}}};p2pose::Pose pose;pose.positions.resize(1);pose.normals.resize(1);
    assert(p2skin::deform(mesh,actor,token,pose)&&near(pose.positions[0].x,2)&&near(pose.positions[0].y,4));
    DamageVolume volume;assert(volume.contact(actor,token,1,0,2,{1,0,0},.1f,0,1,900,{2,4,0}));
    assert(!volume.contact(actor,token,2,0,2,{1,0,0},.1f,0,1,901,{6,0,0}));
    mesh.draws={p2skin::Draw{{{1,.5f,Affine{}},{2,.5f,Affine{}}}}};mesh.positions[0].joint=mesh.normals[0].joint=0;
    assert(p2skin::deform(mesh,actor,token,pose)&&near(pose.positions[0].x,2)&&near(pose.positions[0].y,2.5));
    assert(actor.sample(token,0,0,Affine{},++tick,true,false,nullptr,999)&&actor.socket(token,2,socket)&&near(socket.m[1][3],3)&&!actor.active(token));
    assert(actor.sample(token,0,0,Affine{},++tick)&&actor.socket(token,2,socket)&&near(socket.m[0][3],5));
    JointCorrection duplicate[2]={correction,correction};
    assert(!actor.sample(token,0,0,Affine{},++tick,false,false,duplicate,2)&&!actor.socket(token,2,socket));
    JointCorrection invalid=correction;invalid.joint=4;assert(!actor.sample(token,0,0,Affine{},++tick,false,false,&invalid,1));
    invalid=correction;invalid.delta.m[0][0]=NAN;assert(!actor.sample(token,0,0,Affine{},++tick,false,false,&invalid,1));
    invalid=correction;for(float& v:invalid.delta.m[0])v=0;assert(!actor.sample(token,0,0,Affine{},++tick,false,false,&invalid,1));
    assert(!actor.sample(token,0,0,Affine{},++tick,false,false,nullptr,1));
    invalid=JointCorrection{1,Affine{}};invalid.delta.m[0][0]=1e9f;
    assert(!actor.sample(token,0,0,Affine{},++tick,false,false,&invalid,1)&&!actor.socket(token,1,socket));
    assert(actor.sample(token,0,0,Affine{},++tick,false,false,&correction,1));
    assert(!actor.sample(otherToken,0,0,Affine{},++tick)&&actor.socket(token,2,socket)&&near(socket.m[1][3],3));
    assert(actor.sample(token,0,0,Affine{},++tick,false,true)&&!actor.socket(token,2,socket));actor.reset();assert(!actor.sample(token,0,0,Affine{},++tick));
    if(argc==4){std::ifstream jf(argv[1]),mf(argv[2]);auto real=read(jf);auto skin=p2skin::read(mf);assert(real&&skin);
        Instance instance;auto owner=instance.bind(real);TRS aim;aim.rotation={0,.382683432f,0,.923879533f};JointCorrection delta{real->joint("kuti"),matrix(aim)};assert(delta.joint>=0);
        p2pose::Pose output;output.positions.resize(skin->positions.size());output.normals.resize(skin->normals.size());std::ofstream dump(argv[3]);dump<<std::setprecision(9);uint64_t steps=0;
        for(size_t c=0;c<real->clips.size();++c)for(int frame:real->clips[c].frames){
            assert(instance.sample(owner,c,float(frame),Affine{},++steps,false,false,&delta,1)&&p2skin::deform(*skin,instance,owner,output));
            dump<<real->clips[c].name<<' '<<frame<<' '<<output.positions.size()<<' '<<output.normals.size()<<'\n';
            for(const auto& values:{output.positions,output.normals})for(auto v:values)dump<<v.x<<' '<<v.y<<' '<<v.z<<'\n';
            Affine muzzle;assert(instance.socket(owner,delta.joint,muzzle));dump<<"socket";for(auto& row:muzzle.m)for(float v:row)dump<<' '<<v;dump<<'\n';
        }
        std::cout<<"CORRECTED_GROINK frames="<<steps<<" joint="<<delta.joint<<'\n';
    }
    std::cout<<"PASS joint corrections\n";
}
