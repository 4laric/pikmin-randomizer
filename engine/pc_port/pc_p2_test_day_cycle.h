#pragma once

// TEST-ONLY day-cycle driver for P2 cleanup / re-entry evidence (#246).
//
// Enabled only when PIKMIN_P2_TEST_DAY_CYCLE is set. It never touches game
// state beyond what a player can do: it ends the day through the same call
// the pause menu's "go to sunset" makes (gamecore->forceDayEnd), and on the
// world map re-enters the stage that was just played (the same enterCourse a
// player's map selection runs). Everything in between -- sunset, results,
// memory-card save, stage teardown, next-day load, generator rebirth -- is
// the real engine path. The autoplay bot taps A through the result screens.
//
// Spec: comma-separated steps, one per gameplay day of the session:
//   hurt:<s>     end the day <s> seconds after a bound Titan first loses
//                weapon HP (the Titan is alive at sunset)
//   receipt:<s>  end the day <s> seconds after the Titan corpse is delivered
//   time:<s>     end the day <s> seconds after the stage began
// After the last step's day ends and the next day has run for 60 s,
// P2_TEST_DAY_CYCLE_DONE is printed. Unset: every entry point is inert.
bool pc_p2_test_day_cycle_active();
// Per gameplay frame (RunningModeState). True once when the current step's
// condition has been met: the caller ends the day.
bool pc_p2_test_day_cycle_due(float dt);
// True between the forced sunset and the next stage's first frame: the bot
// only taps A (results, save).
bool pc_p2_test_day_cycle_advancing();
// World map: fills the stage id to re-enter and returns true once per sunset.
bool pc_p2_test_day_cycle_mapselect(int* stageId);
// Titan events ("hurt", "delivered").
void pc_p2_test_day_cycle_note(const char* event);
