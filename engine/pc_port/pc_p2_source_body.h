#pragma once
#include "pc_p2_original_piki_origin.h"
#include "pc_p2_bud_conversion_origin.h"
enum class PcP2SourceBodyKind { None,GenPiki,BudConversion,Unavailable,OnyonEmission };
struct PcP2SourceOnyonRoot {
 std::string campaign,session,sourceSha,sourceKey;
 std::uint32_t uid=0;
 std::uint8_t species=0;
 std::uint64_t birthIncarnation=0;
};
class PcP2SourceOnyonReader;
struct PcP2SourceBody {
 PcP2SourceBodyKind kind=PcP2SourceBodyKind::None;
 OriginalPikiBodyState state;
 OriginalPikiBody genPiki;
 p2budorigin::Record conversion;
 PcP2SourceOnyonRoot onyon;
 const Piki* nativeBody=nullptr; // Transient native read-view; never serialized.
 std::uint64_t nativeLifetime=0;
};
// Tag is returned even if source admission later refuses. Never turn an expired
// labelled source body into an ordinary-P1 fallback. Failed output is unchanged.
PcP2SourceBodyKind pc_p2_source_body_query(const Piki*,PcP2SourceBody&);
bool pc_p2_source_body_admitted(const PcP2SourceBody&,const std::string& campaign,
                              const std::string& genPikiCatalog,std::string&);
bool pc_p2_source_body_recruited(Piki*);

// One source-owned reader, registered before any Onyon-labelled body exists.
// Ownership/lifetime must come from the actual producer, never a pointer hash.
// owned() retains the tag even when query/adoption is unavailable. No method
// may fall back to GenPiki identity or synthesize source authority.
class PcP2SourceOnyonReader {
public:
 virtual ~PcP2SourceOnyonReader()=default;
 virtual bool owned(const Piki*)const noexcept=0;
 virtual bool lifetime(const Piki*,std::uint64_t&)const noexcept=0;
 virtual bool query(const Piki*,std::uint64_t,PcP2SourceOnyonRoot&,OriginalPikiBodyState&)const=0;
 virtual bool admitted(const Piki*,std::uint64_t,const PcP2SourceOnyonRoot&,const std::string&,std::string&)const=0;
 virtual bool recruited(Piki*,std::uint64_t)=0;
 virtual void forget(Piki*)noexcept=0;
 virtual void sceneExit()noexcept=0;
};
// Reader MUST be a process-lifetime stable singleton: there is no uninstall or
// reset. Scene teardown retires associations, never destroys/replaces reader.
bool pc_p2_source_body_install_onyon_reader(PcP2SourceOnyonReader&)noexcept;
void pc_p2_source_body_forget_external(Piki*)noexcept;
void pc_p2_source_body_scene_exit_external()noexcept;
