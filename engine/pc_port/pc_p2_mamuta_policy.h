#pragma once
// Source pose-bank selection by exact P1 Miurin motion. Values checked against
// PaniAnimator.h TekiMotion (Dead 0 .. Type5 14) and the P2 Miulin clip bank.
// Clip indices match the installed bank order.
namespace p2mamuta {
enum Clip { Wait=0, WaitAct=1, Move=2, Attack0=3, Attack1=4, Attack4=5, Flick=6, Dead=7, Type5=8 };
inline int anchor(int type, int motion, bool corpse) {
    if (type != 24) return -1;
    if (corpse || motion == 0) return Dead;          // Dead
    switch (motion) {
    case 2: case 3: return Wait;                     // Wait1/Wait2
    case 4: case 5: return WaitAct;                  // WaitAct1/WaitAct2
    case 6: case 7: return Move;                     // Move1/Move2
    case 8: return Attack1;                          // Attack posture/attack
    case 9: return Flick;                            // Flick (ground shake)
    case 10: case 11: case 12: return Attack1;       // Type1/Type2/Type3 bury strike
    case 13: return Attack4;                         // Type4 recovery
    case 14: return Type5;                           // Type5 pellet tremble
    default: return -1;
    }
}
}
