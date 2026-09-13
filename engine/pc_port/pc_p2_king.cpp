// Emperor Bulblax (KingChappy, enemy ID 53) sampled actor (#289, parent #172).
// Extends the #234 sampled display bank with a behavior FSM mirrored from
// experimental/pikmin2_bulblax_behavior.py (#227, KingChappy section).
// Actor-local receivers only: generic physics/damage, captain states,
// manager/heap lifetime and save/reward code are untouched. The decomp
// collisionCallback no-op quirk is recorded, not "fixed".
#include "pc_p2_king.h"
#include "pc_p2_actor_slots.h"
#include "pc_p2_king_policy.h"
#include "pc_p2_animation.h"
#include "pc_bbft.h"
#include "Shape.h"
#include "Texture.h"
#include "Graphics.h"
#include "Camera.h"
#include "gameflow.h"
#include "Piki.h"
#include "PikiMgr.h"
#include "PikiState.h"
#include "NaviMgr.h"
#include "Navi.h"
#include "Interactions.h"
#include "MapMgr.h"
#include <SDL.h>
#include <map>
#include <set>
#include <vector>
#include <string>
#include <fstream>
#include <cmath>
#include <cstdio>
#include <cstdlib>
namespace {
constexpr float Tick = 1.0f / 30.0f; // 30 Hz bounded behavior clock
constexpr int StuckMax = 32;         // bounded stuck-Pikmin receiver set
constexpr float RootRadius = 80.0f;  // kingchappy/enemycoll.txt root
constexpr float KingSight = 300.0f;          // approximation (not pinned by #227)
constexpr float KingAttackRange = 120.0f;    // approximation: tongue reach trigger
constexpr float KingAttackAngleDeg = 45.0f;  // approximation (checkAttack reconstructed)
constexpr float KingBombAttackRange = 150.0f; // approximation for beyond-80 bomb targeting
constexpr float HomeRadius = 25.0f;          // approximation (return-home bound)
constexpr float TurnRateDeg = 3.0f;          // approximation per tick
constexpr float ExternalBlastRange = 100.0f; // approximation (fixture injection)
p2king::ActorConfig config;
std::map<size_t, std::vector<Shape*>> shapes; // clip index -> pose shapes
size_t totalBytes = 0;

// Actor-local BOMB_Wait stub (enemy ID 36). States mirror the #227 contract:
// only BOMB_Wait is eatable. External blasts are fixture injections.
struct Bomb {
	p2king::BombPlacement cfg;
	int state = 0; // 0 = BOMB_Wait, 1 = eaten, 2 = externally detonated
};
struct King {
	p2king::Placement cfg;
	p2king::VariantInfo info;
	int state = p2king::HideWait;
	float frame = 0;
	float x = 0, y = 0, z = 0, yaw = 0;
	float homeX = 0, homeZ = 0;
	float health = p2king::HealthDefault;
	uint32_t rng = 1;
	// receivers
	Piki* stuck[StuckMax] = {};
	int stuckCount = 0;
	int blows = 0;
	int flickTier = 0;
	// mouth (9 slots kamu1..9)
	Piki* mouth[p2king::MouthSlots] = {};
	int mouthPikmin = 0;
	int mouthBombs = 0;
	// timers
	int framesWaited = 0;       // HideWait
	int framesWithoutTarget = 0; // Walk incubation
	int stunFrames = 0;          // Damage bomb stun
	bool attackArmed = false;
	bool bombArmed = false;
	bool attackAborted = false;
	int whiffStreak = 0; // consecutive licks that connected with nothing (whiff or terrain abort)
	int eatsThisLick = 0;
	bool damageKeyDone = false;
	bool captainHitDone = false;
	bool turnLeft = false;
	bool loggedDead = false;
	bool loggedDive = false;
	float nextRoll() {
		rng = rng * 1664525u + 1013904223u;
		return float(rng >> 8) / 16777216.0f;
	}
};
std::vector<King> kings;
std::vector<Bomb> bombs;
unsigned clockLast = 0;
float clockAcc = 0;
unsigned long behaviorTick = 0;
// Opt-in fixture-only injection (inactive without p2-king-inject.txt): force
// one Emperor into WarCry at a behavior tick so the WarCry astonish and the
// cross-Emperor manager contract can be exercised deterministically. Default
// 0 disables it; nothing here runs for a normal profile.
uint32_t injectWarCryId = 0;
unsigned long injectWarCryTick = 0;
bool injectWarCryDone = false;
unsigned long injectKillTick = 0;
bool injectKillDone = false;
unsigned long injectBombTick = 0;
bool injectBombDone = false;
unsigned long injectTongueTick = 0;
bool injectTongueDone = false;
// Fixture-observation flag: set when the Dead clip reaches its frame-185 kill
// key. Read-only fixture gate; no effect on actor behavior.
bool deadKeySeen = false;

void fail() {
	std::fputs("P2_KING_ACTOR invalid profile/model\n", stderr);
	std::abort();
}
const char* stateClip(int state, bool turnLeft) {
	switch (state) {
	case p2king::Walk: return "move1";
	case p2king::Attack: return "attack";
	case p2king::Dead: return "dead";
	case p2king::Flick: return "flick";
	case p2king::WarCry: return "cry";
	case p2king::Damage: return "damage";
	case p2king::Turn: return turnLeft ? "type1" : "type2";
	case p2king::Eat: return "waitact2";
	case p2king::Hide: return "dive";
	case p2king::HideWait: return "wait2";
	case p2king::Appear: return "type3";
	case p2king::Caution: return "waitact1";
	case p2king::Swallow: return "waitact1";
	}
	return "wait2";
}
Shape* load(const std::string& name, std::vector<unsigned char>& reference, size_t& clipBytes) {
	std::ifstream in("assets/dataDir/courses/pikmin2room/" + name, std::ios::binary | std::ios::ate);
	if (!in) fail();
	auto size = in.tellg();
	if (size <= 0 || size > 1024 * 1024 || clipBytes + size_t(size) > 1024 * 1024 || totalBytes + size_t(size) > 16 * 1024 * 1024)
		fail();
	clipBytes += size_t(size);
	totalBytes += size_t(size);
	in.seekg(0);
	std::vector<unsigned char> data(size_t(size), 0), resources;
	if (!in.read(reinterpret_cast<char*>(data.data()), size) || !p2animation::resources(data, resources)) fail();
	if (!reference.empty() && reference != resources) fail();
	reference = resources;
	Shape* shape = gameflow.loadShape(("courses/pikmin2room/" + name).c_str(), true);
	if (!shape) fail();
	for (int i = 0; i < shape->mTexAttrCount; ++i)
		if (shape->mTexAttrList[i].mTexture) shape->mTexAttrList[i].mTexture->attach();
	return shape;
}

void enter(King& k, int state) {
	k.state = state;
	k.frame = 0;
	if (state == p2king::HideWait) k.framesWaited = 0;
	if (state == p2king::Attack) {
		k.attackArmed = false;
		k.bombArmed = false;
		k.attackAborted = false;
		k.eatsThisLick = 0;
		k.captainHitDone = false;
	}
	if (state == p2king::Damage) k.damageKeyDone = false;
}

// Mouth position approximation: all 9 kamu slots sit at the mouth point in
// front of the Emperor; slot radius 25 * scale. Recorded approximation.
void mouthPos(const King& k, float& mx, float& mz) {
	const float rad = k.yaw * 0.0174532925199433f;
	const float front = 30.0f * k.info.scale;
	mx = k.x + std::sin(rad) * front;
	mz = k.z + std::cos(rad) * front;
}
float nearestTargetDistance(King& k) {
	float best = 1.0e9f;
	if (pikiMgr) {
		Iterator it(pikiMgr);
		CI_LOOP(it) {
			Piki* p = static_cast<Piki*>(*it);
			if (!p || !p->isAlive()) continue;
			const Vector3f& pos = p->getPosition();
			const float dx = pos.x - k.x, dz = pos.z - k.z;
			const float d = std::sqrt(dx * dx + dz * dz);
			if (d < best) best = d;
		}
	}
	if (naviMgr && naviMgr->getNavi()) {
		const Vector3f& pos = naviMgr->getNavi()->getPosition();
		const float dx = pos.x - k.x, dz = pos.z - k.z;
		const float d = std::sqrt(dx * dx + dz * dz);
		if (d < best) best = d;
	}
	return best;
}

void receiveScan(King& k) {
	// Actor-local Pikmin-attack receiver. Buried/hidden states keep the hard
	// constraint on: nothing sticks. The collisionCallback no-op quirk means
	// no extra part-specific channel is synthesized here.
	if (!pikiMgr || k.state == p2king::Dead || k.state == p2king::HideWait || k.state == p2king::Hide) return;
	const float root = RootRadius * k.info.scale;
	Iterator it(pikiMgr);
	CI_LOOP(it) {
		Piki* p = static_cast<Piki*>(*it);
		if (!p || !p->isAlive()) continue;
		const Vector3f& pos = p->getPosition();
		const float dx = pos.x - k.x, dy = pos.y - k.y, dz = pos.z - k.z;
		if (dx * dx + dy * dy + dz * dz > root * root) continue;
		bool known = false;
		for (int i = 0; i < k.stuckCount; ++i)
			if (k.stuck[i] == p) known = true;
		if (known || k.stuckCount >= StuckMax) continue;
		k.stuck[k.stuckCount++] = p;
		++k.blows;
		// Approximate per-blow Pikmin damage of 1 (part-stuck tier x1 from the
		// policy; the P1 per-color blow strength is out of scope).
		k.health -= 1.0f * p2king::damageTier(false, true, true, 0.0f, 0.0f);
		if (k.health < 0.0f) k.health = 0.0f;
	}
	for (int i = 0; i < k.stuckCount; ++i) {
		Piki* p = k.stuck[i];
		if (!p || !p->isAlive()) {
			k.stuck[i] = k.stuck[--k.stuckCount];
			--i;
		}
	}
}

void shakeOff(King& k, float range, float power, const char* tag) {
	const float rad = k.yaw * 0.0174532925199433f;
	const float facing = std::atan2(std::sin(rad), std::cos(rad));
	int shaken = 0;
	if (pikiMgr) {
		Iterator it(pikiMgr);
		CI_LOOP(it) {
			Piki* p = static_cast<Piki*>(*it);
			if (!p || !p->isAlive()) continue;
			const Vector3f& pos = p->getPosition();
			const float dx = pos.x - k.x, dz = pos.z - k.z;
			if (dx * dx + dz * dz > range * range) continue;
			InteractFlick flick(nullptr, power, 0.0f, std::atan2(dx, dz));
			p->stimulate(flick);
			++shaken;
		}
	}
	(void)facing;
	std::printf("P2_KING_SHAKEOFF id=%u %s range=%.0f power=%.0f shaken=%d\n", k.cfg.id, tag, range, power, shaken);
}

void flickStuck(King& k) {
	for (int i = 0; i < k.stuckCount; ++i) {
		Piki* p = k.stuck[i];
		if (!p || !p->isAlive()) continue;
		const Vector3f& pos = p->getPosition();
		InteractFlick flick(nullptr, p2king::AppearShakeOffPower, 1.0f, std::atan2(pos.x - k.x, pos.z - k.z));
		p->stimulate(flick);
	}
	std::printf("P2_KING_FLICK id=%u shaken=%d shake_range=60\n", k.cfg.id, k.stuckCount);
	k.stuckCount = 0;
	k.blows = 0;
	if (k.flickTier < 3) ++k.flickTier;
}

void trampleScan(King& k) {
	// Flick key 3: press every Pikmin and captain within mTramplingRange (45) *
	// scale of the foot position in a 30 unit height band; captains are only
	// flicked if none was pressed. Foot position approximation: front offset.
	const float rad = k.yaw * 0.0174532925199433f;
	const float fx = k.x + std::sin(rad) * 20.0f * k.info.scale;
	const float fz = k.z + std::cos(rad) * 20.0f * k.info.scale;
	const float range = p2king::TramplingRange * k.info.scale;
	int pressedPikmin = 0, pressedCaptains = 0;
	if (pikiMgr) {
		Iterator it(pikiMgr);
		CI_LOOP(it) {
			Piki* p = static_cast<Piki*>(*it);
			if (!p || !p->isAlive() || p->getState() == PIKISTATE_Pressed) continue;
			const Vector3f& pos = p->getPosition();
			const float dx = pos.x - fx, dz = pos.z - fz;
			if (dx * dx + dz * dz > range * range) continue;
			if (std::fabs(pos.y - k.y) > p2king::TrampleHeightBand) continue;
			InteractPress press(nullptr, p2king::AttackDamage);
			p->stimulate(press);
			++pressedPikmin;
		}
	}
	if (naviMgr && naviMgr->getNavi()) {
		Navi* n = naviMgr->getNavi();
		const Vector3f& pos = n->getPosition();
		const float dx = pos.x - fx, dz = pos.z - fz;
		if (dx * dx + dz * dz <= range * range && std::fabs(pos.y - k.y) <= p2king::TrampleHeightBand) {
			InteractPress press(nullptr, p2king::AttackDamage);
			n->stimulate(press);
			++pressedCaptains;
		}
	}
	const p2king::FlickStep step = p2king::flickStep(pressedPikmin, pressedCaptains);
	std::printf("P2_KING_TRAMPLE id=%u pressed_pikmin=%d pressed_captains=%d flick_captains=%d range=%.1f band=30\n",
	            k.cfg.id, step.pressedPikmin, step.pressedCaptains, int(step.flickCaptains), range);
	if (step.flickCaptains && naviMgr && naviMgr->getNavi()) {
		Navi* n = naviMgr->getNavi();
		const Vector3f& pos = n->getPosition();
		const float dx = pos.x - k.x, dz = pos.z - k.z;
		if (dx * dx + dz * dz <= p2king::ShakeRange * p2king::ShakeRange) {
			InteractFlick flick(nullptr, p2king::AppearShakeOffPower, 0.0f, std::atan2(dx, dz));
			n->stimulate(flick);
		}
	}
	flickStuck(k);
}

void astonishScan(King& k) {
	// WarCry key 4: astonish Pikmin within mRoarEffectiveRange (300 disc) and
	// mRoarEffectiveAngleDeg (180 disc). No InteractAstonish exists in the P1
	// runtime: approximated as a zero-damage flick, recorded approximation.
	const float rad = k.yaw * 0.0174532925199433f;
	int hit = 0;
	if (pikiMgr) {
		Iterator it(pikiMgr);
		CI_LOOP(it) {
			Piki* p = static_cast<Piki*>(*it);
			if (!p || !p->isAlive()) continue;
			const Vector3f& pos = p->getPosition();
			const float dx = pos.x - k.x, dz = pos.z - k.z;
			const float dist = std::sqrt(dx * dx + dz * dz);
			if (dist > p2king::RoarEffectiveRange) continue;
			float rel = std::atan2(dx, dz) - std::atan2(std::sin(rad), std::cos(rad));
			while (rel > 3.14159265f) rel -= 6.2831853f;
			while (rel < -3.14159265f) rel += 6.2831853f;
			if (std::fabs(rel) > p2king::RoarEffectiveAngleDeg * 0.5f * 0.0174532925199433f) continue;
			InteractFlick flick(nullptr, 100.0f, 0.0f, std::atan2(dx, dz));
			p->stimulate(flick);
			++hit;
		}
	}
	std::printf("P2_KING_ASTONISH id=%u range=300 angle=180 affected=%d approx=flick\n", k.cfg.id, hit);
}

void crossEmperorRequest(King& k) {
	// WarCry key 3 cross-Emperor contract (actor-family-local, two-Emperor
	// scope): wake one buried Emperor, else make one walking Emperor roar.
	for (auto& other : kings) {
		if (&other == &k) continue;
		const int target = p2king::crossEmperorTarget(other.state);
		if (target < 0) continue;
		std::printf("P2_KING_WARCRY_REQUEST id=%u other=%u from=%d to=%d force_transit=1\n", k.cfg.id, other.cfg.id,
		            other.state, target);
		enter(other, target);
		return;
	}
	std::printf("P2_KING_WARCRY_REQUEST id=%u other=none\n", k.cfg.id);
}

void eatScan(King& k) {
	// Armed tongue frames: try eatBomb (key 6 armed) and eatPikmin (key 3/6).
	// Mouth approximation: the 9 kamu slots sweep the tongue segment from the
	// Emperor to the mouth point; anything within slot radius of that segment
	// is in a slot (recorded approximation).
	float mx, mz;
	mouthPos(k, mx, mz);
	const float slotRadius = p2king::MouthSlotRadius * k.info.scale;
	auto slotDistance = [&](float px, float pz) {
		const float sx = mx - k.x, sz = mz - k.z;
		const float len2 = sx * sx + sz * sz;
		float t = len2 > 1.0e-6f ? ((px - k.x) * sx + (pz - k.z) * sz) / len2 : 0.0f;
		t = t < 0.0f ? 0.0f : t > 1.0f ? 1.0f : t;
		const float dx = px - (k.x + sx * t), dz = pz - (k.z + sz * t);
		return std::sqrt(dx * dx + dz * dz);
	};
	// Bombs ride the retracting tongue from the bero6 tip (reach 100 * scale,
	// approximation) back to the mouth: sweep the full tongue segment.
	const float rad = k.yaw * 0.0174532925199433f;
	const float tx = std::sin(rad) * 100.0f * k.info.scale, tz = std::cos(rad) * 100.0f * k.info.scale;
	auto tongueDistance = [&](float px, float pz) {
		const float len2 = tx * tx + tz * tz;
		float t = len2 > 1.0e-6f ? ((px - k.x) * tx + (pz - k.z) * tz) / len2 : 0.0f;
		t = t < 0.0f ? 0.0f : t > 1.0f ? 1.0f : t;
		const float dx = px - (k.x + tx * t), dz = pz - (k.z + tz * t);
		return std::sqrt(dx * dx + dz * dz);
	};
	bool pikminInRange = false, bombsInRange = false;
	if (pikiMgr) {
		Iterator it(pikiMgr);
		CI_LOOP(it) {
			Piki* p = static_cast<Piki*>(*it);
			if (!p || !p->isAlive()) continue;
			const Vector3f& pos = p->getPosition();
			if (slotDistance(pos.x, pos.z) <= slotRadius) pikminInRange = true;
		}
	}
	for (const auto& b : bombs) {
		if (b.state != 0) continue; // only BOMB_Wait is eatable
		if (tongueDistance(b.cfg.x, b.cfg.z) <= slotRadius) bombsInRange = true;
	}
	const bool slotsFree = k.mouthPikmin + k.mouthBombs < p2king::MouthSlots;
	// Armed frames repeat every frame while armed (each armed frame tries).
	const int actions = p2king::attackStep(k.bombArmed ? 6 : k.attackArmed ? 3 : 0, slotsFree, bombsInRange, pikminInRange);
	if ((actions & 1) && pikiMgr) {
		Iterator it(pikiMgr);
		CI_LOOP(it) {
			Piki* p = static_cast<Piki*>(*it);
			if (!p || !p->isAlive()) continue;
			const Vector3f& pos = p->getPosition();
			if (slotDistance(pos.x, pos.z) > slotRadius) continue;
			if (k.mouthPikmin >= p2king::MouthSlots) break;
			bool held = false;
			for (int i = 0; i < k.mouthPikmin; ++i)
				if (k.mouth[i] == p) held = true;
			if (held) continue;
			k.mouth[k.mouthPikmin++] = p;
			++k.eatsThisLick;
			std::printf("P2_KING_EAT id=%u piki=%p slot=%d radius=%.1f\n", k.cfg.id, (void*)p, k.mouthPikmin - 1,
		            slotRadius);
		}
	}
	if (actions & 2) {
		for (auto& b : bombs) {
			if (b.state != 0) continue;
			if (tongueDistance(b.cfg.x, b.cfg.z) > slotRadius) continue;
			if (k.mouthPikmin + k.mouthBombs >= p2king::MouthSlots) break;
			b.state = 1; // eaten
			++k.mouthBombs;
			++k.eatsThisLick;
			std::printf("P2_KING_EAT_BOMB id=%u bomb=%u state=BOMB_Wait slot_count=%d\n", k.cfg.id, b.cfg.id,
			            k.mouthBombs);
		}
	}
	// Captains in any mouth slot take mAttackDamage (5 disc), once per lick.
	if (k.attackArmed && !k.captainHitDone && naviMgr && naviMgr->getNavi()) {
		Navi* n = naviMgr->getNavi();
		const Vector3f& pos = n->getPosition();
		if (slotDistance(pos.x, pos.z) <= slotRadius) {
			k.captainHitDone = true;
			InteractPress press(nullptr, p2king::AttackDamage);
			n->stimulate(press);
			std::printf("P2_KING_CAPTAIN_HIT id=%u damage=5 slot_radius=%.1f\n", k.cfg.id, slotRadius);
		}
	}
}

void tongueTipScan(King& k) {
	// Tongue tip (bero6-equivalent, radius 5) aborts the lick on floor/wall.
	// Tip extends forward while armed; reach approximation 100 * scale.
	if (!k.attackArmed || k.attackAborted || !mapMgr) return;
	const float reach = 100.0f * k.info.scale;
	const float t = (k.frame - float(p2king::AttackArmKey)) / float(86 - p2king::AttackArmKey);
	const float dist = reach * (t < 0.0f ? 0.0f : t > 1.0f ? 1.0f : t);
	const float rad = k.yaw * 0.0174532925199433f;
	const float tx = k.x + std::sin(rad) * dist;
	const float tz = k.z + std::cos(rad) * dist;
	const float ground = mapMgr->getMinY(tx, tz, true);
	if (ground > k.y + p2king::TongueTipRadius) { // wall or steep rise at the tip
		k.attackAborted = true;
		std::printf("P2_KING_TONGUE_ABORT id=%u frame=%.0f ground=%.3f y=%.3f tip_radius=5\n", k.cfg.id, k.frame, ground,
		            k.y);
	}
}

void damageKillKey(King& k) {
	// Damage key 4: kills everything in the mouth, applies bombs * mBombDamage
	// (200), then stuns for mBombDamageTime frames (180 disc).
	int killed = 0;
	for (int i = 0; i < k.mouthPikmin; ++i) {
		Piki* p = k.mouth[i];
		if (p && p->isAlive()) {
			InteractSwallow swallow(nullptr, nullptr, 0);
			p->stimulate(swallow);
			++killed;
		}
		k.mouth[i] = nullptr;
	}
	k.mouthPikmin = 0;
	const float damage = p2king::bombDamage(k.mouthBombs);
	k.health -= damage;
	if (k.health < 0.0f) k.health = 0.0f;
	k.stunFrames = p2king::BombDamageTime;
	std::printf("P2_KING_BOMB_DAMAGE id=%u bombs=%d damage=%.0f killed_mouth=%d stun_frames=180 health=%.1f\n", k.cfg.id,
	            k.mouthBombs, damage, killed, k.health);
	k.mouthBombs = 0;
	k.damageKeyDone = true;
}

void swallowMouth(King& k) {
	// Swallow entry: poison damage 300 hardcoded (the #227 finding; fp14 header
	// 300 / disc 200 stays distinct in config). Pikmin die via InteractSwallow
	// with no mouth part (P1 runtime kills with the eaten event).
	int swallowed = 0;
	for (int i = 0; i < k.mouthPikmin; ++i) {
		Piki* p = k.mouth[i];
		if (p && p->isAlive()) {
			InteractSwallow swallow(nullptr, nullptr, 0);
			p->stimulate(swallow);
			++swallowed;
		}
		k.mouth[i] = nullptr;
	}
	std::printf("P2_KING_SWALLOW id=%u count=%d poison_damage=300 hardcoded=1 fp14_header=300 fp14_disc=200\n", k.cfg.id,
	            swallowed);
	k.mouthPikmin = 0;
}

void tickKing(King& k) {
	receiveScan(k);
	// Approximation: tiered shake-off thresholds mirror the family-wide general
	// parms (blows 30/35/45/50, sticking 5/10/15); KingChappy-specific disc
	// thresholds are not pinned by the #227 reference.
	const int blowTier = k.flickTier > 3 ? 3 : k.flickTier;
	const int stickTier = k.flickTier > 2 ? 2 : k.flickTier;
	const int blowThresholds[4] = {30, 35, 45, 50};
	const int stickThresholds[3] = {5, 10, 15};
	const bool startFlick = k.blows >= blowThresholds[blowTier] || k.stuckCount >= stickThresholds[stickTier];

	const char* clipName = stateClip(k.state, k.turnLeft);
	const p2king::ActorClip* clip = config.clip(53, clipName);
	const p2king::ClipKeys keys = p2king::clipKeys(clipName);
	const float prev = k.frame;
	k.frame += 1.0f;
	for (int i = 0; i < keys.keyCount; ++i) {
		const int key = keys.keys[i];
		if (!(prev < float(key) && k.frame >= float(key))) continue;
		if (k.state == p2king::Attack && key == p2king::AttackArmKey) {
			k.attackArmed = true;
			std::printf("P2_KING_ATTACK_ARM id=%u frame=40 key=3\n", k.cfg.id);
		}
		if (k.state == p2king::Attack && key == p2king::AttackBombKey) {
			k.bombArmed = true;
			std::printf("P2_KING_ATTACK_BOMB_ARM id=%u frame=92 key=6\n", k.cfg.id);
		}
		if (k.state == p2king::WarCry && key == p2king::CryCrossEmperorKey) crossEmperorRequest(k);
		if (k.state == p2king::WarCry && key == p2king::CryAstonishKey) astonishScan(k);
		if (k.state == p2king::Damage && key == p2king::DamageKillKey && !k.damageKeyDone) damageKillKey(k);
		if (k.state == p2king::Appear && key == p2king::AppearShakeOffKey)
			shakeOff(k, p2king::AppearShakeOffRange, p2king::AppearShakeOffPower, "appear");
		if (k.state == p2king::Flick && key == p2king::FlickTrampleKey) trampleScan(k);
		if (k.state == p2king::Hide && key >= 58 && !k.loggedDive) {
			k.loggedDive = true;
			std::printf("P2_KING_DIVE_EFFECTS id=%u keys=58,60,90 flags_only=1\n", k.cfg.id);
		}
		if (k.state == p2king::Dead && key == 185 && !k.loggedDead) {
			k.loggedDead = true;
			deadKeySeen = true;
			std::printf("P2_KING_DEAD_KEY id=%u frame=185 kill=1\n", k.cfg.id);
		}
	}
	if (k.state == p2king::Attack) {
		tongueTipScan(k);
		if (k.attackArmed) eatScan(k);
	}
	if (k.state == p2king::HideWait) {
		++k.framesWaited;
		const float nearest = nearestTargetDistance(k);
		if (p2king::hidewaitWake(nearest, k.framesWaited, k.info.scale, p2king::DistanceToSpawn,
		                         p2king::TimeToAppearance)) {
			std::printf("P2_KING_APPEAR_TRIGGER id=%u nearest=%.3f range=%.1f waited=%d\n", k.cfg.id, nearest,
			            p2king::DistanceToSpawn * k.info.scale, k.framesWaited);
			enter(k, p2king::Appear);
		}
	}
	if (k.state == p2king::Walk || k.state == p2king::Turn) {
		// Walk toward the nearest target; lose interest after the incubation
		// period without a target, return home and Hide.
		const float nearest = nearestTargetDistance(k);
		float goalX = k.homeX, goalZ = k.homeZ;
		bool hasTarget = nearest < KingSight;
		if (hasTarget) {
			k.framesWithoutTarget = 0;
			// Goal = nearest creature position (nearest scan approximation).
			float best = 1.0e9f;
			if (pikiMgr) {
				Iterator it(pikiMgr);
				CI_LOOP(it) {
					Piki* p = static_cast<Piki*>(*it);
					if (!p || !p->isAlive()) continue;
					const Vector3f& pos = p->getPosition();
					const float dx = pos.x - k.x, dz = pos.z - k.z;
					const float d = dx * dx + dz * dz;
					if (d < best) {
						best = d;
						goalX = pos.x;
						goalZ = pos.z;
					}
				}
			}
			if (naviMgr && naviMgr->getNavi()) {
				const Vector3f& pos = naviMgr->getNavi()->getPosition();
				const float dx = pos.x - k.x, dz = pos.z - k.z;
				if (dx * dx + dz * dz < best) {
					goalX = pos.x;
					goalZ = pos.z;
				}
			}
		} else {
			++k.framesWithoutTarget;
			// checkAttack interest in eatable bombs (approximation): with no
			// creature target, walk toward the nearest BOMB_Wait bomb in
			// range so the beyond-80 bomb trigger can connect.
			float best = KingBombAttackRange * k.info.scale;
			for (const auto& b : bombs) {
				if (b.state != 0) continue;
				const float dx = b.cfg.x - k.x, dz = b.cfg.z - k.z;
				const float d = std::sqrt(dx * dx + dz * dz);
				if (d < best) {
					best = d;
					goalX = b.cfg.x;
					goalZ = b.cfg.z;
					hasTarget = true;
				}
			}
		}
		// Whiff starvation guard (approximation): after several licks that
		// connected with nothing (whiff or terrain abort) the Emperor stops
		// re-licking unreached creatures and lines up on an eatable bomb.
		if (k.whiffStreak >= 3) {
			float best = KingBombAttackRange * k.info.scale;
			bool found = false;
			for (const auto& b : bombs) {
				if (b.state != 0) continue;
				const float dx = b.cfg.x - k.x, dz = b.cfg.z - k.z;
				const float d = std::sqrt(dx * dx + dz * dz);
				if (d < best) {
					best = d;
					goalX = b.cfg.x;
					goalZ = b.cfg.z;
					hasTarget = true;
					found = true;
				}
			}
			// No bomb to line up on: resume normal creature licks.
			if (!found) k.whiffStreak = 0;
		}
		const float gdx = goalX - k.x, gdz = goalZ - k.z;
		const float goalDist = std::sqrt(gdx * gdx + gdz * gdz);
		const float want = std::atan2(gdx, gdz) * 57.29577951308232f;
		float off = want - k.yaw;
		while (off > 180.0f) off -= 360.0f;
		while (off < -180.0f) off += 360.0f;
		const p2king::TurnDecision decision =
		    p2king::walkTurn(off, p2king::RequiredTurningAngleDeg, p2king::TurningEndAngleDeg);
		if (k.state == p2king::Walk && decision == p2king::TurnDecision::Turn) {
			k.turnLeft = off > 0.0f;
			enter(k, p2king::Turn);
		} else if (k.state == p2king::Turn) {
			const float step = off > TurnRateDeg ? TurnRateDeg : off < -TurnRateDeg ? -TurnRateDeg : off;
			k.yaw += step;
			if (decision == p2king::TurnDecision::FinishTurn || decision == p2king::TurnDecision::Walk)
				enter(k, p2king::Walk);
		} else {
			// Walk steering approximation: like the Baby move step, yaw eases
			// toward the goal while walking so the facing converges.
			const float step = off > TurnRateDeg ? TurnRateDeg : off < -TurnRateDeg ? -TurnRateDeg : off;
			k.yaw += step;
			const float rad = k.yaw * 0.0174532925199433f;
			k.x += std::sin(rad) * k.info.speed * Tick;
			k.z += std::cos(rad) * k.info.speed * Tick;
		}
		// Attack decision: close target in front, or an eatable bomb beyond the
		// invisible range (80 disc) with mCanAttackBombs on (default). The bomb
		// trigger requires rough facing; otherwise the bomb becomes the walk
		// goal so the Emperor lines up first (approximation).
		if (k.state == p2king::Walk && hasTarget && nearest < KingAttackRange * k.info.scale
		    && std::fabs(off) <= KingAttackAngleDeg && k.whiffStreak < 3) {
			std::printf("P2_KING_ATTACK_TRIGGER id=%u nearest=%.1f off=%.1f\n", k.cfg.id, nearest, off);
			enter(k, p2king::Attack);
		} else if (k.state == p2king::Walk) {
			for (const auto& b : bombs) {
				if (b.state != 0) continue;
				const float dx = b.cfg.x - k.x, dz = b.cfg.z - k.z;
				const float d = std::sqrt(dx * dx + dz * dz);
				if (!(d < KingBombAttackRange * k.info.scale && p2king::canTargetBomb(d, true))) continue;
				float boff = std::atan2(dx, dz) * 57.29577951308232f - k.yaw;
				while (boff > 180.0f) boff -= 360.0f;
				while (boff < -180.0f) boff += 360.0f;
				// Lick only when the tongue segment can actually reach the
				// bomb: rough facing plus perpendicular distance inside the
				// mouth slot radius; otherwise line up first (approximation).
				const float perp = d * std::sin(std::fabs(boff) * 0.0174532925199433f);
				if (std::fabs(boff) > KingAttackAngleDeg || perp > p2king::MouthSlotRadius * k.info.scale) {
					goalX = b.cfg.x;
					goalZ = b.cfg.z;
					break;
				}
				std::printf("P2_KING_ATTACK_TRIGGER id=%u bomb=%u dist=%.1f off=%.1f beyond_invisible_range=80 can_attack_bombs=1\n",
				            k.cfg.id, b.cfg.id, d, boff);
				enter(k, p2king::Attack);
				break;
			}
		}
		// Give up: out of interest or back home with no target -> Hide.
		if ((k.state == p2king::Walk || k.state == p2king::Turn)
		    && p2king::walkGiveUp(k.framesWithoutTarget, p2king::PeriodOfIncubation, false) && !hasTarget) {
			std::printf("P2_KING_GIVE_UP id=%u frames_without_target=%d incubation=500\n", k.cfg.id,
			            k.framesWithoutTarget);
			enter(k, p2king::Hide);
		}
		if ((k.state == p2king::Walk) && !hasTarget && goalDist < HomeRadius) {
			std::printf("P2_KING_HOME id=%u dist=%.1f home_radius=25\n", k.cfg.id, goalDist);
			enter(k, p2king::Hide);
		}
		// checkFlick: WarCry with p=0.5 under half HP, else Flick.
		if (startFlick && (k.state == p2king::Walk || k.state == p2king::Turn)) {
			const float roll = k.nextRoll();
			const int next = p2king::checkFlick(k.health, k.info.health, roll);
			std::printf("P2_KING_CHECK_FLICK id=%u health=%.1f max=%.1f roll=%.3f shout_rate=0.5 next=%d\n", k.cfg.id,
			            k.health, k.info.health, roll, next);
			enter(k, next);
		}
	}

	// One-shot / loop bounds per state, then deferred end transitions
	// (KEYEVENT_END semantics on the sampled clips).
	const int duration = clip ? clip->duration : keys.frames;
	int loopStart = 0, loopEnd = duration;
	bool loops = false;
	if (k.state == p2king::Walk) {
		loopStart = 15;
		loopEnd = 54;
		loops = true;
	} else if (k.state == p2king::HideWait) {
		loopStart = 0;
		loopEnd = 39;
		loops = true;
	} else if (k.state == p2king::Damage) {
		loopStart = p2king::DamageLoopStart;
		loopEnd = p2king::DamageLoopEnd;
		loops = true; // stun exit is handled at the loop boundary below
	}
	if (k.state == p2king::Damage && k.damageKeyDone && k.stunFrames > 0) --k.stunFrames;
	if (duration > 0 && k.frame >= float(loopEnd)) {
		if (k.state == p2king::Dead) {
			k.frame = float(duration); // stays on the last sampled pose
		} else if (loops) {
			k.frame = float(loopStart);
			if (k.state == p2king::Damage && k.stunFrames <= 0) {
				const int next = p2king::damageEnd(k.health);
				std::printf("P2_KING_STATE id=%u from=5 to=%d health=%.1f stun_done=1\n", k.cfg.id, next, k.health);
				enter(k, next);
			}
		} else {
			int next = -1;
			if (k.state == p2king::Appear)
				next = p2king::Caution;
			else if (k.state == p2king::Caution)
				next = p2king::Walk;
			else if (k.state == p2king::Hide) {
				next = p2king::HideWait;
				k.loggedDive = false;
			} else if (k.state == p2king::Attack) {
				// Whiff guard (approximation): a lick that connected with
				// nothing (whiff or terrain abort) feeds the starvation
				// streak; a connecting lick clears it.
				if (k.eatsThisLick == 0) ++k.whiffStreak; else k.whiffStreak = 0;
				// An aborted lick still resolves a non-empty mouth: anything
				// grabbed before the abort reaches the mouth (approximation).
				next = (k.attackAborted && k.mouthBombs == 0 && k.mouthPikmin == 0)
				           ? p2king::Walk
				           : p2king::attackEnd(k.mouthBombs, k.mouthPikmin);
			} else if (k.state == p2king::Eat)
				next = p2king::Damage;
			else if (k.state == p2king::Swallow)
				next = p2king::Walk;
			else if (k.state == p2king::WarCry)
				next = k.health <= 0.0f ? p2king::Dead : p2king::Walk;
			else if (k.state == p2king::Flick)
				next = k.health <= 0.0f ? p2king::Dead : p2king::Walk;
			else if (k.state == p2king::Turn)
				next = p2king::Walk;
			if (next >= 0 && next != k.state) {
				std::printf("P2_KING_STATE id=%u from=%d to=%d health=%.1f\n", k.cfg.id, k.state, next, k.health);
				if (next == p2king::Swallow) swallowMouth(k);
				enter(k, next);
			}
		}
	}
	// checkDead: Dead (WarCry with mDeathRate, 0 by default -> never).
	if (k.state != p2king::Dead && k.state != p2king::Damage && k.health <= 0.0f) {
		const p2king::DeadChoice choice = p2king::checkDead(k.nextRoll(), p2king::DeathRate);
		const int next = choice == p2king::DeadChoice::WarCry ? p2king::WarCry : p2king::Dead;
		std::printf("P2_KING_STATE id=%u from=%d to=%d health=0 death_rate=0\n", k.cfg.id, k.state, next);
		enter(k, next);
	}
}

void tickBombs() {
	// External blasts (fixture injection): detonation at the configured tick;
	// blast damage is quartered (bombCallBack, kingChappy.cpp:873-877).
	for (auto& b : bombs) {
		if (b.state != 0 || b.cfg.externalBlastTick == 0 || behaviorTick < b.cfg.externalBlastTick) continue;
		b.state = 2;
		std::printf("P2_KING_BOMB_EXTERNAL id=%u tick=%lu injection=1\n", b.cfg.id, behaviorTick);
		for (auto& k : kings) {
			if (k.state == p2king::Dead || k.state == p2king::HideWait || k.state == p2king::Hide) continue;
			const float dx = b.cfg.x - k.x, dz = b.cfg.z - k.z;
			if (dx * dx + dz * dz > ExternalBlastRange * ExternalBlastRange) continue;
			const float damage = p2king::bombDamage(1) * p2king::ExternalBlastFactor;
			k.health -= damage;
			if (k.health < 0.0f) k.health = 0.0f;
			std::printf("P2_KING_BOMB_QUARTERED id=%u bomb=%u damage=%.1f factor=0.25 health=%.1f\n", k.cfg.id, b.cfg.id,
			            damage, k.health);
		}
	}
}
} // namespace

void pc_p2_king_forget_piki(Piki* piki) {
    for (auto& actor : kings) {
        p2ActorForgetSlots(actor.stuck, actor.stuckCount, piki);
        p2ActorForgetSlots(actor.mouth, actor.mouthPikmin, piki);
    }
}

void pc_p2_king_reset() {
	config = p2king::ActorConfig{};
	shapes.clear();
	kings.clear();
	bombs.clear();
	totalBytes = 0;
	clockLast = 0;
	clockAcc = 0;
	behaviorTick = 0;
	injectWarCryId = 0;
	injectWarCryTick = 0;
	injectWarCryDone = false;
	injectKillTick = 0;
	injectKillDone = false;
	injectBombTick = 0;
	injectBombDone = false;
	injectTongueTick = 0;
	injectTongueDone = false;
	deadKeySeen = false;
}

// Fixture-only read-only observation getters. They expose the actor's own
// 30 Hz behavior clock and Dead-key completion so a host fixture can gate
// scenario sequencing deterministically instead of guessing with idle frames.
// No behavior change; absent an opt-in injection nothing here is exercised.
unsigned long pc_p2_king_behavior_tick() { return behaviorTick; }
bool pc_p2_king_dead_key_seen() { return deadKeySeen; }

void pc_p2_king_setup() {
	pc_p2_king_reset();
	if (!pc_pikipelago_room_preview()) return;
	std::ifstream in("p2-king-actor.txt");
	if (!in) return;
	try {
		config = p2king::readActorConfig(in);
	} catch (...) {
		fail();
	}
	// Opt-in, fail-closed fixture injection sidecar; absent in normal runs.
	std::ifstream inject("p2-king-inject.txt");
	if (inject) {
		std::string magic, extra;
		unsigned long long tick = 0, id = 0;
		if (!(inject >> magic >> tick >> id) || magic != "P2_KING_INJECT_1" || tick < 1 || tick > 1000000ULL
		    || id > 0xffffffffULL || (inject >> extra))
			fail();
		injectWarCryTick = (unsigned long)tick;
		injectWarCryId = (uint32_t)id;
		unsigned long long kill = 0; // optional 4th token: force death at tick
		inject >> kill;
		if (kill > 1000000ULL)
			fail();
		injectKillTick = (unsigned long)kill;
		unsigned long long bomb = 0; // optional 5th token: force bomb line-up
		inject >> bomb;
		if (bomb > 1000000ULL)
			fail();
		injectBombTick = (unsigned long)bomb;
		unsigned long long tongue = 0; // optional 6th token: force a normal tongue lick
		inject >> tongue;
		if (tongue > 1000000ULL)
			fail();
		injectTongueTick = (unsigned long)tongue;
	}
	std::map<int, std::vector<unsigned char>> resources;
	// Validate/copy the whole referenced bank before allocating Shapes; clips
	// not selected by this profile never touch the App heap.
	for (size_t ci = 0; ci < config.clips.size(); ++ci) {
		const auto& clip = config.clips[ci];
		size_t bytes = 0;
		for (size_t i = 0; i < clip.frames.size(); ++i) {
			char name[100];
			std::snprintf(name, sizeof(name), "bulblax_KingChappy_%s_%02u.mod", clip.name.c_str(), unsigned(i));
			shapes[ci].push_back(load(name, resources[clip.enemy], bytes));
		}
	}
	for (const auto& p : config.placements) {
		King k;
		k.cfg = p;
		k.info = p2king::variantInfo(p.variant);
		k.health = k.info.health;
		k.x = k.homeX = p.x;
		k.y = p.y;
		k.z = k.homeZ = p.z;
		k.yaw = p.yaw;
		k.rng = 2654435761u * (p.id + 1u);
		enter(k, p2king::entryState());
		std::printf("P2_KING_READY id=%u enemy=53 variant=%s xyz=%.6f,%.6f,%.6f yaw=%.3f health=%.1f scale=%.2f "
		            "speed=%.1f floor_offset=%.0f entry_state=%d gauge_hidden=1\n",
		            p.id, p.variant == p2king::Variant::F03 ? "f_03" : p.variant == p2king::Variant::ForceBig ? "force_big" : "default",
		            p.x, p.y, p.z, p.yaw, k.health, k.info.scale, k.info.speed, k.info.floorOffset, k.state);
		kings.push_back(k);
	}
	for (const auto& bp : config.bombs) {
		Bomb b;
		b.cfg = bp;
		bombs.push_back(b);
		std::printf("P2_KING_BOMB_READY id=%u enemy=36 state=BOMB_Wait xyz=%.6f,%.6f,%.6f external_blast_tick=%u injection=1\n",
		            bp.id, bp.x, bp.y, bp.z, bp.externalBlastTick);
	}
	clockLast = SDL_GetTicks();
}

void pc_p2_king_update() {
	if (kings.empty() && bombs.empty()) return;
	const unsigned now = SDL_GetTicks();
	clockAcc += float(now - clockLast) * 0.001f;
	clockLast = now;
	int steps = 0;
	while (clockAcc >= Tick && steps < 4) { // bounded: never catch up more than 4 ticks
		clockAcc -= Tick;
		++steps;
		++behaviorTick;
		if (injectWarCryTick && !injectWarCryDone && behaviorTick >= injectWarCryTick) {
			for (auto& k : kings) {
				if (injectWarCryId && k.cfg.id != injectWarCryId) continue;
				// Opt-in fixture injection: force WarCry even from a buried
				// state so the scenario does not depend on the squad surviving
				// to provide an appear target. Dead is never resurrected.
				if (k.state == p2king::Dead) continue;
				enter(k, p2king::WarCry);
				injectWarCryDone = true;
				std::printf("P2_KING_INJECT id=%u tick=%lu force=WarCry fixture=1\n", k.cfg.id, behaviorTick);
				break;
			}
		}
		if (injectKillTick && !injectKillDone && behaviorTick >= injectKillTick) {
			for (auto& k : kings) {
				if (injectWarCryId && k.cfg.id != injectWarCryId) continue;
				k.health = 0.0f;
				injectKillDone = true;
				std::printf("P2_KING_INJECT_KILL id=%u tick=%lu health=0 fixture=1\n", k.cfg.id, behaviorTick);
				break;
			}
		}
		if (injectTongueTick && !injectTongueDone && behaviorTick >= injectTongueTick) {
			for (auto& k : kings) {
				if (injectWarCryId && k.cfg.id != injectWarCryId) continue;
				if (k.state == p2king::Dead) continue;
				// Opt-in fixture injection: place the Emperor behind the nearest
				// live Pikmin facing it and enter a normal Attack before the arm
				// key, so the key-40 tongue arm, Pikmin ingestion and the
				// Attack->Swallow transition are observed deterministically even
				// when the live squad would otherwise trigger a flick.
				Piki* best = nullptr;
				float bestSq = 0.0f;
				if (pikiMgr) {
					Iterator it(pikiMgr);
					CI_LOOP(it) {
						Piki* p = static_cast<Piki*>(*it);
						if (!p || !p->isAlive()) continue;
						const Vector3f& pos = p->getPosition();
						const float dx = pos.x - k.x, dz = pos.z - k.z;
						const float d = dx * dx + dz * dz;
						if (!best || d < bestSq) {
							best = p;
							bestSq = d;
						}
					}
				}
				if (!best) continue; // no live Pikmin yet: retry next tick
				const Vector3f& pos = best->getPosition();
				k.x = pos.x;
				k.z = pos.z - 50.0f * k.info.scale;
				k.yaw = 0.0f;
				enter(k, p2king::Attack);
				k.frame = float(p2king::AttackArmKey) - 1.0f;
				k.attackArmed = false;
				k.bombArmed = false;
				injectTongueDone = true;
				std::printf("P2_KING_INJECT_TONGUE id=%u tick=%lu state=Attack fixture=1\n", k.cfg.id, behaviorTick);
				break;
			}
		}
		if (injectBombTick && !injectBombDone && behaviorTick >= injectBombTick) {
			for (auto& k : kings) {
				if (injectWarCryId && k.cfg.id != injectWarCryId) continue;
				// Opt-in fixture injection: force the bomb line-up even from a
				// buried state so the deterministic ingestion lane does not
				// depend on the squad providing an appear target. Dead skipped.
				if (k.state == p2king::Dead) continue;				Bomb* best = nullptr;
				float bestDist = 0.0f;
				for (auto& b : bombs) {
					if (b.state != 0) continue;
					const float dx = b.cfg.x - k.x, dz = b.cfg.z - k.z;
					const float d = std::sqrt(dx * dx + dz * dz);
					if (!best || d < bestDist) { best = &b; bestDist = d; }
				}
				if (!best) continue;
				// Place the Emperor 60*scale behind the bomb facing it so the bomb
				// lies on the tongue segment, then arm the bomb key deterministically.
				k.x = best->cfg.x;
				k.z = best->cfg.z - 60.0f * k.info.scale;
				k.yaw = 0.0f;
				enter(k, p2king::Attack);
				k.frame = float(p2king::AttackBombKey) - 1.0f;
				k.attackArmed = true;
				k.bombArmed = true;
				injectBombDone = true;
				std::printf("P2_KING_INJECT_BOMB id=%u tick=%lu bomb=%u state=Attack fixture=1\n", k.cfg.id, behaviorTick, best->cfg.id);
				break;
			}
		}
		for (auto& k : kings) tickKing(k);
		tickBombs();
	}
	if (steps == 4) clockAcc = 0; // drop backlog; 30 Hz stays bounded
}

void pc_p2_king_draw(Graphics& gfx) {
	if (kings.empty() || !gfx.mCamera) return;
	gfx.setPerspective(gfx.mCamera->mPerspectiveMatrix.mMtx, gfx.mCamera->mFov, gfx.mCamera->mAspectRatio,
	                   gfx.mCamera->mNear, gfx.mCamera->mFar, 1.f);
	gfx.useMaterial(nullptr);
	gfx.setDepth(true);
	for (auto& k : kings) {
		if (k.state == p2king::HideWait) continue; // buried: gauge and model hidden
		const char* clipName = stateClip(k.state, k.turnLeft);
		const p2king::ActorClip* clip = config.clip(53, clipName);
		if (!clip) continue;
		size_t ci = size_t(clip - &config.clips[0]);
		size_t pose = clip->index(k.frame);
		Shape* shape = shapes.at(ci)[pose];
		Matrix4f world, view;
		const float s = k.info.scale;
		world.makeSRT(Vector3f(s, s, s), Vector3f(0, k.yaw * 0.0174532925199433f, 0), Vector3f(k.x, k.y, k.z));
		gfx.mCamera->mLookAtMtx.multiplyTo(world, view);
		shape->updateAnim(gfx, view, nullptr, nullptr);
		shape->drawshape(gfx, *gfx.mCamera, nullptr);
	}
}
