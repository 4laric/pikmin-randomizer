#ifndef PC_CAMPAIGN_UI_OBSERVER_H
#define PC_CAMPAIGN_UI_OBSERVER_H

// Save eligibility is supported only for VERSION_GPIE01_01.
// Value snapshots only. Call on the engine thread between updates. Never a card-commit oracle.
struct PcPauseSnapshot {
    bool available = false;
    int state = -1;
    int mainState = -1;
    int mainSelection = -1;
    int subState = -1;
    int subSelection = -1;
    bool mainInputReady = false;
    bool sunsetInputReady = false;
};
struct PcSaveUiSnapshot {
    bool available = false;
    int resultState = -1;
    int saveState = -1;
    bool resultsInputReady = false;
    bool primaryInputReady = false;
    bool primaryYes = false; // meaningful only when primaryInputReady
    bool secondaryInputReady = false;
    bool secondaryYes = false; // secondary prompt is NOT the save confirmation
    bool fileSelection = false;
    bool cardSlotInputReady = false;
    int cardSlot = -1; // meaningful only when cardSlotInputReady; save-mode selector only
    bool nestedUiBlocked = true;
};
PcPauseSnapshot pc_pause_observe();
PcSaveUiSnapshot pc_save_ui_observe();
#endif
