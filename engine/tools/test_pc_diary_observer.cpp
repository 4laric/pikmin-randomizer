#include "pc_diary_observer.h"
#include <cstdio>

static_assert(pc_diary_message_action(false, false, false) == PcDiaryAction::Unavailable, "inactive");
static_assert(pc_diary_message_action(false, false, true) == PcDiaryAction::Unavailable, "inactive revealed");
static_assert(pc_diary_message_action(true, true, false) == PcDiaryAction::Unavailable, "disabled");
static_assert(pc_diary_message_action(true, true, true) == PcDiaryAction::Unavailable, "disabled revealed");
static_assert(pc_diary_message_action(true, false, false) == PcDiaryAction::RevealPage, "reveal");
static_assert(pc_diary_message_action(true, false, true) == PcDiaryAction::AdvancePage, "advance");

// Engine-free observer policy test. This probe does not fabricate a live UI
// object. Count calls to prove failed outer gates never inspect inner state.
struct MessageProbe {
    bool active, disabled, revealed;
    mutable int reads = 0;
    PcDiaryAction pcDiaryAction() const
    {
        ++reads;
        return pc_diary_message_action(active, disabled, revealed);
    }
};
struct ResultProbe {
    bool diary;
    const MessageProbe* message;
    mutable int reads = 0;
    PcDiaryAction pcDiaryAction() const
    {
        ++reads;
        return pc_diary_result_action(diary, message);
    }
};

int main()
{
    int failures = 0;
    auto check = [&failures](bool value, const char* name) {
        if (!value) { std::printf("FAIL diary observer: %s\n", name); ++failures; }
    };
    const MessageProbe enabled{true, false, false};
    const MessageProbe disabled{true, true, true};
    const ResultProbe outside{false, &enabled};
    const ResultProbe missing{true, nullptr};
    const ResultProbe available{true, &enabled};
    const ResultProbe blocked{true, &disabled};
    check(pc_diary_window_action<ResultProbe>(nullptr) == PcDiaryAction::Unavailable, "missing result window");
    check(pc_diary_result_action<MessageProbe>(true, nullptr) == PcDiaryAction::Unavailable, "missing message");
    check(pc_diary_window_action(&outside) == PcDiaryAction::Unavailable && enabled.reads == 0, "non-diary does not read message");
    check(pc_diary_window_action(&missing) == PcDiaryAction::Unavailable && enabled.reads == 0, "null message does not read unrelated state");
    check(pc_diary_window_action(&blocked) == PcDiaryAction::Unavailable, "disabled message fails closed");
    check(pc_diary_window_action(&available) == PcDiaryAction::RevealPage && enabled.reads == 1, "live diary delegates once");
    check(enabled.active && !enabled.disabled && !enabled.revealed && disabled.active && disabled.disabled && disabled.revealed,
          "eligibility observations preserve input state");
    check(outside.reads == 1 && missing.reads == 1 && available.reads == 1 && blocked.reads == 1, "single read per existing result");
    if (failures) return 1; // Explicit checks remain active under NDEBUG.
    std::puts("PASS diary observer eligibility and failed-read gates (engine-free)");
    return 0;
}
