// In-game dev console (#942). See pc_dev_console.h for the contract.
#include "pc_dev_console.h"
#include "pc_dev_console_parser.h"
#include "pc_randomizer.h"
#include "pc_p2_generated_placement.h"
#include "pc_p2_smoke_any_slot.h"
#include "pc_p2_campaign_actor.h"
#include "pc_p2_kabuto_host.h"
#include "pc_p2_sarai_manager.h"
#include "pc_p2_fuefuki_teki.h"
#include "pc_p2_groink_teki.h"
#include "pc_p2_breadbug_teki.h"
#include "pc_p2_bigtreasure_teki.h"
#include "pc_p2_bombsarai_teki.h"
#include "pc_p2_kurage_teki.h"
#include "pc_p2_onikurage_teki.h"
#include "pc_p2_king_teki.h"
#include "pc_p2_queen_teki.h"
#include "pc_p2_demon_host.h"
#include "pc_p2_preview.h"
#include "pc_p2_teki_lifetime.h"
#include "system.h"
#include "Graphics.h"
#include "Font.h"
#include "Colour.h"
#include "Geometry.h"
#include "Generator.h"
#include "TekiParameters.h"
#include "TekiPersonality.h"
#include "teki.h"
#include "MapMgr.h"
#include "Navi.h"
#include "NaviMgr.h"
#include "Piki.h"
#include "PikiMgr.h"
#include "BombItem.h"
#include "ItemMgr.h"
#include "GameStat.h"
#include "gameflow.h"
#include "MoviePlayer.h"
#include "FlowController.h"
#include <SDL.h>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <map>
#include <new>
#include <string>
#include <vector>

namespace {
using namespace devconsole;

bool sEnabled = false;
bool sOpen = false;
std::string sInput;
std::string sLastLine;
std::vector<std::string> sQueue;
std::string sScriptPath;
long sScriptOffset = 0;
unsigned sFrame = 0;

struct OutputLine {
    std::string text;
    Uint32 atMs;
};
std::vector<OutputLine> sScreenLog;
constexpr int kScreenLogLines = 8;
constexpr Uint32 kScreenLogTtlMs = 12000;

// One runtime generator per spawned species (registered under the dev target
// uid) so every family binder keys off pc_p2_campaign_token() exactly as a
// seed-placed actor does. Allocated outside the engine heaps and never freed;
// the map is dropped on each new scene so a stale pointer is never reused.
std::map<unsigned, Generator*> sGenerators;
unsigned long sGeneratorScene = 0;

void say(const char* fmt, ...)
{
    char buf[512];
    va_list vl;
    va_start(vl, fmt);
    std::vsnprintf(buf, sizeof(buf), fmt, vl);
    va_end(vl);
    std::printf("DEV_CONSOLE %s\n", buf);
    std::fflush(stdout);
    sScreenLog.push_back({buf, SDL_GetTicks()});
    while (int(sScreenLog.size()) > kScreenLogLines) sScreenLog.erase(sScreenLog.begin());
}

bool argvHasNetplay(int argc, char** argv)
{
    static const char* const kSwitches[] = {
        "--netplay-host", "--netplay-join", "--netplay-ice-host", "--netplay-ice-join",
        "--netplay-host-ice", "--netplay-join-ice",
    };
    for (int i = 1; i < argc; ++i) {
        if (!argv[i]) continue;
        for (const char* s : kSwitches) if (!std::strcmp(argv[i], s)) return true;
    }
    return false;
}

bool envSet(const char* name)
{
    const char* v = std::getenv(name);
    return v && *v;
}

Navi* captain()
{
    if (!naviMgr) return nullptr;
    Navi* navi = naviMgr->getActiveNavi();
    return navi ? navi : naviMgr->getNavi();
}

float groundY(float x, float z, float fallback)
{
    if (!mapMgr) return fallback;
    const float y = mapMgr->getMinY(x, z, true);
    return std::isfinite(y) ? y : fallback;
}

Generator* devGenerator(unsigned source)
{
    const unsigned long scene = pc_p2_scene_generation();
    if (scene != sGeneratorScene) {
        // Never dereference the previous scene's generators: their teki are
        // gone and pc_randomizer_bind_generator re-keys any reused address.
        sGenerators.clear();
        sGeneratorScene = scene;
    }
    auto it = sGenerators.find(source);
    if (it != sGenerators.end()) return it->second;
    void* raw = std::malloc(sizeof(Generator));
    if (!raw) return nullptr;
    Generator* gen = new (raw) Generator();
    const unsigned uid = devTargetUid(source);
    gen->_70 = uid;
    pc_randomizer_dev_set_generator_id(gen, uid);
    sGenerators[source] = gen;
    return gen;
}

int p1TypeByName(const char* token)
{
    for (int i = TEKI_START; i < TEKI_TypeCount; ++i) {
        const char* name = TekiMgr::getTypeName(i);
        if (name && ieq(name, token)) return i;
    }
    return -1;
}

void fullRebind(const char* why)
{
    say("rebind=full reason=%s (every P2 family setup re-runs; existing P2 actors restart their FSM)", why);
    pc_p2_kurage_teki_setup();
    pc_p2_onikurage_teki_setup();
    pc_p2_bombsarai_teki_setup();
    pc_p2_groink_teki_setup();
    pc_p2_breadbug_teki_setup();
    pc_p2_bigtreasure_teki_setup();
    pc_p2_king_teki_setup();
    pc_p2_queen_teki_setup();
    pc_p2_demon_manager_setup();
    pc_p2_sarai_manager_setup();
    pc_p2_preview_setup();
}

// Families with a per-actor binder we can call right after birth. Everything
// else goes through the generic setup rerun (`rebind`).
bool lateBind(BTeki* actor, unsigned source, unsigned uid, bool rebindAllowed)
{
    switch (source) {
    case 41: return pc_p2_fuefuki_teki_bind_dynamic(actor);
    case 78: return pc_p2_groink_teki_bind_dynamic(actor);
    case 38: return pc_p2_breadbug_teki_bind_dynamic(actor);
    case 32: // Bound at birth when mGenerator was already set; retry otherwise.
        return pc_p2_sarai_manager_demon_host(actor) != nullptr || pc_p2_sarai_manager_bind_demon(actor, uid, uid);
    case 23:   // Sarai dynamic binder ran at birth (pc_p2_generated_placement_bind).
    case 73:   // BigTreasure binds late spawns on their first tick.
    case 2: case 33: case 35: case 43: case 53: case 67: case 76: // Chappy dynamic binder at birth.
    case 42:   // BlueChappy dynamic binder at birth.
    case 59: case 60: case 61: case 62: // Otakara dynamic binder at birth.
    case 75:   // Kabuto dynamic binder at birth.
        return true;
    default:
        if (!rebindAllowed) {
            say("no per-actor binder for source %u; actor stays a P1 host until `rebind`", source);
            return false;
        }
        char why[32];
        std::snprintf(why, sizeof(why), "source_%u", source);
        fullRebind(why);
        return true;
    }
}

void spawnP2(const Species& sp, int count, bool rebindAllowed)
{
    if (!pc_randomizer_p2_bridge()) {
        say("spawn %u refused: this session has no P2 seed bridge (launch through scripts/p2_dev_console.py)", sp.source);
        return;
    }
    const unsigned uid = devTargetUid(sp.source);
    if (pc_randomizer_p2_source_for_id(uid) != sp.source) {
        say("spawn %u %s refused: not staged in this session (seed has no dev binding for it; see `list`)",
            sp.source, sp.enumName);
        return;
    }
    Navi* navi = captain();
    if (!navi || !tekiMgr) {
        say("spawn refused: no captain/teki manager (not in gameplay?)");
        return;
    }
    Generator* gen = devGenerator(sp.source);
    if (!gen) {
        say("spawn refused: generator allocation failed");
        return;
    }
    const int hostType = pc_randomizer_enemy_for_generator(hostTypeFor(sp.source), false, gen);
    if (hostType < TEKI_START || hostType >= TEKI_TypeCount || !tekiMgr->hasType(hostType)) {
        say("spawn %u refused: host teki type %d unavailable", sp.source, hostType);
        return;
    }
    if (!tekiMgr->hasModel(hostType))
        say("warning: host model %s (%d) not loaded in this stage; the P1 fallback body will not draw",
            TekiMgr::getTypeName(hostType), hostType);
    const Vector3f base = navi->getPosition();
    const float dir = navi->mFaceDirection;
    for (int i = 0; i < count; ++i) {
        const float dist = 140.0f + 45.0f * float(i);
        const float side = (i % 2 ? 1.0f : -1.0f) * 30.0f * float(i / 2);
        Vector3f pos(base.x + std::sin(dir) * dist + std::cos(dir) * side, base.y,
                     base.z + std::cos(dir) * dist - std::sin(dir) * side);
        pos.y = groundY(pos.x, pos.z, base.y);
        gen->setPos(pos);
        Teki* teki = tekiMgr->newTeki(hostType);
        if (!teki) {
            say("spawn %u: teki pool exhausted after %d", sp.source, i);
            return;
        }
        // Same recipe as GenObjectTeki::birth for an unprotected slot.
        TekiPersonality personality;
        personality.reset();
        personality.mPosition.set(pos.x, pos.y, pos.z);
        personality.mNestPosition.set(1.0f, 1.0f, 1.0f);
        personality.mFaceDirection = dir + 3.14159265f; // face the captain
        teki->mPersonality->input(personality);
        teki->reset();
        teki->startAI(0);
        teki->mSRT.r.set(0.0f, personality.mFaceDirection, 0.0f);
        teki->mGenerator = gen;
        gen->mLatestSpawnCreature = teki;
        gen->mAliveCount++;
        std::printf("P2_SEED_RESOLVE source_id=%u target=%u original_type=%d x=%.1f z=%.1f dev_console=1\n",
                    sp.source, uid, hostType, pos.x, pos.z);
        BTeki* actor = static_cast<BTeki*>(teki);
        pc_p2_generated_placement_bind(actor, sp.source, uid, uid);
        pc_p2_kabuto_bind_dynamic(teki, uid, sp.source);
        const bool bound = lateBind(actor, sp.source, uid, rebindAllowed && i == count - 1);
        say("spawned source=%u %s (%s) uid=%u host=%s(%d) x=%.1f y=%.1f z=%.1f late_bind=%d",
            sp.source, sp.enumName, sp.commonName, uid, TekiMgr::getTypeName(hostType), hostType,
            pos.x, pos.y, pos.z, bound ? 1 : 0);
    }
}

void spawnP1(const char* token, int count)
{
    const int type = p1TypeByName(token);
    if (type < 0) {
        say("unknown species '%s' (P2 id/name or P1 teki name; see `list`)", token);
        return;
    }
    Navi* navi = captain();
    if (!navi || !tekiMgr) {
        say("spawn refused: no captain/teki manager (not in gameplay?)");
        return;
    }
    if (!tekiMgr->hasType(type)) {
        say("spawn %s refused: teki type %d has no parameters in this stage", token, type);
        return;
    }
    if (!tekiMgr->hasModel(type))
        say("warning: model for %s (%d) not loaded in this stage", TekiMgr::getTypeName(type), type);
    const Vector3f base = navi->getPosition();
    const float dir = navi->mFaceDirection;
    for (int i = 0; i < count; ++i) {
        const float dist = 140.0f + 45.0f * float(i);
        Vector3f pos(base.x + std::sin(dir) * dist, base.y, base.z + std::cos(dir) * dist);
        pos.y = groundY(pos.x, pos.z, base.y);
        Teki* teki = tekiMgr->newTeki(type);
        if (!teki) {
            say("spawn %s: teki pool exhausted after %d", token, i);
            return;
        }
        TekiPersonality personality;
        personality.reset();
        personality.mPosition.set(pos.x, pos.y, pos.z);
        personality.mNestPosition.set(1.0f, 1.0f, 1.0f);
        personality.mFaceDirection = dir + 3.14159265f;
        teki->mPersonality->input(personality);
        teki->reset();
        teki->startAI(0);
        teki->mSRT.r.set(0.0f, personality.mFaceDirection, 0.0f);
        say("spawned p1 %s(%d) x=%.1f y=%.1f z=%.1f", TekiMgr::getTypeName(type), type, pos.x, pos.y, pos.z);
    }
}

float distXZ(const Vector3f& a, const Vector3f& b)
{
    const float dx = a.x - b.x, dz = a.z - b.z;
    return std::sqrt(dx * dx + dz * dz);
}

void killNearest(bool all)
{
    Navi* navi = captain();
    if (!navi || !tekiMgr) {
        say("kill refused: not in gameplay");
        return;
    }
    BTeki* best = nullptr;
    float bestDist = 0.0f;
    int killed = 0;
    Iterator it(tekiMgr);
    CI_LOOP(it) {
        BTeki* t = static_cast<BTeki*>(*it);
        if (!t || !t->isAlive() || t->mDeadState != 0 || t->mHealth <= 0.0f) continue;
        if (t->mTekiType == TEKI_Palm) continue; // Pellet Posy is not an enemy
        // P2-bound actors (the ones under test) outrank plain P1 tekis.
        const float d = distXZ(t->getPosition(), navi->getPosition()) + (pc_p2_campaign_source(t) ? 0.0f : 100000.0f);
        if (all) {
            // Health 0 + die() arms the natural death: the P1 strategy, the
            // family tick (external-die escape) or a health-watching host
            // (Sarai/Demon) finalises it through dieSoon(), so the corpse
            // pelletises and can be carried.
            t->mHealth = 0.0f;
            t->die();
            ++killed;
            continue;
        }
        if (!best || d < bestDist) {
            best = t;
            bestDist = d;
        }
    }
    if (all) {
        say("killall: %d actors dying", killed);
        return;
    }
    if (!best) {
        say("kill: no live enemy");
        return;
    }
    const unsigned token = pc_p2_campaign_token(best);
    const unsigned source = pc_p2_campaign_source(best);
    best->mHealth = 0.0f;
    best->die();
    say("kill: %s(%d) source=%u uid=%u dist=%.0f (natural die(); corpse follows the family/P1 path)",
        TekiMgr::getTypeName(best->mTekiType), best->mTekiType, source, token, bestDist);
}

// hurt: damage every live campaign P2 actor to (1 - fraction) of its max health
// without killing it, so the life gauge (P1 wheel) can be inspected.
void hurtAll(float fraction, bool stored)
{
    if (!tekiMgr) {
        say("hurt refused: not in gameplay");
        return;
    }
    int n = 0;
    Iterator it(tekiMgr);
    CI_LOOP(it) {
        BTeki* t = static_cast<BTeki*>(*it);
        if (!t || !t->isAlive() || t->mDeadState != 0 || t->mHealth <= 0.0f || !pc_p2_campaign_source(t)) continue;
        // `stored` queues the damage the way a Pikmin hit does (mStoredDamage); the
        // families that own their health (Dwarf Orange, Breadbug) drain it, whereas
        // a direct mHealth write is overwritten by their FSM.
        if (stored) t->mStoredDamage += t->getMaxLife() * fraction;
        else t->mHealth = t->getMaxLife() * (1.0f - fraction);
        ++n;
    }
    say("hurt: %d P2 actors set to %.0f%% health", n, (1.0f - fraction) * 100.0f);
}

// Lit P1 bomb rocks (BombAI::BOMB_Set, the state a Pikmin's set-down starts,
// aiPut.cpp) 60 units to the captain's side: a reference for P2 bomb visuals.
void litBombs(int count)
{
    Navi* navi = captain();
    if (!navi || !itemMgr || !mapMgr) { say("bomb: not in gameplay"); return; }
    int made = 0;
    for (int i = 0; i < count; ++i) {
        const float angle = navi->mFaceDirection + 1.5707963f + (i - (count - 1) * 0.5f) * 0.35f; // to the side, clear of the captain
        Vector3f pos = navi->mSRT.t + Vector3f(60.0f * sinf(angle), 0.0f, 60.0f * cosf(angle));
        pos.y = mapMgr->getMinY(pos.x, pos.z, true) + 3.0f;
        BombItem* bomb = static_cast<BombItem*>(itemMgr->birth(OBJTYPE_Bomb));
        if (!bomb) break;
        bomb->init(pos);
        bomb->startAI(0);
        C_SAI(bomb)->start(bomb, BombAI::BOMB_Set);
        std::printf("DEV_CONSOLE_P1_BOMB n=%d x=%.1f y=%.1f z=%.1f fuse=%.2f state=set\n", made, pos.x, pos.y, pos.z,
                    bomb->mSAICtx.mCurrentItemHealth);
        ++made;
    }
    say("bomb: %d lit P1 bomb rock(s)", made);
}

void addPikmin(int colour, int count)
{
    Navi* navi = captain();
    if (!navi || !pikiMgr || !mapMgr) {
        say("pikmin refused: not in gameplay");
        return;
    }
    int born = 0;
    for (int i = 0; i < count; ++i) {
        Piki* piki = static_cast<Piki*>(pikiMgr->birth());
        if (!piki) break;
        GameStat::workPikis.inc(colour);
        piki->init(navi);
        Vector3f at = navi->getPosition();
        at.x += (colour - 1) * 25.0f + float((i % 5) - 2) * 18.0f;
        at.z += float(i / 5) * 20.0f - 40.0f;
        at.y = mapMgr->getMinY(at.x, at.z, true);
        piki->Creature::init(at);
        piki->initColor(colour);
        piki->changeMode(PikiMode::FormationMode, navi);
        ++born;
    }
    static const char* const names[] = {"blue", "red", "yellow"};
    say("pikmin: %d %s added to the squad", born, names[colour]);
}

void teleport(const Command& c)
{
    Navi* navi = captain();
    if (!navi) {
        say("tp refused: not in gameplay");
        return;
    }
    if (c.arena && flowCont.mCurrentStage && flowCont.mCurrentStage->mStageID != c.arena->stage)
        say("warning: arena %s is on stage %d, current stage is %d", c.arena->id, c.arena->stage,
            flowCont.mCurrentStage->mStageID);
    Vector3f pos(c.x, navi->getPosition().y, c.z);
    pos.y = c.arena ? c.arena->y : groundY(c.x, c.z, pos.y);
    navi->mSRT.t.set(pos.x, pos.y, pos.z);
    navi->mVelocity.set(0.0f, 0.0f, 0.0f);
    say("tp: captain at x=%.1f y=%.1f z=%.1f%s%s", pos.x, pos.y, pos.z, c.arena ? " arena=" : "",
        c.arena ? c.arena->id : "");
}

void listSpecies()
{
    const bool bridge = pc_randomizer_p2_bridge();
    std::string staged, missing;
    for (const Species& s : kSpecies) {
        char item[64];
        std::snprintf(item, sizeof(item), " %u:%s", s.source, s.enumName);
        const bool ok = bridge && pc_randomizer_p2_source_for_id(devTargetUid(s.source)) == s.source;
        (ok ? staged : missing) += item;
    }
    say("staged (spawnable):%s", staged.empty() ? " none" : staged.c_str());
    say("not staged:%s", missing.empty() ? " none" : missing.c_str());
    say("p1 names: any TekiMgr type name, e.g. swallow chappy frog beatle");
}

void runCommand(const Command& c, const char* line)
{
    if (c.kind == Cmd::None) return;
    say("> %s", line);
    if (c.error[0]) {
        say("error: %s", c.error);
        return;
    }
    switch (c.kind) {
    case Cmd::Help: say("%s", helpText()); break;
    case Cmd::List: listSpecies(); break;
    case Cmd::Spawn:
        if (c.species) spawnP2(*c.species, c.count, c.rebind);
        else spawnP1(c.token, c.count);
        break;
    case Cmd::Kill: killNearest(false); break;
    case Cmd::KillAll: killNearest(true); break;
    case Cmd::Hurt: hurtAll(c.time, c.stored); break;
    case Cmd::Pikmin: addPikmin(c.colour, c.count); break;
    case Cmd::Day:
        gameflow.mWorldClock.mCurrentDay = c.day;
        say("day set to %d (generator day gates apply on the next stage load)", c.day);
        break;
    case Cmd::Time:
        gameflow.mWorldClock.setTime(c.time);
        say("time set to %.2f h", c.time);
        break;
    case Cmd::Tp: teleport(c); break;
    case Cmd::Pos: {
        Navi* navi = captain();
        if (!navi) { say("pos: not in gameplay"); break; }
        const Vector3f& p = navi->getPosition();
        say("pos: x=%.1f y=%.1f z=%.1f face=%.2f stage=%d day=%d time=%.2f", p.x, p.y, p.z, navi->mFaceDirection,
            flowCont.mCurrentStage ? flowCont.mCurrentStage->mStageID : -1, gameflow.mWorldClock.mCurrentDay,
            gameflow.mWorldClock.mTimeOfDay);
        break;
    }
    case Cmd::Rebind: fullRebind("command"); break;
    case Cmd::Bomb: litBombs(c.count); break;
    case Cmd::Unknown:
    case Cmd::None:
        break;
    }
}

void pollScript()
{
    if (sScriptPath.empty()) return;
    std::ifstream in(sScriptPath, std::ios::binary);
    if (!in) return;
    in.seekg(0, std::ios::end);
    const long size = long(in.tellg());
    if (size < sScriptOffset) sScriptOffset = 0; // truncated/rewritten: start over
    if (size == sScriptOffset) return;
    in.seekg(sScriptOffset);
    std::string tail(size_t(size - sScriptOffset), '\0');
    in.read(&tail[0], std::streamsize(tail.size()));
    tail.resize(size_t(in.gcount()));
    // Only complete lines: a writer mid-append leaves the unterminated tail
    // for the next poll.
    const size_t lastNewline = tail.rfind('\n');
    if (lastNewline == std::string::npos) return;
    size_t start = 0;
    while (start <= lastNewline) {
        const size_t end = tail.find('\n', start);
        std::string line = tail.substr(start, end - start);
        start = end + 1;
        while (!line.empty() && (line.back() == '\r' || line.back() == ' ')) line.pop_back();
        if (!line.empty()) sQueue.push_back(line);
    }
    sScriptOffset += long(lastNewline + 1);
}
} // namespace

void pc_dev_console_init(int argc, char** argv)
{
    const char* v = std::getenv("PIKMIN_DEV_CONSOLE");
    sEnabled = v && !std::strcmp(v, "1");
    if (!sEnabled) return;
    if (argvHasNetplay(argc, argv) || envSet("PIKMIN_NETPLAY_HOST") || envSet("PIKMIN_NETPLAY_JOIN")) {
        sEnabled = false;
        pc_p2_smoke_any_slot_force_off("netplay");
        std::printf("DEV_CONSOLE refused reason=netplay_session (runtime spawns would desync lockstep)\n");
        std::fflush(stdout);
        return;
    }
    if (const char* script = std::getenv("PIKMIN_DEV_CONSOLE_SCRIPT")) sScriptPath = script;
    std::printf("DEV_CONSOLE enabled key=backquote script=%s\n", sScriptPath.empty() ? "none" : sScriptPath.c_str());
    std::fflush(stdout);
}

bool pc_dev_console_enabled() { return sEnabled; }
bool pc_dev_console_open() { return sEnabled && sOpen; }

bool pc_dev_console_handle_event(const SDL_Event& event)
{
    if (!sEnabled) return false;
    if (event.type == SDL_KEYDOWN) {
        const SDL_Scancode sc = event.key.keysym.scancode;
        if (sc == SDL_SCANCODE_GRAVE) {
            if (event.key.repeat) return true;
            sOpen = !sOpen;
            if (sOpen) SDL_StartTextInput(); else SDL_StopTextInput();
            return true;
        }
        if (!sOpen) return false;
        switch (sc) {
        case SDL_SCANCODE_RETURN:
        case SDL_SCANCODE_KP_ENTER:
            if (!sInput.empty()) {
                sQueue.push_back(sInput);
                sLastLine = sInput;
                sInput.clear();
            }
            break;
        case SDL_SCANCODE_BACKSPACE:
            if (!sInput.empty()) sInput.pop_back();
            break;
        case SDL_SCANCODE_ESCAPE:
            sOpen = false;
            SDL_StopTextInput();
            break;
        case SDL_SCANCODE_UP:
            sInput = sLastLine;
            break;
        default:
            break;
        }
        return true;
    }
    if (event.type == SDL_KEYUP) return sOpen;
    if (event.type == SDL_TEXTINPUT) {
        if (!sOpen) return false;
        for (const char* p = event.text.text; *p; ++p)
            if (*p != '`' && (unsigned char)*p >= 32 && (unsigned char)*p < 127 && sInput.size() < 120) sInput.push_back(*p);
        return true;
    }
    return false;
}

void pc_dev_console_execute(const char* line)
{
    if (!sEnabled || !line) return;
    runCommand(parse(line), line);
}

void pc_dev_console_update()
{
    if (!sEnabled) return;
    if ((++sFrame % 20u) == 0u) pollScript();
    if (sQueue.empty()) return;
    // Hold commands through the day-start cutscene/landing: creatures do not
    // tick while the movie player owns the frame, so a spawn/kill issued then
    // would only settle (at the wrong position) once gameplay starts.
    if (gameflow.mMoviePlayer && gameflow.mMoviePlayer->mIsActive) return;
    std::vector<std::string> pending;
    pending.swap(sQueue);
    for (const std::string& line : pending) pc_dev_console_execute(line.c_str());
}

void pc_dev_console_reserve_host_types()
{
    if (!sEnabled || !tekiMgr || !pc_randomizer_p2_bridge()) return;
    std::string reserved;
    for (const Species& s : kSpecies) {
        if (pc_randomizer_p2_source_for_id(devTargetUid(s.source)) != s.source) continue;
        const int host = hostTypeFor(s.source);
        if (host < TEKI_START || host >= TEKI_TypeCount || !tekiMgr->hasType(host)) continue;
        tekiMgr->mUsingType[host] = true;
        const int spawn = tekiMgr->mTekiParams[host]->getI(TPI_SpawnType);
        if (spawn >= TEKI_START && spawn < TEKI_TypeCount) tekiMgr->mUsingType[spawn] = true;
        char item[48];
        std::snprintf(item, sizeof(item), " %u->%s", s.source, TekiMgr::getTypeName(host));
        reserved += item;
    }
    std::printf("DEV_CONSOLE reserved host types:%s\n", reserved.empty() ? " none" : reserved.c_str());
    std::fflush(stdout);
}

void pc_dev_console_draw()
{
    if (!sEnabled || !gsys || !gsys->mDGXGfx || !gsys->mConsFont) return;
    const Uint32 now = SDL_GetTicks();
    while (!sScreenLog.empty() && now - sScreenLog.front().atMs > kScreenLogTtlMs) sScreenLog.erase(sScreenLog.begin());
    if (!sOpen && sScreenLog.empty()) return;
    Graphics& gfx = *gsys->mDGXGfx;
    Font* font = gsys->mConsFont;
    const int w = gfx.mScreenWidth, h = gfx.mScreenHeight;
    Matrix4f ortho;
    gfx.setOrthogonal(ortho.mMtx, RectArea(0, 0, w, h));
    gfx.setViewport(RectArea(0, 0, w, h));
    gfx.setScissor(RectArea(0, 0, w, h));
    gfx.setFog(false);
    const int lineH = font->mCharHeight + 2;
    const int lines = int(sScreenLog.size()) + (sOpen ? 1 : 0);
    const int top = h - 12 - lines * lineH;
    gfx.useTexture(nullptr, GX_TEXMAP0);
    gfx.setColour(Colour(0, 0, 0, 150), true);
    gfx.setAuxColour(Colour(0, 0, 0, 150));
    gfx.fillRectangle(RectArea(8, top - 4, w - 8, h - 8));
    int y = top;
    auto text = [&](int x, int yy, const Colour& c, const char* s) {
        gfx.setColour(Colour(0, 0, 0, 220), true);
        gfx.setAuxColour(Colour(0, 0, 0, 220));
        gfx.texturePrintf(font, x + 1, yy + 1, "%s", s);
        gfx.setColour(c, true);
        gfx.setAuxColour(c);
        gfx.texturePrintf(font, x, yy, "%s", s);
    };
    for (const OutputLine& l : sScreenLog) {
        text(14, y, Colour(220, 220, 220, 255), l.text.c_str());
        y += lineH;
    }
    if (sOpen) {
        char buf[160];
        std::snprintf(buf, sizeof(buf), "> %s%s", sInput.c_str(), (now / 400u) % 2u ? "_" : " ");
        text(14, y, Colour(255, 229, 120, 255), buf);
    }
}
