// Engine-free test for the shared P2 life-gauge policy and the console `hurt` grammar.
#include "pc_p2_life_gauge.h"
#include "pc_dev_console_parser.h"
#include <cassert>
#include <cstdio>

int main()
{
    // Every playable species the dev console knows has a retail fp27 row.
    for (const devconsole::Species& s : devconsole::kSpecies) assert(p2lifegauge::hasHeight(s.source));
    assert(p2lifegauge::hasHeight(26) && p2lifegauge::hasHeight(27) && p2lifegauge::hasHeight(84) && p2lifegauge::hasHeight(93));
    // Spot checks against retail enemyparm.txt fp27 (US GPVE01).
    assert(p2lifegauge::lifeMeterHeight(32, -1.0f) == 50.0f);  // Demon
    assert(p2lifegauge::lifeMeterHeight(2, -1.0f) == 90.0f);   // Chappy
    assert(p2lifegauge::lifeMeterHeight(33, -1.0f) == 110.0f); // FireChappy
    assert(p2lifegauge::lifeMeterHeight(63, -1.0f) == 20.0f);  // Jigumo
    assert(p2lifegauge::lifeMeterHeight(31, -1.0f) == 50.0f);  // Baby (Bulborb Larva)
    assert(p2lifegauge::lifeMeterHeight(9999, 7.0f) == 7.0f);  // unknown -> fallback
    // Gauge shows only for a live, damaged enemy.
    assert(p2lifegauge::shouldShow(900.0f, 1500.0f, false));
    assert(!p2lifegauge::shouldShow(1500.0f, 1500.0f, false));
    assert(!p2lifegauge::shouldShow(0.0f, 1500.0f, false));
    assert(!p2lifegauge::shouldShow(900.0f, 1500.0f, true));
    assert(p2lifegauge::gaugeFollowsTargetable(12) && p2lifegauge::gaugeFollowsTargetable(14) && !p2lifegauge::gaugeFollowsTargetable(32));
    // Console: hurt [fraction].
    {
        devconsole::Command c = devconsole::parse("hurt");
        assert(c.kind == devconsole::Cmd::Hurt && !c.error[0] && c.time > 0.39f && c.time < 0.41f);
        c = devconsole::parse("hurt 0.75");
        assert(c.kind == devconsole::Cmd::Hurt && !c.error[0] && c.time == 0.75f);
        c = devconsole::parse("hurt 0.5 stored");
        assert(c.kind == devconsole::Cmd::Hurt && !c.error[0] && c.stored && c.time == 0.5f);
        c = devconsole::parse("hurt 2");
        assert(c.kind == devconsole::Cmd::Hurt && c.error[0]);
    }
    std::puts("pc_p2_life_gauge_test OK");
    return 0;
}
