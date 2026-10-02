#pragma once
inline bool pcPurpleDismissInitialModes(unsigned formation,unsigned free) {
    return formation<=19 && free==19-formation;
}
enum class PcPurpleDismissInput { Neutral, Press, Done, Refuse };
class PcPurpleDismissPolicy {
public:
    PcPurpleDismissInput observe(bool idle,bool walking,bool releasing,bool rosterFree) {
        if(done_)return PcPurpleDismissInput::Done;
        if(++frames_>120)return PcPurpleDismissInput::Refuse;
        if(releasing)releaseSeen_=true;
        if(phase_==0) {
            if(walking){phase_=2;return PcPurpleDismissInput::Neutral;}
            if(idle){phase_=1;return PcPurpleDismissInput::Press;}
            return PcPurpleDismissInput::Neutral;
        }
        if(phase_==1) {
            if(walking){phase_=2;return PcPurpleDismissInput::Neutral;}
            return idle?PcPurpleDismissInput::Press:PcPurpleDismissInput::Neutral;
        }
        if(phase_==2){phase_=3;return PcPurpleDismissInput::Press;}
        if(releaseSeen_&&walking&&rosterFree){done_=true;return PcPurpleDismissInput::Done;}
        return PcPurpleDismissInput::Neutral;
    }
    bool releaseSeen()const{return releaseSeen_;}
private:
    unsigned frames_=0,phase_=0;
    bool releaseSeen_=false,done_=false;
};
