"""Compile and execute the actual standalone cargo phase helper."""
from pathlib import Path
import os,subprocess,tempfile

def run():
    header=Path(__file__).resolve().parents[1]/'pc_port/pc_p2_breadbug_cargo_phase.h'
    code='#include "'+header.as_posix()+'"\n'+r'''
#include <cassert>
#include <limits>
using namespace p2breadbugcargo;
int main(){
 auto intro=select(5,true,true,5,50,10,40);assert(intro.kind==Back&&intro.frame==5);
 auto loop=select(6,true,true,25,50,10,40);assert(loop.kind==Back&&loop.frame==24.5f);
 assert(select(6,true,true,25,50,10,40).frame==loop.frame); // paused/repeated draw
 assert(select(6,true,true,10,50,10,40).frame==10); // native loop wrap
 assert(select(8,true,true,24,49,0,0).frame==24);
 assert(select(8,true,true,500,49,0,0).frame==48);
 assert(select(9,false,false,0,0,0,0).kind==Hidden);
 assert(select(6,false,true,25,50,10,40).kind==Fallback);
 assert(select(6,true,false,25,50,10,40).kind==Fallback);
 assert(select(6,true,true,25,50,0,0).kind==Fallback);
 assert(select(6,true,true,25,50,40,10).kind==Fallback);
 assert(select(6,true,true,25,50,10,50).kind==Fallback);
 assert(select(6,true,true,std::numeric_limits<float>::quiet_NaN(),50,10,40).kind==Fallback);
 assert(select(0,true,true,25,50,10,40).kind==Fallback);
}
'''
    with tempfile.TemporaryDirectory() as d:
        root=Path(d);(root/'test.cpp').write_text(code);exe=root/'test.exe';env=dict(os.environ,PATH='C:/msys64/mingw64/bin;'+os.environ['PATH'])
        subprocess.run(['C:/msys64/mingw64/bin/g++.exe','-std=c++17',str(root/'test.cpp'),'-o',str(exe)],check=True,env=env)
        subprocess.run([str(exe)],check=True,env=env)
    print('PASS actual Breadbug cargo phase helper')

if __name__=='__main__':run()
