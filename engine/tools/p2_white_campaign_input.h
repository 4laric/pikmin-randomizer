#pragma once
#include "pc_campaign_ui_observer.h"
#include "pc_diary_observer.h"
enum class WhiteSaveIntent { Neutral, Pause, Down, Up, Confirm, Reveal, Advance, Refuse };
// Read-only UI eligibility. The fixture must release each observed input edge.
inline WhiteSaveIntent white_save_intent(bool requested,bool advanced,const PcPauseSnapshot& pause,PcDiaryAction diary,const PcSaveUiSnapshot& save){
 if(!requested)return WhiteSaveIntent::Pause;
 if(!advanced){
  if(pause.mainInputReady){if(pause.mainSelection==0)return WhiteSaveIntent::Down;if(pause.mainSelection==1)return WhiteSaveIntent::Confirm;if(pause.mainSelection==2)return WhiteSaveIntent::Up;return WhiteSaveIntent::Refuse;}
  if(pause.sunsetInputReady)return pause.subSelection==0?WhiteSaveIntent::Confirm:WhiteSaveIntent::Refuse;
  return WhiteSaveIntent::Neutral;
 }
 if(diary==PcDiaryAction::RevealPage)return WhiteSaveIntent::Reveal;
 if(diary==PcDiaryAction::AdvancePage)return WhiteSaveIntent::Advance;
 if(save.resultsInputReady)return WhiteSaveIntent::Confirm;
 if(save.cardSlotInputReady)return save.cardSlot==0?WhiteSaveIntent::Confirm:WhiteSaveIntent::Refuse;
 if(save.secondaryInputReady)return WhiteSaveIntent::Refuse;
 if(save.primaryInputReady)return save.primaryYes?WhiteSaveIntent::Confirm:WhiteSaveIntent::Up;
 return WhiteSaveIntent::Neutral;
}
inline constexpr int white_campaign_axis(int value){return value*256;}
