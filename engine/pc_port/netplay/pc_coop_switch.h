#ifndef PC_COOP_SWITCH_H
#define PC_COOP_SWITCH_H

// Direct-boot co-op switch (netplay M0): the programmatic equivalent of the
// title/card-select arming (pc_coop_set_pending / pc_coop_set_captain) for
// runs that skip both screens, such as the randomizer direct boot. Opt-in
// only: with no switch present nothing is armed and the game behaves as
// before. Nothing here touches the randomizer manifest or handshake.

struct PcCoopSwitch {
	bool coop = false; // --coop / PIKMIN_COOP (explicit off words honoured)
	int captainP1 = 0; // PcCaptain index; default Olimar (0) ...
	int captainP2 = 1; // ... and Louie (1)
};

// Pure parse of a "<p1>,<p2>" captain string (CLI value or env value).
// Captain names: olimar, louie, pikmin-red, pikmin-yellow, pikmin-blue.
// Returns true and writes both outputs on a valid pair; returns false and
// leaves the outputs alone otherwise. No globals, no env, no game state.
bool pc_coop_switch_parse_captains(const char* text, int* outP1, int* outP2);

// CLI + environment parse. Only --coop and PIKMIN_COOP arm co-op (an
// explicit PIKMIN_COOP=0/false/off keeps it off); --coop-captains=<p1>,<p2>
// and PIKMIN_COOP_CAPTAINS only select captains, except that an explicit CLI
// --coop-captains value implies co-op and wins over the env pair. An invalid
// captains string keeps the default pair and prints one [NETPLAY] warning,
// but only when the switch is otherwise present.
PcCoopSwitch pc_coop_switch_parse(int argc, char** argv);

// Arms pending co-op and both captains for the coming run. Call once at
// startup, before any GameCoreSection is constructed. No-op unless the
// switch requested co-op. Pending is never cleared here, so the switch
// stays on for every day of the run (each day builds a new GameCoreSection
// that re-reads it); it is not a one-shot.
void pc_coop_switch_apply(const PcCoopSwitch& sw);

// True once this process armed co-op through the switch (latched by apply).
// Used for the [NETPLAY] log marker gate.
bool pc_coop_switch_active(void);

#endif // PC_COOP_SWITCH_H
