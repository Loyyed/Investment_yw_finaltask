"""Evidence-bound analytical HTML. No review writes, network or company defaults."""
from pathlib import Path
from decimal import Decimal, localcontext
import argparse, hashlib, html, json, math, re, sys, subprocess, copy, importlib.util
from functools import lru_cache

SPEC_PATH = 'work/research-atlas-current.json'

def read_spec(project, relative=SPEC_PATH):
    p=Path(project).resolve();f=(p/relative).resolve()
    if not f.is_relative_to(p):raise ValueError('研究规格须在当前项目内')
    value=json.loads(f.read_text(encoding='utf-8'))
    if 'spec_path' in value:
        f=(p/value['spec_path']).resolve()
        if not f.is_relative_to(p):raise ValueError('研究规格须在当前项目内')
        value=json.loads(f.read_text(encoding='utf-8'))
    return value

def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest()

def validate_current(project, spec, mode='legacy'):
    """Run authority in a fresh process, avoiding cross-company module caching."""
    project=Path(project).resolve()
    if mode=='legacy':
        script="import sys,json;from pathlib import Path;p=Path(sys.argv[1]);sys.path.insert(0,str(p/'scripts'));from review_store import ReviewStore;s=ReviewStore(p);print(json.dumps({n:getattr(s,n)() for n in json.loads(sys.argv[2])},ensure_ascii=True))"
        names=sorted({r['domain'] for r in spec['authority']})
        allowed={'facts','change_facts','lec03_agent_facts','m01_scale_facts','m01_metric_facts','m01_disclosure_facts'}
        if not set(names)<=allowed:raise ValueError('不支持的事实域')
        result=subprocess.run([sys.executable,'-c',script,str(project),json.dumps(names)],capture_output=True,text=True,encoding='utf-8',timeout=90)
        if result.returncode:raise ValueError('当前原事实接口读取失败；请回原空间检查')
        domains=json.loads(result.stdout)
    else:
        from .core import ReviewStore
        domains={'facts':ReviewStore(project).facts()}
    current={(n,r['id']):r for n,rows in domains.items() for r in rows}
    stale=[]
    for ref in spec['authority']:
        row=current.get((ref['domain'],ref['id']))
        if row is None or row.get('state',row.get('effective_state'))!='Fact' or digest(row)!=ref['record_digest']:
            stale.append(ref['domain']+':'+ref['id'])
    for item in spec.get('dependencies',[]):
        f=(project/item['path']).resolve()
        if not f.is_relative_to(project) or not f.is_file() or hashlib.sha256(f.read_bytes()).hexdigest()!=item['sha256']:
            stale.append(item['path'])
    if stale:raise ValueError('研究图册依据已变化，请更新分析后重生成：'+', '.join(stale[:8]))
    return {'status':'current','authority_records_checked':len(spec['authority']),'dependencies_checked':len(spec.get('dependencies',[]))}

def forecast(model, scenario, overrides=None):
    """Conditional product volume × mixed company ASP; no price target or FCFF."""
    with localcontext() as ctx:
        ctx.prec=40
        D=lambda x:Decimal(str(x));b=model['baseline'];s=model['scenarios'][scenario]
        mtq,mtp,srq,srp=(D(b[k]) for k in ['mt_volume','mt_asp','sr_volume','sr_asp'])
        wr0=mtq*mtp+srq*srp;gm0=D(b['gross_margin']);np0=D(b['net_profit']);se0=D(b['selling_expense']);other=D(b['other_revenue'])
        gm=gm0;out=[]
        for i,year in enumerate(model['years']):
            vals={k:D(s[k][i]) for k in ['mt_q','mt_p','sr_q','sr_p','gm_delta','selling_rate','retention','cash_ratio']}
            if i==0:
                for k,v in (overrides or {}).items():
                    if k not in ('mt_q','mt_p','selling_rate'):raise ValueError('未知预测参数')
                    vals[k]=D(v)
            if any(vals[k]<=-1 for k in ['mt_q','mt_p','sr_q','sr_p']):raise ValueError('量价增速必须大于-100%')
            mtq*=1+vals['mt_q'];mtp*=1+vals['mt_p'];srq*=1+vals['sr_q'];srp*=1+vals['sr_p'];gm+=vals['gm_delta']
            if not 0<=gm<=1 or not 0<=vals['selling_rate']<=1 or not 0<=vals['retention']<=1:raise ValueError('比例超出模型边界')
            wr=mtq*mtp+srq*srp;rev=wr+other;se=rev*vals['selling_rate'];delta=wr*gm-wr0*gm0-(se-se0);np=np0+delta*vals['retention']
            out.append({k:str(v) for k,v in {'year':year,'mt_volume':mtq,'mt_asp':mtp,'sr_volume':srq,'sr_asp':srp,'wine_revenue':wr,'revenue':rev,'gross_margin':gm,'selling_expense':se,'net_profit_bridge':np,'consolidated_cfo_sensitivity':np*vals['cash_ratio']}.items()})
        return out

def e(v):return html.escape(str(v),quote=True)
def number(v,p=2):return f'{float(v):,.{p}f}'

@lru_cache(maxsize=1)
def visual_module():
    source=Path(__file__).with_name('visual_charts.py')
    module_spec=importlib.util.spec_from_file_location('workbench_visual_charts',source)
    module=importlib.util.module_from_spec(module_spec);module_spec.loader.exec_module(module)
    return module

def apply_chart_designs(spec, designs):
    result=copy.deepcopy(spec);by_id={c['id']:c for c in result['chapters']}
    for id,charts in designs.get('new_charts',{}).items():
        if id not in by_id:raise ValueError('图形接续章节不存在：'+id)
        existing={x['title']:x for x in by_id[id].get('charts',[])}
        for chart in charts:
            if chart['title'] in existing:
                old=existing[chart['title']]
                if any(old.get(k)!=chart.get(k) for k in ('rows','series','unit')):raise ValueError('图形样式不得覆盖既有数据：'+chart['title'])
            else:by_id[id].setdefault('charts',[]).append(copy.deepcopy(chart))
    for c in result['chapters']:
        for chart in c.get('charts',[]):
            if chart['title'] in designs['designs']:chart['visual']=copy.deepcopy(designs['designs'][chart['title']])
    return result

def classic_svg(chart):
    data=copy.deepcopy(chart);visual=data.pop('visual',{})
    if visual.get('template') in ('hairline','plumb'):
        data['visual']=visual;data['visual']['simple']=True
        svg=visual_module().render_visual(data)
        return svg.replace('#334EAC','#167d8d').replace('#BAD6EB','#d69545').replace('#F7F2EB','#ffffff')
    data['kind']={'ribbon':'stack','composition':'stack','paired':'bar','dumbbell':'bar','stem':'bar','rungs':'bar'}.get(visual.get('template'),data.get('kind','bar'))
    return chart_svg(data)

def chart_svg(chart):
    """Zero-based bars; full percentage scale for margins; explicit missing gaps."""
    if chart.get('visual'):return visual_module().render_visual(chart)
    kind=chart.get('kind','line');rows=chart['rows'];series=chart['series'];w,h=760,300;left,right,top,bottom=72,26,28,58;pw,ph=w-left-right,h-top-bottom
    colors=['#167d8d','#d69545','#63748d','#7bb6a5'];vals=[float(r[s['key']]) for r in rows for s in series if r.get(s['key']) is not None]
    if not vals:return '<p>当前缺少可绘制输入。</p>'
    low=min(0,min(vals));high=max(vals)*1.16 or 1
    if kind=='stack':high=max(sum(float(r.get(s['key']) or 0) for s in series) for r in rows)*1.13
    if kind=='waterfall':low=min(0,min(vals))*1.25;high=max(0,max(vals))*1.25
    if chart.get('domain'):low,high=chart['domain']
    def yy(v):return top+(high-float(v))/(high-low)*ph
    def xx(i):return left+(i+.5)*pw/len(rows)
    out=[f'<svg viewBox="0 0 {w} {h}" role="img" aria-label="{e(chart["title"])}"><title>{e(chart["title"])}</title>']
    for i in range(5):
        v=low+(high-low)*i/4;y=yy(v);out.append(f'<line x1="{left}" y1="{y}" x2="{w-right}" y2="{y}" stroke="#e0e8e7"/><text x="{left-10}" y="{y+4}" text-anchor="end" class="tick">{e(number(v,chart.get("axis_precision",0)))}</text>')
    if low<0:out.append(f'<line x1="{left}" x2="{w-right}" y1="{yy(0)}" y2="{yy(0)}" stroke="#899a9a"/>')
    for j,s in enumerate(series):
        col=colors[j%len(colors)];key=s['key'];pts=[]
        for i,r in enumerate(rows):
            x=xx(i);v=r.get(key)
            if v is None:
                if len(pts)>1:out.append(f'<polyline points="{" ".join(pts)}" fill="none" stroke="{col}" stroke-width="2.6"/>')
                pts=[];continue
            v=float(v);y=yy(v)
            if kind=='line':
                pts.append(f'{x},{y}');out.append(f'<circle cx="{x}" cy="{y}" r="4" fill="{col}"><title>{e(r["label"])} · {e(s["label"])} {number(v,chart.get("precision",2))}{e(chart["unit"])}</title></circle>')
                if len(rows)<=6:out.append(f'<text x="{x}" y="{y-12-j*3}" text-anchor="middle" class="value">{number(v,chart.get("precision",2))}</text>')
            else:
                width=min(76,pw/len(rows)*.65/(len(series) if kind!='stack' else 1))
                if kind=='stack':base=sum(float(r.get(q['key']) or 0) for q in series[:j]);y=yy(base+v);height=yy(base)-y;bx=x-width/2
                else:height=abs(yy(v)-yy(0));y=min(yy(v),yy(0));bx=x+(j-(len(series)-1)/2)*width-width/2
                out.append(f'<rect x="{bx}" y="{y}" width="{width-2}" height="{max(.5,height)}" rx="3" fill="{col}"><title>{e(r["label"])} · {e(s["label"])} {number(v,chart.get("precision",2))}{e(chart["unit"])}</title></rect>')
                if kind!='stack' and len(rows)*len(series)<=12:out.append(f'<text x="{bx+width/2}" y="{y-8 if v>=0 else y+height+16}" text-anchor="middle" class="value">{number(v,chart.get("precision",2))}</text>')
        if kind=='line' and len(pts)>1:out.append(f'<polyline points="{" ".join(pts)}" fill="none" stroke="{col}" stroke-width="2.6"/>')
    for i,r in enumerate(rows):out.append(f'<text x="{xx(i)}" y="{h-bottom+25}" text-anchor="middle" class="tick">{e(r["label"])}</text>')
    out.append('</svg>');return ''.join(out)

def analysis_details(analysis, summary='图表分析：含义、用途与推断'):
    if not analysis:return '<details class="chart-analysis"><summary>'+e(summary)+'</summary><p>本图的研究解读待补充，请结合图下说明及当前来源判断。</p></details>'
    labels=[('meaning','图表含义'),('use','研究用途'),('inference','分析与推断')]
    return '<details class="chart-analysis"><summary>'+e(summary)+'</summary><dl>'+''.join('<dt>'+label+'</dt><dd>'+e(analysis.get(key,'待补充'))+'</dd>' for key,label in labels)+'</dl></details>'

def apply_story_enrichment(spec, enrichment):
    """Compose authored storytelling without replacing existing chart or model data."""
    result=copy.deepcopy(spec)
    by_id={c['id']:c for c in result['chapters']}
    for id,update in enrichment.get('chapter_updates',{}).items():
        if id not in by_id:raise ValueError('叙事接续章节不存在：'+id)
        c=by_id[id]
        for field in ('story_beats','transition','mind_maps'):
            if field in update:c[field]=copy.deepcopy(update[field])
        for src,dest in [('append_blocks','blocks'),('append_charts','charts')]:
            current={x['title']:x for x in c.get(dest,[])}
            for value in update.get(src,[]):
                old=current.get(value['title'])
                if old is not None:
                    if dest=='charts' and any(old.get(k)!=value.get(k) for k in ('rows','series','unit')):
                        raise ValueError('叙事扩展不得覆盖原图数值：'+value['title'])
                    old.update(copy.deepcopy(value))
                else:c.setdefault(dest,[]).append(copy.deepcopy(value))
    for c in enrichment.get('new_chapters',[]):
        if c['id'] in by_id:
            if by_id[c['id']]!=c:raise ValueError('专题编号冲突：'+c['id'])
            continue
        before=enrichment.get('insert_before');index=next((i for i,x in enumerate(result['chapters']) if x['id']==before),len(result['chapters']))
        result['chapters'].insert(index,copy.deepcopy(c));by_id[c['id']]=result['chapters'][index]
    for field,keys in [('sources',('id',)),('authority',('domain','id')),('dependencies',('path',))]:
        current={tuple(x[k] for k in keys):x for x in result.get(field,[])}
        for value in enrichment.get(field,[]):
            key=tuple(value[k] for k in keys)
            if key in current:
                if current[key]!=value:raise ValueError('叙事扩展依据编号冲突：'+str(key))
            else:result.setdefault(field,[]).append(copy.deepcopy(value));current[key]=result[field][-1]
    return result

def mindmap_html(data, chapters, current=None):
    ids={c['id'] for c in chapters}
    nodes=data['nodes']; positions=[(470,270),(30,38),(30,270),(30,502),(910,38),(910,270),(910,502)]
    if len(nodes)!=7:raise ValueError('思维导图应含一个中心与六个分支')
    pieces=['<figure class="mindmap"><figcaption><span class="eyebrow">研究思路 · 可点击的机制图</span><h3>'+e(data['title'])+'</h3><p>'+e(data['subtitle'])+'</p></figcaption><div class="map-scroll" tabindex="0"><svg viewBox="0 0 1260 680" role="img" aria-label="'+e(data['title'])+'"><title>'+e(data['title'])+'</title>']
    for i in range(1,7):
        x,y=positions[i]; left=i<4; a,b=(470,y+65) if left else (790,y+65)
        pieces.append('<path d="M '+str(470 if left else 790)+' 335 C '+str(410 if left else 850)+' 335 '+str(410 if left else 850)+' '+str(y+65)+' '+str(x+320 if left else x)+' '+str(y+65)+'" fill="none" stroke="#7096D1" stroke-width="2" stroke-dasharray="5 5"/>')
    for i,(node,(x,y)) in enumerate(zip(nodes,positions)):
        target=node['target']
        if target not in ids:raise ValueError('导图目标章节不存在：'+target)
        href='#'+target if current is None or current==target else '../证券投资分析研究图册.html#'+target
        pieces.append('<a href="'+e(href)+'" aria-label="'+e(node['label'])+'，阅读对应分析"><rect x="'+str(x)+'" y="'+str(y)+'" width="320" height="140" rx="15" fill="'+('#183d42' if i==0 else '#fff')+'" stroke="#BAD6EB"/><text x="'+str(x+18)+'" y="'+str(y+27)+'" fill="'+('#BAD6EB' if i==0 else '#63748d')+'" font-size="13">'+e(node['state'])+'</text><text x="'+str(x+18)+'" y="'+str(y+55)+'" fill="'+('#fff' if i==0 else '#183d42')+'" font-size="19" font-weight="600">'+e(node['label'])+'</text>')
        for j,line in enumerate(node['lines'][:3]):pieces.append('<text x="'+str(x+18)+'" y="'+str(y+81+j*21)+'" fill="'+('#fff' if i==0 else '#334EAC')+'" font-size="15">'+e(line)+'</text>')
        pieces.append('</a>')
    pieces.append('</svg></div><p class="chart-reading">虚线连接研究问题与可能机制，不表示已证实因果。点击节点前往对应章节。</p><div class="refs">'+''.join('<a href="#src-'+e(r)+'">['+e(r)+']</a>' for r in data['refs'])+'</div>'+analysis_details(data['analysis']))
    pieces.append('<details><summary>节点依据与阅读顺序</summary>'+''.join('<p><strong>'+e(n['label'])+'</strong>：'+e(n['note'])+'</p>' for n in nodes)+'</details></figure>')
    return re.sub(r'<text([^>]*?)fill="([^"]+)"',lambda m:'<text'+m.group(1)+'style="fill:'+m.group(2)+'" fill="'+m.group(2)+'"',''.join(pieces))

def render(spec, chapter=None, nonce='', source_url=None):
    base=Path(__file__).parent;css=(base/'insight.css').read_text(encoding='utf-8');js=(base/'insight.js').read_text(encoding='utf-8')
    chapters=spec['chapters'];chosen=[c for c in chapters if not chapter or c['id']==chapter]
    if not chosen:raise ValueError('章节不存在')
    source_map={x['id']:x for x in spec['sources']}
    def refs(ids):return '<span class="refs">'+''.join(f'<a href="#src-{e(i)}" title="查看来源批注">[{e(i)}]</a>' for i in ids)+'</span>'
    def table(headers,rows):return '<div class="table-wrap"><table><thead><tr>'+''.join('<th>'+e(x)+'</th>' for x in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+e(x)+'</td>' for x in r)+'</tr>' for r in rows)+'</tbody></table></div>'
    body=[]
    for c in chosen:
        b=[f'<section id="{e(c["id"])}" class="chapter"><header class="chapter-head"><div class="eyebrow">{e(c["kicker"])}</div><h2>{e(c["title"])}</h2><p class="question">{e(c["question"])}</p><div class="verdict"><span>研究判断 · Interpretation</span><p>{e(c["thesis"])}</p>{refs(c.get("refs",[]))}</div></header>']
        if c.get('story_beats'):
            b.append('<div class="story-sequence"><div class="eyebrow">把变化放回经营过程 · 研究者解释</div><ol>'+''.join('<li><span class="story-step">'+str(i+1).zfill(2)+'</span><div><h3>'+e(x['title'])+'</h3><p>'+e(x['text'])+'</p>'+refs(x.get('refs',[]))+'</div></li>' for i,x in enumerate(c['story_beats']))+'</ol></div>')
        if c.get('scope'):b.append('<p class="scope">'+e(c['scope'])+'</p>')
        if c.get('flow'):b.append('<div class="flow">'+''.join('<div><small>'+str(i+1).zfill(2)+'</small><strong>'+e(x[0])+'</strong><p>'+e(x[1])+'</p></div>' for i,x in enumerate(c['flow']))+'</div>')
        for item in c.get('blocks',[]):
            b.append('<article class="argument"><h3>'+e(item['title'])+'</h3>'+''.join('<p>'+e(x)+'</p>' for x in item['paragraphs'])+refs(item.get('refs',[]))+'</article>')
        for map_data in c.get('mind_maps',[]):b.append(mindmap_html(map_data,chapters,chapter))
        if c.get('charts'):
            b.append('<div class="chart-grid">')
            for ch in c['charts']:
                legend='<div class="chart-legend">'+''.join('<span><i style="background:'+['#167d8d','#d69545','#63748d','#7bb6a5'][j%4]+'"></i>'+e(item['label'])+'</span>' for j,item in enumerate(ch['series']))+'</div>'
                classic_legend=legend
                visual=ch.get('visual')
                if visual:
                    if visual.get('template')=='dumbbell':
                        labels=[str(r['label']) for r in ch['rows']] if visual.get('pair_mode')=='rows' else [r['label'] for r in ch['series']]
                        legend='<div class="chart-legend"><span><i class="vis-key hollow"></i>空心：'+e(labels[0])+'</span><span><i class="vis-key solid"></i>实心：'+e(labels[1])+'</span></div>'
                    else:
                        items=visual.get('legend_items') or [{'label':item['label'],'color':visual_module().COLORS[j%4]} for j,item in enumerate(ch['series'])]
                        legend='<div class="chart-legend">'+''.join('<span><i style="background:'+e(item['color'])+'"></i>'+e(item['label'])+'</span>' for item in items)+'</div>'
                if visual:
                    if visual.get('template')=='plumb':classic_legend='<div class="chart-legend"><span><i style="background:#d69545"></i>2016—2021</span><span><i style="background:#167d8d"></i>2022—2025</span></div>'
                    legend='<div class="plot-porcelain">'+legend+'</div><div class="plot-classic">'+classic_legend+'</div>'
                figure_class='figure-replica'+(' figure-wide' if visual and visual.get('full_width') else '') if visual else ''
                controls=('<div class="chart-tools"><span>'+e(visual_module().NAMES[visual['template']])+'</span><button type="button" data-chart-replay>↻ 重播绘制</button></div>') if visual else ''
                b.append('<figure class="'+figure_class+'"><figcaption><span class="eyebrow">'+e(ch.get('tag','计算 · AgentCalculated'))+'</span><h3>'+e(ch['title'])+'</h3><p>'+e(ch['subtitle'])+'</p></figcaption>'+legend+controls+'<div class="chart-unit">'+e(ch['unit'])+'</div>'+'<div class="chart-canvas" tabindex="0" role="region" aria-label="'+e(ch['title'])+'">'+('<div class="plot-porcelain">'+chart_svg(ch)+'</div><div class="plot-classic">'+classic_svg(ch)+'</div>' if visual else chart_svg(ch))+'</div>'+('<p class="chart-pan-hint">窄屏可横向滑动图形，查看完整刻度与标签。</p>' if visual else '')+'<p class="chart-reading">'+e(ch['reading'])+'</p>'+refs(ch['refs']))
                hdr=['期间／类别']+[x['label']+'（'+ch['unit']+'）' for x in ch['series']]
                vals=[[r['label']]+['Unknown' if r.get(s['key']) is None else number(r[s['key']],ch.get('precision',2)) for s in ch['series']] for r in ch['rows']]
                b.append(analysis_details(ch.get('analysis')))
                b.append('<details><summary>查看数据与计算口径</summary><p>'+e(ch.get('formula','原披露或匹配范围派生，输入详见来源批注。'))+'</p>'+table(hdr,vals)+'</details>')
                if visual:b.append('<details class="visual-note"><summary>图型与视觉编码</summary><p>'+e(visual['note'])+'</p><p>图型参考：'+e(visual.get('reference',{}).get('file','本项目图形设计'))+'。按当前项目数据重新绘制，原件留本地；图形复刻不迁移参考事实身份。</p></details>')
                b.append('</figure>')
            b.append('</div>')
        if c.get('matrix'):b.append(table(c['matrix']['headers'],c['matrix']['rows'])+analysis_details(c['matrix'].get('analysis'),'表格分析：含义、用途与推断'))
        if c.get('forecast'):
            parameter_analysis=analysis_details({'meaning':'参数表按情景和年份列出销量、组合ASP、毛利率变动、费用率、增量保留率和现金转换率；各行都是条件假设。','use':'审查未来结果依赖哪些参数，以及压力、基准和修复分别要求怎样的经营变化。','inference':'只有假设兑现，相关路径才成立；不能把参数称为已核业绩或管理层承诺。修改滑块仅覆盖首个预测年的三项参数，原参数表不随滑块改写。'},'表格分析：预测参数的含义、用途与推断')
            b.append('<div class="forecast-lab"><div class="eyebrow">FORECAST LAB · 条件模型</div><h3>改一个假设，看看未来会怎样</h3><p>默认展示研究基准；三个情景并无概率或置信区间含义。滑块仅覆盖首个预测年，后续沿用该情景年度参数。离线改动只在当前页面计算，刷新恢复。</p><div class="scenario-tabs" role="group" aria-label="预测情景">'+''.join('<button data-scenario="'+e(k)+'" aria-pressed="'+('true' if k=='base' else 'false')+'">'+e(v['label'])+'</button>' for k,v in spec['forecast']['scenarios'].items())+'</div><div class="sliders"><label>首个预测年 · 核心产品公司销量增速 <output id="q-label"></output><input id="q-input" type="range" min="-10" max="12" step="0.5"></label><label>首个预测年 · 核心产品组合均价变化 <output id="p-label"></output><input id="p-input" type="range" min="-12" max="10" step="0.5"></label><label>首个预测年 · 公司销售费用率 <output id="s-label"></output><input id="s-input" type="range" min="3" max="7" step="0.1"></label></div><div id="forecast-output" aria-live="polite"></div><details><summary>模型公式、全部参数与假设来源</summary><p>'+e(spec['forecast']['formula_note'])+'</p>'+table(['情景','年份','茅台量%','茅台ASP%','系列量%','系列ASP%','毛利变动pp','销售费率%','增量保留%','CFO/净利'],[[v['label'],yr]+[number(v[k][i]*(100 if k!='cash_ratio' else 1)) for k in ['mt_q','mt_p','sr_q','sr_p','gm_delta','selling_rate','retention','cash_ratio']] for v in spec['forecast']['scenarios'].values() for i,yr in enumerate(spec['forecast']['years'])])+parameter_analysis+'<p>'+e(spec['forecast']['assumption_note'])+'</p></details><button id="reset-forecast">恢复所选情景</button></div>')
        b.append('<div class="reason-grid"><article><span class="eyebrow">替代解释</span><h3>'+e(c['alternative'][0])+'</h3><p>'+e(c['alternative'][1])+'</p></article><article><span class="eyebrow">如何推翻当前判断</span><h3>'+e(c['falsifier'][0])+'</h3><p>'+e(c['falsifier'][1])+'</p></article></div>')
        b.append('<div class="next"><strong>接下来观察什么</strong><p>'+e(c['next'])+'</p></div>')
        if c.get('transition'):
            t=c['transition'];target=t['target']
            if target not in {x['id'] for x in chapters}:raise ValueError('叙事接续目标不存在：'+target)
            href=('#'+target) if not chapter or target==chapter else '../证券投资分析研究图册.html#'+target
            b.append('<div class="chapter-bridge"><small>这一章怎样接到下一环</small><p>'+e(t['text'])+'</p><a href="'+e(href)+'">'+e(t['label'])+' →</a></div>')
        if c.get('deliverables'):b.append('<details><summary>合同问题对应与已有过程底稿</summary>'+''.join('<p>'+e(x)+'</p>' for x in c['deliverables'])+'</details>')
        b.append('</section>');body.extend(b)
    citations=[]
    for src in spec['sources']:
        path=src.get('path','');href=source_url(path) if source_url and path else path
        citations.append('<article id="src-'+e(src['id'])+'"><h3>['+e(src['id'])+'] '+e(src['title'])+'</h3><p>'+e(src['status'])+'</p><p>'+e(src['note'])+'</p>'+('<a href="'+e(href)+'">打开本地依据文件</a>' if path else '')+'<small>'+e(src.get('sha256',''))+'</small></article>')
    nav=''.join('<a href="'+('#'+e(c['id']) if not chapter or c['id']==chapter else '../证券投资分析研究图册.html#'+e(c['id']))+'"><span>'+e(c['number'])+'</span>'+e(c['nav'])+'</a>' for c in chapters)
    data=json.dumps({'forecast':spec['forecast'],'precomputed':spec['forecast_results']},ensure_ascii=False).replace('<','\\u003c').replace('&','\\u0026')
    title=spec['title'] if not chapter else chosen[0]['title']+'｜'+spec['company']+'研究图册'
    page= '<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+e(title)+'</title><style>'+css+'</style></head><body><a class="skip" href="#main">跳到报告正文</a><aside class="rail"><a class="brand" href="#main">研投<span>RESEARCH ATLAS / 600519</span></a><p>从证据，走向解释与预测</p><nav aria-label="合同章节">'+nav+'<a href="#sources">↳ 来源与批注</a></nav><div class="rail-foot">2026.10.25 · 研究扩展稿<br>新增观点及预测待人工最终裁决</div></aside><main id="main"><header class="cover"><div class="eyebrow">SECURITIES RESEARCH / 贵州茅台</div><div class="toolbar"><div class="style-toggle" role="group" aria-label="图形风格"><button data-plot-style="porcelain" aria-pressed="true">青瓷复刻</button><button data-plot-style="classic" aria-pressed="false">常规图</button></div><button id="guide-toggle" aria-pressed="false">显示初学者提示</button><button id="print-report">打印 / 保存PDF</button></div><h1>'+e(title)+'</h1><p class="deck">'+e(spec['subtitle'])+'</p><div class="cover-meta"><span>主实证：2020—2024</span><span>独立后验：2025</span><span>条件预测：2026—2028</span></div><p class="snapshot">'+e(spec['snapshot_note'])+'</p><p class="guide">阅读顺序：先看每章判断，再读图下解释；点击方括号编号看来源。ASP是匹配收入÷公司销量；pp是百分点；CFO是合并经营活动现金流净额。预测表是条件运算，不是将来的确定事实。</p></header>'+''.join(body)+'<section id="sources" class="chapter"><div class="eyebrow">EVIDENCE NOTES</div><h2>来源、运算与阅读批注</h2><p>原始Fact、公司自述、研究推断和Forecast分别标注。未补足的指标不填零；本图册没有新增人工核验、采纳或签署。下列本地原件链接在GitHub副本中可能不可访问，原件按授权留本地。</p><div class="citations">'+''.join(citations)+'</div></section><footer>生成于2026-10-25 · 附件优先 · 研究内容不继承P04等旧版本认可 · 最终裁决由人工完成</footer></main><script nonce="'+e(nonce)+'" id="atlas-data" type="application/json">'+data+'</script><script nonce="'+e(nonce)+'">'+js+'</script></body></html>'

    if spec.get('reader_v2'):
        delivery_spec=importlib.util.spec_from_file_location('workbench_delivery',Path(__file__).with_name('delivery.py'))
        delivery=importlib.util.module_from_spec(delivery_spec);delivery_spec.loader.exec_module(delivery)
        page=delivery.enhance_atlas(page,spec,chapter)
    return page.replace('RESEARCH ATLAS / 600519','RESEARCH ATLAS / '+e(spec.get('security_code',''))).replace('SECURITIES RESEARCH / 贵州茅台','SECURITIES RESEARCH / '+e(spec['company'])).replace('2026.10.25',e(spec['date'])).replace('2026-10-25',e(spec['date']))

def render_visual_gallery(spec, source_url=None, report_link='../证券投资分析研究图册.html'):
    charts=[x for c in spec['chapters'] for x in c.get('charts',[]) if x.get('visual')]
    order=['ribbon','dumbbell','paired','hairline','rungs','plumb','composition','stem','waterfall'];selected=[]
    for template in order:
        candidates=[x for x in charts if x['visual']['template']==template]
        if not candidates:continue
        if template in ('ribbon','paired'):chosen=max(enumerate(candidates),key=lambda pair:(len(pair[1]['rows']),pair[0]))[1]
        elif template=='dumbbell':chosen=max(candidates,key=lambda x:(x['visual'].get('pair_mode')!='rows',len(x['rows'])))
        elif template=='rungs':chosen=max(candidates,key=lambda x:len(x['rows']))
        else:chosen=candidates[0]
        selected.append(copy.deepcopy(chosen))
    if not selected:raise ValueError('当前项目尚无复刻图型，先指定图形编码')
    gallery=copy.deepcopy(spec);gallery['title']=spec['company']+'：青瓷蓝图形复刻样例';gallery['subtitle']='以当前已绑定数据重新实现细线、阶梯、哑铃、构成条带与垂线散点。每幅图保留分析、数据和编码说明，支持重播绘制。'
    gallery['chapters']=[{'id':'visual-gallery','number':'图','nav':'图型样例','kicker':'视觉样例 / 当前项目数据','title':'先看图，再回到研究','question':'哪种图型更容易看清同一份数据？','thesis':'图型为研究问题服务：年度关系、构成、成对差异和机制诊断分别选择合适编码。复刻配色与细线语言，保留精确输入、定义断点和未知边界。','refs':[],'blocks':[],'charts':selected,'alternative':['美观与适配分别判断','需要精确查数时，展开数据表和来源；图型不能改变口径。'],'falsifier':['编码若改变含义就应重选','不跨缺失或定义断点假画连续关系，不让阶梯取整替代数值。'],'next':'返回完整报告可按合同及专题阅读，本页仅汇集图形样式。'}]
    page=render(gallery,'visual-gallery',source_url=source_url)
    return page.replace('<div class="toolbar">','<div class="toolbar"><a href="'+e(report_link)+'">返回完整研究 ↗</a>',1)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('project');ap.add_argument('--spec',default=SPEC_PATH);ap.add_argument('--output',default='outputs/证券投资分析研究图册.html');ap.add_argument('--mode',default='legacy',choices=['legacy','standard']);args=ap.parse_args()
    p=Path(args.project).resolve();spec=read_spec(p,args.spec);check=validate_current(p,spec,args.mode)
    out=(p/args.output).resolve()
    if not out.is_relative_to(p):raise ValueError('输出须在本公司项目内')
    out.parent.mkdir(parents=True,exist_ok=True);out.write_text(render(spec,source_url=lambda x:'../'+x),encoding='utf-8')
    directory=out.parent/'research-atlas';directory.mkdir(exist_ok=True)
    for c in spec['chapters']:(directory/(c['id']+'.html')).write_text(render(spec,c['id'],source_url=lambda x:'../../'+x),encoding='utf-8')
    if any(ch.get('visual') for c in spec['chapters'] for ch in c.get('charts',[])):(directory/'visual-gallery.html').write_text(render_visual_gallery(spec,source_url=lambda x:'../../'+x,report_link='../'+out.name),encoding='utf-8')
    print(json.dumps({'output':str(out),'pages':len(spec['chapters'])+1,**check},ensure_ascii=False))
if __name__=='__main__':main()
