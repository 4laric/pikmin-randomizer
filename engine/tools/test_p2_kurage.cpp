#include "../pc_port/pc_p2_kurage.h"

#include <cassert>

int main()
{
    P2KurageCapturePolicy lesser(P2KurageVariant::Lesser, 1.0f);
    assert(lesser.captureCaptain(4, true) == P2KurageEvent::None);
    assert(lesser.capturePikmin(1, true) == P2KurageEvent::Captured);
    assert(lesser.interrupt(1) == P2KurageEvent::Released);
    assert(lesser.update(2.0f, true, false) == P2KurageEvent::None);

    P2KurageCapturePolicy greater(P2KurageVariant::Greater, 1.0f);
    assert(greater.captureCaptain(7, true) == P2KurageEvent::Captured);
    assert(greater.capturePikmin(2, true) == P2KurageEvent::Captured);
    assert(greater.update(0.5f, true, false) == P2KurageEvent::None);
    assert(greater.update(0.6f, true, false) == P2KurageEvent::Killed);
    assert(greater.interrupt(7) == P2KurageEvent::Released);
    assert(greater.captureCaptain(8, true) == P2KurageEvent::Captured);
    assert(greater.onDeath() == P2KurageEvent::Released);
    assert(greater.slots()[0].kind == P2KurageCaptureKind::Empty);
    for (const P2KurageSlot& slot : greater.slots()) assert(slot.kind == P2KurageCaptureKind::Empty);
    return 0;
}
