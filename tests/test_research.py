import json
from pathlib import Path
import tempfile
import unittest
from companybench.core import create_project
from companybench.research import research_summary


class ResearchNavigationTests(unittest.TestCase):
    def test_fresh_project_does_not_approve_from_template_presence(self):
        with tempfile.TemporaryDirectory() as d:
            p = create_project('合成公司', destination=Path(d)/'company')
            summary = research_summary(p, [])
            self.assertTrue(summary['configured'])
            self.assertEqual(6, len(summary['stages']))
            self.assertTrue(all(s['work_status'] == '未开始' for s in summary['stages']))
            self.assertFalse(json.loads((p/'work/report-scope.json').read_text('utf8'))['ready'])
            self.assertEqual([], json.loads((p/'evidence/ledger.json').read_text('utf8'))['events'])

    def test_invalid_current_fact_blocks_readiness_after_completed_draft(self):
        with tempfile.TemporaryDirectory() as d:
            p = create_project('合成公司', destination=Path(d)/'company')
            f = p/'work/research-navigation.json'
            plan = json.loads(f.read_text('utf8'))
            plan['stages'][0].update(work_status='底稿完成', record_ids=['N01'])
            f.write_text(json.dumps(plan), encoding='utf8')
            good = research_summary(p, [{'id':'N01','effective_state':'Fact'}])
            bad = research_summary(p, [{'id':'N01','effective_state':'Unknown'}])
            self.assertEqual([], good['stages'][0]['ineffective_record_ids'])
            self.assertEqual(['N01'], bad['stages'][0]['ineffective_record_ids'])
            self.assertEqual('依据需重核', bad['stages'][0]['readiness'])

    def test_missing_artifact_and_escaping_path_are_not_available_links(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            (p/'work').mkdir()
            (p/'work/research-navigation.json').write_text(json.dumps({'stages':[
                {'id':'a','title':'a','files':['absent.md','../outside.md']}
            ]}), encoding='utf8')
            s = research_summary(p, [])['stages'][0]
            self.assertEqual('文件待准备', s['readiness'])
            self.assertEqual('', s['files'][1]['path'])
            self.assertTrue(all(not f['exists'] for f in s['files']))

    def test_legacy_project_read_does_not_generate_or_mutate_plan(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertFalse(research_summary(d, [])['configured'])
            self.assertEqual([], list(Path(d).iterdir()))

if __name__ == '__main__':
    unittest.main()
