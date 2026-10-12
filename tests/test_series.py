import csv,json,tempfile,unittest
from pathlib import Path
from companybench.series import profile_series,comparability_gaps,number
from companybench.cli import main
from contextlib import redirect_stdout,redirect_stderr
from io import StringIO

class SeriesTests(unittest.TestCase):
 def fixture(self,rows):
  tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);p=Path(tmp.name)/'source.csv'
  with p.open('w',encoding='utf-8-sig',newline='') as f:
   writer=csv.writer(f);writer.writerow(['time','id','index_name','value','rtime']);writer.writerows(rows)
  return p
 def test_cutoff_and_revision_time_are_separate(self):
  p=self.fixture([['2024-12-31','A','X','1','2025-03-01'],['2025-12-31','A','X','2','2026-01-01']])
  r=profile_series(p,'2024-12-31');self.assertEqual(r['included_by_observation_date'],1);self.assertEqual(r['included_rows_updated_after_cutoff'],1);self.assertEqual(r['after_observation_cutoff'],1);self.assertFalse(r['fact_confirmation'])
 def test_conflicts_are_preserved(self):
  r=profile_series(self.fixture([['2024-01-01','A','X','1',''],['2024-01-01','A','X','2','']]))
  self.assertEqual(r['conflicting_records'],1);self.assertEqual(r['records'],2)
 def test_multiline_and_quoted_fields_keep_source_line(self):
  r=profile_series(self.fixture([['2024-01-01','A','X,\nY','1',''],['2024-01-02','A','X,\nY','2','']]))
  self.assertEqual(r['catalog'][0]['last_line'],4)
 def test_zero_missing_and_scientific_notation(self):
  self.assertEqual(number('0'),0);self.assertIsNone(number(''));self.assertEqual(number('1E3'),1000);self.assertIsNone(number('NaN'))
 def test_missing_units_and_definition_block_comparison(self):
  self.assertIn('缺少unit',comparability_gaps({},{}));self.assertIn('缺少definition',comparability_gaps({},{}))
 def test_different_price_layers_are_not_comparable(self):
  a=dict.fromkeys(['unit','currency','period_basis','market_scope','product_scope','price_layer','definition'],'same');b={**a,'price_layer':'other'}
  self.assertEqual(comparability_gaps(a,b),['price_layer不同'])
 def test_new_project_includes_unfilled_series_definition(self):
  from companybench.core import create_project
  tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
  project=create_project('合成公司',destination=Path(tmp.name)/'project')
  self.assertTrue((project/'work/series-definition.md').is_file())
  self.assertIn('Unknown',(project/'work/series-definition.md').read_text(encoding='utf8'))
 def test_source_is_unchanged(self):
  p=self.fixture([['2024-01-01','A','X','1','']]);before=p.read_bytes();r=profile_series(p);self.assertEqual(before,p.read_bytes());self.assertTrue(r['source_unchanged']);self.assertFalse(r['unit_metadata_present'])
 def test_cli_cannot_overwrite_source_or_existing_result(self):
  p=self.fixture([['2024-01-01','A','X','1','']]);out=p.with_suffix('.json');out.write_text('old')
  with redirect_stdout(StringIO()),redirect_stderr(StringIO()):
   self.assertEqual(main(['series-audit','--source',str(p),'--output',str(p)]),1)
   self.assertEqual(main(['series-audit','--source',str(p),'--output',str(out)]),1)
  self.assertEqual(out.read_text(),'old')
