// Netplay launch lane (issue #887): in-exe self-tests, run by ctest as
//   nectar.exe --netplay-launch-selftest settings
//   nectar.exe --netplay-launch-selftest input
//   nectar.exe --netplay-launch-selftest input-session
// They live in the game exe (netplay builds only) because they exercise the
// game's own settings and window code, which need the whole engine to link.
//
// settings       M2 + B3: pc_settings_netplay_selftest (pc_settings.cpp):
//                adoption round trip over every session key and edge value,
//                then every settings save path with the file checked.
// input          M4 + M6 + m5 + m7 through pc_window_poll_events itself:
//                an SDL virtual gamepad plus synthetic key state/events on
//                the dummy video driver. Keyboard peer ignores the pad and
//                pad presses; gamepad peer ignores keys and key hotkeys
//                (F6/F9); with the randomizer enabled and no focus, the
//                gamepad peer keeps its pad while the keyboard peer is
//                zeroed; gamepad:N resolves when the pad is hot-plugged.
// input-session  same with a netplay session active: F6/F9 are dropped for
//                the keyboard peer too, and the debug keys read as off.

#include "netplay/pc_netplay_launch.h"
#include "netplay/pc_netplay_session.h"

#include "pc_bbft.h"
#include "pc_window.h"
#include "settings/pc_settings.h"
#include "Dolphin/pad.h"

#include <SDL2/SDL.h>

#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>

#ifdef _WIN32
#include <direct.h>
#else
#include <sys/stat.h>
#include <unistd.h>
#endif

namespace {

int sChecks   = 0;
int sFailures = 0;

void check(bool ok, const char* what)
{
	++sChecks;
	if (!ok) {
		++sFailures;
		printf("FAIL: %s\n", what);
	} else {
		printf("ok: %s\n", what);
	}
	fflush(stdout);
}

void enter_work_dir(const char* name)
{
#ifdef _WIN32
	_mkdir(name);
	if (_chdir(name) != 0) {
#else
	mkdir(name, 0755);
	if (chdir(name) != 0) {
#endif
		printf("selftest: cannot enter %s\n", name);
		exit(2);
	}
}

void set_env(const char* name, const char* value)
{
#ifdef _WIN32
	_putenv_s(name, value);
#else
	setenv(name, value, 1);
#endif
}

int selftest_settings()
{
	enter_work_dir("netplay-launch-selftest-settings");
	// The F1 page builds its resolution list from the display modes; the
	// dummy driver has one, which is all the menu needs. No window, no GL.
	set_env("SDL_VIDEODRIVER", "dummy");
	if (SDL_Init(SDL_INIT_VIDEO) < 0) {
		printf("selftest: SDL_Init(video, dummy) failed: %s\n", SDL_GetError());
		return 2;
	}
	const int rc = pc_settings_netplay_selftest(pc_netplay_session_config_text);
	SDL_Quit();
	return rc;
}

PADStatus sPads[PAD_MAX_CONTROLLERS];

void poll(int turns = 3)
{
	for (int i = 0; i < turns; ++i) pc_window_poll_events(sPads);
}

void set_key(SDL_Scancode sc, bool down)
{
	// Synthetic held key: SDL's keyboard state array is the one
	// pc_window_poll_events samples (SDL_GetKeyboardState).
	Uint8* keys = const_cast<Uint8*>(SDL_GetKeyboardState(nullptr));
	keys[sc]    = down ? 1 : 0;
}

void push_key_event(SDL_Scancode sc)
{
	SDL_Event ev;
	memset(&ev, 0, sizeof(ev));
	ev.type                = SDL_KEYDOWN;
	ev.key.state           = SDL_PRESSED;
	ev.key.repeat          = 0;
	ev.key.keysym.scancode = sc;
	SDL_PushEvent(&ev);
}

int selftest_input(bool session)
{
	enter_work_dir(session ? "netplay-launch-selftest-input-session" : "netplay-launch-selftest-input");
	if (session) {
		// A legacy host switch makes pc_netplay_session_active() true; the
		// session driver never runs here, so no socket is ever opened.
		static char a0[] = "nectar";
		static char a1[] = "--netplay-host";
		static char a2[] = "48149";
		static char* fake[] = { a0, a1, a2, nullptr };
		pc_netplay_session_notify_argv(3, fake);
		check(pc_netplay_session_active(), "session variant: a netplay session is active");
	}
	set_env("SDL_VIDEODRIVER", "dummy");
	set_env("SDL_AUDIODRIVER", "dummy");
	SDL_SetHint(SDL_HINT_JOYSTICK_ALLOW_BACKGROUND_EVENTS, "1");
	if (SDL_Init(SDL_INIT_VIDEO | SDL_INIT_EVENTS | SDL_INIT_JOYSTICK | SDL_INIT_GAMECONTROLLER) < 0) {
		printf("selftest: SDL_Init failed: %s\n", SDL_GetError());
		return 2;
	}

	// m5: the gamepad selection is made BEFORE the pad exists (the joiner's
	// launcher applies input at session start); it must resolve on hotplug.
	pc_window_set_netplay_input_filter(true, false);
	pc_window_set_netplay_gamepad(1, 0);
	poll();
	check(pc_window_num_gamepads() == 0, "no gamepad open before the virtual pad is attached");

	SDL_VirtualJoystickDesc desc;
	SDL_zero(desc);
	desc.version     = SDL_VIRTUAL_JOYSTICK_DESC_VERSION;
	desc.type        = SDL_JOYSTICK_TYPE_GAMECONTROLLER;
	desc.naxes       = SDL_CONTROLLER_AXIS_MAX;
	desc.nbuttons    = SDL_CONTROLLER_BUTTON_MAX;
	desc.axis_mask   = (1u << SDL_CONTROLLER_AXIS_MAX) - 1u;
	desc.button_mask = (1u << SDL_CONTROLLER_BUTTON_MAX) - 1u;
	desc.name        = "netplay selftest virtual pad";
	const int devIndex = SDL_JoystickAttachVirtualEx(&desc);
	if (devIndex < 0) {
		printf("selftest: SDL_JoystickAttachVirtualEx failed: %s\n", SDL_GetError());
		return 2;
	}
	poll(5); // SDL_CONTROLLERDEVICEADDED -> pc_controller_open_slot
	check(pc_window_num_gamepads() == 1, "the virtual gamepad is opened as a game controller");
	SDL_Joystick* joy = SDL_JoystickOpen(devIndex);
	check(joy != nullptr, "virtual joystick handle");
	if (joy == nullptr) return 2;
	int gp = -1;
	check(pc_window_input_get_assignment(1, &gp) == PC_INPUT_DEV_GAMEPAD && gp == SDL_JoystickInstanceID(joy),
	      "gamepad:0 resolved on hotplug to the virtual pad for joiner/P2 (m5)");
	check(pc_window_get_controller_p2() != nullptr, "joiner/P2 slot is fed by the pad");

	auto padA = [&](bool down) {
		SDL_JoystickSetVirtualButton(joy, SDL_CONTROLLER_BUTTON_A, down ? 1 : 0);
		poll();
	};

	// ---- focused (randomizer off: pc_bbft_accept_input() is true) ----
	check(pc_bbft_accept_input(), "premise: input accepted (no randomizer, no BBFT hold)");

	// Gamepad peer (joiner, role 1): keys ignored, pad feeds P2.
	pc_window_discard_button_presses();
	set_key(SDL_SCANCODE_SPACE, true); // A on the keyboard
	padA(false);
	check((sPads[0].button & PAD_BUTTON_A) == 0 && (sPads[1].button & PAD_BUTTON_A) == 0,
	      "gamepad peer: a held key reaches no pad");
	padA(true);
	check((sPads[1].button & PAD_BUTTON_A) != 0, "gamepad peer: the pad's A reaches P2");
	padA(false);
	{
		const unsigned before = pc_window_netplay_blocked_hotkeys();
		pc_window_discard_button_presses();
		push_key_event(SDL_SCANCODE_F6);
		push_key_event(SDL_SCANCODE_F9);
		push_key_event(SDL_SCANCODE_Y);
		poll();
		check(pc_window_netplay_blocked_hotkeys() == before + 2,
		      "gamepad peer: F6 and F9 are dropped (hotkeys follow ownership, m7)");
		int kind = -1, id = -1;
		const bool took = pc_window_take_button_press(&kind, &id);
		check(!took || kind != PC_INPUT_DEV_KEYBOARD, "gamepad peer: a key press never reaches a prompt");
	}
	set_key(SDL_SCANCODE_SPACE, false);

	// Keyboard peer (host, role 0): pad ignored, keys feed P1. First the
	// filter on its own, with today's automatic assignment (the pad would
	// feed P1): the ownership filter alone must drop it.
	pc_window_set_netplay_input_filter(false, true);
	pc_window_input_reset_assignment();
	check(pc_window_get_controller() != nullptr, "premise: auto assignment binds the pad to P1");
	padA(true);
	check((sPads[0].button & PAD_BUTTON_A) == 0, "keyboard filter alone: the bound pad's A never reaches P1");
	padA(false);
	// Then the launcher's assignment for a keyboard peer.
	pc_window_input_assign(0, PC_INPUT_DEV_KEYBOARD, -1);
	padA(true);
	check((sPads[0].button & PAD_BUTTON_A) == 0 && (sPads[1].button & PAD_BUTTON_A) == 0,
	      "keyboard peer: the pad's A reaches no pad");
	{
		pc_window_discard_button_presses();
		padA(false);
		padA(true); // a fresh SDL_CONTROLLERBUTTONDOWN
		int kind = -1, id = -1;
		const bool took = pc_window_take_button_press(&kind, &id);
		check(!took || kind != PC_INPUT_DEV_GAMEPAD, "keyboard peer: a pad press never reaches a prompt");
	}
	padA(false);
	set_key(SDL_SCANCODE_SPACE, true);
	poll();
	check((sPads[0].button & PAD_BUTTON_A) != 0, "keyboard peer: a held key reaches P1");
	set_key(SDL_SCANCODE_SPACE, false);
	{
		const unsigned before = pc_window_netplay_blocked_hotkeys();
		push_key_event(SDL_SCANCODE_F6);
		push_key_event(SDL_SCANCODE_F9);
		poll();
		const unsigned dropped = pc_window_netplay_blocked_hotkeys() - before;
		if (session) {
			check(dropped == 2, "keyboard peer in a netplay session: F6 and F9 are dropped (m7)");
			check(pc_settings_get_debug_keys() == 0, "netplay session: the debug keys read as off (m7)");
		} else {
			check(dropped == 0, "keyboard peer outside a session: F6/F9 keep their normal path");
		}
	}

	// ---- unfocused, randomizer enabled (the local two-window case) ----
	{
		// A throwaway run layout: the randomizer derives its campaign dir
		// from the bootstrap's grandparent, so keep it two levels down.
		const std::string runs = session ? "session/runs/0123456789abcdef" : "session/runs/fedcba9876543210";
#ifdef _WIN32
		_mkdir("session");
		_mkdir("session/runs");
		_mkdir(runs.c_str());
#else
		mkdir("session", 0755);
		mkdir("session/runs", 0755);
		mkdir(runs.c_str(), 0755);
#endif
		const std::string tok(64, 'a');
		const std::string boot = runs + "/bootstrap.txt";
		remove((runs + "/hello.txt").c_str());
		FILE* f = fopen(boot.c_str(), "wb");
		if (f != nullptr) {
			fprintf(f,
			        "PIKMIN_RANDOMIZER 5\nSESSION %s\nFINGERPRINT %s\nPROFILE foh-day2\nCATALOG "
			        "gameplay-checks-v5\nPLACEMENT identity-v1\nGOAL 25\nDAYS repeat-day29-v1\nCOLOR "
			        "red\nSTARTING_FLARLIC 10\nEND\n",
			        tok.c_str(), tok.c_str());
			fclose(f);
		}
		static std::string bootArg;
		bootArg          = boot;
		static char b0[] = "nectar";
		static char b1[] = "--randomizer-seed";
		char* bargv[]    = { b0, b1, &bootArg[0], nullptr };
		pc_bbft_init(3, bargv);
		check(pc_bbft_enabled(), "premise: randomizer enabled");
#ifdef _WIN32
        check(!pc_bbft_accept_input(), "premise: input refused (randomizer, window not in the foreground)");
#else
        check(pc_bbft_accept_input(), "Linux premise: BBFT accepts input without Win32 foreground gating");
#endif
	}
	// Keyboard peer keeps the focus rule.
	set_key(SDL_SCANCODE_SPACE, true);
	poll();
#ifdef _WIN32
    check((sPads[0].button & PAD_BUTTON_A) == 0, "keyboard peer, no focus: keys are zeroed (focus rule)");
#else
    check((sPads[0].button & PAD_BUTTON_A) != 0, "Linux keyboard peer: held key still reaches P1 under platform input policy");
#endif
	set_key(SDL_SCANCODE_SPACE, false);
	// Gamepad peer keeps its pad (M4).
	pc_window_set_netplay_input_filter(true, false);
	pc_window_input_reset_assignment();
	pc_window_set_netplay_gamepad(1, 0);
	padA(true);
	check((sPads[1].button & PAD_BUTTON_A) != 0, "gamepad peer, no focus, randomizer on: the pad keeps feeding P2 (M4)");
	padA(false);
	check((sPads[1].button & PAD_BUTTON_A) == 0, "gamepad peer, no focus: releasing the pad clears P2");
	// Hot-unplug and replug: the selection re-resolves (m5).
	SDL_JoystickClose(joy);
	SDL_JoystickDetachVirtual(devIndex);
	poll(5);
	check(pc_window_num_gamepads() == 0 && pc_window_get_controller_p2() == nullptr,
	      "pad unplugged: P2 slot neutral");
	const int dev2 = SDL_JoystickAttachVirtualEx(&desc);
	poll(5);
	check(dev2 >= 0 && pc_window_num_gamepads() == 1 && pc_window_get_controller_p2() != nullptr,
	      "pad replugged: gamepad:0 re-resolves to P2 (m5)");

	SDL_Quit();
	return 0;
}

} // namespace

int pc_netplay_launch_selftest(int argc, char** argv)
{
	const char* which = argc >= 3 ? argv[2] : "";
	int rc            = 2;
	if (std::strcmp(which, "settings") == 0) rc = selftest_settings();
	else if (std::strcmp(which, "input") == 0) rc = selftest_input(false);
	else if (std::strcmp(which, "input-session") == 0) rc = selftest_input(true);
	else {
		printf("usage: --netplay-launch-selftest settings|input|input-session\n");
		return 2;
	}
	if (std::strcmp(which, "settings") != 0) {
		printf("netplay input selftest (%s): %s (%d checks, %d failures)\n", which,
		       (rc == 0 && sFailures == 0) ? "PASS" : "FAIL", sChecks, sFailures);
		if (rc == 0 && sFailures != 0) rc = 1;
	}
	fflush(stdout);
	return rc;
}
