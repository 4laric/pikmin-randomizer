// #892 Gatling Groink armour-cover collision policy (pc_p2_groink_coll.h and the generated
// pc_p2_groink_coll_tables.h). Source: retail minihoudai/enemycoll.txt; CollPart::isStickable
// (collinfo.cpp:806-809); MiniHoudai::Obj::damageCallBack (MiniHoudai.cpp:162-171).
#include "pc_p2_groink_coll.h"
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <initializer_list>

namespace {
void check(bool ok, const char* what) {
    if (!ok) { std::fprintf(stderr, "FAIL %s\n", what); std::exit(1); }
}
bool near(float a, float b, float eps = 0.01f) { return std::fabs(a - b) <= eps; }
}

int main() {
    namespace C = p2groinkcoll;
    // The retail tree: eight nodes, exactly one stickable (body).
    check(C::kCollNodeCount == 8 && C::kCollClipCount == 8, "retail node/clip counts");
    const int body = C::nodeIndex("body");
    check(body == 1 && C::stickable(body), "body is stickable (st__)");
    int stickable = 0;
    for (int i = 0; i < C::kCollNodeCount; ++i) stickable += C::stickable(i) ? 1 : 0;
    check(stickable == 1, "body is the ONLY stickable part");

    // Front cover: cov1..cov3 refuse Pikmin; so do the feet, the coll sphere and the root.
    for (const char* id : {"cov1", "cov2", "cov3"}) {
        const int n = C::nodeIndex(id);
        check(n >= 0 && C::frontCover(n), "cover part exists and is front cover");
        check(!C::stickable(n) && C::contact(n) == C::Contact::Bounce, "cover part: Pikmin bounce off");
        check(C::pikminDamage(n, 10.0f) == 0.0f, "no Pikmin damage through the cover");
    }
    for (const char* id : {"none", "asiL", "asiR", "coll"}) {
        const int n = C::nodeIndex(id);
        check(n >= 0 && !C::frontCover(n) && C::contact(n) == C::Contact::Bounce && C::pikminDamage(n, 10.0f) == 0.0f,
              "touch-only part refuses Pikmin");
    }
    check(C::contact(body) == C::Contact::Latch && C::pikminDamage(body, 10.0f) == 10.0f, "body latches and takes full damage");
    check(C::nodeIndex("nope") == -1 && !C::stickable(-1) && !C::stickable(99), "unknown node is never stickable");

    // Pikmin damage needs a latch on a stickable part; unlatched ground hits are not a P2 hit.
    check(C::pikminHit(true, body) == C::PikminHit::Accept, "latched on body: accepted");
    check(C::pikminHit(false, body) == C::PikminHit::RefuseUnlatched, "unlatched: refused");
    check(C::pikminHit(false, -1) == C::PikminHit::RefuseUnlatched, "unlatched, no part: refused");
    check(C::pikminHit(true, C::nodeIndex("cov2")) == C::PikminHit::RefuseNonStickable, "stuck to cover: refused");
    check(C::pikminHit(true, -1) == C::PikminHit::RefuseNonStickable, "stuck to unknown part: refused");

    // Source damageCallBack: full with a part, a quarter without.
    check(C::damageScale(true) == 1.0f && C::damageScale(false) == 0.25f, "damageCallBack part/no-part scale");

    // The code rule is the leading 's' of CollPart::isStickable.
    check(C::codeStickable("st__") && !C::codeStickable("_t__") && !C::codeStickable("____") && !C::codeStickable(nullptr),
          "code stickable = leading s");

    // Geometry: retail radii, and the cover sits in front of (+z of) the body at every clip start.
    check(near(C::kCollNodes[0].radius, 55.0f) && near(C::kCollNodes[body].radius, 27.5f), "retail radii");
    for (int clip = 0; clip < C::kCollClipCount; ++clip) {
        float b[3], c1[3];
        check(C::centre(clip, 0.0f, body, b) && C::centre(clip, 0.0f, C::nodeIndex("cov1"), c1), "centre lookup");
        check(c1[2] > b[2], "cover is in front of the body");
    }
    // The cover is the frontmost part: its +z reach beats the body sphere by > 10 units in every clip at
    // frame 0, so a Pikmin coming at the face touches the cover before the body.
    for (int clip = 0; clip < C::kCollClipCount; ++clip) {
        float b[3], c[3];
        C::centre(clip, 0.0f, body, b);
        float coverReach = -1e9f;
        for (const char* id : {"cov1", "cov2", "cov3"}) {
            const int n = C::nodeIndex(id);
            C::centre(clip, 0.0f, n, c);
            coverReach = std::fmax(coverReach, c[2] + C::kCollNodes[n].radius);
        }
        check(coverReach > b[2] + C::kCollNodes[body].radius + 10.0f, "cover reaches further forward than the body");
    }
    // walk frame 0: body (0.254, 46.141, 3.055), cov1 (0.256, 41.141, 19.455) (kosi/head joint + offsets).
    float w[3];
    check(C::centre(C::clipIndex("walk"), 0.0f, body, w) && near(w[0], 0.254f) && near(w[1], 46.141f) && near(w[2], 3.055f),
          "walk frame 0 body centre");
    check(C::centre(C::clipIndex("walk"), 0.0f, C::nodeIndex("cov1"), w) && near(w[1], 41.141f) && near(w[2], 19.455f),
          "walk frame 0 cover centre");
    check(!C::centre(-1, 0.0f, 0, w) && !C::centre(0, 0.0f, 99, w), "out-of-range lookups fail");

    // Interpolation is continuous and clamps at the ends.
    float a[3], m[3], z[3];
    const int walk = C::clipIndex("walk");
    C::centre(walk, 0.0f, body, a);
    C::centre(walk, -5.0f, body, z);
    check(near(a[1], z[1]) && near(a[2], z[2]), "negative frame clamps to frame 0");
    C::centre(walk, 1000.0f, body, m);
    C::centre(walk, float(C::kCollClips[walk].frames - 1), body, a);
    check(near(a[1], m[1]) && near(a[2], m[2]), "past-the-end frame clamps to the last sample");

    // Heading maps model +z to world (sin h, cos h); +x to (cos h, -sin h).
    const float pos[3] = {100.0f, 5.0f, 200.0f}, fwd[3] = {0.0f, 0.0f, 10.0f}, side[3] = {10.0f, 0.0f, 0.0f};
    float o[3];
    C::toWorld(pos, 0.0f, fwd, o);
    check(near(o[0], 100.0f) && near(o[2], 210.0f), "heading 0 faces +z");
    C::toWorld(pos, 1.5707963f, fwd, o);
    check(near(o[0], 110.0f) && near(o[2], 200.0f), "heading pi/2 faces +x");
    C::toWorld(pos, 1.5707963f, side, o);
    check(near(o[0], 100.0f) && near(o[2], 190.0f), "heading pi/2 maps model +x to world -z");

    std::puts("p2_groink_coll_test PASS");
    return 0;
}
