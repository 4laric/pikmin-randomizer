#include "pc_p2_bombsarai_blast.h"

#include <cmath>

namespace {
bool finite(const P2BombSaraiVec3& value)
{
    return std::isfinite(value.x) && std::isfinite(value.y) && std::isfinite(value.z);
}

bool validBlast(const P2BombSaraiBlastEvent& blast)
{
    return finite(blast.center) && std::isfinite(blast.radius) && blast.radius > 0.0f
        && std::isfinite(blast.halfHeight) && blast.halfHeight >= 0.0f
        && std::isfinite(blast.tekiDamage) && blast.tekiDamage >= 0.0f
        && std::isfinite(blast.naviPikiDamage) && blast.naviPikiDamage >= 0.0f
        && std::isfinite(blast.knockbackNavi) && std::isfinite(blast.knockbackPiki);
}
}

int p2_bombsarai_route_blast(const P2BombSaraiBlastEvent& blast,
                             const P2BombSaraiReceiver* receivers, int receiverCount,
                             P2BombSaraiRoutedHit* out, int outCapacity)
{
    if (!validBlast(blast) || !receivers || receiverCount < 0 || !out || outCapacity < 0) {
        return -1;
    }
    const float maxY = blast.center.y + blast.halfHeight;
    const float minY = blast.center.y - blast.halfHeight;
    int hits = 0;
    for (int i = 0; i < receiverCount && hits < outCapacity; ++i) {
        const P2BombSaraiReceiver& receiver = receivers[i];
        if (!receiver.alive || !finite(receiver.position)) {
            continue;
        }
        // Height-gated spherical blast (bombState.cpp:142-158).
        const float dx = receiver.position.x - blast.center.x;
        const float dy = receiver.position.y - blast.center.y;
        const float dz = receiver.position.z - blast.center.z;
        const float distanceSquared = dx * dx + dy * dy + dz * dz;
        if (!std::isfinite(distanceSquared)
            || distanceSquared > blast.radius * blast.radius) {
            continue;
        }
        if (receiver.position.y > maxY || receiver.position.y < minY) {
            continue;
        }
        // Receiver callback immunity: an airborne dirigibug rejects the blast
        // (BombSarai.cpp:127-135 requires a floor triangle).
        if (receiver.airborneBombImmune && !receiver.grounded) {
            continue;
        }

        P2BombSaraiRoutedHit hit;
        hit.receiverId = receiver.id;
        hit.kind = receiver.kind;
        if (receiver.kind == P2BombSaraiReceiverKind::Teki) {
            // Friendly fire is unconditional: every Teki in the volume takes
            // fp01 via InteractBomb, attacker is the bomb (:159-165).
            hit.damage = blast.tekiDamage;
            hit.knockback = P2BombSaraiVec3{};
            hit.attributeToSelf = true;
            hit.attackerToken = 0;
        } else {
            hit.damage = blast.naviPikiDamage;
            const float weight = receiver.kind == P2BombSaraiReceiverKind::Piki
                ? blast.knockbackPiki : blast.knockbackNavi;
            // normalizeXZ of the separation; a zero-length XZ separation
            // keeps a zero horizontal knockback rather than inventing a
            // direction (source _normaliseXZ has the same degenerate case).
            const float horizontal = std::sqrt(dx * dx + dz * dz);
            if (horizontal > 0.0f && std::isfinite(horizontal)) {
                hit.knockback = { dx / horizontal * weight, weight, dz / horizontal * weight };
            } else {
                hit.knockback = { 0.0f, weight, 0.0f };
            }
            if (blast.hasCarrier && blast.carrierValid) {
                hit.attackerToken = blast.carrierToken;
                hit.attributeToSelf = false;
            } else {
                hit.attackerToken = 0;
                hit.attributeToSelf = true;
            }
        }
        out[hits++] = hit;
    }
    return hits;
}
