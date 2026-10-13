"""Synthetic fixtures only; no real company confirmations."""
import json,threading,unittest,tempfile
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.error import HTTPError
from companybench.core import create_project,import_sources,ReviewStore,WorkbenchError,read_json,save_json
from companybench.portal import make_server
from companybench.workspace import selected_state,link_project
from companybench.workflow import scenario,generate_report,save_draft,model_current,save_contracts,record_signature

class WorkflowTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.base=Path(self.tmp.name)
  self.p=create_project('合成测试公司','TEST','general',destination=self.base/'company');self.s=ReviewStore(self.p)
  path=self.base/'synthetic.txt';path.write_text('Synthetic testing only.',encoding='utf-8');self.source=import_sources(self.p,path)[0]['id']
  for rid,value,period in [('R1','120','2024'),('R2','100','2023')]:
   self.s.upsert({'id':rid,'kind':'disclosure','claim':'合成FCFF测试数据','value':value,'sources':[{'source_id':self.source,'location':'第1行'}],
    'scope':{'period':period,'entity':'合成公司','basis':'合并','definition':'FCFF','unit':'元','currency':'CNY'}})
   self.s.confirm(rid,'human-chat','合成测试确认，不是真实用户确认')
  self.entry={'path':self.p,'mode':'generic'}
 def tearDown(self):self.tmp.cleanup()
 def model(self,**kw):return {'name':'合成情景','base_id':'R2','years':'2','growth':'10','wacc':'10','terminal_growth':'0','net_debt':'0','shares':'10','assumption_note':'合成测试假设，不是真实估值','fcff_definition_confirmed':True,**kw}
 def test_decimal_dcf_and_assumption_state(self):
  m=scenario(self.p,self.model());self.assertEqual(m['kind'],'Forecast');self.assertEqual(m['result']['display_per_share'],'120.00')
  self.assertEqual(len(self.s.facts()),2);self.assertEqual(len(m['flows']),2)
 def test_dcf_rejects_wrong_unit_and_unexplained_assumptions(self):
  for kw in [{'wacc':'0'},{'terminal_growth':'10'},{'shares':'0'},{'assumption_note':''},{'fcff_definition_confirmed':False}]:
   with self.assertRaises(WorkbenchError):scenario(self.p,self.model(**kw))
  self.s.upsert({'id':'R3','kind':'disclosure','claim':'亿元测试','value':'1','sources':[{'source_id':self.source,'location':'1'}],
    'scope':{'period':'2024','entity':'合成公司','basis':'合并','definition':'FCFF','unit':'亿元','currency':'CNY'}})
  self.s.confirm('R3','human-chat','合成测试')
  with self.assertRaises(WorkbenchError):scenario(self.p,self.model(base_id='R3'))
 def test_base_withdrawal_invalidates_scenario(self):
  m=scenario(self.p,self.model());self.assertTrue(model_current(m,self.s.records()));self.s.withdraw('R2','测试撤回')
  self.assertFalse(model_current(m,self.s.records()))
 def test_report_versions_unknown_and_content_binding(self):
  old=(self.p/'outputs/analysis-report.md').read_bytes();state=selected_state(self.entry,self.p.name)
  report=generate_report(self.base,self.entry,state);text=Path(report['md']).read_text(encoding='utf-8')
  self.assertIn('Unknown：本部分尚无研究意见',text);self.assertEqual((self.p/'outputs/analysis-report.md').read_bytes(),old)
  self.s.approve_report('human-chat','合成测试内容审阅');self.assertTrue(self.s.report_approved())
  self.s.withdraw('R1','合成测试撤回');self.assertFalse(self.s.report_approved())
  next_report=generate_report(self.base,self.entry,selected_state(self.entry,self.p.name));self.assertNotEqual(report['md'],next_report['md']);self.assertTrue(Path(report['md']).exists())
 def test_draft_and_opinion_do_not_promote_fact(self):
  save_draft(self.p,{'summary':'合成意见','sections':{'business':'合成经营解释'}})
  self.s.upsert({'id':'I1','kind':'interpretation','claim':'合成解释','evidence_ids':['R1'],'challenge':'缺反证'})
  self.assertEqual(len(self.s.facts()),2);text=generate_report(self.base,self.entry,selected_state(self.entry,self.p.name))
  self.assertIn('Interpretation',Path(text['md']).read_text(encoding='utf-8'))
 def test_contract_file_presence_not_a_fact(self):
  save_contracts(self.p,{'contracts':[{'name':'合成合同','source_id':self.source,'clauses':[{'id':'C1','requirement':'亲自检查原文','status':'待完成','checked':False,'evidence':['work/claim-notes.md']}]}]})
  self.assertFalse(read_json(self.p/'work/workbench-contracts.json')['contracts'][0]['clauses'][0]['checked']);self.assertEqual(len(self.s.facts()),2)
 def test_project_link_preserves_ledger_and_no_authorization_inheritance(self):
  before=(self.p/'evidence/ledger.json').read_bytes();key=link_project(self.base,self.p,'合成公司');self.assertTrue(key.startswith('linked-'))
  self.assertEqual((self.p/'evidence/ledger.json').read_bytes(),before)
  q=create_project('另一合成公司','','general',destination=self.base/'another');self.assertEqual(ReviewStore(q).facts(),[])
 def test_html_escapes_untrusted_research(self):
  save_draft(self.p,{'summary':'<script>alert(1)</script>'});r=generate_report(self.base,self.entry,selected_state(self.entry,self.p.name))
  text=Path(r['html']).read_text(encoding='utf-8');self.assertNotIn('<script>',text);self.assertIn('&lt;script&gt;',text)
 def test_actual_signature_is_separate_and_source_bound(self):
  generate_report(self.base,self.entry,selected_state(self.entry,self.p.name));b=self.s.report_binding()
  data={'authorized':True,'executor':'合成执行人','reviewer':'合成执行人','date':'2026-10-13','binding':b}
  with self.assertRaises(WorkbenchError):record_signature(self.p,data)
  self.s.approve_report('human-chat','合成测试内容审阅');r=record_signature(self.p,data);self.assertTrue(r['same_person'])
  self.assertTrue(selected_state(self.entry,self.p.name)['current_signature']);self.s.withdraw('R1','合成撤回')
  self.assertFalse(selected_state(self.entry,self.p.name)['current_signature']);self.assertTrue(self.s.history_valid())

class WorkflowAPITests(WorkflowTests):
 def setUp(self):
  super().setUp();self.server=make_server(self.p);self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start();self.url='http://127.0.0.1:'+str(self.server.server_address[1])
 def tearDown(self):self.server.shutdown();self.server.server_close();self.thread.join(2);super().tearDown()
 def request(self,path,data=None):
  req=Request(self.url+path,data=json.dumps(data).encode() if data else None,headers={'Content-Type':'application/json','Origin':self.url,'X-Workbench-Token':self.server.workbench_token})
  with urlopen(req,timeout=10) as r:return r.read()
 def test_api_draft_model_report_download(self):
  self.request('/api/draft',{'project':self.p.name,'summary':'API合成测试意见'})
  self.request('/api/model',{'project':self.p.name,**self.model()})
  self.request('/api/report',{'project':self.p.name});body=self.request('/api/export?project='+self.p.name+'&format=md').decode('utf-8')
  self.assertIn('API合成测试意见',body);self.assertIn('Forecast',body)
 def test_record_cannot_preset_fact_through_api(self):
  with self.assertRaises(HTTPError):self.request('/api/record',{'project':self.p.name,'record':{'id':'BAD','claim':'合成','kind':'disclosure','state':'Fact'}})
 def test_assets_and_csp(self):
  self.assertIn(b'RESEARCH IN PROGRESS',self.request('/assets/ui.js'))
  self.assertIn(b'--green',self.request('/assets/ui.css'))
 def test_changed_draft_blocks_stale_report_export(self):
  self.request('/api/report',{'project':self.p.name});self.request('/api/draft',{'project':self.p.name,'summary':'新合成意见'})
  state=json.loads(self.request('/api/state?project='+self.p.name));self.assertTrue(state['selected']['report_stale'])
  with self.assertRaises(HTTPError):self.request('/api/export?project='+self.p.name+'&format=md')

if __name__=='__main__':unittest.main()
