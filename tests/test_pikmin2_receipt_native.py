"""Compile and execute the lane-06 native receipt/cargo-contest provider surface.

Mirrors tests/test_pikmin2_preview_policy.py: the engine-free headers are
compiled with the maintained MinGW g++ against a resolved native source tree
(``PIKMIN_NATIVE_SOURCE`` or the exported ``engine/``). Skips cleanly when the
toolchain or the not-yet-exported header is unavailable.
"""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


class ReceiptNativeTests(unittest.TestCase):
    def test_native_receipt_contract(self):
        compiler = Path('C:/msys64/mingw64/bin/g++.exe')
        if not compiler.is_file():
            self.skipTest('MinGW compiler unavailable')
        root = Path(__file__).resolve().parents[1]
        native = Path(os.environ.get('PIKMIN_NATIVE_SOURCE', root / 'engine'))
        if not (native / 'pc_port' / 'pc_p2_receipt.h').is_file():
            self.skipTest('pc_p2_receipt.h not available in the resolved native source')
        source = r'''
#include "pc_p2_receipt.h"
#include "pc_p2_cargo_contest.h"
#include <cstdio>
#include <stdexcept>
#include <string>
#include <vector>
using namespace P2Receipt;
template <class F> bool throws(F f){try{f();}catch(const std::runtime_error&){return true;}return false;}
int main() {
    MemoryReceiptPersistence memory;
    ReceiptLedger ledger(memory);
    if(!ledger.grant("s","corpse:1","slot7","enc0"))return 1;
    if(ledger.grant("s","corpse:1","slot7","enc0"))return 2;
    ledger.reload();
    if(!ledger.has("s","corpse:1","slot7","enc0"))return 3;
    if(ledger.grant("s","corpse:1","slot7","enc0"))return 4;
    if(!throws([]{Descriptor d;d.version="nope";d.identity="x";d.family="f";d.drop="corpse";validateDescriptor(d);}))return 5;
    Descriptor pod;pod.identity="corpse:1";pod.family="lane-13";pod.drop="corpse";pod.ledger=Ledger::Pod;
    if(!throws([&]{reconcileOrdinary({pod},{"corpse:1"});}))return 6;
    P2CargoContestConfig cfg;cfg.identity="nest:1";cfg.sourceToken="src";cfg.minThreshold=3;
    cfg.maxThreshold=10;cfg.requiredCarriers=2;cfg.maxCarriers=4;
    P2CargoContest contest(cfg);contest.begin(0.0f);
    std::vector<P2ContestCarrier> weak={{"p:1",2},{"p:2",2}};
    std::vector<P2ContestCarrier> strong={{"p:1",6},{"p:2",6}};
    if(contest.update(0.0f,weak)!=P2ContestOutcome::Held)return 7;
    if(contest.update(1.0f,strong)!=P2ContestOutcome::Stolen)return 8;
    MemoryReceiptPersistence cmem;ReceiptLedger cledger(cmem);
    if(!contest.grantReceipt(cledger,"s","cargo9","enc0"))return 9;
    if(contest.grantReceipt(cledger,"s","cargo9","enc0"))return 10;
    contest.reset();
    if(contest.result()!=P2ContestOutcome::Held)return 11;
    std::printf("PASS p2_receipt_native_contract\n");
    return 0;
}
'''
        with tempfile.TemporaryDirectory(prefix='p2-receipt-') as tmp:
            path = Path(tmp)
            cpp = path / 'receipt.cpp'
            exe = path / 'receipt.exe'
            cpp.write_text(source)
            env = dict(os.environ, PATH=str(compiler.parent) + os.pathsep + os.environ.get('PATH', ''))
            subprocess.run([str(compiler), '-std=c++17', '-I', str(native / 'pc_port'), str(cpp), '-o', str(exe)],
                           check=True, capture_output=True, env=env)
            result = subprocess.run([str(exe)], check=True, capture_output=True, env=env)
            self.assertIn('PASS p2_receipt_native_contract', result.stdout.decode(errors='replace'))

    def test_native_delivery_contract(self):
        compiler = Path('C:/msys64/mingw64/bin/g++.exe')
        if not compiler.is_file():
            self.skipTest('MinGW compiler unavailable')
        root = Path(__file__).resolve().parents[1]
        native = Path(os.environ.get('PIKMIN_NATIVE_SOURCE', root / 'engine'))
        delivery_header = native / 'pc_port' / 'pc_p2_delivery.h'
        receipt_header = native / 'pc_port' / 'pc_p2_receipt.h'
        if not receipt_header.is_file() or not delivery_header.is_file():
            self.skipTest('pc_p2_delivery.h not available in the resolved native source')
        source = r'''
#include "pc_p2_delivery.h"
#include <cstdio>
#include <stdexcept>
#include <string>
using namespace P2Delivery;
template <class F> bool throws(F f){try{f();}catch(const std::runtime_error&){return true;}return false;}
int main() {
    const unsigned kSnow=45, kDwarfOrange=44;
    if(p2SourceIdentity(kSnow,1)==p1ProxyIdentity(3,1))return 1;
    if(p2SourceIdentity(3,1)==p1ProxyIdentity(3,1))return 2;
    P2Receipt::MemoryReceiptPersistence mem;
    P2Receipt::ReceiptLedger ledger(mem);
    DeliveryReceiver receiver(ledger);
    if(!receiver.deliver("seed-a",kSnow,3,1,77,"tutorial_1:floor1"))return 2;
    if(receiver.deliver("seed-a",kSnow,3,1,77,"tutorial_1:floor1"))return 3;
    if(!receiver.delivered("seed-a",kSnow,3,1,77,"tutorial_1:floor1"))return 4;
    if(!receiver.deliver("seed-a",0,3,1,77,"tutorial_1:floor1"))return 5;
    auto d44=sourceDescriptor(kDwarfOrange,1); auto d45=sourceDescriptor(kSnow,1);
    auto ok=P2Receipt::reconcileOrdinary({d44,d45},{p2SourceIdentity(44,1),p2SourceIdentity(45,1)});
    if(!ok.ok)return 6;
    auto pod=sourceDescriptor(kSnow,1); pod.ledger=P2Receipt::Ledger::Pod;
    if(!throws([&]{P2Receipt::reconcileOrdinary({d44,pod},{p2SourceIdentity(44,1),p2SourceIdentity(kSnow,1)});}))return 7;
    std::printf("PASS p2_delivery_native_contract\n");
    return 0;
}
'''
        with tempfile.TemporaryDirectory(prefix='p2-delivery-') as tmp:
            path = Path(tmp)
            cpp = path / 'delivery.cpp'
            exe = path / 'delivery.exe'
            cpp.write_text(source)
            env = dict(os.environ, PATH=str(compiler.parent) + os.pathsep + os.environ.get('PATH', ''))
            subprocess.run([str(compiler), '-std=c++17', '-I', str(native / 'pc_port'), str(cpp), '-o', str(exe)],
                           check=True, capture_output=True, env=env)
            result = subprocess.run([str(exe)], check=True, capture_output=True, env=env)
            self.assertIn('PASS p2_delivery_native_contract', result.stdout.decode(errors='replace'))


if __name__ == '__main__':
    unittest.main()
