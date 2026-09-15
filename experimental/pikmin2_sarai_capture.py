"""Sarai (P2 Swooping Snitchbug, enemy ID 23) Pikmin mouth-capture receiver.

Dependency-free parity mirror of native/pc_port/pc_p2_sarai_capture.h. Pure
functions only; the live stick-to-mouth binding stays in the native capture
bridge. Hosts supply per-candidate facts and consume admission, nearest-slot
selection and fall/flick drop decisions.
"""
import math

MOUTH_SLOTS = 2
MOUTH_RADIUS = 15.0
FLICK_KNOCKBACK = 10.0
FLICK_DAMAGE = 0.0
FALLMECK_DAMAGE = 10.0
NO_SLOT = -1


def capture_eligible(candidate):
    """True iff the candidate is a living Pikmin that is neither already
    mouth-stuck nor self-latched and stands within the mouth slot radius."""
    return (candidate.get('alive', True)
            and candidate.get('is_pikmin', True)
            and not candidate.get('stuck_to_mouth', False)
            and not candidate.get('sticker_is_self', False)
            and candidate.get('within_mouth_radius', True))


def select_mouth_captures(candidates, sqr_dist_xz):
    """Return up to MOUTH_SLOTS chosen indices, nearest-first by squared XZ
    distance, skipping non-eligible, non-finite and negative distances."""
    if candidates is None or sqr_dist_xz is None:
        return []
    count = len(candidates)
    if count > 64 or len(sqr_dist_xz) != count:
        return []
    eligible = []
    for index in range(count):
        if not capture_eligible(candidates[index]):
            continue
        distance = sqr_dist_xz[index]
        if not math.isfinite(distance) or distance < 0.0:
            continue
        eligible.append((distance, index))
    eligible.sort()
    return [index for _, index in eligible[:MOUTH_SLOTS]]


def fall_meck_release_velocity(fall_meck_speed=200.0):
    """Downward velocity applied to a released (FallMeck) captive."""
    if math.isfinite(fall_meck_speed) and fall_meck_speed >= 0.0:
        return -fall_meck_speed
    return -200.0


def fall_meck_damage(attack_damage=10.0):
    """Damage applied through the FallMeck release interaction."""
    if math.isfinite(attack_damage) and attack_damage >= 0.0:
        return attack_damage
    return FALLMECK_DAMAGE
