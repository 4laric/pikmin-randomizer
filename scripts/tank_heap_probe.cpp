#include "tank_heap_probe.h"
#include "Shape.h"
#include "Mesh.h"
#include <cstdio>
#include <cstring>
#include <cstdint>
namespace {
struct Row {Shape* shape;const void* data;int size,heap;unsigned hash;bool submitted,reset;char name[192];};
Row rows[8192];int count=0;
unsigned hash(const void* ptr,int size){unsigned h=2166136261u;const unsigned char* p=(const unsigned char*)ptr;for(int i=0;i<size;++i){h^=p[i];h*=16777619u;}return h;}
}
void tank_diag_register(Shape* s,const char* name,int heap){
 if(!s)return;
 for(int i=0;i<s->mMeshCount;++i)for(int j=0;j<s->mMeshList[i].mMtxGroupCount;++j){auto& g=s->mMeshList[i].mMtxGroupList[j];for(int k=0;k<g.mDispLength;++k){auto& d=g.mDispList[k];if(count>=8192||d.mDataLength<0||d.mDataLength>16*1024*1024||!d.mData)continue;
 Row& r=rows[count++];r.shape=s;r.data=d.mData;r.size=d.mDataLength;r.heap=heap;r.hash=hash(r.data,r.size);r.submitted=false;r.reset=false;std::snprintf(r.name,sizeof(r.name),"%s",name);
 std::fprintf(stderr,"TANK_HEAP_LOAD row=%d shape=%p list=%p size=%d hash=%08x heap=%d name=%s\n",count-1,s,r.data,r.size,r.hash,heap,r.name);
 }}
}
void tank_diag_submit(Shape* s,const void* data,int size){
 for(int i=count-1;i>=0;--i){Row& r=rows[i];if(r.shape!=s||r.data!=data)continue;unsigned now=size>=0&&size<=16*1024*1024?hash(data,size):0;
 if(!r.submitted||now!=r.hash||r.reset){std::fprintf(stderr,"TANK_HEAP_DRAW row=%d shape=%p list=%p size=%d original=%08x now=%08x reset=%d name=%s\n",i,s,data,size,r.hash,now,r.reset,r.name);r.submitted=true;r.reset=false;r.hash=now;}return;}
}
void tank_diag_reset(int heap){std::fprintf(stderr,"TANK_HEAP_RESET heap=%d\n",heap);for(int i=0;i<count;++i)if(rows[i].heap==heap)rows[i].reset=true;}
