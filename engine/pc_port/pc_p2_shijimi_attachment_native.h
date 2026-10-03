#pragma once
#include "pc_p2_shijimi_attachment.h"
class Creature;struct CollPart;
namespace p2original { namespace shijimi {
// The actual source77 owner passes its live body and actual st__ part. Every
// sticker must be an admitted GenPiki; unsupported provenance refuses rather
// than silently dropping that relationship from a checkpoint.
bool captureGenPikiStickers(Creature*,CollPart* sourceStickable,
 const AttachmentAuthority&,std::vector<LiveGenPikiAttachment>&,std::string&);
} }
