#ifndef PC_DIARY_OBSERVER_H
#define PC_DIARY_OBSERVER_H

// Read-only input eligibility. No UI pointer escapes the production query.
enum class PcDiaryAction { Unavailable, RevealPage, AdvancePage };

constexpr PcDiaryAction pc_diary_message_action(bool activeDisplay, bool inputDisabled, bool fullyRevealed)
{
    return !activeDisplay || inputDisabled ? PcDiaryAction::Unavailable
         : fullyRevealed ? PcDiaryAction::AdvancePage : PcDiaryAction::RevealPage;
}

template <class Message>
PcDiaryAction pc_diary_result_action(bool diary, const Message* message)
{
    // Do not even read message eligibility outside the actual diary branch.
    return diary && message ? message->pcDiaryAction() : PcDiaryAction::Unavailable;
}

template <class Result>
PcDiaryAction pc_diary_window_action(const Result* result)
{
    return result ? result->pcDiaryAction() : PcDiaryAction::Unavailable;
}

PcDiaryAction pc_diary_observe();

#endif
