#pragma once
#include <cstdint>
#include <string>
namespace p2original {
// Retail Blue0/Red1/Yellow2/Purple3/White4. Bulbmin5 is always met,
// cannot boot a container. Container discovery, first-met and boot are distinct.
struct ProgressState {std::string campaign;std::uint8_t met=0,boot=0,container=0;};
struct ProgressContext {std::string campaign;std::uint32_t day=0;bool reunited=false,story=true;};
class Progress {
public:
 bool initialize(const std::string& campaign,std::string&);
 bool ready()const{return !mState.campaign.empty();}
 bool met(unsigned)const;
 bool booted(unsigned)const;
 bool container(unsigned)const;
 // Original actual whistle recruitment: RGB only. Red's met event belongs
 // to delayed helloPikmin, independently of immediate container boot.
 bool recruited(unsigned,std::string&);
 bool hello(unsigned,std::string&);
 bool boot(unsigned,std::string&);
 bool discover(unsigned,std::string&);
 const ProgressState& snapshot()const{return mState;}
 bool restore(const ProgressState&,std::string&);
 bool encode(std::string&,std::string&)const;
 bool decode(const std::string& bytes,const std::string& campaign,std::string&);
 // Source day is zero-based and advances only from an actual original story
 // day completion. Reunited is the distinct DEMO_Reunite_Captains event.
 bool nextDay(std::string&);
 bool reunite(std::string&);
 bool captainAllowed(unsigned captain,bool wasWild)const;
 const ProgressContext& context()const{return mContext;}
 bool restoreContext(const ProgressContext&,std::string&);
 bool encodeContext(std::string&,std::string&)const;
 bool decodeContext(const std::string&,const std::string& campaign,std::string&);
private: ProgressState mState;ProgressContext mContext;
};
Progress& originalProgress();
}
// Actual source body/item event owners call these AFTER accepted events.
// Ordinary P1/AP events must never call these entrypoints.
bool pc_p2_original_progress_met(unsigned);
bool pc_p2_original_progress_booted(unsigned);
bool pc_p2_original_progress_container(unsigned);
bool pc_p2_original_progress_recruited(unsigned,std::string&);
bool pc_p2_original_progress_hello(unsigned,std::string&);
bool pc_p2_original_progress_boot(unsigned,std::string&);
bool pc_p2_original_progress_discover(unsigned,std::string&);
bool pc_p2_original_progress_captain_allowed(unsigned captain,bool wasWild);
bool pc_p2_original_progress_reunite(std::string&);
bool pc_p2_original_progress_next_day(std::string&);
