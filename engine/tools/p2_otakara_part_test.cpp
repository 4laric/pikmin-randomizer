// p2_otakara_part_test (Dweevil family fidelity): the retail Otakara collision tree has exactly
// one stickable, damageable part (the body sphere on joint 11) and nothing on the legs, and
// OtakaraBase::damageCallBack damages only through a part (OtakaraBase.cpp:190-197), so the
// partless ground punch is refused while a latched Pikmin attack is accepted. BombOtakara
// overrides damageCallBack without a part test (BombOtakara.cpp) and is not gated.
//
// Engine-free parts exercise pc_p2_otakara_part.h. The wiring part reads the engine sources as
// text: InteractAttack::actTeki asks pc_p2_otakara_attack_part before the host interact and
// returns false on a refusal, pc_p2_otakara.cpp exempts BombOtakara, and the retail tree data
// matches the disc enemycoll.txt (two spheres, both on joint 11).
//
// Negative controls:
//   * -DP2_OTAKARA_PART_TEST_LEGACY swaps the verdict for the pre-fix behaviour (every attack is
//     accepted, the P1 host tree has stickable parts everywhere), so the test fails.
//   * Passing a source root as argv[1] that holds the pre-fix tekiinteraction.cpp makes the
//     wiring checks fail.
//
// NOTE: checks use an always-evaluated CHECK macro, never bare assert().
#include "pc_p2_otakara_part.h"

#include <cmath>
#include <cstdio>
#include <cstring>
#include <fstream>
#include <sstream>
#include <string>

#ifndef P2_OTAKARA_PART_SOURCE_ROOT
#define P2_OTAKARA_PART_SOURCE_ROOT "."
#endif

static int failures = 0;

#define CHECK(cond)                                                                       \
    do {                                                                                  \
        if (!(cond)) {                                                                    \
            std::printf("P2_OTAKARA_PART_TEST_FAIL line=%d check=%s\n", __LINE__, #cond); \
            ++failures;                                                                   \
        }                                                                                 \
    } while (0)

namespace {

#ifdef P2_OTAKARA_PART_TEST_LEGACY
// Pre-fix: the Chappy host accepts every attack, part or not.
p2otakarapart::Verdict underTest(bool) { return {true, "legacy_accept_all"}; }
#else
p2otakarapart::Verdict underTest(bool partPresent) { return p2otakarapart::verdict(partPresent); }
#endif

std::string readFile(const std::string& path) {
    std::ifstream in(path, std::ios::binary);
    if (!in) return std::string();
    std::ostringstream ss;
    ss << in.rdbuf();
    return ss.str();
}

std::string functionBody(const std::string& text, const std::string& signature) {
    const size_t at = text.find(signature);
    if (at == std::string::npos) return std::string();
    size_t end = text.find("\n}", at);
    if (end == std::string::npos) end = text.size();
    return text.substr(at, end - at);
}

bool near(float a, float b, float eps = 0.06f) { return std::fabs(a - b) <= eps; }

void checkTree() {
    const p2flyer::Sphere* t = p2otakarapart::spheres();
    // disc otakara/enemycoll.txt: root {none}{____} r15 joint 11, child {body}{st__} r10 joint 11.
    CHECK(p2otakarapart::kSphereCount == 2);
    CHECK(std::strcmp(t[0].id, "none") == 0);
    CHECK(std::strcmp(t[0].code, "____") == 0);
    CHECK(near(t[0].radius, 15.0f));
    CHECK(t[0].parent == -1);
    CHECK(std::strcmp(t[1].id, "body") == 0);
    CHECK(std::strcmp(t[1].code, "st__") == 0);
    CHECK(near(t[1].radius, 10.0f));
    CHECK(t[1].parent == 0);
    // Exactly one stickable part and exactly one damageable part, and it is the same one.
    int sticky = 0, damage = 0;
    for (int i = 0; i < p2otakarapart::kSphereCount; ++i) {
        sticky += p2otakarapart::stickable(t[i].code) ? 1 : 0;
        damage += p2otakarapart::damageable(t[i].code) ? 1 : 0;
    }
    CHECK(sticky == 1);
    CHECK(damage == 1);
    CHECK(p2otakarapart::stickable(t[p2otakarapart::kBodySphere].code));
    CHECK(p2otakarapart::damageable(t[p2otakarapart::kBodySphere].code));
    CHECK(!p2otakarapart::stickable(t[0].code));
    // No sphere sits at leg height: the lowest stickable point is the body sphere's bottom,
    // ~27 above the feet in the standing pose, so a Pikmin at the feet cannot touch one.
    const float standing = p2otakarapart::bodyHeight("wait1", 0.3f);
    CHECK(standing > 35.0f && standing < 38.0f);
    CHECK(p2otakarapart::stickBottom(standing) > 24.0f);
    // The attack crouch (attack1 ~frame 40) is the lowest the body gets in the plain clips.
    float lowest = 1.0e9f;
    for (int i = 0; i <= 50; ++i) {
        const float y = p2otakarapart::bodyHeight("attack1", float(i) / 50.0f);
        if (y < lowest) lowest = y;
    }
    CHECK(lowest > 21.5f && lowest < 24.0f);
    // Carrying clips sit lower (the body crouches) but the tree is the same.
    CHECK(p2otakarapart::bodyHeight("wait2", 0.4f) < 12.0f);
    CHECK(p2otakarapart::bodyHeight("unknown", 0.5f) == 36.6f);
}

void checkVerdict() {
    // Source damageCallBack: `if (collpart) { damageTreasure(damage); return true; } return false;`
    const p2otakarapart::Verdict latched = underTest(true);
    const p2otakarapart::Verdict punch = underTest(false);
    CHECK(latched.accept);
    CHECK(!punch.accept); // the owner's "can't hurt it from the ground"
    CHECK(std::string(punch.reason) == "partless_refused");
    CHECK(p2otakarapart::formOf(true) == p2otakarapart::Form::LatchedAttack);
    CHECK(p2otakarapart::formOf(false) == p2otakarapart::Form::GroundPunch);
}

void checkWiring(const std::string& root) {
    const std::string inter = readFile(root + "/src/plugPikiNakata/tekiinteraction.cpp");
    const std::string bteki = readFile(root + "/src/plugPikiNakata/tekibteki.cpp");
    const std::string header = readFile(root + "/pc_port/pc_p2_otakara.h");
    const std::string glue = readFile(root + "/pc_port/pc_p2_otakara.cpp");
    CHECK(!inter.empty());
    CHECK(!bteki.empty());
    CHECK(!header.empty());
    CHECK(!glue.empty());

    CHECK(header.find("int pc_p2_otakara_attack_part(BTeki*") != std::string::npos);
    CHECK(header.find("bool pc_p2_otakara_divert(BTeki*") != std::string::npos);

    // InteractAttack::actTeki: the part gate runs inside the PIKI_PC_PORT block, before the host
    // interact, and a 0 verdict returns false (no damage, no flick count).
    const std::string att = functionBody(inter, "bool InteractAttack::actTeki(");
    CHECK(!att.empty());
    const size_t gate = att.find("pc_p2_otakara_attack_part(teki, mOwner, mCollPart, mDamage) == 0");
    const size_t host = att.find("teki->interact(TekiInteractionKey(TekiInteractType::Attack, this))");
    CHECK(gate != std::string::npos);
    CHECK(host != std::string::npos);
    CHECK(gate != std::string::npos && host != std::string::npos && gate < host);
    if (gate != std::string::npos) {
        const size_t ret = att.find("return false;", gate);
        CHECK(ret != std::string::npos && ret - gate < 120);
    }

    // BTeki::interactDefault: the treasure divert runs before mStoredDamage is raised.
    const std::string def = functionBody(bteki, "bool BTeki::interactDefault(");
    CHECK(!def.empty());
    const size_t divert = def.find("pc_p2_otakara_divert(this, attack->mOwner, attack->mDamage)");
    const size_t stored = def.find("mStoredDamage += attack->mDamage;");
    CHECK(divert != std::string::npos);
    CHECK(stored != std::string::npos);
    CHECK(divert != std::string::npos && stored != std::string::npos && divert < stored);

    // BombOtakara (93) keeps the partless path: BombOtakara::damageCallBack has no part test.
    const std::string gateFn = functionBody(glue, "int pc_p2_otakara_attack_part(");
    CHECK(!gateFn.empty());
    CHECK(gateFn.find("p2dweevil::BombId") != std::string::npos);
    CHECK(gateFn.find("return -1;") != std::string::npos);

    // A second registration of the same actor (dynamic bind, then setup pass) gives the host tree
    // back before the new own tree is bound; otherwise the first own tree would be taken for the
    // vehicle tree and the real one lost (pooled-actor crash).
    const std::string reg = functionBody(glue, "static bool registerActor(");
    CHECK(!reg.empty());
    const size_t detach = reg.find("old.coll.detach(actor)");
    const size_t reset = reg.find("s = Otakara();");
    CHECK(detach != std::string::npos);
    CHECK(reset != std::string::npos);
    CHECK(detach != std::string::npos && reset != std::string::npos && detach < reset);

    // The tree the glue binds is the retail two spheres plus the port's mouth anchor.
    CHECK(glue.find("p2otakarapart::spheres()") != std::string::npos);
    CHECK(glue.find("\"otak\"") != std::string::npos);
}

} // namespace

int main(int argc, char** argv) {
    checkTree();
    checkVerdict();
    checkWiring(argc > 1 ? std::string(argv[1]) : std::string(P2_OTAKARA_PART_SOURCE_ROOT));
    if (failures) {
        std::printf("FAIL p2_otakara_part_test failures=%d\n", failures);
        return 1;
    }
    std::printf("PASS p2_otakara_part_test\n");
    return 0;
}
