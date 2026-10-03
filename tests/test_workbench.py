"""Isolated synthetic fixtures. Never evidence or company results."""
from pathlib import Path
from unittest import TestCase,main,mock
from urllib.request import Request,urlopen
from urllib.error import HTTPError
import copy,json,shutil,tempfile,threading,zipfile,subprocess,sys,base64,struct
from companybench.cli import find_git
from companybench.core import ROOT,ReviewStore,WorkbenchError,create_project,import_sources,read_json,save_json,sha,validate_project,zip_members
from companybench.portal import make_server

class ProjectFixture(TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.base=Path(self.temp.name)
        self.project=create_project('合成测试公司',destination=self.base/'project')
        self.store=ReviewStore(self.project)
        self.source=self.base/'source.txt';self.source.write_text('合成夹具：本期120，上期100。\n',encoding='utf-8')
        self.sid=import_sources(self.project,self.source)[0]['id']
    def tearDown(self):self.temp.cleanup()
    def raw(self,rid='R1',value='120',period='2024',**scope):
        return {'id':rid,'kind':'disclosure','claim':'合成营业收入，非真实公司数据','value':value,
                'scope':{'period':period,'entity':'合成测试公司','basis':'合并','definition':'营业收入','unit':'元','currency':'CNY',**scope},
                'sources':[{'source_id':self.sid,'location':'合成文本第1行，本期或上期'}],'support_boundary':'仅供自动测试'}
    def confirm(self,rid):self.store.confirm(rid,'human-chat','合成测试中的明确确认，不是实际用户核验')
    def add_two(self):
        self.store.upsert(self.raw());self.store.upsert(self.raw('R2','100','2023'));self.confirm('R1');self.confirm('R2')
    def calc(self,rid='G1',op='growth',inputs=None,**extra):
        return {'id':rid,'kind':'derived','claim':'合成计算，非真实公司结果',
                'scope':{'period':'2024对2023','entity':'合成测试公司','basis':'合并','definition':'同比','unit':'%'},
                'formula':{'op':op,'inputs':inputs or ['R1','R2'],'precision':2,
                    'comparability':{k:True for k in ('version','period','currency_unit','entity','scope','definition','restatement')},**extra},
                'support_boundary':'测试算术，不支持经营因果'}

class EvidenceTests(ProjectFixture):
    def test_new_project_has_no_company_facts_or_delegation(self):
        other=create_project('独立合成项目',destination=self.base/'other')
        ledger=read_json(other/'evidence/ledger.json');self.assertEqual(ledger['records'],{});self.assertEqual(ledger['delegations'],[])
        self.assertEqual(ReviewStore(other).facts(),[])
    def test_import_preserves_bytes_and_repeat_deduplicates(self):
        original=self.source.read_bytes();source=self.store.source_rows()[0]
        self.assertEqual((self.project/source['path']).read_bytes(),original)
        self.assertEqual(import_sources(self.project,self.source),[])
    def test_candidate_alone_never_becomes_fact(self):
        self.store.upsert(self.raw());self.assertEqual(self.store.facts(),[])
        self.confirm('R1');self.assertEqual(len(self.store.facts()),1)
    def test_source_change_invalidates_old_confirmation(self):
        self.store.upsert(self.raw());self.confirm('R1')
        path=self.project/self.store.source_rows()[0]['path'];path.write_text('改动后的测试文件',encoding='utf-8')
        self.assertEqual(self.store.facts(),[])
        with self.assertRaises(WorkbenchError):self.confirm('R1')
    def test_candidate_revision_preserves_history_and_invalidates(self):
        self.store.upsert(self.raw());self.confirm('R1');self.store.upsert(self.raw(value='130'))
        self.assertEqual(self.store.facts(),[])
        actions=[e['action'] for e in self.store._read()['events']]
        self.assertIn('record-confirmed',actions);self.assertIn('candidate-revised',actions)
    def test_stale_screen_binding_rejected(self):
        self.store.upsert(self.raw());binding=self.store.records()[0]['binding'];self.store.upsert(self.raw(value='130'))
        with self.assertRaises(WorkbenchError):self.store.confirm('R1','human-ui',expected_binding=binding)
    def test_growth_rounding_and_input_withdrawal(self):
        self.add_two();self.store.upsert(self.calc());self.confirm('G1')
        result=next(r for r in self.store.facts() if r['id']=='G1');self.assertEqual(result['value'],'20.00')
        self.store.withdraw('R2','合成撤回')
        self.assertNotIn('G1',[r['id'] for r in self.store.facts()]);self.confirm('R2')
        self.assertNotIn('G1',[r['id'] for r in self.store.facts()])
        self.confirm('G1');self.assertIn('G1',[r['id'] for r in self.store.facts()])
    def test_unverified_input_and_zero_base_block_calculation_fact(self):
        self.store.upsert(self.raw());self.store.upsert(self.raw('R2','0','2023'));self.store.upsert(self.calc())
        with self.assertRaises(WorkbenchError):self.confirm('G1')
        self.confirm('R1');self.confirm('R2')
        with self.assertRaises(WorkbenchError):self.confirm('G1')
    def test_restatement_and_scope_mismatch_block_growth(self):
        self.add_two();self.store.upsert(self.calc(comparability={'restatement':False}))
        with self.assertRaises(WorkbenchError):self.confirm('G1')
        self.store.upsert(self.raw('R2','100','2023',basis='母公司'));self.confirm('R2');self.store.upsert(self.calc())
        with self.assertRaises(WorkbenchError):self.confirm('G1')
    def test_margin_and_price_use_matched_inputs_and_decimal_scale(self):
        self.store.upsert(self.raw('REVENUE','1000000','2024'));self.store.upsert(self.raw('COST','100000','2024',definition='营业成本'))
        self.store.upsert(self.raw('SALES','10','2024',definition='销量',unit='吨',currency=None))
        for rid in ('REVENUE','COST','SALES'):self.confirm(rid)
        self.store.upsert(self.calc('MARGIN','margin',['REVENUE','COST']));self.confirm('MARGIN')
        self.store.upsert(self.calc('PRICE','ratio',['REVENUE','SALES'],scale='0.0001'));self.confirm('PRICE')
        values={r['id']:r['value'] for r in self.store.facts()};self.assertEqual(values['MARGIN'],'90.00');self.assertEqual(values['PRICE'],'10.00')
    def test_blank_cell_does_not_silently_become_zero(self):
        blank=self.raw('BLANK');blank.pop('value');blank['blank_cell']=True;self.store.upsert(blank);self.confirm('BLANK')
        self.assertIsNone(self.store.facts()[0]['value'])
        self.store.upsert(self.calc('BZERO','blank-zero',['BLANK']));self.confirm('BZERO')
        self.assertEqual(next(r for r in self.store.facts() if r['id']=='BZERO')['value'],'0.00')
    def test_agent_authorization_is_required_and_revoke_invalidates(self):
        self.store.upsert(self.raw())
        with self.assertRaises(WorkbenchError):self.store.confirm('R1','agent','合成原文核查')
        did=self.store.delegate('合成授权，只用于测试')
        self.store.confirm('R1','agent','合成原文核查',did)
        fact=self.store.facts()[0];self.assertEqual(fact['verifier'],'agent');self.assertFalse(fact['human_confirmation'])
        self.store.revoke_delegation(did);self.assertEqual(self.store.facts(),[])
    def test_interpretation_never_automatically_becomes_fact(self):
        self.store.upsert({'id':'I1','kind':'interpretation','claim':'合成机制解释','support_boundary':'缺因果对照'})
        with self.assertRaises(WorkbenchError):self.store.confirm('I1','human-chat','合成认可')
        self.assertEqual(self.store.records()[0]['effective_state'],'Interpretation')
    def test_projection_and_event_tampering_are_detected(self):
        self.store.upsert(self.raw());self.confirm('R1');ledger=self.store._read();ledger['records']['R1']['value']='999';save_json(self.store.path,ledger)
        with self.assertRaises(WorkbenchError):self.store.facts()
    def test_report_content_signature_and_dependency_are_separate(self):
        self.add_two();self.store.review_ready(['R1']);self.store.approve_report('human-chat','合成报告审阅')
        self.assertTrue(self.store.report_approved());self.assertEqual(read_json(self.project/'project.json')['signature_status'],'pending')
        self.store.upsert(self.raw('UNRELATED','3','2022'));self.assertTrue(self.store.report_approved())
        self.store.withdraw('R1');self.assertFalse(self.store.report_approved())
    def test_agent_content_acceptance_needs_separate_authorization(self):
        self.store.review_ready([]);did=self.store.delegate('合成仅原文代理授权')
        with self.assertRaises(WorkbenchError):self.store.approve_report('agent','合成验收',did)
        did=self.store.delegate('合成内容代理授权',content=True);self.store.approve_report('agent','合成验收',did);self.assertTrue(self.store.report_approved())
    def test_moved_project_remains_source_bound_and_standalone(self):
        self.add_two();self.store.upsert(self.calc());self.confirm('G1')
        moved=self.base/'另一目录 中文 with spaces';shutil.copytree(self.project,moved,ignore=shutil.ignore_patterns('runtime','__pycache__'))
        self.assertEqual(len(ReviewStore(moved).facts()),3)
        process=subprocess.run([sys.executable,'workbench.py','status'],cwd=moved,capture_output=True,text=True,encoding='utf-8')
        self.assertEqual(process.returncode,0,process.stderr);self.assertEqual(json.loads(process.stdout)['facts'],3)
    def test_code_change_invalidates_only_derived_facts(self):
        self.add_two();self.store.upsert(self.calc());self.confirm('G1');real_sha=sha
        with mock.patch('companybench.core.sha',side_effect=lambda p:'0'*64 if Path(p).name=='core.py' else real_sha(p)):
            self.assertEqual({r['id'] for r in self.store.facts()},{'R1','R2'})
    def test_cannot_preset_fact_or_use_floating_point(self):
        r=self.raw();r['state']='Fact'
        with self.assertRaises(WorkbenchError):self.store.upsert(r)
        r=self.raw();r['value']=1.2
        with self.assertRaises(WorkbenchError):self.store.upsert(r)
    def test_missing_sources_invalidates_without_deleting_history(self):
        self.store.upsert(self.raw());self.confirm('R1');(self.project/self.store.source_rows()[0]['path']).unlink()
        self.assertEqual(self.store.facts(),[]);self.assertTrue(self.store.history_valid())
    def test_derived_unit_must_be_explicit(self):
        self.add_two();record=self.calc();record['scope'].pop('unit');self.store.upsert(record)
        with self.assertRaises(WorkbenchError):self.confirm('G1')
    def test_agent_content_acceptance_cannot_fake_user_click(self):
        self.store.review_ready([]);did=self.store.delegate('合成验收授权',content=True)
        with self.assertRaises(WorkbenchError):self.store.approve_report('agent',delegation_id=did)
        self.assertFalse(self.store.report_approved())

class GitTests(ProjectFixture):
    def run_cli(self,*args):
        return subprocess.run([sys.executable,'workbench.py',*args],cwd=self.project,capture_output=True,text=True,encoding='utf-8')
    def test_parent_repository_cannot_be_mistaken_for_project(self):
        git=find_git()
        if not git:self.skipTest('Git未安装，核心工作台仍可运行')
        subprocess.run([git,'init','-b','main',str(self.base)],check=True,capture_output=True)
        result=self.run_cli('git-save','--message','合成测试提交')
        self.assertNotEqual(result.returncode,0)
        self.assertFalse((self.project/'.git').exists())
        self.assertIn('不能误用父目录仓库',result.stderr)
    def test_independent_project_git_commit_without_push(self):
        git=find_git()
        if not git:self.skipTest('Git未安装，核心工作台仍可运行')
        result=self.run_cli('git-init');self.assertEqual(result.returncode,0,result.stderr)
        result=self.run_cli('git-save','--message','验证独立公司项目中文提交')
        self.assertEqual(result.returncode,0,result.stderr);self.assertFalse(json.loads(result.stdout)['pushed'])
        result=subprocess.run([git,'-C',str(self.project),'ls-files'],capture_output=True,text=True,encoding='utf-8')
        self.assertIn('evidence/ledger.json',result.stdout);self.assertNotIn('runtime/',result.stdout)
        result=subprocess.run([git,'-C',str(self.project),'log','-1','--format=%s'],capture_output=True,text=True,encoding='utf-8')
        self.assertEqual(result.stdout.strip(),'验证独立公司项目中文提交')

class ArchiveTests(ProjectFixture):
    def test_zip_slip_blocks_before_adding_sources(self):
        path=self.base/'bad.zip'
        with zipfile.ZipFile(path,'w') as z:z.writestr('../outside.txt','bad')
        before=len(self.store.source_rows())
        with self.assertRaises(WorkbenchError):import_sources(self.project,path)
        self.assertEqual(len(self.store.source_rows()),before);self.assertFalse((self.base/'outside.txt').exists())
    def test_chinese_zip_member_is_registered_with_content_relationship(self):
        path=self.base/'材料.zip'
        with zipfile.ZipFile(path,'w') as z:z.writestr('任意名称/合同.md','# 合成合同\n仅测试，非真实条款。')
        added=import_sources(self.project,path);self.assertEqual(len(added),2)
        extracted=next(r for r in added if r['format']=='.md');self.assertEqual(extracted['original_name'],'任意名称/合同.md');self.assertIsNotNone(extracted['archive_id'])
    def test_legacy_gb_zip_name_is_recovered(self):
        path=self.base/'legacy.zip';name='合同.md';raw=name.encode('gb18030');placeholder='A'*len(raw)
        with zipfile.ZipFile(path,'w') as z:z.writestr(placeholder,'synthetic')
        data=path.read_bytes().replace(placeholder.encode(),raw);path.write_bytes(data)
        names=[name for info,name in zip_members(path)];self.assertEqual(names,['合同.md'])
    def test_symlink_and_drive_paths_blocked(self):
        for name,islink in [('C:/outside.txt',False),('link',True)]:
            path=self.base/('link.zip' if islink else 'drive.zip')
            with zipfile.ZipFile(path,'w') as z:
                info=zipfile.ZipInfo(name)
                if islink:info.create_system=3;info.external_attr=(0o120777<<16)
                z.writestr(info,'synthetic')
            with self.assertRaises(WorkbenchError):zip_members(path)

class PortalTests(ProjectFixture):
    def setUp(self):
        super().setUp();self.server=make_server(self.project);self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        self.url='http://127.0.0.1:'+str(self.server.server_address[1]);self.token=self.server.workbench_token
    def tearDown(self):
        self.server.shutdown();self.server.server_close();self.thread.join(timeout=2);super().tearDown()
    def request(self,path,data=None,token=True):
        headers={'Content-Type':'application/json','Origin':self.url}
        if token:headers['X-Workbench-Token']=self.token
        req=Request(self.url+path,data=json.dumps(data).encode() if data else None,headers=headers)
        with urlopen(req,timeout=5) as r:return r.status,r.read()
    def test_browser_confirm_source_and_report_flow(self):
        self.store.upsert(self.raw());rid=self.project.name
        state=json.loads(self.request('/api/state?project='+rid)[1]);r=state['selected']['records'][0]
        self.request('/api/confirm',{'project':rid,'id':'R1','binding':r['binding']})
        self.assertEqual(self.store.facts()[0]['verifier'],'human-ui')
        self.store.review_ready(['R1']);binding=self.store.report_binding();self.request('/api/approve',{'project':rid,'binding':binding})
        self.assertTrue(self.store.report_approved())
        content=self.request('/file?project='+rid+'&path=outputs/../evidence/facts.md')[1].decode();self.assertIn('当前来源绑定',content)
    def test_post_without_token_rejected(self):
        with self.assertRaises(HTTPError) as caught:self.request('/api/delegate',{'project':self.project.name},token=False)
        self.assertEqual(caught.exception.code,403)
    def test_file_traversal_rejected(self):
        with self.assertRaises(HTTPError):self.request('/file?project='+self.project.name+'&path=../../outside.txt')
    def test_browser_file_upload_and_qualified_authorization(self):
        self.request('/api/import',{'project':self.project.name,'files':[{'name':'new.txt','base64':base64.b64encode(b'synthetic second source').decode()}]})
        self.assertEqual(len(self.store.source_rows()),2)
        self.request('/api/delegate',{'project':self.project.name,'content':True})
        self.assertTrue(self.store._read()['delegations'][0]['content_acceptance'])

if __name__=='__main__':main(verbosity=2)
