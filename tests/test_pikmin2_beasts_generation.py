import copy
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys
import unittest

from experimental.pikmin2_beasts_floor2 import generation_context,decode_no_cargo,prepare
from experimental.pikmin2_beasts_floor2_runtime import validate
from tests.test_pikmin2_beasts_floor2_runtime import PLAN,trace


def plan(count):
    context=generation_context(count)
    return dict(flowers=copy.deepcopy(PLAN['flowers']) if count<20 else [],generation_context=context,
                generation_identity=hashlib.sha256(json.dumps(context,sort_keys=True,separators=(',',':')).encode()).hexdigest())


def suppressed(count=20):
    return (f'P2_ROOM_CARGO_FREE_READY cargo=0 repairs=1\nP2_BEASTS_GENERATION purple={count} flowers=0\n'
            'P2_BEASTS_READY reds=20 flowers=0 cargo=0\n'
            'PASS P2_BEASTS_SUPPRESSED reds=20 purple=0 sprouts=0 flowers=0 cargo=0 pokos=0 repairs_unchanged=1\n')


class GenerationTests(unittest.TestCase):
    def test_source_boundary_and_deterministic_context(self):
        for count in (0,19,20,21,2147483647):
            with self.subTest(count=count):
                context=generation_context(count)
                self.assertEqual(context['spawned_generators'],[62000,62001] if count<20 else [])
                self.assertEqual(sum(context['conversion_budgets'].values()),10 if count<20 else 0)
                self.assertEqual(context,generation_context(count))
                self.assertFalse(context['native_global_population_verified'])
        self.assertNotEqual(plan(19)['generation_identity'],plan(20)['generation_identity'])
        self.assertNotEqual(plan(20)['generation_identity'],plan(21)['generation_identity'])

    def test_invalid_context_rejected_before_asset_access(self):
        for count in (None,True,False,-1,1.5,'20',float('nan'),2147483648):
            with self.subTest(count=count),self.assertRaises(ValueError):generation_context(count)
            if count is not None:
                with self.assertRaises(ValueError):prepare(Path('missing'),Path('missing'),Path('missing'),Path('missing'),Path('missing'),global_purple_count=count)

    def test_zero_flower_generator_and_context_mismatch(self):
        entries=[]
        for label in ['preview red onion','preview ship']+['preview red pikmin']*20:
            e=bytearray(100);e[:8]=b'    0.0v';e[16:48]=label.encode().ljust(32,b'\0');entries.append(e)
        raw=b'1.0v'+struct.pack('>4fI',0,0,0,0,22)+b''.join(entries)
        self.assertEqual(decode_no_cargo(raw,0)['flowers'],0)
        with self.assertRaises(ValueError):decode_no_cargo(raw,2)
        with self.assertRaises(ValueError):decode_no_cargo(raw,True)
        for raw_bad in (raw[:20],raw.replace(b'preview ship',b'preview pond'),raw+b'    0.0v'):
            with self.assertRaises(ValueError):decode_no_cargo(raw_bad,0)

    def test_native_boundary_evidence(self):
        allowed=trace().replace('P2_BEASTS_READY','P2_BEASTS_GENERATION purple=19 flowers=2\nP2_BEASTS_READY',1)
        self.assertEqual(validate(allowed,plan(19))['final_population']['purple'],10)
        self.assertEqual(validate(suppressed(),plan(20))['final_population']['purple'],0)
        for log,p in ((allowed,plan(20)),(suppressed(),plan(19)),(suppressed(),plan(21))):
            with self.assertRaises(ValueError):validate(log,p)
        tampered=plan(20);tampered['generation_context']['global_plus_cave_purple']=21
        with self.assertRaises(ValueError):validate(suppressed(21),tampered)

    def test_suppressed_stage_rejects_events_rewards_and_duplicates(self):
        for suffix in ('P2_BEASTS_FLOWER id=62000','P2_BEASTS_THROW original=0',
                       'P2_VIOLET_WITNESS sequence=1 generator=62000 input=red',
                       'P2_VIOLET_CONVERT count=1','P2_POD_RECEIPT id=unexpected','FAIL hidden cargo',
                       'P2_BEASTS_GENERATION purple=20 flowers=0'):
            with self.subTest(suffix=suffix),self.assertRaises(ValueError):validate(suppressed()+suffix+'\n',plan(20))
        with self.assertRaises(ValueError):validate(suppressed().replace('reds=20 purple=0','reds=19 purple=1'),plan(20))

    def test_runtime_cli_requires_context(self):
        result=subprocess.run([sys.executable,'-m','experimental.pikmin2_beasts_floor2_runtime',
                               '--root','missing','--assets','missing','--exe','missing','--output','missing'],
                              capture_output=True,text=True,cwd=Path(__file__).resolve().parents[1])
        self.assertEqual(result.returncode,2)
        self.assertIn('--global-purple-count',result.stderr)


if __name__=='__main__':unittest.main()
