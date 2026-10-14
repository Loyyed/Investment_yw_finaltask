import unittest,tempfile,json
from pathlib import Path
from companybench.core import WorkbenchError
from companybench.methods import template,save_plan,plan_view,plan_report
from companybench.workflow import report_fingerprint

class MethodsTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
  self.rows=[{'id':'A','claim':'原披露收入','value':'123.45','scope':{'unit':'人民币元'},'effective_state':'Fact','binding':'first','support_boundary':'仅原数'}]
  self.p=template();self.p['nodes'][0].update({'evidence_ids':['A'],'interpretation':'解释','alternative':'其他机制','refutation':'可观察反证'})
 def tearDown(self):self.tmp.cleanup()
 def test_plan_does_not_write_fact_or_signature(self):
  save_plan(self.root,self.p,self.rows,'Agent')
  self.assertFalse((self.root/'evidence').exists());self.assertEqual(plan_view(self.root,self.rows)['nodes'][0]['state'],'Interpretation')
 def test_source_change_marks_unknown(self):
  save_plan(self.root,self.p,self.rows);changed=[{**self.rows[0],'binding':'second'}]
  node=plan_view(self.root,changed)['nodes'][0];self.assertFalse(node['evidence_ready']);self.assertEqual(node['state'],'Unknown');self.assertTrue(node['issues'])
 def test_withdrawn_fact_not_used(self):
  save_plan(self.root,self.p,self.rows);v=plan_view(self.root,[{**self.rows[0],'effective_state':'Unknown'}]);self.assertEqual(v['nodes'][0]['valid_evidence_ids'],[])
 def test_post_cutoff_source_not_historical_evidence(self):
  self.p.update({'analysis_mode':'历史时点决策','information_cutoff':'2024-12-31'});self.p['nodes'][0]['source_date']='2025-04-03'
  save_plan(self.root,self.p,self.rows);self.assertFalse(plan_view(self.root,self.rows)['nodes'][0]['evidence_ready'])
 def test_unknown_availability_stops_historical_use(self):
  self.p.update({'analysis_mode':'历史时点决策','information_cutoff':'2024-12-31'})
  save_plan(self.root,self.p,self.rows);self.assertFalse(plan_view(self.root,self.rows)['nodes'][0]['evidence_ready'])
 def test_forecast_never_becomes_fact_from_raw_link(self):
  self.p['parameters']=[{'id':'P','type':'预测参数','label':'WACC','value':'8','record_id':'A'}]
  save_plan(self.root,self.p,self.rows);self.assertNotEqual(plan_view(self.root,self.rows)['parameters'][0]['state'],'Fact')
 def test_fact_display_cannot_use_unverified_edited_amount(self):
  self.p['parameters']=[{'id':'P','type':'原值','label':'其他指标','value':'999','record_id':'A'}]
  save_plan(self.root,self.p,self.rows);q=plan_view(self.root,self.rows)['parameters'][0]
  self.assertEqual(q['value'],'123.45');self.assertEqual(q['label'],'原披露收入');self.assertEqual(q['unit'],'人民币元')
 def test_history_and_unknown_no_defaults(self):
  save_plan(self.root,self.p,self.rows);self.p['nodes'][0]['unknown']='新缺口';save_plan(self.root,self.p,self.rows)
  self.assertEqual(len(list((self.root/'work/research-plan-history').glob('*.json'))),1)
  self.assertEqual(plan_view(self.root,self.rows)['nodes'][1]['state'],'Unknown')
  self.assertIn('新缺口',plan_report(plan_view(self.root,self.rows)))
 def test_unknown_record_and_invalid_date_rejected(self):
  self.p['nodes'][0]['evidence_ids']=['OTHER'];self.assertRaises(WorkbenchError,save_plan,self.root,self.p,self.rows)
  self.p['nodes'][0]['evidence_ids']=['A'];self.p['information_cutoff']='not-date';self.assertRaises(WorkbenchError,save_plan,self.root,self.p,self.rows)

if __name__=='__main__':unittest.main()
