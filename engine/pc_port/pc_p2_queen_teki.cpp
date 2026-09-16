#include "pc_p2_queen_teki.h"
#include "pc_p2_queen_teki_policy.h"
#include "pc_p2_queen_policy.h"
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
#include "PikiAI.h"
#include "Interactions.h"
#include "teki.h"
#include "Generator.h"
#include <SDL.h>
#include <map>
#include <vector>
#include <string>
#include <fstream>
#include <cmath>
#include <cstdio>
#include <cstdlib>
namespace {
struct Binding {
	unsigned generator = 0;
	int type = 0;
	float health = p2queen::HealthDefault; // Empress default; host health rewritten to this
	float scale = 1.0f;
	Vector3f home;                        // spawn hold; the Empress is an ambush, not a roamer
	// source stuck/shake-off accumulation (general parms: blows 30/35/45/50, sticking 5/10/15)
	int stuck = 0;
	int blows = 0;
	int flickTier = 0;
	int attached = 0;
	float prevHealth = 0;                  // last observed host health; drops feed the blow counter
	bool deadLogged = false;
	std::vector<Shape*> walkShapes;       // wait1 sampled poses
	std::vector<Shape*> deadShapes;       // dead sampled poses
};
std::map<BTeki*, Binding> s;
unsigned lastTicks = 0;
float clockAcc = 0;
unsigned long behaviorTick = 0;
bool gDeadKeySeen = false;
constexpr float Tick = 1.0f / 30.0f;

void fail() { std::fputs("P2_QUEEN_TEKI invalid config/model\n", stderr); std::abort(); }

Shape* loadOne(const std::string& name, std::vector<unsigned char>& reference, size_t& clipBytes) {
	std::ifstream in("assets/dataDir/courses/pikmin2room/" + name, std::ios::binary | std::ios::ate);
	if (!in) fail();
	auto size = in.tellg();
	if (size <= 0 || size > 1024 * 1024 || clipBytes + size_t(size) > 1024 * 1024)
		fail();
	clipBytes += size_t(size);
	in.seekg(0);
	std::vector<unsigned char> data(size_t(size), 0), resources;
	if (!in.read(reinterpret_cast<char*>(data.data()), size) || !p2animation::resources(data, resources))
		fail();
	if (!reference.empty() && reference != resources) fail();
	reference = resources;
	Shape* shape = gameflow.loadShape(("courses/pikmin2room/" + name).c_str(), true);
	if (!shape) fail();
	for (int i = 0; i < shape->mTexAttrCount; ++i)
		if (shape->mTexAttrList[i].mTexture) shape->mTexAttrList[i].mTexture->attach();
	return shape;
}

void loadClip(const char* clip, std::vector<Shape*>& out) {
	size_t clipBytes = 0;
	std::vector<unsigned char> reference;
	for (int i = 0; i < 12; ++i) {
		char name[100];
		std::snprintf(name, sizeof(name), "bulblax_Queen_%s_%02u.mod", clip, unsigned(i));
		std::ifstream probe("assets/dataDir/courses/pikmin2room/" + std::string(name), std::ios::binary | std::ios::ate);
		if (!probe) break;
		out.push_back(loadOne(name, reference, clipBytes));
	}
}

// Source-faithful latch gate: a Pikmin only sticks when it is actually attached
// and running the Attack action against this host, not merely passing near it.
bool isAttackingHost(BTeki* t, Piki* p) {
	if (!t || !p || !p->isAlive()) return false;
	if (p->mMode != PikiMode::AttackMode || !p->mActiveAction) return false;
	if (p->mActiveAction->mCurrActionIdx != PikiAction::Attack) return false;
	return p->getStickObject() == t;
}

void scanFlick(Binding& b, BTeki* t) {
	if (!pikiMgr) return;
	int attached = 0;
	Iterator it(pikiMgr);
	CI_LOOP(it) {
		Piki* p = static_cast<Piki*>(*it);
		if (isAttackingHost(t, p)) ++attached;
	}
	b.attached = attached;
	b.stuck = attached;
	const int blowTier = b.flickTier > 3 ? 3 : b.flickTier;
	const int stickTier = b.flickTier > 2 ? 2 : b.flickTier;
	const int blowTh[4] = {p2queen::ShakeBlows[0], p2queen::ShakeBlows[1], p2queen::ShakeBlows[2],
	                       p2queen::ShakeBlows[3]};
	const int stickTh[3] = {p2queen::ShakeSticking[0], p2queen::ShakeSticking[1],
	                        p2queen::ShakeSticking[2]};
	const bool startFlick = b.blows >= blowTh[blowTier] || b.stuck >= stickTh[stickTier];
	std::printf("P2_QUEEN_TEKI_ATTACHED generator=%u attached=%d blows=%d stuck=%d tier=%d flick=%d\n",
	            b.generator, attached, b.blows, b.stuck, b.flickTier, int(startFlick));
	if (startFlick) {
		std::printf("P2_QUEEN_TEKI_FLICK generator=%u shaken=%d blown_threshold=%d stuck_threshold=%d\n",
		            b.generator, attached, blowTh[blowTier], stickTh[stickTier]);
		Iterator f(pikiMgr);
		CI_LOOP(f) {
			Piki* p = static_cast<Piki*>(*f);
			if (!isAttackingHost(t, p)) continue;
			const Vector3f& pos = p->getPosition();
			InteractFlick flick(nullptr, p2queen::ShakeKnockback, p2queen::ShakeDamage,
			                    std::atan2(pos.x - t->mSRT.t.x, pos.z - t->mSRT.t.z));
			p->stimulate(flick);
		}
		Iterator pr(pikiMgr);
		CI_LOOP(pr) {
			Piki* p = static_cast<Piki*>(*pr);
			if (!isAttackingHost(t, p)) continue;
			InteractPress press(nullptr, p2queen::PressDamage);
			p->stimulate(press);
		}
		b.blows = 0;
		if (b.flickTier < 3) ++b.flickTier;
	}
}
} // namespace

void pc_p2_queen_teki_reset() {
	s.clear();
	lastTicks = 0;
	clockAcc = 0;
	behaviorTick = 0;
	gDeadKeySeen = false;
}
void pc_p2_queen_teki_forget(BTeki* t) { if (t) s.erase(t); }
bool pc_p2_queen_teki_is_bound(const BTeki* t) { return t && s.count(const_cast<BTeki*>(t)); }

void pc_p2_queen_teki_setup() {
	pc_p2_queen_teki_reset();
	if (!pc_pikipelago_room_preview()) return;
	std::ifstream in("p2-queen-teki.txt");
	if (!in) return;
	p2queenteki::Binding cfg{};
	if (!p2queenteki::read(in, cfg) || !tekiMgr) fail();
	Iterator it(tekiMgr);
	CI_LOOP(it) {
		auto* t = static_cast<Teki*>(*it);
		if (!t || !t->mGenerator || t->mGenerator->_70 != cfg.generator) continue;
		if (t->mTekiType != cfg.type) fail();
		if (!s.empty()) fail();
		Binding b;
		b.generator = cfg.generator;
		b.type = cfg.type;
		b.home = t->mSRT.t;
		b.health = p2queen::HealthDefault;
		b.scale = 1.0f;
		b.prevHealth = b.health;
		t->mHealth = b.health;
		// The Empress drops no pellets in source; the copied iket personality may
		// carry a non-zero appear chance, so zero it on the bound host.
		t->setPersonalityF(TekiPersonality::FLT_PelletAppearChance, 0.0f);
		loadClip("wait1", b.walkShapes);
		loadClip("dead", b.deadShapes);
		if (b.walkShapes.empty() || b.deadShapes.empty()) fail();
		s.emplace(t, b);
		lastTicks = SDL_GetTicks();
		std::printf("P2_QUEEN_TEKI_READY generator=%u type=%d binding=creature_host health=%.1f scale=%.2f xyz=%.3f,%.3f,%.3f\n",
		            cfg.generator, cfg.type, b.health, b.scale, b.home.x, b.home.y, b.home.z);
		std::printf("P2_QUEEN_TEKI_HOST_AI_SUPPRESSED generator=%u method=param_seam sight_attack_indices=9 "
		            "eat_state=CHAPPYSTATE_Unk8 latch_preserved=1\n", cfg.generator);
	}
}

void pc_p2_queen_teki_tick(BTeki* t) {
	auto i = s.find(t);
	if (i == s.end()) return;
	Binding& b = i->second;
	if (t->mHealth <= 0.0f) {
		if (!b.deadLogged) {
			b.deadLogged = true;
			gDeadKeySeen = true;
			std::printf("P2_QUEEN_TEKI_CORPSE generator=%u health=0.0 carcass_pellet=%d\n", b.generator,
			            int(t->mPellet != nullptr));
		}
		return; // stop re-pinning once dead so the engine's carcass pellet moves freely
	}
	// The Empress is an ambush predator: hold the host at its spawn so it does not
	// wander off and drag the fight/carcass away from the squad.
	t->mSRT.t = b.home;
	const unsigned now = SDL_GetTicks();
	clockAcc += float(now - lastTicks) * 0.001f;
	lastTicks = now;
	int steps = 0;
	while (clockAcc >= Tick && steps < 4) {
		clockAcc -= Tick;
		++steps;
		++behaviorTick;
		// Source-faithful blow counter: each unit of health lost to an attached
		// Pikmin since the last behavior tick is one blow, feeding the tiered
		// 30/35/45/50 threshold.
		if (t->mHealth < b.prevHealth) b.blows += int(b.prevHealth - t->mHealth);
		b.prevHealth = t->mHealth;
		scanFlick(b, t);
	}
	if (steps == 4) clockAcc = 0;
}

bool pc_p2_queen_teki_draw(BTeki* t, Graphics& gfx, const Matrix4f& matrix, bool corpse) {
	auto i = s.find(t);
	if (i == s.end() || !gfx.mCamera) return false;
	Binding& b = i->second;
	const bool dead = corpse || t->mHealth <= 0.0f;
	Shape* shape = dead ? b.deadShapes.back() : b.walkShapes.front();
	if (!shape) return false;
	Matrix4f world, view;
	world.makeSRT(Vector3f(b.scale, b.scale, b.scale), Vector3f(0, 0, 0),
	              Vector3f(t->mSRT.t.x, t->mSRT.t.y, t->mSRT.t.z));
	gfx.mCamera->mLookAtMtx.multiplyTo(world, view);
	gfx.setPerspective(gfx.mCamera->mPerspectiveMatrix.mMtx, gfx.mCamera->mFov, gfx.mCamera->mAspectRatio,
	                   gfx.mCamera->mNear, gfx.mCamera->mFar, 1.f);
	gfx.useMaterial(nullptr);
	gfx.setDepth(true);
	shape->updateAnim(gfx, view, nullptr, nullptr);
	shape->drawshape(gfx, *gfx.mCamera, nullptr);
	(void)matrix;
	return true;
}

bool pc_p2_queen_teki_dead_key_seen() { return gDeadKeySeen; }
unsigned long pc_p2_queen_teki_behavior_tick() { return behaviorTick; }
int pc_p2_queen_teki_attached_count(const BTeki* t) { auto i = s.find(const_cast<BTeki*>(t)); return i == s.end() ? -1 : i->second.attached; }

float pc_p2_queen_teki_param_f(const BTeki* actor, int idx, float fallback) {
    auto i = s.find(const_cast<BTeki*>(actor));
    if (i == s.end()) return fallback;
    // The Empress's health is the host's max life, and its regen is zero, so the
    // per-frame life-recovery clamp (tekibteki.cpp) keeps the host at 5000 until
    // real Pikmin damage is dealt through the engine.
    if (idx == TPF_Life) return p2queen::HealthDefault;
    if (idx == TPF_LifeRecoverRate) return 0.0f;
    // Host-AI suppression (the armor/kogane pattern): zero the bound host's own
    // sight/attack parms so the borrowed Chappy strategy can never target or eat
    // the squad. Pikmin still latch and damage the host via TPF_CollisionRadius
    // and the engine InteractAttack, so latchability is unaffected.
    switch (idx) {
    case TPF_VisibleRange:
    case TPF_VisibleAngle:
    case TPF_AttackableRange:
    case TPF_AttackableAngle:
    case TPF_AttackRange:
    case TPF_AttackHitRange:
    case TPF_AttackPower:
    case TPF_DangerTerritoryRange:
    case TPF_SafetyTerritoryRange:
        return 0.0f;
    default:
        return fallback;
    }
}

bool pc_p2_queen_teki_receipt(PelletView* view, unsigned& generator) {
    if (!view) return false;
    auto i = s.find(static_cast<BTeki*>(view));
    if (i == s.end()) return false;
    generator = i->second.generator;
    return true;
}

const char* pc_p2_queen_teki_name(PelletView* view) {
    if (!view) return nullptr;
    auto i = s.find(static_cast<BTeki*>(view));
    return i == s.end() ? nullptr : "Empress Bulblax";
}
