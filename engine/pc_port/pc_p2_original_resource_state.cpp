#include "pc_p2_original_resource_state.h"
#include <climits>
#include <tuple>
namespace p2originalresource { namespace {
int index(HoneyKind kind){return kind==HoneyKind::Spicy?0:kind==HoneyKind::Bitter?1:-1;}
bool fail(std::string& e,const char* why){e=why;return false;}
bool bornSpray(const SprayCompletion& event,const EggContents& contents){
 if(!event.child.ancestry.empty()||!validChildIdentity(event.child)||event.captain>1||index(event.kind)<0)return false;
 for(const auto& record:contents.snapshot())if(record.source==event.child.source&&record.complete)
  for(const auto& child:record.children)if(child.identity==event.child&&child.born&&child.attempted)
   return child.kind==(event.kind==HoneyKind::Spicy?ChildKind::Spicy:ChildKind::Bitter);
 return false;
}
}
bool SprayCompletion::operator<(const SprayCompletion& b)const {
 return std::tie(child,captain)<std::tie(b.child,b.captain);
}
bool ResourceState::restore(const ResourceSnapshot& state,const EggContents& contents,std::string& e){
 if(state.version!=1||state.completed.size()>4096||state.sprayCounts[0]<0||state.sprayCounts[1]<0||state.berryCounts[0]<0||state.berryCounts[1]<0||state.sprayUses[0]<0||state.sprayUses[1]<0)return fail(e,"original resource snapshot bounds invalid");
 std::set<SprayCompletion> events;
 for(const auto& event:state.completed)if(!bornSpray(event,contents)||!events.insert(event).second)return fail(e,"original spray completion absent/mismatched/duplicate");
 mState=state;mCompleted=std::move(events);mReady=true;e.clear();return true;
}
bool ResourceState::snapshot(ResourceSnapshot& out,std::string& e)const{
 if(!mReady)return fail(e,"original resource campaign state uninstalled");
 out=mState;out.completed.assign(mCompleted.begin(),mCompleted.end());e.clear();return true;
}
bool ResourceState::sprayMade(HoneyKind kind)const{int i=index(kind);return mReady&&i>=0&&mState.sprayMade[i];}
int ResourceState::sprayCount(HoneyKind kind)const{int i=index(kind);return mReady&&i>=0?mState.sprayCounts[i]:0;}
bool ResourceState::completeSpray(const ChildIdentity& child,HoneyKind kind,unsigned captain,const EggContents& contents,std::string& e){
 if(!mReady)return fail(e,"original resource campaign state uninstalled");
 SprayCompletion event{child,kind,captain};if(!bornSpray(event,contents))return fail(e,"original spray END is not a born source child/captain");
 auto previous=mCompleted.find(event);if(previous!=mCompleted.end()){if(previous->kind!=kind)return fail(e,"original spray END kind mismatch");e.clear();return true;}
 int i=index(kind);if(mState.sprayCounts[i]==INT_MAX)return fail(e,"original spray counter overflow");
 mCompleted.insert(event);++mState.sprayCounts[i];e.clear();return true;
}
bool ResourceState::useSpray(HoneyKind kind,std::string& e){
 int i=index(kind);if(!mReady||i<0||mState.sprayCounts[i]<=0)return fail(e,"original source spray unavailable");
 if(mState.sprayUses[i]==INT_MAX)return fail(e,"original spray use counter overflow");
 --mState.sprayCounts[i];++mState.sprayUses[i];e.clear();return true;
}
bool ResourceState::markSprayMade(HoneyKind kind,std::string& e){
 int i=index(kind);if(!mReady||i<0)return fail(e,"original spray crafting state uninstalled/invalid");
 mState.sprayMade[i]=true;e.clear();return true;
}
bool ResourceState::addBerry(HoneyKind kind,int count,int threshold,std::string& e){
 int i=index(kind);if(!mReady||i<0||count<=0||threshold<=0)return fail(e,"original berry production lacks actual state/threshold");
 const std::uint64_t current=static_cast<unsigned>(mState.berryCounts[i]),n=static_cast<unsigned>(count),t=static_cast<unsigned>(threshold);
 // A changed source parameter below an inherited remainder clears the whole
 // remainder on the first production, matching literal addDopeFruit.
 std::uint64_t produced=current>=t?1+(n-1)/t:(current+n)/t;
 std::uint64_t remainder=current>=t?(n-1)%t:(current+n)%t;
 if(produced>static_cast<unsigned>(INT_MAX-mState.sprayCounts[i]))return fail(e,"original berry spray counter overflow");
 mState.sprayCounts[i]+=static_cast<int>(produced);mState.berryCounts[i]=static_cast<int>(remainder);e.clear();return true;
}
}
