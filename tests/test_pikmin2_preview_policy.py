"""Compile and execute the engine-independent native cargo-free policy."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


class PreviewPolicyTests(unittest.TestCase):
    def test_native_policy_matrix(self):
        compiler=Path('C:/msys64/mingw64/bin/g++.exe')
        if not compiler.is_file():self.skipTest('MinGW compiler unavailable')
        root=Path(__file__).resolve().parents[1]
        native=Path(os.environ.get('PIKMIN_NATIVE_SOURCE',root/'engine'))
        source=r'''
#include "pc_p2_preview_policy.h"
#include <sstream>
int main() {
    const char* good[]={"P2_CARGO_FREE_1", "P2_CARGO_FREE_1\n", "  P2_CARGO_FREE_1\r\n"};
    for(auto text:good){std::istringstream in(text);p2ReadCargoFree(in);}
    const char* bad[]={"", "P2_CARGO_FREE_2", "P2_CARGO_FREE_1 0", "P2_CARGO_FREE_1 junk", "P2_CARGO_FREE_1\nP2_CARGO_FREE_1"};
    for(auto text:bad){bool rejected=false;try{std::istringstream in(text);p2ReadCargoFree(in);}catch(const std::exception&){rejected=true;}if(!rejected)return 1;}
    for(int free=0;free<2;++free)for(int config=0;config<2;++config)for(int actor=0;actor<2;++actor){
        bool accepted=true;try{p2ValidatePreviewCargo(free,config,actor);}catch(const std::exception&){accepted=false;}
        const bool expected=free?(!config&&!actor):bool(actor);
        if(accepted!=expected)return 2;
    }
    return 0;
}
'''
        with tempfile.TemporaryDirectory(prefix='p2-policy-') as tmp:
            path=Path(tmp);cpp=path/'policy.cpp';exe=path/'policy.exe';cpp.write_text(source)
            env=dict(os.environ,PATH=str(compiler.parent)+os.pathsep+os.environ.get('PATH',''))
            subprocess.run([str(compiler),'-std=c++17','-I',str(native/'pc_port'),str(cpp),'-o',str(exe)],check=True,capture_output=True,env=env)
            subprocess.run([str(exe)],check=True,capture_output=True,env=env)


if __name__=='__main__':unittest.main()
