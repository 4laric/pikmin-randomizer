import unittest
from scripts.purple_birth_ledger import validate_birth_receipts
from scripts.purple_birth_ledger import SAVE

def rows(stage,field_red=0,stock_red=0,purple=0):
 return [f'P2_PURPLE_BIRTH_CENSUS stage={stage} species={s} maturity={m} field={field_red if (s,m)==(1,0) else purple if stage=="acquired" and (s,m)==(3,0) else 0} stock={stock_red if (s,m)==(1,0) else purple if stage=="saved" and (s,m)==(3,0) else 0} heads=0 read_only=1' for s in range(6) for m in range(3)]
REQUEST='P2_PURPLE_BIRTH_RECEIPT kind=0 frame=1 receipt=1 onion=1 source=2 head=0 model=825258608 color=1 maturity=-1 requested=2 pending_before=0 pending_after=2 physical_pellet_binding=0 logical_demand_accounting=1 read_only=1'
EMIT='P2_PURPLE_BIRTH_RECEIPT kind=1 frame=2 receipt=1 onion=1 source=0 head=3 model=0 color=1 maturity=-1 requested=0 pending_before=2 pending_after=1 physical_pellet_binding=0 logical_demand_accounting=1 read_only=1'
STORED='P2_PURPLE_BIRTH_RECEIPT kind=2 frame=3 receipt=1 onion=1 source=0 head=0 model=0 color=1 maturity=0 requested=0 pending_before=1 pending_after=0 physical_pellet_binding=0 logical_demand_accounting=1 read_only=1'
CONVERT='P2_PURPLE_CONVERSION_RECEIPT frame=4 bud=4 generator=5 input=6 head=7 input_species=1 input_maturity=0 output_species=3 one_to_one=1 read_only=1'
def fixture():
 return rows('initial',20)+[REQUEST,EMIT,STORED,CONVERT]+rows('acquired',19,2,1)+rows('saved',0,21,1)+[SAVE]
class ReceiptControls(unittest.TestCase):
 def test_successful_earned2_control_not_gameplay(self):
  p=validate_birth_receipts('\n'.join(fixture()));self.assertEqual(p['saved_total'],22);self.assertEqual(p['successful_earned_births'],[0,2,0])
 def test_request_not_birth(self):
  lines=fixture();lines.remove(EMIT);lines.remove(STORED)
  with self.assertRaises(ValueError):validate_birth_receipts('\n'.join(lines))
 def test_malformed_native_source_counter_and_width(self):
  for text in [EMIT.replace('receipt=1','receipt=2'),EMIT.replace('color=1','color=0'),EMIT.replace('pending_before=2','pending_before=1'),STORED.replace('maturity=0','maturity=1'),EMIT.replace('head=3','head=0'),REQUEST.replace('model=825258608','model=4294967296'),EMIT.replace('frame=2','frame=0'),REQUEST.replace('receipt=1','receipt=2')]:
   with self.subTest(text=text),self.assertRaises(ValueError):validate_birth_receipts('\n'.join([text if x in (REQUEST,EMIT,STORED) and x.split(' kind=')[1][0]==text.split(' kind=')[1][0] else x for x in fixture()]))
 def test_missing_duplicate_conversion(self):
  for lines in [[x for x in fixture() if x!=CONVERT],fixture()+[CONVERT]]:
   with self.assertRaises(ValueError):validate_birth_receipts('\n'.join(lines))
 def test_wrong_saved_population_or_field(self):
  for old,new in [('stock=21','stock=19'),('stock=21','stock=22'),('species=1 maturity=0 field=0 stock=21','species=1 maturity=0 field=1 stock=21')]:
   with self.subTest(new=new),self.assertRaises(ValueError):validate_birth_receipts('\n'.join(fixture()).replace(old,new))
 def test_initial_foreign_stock(self):
  bad='\n'.join(fixture()).replace('stage=initial species=0 maturity=0 field=0 stock=0','stage=initial species=0 maturity=0 field=0 stock=1')
  with self.assertRaises(ValueError):validate_birth_receipts(bad)
 def test_duplicate_compartment_late_receipt(self):
  for lines in [fixture()+[REQUEST],fixture()[:-1]+[rows('saved',0,21,1)[0],SAVE]]:
   with self.assertRaises(ValueError):validate_birth_receipts('\n'.join(lines))
if __name__=='__main__':unittest.main()
