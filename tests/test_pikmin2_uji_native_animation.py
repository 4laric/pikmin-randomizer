"""Compile the family-only parser without building the game."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

class UjiNativePolicyTests(unittest.TestCase):
    def test_strict_bank_parser(self):
        root=Path(__file__).resolve().parents[1]
        cpp=r'''
#include "pc_p2_uji_animation.h"
#include <sstream>
#include <cassert>
std::string valid(){std::string s="P2_UJI_ANIMATION_1 ";for(int k=0;k<2;++k){s+=k?"UjiB ":"UjiA ";for(auto n:{"dead","dead_p","appear","dive","move","attack1"})s+=std::string(n)+" 2 20 0 19 ";if(k)s+="attack2 2 20 0 19 eat 2 20 0 19 ";s+="type5 2 20 0 19 ";}return s;}
bool parse(std::string s){std::istringstream in(s);std::vector<p2animation::Clip> b[2];return p2uji::parse(in,b);}
int main(){auto s=valid();assert(parse(s));assert(!parse(s+"trailing"));assert(!parse(s.substr(0,s.size()-8)));auto bad=s;bad.replace(bad.find("2 20"),4,"13 20");assert(!parse(bad));bad=s;bad.replace(bad.find("0 19"),4,"1 19");assert(!parse(bad));bad=s;bad.replace(bad.find("UjiB"),4,"UjiA");assert(!parse(bad));}
'''
        with tempfile.TemporaryDirectory() as tmp:
            source=Path(tmp)/'policy.cpp';exe=Path(tmp)/'policy.exe';source.write_text(cpp)
            env=dict(os.environ,PATH='C:/msys64/mingw64/bin;'+os.environ.get('PATH',''))
            subprocess.run(['C:/msys64/mingw64/bin/g++.exe','-std=c++17','-I'+str(root/'native/pc_port'),str(source),'-o',str(exe)],check=True,env=env,capture_output=True)
            subprocess.run([str(exe)],check=True,env=env,capture_output=True)

if __name__=='__main__':unittest.main()
