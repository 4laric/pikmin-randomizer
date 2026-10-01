#pragma once
// In-game dev console (#942): spawn/kill/pikmin/day/time/tp for hand-testing
// ported P2 enemies without regenerating seeds.
//
// Inert unless PIKMIN_DEV_CONSOLE=1 is set in the environment: every entry
// point below returns immediately, no key is read, no line is logged. It also
// refuses to enable when a netplay switch (--netplay-host/--netplay-join or
// PIKMIN_NETPLAY_HOST/JOIN) is present, because runtime spawns would break
// lockstep determinism.
//
// Keyboard: backquote (`) toggles the one-line input; Enter runs it; Esc
// closes it; Up recalls the last line. While open every other key is
// swallowed (the virtual pad reads no keys).
//
// Script feed: PIKMIN_DEV_CONSOLE_SCRIPT=<file> is polled during gameplay;
// every newly appended line is executed as if typed, so headless runs can
// drive it (`echo spawn 41 >> file`). Output goes to stdout (native.log) as
// `DEV_CONSOLE ...` lines and to the on-screen log.
//
// The grammar and species table are engine-free in pc_dev_console_parser.h.
union SDL_Event;

// pc_main: read the env switch and the netplay refusal before the game starts.
void pc_dev_console_init(int argc, char** argv);
bool pc_dev_console_enabled();
// True while the text input is open (keyboard captured).
bool pc_dev_console_open();
// pc_window event loop: returns true when the console consumed the event.
bool pc_dev_console_handle_event(const SDL_Event& event);
// GameCoreSection::update: runs queued/script commands on the gameplay thread.
void pc_dev_console_update();
// VIWaitForRetrace overlay: input line + recent output.
void pc_dev_console_draw();
// GameCoreSection stage load, before tekiMgr->startStage(): mark the P1 host
// vehicle of every dev-bound species as used so its model loads.
void pc_dev_console_reserve_host_types();
// Execute one command line now (fixtures / script feed).
void pc_dev_console_execute(const char* line);
