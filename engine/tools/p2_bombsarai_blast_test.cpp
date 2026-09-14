#include "pc_p2_bombsarai_blast.h"

#include <cassert>
#include <cmath>
#include <limits>

namespace {
bool near(float actual, float expected, float epsilon = 0.0001f)
{
    return std::fabs(actual - expected) <= epsilon;
}

P2BombSaraiBlastEvent blastAt(float y)
{
    P2BombSaraiBlastEvent blast;
    blast.center = { 0.0f, y, 0.0f };
    blast.radius = 75.0f;
    blast.halfHeight = 50.0f;
    blast.tekiDamage = 250.0f;
    blast.naviPikiDamage = 10.0f;
    blast.knockbackNavi = 100.0f;
    blast.knockbackPiki = 200.0f;
    blast.carrierToken = 42;
    blast.hasCarrier = true;
    blast.carrierValid = true;
    return blast;
}
}

int main()
{
    // Teki friendly fire: unconditional 250, no knockback, bomb-self attacker.
    {
        const P2BombSaraiBlastEvent blast = blastAt(0.0f);
        const P2BombSaraiReceiver receivers[] = {
            { 1, { 30.0f, 0.0f, 0.0f }, P2BombSaraiReceiverKind::Teki, true, false, true },
        };
        P2BombSaraiRoutedHit hits[4];
        const int count = p2_bombsarai_route_blast(blast, receivers, 1, hits, 4);
        assert(count == 1);
        assert(hits[0].receiverId == 1 && near(hits[0].damage, 250.0f));
        assert(near(hits[0].knockback.x, 0.0f) && near(hits[0].knockback.y, 0.0f));
        assert(hits[0].attributeToSelf);
    }

    // Navi/Pikmin: general attack damage, weighted separation knockback,
    // carrier-token attribution when the carrier is confirmed live.
    {
        const P2BombSaraiBlastEvent blast = blastAt(0.0f);
        const P2BombSaraiReceiver receivers[] = {
            { 2, { 50.0f, 0.0f, 0.0f }, P2BombSaraiReceiverKind::Navi, true, false, true },
            { 3, { 0.0f, 0.0f, -60.0f }, P2BombSaraiReceiverKind::Piki, true, false, true },
        };
        P2BombSaraiRoutedHit hits[4];
        const int count = p2_bombsarai_route_blast(blast, receivers, 2, hits, 4);
        assert(count == 2);
        assert(near(hits[0].damage, 10.0f) && !hits[0].attributeToSelf
               && hits[0].attackerToken == 42);
        assert(near(hits[0].knockback.x, 100.0f) && near(hits[0].knockback.y, 100.0f)
               && near(hits[0].knockback.z, 0.0f));
        assert(near(hits[1].damage, 10.0f) && !hits[1].attributeToSelf
               && hits[1].attackerToken == 42);
        assert(near(hits[1].knockback.z, -200.0f) && near(hits[1].knockback.y, 200.0f));
    }

    // Dead/unconfirmed carrier: Navi/Pikmin fall back to bomb-self
    // attribution; Teki routing is unaffected.
    {
        P2BombSaraiBlastEvent blast = blastAt(0.0f);
        blast.carrierValid = false; // stale-mCarrier fallback path
        const P2BombSaraiReceiver receivers[] = {
            { 4, { 10.0f, 0.0f, 0.0f }, P2BombSaraiReceiverKind::Piki, true, false, true },
            { 5, { 20.0f, 0.0f, 0.0f }, P2BombSaraiReceiverKind::Teki, true, false, true },
        };
        P2BombSaraiRoutedHit hits[4];
        const int count = p2_bombsarai_route_blast(blast, receivers, 2, hits, 4);
        assert(count == 2);
        assert(hits[0].attributeToSelf && hits[0].attackerToken == 0);
        assert(hits[1].attributeToSelf && near(hits[1].damage, 250.0f));
    }

    // Airborne dirigibug self-immunity: an airborne bomb-immune receiver is
    // skipped; the same receiver grounded takes the Teki hit
    // (BombSarai.cpp:127-135 requires a floor triangle).
    {
        const P2BombSaraiBlastEvent blast = blastAt(0.0f);
        const P2BombSaraiReceiver airborne[] = {
            { 6, { 10.0f, 0.0f, 0.0f }, P2BombSaraiReceiverKind::Teki, true, true, false },
        };
        P2BombSaraiRoutedHit hits[4];
        assert(p2_bombsarai_route_blast(blast, airborne, 1, hits, 4) == 0);
        const P2BombSaraiReceiver grounded[] = {
            { 6, { 10.0f, 0.0f, 0.0f }, P2BombSaraiReceiverKind::Teki, true, true, true },
        };
        assert(p2_bombsarai_route_blast(blast, grounded, 1, hits, 4) == 1);
        assert(near(hits[0].damage, 250.0f));
    }

    // Volume gates: exact sphere radius and +-50 vertical half height;
    // dead and non-finite receivers are skipped.
    {
        const P2BombSaraiBlastEvent blast = blastAt(100.0f);
        const P2BombSaraiReceiver receivers[] = {
            { 7, { 75.0f, 100.0f, 0.0f }, P2BombSaraiReceiverKind::Teki, true, false, true },   // on radius
            { 8, { 75.1f, 100.0f, 0.0f }, P2BombSaraiReceiverKind::Teki, true, false, true },  // outside
            { 9, { 0.0f, 150.0f, 0.0f }, P2BombSaraiReceiverKind::Teki, true, false, true },   // on gate
            { 10, { 0.0f, 150.1f, 0.0f }, P2BombSaraiReceiverKind::Teki, true, false, true },  // above gate
            { 11, { 0.0f, 49.9f, 0.0f }, P2BombSaraiReceiverKind::Teki, true, false, true },   // below gate
            { 12, { 10.0f, 100.0f, 0.0f }, P2BombSaraiReceiverKind::Teki, false, false, true },// dead
            { 13, { std::numeric_limits<float>::quiet_NaN(), 100.0f, 0.0f },
              P2BombSaraiReceiverKind::Teki, true, false, true },                              // NaN
        };
        P2BombSaraiRoutedHit hits[8];
        const int count = p2_bombsarai_route_blast(blast, receivers, 7, hits, 8);
        assert(count == 2);
        assert(hits[0].receiverId == 7 && hits[1].receiverId == 9);
    }

    // Output capacity truncates cleanly; invalid input returns -1.
    {
        const P2BombSaraiBlastEvent blast = blastAt(0.0f);
        const P2BombSaraiReceiver receivers[] = {
            { 14, { 10.0f, 0.0f, 0.0f }, P2BombSaraiReceiverKind::Teki, true, false, true },
            { 15, { 20.0f, 0.0f, 0.0f }, P2BombSaraiReceiverKind::Teki, true, false, true },
        };
        P2BombSaraiRoutedHit hits[2];
        assert(p2_bombsarai_route_blast(blast, receivers, 2, hits, 1) == 1);
        assert(p2_bombsarai_route_blast(blast, nullptr, 1, hits, 2) == -1);
        assert(p2_bombsarai_route_blast(blast, receivers, 2, nullptr, 2) == -1);
        P2BombSaraiBlastEvent bad = blast;
        bad.radius = 0.0f;
        assert(p2_bombsarai_route_blast(bad, receivers, 2, hits, 2) == -1);
    }

    // Degenerate XZ separation keeps a vertical-only knockback instead of
    // inventing a horizontal direction (source _normaliseXZ degenerate case).
    {
        const P2BombSaraiBlastEvent blast = blastAt(0.0f);
        const P2BombSaraiReceiver receivers[] = {
            { 16, { 0.0f, 10.0f, 0.0f }, P2BombSaraiReceiverKind::Piki, true, false, true },
        };
        P2BombSaraiRoutedHit hits[2];
        assert(p2_bombsarai_route_blast(blast, receivers, 1, hits, 2) == 1);
        assert(near(hits[0].knockback.x, 0.0f) && near(hits[0].knockback.z, 0.0f)
               && near(hits[0].knockback.y, 200.0f));
    }

    return 0;
}
