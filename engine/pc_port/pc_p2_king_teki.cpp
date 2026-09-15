#include "pc_p2_king_teki.h"
#include "pc_p2_king_teki_policy.h"
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
	float health = p2king::HealthDefault; // Emperor default; host health rewritten to this
	float scale = 1.0f;
	Vector3f home;                        // spawn hold; the Emperor is an ambush, not a roamer
	// source stuck/flick accumulation (general parms: blows 30/35/45/50, sticking 5/10/15)
	int stuck = 0;
	int blows = 0;
	int flickTier = 0;
	int attached = 0;
	bool deadLogged = false;
	std::vector<Shape*> walkShapes;       // move1 sampled poses
	std::vector<Shape*> deadShapes;       // dead sampled poses
};
std::map<BTeki*, Binding> s;
unsigned lastTicks = 0;
float clockAcc = 0;
unsigned long behaviorTick = 0;
bool gDeadKeySeen = false;
constexpr float Tick = 1.0f / 30.0f;

void fail() { std::fputs("P2_KING_TEKI invalid config/model\n", stderr); std::abort(); }

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
		std::snprintf(name, sizeof(name), "bulblax_KingChappy_%s_%02u.mod", clip, unsigned(i));
		std::ifstream probe("assets/dataDir/courses/pikmin2room/" + std::string(name), std::ios::binary | std::ios::ate);
		if (!probe) break;
		out.push_back(loadOne(name, reference, clipBytes));
	}
}

// Source-faithful latch gate (same predicate the slice-3 King receiver uses): a
// Pikmin only sticks when it is actually attached and running the Attack action
// against this host, not merely passing near it.
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
	const int blowTh[4] = {30, 35, 45, 50};
	const int stickTh[3] = {5, 10, 15};
	const bool startFlick = b.blows >= blowTh[blowTier] || b.stuck >= stickTh[stickTier];
	std::printf("P2_KING_TEKI_ATTACHED generator=%u attached=%d blows=%d stuck=%d tier=%d flick=%d\n",
	            b.generator, attached, b.blows, b.stuck, b.flickTier, int(startFlick));
	if (startFlick) {
		std::printf("P2_KING_TEKI_FLICK generator=%u shaken=%d blown_threshold=%d stuck_threshold=%d\n",
		            b.generator, b.blows, blowTh[blowTier], stickTh[stickTier]);
		Iterator f(pikiMgr);
		CI_LOOP(f) {
			Piki* p = static_cast<Piki*>(*f);
			if (!isAttackingHost(t, p)) continue;
			const Vector3f& pos = p->getPosition();
			InteractFlick flick(nullptr, p2king::AppearShakeOffPower, 1.0f,
			                    std::atan2(pos.x - t->mSRT.t.x, pos.z - t->mSRT.t.z));
			p->stimulate(flick);
		}
		Iterator pr(pikiMgr);
		CI_LOOP(pr) {
			Piki* p = static_cast<Piki*>(*pr);
			if (!isAttackingHost(t, p)) continue;
			InteractPress press(nullptr, p2king::AttackDamage);
			p->stimulate(press);
		}
		b.blows = 0;
		if (b.flickTier < 3) ++b.flickTier;
	}
}
} // namespace

void pc_p2_king_teki_reset() {
	s.clear();
	lastTicks = 0;
	clockAcc = 0;
	behaviorTick = 0;
	gDeadKeySeen = false;
}
void pc_p2_king_teki_forget(BTeki* t) { if (t) s.erase(t); }
bool pc_p2_king_teki_is_bound(const BTeki* t) { return t && s.count(const_cast<BTeki*>(t)); }

void pc_p2_king_teki_setup() {
	pc_p2_king_teki_reset();
	if (!pc_pikipelago_room_preview()) return;
	std::ifstream in("p2-king-teki.txt");
	if (!in) return;
	p2kingteki::Binding cfg{};
	if (!p2kingteki::read(in, cfg) || !tekiMgr) fail();
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
		b.health = p2king::HealthDefault;
		b.scale = 1.0f;
		t->mHealth = b.health;
		loadClip("move1", b.walkShapes);
		loadClip("dead", b.deadShapes);
		if (b.walkShapes.empty() || b.deadShapes.empty()) fail();
		s.emplace(t, b);
		lastTicks = SDL_GetTicks();
		std::printf("P2_KING_TEKI_READY generator=%u type=%d binding=creature_host health=%.1f scale=%.2f xyz=%.3f,%.3f,%.3f\n",
		            cfg.generator, cfg.type, b.health, b.scale, b.home.x, b.home.y, b.home.z);
	}
}

void pc_p2_king_teki_tick(BTeki* t) {
	auto i = s.find(t);
	if (i == s.end()) return;
	Binding& b = i->second;
	if (t->mHealth <= 0.0f) {
		if (!b.deadLogged) {
			b.deadLogged = true;
			gDeadKeySeen = true;
			std::printf("P2_KING_TEKI_CORPSE generator=%u health=0.0 corpse_pellet=1 cleanup_engine=1\n", b.generator);
		}
		return;
	}
	const unsigned now = SDL_GetTicks();
	clockAcc += float(now - lastTicks) * 0.001f;
	lastTicks = now;
	int steps = 0;
	while (clockAcc >= Tick && steps < 4) {
		clockAcc -= Tick;
		++steps;
		++behaviorTick;
		scanFlick(b, t);
	}
	if (steps == 4) clockAcc = 0;
}

bool pc_p2_king_teki_draw(BTeki* t, Graphics& gfx, const Matrix4f& matrix, bool corpse) {
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

bool pc_p2_king_teki_dead_key_seen() { return gDeadKeySeen; }
unsigned long pc_p2_king_teki_behavior_tick() { return behaviorTick; }
int pc_p2_king_teki_attached_count(const BTeki* t) { auto i = s.find(const_cast<BTeki*>(t)); return i == s.end() ? -1 : i->second.attached; }
