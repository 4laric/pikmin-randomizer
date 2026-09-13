#include "pc_p2_crossfade.h"
#include "pc_p2_skin.h"
#include <cassert>
#include <iostream>
using namespace p2attach;
static bool near(float a,float b){return std::fabs(a-b)<.0001f;}
int main(){
    auto bank=std::make_shared<Bank>();bank->joints={{"root",-1},{"child",0}};
    Clip a;a.name="idle";a.duration=1;a.frames={0};a.samples.resize(2);a.samples[1].translation={2,0,0};
    Clip b=a;b.name="walk";b.samples[0].translation={10,0,0};b.samples[0].rotation={0,0,1,0};
    Clip c=a;c.name="attack";c.samples[0].translation={20,0,0};bank->clips={a,b,c};
    Instance actor,other;auto token=actor.bind(bank),ot=other.bind(bank);Crossfade fade;
    auto sample=[&](int clip,bool snap=false){assert(fade.sample(actor,token,clip,0,Affine{},1,.15f,snap));};
    auto x=[&](){Affine out;assert(actor.socket(token,1,out));return out.m[0][3];};
    sample(0);assert(near(x(),2));sample(1);assert(fade.weight()==0&&near(x(),2));
    assert(fade.advance(.075f));sample(1);assert(near(fade.weight(),.5f)&&near(x(),5));
    Affine out;assert(actor.socket(token,1,out)&&near(out.m[1][3],2));
    // Weighted skin and sockets use the same blended hierarchy.
    p2skin::Mesh mesh;mesh.joints=2;mesh.positions={{0,{0,0,0}}};mesh.normals={{0,{1,0,0}}};
    mesh.draws={p2skin::Draw{{{0,.5f,Affine{}},{1,.5f,Affine{}}}}};p2pose::Pose pose;pose.positions.resize(1);pose.normals.resize(1);
    assert(p2skin::deform(mesh,actor,token,pose)&&near(pose.positions[0].x,5)&&near(pose.positions[0].y,1));
    // A duplicate render does not advance time; pause and invalid deltas do not either.
    sample(1);assert(near(x(),5));assert(fade.advance(1,true));sample(1);assert(near(x(),5));
    assert(!fade.advance(NAN)&&!fade.advance(-1));sample(1);assert(near(x(),5));
    // Interrupt exactly at the last displayed blend, then reach the new endpoint.
    sample(2);assert(fade.weight()==0&&near(x(),5));assert(fade.advance(.15f));sample(2);assert(fade.weight()==1&&near(x(),22));
    sample(0,true);assert(near(x(),2));
    assert(other.sample(ot,1,0,Affine{},1)&&other.socket(ot,1,out)&&near(out.m[0][3],8));assert(near(x(),2));
    Instance::Pose frozen;assert(actor.capture(token,frozen));
    auto blend=[&](float w,const Instance::Pose* source){return actor.sample(token,1,0,Affine{},1,false,false,nullptr,0,source,w);};
    assert(blend(0,&frozen)&&near(x(),2));assert(blend(1,&frozen)&&near(x(),8));
    assert(!blend(NAN,&frozen));assert(!blend(-.1f,&frozen));assert(!blend(1.1f,&frozen));
    auto invalid=frozen;invalid.count=MaxJoints+1;assert(!blend(.5f,&invalid));invalid=frozen;invalid.joints[0].scale.x=0;assert(!blend(.5f,&invalid));
    invalid=frozen;invalid.joints[0].rotation.w=0;assert(!blend(.5f,&invalid));invalid=frozen;invalid.joints[0].translation.x=NAN;assert(!blend(.5f,&invalid));
    assert(!other.sample(ot,1,0,Affine{},1,false,false,nullptr,0,&frozen,.5f));
    // Corrections are applied once after blending; capture excludes them.
    JointCorrection correction{1,Affine{}};correction.delta.m[0][3]=3;
    assert(actor.sample(token,1,0,Affine{},1,false,false,&correction,1,&frozen,0)&&near(x(),5));
    Instance::Pose corrected;assert(actor.capture(token,corrected));assert(blend(0,&corrected)&&near(x(),2));
    // Antipodal quaternions take the shortest path, with scale/translation lerp.
    invalid=frozen;invalid.joints[0].rotation.w=-1;invalid.joints[0].scale={3,3,3};
    assert(actor.sample(token,0,0,Affine{},1,false,false,nullptr,0,&invalid,.5f)&&near(x(),4));
    assert(actor.sample(token,0,0,Affine{},1,true)&&!actor.active(token));
    assert(actor.sample(token,0,0,Affine{},1,false,true)&&!actor.capture(token,frozen));
    token=actor.bind(bank);assert(!blend(0,&corrected));sample(0);assert(near(x(),2));
    actor.reset();assert(!actor.capture(token,frozen));
    std::cout<<"PASS skeletal crossfade\n";
}
