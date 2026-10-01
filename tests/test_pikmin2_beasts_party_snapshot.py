import unittest
from experimental.pikmin2_beasts_party_snapshot import party_snapshot


def with_party(log,red=10,purple=10):
    lines=['P2_BEASTS_PARTY health=0.875 count=20']
    for i,species in enumerate(['red']*red+['purple']*purple):
        lines.append(f'P2_BEASTS_SURVIVOR index={i} species={species} maturity={i%3}')
    lines.append('P2_BEASTS_PARTY_END')
    return log.replace('PASS P2_BEASTS_','\n'.join(lines)+'\nPASS P2_BEASTS_',1)


class PartyTests(unittest.TestCase):
    def setUp(self):
        self.log=with_party('P2_BEASTS_READY reds=20 flowers=2 cargo=0\nP2_BEASTS_CAPTAIN_PLUCK purple=1\nPASS P2_BEASTS_FLOOR2\n')
        self.population=dict(red=10,purple=10,sprouts=0)
    def test_actual_fields_preserved(self):
        result=party_snapshot(self.log,self.population)
        self.assertEqual(result['health'],.875)
        self.assertEqual([p['maturity'] for p in result['squad']],[i%3 for i in range(20)])
    def test_malformed_duplicate_count_and_population(self):
        for old,new in [('health=0.875','health=nan'),('health=0.875','health=1e999'),
                        ('health=0.875','health=0'),('health=0.875','health=1.1'),
                        ('count=20','count=19'),('index=1 ','index=0 '),('maturity=2','maturity=3'),
                        ('species=purple','species=red'),('PARTY_END','PARTY_END\nP2_BEASTS_PARTY_END')]:
            with self.subTest(old=old,new=new),self.assertRaises(ValueError):party_snapshot(self.log.replace(old,new),self.population)
        with self.assertRaises(ValueError):party_snapshot(self.log,dict(red=10,purple=10,sprouts=1))
    def test_snapshot_phase_and_outside_records(self):
        line='P2_BEASTS_SURVIVOR index=0 species=red maturity=0\n'
        for log in (line+self.log,self.log+line,self.log.replace('P2_BEASTS_CAPTAIN_PLUCK purple=1\n',''),self.log+self.log):
            with self.subTest(log=log),self.assertRaises(ValueError):party_snapshot(log,self.population)
