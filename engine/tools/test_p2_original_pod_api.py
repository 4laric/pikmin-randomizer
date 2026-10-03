"""Compile the real consumer API and prove consumers cannot issue suction authority.

No engine mocks, synthetic receipt grant, runtime or gameplay claim. Writes only
to the supplied private output directory.
"""
import argparse
import subprocess
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--compiler', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    source = Path(__file__).resolve().parents[1]
    args.output.mkdir(parents=True, exist_ok=True)
    cases = {
        'consumer': (True, '''#include "pc_p2_original_pod.h"
static_assert(p2originalpod::sourceType==3 && p2originalpod::sourceObject==1);
bool observe(Pellet* p,Suckable* r,const p2retail::SceneIdentity& scene) {
 p2retail::Snapshot floor;
 (void)pc_p2_original_pod_can_abort_prepared(scene);
 return pc_p2_original_pod_owned() && pc_p2_original_pod_completed(p,r,scene)
     && pc_p2_original_pod_context(r,scene,floor);
}
'''),
        'forge_begin': (False, '''#include "pc_p2_original_pod.h"
void forge(Pellet* p) {P2OriginalPodNativeSeam::begin(p);}
'''),
        'forge_completion': (False, '''#include "pc_p2_original_pod.h"
bool forge(Pellet* p,const PelletGoalState& s) {return P2OriginalPodNativeSeam::done(p,s);}
'''),
        'forge_cleanup': (False, '''#include "pc_p2_original_pod.h"
void forge(Pellet* p) {P2OriginalPodNativeSeam::cleanup(p);}
'''),
    }
    for name, (accepted, contents) in cases.items():
        path = args.output / (name + '.cpp')
        path.write_text(contents, encoding='utf-8')
        result = subprocess.run([str(args.compiler), '-std=c++17', '-fsyntax-only',
                                 '-I' + str(source / 'pc_port'), str(path)],
                                capture_output=True, text=True, timeout=30)
        (args.output / (name + '.log')).write_text(result.stdout + result.stderr,
                                                 encoding='utf-8')
        if (result.returncode == 0) != accepted:
            raise SystemExit('FAIL ' + name + ': unexpected API access')
        if not accepted and 'private' not in result.stderr:
            raise SystemExit('FAIL ' + name + ': rejected for an unrelated reason')
        print('PASS', name, 'accepted' if accepted else 'native-only authority denied')


if __name__ == '__main__':
    main()
