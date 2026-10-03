#pragma once
#include "pc_midday_render_graph.h"
class BaseShape;
namespace pc_midday {
// Registry of installed asset factories. Model/slot inputs are source-owned
// content identities supplied by the complete scene catalog, never saved pointers.
class RenderDescriptorIndex {
 struct Entry {RenderKind kind;BaseShape* model;std::vector<u32> materialSlots;bool fullTevArray=false;};
 std::map<u64,Entry> entries_;
public:
 bool declare(u64 factory,RenderKind,BaseShape&,const std::vector<u32>& slots,std::string&);
 // Source-owned complete loaded model TEV allocation, including unused entries.
 bool declareTevArray(u64 factory,BaseShape&,std::string&);
 bool validate(const RenderGraph&,std::string&)const;
 bool matchesInitializedBacking(const RenderGraph&,const IsolatedRenderAllocations&,const ConstructorFence&,std::string&)const;
 bool validateStateGeometry(const RenderNode&,u32,const ActorFields&,std::string&)const;
 // Only immutable named descriptor backing and canonical allocation pointers.
 // Mutable payload bind/typed prevalidation is still a separate mandatory pass.
 bool initializeBacking(const RenderGraph&,IsolatedRenderAllocations&,ConstructorFence&,std::string&)const;
};
}
