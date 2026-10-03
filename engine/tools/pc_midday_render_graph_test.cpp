#include "pc_midday_render_graph.h"
#include <cstdio>
#include <limits>
using namespace pc_midday;
namespace {int checks=0,failed=0;void check(bool b,const char* s){++checks;if(!b){++failed;std::printf("FAIL %s\n",s);}}}
int main(){
 std::string e;RenderGraph graph;
 std::vector<RenderObservation> source{{1,101,RenderKind::Materials,2,1000,80},{2,102,RenderKind::Tev,1,2000,90},{3,103,RenderKind::Tev,1,3000,90},{4,104,RenderKind::Textures,3,4000,100}};
 std::vector<RenderLink> links{{1,0,true,2,4,3},{1,1,true,3,4,3}};
 check(planRenderGraph(7,source,links,{1,2,3,4},graph,e)&&graph.nodes.size()==4&&graph.links.size()==2,"canonical cloned TEV and shared texture array inventory");
 check(graph.links[0].tev!=graph.links[1].tev&&graph.links[0].textures==graph.links[1].textures,"distinct TEV allocation and preserved shared texture alias");
 check(graph.generation==7&&graph.nodes[3].count==3&&graph.nodes[3].factory==104,"generation/factory/count retained without source addresses");
 auto bad=source;bad[3].address=source[0].address;check(!planRenderGraph(7,bad,links,{1,2,3,4},graph,e)&&graph.generation==7&&graph.nodes.size()==4,"duplicate physical allocation refuses transactionally");
 bad=source;bad[3].address=1001;check(!planRenderGraph(7,bad,links,{1,2,3,4},graph,e),"interior overlapping allocation refused");
 bad=source;bad[0].address=4001;check(!planRenderGraph(7,bad,links,{1,2,3,4},graph,e),"reverse order overlapping allocation refused");
 bad=source;bad[3].address=1160;check(planRenderGraph(7,bad,links,{1,2,3,4},graph,e),"adjacent distinct allocation allowed");
 bad=source;bad[3].count=2;check(!planRenderGraph(7,bad,links,{1,2,3,4},graph,e),"shared array count mismatch refused");
 bad=source;bad[2].kind=RenderKind::Textures;check(!planRenderGraph(7,bad,links,{1,2,3,4},graph,e),"TEV target concrete kind mismatch refused");
 bad=source;bad[1].count=2;check(planRenderGraph(7,bad,links,{1,2,3,4},graph,e),"TEV allocation captures all initialized array entries");
 bad=source;bad[3].count=257;check(!planRenderGraph(7,bad,links,{1,2,3,4},graph,e),"compiled maximum texture count enforced");
 bad=source;bad[0].count=0;check(!planRenderGraph(7,bad,links,{1,2,3,4},graph,e),"empty allocation has no canonical native identity");
 bad=source;bad[2].id=2;check(!planRenderGraph(7,bad,links,{1,2,3,4},graph,e),"duplicate canonical ID refused");
 bad=source;bad[2].id=0;check(!planRenderGraph(7,bad,links,{1,2,3,4},graph,e),"zero canonical ID refused");
 bad=source;bad[2].factory=0;check(!planRenderGraph(7,bad,links,{1,2,3,4},graph,e),"missing installed factory identity refused");
 bad=source;bad[2].address=0;check(!planRenderGraph(7,bad,links,{1,2,3,4},graph,e),"null allocation refused");
 bad=source;bad[2].elementSize=0;check(!planRenderGraph(7,bad,links,{1,2,3,4},graph,e),"zero element span refused");
 bad=source;bad[3].elementSize=std::numeric_limits<size_t>::max();check(!planRenderGraph(7,bad,links,{1,2,3,4},graph,e),"size multiplication overflow refused");
 bad=source;bad[2].address=std::numeric_limits<uintptr_t>::max()-1;check(!planRenderGraph(7,bad,links,{1,2,3,4},graph,e),"address addition overflow refused");
 bad=source;bad[2].kind=static_cast<RenderKind>(255);check(!planRenderGraph(7,bad,links,{1,2,3,4},graph,e),"unknown concrete render kind refused");
 check(!planRenderGraph(0,source,links,{1,2,3,4},graph,e),"zero world epoch refused");
 check(!planRenderGraph(7,source,links,{1,2,3},graph,e),"foreign allocation not admitted by authoritative inventory");
 check(!planRenderGraph(7,source,links,{1,2,3,4,5},graph,e),"omitted authoritative allocation refused");
 check(!planRenderGraph(7,source,links,{0,1,2,3,4},graph,e),"invalid required inventory refused");
 auto wrong=links;wrong.pop_back();check(!planRenderGraph(7,source,wrong,{1,2,3,4},graph,e),"omitted material consumer refused");
 wrong=links;wrong[1].slot=0;check(!planRenderGraph(7,source,wrong,{1,2,3,4},graph,e),"duplicate material slot refused");
 wrong=links;wrong[1].slot=2;check(!planRenderGraph(7,source,wrong,{1,2,3,4},graph,e),"foreign material slot refused");
 wrong=links;wrong[1].materials=2;check(!planRenderGraph(7,source,wrong,{1,2,3,4},graph,e),"wrong material container kind refused");
 wrong=links;wrong[1].tev=99;check(!planRenderGraph(7,source,wrong,{1,2,3,4},graph,e),"missing TEV target refused");
 wrong=links;wrong[1].textures=99;check(!planRenderGraph(7,source,wrong,{1,2,3,4},graph,e),"missing texture target refused");
 wrong=links;wrong[1].textureCount=0;check(!planRenderGraph(7,source,wrong,{1,2,3,4},graph,e),"empty array cannot carry identity");
 wrong=links;wrong[1].textures=0;check(!planRenderGraph(7,source,wrong,{1,2,3,4},graph,e),"nonempty array requires identity");
 wrong=links;wrong[1].tev=2;check(!planRenderGraph(7,source,wrong,{1,2,3,4},graph,e),"unreachable cloned TEV refuses instead of silently dropping");
 wrong=links;wrong[1].pvw=false;check(!planRenderGraph(7,source,wrong,{1,2,3,4},graph,e),"non-PVW storage is never inspected");
 check(planRenderGraph(8,{{1,101,RenderKind::Materials,1,1000,80}},{{1,0,false,0,0,0}},{1},graph,e)&&graph.generation==8,"non-PVW-only graph has no invented PVW nodes");
 check(planRenderGraph(9,{}, {}, {},graph,e)&&graph.nodes.empty(),"complete legitimately empty resource graph");
 // The model owns one array; unused initialized elements remain in its payload.
 auto array=source;array.erase(array.begin()+2);array[1].count=3;array[1].contentRoot=true;
 auto arrayLinks=links;arrayLinks[1].tev=2;arrayLinks[1].tevSlot=2;
 check(planRenderGraph(10,array,arrayLinks,{1,2,4},graph,e)&&graph.nodes[1].count==3&&graph.nodes[1].contentRoot&&graph.links[1].tevSlot==2,"whole TEV array and nonzero element link preserved");
 auto arrayBad=arrayLinks;arrayBad[1].tevSlot=3;check(!planRenderGraph(10,array,arrayBad,{1,2,4},graph,e)&&graph.links[1].tevSlot==2,"one-past array slot refuses transactionally");
 arrayBad=arrayLinks;arrayBad[0].tevSlot=1;check(planRenderGraph(10,array,arrayBad,{1,2,4},graph,e),"unused and shared TEV array elements are legal typed inventory");
 auto rootOnly=array;rootOnly.erase(rootOnly.begin());rootOnly.pop_back();check(planRenderGraph(10,rootOnly,{}, {2},graph,e)&&graph.nodes[0].count==3,"registered prototype allocation remains captured without material consumer");
 rootOnly[0].contentRoot=false;check(!planRenderGraph(10,rootOnly,{}, {2},graph,e),"unregistered unreachable array remains refused");
 array[0].contentRoot=true;check(!planRenderGraph(10,array,arrayLinks,{1,2,4},graph,e),"material cannot forge full TEV content-root class");
 arrayBad={{1,0,false,0,0,0,1}};check(!planRenderGraph(10,{{1,101,RenderKind::Materials,1,1000,80}},arrayBad,{1},graph,e),"non-PVW cannot carry latent TEV slot");
 std::printf("%d checks, %d failures\n",checks,failed);return failed?1:0;
}
