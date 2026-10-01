// Engine-linked, headless regression. Source ids are supplied from the admitted
// root pool. Injected health/death state tests the shared host contract; this is
// not natural-combat, rendered-animation or campaign acceptance.
#include "teki.h"
#include "Piki.h"
#include "Interactions.h"
#include "pc_randomizer.h"
#include <cstdio>
#include <cstdlib>

static void initializeLinks(Creature& creature) {
    // Scene Creature::init normally initializes these intrusive attachment fields.
    creature.mStickTarget = nullptr;
    creature.mStickPart = nullptr;
    creature.mStickListHead = nullptr;
    creature.mPrevSticker = nullptr;
    creature.mNextSticker = nullptr;
    creature.mPelletStickSlot = -1;
}
class FixturePiki : public Piki {
public:
    FixturePiki() : Piki(nullptr) { initializeLinks(*this); }
    void refresh(Graphics&) override {}
    bool isKinoko() override { return false; }
    // This headless contract fixture has no scene state machine running.
    // Attachment links use production code; scene messages are outside scope.
    void stickToCallback(Creature*) override {}
};
class FixtureAttachment : public Creature {
public:
    FixtureAttachment() : Creature(nullptr) { initializeLinks(*this); }
    void refresh(Graphics&) override {}
    void doKill() override {}
};

static void require(bool ok, const char* reason, unsigned source) {
    if (!ok) { std::printf("P2_DEATH_COMBAT_FAIL source=%u reason=%s\n", source, reason); std::exit(1); }
}

int main(int argc, char** argv) {
    setvbuf(stdout, nullptr, _IONBF, 0);
    require(argc > 1, "supply admitted source ids", 0);
    for (int i = 1; i < argc; ++i) {
        const unsigned source = static_cast<unsigned>(std::strtoul(argv[i], nullptr, 10));
        Teki actor;
        initializeLinks(actor);
        actor.clearTekiOptions();
        actor.setTekiOption(BTeki::TEKI_OPTION_ALIVE);
        actor.mHealth = 10.0f;
        actor.mDeadState = 0;
        actor.mStoredDamage = 0.0f;
        actor.mTekiType = TEKI_Chappy;
        pc_randomizer_p2_bind_source(static_cast<PelletView*>(&actor), source, source);
        require(pc_randomizer_p2_source_for(static_cast<PelletView*>(&actor)) == source, "binding", source);
        require(actor.isAlive() && actor.isHostAlive(), "living actor", source);

        FixturePiki first, second, late;
        FixtureAttachment attachment;
        attachment.mObjType = OBJTYPE_Pellet;
        require(first.startStick(&actor, nullptr), "first latch", source);
        require(attachment.startStick(&actor, nullptr), "non Pikmin attachment", source);
        second.startStickMouth(&actor, nullptr);
        require(second.getStickObject() == &actor && second.isStickToMouth(), "mouth attachment", source);

        actor.mHealth = 0.0f;
        require(!actor.isAlive() && actor.isHostAlive(), "combat ends while animation host lives", source);
        require(!late.startStick(&actor, nullptr), "reject late latch", source);
        late.startStickMouth(&actor, nullptr);
        require(!late.getStickObject() && !late.isStickToMouth(), "reject late mouth capture without fatal error", source);
        InteractAttack hit(&late, nullptr, 5.0f, false);
        require(!hit.actTeki(&actor), "reject attack wrapper", source);
        require(!actor.interact(TekiInteractionKey(TekiInteractType::Attack, &hit)), "reject direct attack", source);
        require(actor.mHealth == 0.0f && actor.mStoredDamage == 0.0f, "no post death damage", source);
        actor.releaseP2DeathStickers();
        require(!first.getStickObject() && !second.getStickObject(), "release both Pikmin", source);
        require(!second.isStickToMouth(), "clear mouth attachment flag", source);
        require(attachment.getStickObject() == &actor && actor.mStickListHead == &attachment, "preserve non Pikmin attachment", source);
        actor.releaseP2DeathStickers();
        require(actor.mStickListHead == &attachment, "idempotent release", source);
        attachment.endStickObject();

        actor.mHealth = 10.0f;
        actor.mDeadState = 1;
        require(!actor.isAlive() && !late.startStick(&actor, nullptr), "explicit death state with positive health", source);
        actor.mDeadState = 0;
        require(actor.isAlive() && late.startStick(&actor, nullptr), "revival or slot reuse", source);
        late.endStickObject();
        pc_randomizer_p2_forget_source(static_cast<PelletView*>(&actor));
        actor.mHealth = 0.0f;
        require(actor.isAlive() && !actor.isP2Dying(), "unbound P1 semantics", source);
        std::printf("P2_DEATH_COMBAT_SOURCE_PASS source=%u injected_health=1 host_lifetime=1 late_latch_rejected=1 attack_rejected=1 stickers_released=2 P1_unchanged=1\n", source);
    }
    std::printf("P2_DEATH_COMBAT_PASS sources=%d\n", argc - 1);
    return 0;
}
