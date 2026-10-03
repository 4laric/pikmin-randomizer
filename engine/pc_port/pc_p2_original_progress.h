#pragma once
#include <cstdint>
#include <string>
namespace p2original {
// Retail Blue0/Red1/Yellow2/Purple3/White4. Bulbmin5 is always met,
// cannot boot a container. Container discovery, first-met and boot are distinct.
struct ProgressState {std::string campaign;std::uint8_t met=0,boot=0,container=0;};
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
private: ProgressState mState;
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
