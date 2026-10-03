#pragma once
#include "pc_p2_original_shijimi_group.h"
#include "pc_p2_original_piki_origin.h"
namespace p2original { namespace shijimi {
// GenPiki branch only. BudConversion and OnyonEmission must use their own
// complete released identities; never collapse them into a GenPiki record.
struct GenPikiAttachment { OriginalPikiOrigin body;Position local; };
struct LiveGenPikiAttachment {
 GenPikiAttachment saved;Piki* body=nullptr;std::uint64_t nativeLifetime=0;
};
class AttachmentAuthority {
public:
 virtual ~AttachmentAuthority()=default;
 // Actual party/selected-graph owner verifies the complete saved source member.
 // Syntactic validity or the producer's own tuple is not source authority.
 virtual bool member(const OriginalPikiOrigin&,std::string&)const=0;
};
bool captureAttachment(Piki*,Position,const AttachmentAuthority&,LiveGenPikiAttachment&,std::string&);
bool currentAttachment(const LiveGenPikiAttachment&)noexcept;
bool encodeAttachments(const std::vector<GenPikiAttachment>&,const AttachmentAuthority&,std::string&,std::string&);
bool decodeAttachments(const std::string&,const AttachmentAuthority&,std::vector<GenPikiAttachment>&,std::string&);
// Resolve saved ancestry to CURRENT handles supplied by the actual party owner.
// Saved process lifetimes/pointers never enter bytes or authorize this mapping.
// This is not cold allocation, stick-FSM application or graph publication.
bool resolveAttachments(const std::vector<GenPikiAttachment>&,const std::vector<LiveGenPikiAttachment>& actualParty,
 const AttachmentAuthority&,std::vector<LiveGenPikiAttachment>&,std::string&);
} }
