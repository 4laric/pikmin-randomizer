"""One queued Start diagnostic; private MoviePlayer observation only."""
from experimental.pikmin2_tank_heap_diagnostic import once

def movie_probe(source):
    source='extern void tank_diag_pump_start();\n'+source
    old='if (pc_bbft_take_skip() && mIsActive) requestSkip();'
    new='''tank_diag_pump_start();
    if (pc_bbft_take_skip() && mIsActive) {
        fprintf(stderr, "TANK_START_CONSUMED allowed=%d\\n", !gameflow.mGameInterface || gameflow.mGameInterface->movieSkipAllowed());
        requestSkip();
    }'''
    return once(source,old,new)

def analyze_start(text,requested):
    scheduled=text.count('TANK_START_SCHEDULE ');delivered=text.count('TANK_START_EDGE delivered=1');consumed=text.count('TANK_START_CONSUMED ')
    if requested and (scheduled,delivered,consumed)!=(1,1,1):raise ValueError('Expected exactly one scheduled/delivered/consumed Start')
    if not requested and (scheduled or delivered or consumed):raise ValueError('Unexpected control input')
    return dict(scheduled=scheduled,delivered=delivered,consumed=consumed,allowed='TANK_START_CONSUMED allowed=1' in text,denied='TANK_START_CONSUMED allowed=0' in text,desync_lines=text.count('[PC GX] DESYNC #'))
