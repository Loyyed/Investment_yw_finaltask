"""Synthetic model invariants only; no company records or authorizations."""
import json,tempfile,unittest
from pathlib import Path
from companybench.insight import forecast,read_spec

class InsightTests(unittest.TestCase):
 def model(self):
  return {'years':[2030,2031,2032],'baseline':{'year':2029,'mt_volume':'10','mt_asp':'20','sr_volume':'5','sr_asp':'10','gross_margin':'.8','other_revenue':'50','net_profit':'100','selling_expense':'30','company_revenue':'300'},'scenarios':{'base':{'mt_q':[0,0,0],'mt_p':[0,0,0],'sr_q':[0,0,0],'sr_p':[0,0,0],'gm_delta':[0,0,0],'selling_rate':[.1,.1,.1],'retention':[.6,.6,.6],'cash_ratio':[1,1,1]}}}
 def test_zero_changes_keep_baseline(self):
  for r in forecast(self.model(),'base'):self.assertEqual(float(r['revenue']),300);self.assertEqual(float(r['net_profit_bridge']),100)
 def test_fee_shock_preserves_revenue_reduces_profit(self):
  r=forecast(self.model(),'base',{'selling_rate':.2})[0];self.assertEqual(float(r['revenue']),300);self.assertEqual(float(r['net_profit_bridge']),82)
 def test_product_volume_propagates_to_next_year(self):
  r=forecast(self.model(),'base',{'mt_q':.1});self.assertEqual([float(x['revenue']) for x in r],[320,320,320]);self.assertEqual(float(r[0]['net_profit_bridge']),108.4)
 def test_invalid_percentages_stop(self):
  for v in [{'mt_p':-1},{'selling_rate':1.1},{'unrecognized':0}]:
   with self.assertRaises(ValueError):forecast(self.model(),'base',v)
 def test_project_pointer_cannot_escape(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);(p/'index.json').write_text(json.dumps({'spec_path':'../secret.json'}))
   with self.assertRaises(ValueError):read_spec(p,'index.json')
if __name__=='__main__':unittest.main()
