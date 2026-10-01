// Engine-free unit test for the dev console grammar (#942).
#include "pc_dev_console_parser.h"
#include <cassert>
#include <cstdio>
#include <cstring>

using namespace devconsole;

int main()
{
    // Dev target uid scheme round-trips and never collides with source 0.
    assert(devTargetUid(41) == 0xDE000029u);
    assert(isDevTargetUid(devTargetUid(41)));
    assert(devTargetSource(devTargetUid(78)) == 78u);
    assert(!isDevTargetUid(0u));
    assert(!isDevTargetUid(1254096625u)); // a real FoH slot uid
    assert(devTargetSource(1254096625u) == 0u);

    // Species resolution: id, enum name, common name (spaces as '_'), case-insensitive.
    assert(findSpecies("41") && findSpecies("41")->source == 41u);
    assert(findSpecies("fuefuki") && findSpecies("fuefuki")->source == 41u);
    assert(findSpecies("Antenna_Beetle") && findSpecies("Antenna_Beetle")->source == 41u);
    assert(findSpecies("gatling_groink") && findSpecies("gatling_groink")->source == 78u);
    assert(findSpecies("99") == nullptr);   // Waterwraith is not in the playable pool
    assert(findSpecies("bogus") == nullptr);
    assert(findSpecies("") == nullptr);

    // Host vehicles agree with the placement policy the seed path uses.
    assert(hostTypeFor(41) == 3);   // TEKI_Chappy
    assert(hostTypeFor(38) == 8);   // TEKI_Collec
    assert(hostTypeFor(78) == 0);   // TEKI_Frog
    assert(hostTypeFor(32) == 3);
    assert(hostTypeFor(73) == 4);   // TEKI_Swallow
    for (const Species& s : kSpecies) assert(hostTypeFor(s.source) >= 0);

    // spawn grammar.
    {
        Command c = parse("spawn 41");
        assert(c.kind == Cmd::Spawn && c.species && c.species->source == 41u && c.count == 1 && c.rebind);
        assert(!c.error[0]);
    }
    {
        Command c = parse("  spawn   MiniHoudai 3 norebind ");
        assert(c.kind == Cmd::Spawn && c.species && c.species->source == 78u && c.count == 3 && !c.rebind);
    }
    {
        Command c = parse("spawn swallow 2");
        assert(c.kind == Cmd::Spawn && c.species == nullptr && !std::strcmp(c.token, "swallow") && c.count == 2);
        assert(!c.error[0]); // a P1 teki name resolves at runtime
    }
    assert(parse("spawn").error[0]);
    assert(parse("spawn 41 0").error[0]);
    assert(parse("spawn 41 17").error[0]);
    assert(parse("spawn 41 x").error[0]);

    // kill / killall / pikmin / day / time / tp / pos / list / help / rebind.
    assert(parse("kill").kind == Cmd::Kill);
    assert(parse("kill all").kind == Cmd::KillAll);
    assert(parse("killall").kind == Cmd::KillAll);
    {
        Command c = parse("pikmin yellow 7");
        assert(c.kind == Cmd::Pikmin && c.colour == kColourYellow && c.count == 7 && !c.error[0]);
        assert(parse("pikmin red").count == 5);
        assert(parse("pikmin blue").colour == kColourBlue);
        assert(parse("pikmin green 3").error[0]);
        assert(parse("pikmin red 0").error[0]);
    }
    assert(parse("day 4").kind == Cmd::Day && parse("day 4").day == 4);
    assert(parse("day 0").error[0]);
    assert(parse("day").error[0]);
    {
        Command c = parse("time 0.5");
        assert(c.kind == Cmd::Time && c.time == 12.0f);
        assert(parse("time 15").time == 15.0f);
        assert(parse("time 1").time == 24.0f); // 1 is a full-day fraction
        assert(parse("time 25").error[0]);
        assert(parse("time").error[0]);
    }
    {
        Command c = parse("tp -100.5 250");
        assert(c.kind == Cmd::Tp && c.x == -100.5f && c.z == 250.0f && !c.arena && !c.error[0]);
        Command a = parse("tp hope_snagret_pit");
        assert(a.kind == Cmd::Tp && a.arena && a.arena->stage == 1 && a.x == -867.4f && a.z == 3901.8f);
        assert(parse("tp nowhere").error[0]);
        assert(parse("tp 1").error[0]);
    }
    assert(parse("pos").kind == Cmd::Pos);
    assert(parse("list").kind == Cmd::List);
    assert(parse("help").kind == Cmd::Help);
    assert(parse("rebind").kind == Cmd::Rebind);
    assert(parse("").kind == Cmd::None);
    assert(parse("   \n").kind == Cmd::None);
    assert(parse("# comment").kind == Cmd::None);
    assert(parse(nullptr).kind == Cmd::None);
    {
        Command c = parse("frobnicate 1 2");
        assert(c.kind == Cmd::Unknown && c.error[0]);
    }
    assert(findArena("IMPACT_GOOLIX") && findArena("impact_goolix")->stage == 0);
    assert(kSpeciesCount == 41);
    assert(kArenaCount == 7);
    assert(helpText() && std::strstr(helpText(), "spawn"));
    std::printf("pc_dev_console_parser_test OK\n");
    return 0;
}
