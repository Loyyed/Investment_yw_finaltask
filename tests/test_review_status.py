"""Synthetic project statuses only; no real approvals or fact events."""
from pathlib import Path
import tempfile,unittest,subprocess,sys,json
from companybench.review_status import current_reviews
from companybench.workflow import report_text,report_fingerprint

class ReviewStatusTests(unittest.TestCase):
 def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);(self.root/'scripts').mkdir();(self.root/'evidence').mkdir()
 def tearDown(self):self.tmp.cleanup()
 def project(self,status):
  (self.root/'evidence/task67-content-review.json').write_text('{"status":"accepted-current"}',encoding='utf-8')
  (self.root/'scripts/task67_content_review.py').write_text('def current_p04_adoption(root):\n return '+repr({'status':status,'new_signature_created':False,'contracts_formally_closed':False})+'\n',encoding='utf-8')
 def state(self,reviews):return {'settings':{'company':'合成公司'},'counts':{'Fact':0,'Unknown':0},'records':[],'sources':[],'mode':'legacy','content_reviews':reviews}
 def test_cached_acceptance_does_not_override_current_stale_validator(self):
  self.project('stale');reviews=current_reviews(self.root);self.assertEqual(reviews[0]['status'],'stale');self.assertIn('需重评',report_text(self.state(reviews)))
 def test_content_adoption_does_not_claim_signature_or_close(self):
  self.project('accepted-current');text=report_text(self.state(current_reviews(self.root)));self.assertIn('已认可',text);self.assertIn('未新增签署',text);self.assertIn('未正式关闭',text)
 def test_missing_validator_does_not_trust_ledger(self):
  (self.root/'evidence/task67-content-review.json').write_text('{"status":"accepted-current"}',encoding='utf-8');self.assertEqual(current_reviews(self.root)[0]['status'],'unavailable')
 def test_unlinked_project_does_not_inherit_reviews(self):self.assertEqual(current_reviews(self.root),[])
 def test_standalone_legacy_reader_runs_outside_toolkit_directory(self):
  self.project('accepted-current')
  methods=['list_candidates','facts','change_facts','lec03_agent_facts','m01_scale_facts','m01_metric_facts','m01_disclosure_facts']
  stub='class ReviewStore:\n def __init__(self,root):pass\n'+''.join(' def '+name+'(self):return []\n' for name in methods)
  (self.root/'scripts/review_store.py').write_text(stub,encoding='utf-8')
  (self.root/'work').mkdir();(self.root/'outputs').mkdir()
  (self.root/'work/task07-narrative-audit.md').write_text('Synthetic current narrative',encoding='utf-8')
  (self.root/'outputs/lec03-final-results.md').write_text('Synthetic historical narrative',encoding='utf-8')
  reader=Path(__file__).resolve().parents[1]/'companybench/legacy_reader.py'
  run=subprocess.run([sys.executable,str(reader),str(self.root)],cwd=self.root,capture_output=True,text=True,encoding='utf-8',timeout=30)
  self.assertEqual(run.returncode,0,run.stdout+run.stderr);data=json.loads(run.stdout)
  self.assertEqual(data['records'],[]);self.assertEqual(data['content_reviews'][0]['status'],'accepted-current');self.assertFalse(data['content_reviews'][0]['formally_closed']);self.assertEqual(data['research_sections']['narrative']['path'],'work/task07-narrative-audit.md');self.assertIn('Synthetic current narrative',data['research_sections']['narrative']['content'])
 def test_overlapping_authority_domains_are_not_reported_as_unique_facts(self):
  state=self.state([]);state['counts']['Fact']=6;state['domains']={'facts':4,'change_facts':2}
  text=report_text(state);self.assertIn('原披露有效Fact 4项',text);self.assertIn('不合计独立事实条数',text);self.assertNotIn('当前有效Fact 6条',text)
 def test_review_state_changes_report_fingerprint(self):
  a=self.state([{'id':'P04','label':'合成内容','status':'accepted-current','source':'evidence/synthetic.json','new_signature_created':False,'formally_closed':False}]);b=self.state([{**a['content_reviews'][0],'status':'stale'}]);self.assertNotEqual(report_fingerprint(a),report_fingerprint(b))

if __name__=='__main__':unittest.main()
