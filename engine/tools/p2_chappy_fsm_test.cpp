// Isolated fixtures for pc_p2_chappy_fsm.h (Chappy family, inst-chappy #871).
// Build: g++ -std=gnu++17 -Wall -Wextra -Werror -Ipc_port tools/p2_chappy_fsm_test.cpp -o p2_chappy_fsm_test.exe
#include <cstdio>
#include <cstdlib>
#include "pc_p2_chappy_fsm.h"

using namespace p2chappyfsm;

static int gChecks = 0;
static void require(bool ok, const char* what)
{
    ++gChecks;
    if (!ok) {
        std::printf("FAIL p2_chappy_fsm_test: %s\n", what);
        std::fflush(stdout);
        std::_Exit(1);
    }
}

int main()
{
    require(familyForSource(2) == FAMILY_ADULT, "Chappy is adult");
    require(familyForSource(33) == FAMILY_ADULT, "FireChappy is adult");
    require(familyForSource(43) == FAMILY_ADULT, "YellowChappy is adult");
    require(familyForSource(35) == FAMILY_KUMA, "KumaChappy is kuma");
    require(familyForSource(67) == FAMILY_KUMA, "LeafChappy is kuma");
    require(familyForSource(76) == FAMILY_KUMAKO, "KumaKochappy is kumako");
    require(familyForSource(53) == FAMILY_KING, "KingChappy is king");

    // --- adult: sleep -> turn -> walk -> attack -> walk; flick; home; dead ---
    {
        In in;
        in.state = p2chappy::ADULT_SLEEP;
        Out still = tick(2, in);
        require(still.next == p2chappy::ADULT_SLEEP && !still.changed, "sleep holds without stimulus");
        in.seesTarget = true;
        Out wake = tick(2, in);
        require(wake.next == p2chappy::ADULT_TURN && wake.changed, "sight wakes to turn");
        in.state = p2chappy::ADULT_TURN;
        in.seesTarget = false;
        require(tick(2, in).next == p2chappy::ADULT_WALK, "turn advances to walk");
        in.state = p2chappy::ADULT_WALK;
        in.inRange = true;
        require(tick(2, in).next == p2chappy::ADULT_ATTACK, "range starts attack");
        in.state = p2chappy::ADULT_ATTACK;
        in.inRange = false;
        in.attackDone = true;
        require(tick(2, in).next == p2chappy::ADULT_WALK, "attack completion returns to walk");
        in.state = p2chappy::ADULT_WALK;
        in.attackDone = false;
        in.flick = true;
        require(tick(2, in).next == p2chappy::ADULT_FLICK, "shake-off flicks");
        in.state = p2chappy::ADULT_WALK;
        in.flick = false;
        in.farFromHome = true;
        require(tick(2, in).next == p2chappy::ADULT_TURN_TO_HOME, "far from home turns home");
        in.state = p2chappy::ADULT_TURN_TO_HOME;
        require(tick(2, in).next == p2chappy::ADULT_GO_HOME, "turn-to-home goes home");
        in.state = p2chappy::ADULT_GO_HOME;
        require(tick(2, in).next == p2chappy::ADULT_GO_HOME, "go-home continues while far");
        in.farFromHome = false;
        require(tick(2, in).next == p2chappy::ADULT_SLEEP, "home arrival sleeps");
        in.state = p2chappy::ADULT_WALK;
        in.hp = 0.0f;
        require(tick(2, in).next == p2chappy::ADULT_DEAD, "zero health dies");
    }

    // --- kuma: patrol, lost, rebirth ---
    {
        In in;
        in.state = 6; // TurnPath
        require(tick(35, in).next == 8, "turn-path walks the path");
        in.state = 8; // WalkPath
        in.seesTarget = true;
        require(tick(35, in).next == 7, "sight leaves the path to walk");
        in.state = 8;
        in.seesTarget = false;
        in.lostTarget = true;
        require(tick(35, in).next == 2, "lost target goes lost");
        in.state = 2; // Lost
        in.lostTarget = false;
        in.reviveReady = true;
        require(tick(35, in).next == 1, "revive timer goes rebirth");
        in.state = 1; // Rebirth
        in.reviveReady = false;
        in.attackDone = true;
        require(tick(35, in).next == 6, "rebirth resumes patrol");
        in.state = 7;
        in.hp = 0.0f;
        require(tick(35, in).next == 0, "kuma death is state 0");
        // Runtime-driven details: flick preempts walk, attack completion
        // returns to walk, lost reacquires on sight.
        in.hp = 1200.0f;
        in.state = 7; // Walk
        in.flick = true;
        in.attackDone = false;
        require(tick(35, in).next == 4, "walk flicks on shake-off");
        in.state = 3; // Attack
        in.flick = false;
        in.attackDone = true;
        require(tick(35, in).next == 7, "attack completion walks");
        in.state = 2; // Lost
        in.attackDone = false;
        in.seesTarget = true;
        in.reviveReady = false;
        require(tick(35, in).next == 7, "lost reacquires on sight");
        in.state = 5; // Turn
        in.seesTarget = false;
        require(tick(35, in).next == 7, "turn advances to walk");
    }

    // --- kumako: wait, follow, attack ---
    {
        In in;
        in.state = 2; // Wait
        require(tick(76, in).next == 2, "wait holds without parent or sight");
        in.parentNear = true;
        require(tick(76, in).next == 6, "parent proximity walks the path");
        in.state = 6; // WalkPath
        in.inRange = true;
        require(tick(76, in).next == 3, "range attacks");
        in.state = 6;
        in.inRange = false;
        in.parentNear = false;
        require(tick(76, in).next == 2, "parent loss returns to wait");
        in.hp = 0.0f;
        require(tick(76, in).next == 0, "kumako death is state 0");
        // Press (state 1) is entered via the pc_p2_chappy_press trigger, not
        // the table: the table must hold it so the runtime can graduate it
        // to Dead after the press clip.
        in.hp = 500.0f;
        in.state = 1; // Press
        require(tick(76, in).next == 1, "press holds for the runtime");
        in.state = 5; // Walk
        in.inRange = true;
        require(tick(76, in).next == 3, "walk range attacks");
        in.state = 4; // Flick
        in.inRange = false;
        in.flick = false;
        in.attackDone = true;
        require(tick(76, in).next == 5, "flick completion walks");
    }

    // --- king: walk, warcry, burrow, bombs, dead ---
    {
        In in;
        in.state = 0; // Walk
        in.seesTarget = true;
        require(tick(53, in).next == 4, "sight roars warcry");
        in.state = 4; // WarCry
        in.seesTarget = false;
        in.attackDone = true;
        require(tick(53, in).next == 0, "warcry completion walks");
        in.state = 0;
        in.attackDone = false;
        in.inRange = true;
        require(tick(53, in).next == 1, "range attacks");
        in.state = 0;
        in.inRange = false;
        in.burrowed = true;
        require(tick(53, in).next == 8, "burrow flag hides");
        in.state = 9; // HideWait
        in.burrowed = false;
        require(tick(53, in).next == 10, "surface order appears");
        in.state = 0;
        in.bombStun = true;
        require(tick(53, in).next == 5, "bomb stun damages");
        in.bombStun = false;
        in.hp = 0.0f;
        require(tick(53, in).next == 2, "king death is state 2");
        // Burrow/appear/caution chain and the bomb-eat path the runtime
        // drives on timers (Eat->Swallow, Hide->HideWait->Appear->Caution).
        in.hp = 1300.0f;
        in.state = 8; // Hide
        require(tick(53, in).next == 9, "hide enters hidewait");
        in.state = 10; // Appear
        in.attackDone = true;
        require(tick(53, in).next == 11, "appear enters caution");
        in.state = 11; // Caution
        require(tick(53, in).next == 0, "caution completion walks");
        in.state = 7; // Eat
        in.attackDone = false;
        require(tick(53, in).next == 12, "eat enters swallow");
        in.state = 12; // Swallow
        in.attackDone = true;
        require(tick(53, in).next == 0, "swallow completion walks");
        in.state = 3; // Flick
        in.attackDone = true;
        in.flick = false;
        require(tick(53, in).next == 3, "flick holds without completion");
    }

    std::printf("PASS p2_chappy_fsm_test checks=%d\n", gChecks);
    return 0;
}
