"""Engine-free native marker accounting controls, not actual pluck proof."""
import importlib.util,sys,unittest,copy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
spec=importlib.util.spec_from_file_location('ivory54',ROOT/'scripts/run_p2_white_campaign.py');r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)
class IvoryOutputs(unittest.TestCase):
 def sample(self,adults=(0,0,0)):
  return [dict(uid=str(uid),natural_outputs='5',red=str(20-5*(i+1)),white_heads=str(5*(i+1)-adults[i]),white_adults=str(adults[i]),spent=str(5*(i+1))) for i,uid in enumerate((25,28,29))]
 def test_heads_only_real_count_with_explicit_zero_adults(self):r.assess_ivory_outputs(self.sample())
 def test_early_ordinary_plucks_conserve_outputs(self):
  for adults in [(0,0,1),(1,1,1),(5,10,15),(0,7,15)]:
   with self.subTest(adults=adults):r.assess_ivory_outputs(self.sample(adults))
 def test_exact_order_budget_source_fields(self):
  for key,value in [('uid','28'),('red','14'),('spent','4'),('natural_outputs','4'),('white_heads','4'),('white_adults','1'),('white_heads','-1'),('white_adults','-1'),('white_adults','01'),('white_adults','+0'),('white_adults','NaN')]:
   buds=self.sample();buds[0][key]=value
   with self.subTest(key=key,value=value),self.assertRaises(ValueError):r.assess_ivory_outputs(buds)
 def test_missing_extra_or_duplicate_source_refuses(self):
  buds=self.sample()
  for variant in [buds[:2],buds+[buds[0]],list(reversed(buds))]:
   with self.subTest(variant=variant),self.assertRaises(ValueError):r.assess_ivory_outputs(variant)
  for key in ('white_adults','white_heads','spent'):
   variant=copy.deepcopy(buds);del variant[0][key]
   with self.subTest(key=key),self.assertRaises(ValueError):r.assess_ivory_outputs(variant)
  buds[0]['extra']='1'
  with self.assertRaises(ValueError):r.assess_ivory_outputs(buds)
 def test_adult_loss_between_milestones_refuses(self):
  with self.assertRaises(ValueError):r.assess_ivory_outputs(self.sample((1,0,1)))
if __name__=='__main__':unittest.main()
