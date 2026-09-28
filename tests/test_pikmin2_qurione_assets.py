import copy, unittest
from experimental.pikmin2_qurione_assets import validate, EXPECTED
from experimental.pikmin2_breadbug_assets import parameter_blocks
from experimental.pikmin2_sheargrub_assets import animation_rows
class QurioneTests(unittest.TestCase):
    def test_contract(self):
        rows=[dict(file=f,events=e) for f,e in EXPECTED];names=['water','body_jnt2'];params=[{}, {},dict.fromkeys(['fp01','fp02','fp03','fp04','fp05'],1)]
        validate(rows,names,params,4)
        for limit in (True,1,9):
            with self.assertRaises(ValueError):validate(rows,names,params,limit)
        for bad in ([],['water','water','body_jnt2']):
            with self.assertRaises(ValueError):validate(rows,bad,params,4)
        changed=copy.deepcopy(rows);changed[1]['events']=[[6,2]]
        with self.assertRaises(ValueError):validate(changed,names,params,4)
        with self.assertRaises(ValueError):validate(rows,names,params[:2],4)
    def test_malformed_registration(self):
        for raw in ('1 { x damage.bca 5 -1 }','2 { x damage.bca -1 }'):
            with self.assertRaises(ValueError):animation_rows(raw)
    def test_nonfinite_parameter(self):
        with self.assertRaises(ValueError):parameter_blocks(b'{ {fp01} 4 nan {_eof} }')
if __name__=='__main__':unittest.main()
