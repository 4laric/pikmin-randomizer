#pragma once
#include <cstdint>
#include <string>
#include <optional>
class Creature; class Navi; class NaviState; class MoviePlayer;

// #1289: source-owned contracts. Implementations must be actual loaded source
// lifecycle/FSM owners. P1/AP flags, native state IDs and prepared assets are
// not implementations of these interfaces. Doubles establish controls only.
namespace p2original { namespace captain {
enum class Phase { Loading, GameWorldActive, Inactive };
enum class Demo { Unknown, Absent, Inactive, Playing };
// Retail Game/NaviState.h identities, deliberately distinct from P1 IDs.
enum class StateId { Walk=0, Follow=1, Punch=2, Change=3, Gather=4, Throw=5,
 ThrowWait=6, Dope=7, Nuku=8, NukuAdjust=9, Container=10, Absorb=11,
 Flick=12, Damaged=13, Pressed=14, FallMeck=15, KokeDamage=16,
 Sarai=17, SaraiExit=18, Dead=19, Stuck=20, DemoUfo=21,
 DemoHoleIn=22, Pellet=23, CarryBomb=24, Climb=25, PathMove=26 };
class State {
public:
 virtual ~State()=default;
 // Pointer must be the live Navi::getCurrState(), not a cached source label.
 virtual const NaviState* nativeState() const=0;
 virtual StateId sourceStateId() const=0;
 // Retail Creature::CF_IsAlive; native Creature::isAlive() is HP>0 and
 // cannot supply this fact. Source actor lifetime owner supplies it.
 virtual bool sourceAlive(const Navi&) const=0;
 virtual bool sourceInvincible() const=0;
 // Actor-owned source mInvincibleTimer, never a P1 hurt/flick timer.
 virtual std::optional<std::uint8_t> actorInvincibleFrames(const Navi&) const=0;
 // Must preflight a genuine source Dead transition BEFORE HP mutation.
 virtual bool canEnterSourceDead(const Navi&) const=0;
 virtual void enterSourceDead(Navi&)=0;
 // Retail optional feedback. No P1 startDamageEffect/Mods damage wrapper.
 virtual void sourceDamageFeedback(Navi&)=0;
};
// Concrete source startup owns this descriptor; Runtime only accepts the
// canonical live query. Course loading alone does not activate the world.
class LoadedScene {
public:
 virtual ~LoadedScene()=default;
 virtual const std::string& selectedCampaign() const=0;
 virtual const std::string& selectedFingerprint() const=0;
 virtual const std::string& sourceCatalog() const=0;
 virtual MoviePlayer* moviePlayer() const=0;
 virtual std::uint64_t incarnation() const=0;
 virtual Navi* captainAt(unsigned slot) const=0;
};
class World {
public:
 virtual ~World()=default;
 virtual const std::string& selectedCampaign() const=0;
 virtual const std::string& selectedFingerprint() const=0;
 virtual std::uint64_t incarnation() const=0;
 virtual const std::string& sourceCatalog() const=0;
 virtual Phase phase() const=0;
 virtual Demo demo() const=0;
 // Both source roster slots, including inactive partner; no active-only query.
 virtual Navi* captainAt(unsigned slot) const=0;
};
enum class Refusal { None, MissingWorld, WrongSession, InactiveWorld,
 MissingCaptain, MissingSourceState, InvalidHealth, InvalidDamage,
 MissingMovieAuthority, DemoPlaying, NotAlive, StateInvincible, MissingActorAuthority, ActorInvincible, MissingDeadTransition,
 NotReunited, MissingEnemy };
struct DamageResult {
 Refusal refusal=Refusal::MissingWorld;
 float applied=0;
 bool knockedOut=false;
 explicit operator bool() const { return refusal==Refusal::None; }
};
// Requeries world/session/FSM/timer on each call. Raw damage is reduced once
// here; source Flick invokes it only at Koke END, not at interaction admission.
DamageResult addDamage(Navi*,float rawDamage,bool playFeedback);
// InteractFlick's outer active-world + DEMO_Reunite_Captains guard. This does
// not apply addDamage's later immunity checks early or consume RNG.
Refusal flickAdmission(const Creature* authenticatedEnemy,const Navi*);
} }
// Concrete original startup owner supplies this read-only typed query. Missing
// producer means refusal. No public setter accepts an "authenticated" bool.
const p2original::captain::World* pc_p2_original_captain_world();

const p2original::captain::LoadedScene* pc_p2_original_captain_loaded_scene();
// Actual engine event hooks. No call accepts a source-ready/authentication bool.
// An absent/wrong selected LoadedScene refuses activation and actor writes.
void pc_p2_original_captain_main_game_entered();
void pc_p2_original_captain_main_game_left();
void pc_p2_original_captain_movie_started(MoviePlayer*);
void pc_p2_original_captain_movie_ended(MoviePlayer*);
void pc_p2_original_captain_actor_update(Navi*);
// Query actor lifetime/iframes only for the exact live source scene roster.
bool pc_p2_original_captain_actor_alive(const Navi*);
bool pc_p2_original_captain_actor_frames(const Navi*,std::uint8_t&);
// Source state owners call these at actual Damaged::cleanup/Dead::init; both
// verify the current genuine State identity. Unsupported states cannot write.
bool pc_p2_original_captain_damaged_cleanup(Navi*);
bool pc_p2_original_captain_dead_entered(Navi*);
