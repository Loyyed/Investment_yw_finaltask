import unittest,json
from fractions import Fraction as F
from companybench.research_depth import revenue_bridge,valuation_audit,knowledge,knowledge_page
class Depth(unittest.TestCase):
 def setUp(self):
  self.b={'A':{'quantity':'10','revenue':'100'},'B':{'quantity':'10','revenue':'20'}}
  self.a={'A':{'quantity':'5','revenue':'50'},'B':{'quantity':'15','revenue':'30'}}
 def test_pure_mix(self):
  r=revenue_bridge(self.b,self.a);self.assertEqual(r['aggregate']['volume'],'0');self.assertEqual(r['aggregate']['within_product_asp'],'0');self.assertEqual(r['aggregate']['product_mix'],'-40')
 def test_pure_volume(self):
  a={k:{'quantity':str(int(v['quantity'])*2),'revenue':str(int(v['revenue'])*2)} for k,v in self.b.items()};r=revenue_bridge(self.b,a);self.assertEqual(r['aggregate']['volume'],'120');self.assertEqual(r['aggregate']['product_mix'],'0')
 def test_unit_invariance(self):
  a={k:{'quantity':str(int(v['quantity'])*1000),'revenue':v['revenue']} for k,v in self.a.items()};b={k:{'quantity':str(int(v['quantity'])*1000),'revenue':v['revenue']} for k,v in self.b.items()};self.assertEqual(revenue_bridge(b,a)['aggregate'],revenue_bridge(self.b,self.a)['aggregate'])
 def test_label_order(self):self.assertEqual(revenue_bridge(dict(reversed(list(self.b.items()))),self.a)['aggregate'],revenue_bridge(self.b,self.a)['aggregate'])
 def test_ineligible_data(self):
  for v in [None,'NaN','Infinity',0,-1,1.5,True]:
   a={'A':{'quantity':v,'revenue':'1'}}
   with self.assertRaises(ValueError):revenue_bridge(a,a)
 def test_category_mismatch(self):
  with self.assertRaises(ValueError):revenue_bridge(self.b,{'C':{'quantity':'1','revenue':'1'}})
 def test_discount_claim_pairing(self):
  m=dict(basis='FCFF',discount_basis='CostOfEquity',r='.08',g='.03',cashflow_defined=True,reinvestment_defined=True,financial_scope_defined=True,asof_defined=True);self.assertFalse(valuation_audit(m)['eligible']);m['discount_basis']='WACC';self.assertTrue(valuation_audit(m)['eligible']);m['g']='.08';self.assertFalse(valuation_audit(m)['eligible'])
 def test_missing_inputs_stop(self):self.assertFalse(valuation_audit({})['eligible'])
 def test_knowledge_provenance(self):
  self.assertEqual(len(knowledge()),20);self.assertTrue(knowledge('收入'));self.assertTrue(all(c['source'] and c['stop'] for c in knowledge()));page=knowledge_page('abc');self.assertIn('nonce="abc"',page);self.assertEqual(page.count('<article'),20)
if __name__=='__main__':unittest.main()
