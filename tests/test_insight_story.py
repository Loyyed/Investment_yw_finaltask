"""Editorial composition must not rewrite model or numerical evidence."""
import copy,unittest
from companybench.insight import apply_story_enrichment

class StoryTests(unittest.TestCase):
 def base(self):return {'chapters':[{'id':'one','blocks':[],'charts':[{'title':'original','rows':[{'v':1}],'series':[{'key':'v'}],'unit':'元'}]},{'id':'forecast','blocks':[],'charts':[]}],'forecast':{'years':[2030],'assumptions':[1]},'forecast_results':{'value':2},'sources':[],'authority':[{'domain':'facts','id':'A','record_digest':'old'}],'dependencies':[]}
 def overlay(self):return {'chapter_updates':{'one':{'story_beats':[{'title':'why','text':'process'}],'transition':{'target':'topic'},'append_blocks':[{'title':'new','paragraphs':['reason']}]}},'new_chapters':[{'id':'topic','blocks':[],'charts':[]}],'insert_before':'forecast','sources':[],'authority':[],'dependencies':[]}
 def test_idempotent_and_no_input_mutation(self):
  base=self.base();original=copy.deepcopy(base);overlay=self.overlay();out=apply_story_enrichment(base,overlay)
  self.assertEqual(base,original);self.assertEqual(apply_story_enrichment(out,overlay),out);self.assertEqual([c['id'] for c in out['chapters']],['one','topic','forecast']);self.assertEqual(out['forecast'],base['forecast']);self.assertEqual(out['forecast_results'],base['forecast_results']);self.assertEqual(out['chapters'][0]['charts'],base['chapters'][0]['charts'])
 def test_reject_changed_original_chart(self):
  overlay=self.overlay();overlay['chapter_updates']['one']['append_charts']=[{'title':'original','rows':[{'v':999}],'series':[{'key':'v'}],'unit':'元'}]
  with self.assertRaisesRegex(ValueError,'覆盖原图数值'):apply_story_enrichment(self.base(),overlay)
 def test_reject_silent_rebinding(self):
  overlay=self.overlay();overlay['authority']=[{'domain':'facts','id':'A','record_digest':'replacement'}]
  with self.assertRaisesRegex(ValueError,'依据编号冲突'):apply_story_enrichment(self.base(),overlay)
 def test_missing_chapter_rejected(self):
  overlay=self.overlay();overlay['chapter_updates']['absent']={}
  with self.assertRaisesRegex(ValueError,'章节不存在'):apply_story_enrichment(self.base(),overlay)
if __name__=='__main__':unittest.main()
