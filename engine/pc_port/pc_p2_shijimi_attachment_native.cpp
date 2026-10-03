#include "pc_p2_shijimi_attachment_native.h"
#include "Creature.h"
#include "Piki.h"
#include <set>
namespace p2original { namespace shijimi {
bool captureGenPikiStickers(Creature* source,CollPart* part,const AttachmentAuthority& authority,std::vector<LiveGenPikiAttachment>& out,std::string& e){
 if(!source||!part){e="source77 attachment capture requires actual owned body and stickable part";return false;}
 std::vector<LiveGenPikiAttachment> next;std::set<Creature*> seen;
 for(auto* sticker=source->mStickListHead;sticker;sticker=sticker->mNextSticker){
  if(!seen.insert(sticker).second||seen.size()>100||!sticker->isPiki()||sticker->mStickTarget!=source||sticker->mStickPart!=part){e="source77 actual sticker topology/provenance unsupported";return false;}
  LiveGenPikiAttachment entry;const auto local=sticker->mAttachPosition;
  if(!captureAttachment(static_cast<Piki*>(sticker),{local.x,local.y,local.z},authority,entry,e))return false;
  next.push_back(std::move(entry));
 }
 // Re-read topology and incarnation after source-authority callbacks. Output
 // stays unchanged if any sticker disappeared, changed parent/part or reused.
 std::size_t n=0;for(auto* sticker=source->mStickListHead;sticker;sticker=sticker->mNextSticker){
  if(n>=next.size()||sticker!=next[n].body||sticker->mStickTarget!=source||sticker->mStickPart!=part||!currentAttachment(next[n])
    ||sticker->mAttachPosition.x!=next[n].saved.local.x||sticker->mAttachPosition.y!=next[n].saved.local.y||sticker->mAttachPosition.z!=next[n].saved.local.z){e="source77 actual attachment graph changed during capture";return false;}++n;
 }
 if(n!=next.size()){e="source77 actual attachment census changed during capture";return false;}
 out=std::move(next);e.clear();return true;
}
} }
