#include "pc_p2_purple_direct.h"
#include "pc_p2_kochappy.h"
#include "pc_p2_purple.h"
#include "TAI/Chappy.h"

static void purpleDirectFixture(Navi* n)
{
    static int state = 0, timer = 0;
    static Piki* source = nullptr;
    static BTeki* target = nullptr;
    static bool adult = false;
    static float startingHealth = 0.0f;
    static Vector3f targetPosition;
    ++timer;

    auto parkSource = [&]() {
        if (source->isStickTo()) source->endStickObject();
        source->changeMode(PikiMode::FreeMode, n);
        source->resetPosition(Vector3f(-220.0f, mapMgr->getMinY(-220.0f, -180.0f, true), -180.0f));
    };
    auto throwAtTarget = [&]() {
        parkSource();
        const Vector3f position = targetPosition;
        n->resetPosition(Vector3f(position.x - 70.0f, mapMgr->getMinY(position.x - 70.0f, position.z, true), position.z));
        source->mFSM->transit(source, PIKISTATE_Flying);
        // Native throw targeting lands about 36 world units short in this arena.
        // Aim beyond the receiver so the descending arc crosses its collision body.
        n->throwPiki(source, Vector3f(position.x + 42.0f, position.y, position.z));
        // Keep the actual throw/arming path, then stage its descending flight over
        // the fixed receiver so autonomous target motion cannot make the proof flaky.
        const float stagedHeight = adult ? 80.0f : 24.0f;
        source->resetPosition(Vector3f(position.x, position.y + stagedHeight, position.z));
        source->mVelocity = Vector3f(0.0f, -100.0f, 0.0f);
        source->mTargetVelocity = source->mVelocity;
        timer = 0;
    };

    if (state == 0 && timer >= 90) {
        Iterator pikis(pikiMgr);
        CI_LOOP(pikis) {
            Piki* piki = static_cast<Piki*>(*pikis);
            if (!source && piki->isAlive()) source = piki;
        }
        Iterator enemies(tekiMgr);
        CI_LOOP(enemies) {
            BTeki* teki = static_cast<BTeki*>(*enemies);
            if (pc_p2_purple_direct_adult_registered(teki)) {
                require(!target, "multiple direct adult receivers");
                target = teki;
                adult = true;
            }
        }
        if (!target) {
            Iterator dwarfs(tekiMgr);
            CI_LOOP(dwarfs) {
                BTeki* teki = static_cast<BTeki*>(*dwarfs);
                if (pc_p2_kochappy_registered(teki)) {
                    require(!target, "multiple direct dwarf receivers");
                    target = teki;
                }
            }
        }
        require(source && target, "direct fixture actors missing");
        targetPosition = target->mSRT.t;
        Iterator parked(pikiMgr);
        CI_LOOP(parked) {
            Piki* piki = static_cast<Piki*>(*parked);
            if (piki != source) piki->resetPosition(Vector3f(-220.0f, mapMgr->getMinY(-220.0f, -180.0f, true), -180.0f));
        }
        startingHealth = target->mHealth;
        const int startingState = target->mStateID;
        const float startingStoredDamage = target->mStoredDamage;

        source->mVelocity.y = -1.0f;
        require(!pc_p2_purple_direct_begin(source, target, nullptr).handled,
            "non-Purple helper check reached direct receiver");
        pc_p2_make_purple(source);
        source->mVelocity.y = 1.0f;
        require(!pc_p2_purple_direct_begin(source, target, nullptr).handled,
            "ascending helper check reached direct receiver");
        source->mVelocity.y = -1.0f;
        require(!pc_p2_purple_direct_begin(source, n, nullptr).handled,
            "non-enemy helper check reached direct receiver");
        require(target->mHealth == startingHealth && target->mStateID == startingState
                && target->mStoredDamage == startingStoredDamage,
            "negative helper checks changed receiver");
        std::puts("P2_PURPLE_DIRECT_NEGATIVE_PASS non_purple ascending non_enemy");
        throwAtTarget();
        state = 1;
        std::printf("P2_PURPLE_DIRECT_FIXTURE_READY family=%s health=%.1f\n", adult ? "adult_bulborb" : "red_dwarf", startingHealth);
    } else if (state == 1) {
        target->mVelocity = Vector3f(0.0f, 0.0f, 0.0f);
        target->mTargetVelocity = Vector3f(0.0f, 0.0f, 0.0f);
        target->resetPosition(targetPosition);
        if (adult && target->mStoredDamage >= 49.9f) {
            const float queuedDamage = target->mStoredDamage;
            source->mVelocity.y = -1.0f;
            require(!pc_p2_purple_direct_begin(source, target, nullptr).handled
                    && target->mStoredDamage == queuedDamage,
                "consumed throw token replayed direct damage");
            std::puts("P2_PURPLE_DIRECT_REPLAY_PASS consumed_token");
            parkSource();
            state = 2;
            timer = 0;
        } else if (!adult && target->mStateID == CHAPPYSTATE_Unk2) {
            parkSource();
            state = 4;
            timer = 0;
            std::puts("P2_PURPLE_DIRECT_CRUSH_PASS state=2");
        }
        require(timer < 240, "direct callback did not reach receiver");
    } else if (state == 2 && target->mHealth < startingHealth) {
        require(target->isAlive() && target->mHealth <= startingHealth - 49.9f
                && target->mHealth >= startingHealth - 50.1f,
            "adult direct hit health delta was not exactly one fp36 damage");
        std::printf("P2_PURPLE_DIRECT_DAMAGE_PASS before=%.1f after=%.1f\n", startingHealth, target->mHealth);
        target->mHealth = 40.0f;
        throwAtTarget();
        state = 3;
    } else if (state == 2) {
        require(timer < 60, "adult queued fp36 damage was not consumed by native update");
    } else if (state == 3) {
        target->mVelocity = Vector3f(0.0f, 0.0f, 0.0f);
        target->mTargetVelocity = Vector3f(0.0f, 0.0f, 0.0f);
        target->resetPosition(targetPosition);
        if (target->mDeadState || !target->isAlive()) {
            state = 4;
            timer = 0;
            std::puts("P2_PURPLE_DIRECT_LETHAL_PASS adult normal death entered");
        }
        require(timer < 300, "lethal direct hit did not enter native death");
    } else if (state == 4) {
        int matchingCorpses = 0;
        Iterator pellets(pelletMgr);
        CI_LOOP(pellets) {
            Pellet* corpse = static_cast<Pellet*>(*pellets);
            if (corpse->isAlive() && corpse->mPelletView == static_cast<PelletView*>(target)) {
                ++matchingCorpses;
            }
        }
        require(matchingCorpses <= 1, "direct receiver produced duplicate corpses");
        if (matchingCorpses == 1) {
            state = 5;
            timer = 0;
        }
        require(timer < 600, "direct receiver corpse did not appear");
    } else if (state == 5 && timer >= 30) {
        int matchingCorpses = 0;
        Iterator pellets(pelletMgr);
        CI_LOOP(pellets) {
            Pellet* corpse = static_cast<Pellet*>(*pellets);
            if (corpse->isAlive() && corpse->mPelletView == static_cast<PelletView*>(target)) ++matchingCorpses;
        }
        require(matchingCorpses == 1, "direct receiver corpse count was not stable at one");
        std::printf("PASS p2 Purple direct: %s direct hit used one token, native receiver ordering, and exactly one stable corpse\n",
            adult ? "adult fp36 damage and lethal retry" : "dwarf crush");
        std::fflush(stdout);
        std::_Exit(0);
    }
}
