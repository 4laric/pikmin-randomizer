"""Execute the exact isolated native profile parser without engine/render dependencies."""
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

MODULE=Path(__file__).resolve().parents[1]/'native-patches/giant-breadbug/pc_p2_giant_breadbug_visual.cpp'
COMPILER=Path('C:/msys64/mingw64/bin/g++.exe')

@unittest.skipUnless(COMPILER.exists(),'MinGW compiler required')
class NativeParserTests(unittest.TestCase):
    def test_actual_native_parser(self):
        source=MODULE.read_text();start=source.index('    std::ifstream in("p2-giant-breadbug-visual.txt")');end=source.index('    for(int kind=0;kind<2;++kind)for',start)
        parser=source[start:end].replace('std::ifstream in("p2-giant-breadbug-visual.txt");if(!in)return;','std::istringstream in(text);')
        program='''#include <sstream>
#include <vector>
#include <string>
#include <set>
#include <cmath>
#include <stdexcept>
#include <iostream>
struct Clip { int duration=0;std::vector<int> frames; };
struct Display { unsigned id;int kind;float x,y,z,yaw; };
void fail(){throw std::runtime_error("invalid");}
void parse(const std::string& text){ Clip clips[2];std::vector<Display> displays;
'''+parser+'''}
int main(){std::string input((std::istreambuf_iterator<char>(std::cin)),{});try{parse(input);return 0;}catch(...){return 2;}}
'''
        valid='P2_GIANT_BREADBUG_VISUAL_1\nwait 59 2 0 58\nmove 54 2 0 53\n1\n229001 wait -150 30 1850 0\n'
        cases=[(valid,0),(valid+'garbage',2),(valid.replace('229001','4294967296'),2),(valid.replace('229001','-1'),2),(valid.replace('0 58','58 0'),2),(valid.replace('wait -150','actor -150'),2),(valid.replace('30 1850','nan 1850'),2),(valid.replace('\n1\n','\n9\n'),2),(valid.replace('1\n229001','2\n229001')+'229001 nest 0 0 0 0\n',2)]
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp);cpp=path/'parser.cpp';exe=path/'parser.exe';cpp.write_text(program)
            env=os.environ.copy();env['PATH']=str(COMPILER.parent)+';'+env['PATH']
            r=subprocess.run([str(COMPILER),'-std=c++17',str(cpp),'-o',str(exe)],env=env,capture_output=True,text=True)
            self.assertEqual(0,r.returncode,r.stderr)
            for text,code in cases:
                with self.subTest(profile=text):self.assertEqual(code,subprocess.run([str(exe)],input=text,text=True,env=env,capture_output=True).returncode)

if __name__=='__main__':unittest.main()
