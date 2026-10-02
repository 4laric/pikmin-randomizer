#ifndef PC_COOP_POLICY_H
#define PC_COOP_POLICY_H

// Netplay M4 D-policy (issue #885): the owner's co-op randomizer policy as
// pure functions over small structs, so every decision is unit-testable
// without the engine (pc_coop_policy_test.cpp). The engine side
// (gameCoreSection.cpp, co-op branch only) fills the structs from the two
// captains and applies the result. Single-captain play never calls this.
//
// Owner decisions (final):
//   1. Heal goes to the triggering captain, otherwise to the live captain
//      with the lowest HP.
//   2. Trap and delivery anchors alternate between live captains,
//      round-robin (one cursor per anchored kind).
//   3. Benefits apply while ANY captain lives.
//   4. DeathLink uses a combined Pikmin pool (count Pikmin, not captains).
//
// Captain index: 1 = P1 (GameCoreSection::mNavi), 2 = P2 (mNavi2). Ties
// always break to the lower index. No RNG and no wall clock anywhere, so
// the same inputs give the same answer on both lockstep peers.

#include <cstdint>

enum { PC_COOP_CAPTAINS = 2 };

struct PcCoopCaptain {
	int id;       // 1 or 2
	bool live;    // pcIsLastNaviStanding predicate: hp > 1 and not NAVISTATE_Dead
	float hp;     // Navi::mHealth
	float maxHp;  // C_NAVI_PARM(navi, mHealth)
};

// Rule 3: benefits (and the randomizer tick) run while any captain lives.
bool pc_coop_any_live(const PcCoopCaptain caps[PC_COOP_CAPTAINS]);

// Rule 1: heal target.
enum PcCoopHealReason { PC_COOP_HEAL_NONE = 0, PC_COOP_HEAL_TRIGGER, PC_COOP_HEAL_LOWEST };
struct PcCoopHealPick {
	int captain;              // 1 or 2; 0 = nobody qualifies (heal stays pending)
	PcCoopHealReason reason;
};
// Candidates are the live captains with hp < maxHp. A candidate "triggered"
// when prevValid[i] and caps[i].hp < prevHp[i] (its HP dropped since the
// previous co-op tick's sample). Exactly one triggering candidate wins
// (reason TRIGGER); otherwise (none or several) the candidate with the
// lowest hp wins (reason LOWEST), ties to captain 1. A downed captain is
// never a candidate.
PcCoopHealPick pc_coop_pick_heal(const PcCoopCaptain caps[PC_COOP_CAPTAINS],
                                 const float prevHp[PC_COOP_CAPTAINS],
                                 const bool prevValid[PC_COOP_CAPTAINS]);
const char* pc_coop_heal_reason_name(PcCoopHealReason reason);

// Rule 2: captain-anchored grants, one round-robin cursor per kind.
// Onion-anchored grants (BOMBS, DELIVERY) have no captain anchor.
enum PcCoopAnchorKind {
	PC_COOP_ANCHOR_BOMB_TRAP = 0,
	PC_COOP_ANCHOR_PROGG,
	PC_COOP_ANCHOR_PRERELEASE,
	PC_COOP_ANCHOR_FLOWERS,
	PC_COOP_ANCHOR_COUNT
};
const char* pc_coop_anchor_name(PcCoopAnchorKind kind);

struct PcCoopCursors {
	int next[PC_COOP_ANCHOR_COUNT]; // captain (1 or 2) tried first for each kind
};
// Every cursor starts on P1.
void pc_coop_cursors_reset(PcCoopCursors& cursors);
// Try order for one attempt: the cursor's captain first if it is live, then
// the other live captain (same tick). live[i] is captain i+1. Writes up to
// two captain ids into order[] and returns how many.
int pc_coop_anchor_order(const PcCoopCursors& cursors, PcCoopAnchorKind kind,
                         const bool live[PC_COOP_CAPTAINS], int order[PC_COOP_CAPTAINS]);
// After a successful consume by captain `succeeded` (1 or 2), point the
// cursor at the captain after it (with two captains: the other one).
// Returns the new cursor value.
int pc_coop_anchor_advance(PcCoopCursors& cursors, PcCoopAnchorKind kind, int succeeded);

// One anchored grant attempt, the loop the engine runs (gameCoreSection.cpp
// coopAnchored calls exactly this). place(captain, ctx) tries to place the
// grant on that captain: FAILED lets the next captain in the order try in the
// same tick; CONSUMED ends the attempt and advances the cursor past that
// captain; STOP ends the attempt with no consume and no cursor move.
enum PcCoopPlaceResult { PC_COOP_PLACE_FAILED = 0, PC_COOP_PLACE_CONSUMED, PC_COOP_PLACE_STOP };
enum PcCoopSkipReason { PC_COOP_SKIP_NOT_LIVE = 1, PC_COOP_SKIP_PLACEMENT };
typedef PcCoopPlaceResult (*PcCoopPlaceFn)(int captain, void* ctx);
struct PcCoopAnchorAttempt {
	int captain;   // consuming captain (1 or 2); 0 = nobody placed; -1 = STOP
	int cursor;    // the cursor captain before the attempt
	int next;      // the cursor after the attempt (unchanged unless consumed)
	int skipCount; // captains passed over, in order: the cursor captain when
	               // not live, then every captain whose placement FAILED
	int skipCaptain[PC_COOP_CAPTAINS];
	PcCoopSkipReason skipReason[PC_COOP_CAPTAINS];
};
PcCoopAnchorAttempt pc_coop_anchor_try(PcCoopCursors& cursors, PcCoopAnchorKind kind,
                                       const bool live[PC_COOP_CAPTAINS], PcCoopPlaceFn place, void* ctx);
const char* pc_coop_skip_reason_name(PcCoopSkipReason reason);

// Per-stage reset of the co-op policy state (cursors, HP samples, tick).
// The day number alone is not a stage-entry edge: pc_randomizer_next_day
// pins it at 29 from day 28 on, and a same-day reload keeps it. A new stage
// entry always restarts the world clock at the stage's start hour, so the
// time of day going backwards is the edge those cases need.
struct PcCoopStageKey {
	int stage;       // flowCont.mCurrentStage->mStageID, -1 when none
	int day;         // gameflow.mWorldClock.mCurrentDay
	float timeOfDay; // gameflow.mWorldClock.mTimeOfDay
};
// True when the state must reset: the first call (!started), a stage or day
// change, or the time of day going backwards. *reason (optional) is set to
// "start", "stage", "day" or "clock".
bool pc_coop_stage_changed(bool started, const PcCoopStageKey& prev, const PcCoopStageKey& cur, const char** reason);

// Test knob (PIKMIN_NETPLAY_TEST_COOP_EVENTS=<file>): at most
// PC_COOP_EVENTS_MAX lines, each `<tick> HP <1|2> <fraction 0..1>` or
// `<tick> DOWN <1|2>`. Blank lines and `#` comments are skipped. <tick>
// counts co-op randomizer updateAI calls since the stage started; it is
// 1-based (the first co-op tick of a stage is tick 1), so tick 0 is
// rejected. The file is parsed once per process and the tick restarts on
// every stage entry, so the schedule re-arms each stage/day (logged).
// M4 gap-fix K (#885) adds day-end kinds, so a pair reaches a co-op sunset
// with captain 2 owning Pikmin in a few hundred ticks instead of ~26,500:
//   `<tick> SQUAD <1|2> <count 1..200>`  up to <count> Pikmin in the other
//                                         captain's squad join this one's
//   `<tick> DISMISS <1|2>`                that captain's squad goes free
//                                         where it stands (still owned by it)
//   `<tick> HOME <1|2>`                   that captain's free Pikmin stand by
//                                         their Onion (or the ship), inside
//                                         the sunset safety range
//   `<tick> SUNSET`                       the clock jumps to the day's end
//                                         hour; the normal day end follows
// The day end sets the clock back and re-arms the schedule inside the day-end sequence: these four kinds are
// refused there (reason=day-end) and fire again on the next stage/day, like HP/DOWN. DISMISS is
// Navi::releasePikis, which walks the plate the captain's control update refreshes, so it releases nobody
// during the stage-start movie; SUNSET is refused there (reason=stage-start). Committed fixtures:
// tools/netplay/fixtures/coop_dayend_{home,squad}.events (docs/NETPLAY_COOP_POLICY.md).
enum { PC_COOP_EVENTS_MAX = 64, PC_COOP_EVENT_TEXT = 48, PC_COOP_EVENT_SQUAD_MAX = 200 };
enum PcCoopEventKind {
	PC_COOP_EVENT_HP = 0,
	PC_COOP_EVENT_DOWN,
	PC_COOP_EVENT_SQUAD,
	PC_COOP_EVENT_DISMISS,
	PC_COOP_EVENT_SUNSET,
	PC_COOP_EVENT_HOME
};
struct PcCoopEvent {
	unsigned tick;
	PcCoopEventKind kind;
	int captain;       // 1 or 2 (0 for SUNSET)
	float fraction;    // HP only, 0..1 of max HP
	int count;         // SQUAD only, 1..PC_COOP_EVENT_SQUAD_MAX
	char text[PC_COOP_EVENT_TEXT]; // canonical form for the log line
};
// Parses the whole file text. Returns the event count (0..max), or -1 on a
// malformed line or too many lines (*badLine = 1-based line number).
int pc_coop_events_parse(const char* text, PcCoopEvent* out, int max, int* badLine);

// Reads and parses the events file. A file larger than
// PC_COOP_EVENTS_FILE_MAX bytes is rejected whole (never truncated). Returns
// the event count, or -1 with *why = "unreadable", "too-large" or "bad-line"
// (then *badLine is the 1-based line).
enum { PC_COOP_EVENTS_FILE_MAX = 16384 };
int pc_coop_events_load(const char* path, PcCoopEvent* out, int max, const char** why, int* badLine);

// The knob's file path, or nullptr. The knob mutates the sim, so it is
// compiled only into the netplay build (PIKI_NETPLAY_BUILD) and honoured
// only in hidden test runs (PIKMIN_RANDOMIZER_TEST_BACKGROUND=1). The
// default build never reads the variable.
const char* pc_coop_events_knob_path();

// Netplay gapfix C (issue #885): handshake config hash input for the knob.
// FNV-1a 64 over the file's bytes; 0 when path is null (knob unset, or not
// honoured: default build or not a hidden test run). An unreadable file
// hashes as zero bytes (the FNV-1a offset basis), which still differs from
// "no knob". The session folds pc_coop_events_config_hash() into the config
// string as `coopEvents`, so a pair whose peers load different event files
// (or only one of them) is refused with "handshake refused: config".
uint64_t pc_coop_events_file_hash(const char* path);
uint64_t pc_coop_events_config_hash();

// Netplay gapfix C (issue #885): the co-op policy's sim state, as the
// per-tick state hash folds it (pc_state_hash.cpp, rand sub-hash) while the
// co-op branch is active. Decision state only: the per-stage policy state
// (reset key, tick, cursors, the HP samples of rule 1) and the three co-op
// cooldowns (bomb trap, Progg, nectar), which persist across stages. The
// fixture read-back fields and log-only text are not sim state.
enum { PC_COOP_COOLDOWNS = 3 };
struct PcCoopHashState {
	bool started;
	PcCoopStageKey key;
	unsigned tick;
	PcCoopCursors cursors;
	float prevHp[PC_COOP_CAPTAINS];
	bool prevValid[PC_COOP_CAPTAINS];
	float cooldown[PC_COOP_COOLDOWNS]; // bomb trap, Progg, nectar
};
// FNV-1a 64 over every field in declaration order, little-endian, floats
// by their bit patterns. Never 0.
uint64_t pc_coop_state_hash(const PcCoopHashState& state);

// Test knob (PIKMIN_NETPLAY_TEST_COOP_PERTURB=<tick>): at that co-op tick
// one peer flips its Flower Shower cursor, a change nothing else in the sim
// reads until the next Flower Shower, so only the state-hash fold can see
// it. It proves desync detection for the co-op policy state, so it is
// deliberately NOT in the handshake config hash. Compiled only into the
// netplay build and honoured only in hidden test runs, like the events
// knob; 0 when unset, not honoured or not a positive decimal.
unsigned pc_coop_perturb_knob_tick();

// Onion exit routing (issue #1028). GoalItem::exitPiki used to hand every
// Pikmin to captain 1, so what captain 2 took out of the Onion joined the
// wrong squad. Each Onion keeps how many exits are still owed to each captain
// (navi id 0 / 1, the captain whose Onion menu asked); the next Pikmin goes to
// the lowest-id captain that is owed one, and that debt shrinks. Returns -1
// when nobody is owed one (a start-of-day or scripted exit: the default
// captain, as before). Pure and RNG-free, so both lockstep peers agree.
inline int pc_coop_onion_exit_next(int owed[PC_COOP_CAPTAINS])
{
	for (int id = 0; id < PC_COOP_CAPTAINS; id++) {
		if (owed[id] > 0) {
			owed[id]--;
			return id;
		}
	}
	return -1;
}

// Issue #1028 review minor: the captain who asked may have been downed while
// the Onion was still dispensing. A downed captain cannot lead a squad, so the
// Pikmin join the other captain if that one is alive; if neither is alive the
// requester keeps them. live[] is indexed by navi id (0 / 1).
inline int pc_coop_onion_exit_target(int requesterId, const bool live[PC_COOP_CAPTAINS])
{
	if (requesterId < 0 || requesterId >= PC_COOP_CAPTAINS || live[requesterId]) {
		return requesterId;
	}
	for (int id = 0; id < PC_COOP_CAPTAINS; id++) {
		if (id != requesterId && live[id]) {
			return id;
		}
	}
	return requesterId;
}

#endif // PC_COOP_POLICY_H
