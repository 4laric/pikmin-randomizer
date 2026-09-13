#include "pc_p2_skin.h"
#include <cassert>
#include <fstream>
#include <iostream>
#include <iomanip>
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
    if(argc==4){std::ifstream joints(argv[1]),meshFile(argv[2]);auto bank=read(joints);auto mesh=p2skin::read(meshFile);assert(bank&&mesh);
        Instance instance,other;auto token=instance.bind(bank);auto otherToken=other.bind(bank);p2pose::Pose pose;pose.positions.resize(mesh->positions.size());pose.normals.resize(mesh->normals.size());
        std::ofstream dump(argv[3]);dump<<std::setprecision(9);uint64_t tick=0;
        for(size_t c=0;c<bank->clips.size();++c)for(int frame:bank->clips[c].frames){
            assert(instance.sample(token,c,float(frame),Affine{},++tick));assert(p2skin::deform(*mesh,instance,token,pose));
            dump<<bank->clips[c].name<<' '<<frame<<' '<<pose.positions.size()<<' '<<pose.normals.size()<<'\n';
            for(const auto& values:{pose.positions,pose.normals})for(auto v:values)dump<<v.x<<' '<<v.y<<' '<<v.z<<'\n';
        }
        assert(!p2skin::deform(*mesh,other,token,pose));assert(other.sample(otherToken,0,0,Affine{},1));assert(p2skin::deform(*mesh,other,otherToken,pose));
        instance.reset();assert(!p2skin::deform(*mesh,instance,token,pose));
        std::cout<<"REAL_SKIN samples="<<tick<<" positions="<<mesh->positions.size()<<" normals="<<mesh->normals.size()<<'\n';
    }
    std::cout<<"PASS skeletal deformation\n";
}
