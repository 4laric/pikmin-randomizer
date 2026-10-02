#ifndef PC_BLANK_CARD_OBSERVER_H
#define PC_BLANK_CARD_OBSERVER_H
#include "pc_campaign_ui_observer.h"
// Diagnostic-only value copies. Never enable from gameplay or use to change UI.
struct PcBlankCardSnapshot {
    bool title = false, card = false, active = false;
    bool pressStart = false, titleReady = false;
    int titleSelection = -1;
    bool captainPrompt = false, captainReady = false;
    int captainChoice = -1;
    bool foreignPrompt = false, fileVisible = false, fileReady = false;
    int fileState = -1, memoryState = -1;
    int slots[3] = {0,0,0};
    PcDefaultFileSnapshot defaults;
};
inline bool pc_blank_card_observer_enabled = false;
inline PcBlankCardSnapshot pc_blank_card_snapshot;
inline unsigned pc_blank_card_publications = 0;
inline void pc_blank_card_publish(const PcBlankCardSnapshot& value) {
    if (!pc_blank_card_observer_enabled) return;
    pc_blank_card_snapshot=value; ++pc_blank_card_publications;
}
// Publish on every ordinary update return, without changing any native state.
template<class F> struct PcBlankCardAfter {
    F read;
    ~PcBlankCardAfter() { if(pc_blank_card_observer_enabled) read(); }
};
template<class F> PcBlankCardAfter<F> pc_blank_card_after(F read) { return {read}; }
bool pc_blank_captain_ready();
int pc_blank_captain_choice();
#endif
