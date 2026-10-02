#ifndef P2_PURPLE_SAVE_INPUT_H
#define P2_PURPLE_SAVE_INPUT_H
#include "pc_campaign_ui_observer.h"
#include "pc_diary_observer.h"
// Intent only: no controller/UI/game state writes. The caller releases every edge.
enum class PurpleSaveInput { Neutral, Down, Up, Confirm, RevealDiary, AdvanceDiary, Unexpected };
inline PurpleSaveInput purple_save_input(bool dayAdvanced, const PcPauseSnapshot& pause,
                                         PcDiaryAction diary, const PcSaveUiSnapshot& save)
{
    if (!dayAdvanced) {
        if (pause.mainInputReady) {
            if (pause.mainSelection == 0) return PurpleSaveInput::Down;
            if (pause.mainSelection == 1) return PurpleSaveInput::Confirm;
            if (pause.mainSelection == 2) return PurpleSaveInput::Up;
            return PurpleSaveInput::Unexpected;
        }
        if (pause.sunsetInputReady)
            return pause.subSelection == 0 ? PurpleSaveInput::Confirm : PurpleSaveInput::Unexpected;
        return PurpleSaveInput::Neutral;
    }
    if (diary == PcDiaryAction::RevealPage) return PurpleSaveInput::RevealDiary;
    if (diary == PcDiaryAction::AdvancePage) return PurpleSaveInput::AdvanceDiary;
    if (save.resultsInputReady) return PurpleSaveInput::Confirm;
    if (save.defaultFile.available) {
        // First-save creation owns the outer memory update, before slot selection.
        // The existing const observer exposes success only in the real native
        // AwaitingConfirmation branch, and eligibility only after text completes.
        // nestedUiBlocked is expected while memory owns this routed prompt.
        if (!save.available || !save.outerMemoryRouted || !save.memoryAvailable
            || !save.failureAvailable || !save.failureInactive || !save.fileAvailable
            || save.fileSelection) return PurpleSaveInput::Unexpected;
        if (!save.defaultFile.successful) return PurpleSaveInput::Neutral;
        if (save.defaultFile.confirmationReady != save.defaultFile.typingComplete)
            return PurpleSaveInput::Unexpected;
        return save.defaultFile.confirmationReady ? PurpleSaveInput::Confirm : PurpleSaveInput::Neutral;
    }
    if (save.cardSlotInputReady)
        return save.cardSlot == 0 ? PurpleSaveInput::Confirm : PurpleSaveInput::Unexpected;
    if (save.secondaryInputReady) return PurpleSaveInput::Unexpected; // exits without saving
    if (save.primaryInputReady) return save.primaryYes ? PurpleSaveInput::Confirm : PurpleSaveInput::Up;
    return PurpleSaveInput::Neutral;
}
#endif
