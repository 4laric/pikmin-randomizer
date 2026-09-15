"""#365 fixed-build diagnostics; does not mutate actors, routes or geometry."""
import json
import math
import re
from pathlib import Path
from experimental.pikmin2_beasts_floor3_donut_runtime import run as base_run,sha
from experimental.pikmin2_beasts_floor3_donut_runtime import diagnostic_fixture


def baseline_fixture(source,output):
    """Observe the legacy high-face penetration without modifying its dynamics."""
    diagnostic_fixture(source,output)
    raw=output.read_text().replace('#include "Stickers.h"','#include "Stickers.h"\n#include "DynParticle.h"')
    raw=raw.replace('if(ticks%120==0)','if(ticks%5==0)')
    marker='if(attached>maxAttached)maxAttached=attached;'
    if raw.count(marker)!=1:raise ValueError('Particle observer anchor changed')
    observer=Path(__file__).with_name('pikmin2_beasts_donut_particles.inc').read_text()
    output.write_text(raw.replace(marker,marker+observer))
    return output


def fixture(source,output):
    diagnostic_fixture(source,output)
    raw=output.read_text()
    checks=Path(__file__).with_name('pikmin2_beasts_donut_ground_checks.inc').read_text()
    anchor='if(state==0){'
    if raw.count(anchor)!=1:raise ValueError('Donut state anchor changed')
    output.write_text(raw.replace(anchor,anchor+checks))
    return output


def validate_queries(log):
    expected=[(1,20.5),(0,-98765),(1,20.5),(1,12.7536954),(0,-98765),(0,-98765),(1,0),(0,-98765)]
    rows=re.findall(r'^P2_DONUT_GROUND_CASE id=(\d+) found=(\d+) height=([^\n]+)$',log,re.M)
    if len(rows)!=8:raise ValueError('Missing bounded ground cases')
    for i,((identity,found,height),(ef,eh)) in enumerate(zip(rows,expected)):
        if int(identity)!=i or int(found)!=ef or not math.isfinite(float(height)) or abs(float(height)-eh)>.02:raise ValueError('Wrong bounded ground result')
    marker='P2_DONUT_GROUND_QUERY bounded=8 overhead_rejected=1 wall_blocked=1'
    if log.splitlines().count(marker)!=1:raise ValueError('Missing wall/ground completion')
    wall=re.findall(r'^P2_DONUT_WALL x=([^ ]+) y=([^ ]+) z=([^ ]+) front=([^\n]+)$',log,re.M)
    if len(wall)!=1:raise ValueError('Missing wall trace')
    x,y,z,front=map(float,wall[0]);computed=-.4227628*x-.00005376*(y+5)+.9062404*z+52.104539
    if not all(map(math.isfinite,(x,y,z,front))) or front<4.9 or abs(front-computed)>.01:raise ValueError('Wall trace failed')
    return dict(cases=8,wall_front=front)


def verify(directory):
    result=json.loads((directory/'acceptance.json').read_bytes())
    log=(directory/'native.log').read_bytes()
    if not result['passed'] or sha(log)!=result['log_sha256']:raise ValueError('Native haul evidence failed or changed')
    if any(sha((directory/name).read_bytes())!=h for name,h in result['input_sha256'].items()):raise ValueError('Stage input changed')
    result.update(issue=365,ground_queries=validate_queries(log.decode(errors='replace')))
    (directory/'ground-acceptance.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


def run(exe,directory,timeout=180):
    base_run(exe,directory,timeout=timeout)
    return verify(directory)
