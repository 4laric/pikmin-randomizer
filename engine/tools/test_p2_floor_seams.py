"""Compile the actual production seam predicate against minimal collision structs.

No game assets or complete engine build are needed. The predicate is extracted
from mapMgr.cpp, not reimplemented here; the native haul fixture covers its callsite.
"""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import tempfile


STUBS = r'''
#include <cassert>
#include <cmath>
#include <limits>
#include <initializer_list>
using u32 = unsigned;
float absF(float value) { return std::fabs(value); }
struct Vector3f { float x, y, z; };
struct Plane { Vector3f mNormal; float mOffset; };
struct CollTriInfo {
    int mAdjacentTriIndices[3];
    unsigned mMapCode;
    Plane mTriangle;
    u32 mVertexIndices[3];
};
struct BaseShape { CollTriInfo* mTriList; int mTriCount; };
'''

CASES = r'''
int main() {
    // Real imported seam: floor2 triangles9/18, renumbered to0/1.
    CollTriInfo tris[2] = {
        {{-1, -1, 1}, 7, {{0, 1, 0}, 25}, {18, 17, 7}},
        {{0, -1, -1}, 7, {{0, 1, 0}, 25}, {18, 7, 8}}
    };
    BaseShape model{tris, 2};
    assert(p2SmoothStaticFloorEdge(&model, tris[0], 2));
    assert(p2SmoothStaticFloorEdge(&model, tris[1], 0));
    assert(!p2SmoothStaticFloorEdge(&model, tris[0], 0)); // Boundary.
    tris[0].mAdjacentTriIndices[2] = 2;
    assert(!p2SmoothStaticFloorEdge(&model, tris[0], 2)); // Out-of-bounds neighbor.
    tris[0].mAdjacentTriIndices[2] = 0;
    assert(!p2SmoothStaticFloorEdge(&model, tris[0], 2)); // Self neighbor.
    tris[0].mAdjacentTriIndices[2] = 1;
    for (int bad : {-1, 2}) {
        tris[1].mAdjacentTriIndices[0] = bad;
        assert(!p2SmoothStaticFloorEdge(&model, tris[0], 2)); // Bad reciprocal ID.
    }
    tris[1].mAdjacentTriIndices[0] = 0;
    tris[1].mVertexIndices[0] = 19;
    assert(!p2SmoothStaticFloorEdge(&model, tris[0], 2)); // Wrong shared edge.
    tris[1].mVertexIndices[0] = 18;
    tris[1].mMapCode = 8;
    assert(!p2SmoothStaticFloorEdge(&model, tris[0], 2)); // Material transition.
    tris[1].mMapCode = 7;
    tris[1].mTriangle.mOffset = 26;
    assert(!p2SmoothStaticFloorEdge(&model, tris[0], 2)); // Different height.
    tris[1].mTriangle.mOffset = 25;
    tris[1].mTriangle.mNormal = {.01f, .9999f, 0};
    assert(!p2SmoothStaticFloorEdge(&model, tris[0], 2)); // Real crease.
    tris[0].mTriangle.mNormal = {1, 0, 0};
    tris[1].mTriangle.mNormal = {1, 0, 0};
    assert(!p2SmoothStaticFloorEdge(&model, tris[0], 2)); // Coplanar wall.
    tris[0].mTriangle.mNormal = {0, 1, 0};
    tris[1].mTriangle.mNormal = {0, 1, 0};
    CollTriInfo foreign = tris[0];
    assert(!p2SmoothStaticFloorEdge(&model, foreign, 2)); // Different model.
    tris[1].mTriangle.mOffset = std::numeric_limits<float>::quiet_NaN();
    assert(!p2SmoothStaticFloorEdge(&model, tris[0], 2));
    assert(!p2SmoothStaticFloorEdge(nullptr, tris[0], 2));
    model.mTriList = nullptr;
    assert(!p2SmoothStaticFloorEdge(&model, tris[0], 2));
}
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--compiler', default=os.environ.get('CXX', 'g++'))
    args = parser.parse_args()
    compiler = shutil.which(args.compiler)
    if compiler is None:
        parser.error('C++ compiler unavailable; pass --compiler with its executable path')
    native = Path(__file__).resolve().parents[1]
    source = (native/'src/plugPikiColin/mapMgr.cpp').read_text()
    start = source.index('static bool p2SmoothStaticFloorEdge(')
    end = source.index('\n#endif', start)
    predicate = source[start:end]
    env = dict(os.environ)
    env['PATH'] = str(Path(compiler).parent) + os.pathsep + env.get('PATH', '')
    with tempfile.TemporaryDirectory(prefix='p2-floor-seams-') as tmp:
        directory = Path(tmp)
        test = directory/'test.cpp'
        exe = directory/('test.exe' if os.name == 'nt' else 'test')
        test.write_text(STUBS + predicate + CASES)
        subprocess.run([compiler, '-std=c++17', '-UNDEBUG', str(test), '-o', str(exe)], env=env, check=True)
        subprocess.run([str(exe)], env=env, check=True)
    print('PASS production floor seam predicate: reciprocal floor, boundary, topology, bounds, material, height, crease, wall, invalid model')


if __name__ == '__main__':
    main()
