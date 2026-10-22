import unittest,tempfile
from pathlib import Path
from companybench.materials import proxy_gate,material_view,materials_report
class MaterialTests(unittest.TestCase):
 def test_no_grade_creates_fact_or_closes_gap(self):
  for level in ['S0','S1','S2','S3','S4']:
   result=proxy_gate(level,'真实需求','公司出货');self.assertFalse(result['can_close_gap']);self.assertNotEqual(result['state'],'Fact')
 def test_invalid_grade_rejected(self):self.assertRaises(ValueError,proxy_gate,'HV','需求','原值')
 def test_blank_company_has_no_other_company_material(self):
  with tempfile.TemporaryDirectory() as p:self.assertEqual(material_view(Path(p))['files'],[])
 def test_report_keeps_failed_comparison_visible(self):
  self.assertIn('待排差',materials_report({'reproductions':[{'package':'合成包','csv_match':False,'html_status':'内容差异待核'}]}))
if __name__=='__main__':unittest.main()
