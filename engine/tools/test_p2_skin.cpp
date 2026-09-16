#include "pc_p2_skin.h"
#include <cassert>
#include <fstream>
#include <iostream>
#include <iomanip>
#include <chrono>
int main(int argc,char** argv){
    using namespace p2attach;
    Vec out;Affine a;a.m[0][0]=2;a.m[1][1]=3;
    assert(p2skin::normal(a,{1,1,0},out));assert(std::fabs(out.x-.8320503f)<1e-5);
    a.m[2][2]=0;assert(!p2skin::normal(a,{0,1,0},out));
    for(const char* bad:{"P2_SKIN_RIGID_1 0 1 1", "P2_SKIN_RIGID_1 1 999999999 1", "P2_SKIN_RIGID_1 1 1 1 2 0 0 0 0 0 1 0", "P2_SKIN_RIGID_1 1 1 1 0 nan 0 0 0 0 1 0"}){std::istringstream in(bad);assert(!p2skin::read(in));}
    auto synthetic=std::make_shared<Bank>();synthetic->joints.push_back({"root",-1});
    Clip motion;motion.name="turn";motion.duration=3;motion.frames={0,2};TRS left,right;
    right.rotation={0,0,.707106781f,.707106781f};motion.samples={left,right};synthetic->clips.push_back(motion);
    Instance midpoint;auto midToken=midpoint.bind(synthetic);assert(midToken);
    p2skin::Mesh syntheticMesh;syntheticMesh.joints=1;syntheticMesh.positions.push_back({0,{1,0,0}});syntheticMesh.normals.push_back({0,{1,0,0}});
    p2pose::Pose mid;mid.positions.resize(1);mid.normals.resize(1);
    assert(midpoint.sample(midToken,0,1,Affine{},1)&&p2skin::deform(syntheticMesh,midpoint,midToken,mid));
    assert(std::fabs(mid.positions[0].x-.707106781f)<1e-5&&std::fabs(mid.positions[0].y-.707106781f)<1e-5);
    assert(midpoint.sample(midToken,0,2,Affine{},2,true)&&p2skin::deform(syntheticMesh,midpoint,midToken,mid));
    assert(std::fabs(mid.positions[0].x-.707106781f)<1e-5);
    assert(midpoint.sample(midToken,0,2,Affine{},3,false,true)&&!p2skin::deform(syntheticMesh,midpoint,midToken,mid));
    // Distinct inverse binds must be composed inside the influence sum.
    auto weightedBank=std::make_shared<Bank>();weightedBank->joints={{"a",-1},{"b",-1}};
    Clip wc;wc.name="wait";wc.duration=1;wc.frames={0};TRS second;second.translation={8,0,0};second.scale={2,1,1};wc.samples={TRS{},second};weightedBank->clips.push_back(wc);
    const std::string prefix="P2_SKIN_WEIGHTED_1 2 1 1 1 2 0 ";
    const std::string identity=" 1 0 0 0 0 1 0 0 0 0 1 0 ";
    const std::string inverse=" 1 0 0 -2 0 1 0 0 0 0 1 0 ";
    const std::string valid=prefix+"0.25"+identity+"1 0.75"+inverse+"0 1 0 0 0 1 1 0";
    std::istringstream weightedInput(valid);auto weightedMesh=p2skin::read(weightedInput);assert(weightedMesh);
    Instance wi;auto wt=wi.bind(weightedBank);assert(wi.sample(wt,0,0,Affine{},1));
    p2pose::Pose wp;wp.positions.resize(1);wp.normals.resize(1);assert(p2skin::deform(*weightedMesh,wi,wt,wp));
    assert(std::fabs(wp.positions[0].x-4.75f)<1e-5);
    assert(std::fabs(wp.normals[0].x-1/std::sqrt(1+1.75f*1.75f))<1e-5);
    for(const auto& bad:{prefix+"-0.25"+identity+"1 1.25"+inverse+"0 1 0 0 0 1 1 0",
        prefix+"0.25"+identity+"1 0.5"+inverse+"0 1 0 0 0 1 1 0",
        prefix+"0.25"+identity+"0 0.75"+inverse+"0 1 0 0 0 1 1 0",
        prefix+"nan"+identity+"1 0.75"+inverse+"0 1 0 0 0 1 1 0",
        valid+" extra",std::string("P2_SKIN_WEIGHTED_1 2 1 1 513")}){std::istringstream input(bad);assert(!p2skin::read(input));}
    const std::string singularInverse=" 0 0 0 0 0 1 0 0 0 0 1 0 ";
    for(const auto& bad:{prefix+"0.25"+identity+"2 0.75"+inverse+"0 1 0 0 0 1 1 0",
        prefix+"0.25"+identity+"1 0.75"+singularInverse+"0 1 0 0 0 1 1 0"}){std::istringstream input(bad);assert(!p2skin::read(input));}
    auto cancelBank=std::make_shared<Bank>(*weightedBank);cancelBank->clips[0].samples[1]=TRS{};cancelBank->clips[0].samples[1].rotation={0,0,1,0};
    std::istringstream cancelInput(prefix+"0.5"+identity+"1 0.5"+identity+"0 1 0 0 0 1 1 0");auto cancelMesh=p2skin::read(cancelInput);assert(cancelMesh);
    Instance cancel;auto cancelToken=cancel.bind(cancelBank);assert(cancel.sample(cancelToken,0,0,Affine{},1));assert(!p2skin::deform(*cancelMesh,cancel,cancelToken,wp));
    if(argc==4){std::ifstream joints(argv[1]),meshFile(argv[2]);auto bank=read(joints);auto mesh=p2skin::read(meshFile);assert(bank&&mesh);
        Instance instance,other;auto token=instance.bind(bank);auto otherToken=other.bind(bank);p2pose::Pose pose;pose.positions.resize(mesh->positions.size());pose.normals.resize(mesh->normals.size());
        std::ofstream dump(argv[3]);dump<<std::setprecision(9);uint64_t tick=0;
        for(size_t c=0;c<bank->clips.size();++c)for(int frame:bank->clips[c].frames){
            assert(instance.sample(token,c,float(frame),Affine{},++tick));assert(p2skin::deform(*mesh,instance,token,pose));
            dump<<bank->clips[c].name<<' '<<frame<<' '<<pose.positions.size()<<' '<<pose.normals.size()<<'\n';
            for(const auto& values:{pose.positions,pose.normals})for(auto v:values)dump<<v.x<<' '<<v.y<<' '<<v.z<<'\n';
        }
        assert(!p2skin::deform(*mesh,other,token,pose));assert(other.sample(otherToken,0,0,Affine{},1));assert(p2skin::deform(*mesh,other,otherToken,pose));
        const auto start=std::chrono::steady_clock::now();
        for(int i=0;i<10000;++i){assert(instance.sample(token,0,float(i%bank->clips[0].duration),Affine{},++tick));assert(p2skin::deform(*mesh,instance,token,pose));}
        std::cout<<"CPU_SKIN iterations=10000 milliseconds="<<std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-start).count()<<'\n';
        instance.reset();assert(!p2skin::deform(*mesh,instance,token,pose));
        std::cout<<"REAL_SKIN samples="<<(tick-10000)<<" positions="<<mesh->positions.size()<<" normals="<<mesh->normals.size()<<'\n';
    }
    std::cout<<"PASS skeletal deformation\n";
}
