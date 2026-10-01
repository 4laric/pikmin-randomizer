"""Analytic plane and exclusion tests for the native cargo support function."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


class CargoUphillTests(unittest.TestCase):
    def test_plane_tangent_and_preserved_velocity_cases(self):
        root = Path(__file__).resolve().parents[1]
        native = Path(os.environ.get('PIKMIN_NATIVE_SOURCE', root/'engine'))
        compiler = shutil.which('g++') or ('C:/msys64/mingw64/bin/g++.exe' if Path('C:/msys64/mingw64/bin/g++.exe').exists() else None)
        if not compiler:
            self.skipTest('C++ compiler unavailable')
        source = r'''
#include "pc_p2_cargo_ground.h"
#include <cassert>
#include <limits>
int main(){
  const float nx=.258f,ny=.966f,nz=.024f,vx=-8.39f,vz=.85f;
  const float y=pc_p2_cargo_uphill_velocity(vx,vz,-20.f,nx,ny,nz);
  assert(y>0 && std::fabs(nx*vx+ny*y+nz*vz)<.00001f);
  assert(pc_p2_cargo_uphill_velocity(vx,vz,9.f,nx,ny,nz)==9.f); // upward impulse
  assert(pc_p2_cargo_uphill_velocity(vx,vz,y,nx,ny,nz)==y); // stable support
  assert(pc_p2_cargo_uphill_velocity(8,0,-20,nx,ny,0)==-20); // downhill
  assert(pc_p2_cargo_uphill_velocity(-8,0,-20,0,1,0)==-20); // flat
  assert(pc_p2_cargo_uphill_velocity(0,0,-20,nx,ny,nz)==-20); // stationary
  assert(pc_p2_cargo_uphill_velocity(-8,0,-20,1,.6f,0)==-20); // wall cutoff
  assert(pc_p2_cargo_uphill_velocity(-8,0,-20,1,-1,0)==-20); // downward normal
  const float nan=std::numeric_limits<float>::quiet_NaN();
  const float inf=std::numeric_limits<float>::infinity();
  assert(pc_p2_cargo_uphill_velocity(nan,0,-20,nx,ny,nz)==-20);
  assert(pc_p2_cargo_uphill_velocity(-8,0,-20,nx,inf,nz)==-20);
  assert(std::isnan(pc_p2_cargo_uphill_velocity(-8,0,nan,nx,ny,nz)));
  assert(pc_p2_cargo_uphill_velocity(-3e38f,0,-20,3e38f,1,0)==-20);
}
'''
        with tempfile.TemporaryDirectory() as temp:
            cpp=Path(temp)/'uphill.cpp'
            exe=Path(temp)/('uphill.exe' if os.name=='nt' else 'uphill')
            cpp.write_text(source)
            env=dict(os.environ,PATH=str(Path(compiler).parent)+os.pathsep+os.environ.get('PATH',''))
            build=subprocess.run([compiler,'-std=c++17','-O2','-I'+str(native/'pc_port'),str(cpp),'-o',str(exe)],env=env,capture_output=True,text=True)
            self.assertEqual(build.returncode,0,build.stdout+build.stderr)
            subprocess.run([str(exe)],check=True,env=env,capture_output=True)


if __name__=='__main__':unittest.main()
