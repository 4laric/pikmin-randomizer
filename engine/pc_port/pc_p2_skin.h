#pragma once
// CPU skeletal deformation for rigid bindings and weighted J3D draw palettes.
#include "pc_p2_attachments.h"
namespace p2skin {
constexpr size_t MaxElements=65536,MaxBytes=8*1024*1024;
struct Binding { size_t joint=0;p2attach::Vec value{0,0,0}; };
constexpr size_t MaxDraws=512,MaxInfluences=8;
struct Influence { size_t joint=0;float weight=0;p2attach::Affine inverse; };
struct Draw { std::vector<Influence> influences; };
struct Mesh { size_t joints=0;std::vector<Binding> positions,normals;std::vector<Draw> draws; };
inline bool normal(const p2attach::Affine&,p2attach::Vec,p2attach::Vec&);
inline std::shared_ptr<const Mesh> read(std::istream& input){
    std::string bytes;char c;while(input.get(c)){if(bytes.size()==MaxBytes)return {};bytes+=c;}
    if(!input.eof())return {};
    std::istringstream in(bytes);std::string magic;size_t p,n;auto mesh=std::make_shared<Mesh>();
    if(!(in>>magic>>mesh->joints>>p>>n)||(magic!="P2_SKIN_RIGID_1"&&magic!="P2_SKIN_WEIGHTED_1")||!mesh->joints||mesh->joints>p2attach::MaxJoints||!p||!n||p>MaxElements||n>MaxElements)return {};
    size_t bindings=mesh->joints;
    if(magic=="P2_SKIN_WEIGHTED_1"){
        if(!(in>>bindings)||!bindings||bindings>MaxDraws)return {};
        mesh->draws.resize(bindings);
        for(auto& draw:mesh->draws){size_t count;if(!(in>>count)||!count||count>MaxInfluences)return {};
            draw.influences.resize(count);double sum=0;std::set<size_t> seen;
            for(auto& v:draw.influences){
                if(!(in>>v.joint>>v.weight)||v.joint>=mesh->joints||!seen.insert(v.joint).second||!std::isfinite(v.weight)||v.weight<0||v.weight>1)return {};
                sum+=v.weight;
                for(auto& row:v.inverse.m)for(float& x:row)if(!(in>>x)||!std::isfinite(x)||std::fabs(x)>1e6f)return {};
                p2attach::Vec ignored;if(!normal(v.inverse,{1,0,0},ignored))return {};
            }
            if(std::fabs(sum-1)>1e-4)return {};
        }
    }
    for(int array=0;array<2;++array){
        auto& values=array==0?mesh->positions:mesh->normals;values.resize(array==0?p:n);
        for(auto& b:values){if(!(in>>b.joint>>b.value.x>>b.value.y>>b.value.z)||b.joint>=bindings)return {};
            for(float v:{b.value.x,b.value.y,b.value.z})if(!std::isfinite(v)||std::fabs(v)>1e6f)return {};}
    }
    if(in>>magic)return {};
    return mesh;
}
inline bool normal(const p2attach::Affine& m,p2attach::Vec v,p2attach::Vec& out){
    const float a=m.m[0][0],b=m.m[0][1],c=m.m[0][2],d=m.m[1][0],e=m.m[1][1],f=m.m[1][2],g=m.m[2][0],h=m.m[2][1],i=m.m[2][2];
    const float cof[3][3]={{e*i-f*h,f*g-d*i,d*h-e*g},{c*h-b*i,a*i-c*g,b*g-a*h},{b*f-c*e,c*d-a*f,a*e-b*d}};
    const float det=a*cof[0][0]+b*cof[0][1]+c*cof[0][2];
    if(!std::isfinite(det)||std::fabs(det)<1e-12f)return false;
    p2attach::Vec raw{(cof[0][0]*v.x+cof[0][1]*v.y+cof[0][2]*v.z)/det,(cof[1][0]*v.x+cof[1][1]*v.y+cof[1][2]*v.z)/det,(cof[2][0]*v.x+cof[2][1]*v.y+cof[2][2]*v.z)/det};
    return p2pose::unit(raw,out);
}
// Caller preallocates output and samples the skeleton in model space once.
// On failure output must not be rendered; caller publishes only on success.
inline bool deform(const Mesh& mesh,const p2attach::Instance& instance,uint64_t token,p2pose::Pose& out){
    if(out.positions.size()!=mesh.positions.size()||out.normals.size()!=mesh.normals.size())return false;
    std::array<p2attach::Affine,p2attach::MaxJoints> matrices;
    if(!mesh.joints||mesh.joints>matrices.size())return false;
    for(size_t j=0;j<mesh.joints;++j)if(!instance.socket(token,j,matrices[j]))return false;
    std::array<p2attach::Affine,MaxDraws> palette;
    size_t count=mesh.joints;
    if(mesh.draws.empty()){for(size_t j=0;j<count;++j)palette[j]=matrices[j];}
    else{count=mesh.draws.size();if(count>MaxDraws)return false;
        for(size_t j=0;j<count;++j){auto& result=palette[j];for(auto& row:result.m)for(float& x:row)x=0;
            if(mesh.draws[j].influences.empty()||mesh.draws[j].influences.size()>MaxInfluences)return false;
            for(const auto& v:mesh.draws[j].influences){if(v.joint>=mesh.joints||!std::isfinite(v.weight))return false;
                const auto m=p2attach::compose(matrices[v.joint],v.inverse);
                for(int r=0;r<3;++r)for(int c=0;c<4;++c)result.m[r][c]+=v.weight*m.m[r][c];
            }
            if(!p2attach::valid(result))return false;
        }
    }
    for(size_t k=0;k<mesh.positions.size();++k){const auto& b=mesh.positions[k];if(b.joint>=count)return false;
        out.positions[k]=p2attach::point(palette[b.joint],b.value);
        const auto& v=out.positions[k];if(!std::isfinite(v.x)||!std::isfinite(v.y)||!std::isfinite(v.z))return false;}
    for(size_t k=0;k<mesh.normals.size();++k){const auto& b=mesh.normals[k];if(b.joint>=count||!normal(palette[b.joint],b.value,out.normals[k]))return false;}
    return true;
}
}
