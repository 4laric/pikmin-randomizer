#ifndef P2_BLANK_CARD_INPUT_H
#define P2_BLANK_CARD_INPUT_H
#include "pc_blank_card_observer.h"
namespace blankcard {
enum class Input { Neutral, A, Complete, Refuse };
enum class Stage { Title, Story, Captain, Default, Files, Done };
struct Policy {
    Stage stage=Stage::Title;
    bool release=false, sawDefault=false, acknowledged=false;
    Input step(const PcBlankCardSnapshot& s, unsigned publications, bool forbidden,
               bool generationPresent, double elapsed) {
        // Evaluate refusals even on mandatory neutral frames.
        if(forbidden || generationPresent || !(elapsed>=0 && elapsed<60)
           || publications>1 || s.foreignPrompt) return Input::Refuse;
        if(s.title && s.card) return Input::Refuse;
        if(s.fileReady && (!s.card || !s.active || !s.fileVisible || s.fileState!=0 || s.memoryState!=-1)) return Input::Refuse;
        if(s.fileReady)for(int v:s.slots)if(v!=1)return Input::Refuse;
        if(s.card && s.fileState>0)return Input::Refuse; // Any selection/exit is forbidden.
        // Only native inactive/starting/default/success stages are permissible.
        if(s.card && s.memoryState!=-1 && s.memoryState!=0 && s.memoryState!=15 && s.memoryState!=21) return Input::Refuse;
        if(s.defaults.available) {
            if(!s.card || s.memoryState!=15 || s.defaults.memoryState!=15)return Input::Refuse;
            if(s.defaults.state<0 || s.defaults.state>4)return Input::Refuse;
            if(s.defaults.state==1 && !s.defaults.successful)return Input::Refuse;
            if(s.defaults.confirmationReady && (s.defaults.state!=1 || !s.defaults.successful || !s.defaults.typingComplete))return Input::Refuse;
        }
        if(release){release=false;return Input::Neutral;}
        if(!publications)return Input::Neutral; // Logos/setup have no menu snapshot.
        auto press=[&](){release=true;return Input::A;};
        switch(stage) {
        case Stage::Title:
            if(s.card)return Input::Refuse;
            if(s.pressStart){stage=Stage::Story;return press();}
            break;
        case Stage::Story:
            if(s.card)return Input::Refuse;
            if(s.titleReady){if(s.titleSelection!=0)return Input::Refuse;stage=Stage::Captain;return press();}
            break;
        case Stage::Captain:
            if(s.card && s.captainReady){if(s.captainChoice!=0)return Input::Refuse;stage=Stage::Default;return press();}
            if(s.defaults.available || s.fileReady)return Input::Refuse;
            break;
        case Stage::Default:
            if(s.defaults.available)sawDefault=true;
            if(s.defaults.confirmationReady){acknowledged=true;stage=Stage::Files;return press();}
            if(s.fileReady)return Input::Refuse;
            break;
        case Stage::Files:
            if(s.fileReady){if(!sawDefault || !acknowledged)return Input::Refuse;stage=Stage::Done;return Input::Complete;}
            break;
        case Stage::Done:return Input::Refuse;
        }
        return Input::Neutral;
    }
};
}
#endif
