// #884 wiring guard: the Kabuto 75 campaign path must reach the tested Stone
// seam (pc_p2_kabuto_stone_fleet.h). p2_kabuto_stone_fleet_test drives that
// seam (attackStep / advanceStateTime / stoneTicksFor / Fleet) on host frame
// clocks, but the shipped glue lives in engine-bound files that cannot be
// linked into an engine-free test. This guard reads the shipped sources and
// fails if the glue is reverted or unhooked, e.g. restoring the pre-#884
// doStoneFire instant InteractAttack cone at half the attack clip, dropping
// the gameCoreSection stone update/draw hooks, or losing the reset/forget
// cleanup. Whitespace is ignored when matching.
//
// Usage: p2_kabuto_stone_wiring_test [native_source_root]
// (default: the configured source root, P2_KABUTO_SOURCE_ROOT).
#include <cstdio>
#include <fstream>
#include <sstream>
#include <string>

#ifndef P2_KABUTO_SOURCE_ROOT
#define P2_KABUTO_SOURCE_ROOT "."
#endif

namespace {

int failures = 0;
int checks = 0;

std::string squeeze(const std::string& s)
{
    std::string out;
    out.reserve(s.size());
    for (char c : s) {
        if (c != ' ' && c != '\t' && c != '\r' && c != '\n') {
            out.push_back(c);
        }
    }
    return out;
}

bool load(const std::string& root, const char* rel, std::string& out)
{
    std::ifstream in(root + "/" + rel, std::ios::binary);
    if (!in) {
        std::printf("FAIL open %s/%s\n", root.c_str(), rel);
        ++failures;
        return false;
    }
    std::ostringstream ss;
    ss << in.rdbuf();
    out = squeeze(ss.str());
    return true;
}

void check(bool ok, const char* file, const char* what)
{
    ++checks;
    if (!ok) {
        ++failures;
        std::printf("FAIL %s: %s\n", file, what);
    }
}

bool has(const std::string& text, const char* needle) { return text.find(squeeze(needle)) != std::string::npos; }

// Text from `begin` up to (not including) the first `end` after it; empty if
// `begin` is missing.
std::string region(const std::string& text, const char* begin, const char* end)
{
    const std::string b = squeeze(begin), e = squeeze(end);
    const size_t i = text.find(b);
    if (i == std::string::npos) {
        return std::string();
    }
    const size_t j = text.find(e, i + b.size());
    return text.substr(i, j == std::string::npos ? std::string::npos : j - i);
}

} // namespace

int main(int argc, char** argv)
{
    const std::string root = argc > 1 ? argv[1] : P2_KABUTO_SOURCE_ROOT;
    std::string fsm, core, mapCpp, mapH;
    const char* F = "pc_port/pc_p2_kabuto_fsm.cpp";
    const char* G = "src/plugPikiKando/gameCoreSection.cpp";
    const char* M = "src/plugPikiColin/mapMgr.cpp";
    const char* H = "include/MapMgr.h";
    if (load(root, F, fsm)) {
        // KB_ATTACK goes through the tested seam, in source exec order.
        const std::string attack = region(fsm, "case KB_ATTACK:{", "case KB_FLICK:");
        check(!attack.empty(), F, "KB_ATTACK case present");
        check(has(attack, "p2kabutostone::attackStep(fleet,tokenOf(actor),actor->mHealth,s.fireDone,prevStateTime,s.stateTime,"),
              F, "KB_ATTACK calls p2kabutostone::attackStep with the live health, latch and state clock");
        check(has(attack, "if(step.action==p2kabutostone::AttackAction::Die){die("), F,
              "KB_ATTACK transits to Dead on the seam's death gate");
        check(has(attack, "logStoneFire(s,gen,step);"), F, "KB_ATTACK logs the seam outcome");
        check(!has(attack, "InteractAttack") && !has(attack, "stimulate("), F,
              "KB_ATTACK applies no instant interaction (pre-#884 cone)");
        check(!has(attack, "clipSeconds(\"attack\")*0.5"), F, "KB_ATTACK has no half-clip fire rule");
        check(has(fsm, "const float prevStateTime=p2kabutostone::advanceStateTime(s.stateTime,dt);"), F,
              "state clock advanced by the seam's advanceStateTime");
        check(!has(fsm, "doStoneFire") && !has(fsm, "P2_KABUTO_FIRE generator"), F,
              "pre-#884 doStoneFire / P2_KABUTO_FIRE cone removed");
        check(!has(fsm, "kMouthForwardHostApprox"), F, "no host-approximated mouth offset");
        // Cleanup and ownership.
        const std::string reset = region(fsm, "void pc_p2_kabuto_fsm_reset(){", "void pc_p2_kabuto_fsm_forget(");
        check(has(reset, "fleet.reset();") && has(reset, "stoneDebt=0.0;"), F,
              "reset clears the fleet and the stone clock (teardown / re-entry)");
        const std::string forget = region(fsm, "void pc_p2_kabuto_fsm_forget(", "float pc_p2_kabuto_fsm_param_f(");
        check(has(forget, "fleet.forgetOwner(tok)"), F, "forget orphans the shooter's stones instead of dropping them");
        // Global stone tick / trace / draw.
        const std::string update = region(fsm, "void pc_p2_kabuto_fsm_update_stones(){", "void pc_p2_kabuto_fsm_draw_stones(");
        check(has(update, "p2kabutostone::stoneTicksFor(stoneDebt,gsys->getFrameTime())") && has(update, "stoneTick(snap)"),
              F, "update_stones runs seam-clocked fleet ticks");
        const std::string tick = region(fsm, "void stoneTick(StoneSnapshot& snap){", "void pc_p2_kabuto_fsm_update_stones(");
        check(has(tick, "fleet.tick(p2kabutostone::kStoneGravity,&stoneTrace,&stoneMap,"), F,
              "stoneTick ticks the fleet with the map trace and the retail P2 gravity");
        check(has(tick, "p2_projectile_apply_engine_strike("), F, "strikes reach the P1 receivers");
        check(has(tick, "buildSnapshot(snap);snapshotOthers(snap);"), F,
              "pellets / P1 bosses are offered to the Stone as stopping contacts");
        check(has(tick, "kabutoHost=attack&&code=='t'&&kabutoHostStoneAttack(target,k.damage,hit);"), F,
              "Teki Attack on a Beatle-hosted Kabuto goes through the Kabuto stored-damage path");
        const std::string trace = region(fsm, "bool stoneTrace(", "struct StoneSnapshot");
        check(has(trace, "mv.mIgnoreEnemyCollParts=true;") && has(trace, "mapMgr->traceMove(&m.proxy,mv,dt);"), F,
              "stone trace skips enemy body platforms");
        check(has(trace, "mv.mP2WallThreshold=true;"), F, "stone trace uses the P2 wall classification");
        // Round 4: source attack selection. The attack entry is the lane
        // (p2kabutoaim, the header p2_kabuto_stone_fleet_test drives), never
        // the old 180 / 0.5 rad cone, and Turn has no facing-close-enough exit.
        check(!has(fsm, "boolattackable(") && !has(fsm, "ATTACK_ANGLE") && !has(fsm, "FACE_OK_ANGLE") &&
                  !has(fsm, "nearestTarget("),
              F, "pre-round-4 cone gate / FACE_OK exit / XZ-only nearestTarget removed");
        check(!has(fsm, "s.state==KB_TURN&&s.stateTime>5.0f"), F, "no non-source Turn->Move chase after 5 s");
        // Rounds 5-6: the host offer maps P1 Piki states to their P2 object
        // (sprouts never targets; Pressed / DenkiDying / Swallowed are P2
        // dead() states, so P2 isAlive rejects them), not P1 isAlive only.
        const std::string phase = region(fsm, "p2kabutoaim::PikminPhasepikminPhase(Piki*p){", "structAimSnapshot{");
        check(has(phase, "casePIKISTATE_Grow:casePIKISTATE_Bury:casePIKISTATE_NukareWait:returnp2kabutoaim::PikminPhase::Sprout;") &&
                  has(phase, "casePIKISTATE_Pressed:casePIKISTATE_DenkiDying:casePIKISTATE_Swallowed:returnp2kabutoaim::PikminPhase::Dead;") &&
                  has(phase, "if(p->isStickToMouth())returnp2kabutoaim::PikminPhase::Dead;") &&
                  !has(phase, "StuckToMouth"),
              F, "pikminPhase maps Grow/Bury/NukareWait to Sprout and Pressed/DenkiDying/Swallowed/mouth-held to Dead");
        const std::string aimBuild = region(fsm, "voidbuildAim(AimSnapshot&a){", "floatrngUnit(");
        check(has(aimBuild, "push(q,p2kabutoaim::pikminCandidate(aimVec(q->getPosition()),true,pikminPhase(q)));") &&
                  has(aimBuild, "push(n,p2kabutoaim::naviCandidate(aimVec(n->getPosition()),true));") &&
                  !has(aimBuild, "k.alive=true;"),
              F, "buildAim offers Pikmin through pikminCandidate(pikminPhase) and Navis through naviCandidate");
        const std::string wait = region(fsm, "case KB_WAIT:{", "case KB_TURN:{");
        check(has(wait, "p2kabutoaim::waitWantsTurn(s.waitTimer,searched())") && !has(wait, "KB_ATTACK"), F,
              "Wait latches Turn (target or 3 s) and never attacks directly");
        const std::string turn = region(fsm, "case KB_TURN:{", "case KB_MOVE:{");
        check(has(turn, "p2kabutoaim::turnExec(apos,s.heading,dt,p2kabutoaim::viewAngleDeg(s.alert),") &&
                  has(turn, "if(r.next==p2kabutoaim::Next::Attack){logLane(gen,\"turn\",s,pos,aim);transition(actor,s,KB_ATTACK,\"attack\",gen);}") &&
                  !has(turn, "KB_WAIT,"),
              F, "Turn turns via turnExec, attacks only on the lane decision, and never drops to Wait");
        const std::string move = region(fsm, "case KB_MOVE:{", "case KB_ATTACK:{");
        check(has(move, "p2kabutoaim::moveExec(") && has(move, "if(r.next==p2kabutoaim::Next::Attack)"), F,
              "Move attacks only on the lane decision");
        check(has(fsm, "void pc_p2_kabuto_fsm_draw_stones(Graphics& gfx){"), F, "stone draw defined");
        // The Iwagon stand-in shares TekiShapeObject::mAnimContext, which is
        // null until a live Iwagon draws; updateAnim would then halt on
        // ERROR("no joint anim!!") (shapeBase.cpp:3358-3361).
        // The draw is the last definition in the file: take it to the end.
        const std::string drawTail = region(fsm, "void pc_p2_kabuto_fsm_draw_stones(Graphics& gfx){", "#if");
        check(has(drawTail, "AnimData*constsharedAnim=so?so->mAnimContext.mData:nullptr;") &&
                  has(drawTail, "AnimData*constshapeAnim=(shape&&shape->mCurrentAnimation)?shape->mCurrentAnimation->mData:nullptr;") &&
                  has(drawTail, "AnimData*constdrawAnim=sharedAnim?sharedAnim:shapeAnim;"),
              F, "stone draw falls back to the shape's current animation data when the shared Iwagon context is empty");
        check(has(drawTail, "if(!shape||!drawAnim)return;"), F, "stone draw skips when no anim data is bindable");
        {
            const size_t bind = drawTail.find(squeeze("so->mAnimContext.mData=drawAnim;"));
            const size_t anim = drawTail.find(squeeze("shape->updateAnim(gfx,view,&frame,nullptr);"));
            const size_t restore = drawTail.find(squeeze("so->mAnimContext.mData=sharedAnim;"));
            check(bind != std::string::npos && anim != std::string::npos && restore != std::string::npos &&
                      bind < anim && anim < restore,
                  F, "stone draw binds the anim before updateAnim and restores the shared context after");
        }
        check(!drawTail.empty(), F, "stone draw region found");
    }
    if (load(root, G, core)) {
        check(has(core, "#include \"pc_p2_kabuto_fsm.h\""), G, "includes pc_p2_kabuto_fsm.h");
        check(has(core, "pc_p2_kabuto_fsm_update_stones();"), G, "calls pc_p2_kabuto_fsm_update_stones each frame");
        check(has(core, "pc_p2_kabuto_fsm_draw_stones(gfx);"), G, "calls pc_p2_kabuto_fsm_draw_stones");
    }
    if (load(root, M, mapCpp)) {
        check(has(mapCpp, "if (trace.mIgnoreEnemyCollParts && coll->mCreature && (coll->mCreature->isTeki() || coll->mCreature->isBoss())) {"),
              M, "traceMove honours MoveTrace::mIgnoreEnemyCollParts");
        check(has(mapCpp, "const bool isWall = trace.mP2WallThreshold") &&
                  has(mapCpp, "(collNormal.y < 0.6f && collNormal.y <= 0.70710677f && collNormal.y >= -0.70710677f)") &&
                  has(mapCpp, ": (tri->mTriangle.mNormal.y < 0.5f && tri->mTriangle.mNormal.y > -0.5f);") &&
                  has(mapCpp, "if (collisionType != NoCollision && isWall) {"),
              M, "traceMove honours MoveTrace::mP2WallThreshold and keeps the P1 rule by default");
    }
    if (load(root, H, mapH)) {
        check(has(mapH, "mIgnoreEnemyCollParts   = false;") && has(mapH, "bool mIgnoreEnemyCollParts;"), H,
              "MoveTrace::mIgnoreEnemyCollParts defaults to false");
        check(has(mapH, "mP2WallThreshold        = false;") && has(mapH, "bool mP2WallThreshold;"), H,
              "MoveTrace::mP2WallThreshold defaults to false");
    }
    std::printf("p2_kabuto_stone_wiring_test root=%s checks=%d failures=%d\n", root.c_str(), checks, failures);
    if (failures) {
        return 1;
    }
    std::printf("p2_kabuto_stone_wiring_test: all checks passed\n");
    return 0;
}
