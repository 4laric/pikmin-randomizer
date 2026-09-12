#include "pc_whistle.h"
#include <cassert>
int main() {
 PcWhistleTapState a, b;
 assert(!a.press(0)); assert(a.press(.35));
 assert(!a.press(1)); assert(a.press(1.2));
 assert(!b.press(1.25)); assert(!a.press(2));
 assert(!a.press(2)); assert(!a.press(1));
 assert(!pc_whistle_recall_workers(.59f,true));
 assert(pc_whistle_recall_workers(.6f,true));
 assert(!pc_whistle_recall_workers(.6f,false));
}
