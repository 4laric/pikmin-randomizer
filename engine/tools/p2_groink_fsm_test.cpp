// Engine-free regressions for the Gatling Groink source FSM port
// (pc_port/pc_p2_groink_fsm.*). Each block names the source lines it pins.
#include "pc_p2_groink_fsm.h"
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <sstream>
#include <vector>

using namespace p2groinkfsm;

namespace {
int failures = 0;
void check(bool ok, const char* what) {
    if (!ok) { std::fprintf(stderr, "FAIL %s\n", what); ++failures; }
}
bool near(float a, float b, float eps = 1e-4f) { return std::fabs(a - b) <= eps; }

// Straight corridor of waypoints along +Z, radius 20, bidirectional links.
struct LineRoute : Route {
    std::vector<WayPointInfo> points;
    explicit LineRoute(int n, float spacing) {
        for (int i = 0; i < n; ++i) {
            WayPointInfo w;
            w.index = i;
            w.pos = {0.0f, 0.0f, float(i) * spacing};
            w.radius = 20.0f;
            if (i > 0) w.links[w.linkCount++] = i - 1;
            if (i + 1 < n) w.links[w.linkCount++] = i + 1;
            points.push_back(w);
        }
    }
    int nearest(const P2GroinkVec3& p) const override {
        int best = -1; float bd = 1e30f;
        for (const auto& w : points) {
            const float dx = w.pos.x - p.x, dz = w.pos.z - p.z, d = dx * dx + dz * dz;
            if (d < bd) { bd = d; best = w.index; }
        }
        return best;
    }
    bool get(int i, WayPointInfo& out) const override {
        if (i < 0 || i >= int(points.size())) return false;
        out = points[size_t(i)];
        return true;
    }
};

// Flat floor at y=0: integrate, report a floor hit when the sphere touches it.
bool floorTrace(void*, const P2GroinkVec3& c, const P2GroinkVec3& v, float dt, float r, P2GroinkTraceResult& out) {
    out = {};
    out.position = {c.x + v.x * dt, c.y + v.y * dt, c.z + v.z * dt};
    out.velocity = v;
    if (out.position.y - r <= 0.0f) {
        out.position.y = r;
        out.floor = true;
        out.hasGroundY = true;
        out.groundY = 0.0f;
    }
    return true;
}

struct World {
    std::vector<Candidate> c;
    P2GroinkVec3 pos{};
    float health = 100.0f;
    int hits = 0, stuck = 0;
    const Route* route = nullptr;
    TickInput input() const {
        TickInput in;
        in.position = pos;
        in.health = health;
        in.damageHits = hits;
        in.stuckPikmin = stuck;
        in.candidates = c.data();
        in.count = c.size();
        in.route = route;
        in.trace = floorTrace;
        return in;
    }
};
Candidate navi(std::uint64_t id, P2GroinkVec3 p) { Candidate c; c.id = id; c.pos = p; c.navi = true; return c; }
Candidate piki(std::uint64_t id, P2GroinkVec3 p) { Candidate c; c.id = id; c.pos = p; c.pikmin = true; return c; }

// Advance the FSM, integrating its velocity like the host does.
TickOutput step(Fsm& f, World& w) {
    TickOutput o = f.tick(w.input());
    w.pos.x += o.velocity.x * kSourceDelta;
    w.pos.z += o.velocity.z * kSourceDelta;
    w.hits = 0;
    return o;
}
bool entered(const TickOutput& o, State s) {
    for (State e : o.entered) if (e == s) return true;
    return false;
}
} // namespace

int main() {
    // ---- Animator: SysShape::Animator loop/finish/END and the single latch.
    {
        Clip loop;
        loop.frames = 20;
        loop.events = {{2, KeyLoopStart}, {5, Key2}, {10, KeyLoopEnd}};
        Animator a;
        a.start(&loop, 0);
        int ends = 0, key2 = 0, loops = 0;
        for (int i = 0; i < 60; ++i) { a.animate(kSourceDelta); key2 += a.is(Key2); loops += a.is(KeyLoopStart); ends += a.is(KeyEnd); }
        check(ends == 0 && key2 >= 5 && loops >= 5, "unfinished loop never reaches END");
        check(a.frame() < 11.0f, "loop jumps back to LOOP_START");
        a.finish();
        for (int i = 0; i < 30; ++i) { a.animate(kSourceDelta); ends += a.is(KeyEnd); }
        check(ends == 1, "finishMotion plays through to exactly one END");
        Clip once;
        once.frames = 10;
        once.events = {{3, Key4}};
        a.start(&once, 1);
        a.animate(kSourceDelta); a.animate(kSourceDelta); a.animate(kSourceDelta);
        check(!a.is(Key4), "event at frame 3 not yet crossed at timer 3 (strict <)");
        a.animate(kSourceDelta);
        check(a.is(Key4), "event latched on the update that crosses it");
        a.animate(kSourceDelta);
        check(!a.playing(), "latch cleared on the next animate");
        a.stop();
        const float frozen = a.frame();
        a.animate(kSourceDelta);
        check(a.frame() == frozen, "stopMotion freezes the clock");
        a.resume();
        a.animate(kSourceDelta);
        check(near(a.frame(), frozen + 1.0f), "startMotion resumes at 30 fps");
    }

    // ---- Parameter parser: retail text layout, general vs proper fp11/fp12.
    {
        std::istringstream text(
            "# CreatureProps\n{\n\t{s003} 4 0.200000 \t# accel\n{_eof}\n}\n"
            "# EnemyParmsBase\n{\n\t{fp00} 4 750.000000 \t# life\n\t{fp11} 4 70.000000 \t# private\n"
            "\t{fp12} 4 400.000000 \t# sight\n\t{fp14} 4 350.000000 \t# search\n"
            "\t{fp24} 4 12.500000 \t# dmg\n\t{ip01} 4 4 \t# blowA\n{_eof}\n}\n"
            "# EnemyParmsBase\n{\n\t{fp11} 4 25.000000 \t# gauge\n\t{fp12} 4 8.000000 \t# respawn\n{_eof}\n}\n");
        Params p;
        std::string err;
        check(parseEnemyParm(text, p, err) && p.retail, "retail parm text parses");
        check(p.health == 750.0f && p.sightRadius == 400.0f && p.privateRadius == 70.0f, "general block values");
        check(p.healthGaugeTimer == 25.0f && p.respawnRate == 8.0f, "proper fp11/fp12 not confused with general");
        check(p.searchDistance == 350.0f && p.attackDamage == 12.5f && p.shakeOffBlowA == 4 && p.accel == 0.2f, "other rows");
        check(p.moveSpeed == 80.0f, "missing rows keep the source default");
        std::istringstream bad("{\n\t{fp06} 4 80.0\n{_eof}\n}\n");
        Params q;
        check(!parseEnemyParm(bad, q, err) && !q.retail, "no general block fails closed");
    }

    // ---- Bank parser.
    {
        std::istringstream text("P2_GROINK_BANK_1 1\nclip 3 attack1 44 4 11 2 22 3 25 4 32 5 3 0 21 43\n"
                                "muzzle 0 0 1 0 1 0 -1 0 0 0 40 30\nEND\n");
        Bank b = defaultBank();
        std::string err;
        check(parseBank(text, b, err), "bank parses");
        check(b.clip[AnimAttack].staged && b.clip[AnimAttack].poses.size() == 3 && b.muzzleStaged, "bank clip + muzzle");
        check(!b.clip[AnimWalk].staged && b.clip[AnimWalk].frames == 36 && b.clip[AnimWalk].events.size() == 3, "unlisted clip keeps fallback");
        std::istringstream bad("P2_GROINK_BANK_1 1\nclip 3 attack1 44 1 50 2 0\nEND\n");
        Bank c = defaultBank();
        check(!parseBank(bad, c, err), "event beyond clip fails closed");
    }

    const Bank bank = defaultBank();
    const Params params;

    // ---- onInit starts in TurnPath; turning toward the waypoint uses the
    // source turn rate (angleDist*fp08 clamped to fp28 degrees per update).
    {
        LineRoute route(3, 200.0f);
        World w;
        w.route = &route;
        w.pos = {0.0f, 0.0f, 0.0f};
        Fsm f;
        f.init(params, bank, false, w.pos, kPi, 7u, &route); // facing -Z
        check(f.state() == State::TurnPath, "onInit -> TurnPath");
        check(f.nearestWayPoint() == 0, "setNearestWayPoint at init");
        // Standing on waypoint 0 (radius 20): updateTargetDistance links to 1.
        TickOutput o = step(f, w);
        check(f.nearestWayPoint() == 1 && near(f.walkTarget().z, 200.0f), "setLinkWayPoint picks the only open link");
        const float before = kPi;
        const float turned = std::fabs(angDist(o.faceDir, before));
        check(near(turned, 10.0f * kPi / 180.0f, 1e-3f), "turn clamps to fp28 = 10 deg per update");
        bool walkPath = false;
        for (int i = 0; i < 200 && !walkPath; ++i) walkPath = entered(step(f, w), State::WalkPath);
        check(walkPath, "TurnPath -> WalkPath once within 45 deg (after the turn clip END)");
        float z0 = w.pos.z;
        for (int i = 0; i < 60; ++i) step(f, w);
        check(w.pos.z > z0 + 30.0f, "WalkPath walks toward the waypoint at fp06");
    }

    // ---- Target search: getNearestPikminOrNavi (a Pikmin strictly nearer
    // than the nearest captain wins; view cone fp13 = 90 deg until alerted).
    // Captains are placed high (|dy| >= 200) so the attack lane never fires.
    {
        auto firstSearch = [&](std::vector<Candidate> cs) {
            World w;
            Fsm f;
            f.init(params, bank, false, w.pos, 0.0f, 3u, nullptr);
            w.c = cs;
            for (int i = 0; i < 5; ++i) step(f, w);
            return f.lastSearched();
        };
        Candidate farPiki = piki(2, {40, 0, 120});
        check(firstSearch({navi(1, {0, 250, 150}), farPiki}) == 2, "nearer Pikmin beats the captain");
        farPiki.pos = {40, 0, 170};
        check(firstSearch({navi(1, {0, 250, 150}), farPiki}) == 1, "farther Pikmin loses to the captain");
        check(firstSearch({piki(3, {0, 0, -60})}) == 0, "behind the 90 deg cone before any alert");
        Candidate hidden = piki(4, {0, 0, 60});
        hidden.searchable = false;
        check(firstSearch({hidden}) == 0, "unsearchable Pikmin ignored");
        check(firstSearch({piki(5, {0, 0, 260})}) == 0, "beyond fp12 sight radius");
        World w;
        Fsm f;
        f.init(params, bank, false, w.pos, 0.0f, 3u, nullptr);
        w.c = {navi(1, {0, 250, 150})};
        for (int i = 0; i < 3; ++i) step(f, w);
        check(f.cautionTimer() < params.alertDuration, "getSearchedTarget resets the caution timer");
        w.c.push_back(piki(3, {0, 0, -60}));
        w.stuck = 1; // alert: view angle widens to 180
        for (int i = 0; i < 3; ++i) step(f, w);
        check(f.lastSearched() == 3, "alerted (stuck Pikmin) Groink sees behind itself");
    }

    // ---- The source attack: retail attack1 events, gun aim lock, 3-shell
    // volleys (MiniHoudaiState.cpp:282-400, MiniHoudaiShotGun.cpp:407-451).
    {
        World w;
        Fsm f;
        f.init(params, bank, false, w.pos, 0.0f, 11u, nullptr);
        // Pikmin straight ahead inside the fp14 lane (|lateral| < 25). The
        // source ballistics land a shell short of a target (0.9 x (d - 50)),
        // so a row of Pikmin covers the impact zone; id 9 is the lane target.
        w.c = {piki(9, {0.0f, 0.0f, 190.0f})};
        for (int k = 0; k < 8; ++k) w.c.push_back(piki(100 + k, {0.0f, 0.0f, 60.0f + 15.0f * k}));
        int attacks = 0, volleys = 0, shells = 0, hits = 0, maxShells = 0, emitFrame = -1, locks = 0;
        bool stoppedWhileAiming = false;
        for (int i = 0; i < 600; ++i) {
            const int frameBefore = int(f.animator().frame());
            const bool inAttack = f.state() == State::Attack;
            TickOutput o = step(f, w);
            if (entered(o, State::Attack)) ++attacks;
            if (o.volley) {
                ++volleys;
                shells += o.volley;
                if (o.volley > maxShells) maxShells = o.volley;
                if (emitFrame < 0) emitFrame = frameBefore;
                check(o.volleySpeed > 0.0f, "shell speed comes from the locked aim");
                // #892 burst policy: one key event, three shells, same tick, primary first.
                check(o.burst.shots == 3 && o.burst.intervalTicks == 0 && o.burst.sameTick, "burst is 3 shells in one tick");
                check(o.burst.primaryFirst, "first shell of the burst is the primary");
                check(o.burst.maxSpreadDeg > 0.0f && o.burst.maxSpreadDeg < 25.0f, "burst spread is the +-0.1 jitter");
                // #892: the flash basis is the one the shells left from.
                check(o.shotFired, "a volley tick reports emitShotGun (TChibiShoot)");
                const P2GroinkVec3 m0 = o.volleyMuzzle.column0;
                const float ml = std::sqrt(m0.x * m0.x + m0.y * m0.y + m0.z * m0.z);
                bool along = ml > 0.0f;
                for (std::size_t sl = 0; sl < P2GroinkVolley::kCapacity && along; ++sl) {
                    const P2GroinkShell sh = f.shells().shell(sl);
                    if (!sh.active) continue;
                    // 3D: the kuti axis is steep (lobbed shells), so compare full
                    // directions; the source spread is +-0.1 per axis (< ~10 deg),
                    // gravity has acted for one update at most.
                    const P2GroinkVec3 v = sh.velocity;
                    const float vl = std::sqrt(v.x * v.x + v.y * v.y + v.z * v.z);
                    if (vl > 0.0f) along = (v.x * m0.x + v.y * m0.y + v.z * m0.z) / (vl * ml) > 0.9f;
                }
                check(along, "live shells fly along the reported muzzle axis");
            } else {
                check(!o.shotFired, "no emitShotGun without a volley while the pool has room");
            }
            if (o.lockedOn) ++locks;
            if (inAttack && f.animator().isStopped() && f.gun().rotating() && !f.gun().locked()) stoppedWhileAiming = true;
            for (const auto& h : o.hits) {
                if (h.hit.kind == P2GroinkHitKind::Bomb) {
                    ++hits;
                    check(h.hit.damage == params.attackDamage, "shell Bomb damage is fp24");
                }
            }
        }
        check(attacks >= 2, "the Groink attacks the lane target repeatedly");
        check(maxShells == 3 && volleys >= 2 && shells == 3 * volleys, "every KEYEVENT_4 emits exactly three shells");
        check(emitFrame == 26, "emission latches on the update after the frame-25 key");
        check(stoppedWhileAiming, "KEYEVENT_2 stops the motion while the gun aims");
        check(locks >= 2, "gun lock-on precedes every volley");
        check(hits >= 1, "a shell sweep hits a Pikmin in the impact zone");
        check(f.shells().activeCount() <= P2GroinkVolley::kCapacity, "six-node pool bound");
    }

    // ---- Shake-off: isStartFlick thresholds and the Flick KEYEVENT_2 flicks.
    // A captain high above the lane (|dy| >= 200 is never attackable) keeps
    // the Groink walking, where isStartFlick(false) holds the request.
    {
        World w;
        Fsm f;
        f.init(params, bank, false, w.pos, 0.0f, 5u, nullptr);
        Candidate stuck = piki(4, {0, 0, 5});
        stuck.stuckToSelf = true;
        w.c = {navi(6, {0, 250, 60}), stuck, piki(5, {-50, 0, -40}), piki(7, {500, 0, 0})};
        bool walking = false;
        for (int i = 0; i < 200 && !walking; ++i) walking = entered(step(f, w), State::Walk);
        check(walking, "a visible captain is chased (Walk)");
        w.stuck = 1;
        w.hits = 3; // ip01 = 3: needs MORE than 3 blows below ip02 = 3 stuck
        bool early = entered(step(f, w), State::Flick);
        check(f.flickTimer() == 3.0f, "three blows add three to mFlickTimer");
        for (int i = 0; i < 90; ++i) early = early || entered(step(f, w), State::Flick);
        check(!early && f.flickTimer() == 3.0f, "three blows with one stuck Pikmin never flick");
        w.hits = 1;
        bool flick = false, flicked = false;
        for (int i = 0; i < 200 && !flicked; ++i) {
            TickOutput o = step(f, w);
            flick = flick || entered(o, State::Flick);
            if (o.flick) {
                flicked = true;
                check(o.flickStick.size() == 1 && o.flickStick[0] == 4, "stuck Pikmin flicked (fp16 = 1)");
                check(o.flickPiki.size() == 1 && o.flickPiki[0] == 5, "nearby unstuck Pikmin within fp19");
                check(o.flickNavi.empty(), "captain outside fp19 (3D) not flicked");
                check(o.flickKnockback == params.shakeKnockback && o.flickDamage == params.shakeDamage, "shake parms");
                check(f.flickTimer() == 0.0f, "flick resets mFlickTimer");
            }
        }
        check(flick && flicked, "the fourth blow finishes Walk into Flick");
    }

    // ---- Death: drained health finishes the walk motion into Dead, the dead
    // clip's END requests kill(), shells are dropped on kill.
    {
        World w;
        Fsm f;
        f.init(params, bank, false, w.pos, 0.0f, 9u, nullptr);
        for (int i = 0; i < 5; ++i) step(f, w);
        w.health = 0.0f;
        bool dead = false, kill = false, deadBomb = false;
        for (int i = 0; i < 300 && !kill; ++i) {
            TickOutput o = step(f, w);
            dead = dead || entered(o, State::Dead);
            kill = o.killRequest;
            if (o.deadBomb) {
                deadBomb = true;
                const P2GroinkMuzzle want = f.worldMuzzle(w.pos);
                check(near(o.deadMuzzle.column3.x, want.column3.x, 1e-2f) && near(o.deadMuzzle.column3.y, want.column3.y, 1e-2f)
                      && near(o.deadMuzzle.column3.z, want.column3.z, 1e-2f),
                      "dead KEYEVENT_2 reports the kuti basis (createDeadBombEmitEffect)");
            }
        }
        check(deadBomb, "the dead clip reaches KEYEVENT_2");
        check(dead && kill && f.state() == State::Dead, "0 HP -> Dead -> END kill request");
        check(near(std::hypot(step(f, w).velocity.x, 0.0f), 0.0f, 1e-3f), "Dead stops the target velocity");
    }

    // ---- Territory: chasing beyond fp09 from home -> Lost -> WalkHome.
    {
        World w;
        Fsm f;
        f.init(params, bank, false, w.pos, 0.0f, 13u, nullptr);
        w.c = {navi(6, {0, 250, 80})};
        bool walking = false;
        for (int i = 0; i < 200 && !walking; ++i) walking = entered(step(f, w), State::Walk);
        const P2GroinkVec3 home = f.home();
        // Displace the Groink (and its quarry) far outside the territory.
        w.pos = {home.x, 0.0f, home.z + 400.0f};
        w.c[0].pos = {home.x, 250.0f, home.z + 480.0f};
        bool lost = false, back = false;
        for (int i = 0; i < 400 && !back; ++i) {
            TickOutput o = step(f, w);
            lost = lost || entered(o, State::Lost);
            back = entered(o, State::WalkHome) || entered(o, State::TurnHome);
        }
        check(walking && lost && back, "Walk beyond territory -> Lost -> WalkHome/TurnHome");
        const float d0 = std::hypot(w.pos.x - home.x, w.pos.z - home.z);
        for (int i = 0; i < 150; ++i) step(f, w);
        check(std::hypot(w.pos.x - home.x, w.pos.z - home.z) < d0 - 20.0f, "WalkHome closes on home");
    }

    // ---- FixMiniHoudai (97): same FSM, no locomotion, still fires.
    {
        World w;
        Fsm f;
        f.init(params, bank, true, w.pos, 0.0f, 17u, nullptr);
        w.c = {piki(3, {0, 0, 110})};
        float moved = 0.0f;
        // Phase 1: a high captain is chased (Walk) but must not move the tower.
        std::vector<Candidate> lane = w.c;
        w.c = {navi(8, {60, 250, 120})};
        bool walked = false;
        for (int i = 0; i < 200; ++i) {
            TickOutput o = step(f, w);
            walked = walked || entered(o, State::Walk);
            moved += std::fabs(o.velocity.x) + std::fabs(o.velocity.z);
        }
        check(walked, "fixed variant still enters Walk (turn-in-place)");
        w.c = lane;
        int volleys = 0;
        for (int i = 0; i < 400; ++i) {
            TickOutput o = step(f, w);
            moved += std::fabs(o.velocity.x) + std::fabs(o.velocity.z);
            volleys += o.volley ? 1 : 0;
        }
        check(moved == 0.0f && w.pos.z == 0.0f, "fixed variant never translates");
        check(volleys >= 2, "fixed variant fires volleys");
    }

    if (failures) {
        std::fprintf(stderr, "p2_groink_fsm_test FAILED (%d)\n", failures);
        return 1;
    }
    std::puts("p2_groink_fsm_test PASS");
    return 0;
}
