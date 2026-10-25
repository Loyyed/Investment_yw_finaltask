"""Local SVG chart grammar inspired by supplied porcelain teaching figures.

Glyph count is decorative; endpoints and labels retain the exact input values.
No network, data review mutations or hidden statistical estimation.
"""
import html,math

INK='#081F5C';BLUE='#334EAC';MID='#7096D1';LIGHT='#BAD6EB';QUIET='#D0E3FF';PAPER='#F7F2EB';GRID='#dce3ec'
COLORS=[BLUE,LIGHT,MID,QUIET]
NAMES={'rungs':'F1 · 阶梯刻度','hairline':'F2 · 细线与年度点','paired':'F6 · 双列阶梯','dumbbell':'F12 · 哑铃对照','ribbon':'F16 · 构成条带','composition':'构成条带 · 单期转译','stem':'年度茎叶 · 离散观察','plumb':'F8 · 垂线散点','waterfall':'贡献桥 · 阶梯转译'}
def esc(x):return html.escape(str(x),quote=True)
def fmt(x,p=2):return f'{float(x):,.{p}f}'
def step_label(x):return fmt(x,0) if float(x).is_integer() else fmt(x,6).rstrip('0').rstrip('.')
def nice(x):
 if x<=0:return 1
 base=10**math.floor(math.log10(x));part=x/base
 return next((a*base for a in [1,2,2.5,5,10] if a>=part),10*base)

class SVG:
 def __init__(self,title,height=340):
  self.w=840;self.h=height;self.out=[f'<svg class="vis-svg" viewBox="0 0 840 {height}" role="img" aria-label="{esc(title)}"><title>{esc(title)}</title>']
 def line(self,x1,y1,x2,y2,color=GRID,width=1,**attrs):self.el('line',{'x1':x1,'y1':y1,'x2':x2,'y2':y2,'stroke':color,'stroke-width':width,**attrs})
 def text(self,x,y,value,size=15,color=INK,anchor='start',**attrs):self.el('text',{'x':x,'y':y,'font-size':size,'fill':color,'style':'fill:'+color+';font-size:'+str(size)+'px','text-anchor':anchor,**attrs},esc(value))
 def el(self,tag,attrs,content=None):
  a=' '.join(str(k).replace('_','-')+'="'+esc(v)+'"' for k,v in attrs.items());self.out.append('<'+tag+' '+a+('/>' if content is None else '>'+content+'</'+tag+'>'))
 def point(self,x,y,label,fill=BLUE,r=4,**attrs):self.el('circle',{'cx':x,'cy':y,'r':r,'fill':fill,'stroke':BLUE,'stroke-width':1.7,**attrs},'<title>'+esc(label)+'</title>')
 def end(self):return ''.join(self.out)+'</svg>'

def domain(ch,values,pad=.12):
 if ch.get('domain'):return map(float,ch['domain'])
 low=min(0,min(values));high=max(0,max(values));span=high-low or 1
 return (low-span*pad if low<0 else 0, high+span*pad if high>0 else span*.1)

def grids(s,lo,hi,left=72,right=806,top=36,bottom=266,precision=0):
 y=lambda v:bottom-(v-lo)/(hi-lo)*(bottom-top)
 for j in range(5):
  value=lo+(hi-lo)*j/4;yy=y(value);s.line(left,yy,right,yy);s.text(left-12,yy+5,fmt(value,precision),13,MID,'end')
 if lo<0:s.line(left,y(0),right,y(0),MID,1)
 return y

def rungs(ch):
 rows=ch['rows'];series=ch['series'];v=ch['visual'];orientation=v.get('orientation','vertical');allv=[float(r[k['key']]) for r in rows for k in series if r.get(k['key']) is not None]
 lo,hi=domain(ch,allv);unit=float(v.get('rung_unit') or nice(max(abs(x) for x in allv)/35));prec=ch.get('precision',2)
 if orientation=='horizontal':
  h=90+len(rows)*66;s=SVG(ch['title'],h);left,right=235,748;zero=left+(0-lo)/(hi-lo)*(right-left);scale=(right-left)/(hi-lo)
  s.line(zero,28,zero,h-55,GRID)
  for i,row in enumerate(rows):
   y=48+i*66;value=row.get(series[0]['key']);s.text(left-18,y+5,row['label'],17,INK,'end')
   if value is None:s.text(zero+8,y+5,'Unknown',14,MID);continue
   value=float(value);end=zero+value*scale;direction=1 if value>=0 else -1;n=int(abs(value)/unit)
   for k in range(1,n+1):x=zero+direction*k*unit*scale;s.line(x,y-12,x,y+12,BLUE,1.4,**{'class':'vis-mark'})
   s.line(zero,y,end,y,BLUE,.7);s.point(end,y,fmt(value,prec)+' '+ch['unit'],r=2.8)
   s.text(end+direction*12,y+5,fmt(value,prec),16,BLUE,'start' if value>=0 else 'end',**{'font-weight':700})
  s.text(28,h-14,'每条短线 '+step_label(unit)+' '+('个百分点' if ch['unit']=='%' else ch['unit'])+'；端点与标签保留精确值',13,MID)
  return s.end()
 s=SVG(ch['title']);left,right=70,802;bottom=266;top=38;y=grids(s,lo,hi,left,right,top,bottom,ch.get('axis_precision',0));step=(right-left)/len(rows)
 for i,row in enumerate(rows):
  center=left+(i+.5)*step
  for j,ser in enumerate(series):
   value=row.get(ser['key'])
   if value is None:continue
   value=float(value);x=center+(j-(len(series)-1)/2)*min(30,step/(len(series)+2));span=min(18,step/(len(series)+1)*.5);n=int(abs(value)/unit);direction=1 if value>=0 else -1;col=COLORS[j%4]
   for k in range(1,n+1):yy=y(direction*k*unit);s.line(x-span/2,yy,x+span/2,yy,col,1.4,**{'class':'vis-mark'})
   endpoint=y(value);s.line(x-span/2,endpoint,x+span/2,endpoint,col,2.4)
   if len(rows)*len(series)<=12:s.text(x,endpoint-12-j*23 if value>=0 else endpoint+20+j*23,fmt(value,prec),14,BLUE,'middle',**{'font-weight':700})
   s.el('circle',{'cx':x,'cy':endpoint,'r':9,'fill':'transparent'},'<title>'+esc(row['label']+' · '+ser['label']+' '+fmt(value,prec)+ch['unit'])+'</title>')
  label=str(row['label']);parts=label.split(' n')
  s.text(center,292,parts[0],14,INK,'middle')
  if len(parts)>1:s.text(center,312,'n='+parts[1],12,MID,'middle')
 s.text(72,333,'每阶 '+step_label(unit)+' '+('个百分点' if ch['unit']=='%' else ch['unit'])+' · 末阶按精确值定位',12,MID)
 return s.end()

def hairline(ch):
 rows=ch['rows'];series=ch['series'];v=ch['visual'];allv=[float(r[k['key']]) for r in rows for k in series if r.get(k['key']) is not None];lo,hi=domain(ch,allv);s=SVG(ch['title']);left,right=74,794;top,bottom=42,266;x=lambda i:left+i*(right-left)/max(1,len(rows)-1)
 def year(row):
  try:return int(str(row['label'])[:4])
  except ValueError:return 0
 boundaries=v.get('breaks',[]);boundary=v.get('break_at');post=v.get('post_period')
 if boundary:
  idx=next((i for i,r in enumerate(rows) if year(r)>=boundary),None)
  if idx is not None:
   a=max(left,x(idx)-((right-left)/max(1,len(rows)-1))/2);s.el('rect',{'x':a,'y':22,'width':right-a+12,'height':bottom-22,'fill':QUIET,'opacity':.42});s.text(a+9,34,str(boundary)+' 定义扩展后',12,MID)
 y=grids(s,lo,hi,left,right,top,bottom,ch.get('axis_precision',0))
 for j,ser in enumerate(series):
  col=COLORS[j%4];segment=[]
  def draw():
   if len(segment)>1:s.el('polyline',{'points':' '.join(segment),'fill':'none','stroke':col,'stroke-width':2,'pathLength':1,'class':'vis-draw'})
  for i,r in enumerate(rows):
   value=r.get(ser['key'])
   if value is None:draw();segment=[];continue
   yy=y(float(value));ispost=bool(post and year(r)>=post)
   if i and (boundary and year(r)>=boundary>year(rows[i-1]) or any(year(r)>=b>year(rows[i-1]) for b in boundaries) or ispost):
    draw();segment=[]
    if ispost and rows[i-1].get(ser['key']) is not None:s.line(x(i-1),y(float(rows[i-1][ser['key']])),x(i),yy,col,1.5,**{'stroke-dasharray':'4 5'})
   segment.append(f'{x(i)},{yy}');s.point(x(i),yy,str(r['label'])+' · '+ser['label']+' '+fmt(value,ch.get('precision',2))+ch['unit'],PAPER if ispost else col,r=4)
   if v.get('show_values',True) and (len(rows)<=6 or i in (0,len(rows)-1)):s.text(x(i),yy-15-j*12,fmt(value,ch.get('precision',2)),14,col,'middle')
  draw()
 for i,r in enumerate(rows):
  if i%v.get('tick_every',1)==0 or i==len(rows)-1:s.text(x(i),294,str(r['label']),13,INK,'middle')
 if v.get('reference_line') is not None:
  val=float(v['reference_line'])
  if lo<=val<=hi:s.line(left,y(val),right,y(val),MID,1,**{'stroke-dasharray':'3 5'});s.text(right,y(val)-8,'参考 '+str(val),12,MID,'end')
 return s.end()

def dumbbell(ch):
 rows=ch['rows'];series=ch['series'];v=ch['visual'];mode=v.get('pair_mode','series');pairs=[]
 if mode=='rows':
  if len(rows)!=2:raise ValueError('跨期哑铃需要两行数据')
  for ser in series:pairs.append((ser['label'],rows[0].get(ser['key']),rows[1].get(ser['key'])))
  names=[str(rows[0]['label']),str(rows[1]['label'])]
 else:
  if len(series)!=2:raise ValueError('分组哑铃需要两条数据系列')
  pairs=[(str(r['label']),r.get(series[0]['key']),r.get(series[1]['key'])) for r in rows];names=[x['label'] for x in series]
 values=[float(z) for _,a,b in pairs for z in (a,b) if z is not None];lo,hi=domain(ch,values,.15);left,right=245,735;xx=lambda x:left+(float(x)-lo)/(hi-lo)*(right-left);height=150+len(pairs)*65;s=SVG(ch['title'],height)
 s.text(26,27,'空心：'+names[0]+'   实心：'+names[1],14,MID)
 for j in range(5):val=lo+(hi-lo)*j/4;x=xx(val);s.line(x,45,x,height-55,GRID);s.text(x,height-28,fmt(val,ch.get('axis_precision',0)),12,MID,'middle')
 for i,(name,a,b) in enumerate(pairs):
  y=74+i*65;s.text(left-20,y+5,name,16,INK,'end')
  if a is None or b is None:s.text(left,y+5,'Unknown',14,MID);continue
  xa,xb=xx(a),xx(b);s.line(xa,y,xb,y,MID,2,**{'class':'vis-mark'});s.point(xa,y,names[0]+' '+fmt(a,ch.get('precision',2))+ch['unit'],PAPER,6);s.point(xb,y,names[1]+' '+fmt(b,ch.get('precision',2))+ch['unit'],BLUE,5)
  s.text(xa,y-14,fmt(a,ch.get('precision',2)),14,BLUE,'middle');s.text(xb,y+25,fmt(b,ch.get('precision',2)),14,BLUE,'middle')
 s.text(28,height-3,ch['unit']+' · 横轴同一尺度；两点仅作并列对照',12,MID)
 return s.end()

def smooth_path(points):
 if not points:return ''
 out=[f'M{points[0][0]},{points[0][1]}']
 for (x1,y1),(x2,y2) in zip(points,points[1:]):mid=(x1+x2)/2;out.append(f'C{mid},{y1} {mid},{y2} {x2},{y2}')
 return ' '.join(out)

def ribbon(ch):
 rows=ch['rows'];series=ch['series'];s=SVG(ch['title']);left,right=115,795;cy=152
 if any(r.get(k['key']) is None or float(r[k['key']])<0 for r in rows for k in series):raise ValueError('缺失或负数不能构成连续条带')
 max_total=max(sum(float(r[k['key']]) for k in series) for r in rows)
 if max_total<=0:raise ValueError('构成条带需要正的总量')
 scale=210/max_total;xs=[left+i*(right-left)/max(1,len(rows)-1) for i in range(len(rows))];bounds=[]
 for row in rows:
  values=[float(row[k['key']]) for k in series];top=cy-sum(values)*scale/2;boundary=[top]
  for value in values:boundary.append(boundary[-1]+value*scale)
  bounds.append(boundary)
 split=ch['visual'].get('break_at');cut=next((i for i,r in enumerate(rows) if split and int(str(r['label'])[:4])>=split),None);groups=[list(range(len(rows)))] if cut is None or cut==0 else [list(range(cut)),list(range(cut,len(rows)))]
 for j,ser in enumerate(series):
  for group in groups:
   upper=[(xs[i],bounds[i][j]) for i in group];lower=[(xs[i],bounds[i][j+1]) for i in group];path=smooth_path(upper)+' L'+str(lower[-1][0])+','+str(lower[-1][1])+' '+smooth_path(list(reversed(lower)))[1:]+' Z'
   s.el('path',{'d':path,'fill':COLORS[j%4],'stroke':PAPER,'stroke-width':1.7,'class':'vis-area'},'<title>'+esc(ser['label']+'；厚度编码'+ch['unit'])+'</title>')
 if cut:
  seam=(xs[cut-1]+xs[cut])/2;s.line(seam,30,seam,272,MID,1,**{'stroke-dasharray':'3 5'});s.text(seam,18,str(split)+' 定义扩展',12,MID,'middle')
 for i,row in enumerate(rows):
  total=sum(float(row[k['key']]) for k in series);s.text(xs[i],bounds[i][0]-14,fmt(total,ch.get('precision',2)),12,BLUE,'middle');s.text(xs[i],292,row['label'],13,INK,'middle')
  s.el('circle',{'cx':xs[i],'cy':cy,'r':10,'fill':'transparent'},'<title>'+esc(str(row['label'])+' · '+'；'.join(k['label']+' '+fmt(row[k['key']],ch.get('precision',2)) for k in series))+'</title>')
 unit=nice(max_total/3);hh=unit*scale;s.line(55,cy-hh/2,55,cy+hh/2,MID,1.5);s.line(48,cy-hh/2,62,cy-hh/2,MID);s.line(48,cy+hh/2,62,cy+hh/2,MID);s.text(48,cy+hh/2+22,fmt(unit,0 if unit>=1 else 2),12,MID,'middle')
 s.text(28,327,'厚度编码数量/金额；上方为年度总量。'+('定义变化处断开，不代表零。' if cut else '曲线只连接年度观察。'),12,MID)
 return s.end()

def composition(ch):
 if len(ch['rows'])!=1:raise ValueError('单期构成需要一行数据')
 row=ch['rows'][0];series=ch['series'];values=[float(row[x['key']]) for x in series]
 if any(x<0 for x in values) or sum(values)<=0:raise ValueError('单期构成需要非负且总量为正')
 s=SVG(ch['title'],245);total=sum(values);x=44;full=752;s.text(44,32,str(row['label'])+' · 总量 '+fmt(total,ch.get('precision',2))+' '+ch['unit'],16,BLUE)
 for i,(ser,value) in enumerate(zip(series,values)):
  width=value/total*full;s.el('rect',{'x':x,'y':65,'width':max(.6,width),'height':58,'fill':COLORS[i%4],'class':'vis-area'},'<title>'+esc(ser['label']+' '+fmt(value,2)+ch['unit']+' / '+fmt(value/total*100,2)+'%')+'</title>')
  if width>110:s.text(x+width/2,102,fmt(value/total*100,2)+'%',21,PAPER if i==0 else INK,'middle',**{'font-weight':700})
  x+=width
 for i,(ser,value) in enumerate(zip(series,values)):
  x=44+i*full/len(series);s.line(x,156,x+18,156,COLORS[i%4],4);s.text(x+27,162,ser['label'],16);s.text(x,192,fmt(value,2)+' '+ch['unit'],17,BLUE);s.text(x,219,fmt(value/total*100,2)+'%',13,MID)
 return s.end()

def stem(ch):
 s=SVG(ch['title']);rows=ch['rows'];ser=ch['series'][0];values=[float(r[ser['key']]) for r in rows];lo,hi=domain(ch,values);left,right=78,793;bottom=266;y=grids(s,lo,hi,left,right,42,bottom,ch.get('axis_precision',0))
 for i,r in enumerate(rows):
  x=left+(i+.5)*(right-left)/len(rows);value=float(r[ser['key']]);yy=y(value);s.line(x,bottom,x,yy,LIGHT,2);s.point(x,yy,str(r['label'])+' '+fmt(value,2)+ch['unit'],BLUE,5);s.text(x,yy-17,fmt(value,2),15,BLUE,'middle');s.text(x,297,r['label'],15,INK,'middle')
 s.text(78,330,'各年独立观察 · 未跨口径连线',13,MID)
 return s.end()

def plumb(ch):
 v=ch['visual'];xkey=v['x_key'];ykey=v['y_key'];xd=v.get('x_domain',[0,55]);yd=v.get('y_domain',[0,6]);left,right,top,bottom=95,780,38,258;s=SVG(ch['title'],350);xx=lambda x:left+(float(x)-xd[0])/(xd[1]-xd[0])*(right-left);yy=lambda y:bottom-(float(y)-yd[0])/(yd[1]-yd[0])*(bottom-top)
 for i in range(4):
  a=xd[0]+(xd[1]-xd[0])*i/3;x=xx(a);s.line(x,top,x,bottom,GRID);s.text(x,285,fmt(a,1),13,MID,'middle');b=yd[0]+(yd[1]-yd[0])*i/3;y=yy(b);s.line(left,y,right,y,GRID);s.text(left-14,y+4,fmt(b,1),13,MID,'end')
 label_boxes=[]
 for r in ch['rows']:
  a,b=r.get(xkey),r.get(ykey)
  if a is None or b is None:continue
  x,y=xx(a),yy(b);post=int(str(r['label'])[:4])>=int(v.get('break_at',2022));color=BLUE if post else LIGHT;(None if v.get('simple') else s.line(x,bottom,x,y,color,.9,opacity=.6));s.point(x,y,str(r['label'])+'；X='+fmt(a,2)+'%；Y='+fmt(b,2)+'%',color,5)
  tx,ty=x+9,y-8
  for dx,dy in [(9,-8),(9,22),(-46,-8),(9,-28),(-46,22),(9,40)]:
   bx,by=x+dx,y+dy;box=(bx-2,by-14,bx+39,by+3)
   if box[0]<left or box[2]>right or box[1]<top or box[3]>bottom:continue
   if any(not (box[2]<a[0] or box[0]>a[2] or box[3]<a[1] or box[1]>a[3]) for a in label_boxes):continue
   tx,ty=bx,by;break
  label_boxes.append((tx-2,ty-14,tx+39,ty+3))
  if (tx,ty)!=(x+9,y-8):s.line(x,y,tx+3,ty-5,MID,.6)
  s.text(tx,ty,str(r['label']),13,BLUE)
 s.text(438,320,v.get('x_label','X'),16,INK,'middle');s.text(96,20,v.get('y_label','Y'),14,INK);s.text(438,345,'每个点为一个财年；不拟合因果线',12,MID,'middle')
 return s.end()

def waterfall(ch):
 vals=[float(r[ch['series'][0]['key']]) for r in ch['rows']]
 if len(vals)!=3 or not math.isclose(vals[0]+vals[1],vals[2],abs_tol=1e-8):raise ValueError('贡献桥需要两项贡献与一致的总变化')
 bounds=[0,vals[0],vals[2]];lo=min(bounds)*1.2;hi=max(bounds)*1.3
 if hi==lo:hi=lo+1
 s=SVG(ch['title']);y=grids(s,lo,hi,78,795,40,266,ch.get('axis_precision',1));xs=[195,430,665];width=84
 for i,value in enumerate(vals):
  a,b=(0,value) if i==2 else (bounds[i],bounds[i+1]);ya,yb=y(a),y(b);col=BLUE if i==2 else MID if value>=0 else LIGHT
  for yy in range(math.ceil(min(ya,yb)),math.floor(max(ya,yb)),5):s.line(xs[i]-width/2,yy,xs[i]+width/2,yy,col,1.7,**{'class':'vis-mark'})
  s.line(xs[i]-width/2,yb,xs[i]+width/2,yb,col,3);s.text(xs[i],min(ya,yb)-16,('+' if value>0 else '')+fmt(value,3),17,BLUE,'middle');s.text(xs[i],301,ch['rows'][i]['label'],16,INK,'middle')
  if i<1:s.line(xs[i]+width/2,yb,xs[i+1]-width/2,yb,MID,1,**{'stroke-dasharray':'3 4'})
 s.text(78,332,'两项贡献相加为总变化；总变化列以零为基线。',13,MID)
 return s.end()

def render_visual(ch):
 template=ch.get('visual',{}).get('template');fn={'rungs':rungs,'paired':rungs,'hairline':hairline,'dumbbell':dumbbell,'ribbon':ribbon,'composition':composition,'stem':stem,'plumb':plumb,'waterfall':waterfall}.get(template)
 if not fn:raise ValueError('未知复刻图型：'+str(template))
 return fn(ch)
