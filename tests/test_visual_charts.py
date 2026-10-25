import copy,math,unittest,xml.etree.ElementTree as ET
from companybench.visual_charts import render_visual
from companybench.insight import apply_chart_designs

class VisualTests(unittest.TestCase):
 def chart(self,template):return {'title':'测试 <数值> & 单位','unit':'元','rows':[{'label':'2020','a':2.4,'b':1.5},{'label':'2021','a':3.3,'b':2.1}],'series':[{'key':'a','label':'A'},{'key':'b','label':'B'}],'visual':{'template':template}}
 def test_svg_escaping_and_finite_geometry(self):
  for kind in ['rungs','paired','hairline','dumbbell','ribbon','composition','stem','plumb','waterfall']:
   ch=self.chart(kind)
   if kind=='composition':ch['rows']=ch['rows'][:1]
   if kind=='plumb':ch['visual'].update(x_key='a',y_key='b')
   if kind=='waterfall':ch['rows']=[{'label':'one','a':.3},{'label':'two','a':-.8},{'label':'sum','a':-.5}];ch['series']=ch['series'][:1]
   root=ET.fromstring(render_visual(ch));self.assertEqual(root.tag,'svg');self.assertEqual(root.find('title').text,ch['title'])
   for el in root.iter():
    for name in ['x','y','x1','y1','x2','y2','cx','cy','width','height']:
     if name in el.attrib:self.assertTrue(math.isfinite(float(el.attrib[name])))
 def test_fractional_rung_keeps_exact_endpoint(self):
  ch=self.chart('rungs');ch['rows']=ch['rows'][:1];ch['series']=ch['series'][:1];ch['visual'].update(orientation='horizontal',rung_unit=1)
  root=ET.fromstring(render_visual(ch));circle=root.find('circle');self.assertAlmostEqual(float(circle.attrib['cx']),235+2.4/(2.4*1.12)*(748-235));self.assertIn('2.40',ET.tostring(root,encoding='unicode'))
  ch['visual']['rung_unit']=.025;self.assertIn('0.025',ET.tostring(ET.fromstring(render_visual(ch)),encoding='unicode'))
 def test_hairline_gap_is_not_interpolated(self):
  ch=self.chart('hairline');ch['series']=ch['series'][:1];ch['rows']=[{'label':str(2020+i),'a':v} for i,v in enumerate([1,2,None,3,4])]
  root=ET.fromstring(render_visual(ch));self.assertEqual(len(root.findall('polyline')),2)
 def test_ribbon_rejects_missing_or_negative(self):
  for bad in [None,-1]:
   ch=self.chart('ribbon');ch['rows'][0]['a']=bad
   with self.assertRaises(ValueError):render_visual(ch)
 def test_definition_break_splits_ribbons(self):
  ch=self.chart('ribbon');ch['rows']=[{'label':str(y),'a':2,'b':3} for y in [2020,2021,2022,2023]];ch['visual']['break_at']=2022
  root=ET.fromstring(render_visual(ch));self.assertEqual(len(root.findall('path')),4)
 def test_inconsistent_contribution_bridge_stops(self):
  ch=self.chart('waterfall');ch['rows']=[{'label':'one','a':1},{'label':'two','a':2},{'label':'sum','a':8}];ch['series']=ch['series'][:1]
  with self.assertRaises(ValueError):render_visual(ch)
 def test_design_replay_does_not_override_numeric_data(self):
  chart=self.chart('rungs');chart.pop('visual');base={'chapters':[{'id':'x','charts':[chart]}],'forecast':{'keep':1}};designs={'designs':{chart['title']:{'template':'rungs'}},'new_charts':{}}
  out=apply_chart_designs(base,designs);self.assertEqual(apply_chart_designs(out,designs),out);self.assertEqual(out['chapters'][0]['charts'][0]['rows'],base['chapters'][0]['charts'][0]['rows']);self.assertEqual(out['forecast'],base['forecast'])
  changed=copy.deepcopy(chart);changed['rows'][0]['a']=99;designs['new_charts']={'x':[changed]}
  with self.assertRaisesRegex(ValueError,'覆盖既有数据'):apply_chart_designs(base,designs)
if __name__=='__main__':unittest.main()
