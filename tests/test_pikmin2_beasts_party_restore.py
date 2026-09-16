import copy
import unittest
from experimental.pikmin2_beasts_party_restore import restore_party,entry_text,validate_restore
from tests.test_pikmin2_beasts_party_snapshot import with_party


class RestoreTests(unittest.TestCase):
    def setUp(self):
        self.party=dict(health=.875,squad=[dict(species='red' if i<10 else 'purple',maturity=i%3) for i in range(20)])
        self.log='P2_ROOM_CARGO_FREE_READY cargo=0\n'
        self.log+=''.join(f'P2_CAVE_RESTORE species={1 if p["species"]=="red" else 3} maturity={p["maturity"]}\n' for p in self.party['squad'])
        self.log+=with_party('P2_BEASTS_READY reds=10 flowers=0 cargo=0\nPASS P2_BEASTS_RESTORE updates=300 cargo=0 pokos=0 repairs_unchanged=1\n')
    def test_entry_and_roundtrip(self):
        text=entry_text(self.party,'a'*32)
        self.assertEqual(text.splitlines()[:4],['P2_CAVE_ENTRY_1','a'*32,'2 0.875 20','1 0'])
        self.assertIn('3 1',text)
        self.assertEqual(validate_restore(self.log,self.party),self.party)
        result=restore_party(self.party);result['squad'][0]['maturity']=2
        self.assertEqual(self.party['squad'][0]['maturity'],0)
    def test_invalid_input(self):
        for health in (0,2,True,float('nan'),float('inf')):
            bad=copy.deepcopy(self.party);bad['health']=health
            with self.subTest(health=health),self.assertRaises(ValueError):restore_party(bad)
        for squad in ([],self.party['squad'][:19],[dict(species='blue',maturity=0)]*20):
            with self.subTest(squad=squad),self.assertRaises(ValueError):restore_party(dict(health=1,squad=squad))
        with self.assertRaises(ValueError):entry_text(self.party,'invalid')
    def test_changed_health_maturity_missing_restore_and_rewards(self):
        for old,new in [('health=0.875','health=1'),('maturity=2','maturity=1'),
                        ('P2_CAVE_RESTORE','IGNORED_RESTORE'),('updates=300','updates=30')]:
            with self.subTest(old=old),self.assertRaises(ValueError):validate_restore(self.log.replace(old,new),self.party)
        with self.assertRaises(ValueError):validate_restore(self.log+'P2_VIOLET_WITNESS unexpected\n',self.party)
        with self.assertRaises(ValueError):validate_restore(self.log+'P2_CAVE_RESTORE malformed\n',self.party)
