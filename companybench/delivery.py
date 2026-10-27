"""Reader-first research delivery. No evidence, signatures or company defaults."""
from pathlib import Path
import html,json,re

def e(x):return html.escape(str(x),quote=True)

CSS='''
.v2-summary>.v2-answer{grid-column:1/-1;min-width:0;padding:24px 28px;background:#eaf2ed;border:1px solid #c5d8ce;border-left:4px solid #167d8d;border-radius:0 12px 12px 0}.v2-answer h3{font-size:21px;line-height:1.5;margin:0 0 14px;color:#123e45}.v2-answer p{font-size:17px;line-height:1.95;margin:10px 0}.v2-answer p.v2-answer-boundary{font-size:14px;color:#4d6870}.v2-answer-state{font-size:12px;line-height:1.8;color:#557078;margin-top:16px}.v2-answer-state .refs{margin-left:12px}@media(max-width:800px){.v2-summary>.v2-answer{padding:20px 18px}}@media print{.v2-answer{break-inside:avoid}}
.v2-intro{margin:30px 0 50px;padding:34px;background:#fffdf8;border:1px solid #d6ded8;border-radius:20px}.v2-intro h2{font-size:32px;line-height:1.4;margin:12px 0;color:#123e45}.v2-lead{font-size:19px;line-height:1.9;max-width:850px}.v2-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px;margin:24px 0}.v2-card{padding:22px;background:#edf3f1;border-radius:12px;min-width:0}.v2-card strong{display:block;color:#123e45;font-size:21px;line-height:1.5}.v2-card p{font-size:15px;line-height:1.85}.v2-tag{font:700 11px/1.7 sans-serif;letter-spacing:.12em;text-transform:uppercase;color:#39717b}.v2-path{display:flex;gap:8px;flex-wrap:wrap;margin:20px 0}.v2-path a{padding:10px 16px;border:1px solid #c0d4d0;border-radius:30px;color:#123e45;text-decoration:none}.v2-path a:hover{background:#e0efeb}.v2-note{font-size:13px;line-height:1.9;color:#557078}.v2-summary{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin:22px 0 36px}.v2-summary>div{padding:20px 24px;border-left:3px solid #bd8b42;background:#f2f3eb}.v2-summary p{font-size:16px;line-height:1.9;margin:8px 0}.v2-map{overflow-x:auto;margin:24px 0}.v2-map svg{min-width:840px;width:100%;height:auto;font-family:Microsoft YaHei,Arial,sans-serif}.v2-table{overflow-x:auto}.v2-table table{width:100%;border-collapse:collapse;min-width:660px}.v2-table th,.v2-table td{padding:13px;text-align:left;border-bottom:1px solid #d5ded8;font-size:14px;line-height:1.65}.v2-table th{background:#e9f1ee}.v2-badge{display:inline-block;padding:6px 12px;background:#bd8b42;color:white;border-radius:6px;font:700 12px sans-serif}.v2-intro details{margin-top:18px}.v2-intro summary{cursor:pointer}.v2-intro .glossary{display:grid;grid-template-columns:1fr 1fr;gap:10px}.v2-intro .glossary p{padding:10px;background:#f3f5f0;font-size:14px;line-height:1.8}.v2-intro a{overflow-wrap:anywhere}@media(max-width:800px){.v2-intro{padding:22px 18px}.v2-intro h2{font-size:26px}.v2-grid,.v2-summary,.v2-intro .glossary{grid-template-columns:1fr}.v2-lead{font-size:17px}}@media print{.v2-intro{break-inside:auto}.v2-card{break-inside:avoid}.v2-map svg{min-width:0}.v2-path{display:none}}
'''

def mindmap(center, branches, label='研究框架导图'):
    # Six plain-language branches; edges are research connections, not causal estimates.
    positions=[(20,25),(20,205),(20,385),(790,25),(790,205),(790,385)]
    b=['<div class="v2-map"><svg viewBox="0 0 1100 535" role="img" aria-label="'+e(label)+'"><title>'+e(label)+'</title>']
    for i,item in enumerate(branches[:6]):
        x,y=positions[i];end=x+290 if x<500 else x;start=450 if x<500 else 650
        b.append(f'<path d="M{start},265 C{start+(end-start)/2},265 {start+(end-start)/2},{y+65} {end},{y+65}" fill="none" stroke="#b4c9c4" stroke-width="2"/>')
    b.append('<rect x="420" y="207" width="260" height="116" rx="22" fill="#123e45"/>')
    for j,line in enumerate(center.split('|')):b.append(f'<text x="550" y="{250+j*28}" text-anchor="middle" fill="#ffffff" style="fill:#ffffff;font-size:22px;font-weight:700">{e(line)}</text>')
    for i,item in enumerate(branches[:6]):
        x,y=positions[i];href=item.get('href');b.append(('<a href="'+e(href)+'">') if href else '<g>')
        b.append(f'<rect x="{x}" y="{y}" width="290" height="130" rx="15" fill="#e9f1ee" stroke="#c2d4ce"/><text x="{x+18}" y="{y+28}" fill="#44717a" style="font-size:12px">{e(item.get("tag","研究关联"))}</text><text x="{x+18}" y="{y+58}" fill="#123e45" style="font-size:20px;font-weight:700">{e(item["title"])}</text>')
        for j,line in enumerate(item.get('lines',[])[:2]):b.append(f'<text x="{x+18}" y="{y+87+j*21}" fill="#46636a" style="font-size:14px">{e(line)}</text>')
        b.append('</a>' if href else '</g>')
    return ''.join(b)+'</svg></div>'

def table(headers,rows):
    return '<div class="v2-table"><table><thead><tr>'+''.join('<th>'+e(x)+'</th>' for x in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+e(v)+'</td>' for v in row)+'</tr>' for row in rows)+'</tbody></table></div>'

def reader_intro(spec):
    r=spec['reader_v2'];b=['<section class="v2-intro" id="start-here"><span class="v2-badge">V2.0 · 第一次阅读从这里开始</span><h2>'+e(r['title'])+'</h2><p class="v2-lead">'+e(r['lead'])+'</p><div class="v2-grid">']
    for c in r['cards']:b.append('<article class="v2-card"><span class="v2-tag">'+e(c['tag'])+'</span><strong>'+e(c['title'])+'</strong><p>'+e(c['text'])+'</p></article>')
    b.append('</div>'+mindmap(r['map_center'],r['map_branches'],'一瓶酒如何通过供给、销售与现金三道检验'))
    b.append('<p class="v2-note">图中连线表示待检验的经营联系；历史数字、解释和未来假设分别判断。点击节点进入相应章节。</p><h3>选一条适合你的阅读路线</h3><div class="v2-path">')
    b.extend('<a href="'+e(x['href'])+'">'+e(x['label'])+'</a>' for x in r['routes']);b.append('</div><h3>先看关键变化，再判断故事是否需要改写</h3>')
    b.append(table(r['observations']['headers'],r['observations']['rows']))
    b.append('<p class="v2-note">上述为披露与同口径运算的阅读摘要，精确值、PDF定位和支持边界见 [E04]—[E08] 及对应章节；库存和公司出货均非终端口径，合并CFO含金融业务。不同指标的增速不能相加或据此直接归因。</p><h3>我倾向怎样的未来，什么会令我改判</h3><p class="v2-lead">'+e(r['forecast_reading'])+'</p>')
    b.append(table(r['scenarios']['headers'],r['scenarios']['rows']))
    b.append('<p class="v2-note">这是明确假设下的条件运算，未分配概率。利润是合并条件利润桥，现金是合并CFO敏感性；模型公式、全参数和可调实验在预测章。2025为独立后验与新预测基期，不能回填2024历史判断。</p><details><summary>先把术语翻译成日常语言</summary><div class="glossary">')
    b.extend('<p><strong>'+e(k)+'</strong><br>'+e(v)+'</p>' for k,v in r['glossary']);b.append('</div></details><details><summary>V2.0具体改进了什么</summary><p>'+e(r['changes'])+'</p></details></section>')
    return ''.join(b)


CONTRACT_CSS='''.contract-answers{padding:24px 0 10px;border-top:1px solid #b6cbc3;margin:26px 0}.contract-answers>h3{font-size:25px;color:#173f45}.contract-answer{margin:25px 0;padding:22px 24px;background:#fffdf8;border-left:3px solid #b99356;scroll-margin-top:20px}.contract-answer h4{font-size:20px;line-height:1.65;margin:4px 0 14px;color:#193f45}.contract-answer p{font-size:16px;line-height:1.95;margin:12px 0}.contract-state{font-size:12px!important;color:#58716c}.contract-answer details{font-size:13px}.contract-answer details a{display:inline-block;margin:8px 18px 6px 0}.contract-note{font-size:14px!important;color:#55766d}.contract-answers .v2-table{max-width:100%;margin:16px 0}.contract-answers .v2-table th,.contract-answers .v2-table td{font-size:13px}.contract-answers .v2-table th{white-space:normal}@media(max-width:760px){.contract-answer{padding:18px 15px}.contract-answer h4{font-size:19px}.contract-answer p{font-size:15px}.contract-answers .v2-table table{min-width:600px}}@media print{.contract-answer{break-inside:auto}.contract-answer details{display:block}}'''

def contract_answers_html(spec,chapter_id,separate_page=False):
    """Visible answers to actual contract questions; never an automatic acceptance."""
    rows=spec.get('reader_v2',{}).get('contract_checks',{}).get(chapter_id,[])
    if not rows:return ''
    source_ids={s['id'] for s in spec.get('sources',[])};seen=set();prefix='../../' if separate_page else '../'
    b=['<section class="contract-answers" aria-label="合同逐问核对"><h3>合同问题，逐问回答</h3><p class="contract-note">内容覆盖与事实核验、研究采纳、正式签署分别记录。'+e(spec.get('reader_v2',{}).get('contract_revision',''))+'</p>']
    for r in rows:
        key=r['id']
        if key in seen or not r.get('question') or not r.get('paragraphs'):raise ValueError('合同回答缺项或重复：'+str(key))
        seen.add(key)
        if any(x not in source_ids for x in r.get('refs',[])):raise ValueError('合同回答引用不存在：'+key)
        anchor='contract-'+chapter_id+'-'+key
        b.append('<article class="contract-answer" id="'+e(anchor)+'"><p class="contract-state">'+e(r.get('status','研究回答，非自动验收'))+'</p><h4>'+e(r['question'])+'</h4>')
        b.extend('<p>'+e(v)+'</p>' for v in r['paragraphs'])
        if r.get('table'):
            t=r['table']
            if any(len(row)!=len(t['headers']) for row in t['rows']):raise ValueError('合同回答表格列数不符：'+key)
            b.append(table(t['headers'],t['rows']))
        b.append('<span class="refs">'+''.join('<a href="#src-'+e(x)+'">['+e(x)+']</a>' for x in r.get('refs',[]))+'</span>')
        if r.get('evidence'):
            b.append('<details><summary>回查本题底稿与实际记录</summary>'+''.join('<a href="'+prefix+e(x['path'])+'">'+e(x['label'])+' ↗</a>' for x in r['evidence'])+'</details>')
        b.append('</article>')
    return ''.join(b)+'</section>'


def enhance_atlas(page,spec,chapter=None):
    r=spec.get('reader_v2')
    if not r or '<!-- research-reader-v2 -->' in page:return page
    page=page.replace('<body>','<body><!-- research-reader-v2 -->',1)
    page=page.replace('</style>','\n'+CSS+CONTRACT_CSS+'</style>',1)
    if not chapter:
        marker='<section id="'+e(spec['chapters'][0]['id'])+'"'
        page=page.replace(marker,reader_intro(spec)+marker,1)
        page=page.replace('<nav aria-label="合同章节">','<nav aria-label="合同章节"><a href="#start-here">◎ V2.0 · 五分钟导读</a>',1)
    for c in spec['chapters']:
        if chapter and chapter!=c['id']:continue
        plain=r.get('chapter_guides',{}).get(c['id'])
        if not plain:continue
        start=page.find('<section id="'+e(c['id'])+'"')
        pos=page.find('</header>',start)
        if start<0 or pos<0:raise ValueError('V2章节锚点缺失')
        answer=''
        if plain.get('conclusion'):
            ids=plain.get('answer_refs',c.get('refs',[]))
            citations='<span class="refs">'+''.join('<a href="#src-'+e(id)+'">['+e(id)+']</a>' for id in ids)+'</span>'
            answer='<article class="v2-answer" aria-label="本章的结论与判断"><h3>本章的结论与判断</h3><p><strong>结论：</strong>'+e(plain['conclusion'])+'</p><p><strong>我的判断：</strong>'+e(plain['judgment'])+'</p><p class="v2-answer-boundary"><strong>判断边界与后续观察：</strong>'+e(plain['boundary'])+'</p><div class="v2-answer-state">'+e(plain.get('answer_state','研究总结'))+citations+'</div></article>'
        panel='<div class="v2-summary"><div><span class="v2-tag">这章在回答什么</span><p>'+e(plain['question'])+'</p></div><div><span class="v2-tag">请记住这一步推断</span><p>'+e(plain['logic'])+'</p></div>'+answer+'</div>'
        pos+=len('</header>');panel+=contract_answers_html(spec,c['id'],bool(chapter));page=page[:pos]+panel+page[pos:]
    return page

START_CSS='''*{box-sizing:border-box}body{margin:0;background:#f2f4ef;color:#163e45;font-family:Microsoft YaHei,Arial,sans-serif}main{max-width:1160px;margin:auto;padding:48px 28px}h1{font-size:42px;max-width:800px;line-height:1.35}h2{font-size:25px}p{line-height:1.9}small{color:#617c7f}.eyebrow{font-size:12px;letter-spacing:.16em;color:#6d8a87}.grid{display:grid;grid-template-columns:1fr 1fr;gap:20px}.box{background:#fffdf8;padding:28px;border:1px solid #d3dfd5;border-radius:18px;margin:20px 0}.box label{display:block;line-height:1.8;margin:14px 0}input,textarea,select{display:block;width:100%;font:inherit;color:inherit;border:1px solid #b7ccc5;background:white;border-radius:8px;padding:12px}textarea{min-height:85px}button,.pill{display:inline-block;font:inherit;padding:11px 18px;border:1px solid #b3ccc3;border-radius:9px;background:#143e45;color:white;cursor:pointer;margin:6px 4px 6px 0}a{color:#126e78}#status{min-height:28px}.checks input{display:inline;width:auto;margin-right:10px}li{line-height:2}.flow{display:grid;grid-template-columns:repeat(4,1fr);gap:10px}.flow div{padding:18px;background:#e6efeb;border-radius:10px}footer{font-size:13px;line-height:1.8}@media(max-width:750px){main{padding:24px 16px}h1{font-size:31px}.grid,.flow{grid-template-columns:1fr}}@media print{button{display:none}.box{break-inside:avoid}}'''

def render_start(company,code='',profile='general'):
    fields=[('purpose','本次只回答一个什么问题？','例如：增长还能持续吗？先说明公司、业务与研究期限。'),('cutoff','我们站在哪个时点看？','分别填写历史判断截止、新增观察与未来预测期。'),('model','谁付钱，公司做什么？','写出客户、产品、收费方式、渠道和交付责任。'),('drivers','先检查哪三个变量？','根据业态选择数量/单价、续费/留存、订单/交付、利差/风险等。'),('conflict','目前最矛盾的一组变化？','例如：收入升而现金降；用户升而单客收入降。'),('hypothesis','优先解释、替代解释与区分证据？','把每个“所以”接到可观察变量。'),('unknown','最影响结论的三个缺口？','写缺什么、影响什么、去哪找、何时停止计算。'),('next','下一步交给谁、做什么？','把新原数核验、口径裁决、研究讨论和正式签署分开。')]
    form=''.join('<label>'+e(label)+'<textarea data-field="'+key+'" placeholder="'+e(placeholder)+'"></textarea></label>' for key,label,placeholder in fields)
    metadata=json.dumps({'company':company,'code':code,'profile':profile},ensure_ascii=False).replace('<','\\u003c')
    js='''const meta=JSON.parse(document.getElementById('project-meta').textContent), key='research-start-v2:'+meta.company+':'+location.pathname;const fields=[...document.querySelectorAll('[data-field]')],checks=[...document.querySelectorAll('.checks input')];const status=document.getElementById('status');function snapshot(){return {schema_version:1,kind:'research-planning-draft',human_confirmation:false,company:meta.company,code:meta.code,profile:meta.profile,fields:Object.fromEntries(fields.map(x=>[x.dataset.field,x.value])),personal_checklist:checks.map(x=>x.checked)}}function save(){try{localStorage.setItem(key,JSON.stringify(snapshot()));status.textContent='已保存到当前浏览器；未写入事实库或项目底稿。'}catch(e){status.textContent='浏览器未允许本地保存，请下载草稿备份。'}}function restore(v){if(v.company!==meta.company||v.kind!=='research-planning-draft')throw Error('不是当前公司的研究草稿');fields.forEach(x=>x.value=v.fields?.[x.dataset.field]||'');checks.forEach((x,i)=>x.checked=Boolean(v.personal_checklist?.[i]))}try{const v=localStorage.getItem(key);if(v)restore(JSON.parse(v))}catch(e){status.textContent='历史草稿未载入，可导入此前下载的草稿。'}fields.concat(checks).forEach(x=>x.addEventListener('input',save));function download(text,name,type){const u=URL.createObjectURL(new Blob([text],{type})),a=document.createElement('a');a.href=u;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(u),1000)}document.getElementById('json').onclick=()=>download(JSON.stringify(snapshot(),null,2),meta.company+'-研究草稿.json','application/json');document.getElementById('md').onclick=()=>download('# '+meta.company+' 研究简报草稿\\n\\n本文件为个人研究计划，不代表Fact、研究结论采纳或签署。\\n\\n'+fields.map(x=>'## '+x.parentElement.firstChild.textContent+'\\n\\n'+(x.value||'待填写')+'\\n').join('\\n'),meta.company+'-研究简报草稿.md','text/markdown');document.getElementById('import').onchange=async ev=>{try{restore(JSON.parse(await ev.target.files[0].text()));save()}catch(e){status.textContent='导入失败：'+e.message}};document.getElementById('print').onclick=()=>print();'''
    # JS literals need real newline escape sequences rather than doubled backslashes.
    js=js.replace('\\\\n','\\n')
    return '<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+e(company)+'｜研究起步台</title><style>'+START_CSS+'</style><main><div class="eyebrow">RESEARCH WORKBENCH / V2.0</div><h1>先想清一个问题，再让证据推动判断。</h1><p>'+e(company)+' '+e(code)+' · 行业适配：'+e(profile)+'。填写简报后，让Agent据此推进研究。此页是可保存、可导入导出的个人计划入口。</p><div class="flow"><div>01 定问题与时点</div><div>02 证据与可比性</div><div>03 机制与替代解释</div><div>04 条件未来与复盘</div></div><div class="grid"><section class="box"><h2>你的研究简报</h2>'+form+'<button id="md">下载中文简报</button><button id="json">备份草稿</button><label>导入同公司草稿<input id="import" type="file" accept="application/json,.json"></label><p id="status" role="status">草稿只保存在浏览器；下载后可交给Agent。</p></section><div><section class="box"><h2>一次合作分四种确认</h2><ol><li>原数核验：展示原页、值、期间、单位与主体。</li><li>用途裁决：这些数是否能用于这项比较？</li><li>研究讨论：哪种解释优先，什么会改判？</li><li>验收签署：只记录真实授权与本版完成范围。</li></ol><p>同来源、同期间、同单位可组成一批。有效旧Fact按当前绑定复用；新公司需独立材料和授权。</p></section><section class="box checks"><h2>个人准备清单</h2>'+''.join('<label><input type="checkbox">'+e(x)+'</label>' for x in ['已确定研究问题与截止时点','已选当前公司原始材料与合同','已识别主体、单位、期间和分类断点','已找到需要解释的变化或分化','已写替代解释与下一项区分证据','已列量价成本资本的情景条件'])+'<small>勾选只记个人进度，不会确认Fact或关闭合同。</small></section><section class="box"><h2>让报告更容易被理解</h2><p>每章用一句判断开头，接两三组关键数字，讲清机制和替代解释，再说明未来观察什么。一图只回答一个问题，术语给日常解释，精确值和原页放展开层。</p><p>消费看量价与渠道；工业看订单、交付与产能；订阅看客户、留存与单客收入；金融看利差、信用与资本约束。</p><button id="print">打印计划</button></section></div></div><footer>草稿与事实账本分开。窗口中的原数确认继续由当前项目ReviewStore维护；此页不提交核验、不签名、不产生投资行动。</footer></main><script id="project-meta" type="application/json">'+metadata+'</script><script>'+js+'</script></html>'

def build_start(project):
    p=Path(project).resolve();settings=json.loads((p/'project.json').read_text(encoding='utf-8'));out=p/'outputs/研究起步台.html';out.parent.mkdir(exist_ok=True)
    out.write_text(render_start(settings['company'],settings.get('code',''),settings.get('profile','general')),encoding='utf-8')
    brief=p/'work/research-brief-v2.md'
    if not brief.exists():brief.write_text('# '+settings['company']+'研究简报\n\n状态：待填写的计划，不是Fact、结论采纳或签署。\n\n研究问题：\n\n历史判断截止／新增观察期／预测期：\n\n客户、产品、渠道与收费：\n\n三项关键变量：\n\n最需要解释的变化：\n\n优先解释／替代解释／区分证据：\n\n关键缺口及停止条件：\n\n下一步人机分工：\n',encoding='utf-8')
    return {'output':str(out),'brief':str(brief),'state':'planning-only','human_confirmation':False}


def review_groups(records,limit=8):
    """Read-only, binding-preserving disclosure batches. Missing metadata stays separate."""
    import hashlib
    if not 1<=limit<=10:raise ValueError('批次数量须为1—10')
    groups={}
    for r in records:
        if r.get('effective_state',r.get('state'))!='Unknown' or r.get('kind')!='disclosure':continue
        scope=r.get('scope') if isinstance(r.get('scope'),dict) else {}
        sources=r.get('sources',[])
        identities=[{k:x.get(k) for k in ('source_id','id','path','sha256') if x.get(k)} for x in sources if isinstance(x,dict)]
        complete=bool(r.get('binding') and identities and all(scope.get(k) for k in ('period','entity','unit','currency','basis')) and all(x.get('source_id') or x.get('id') or x.get('path') for x in identities))
        key=json.dumps([identities,[scope.get(k) for k in ('period','entity','unit','currency','basis')]],ensure_ascii=False,sort_keys=True) if complete else 'single:'+str(r['id'])
        row={k:r.get(k) for k in ('id','claim','value','scope','sources','binding')};row['metadata_complete_for_grouping']=complete
        groups.setdefault(key,[]).append(row)
    out=[]
    for rows in groups.values():
        for i in range(0,len(rows),limit):
            chunk=rows[i:i+limit];payload=json.dumps(chunk,ensure_ascii=False,sort_keys=True,separators=(',',':'));digest=hashlib.sha256(payload.encode()).hexdigest()
            out.append({'id':'BATCH-'+digest[:12],'display_sha256':digest,'kind':'disclosure-review-preview','human_confirmation':False,'items':chunk,'note':'导出后按实际原页核验；只对真实答复明确覆盖项目提交原接口，并使用展示binding。未提交任何确认。'})
    return out

def render_review_preview(company,records):
    groups=review_groups(records);body=[]
    for g in groups:
        rows=[[r['id'],r.get('claim',''),r.get('value',''),json.dumps(r.get('scope'),ensure_ascii=False),json.dumps(r.get('sources'),ensure_ascii=False),r.get('binding') or '缺绑定，须补齐后重展示'] for r in g['items']]
        body.append('<section class="box"><h2>'+e(g['id'])+'</h2><p>展示指纹：'+e(g['display_sha256'])+'</p>'+table(['ID','原披露字段','原值','期间/主体/单位','原件位置','当前绑定'],rows)+'<p>定义或复杂脚注需单独核对；元数据不齐的记录单独列示，不自动归成同口径一批。</p></section>')
    payload=json.dumps({'company':company,'batches':groups,'human_confirmation':False},ensure_ascii=False).replace('<','\\u003c')
    js="document.getElementById('freeze').onclick=()=>{const raw=document.getElementById('batch-data').textContent,u=URL.createObjectURL(new Blob([raw],{type:'application/json'})),a=document.createElement('a');a.href=u;a.download='原数核验批次展示.json';a.click();setTimeout(()=>URL.revokeObjectURL(u),1000)}"
    return '<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+e(company)+'｜原数批次预览</title><style>'+START_CSS+CSS+'</style><main><div class="eyebrow">REVIEW PREVIEW / NO CONFIRMATION SUBMITTED</div><h1>'+e(company)+'：按来源和口径集中核验</h1><p>仅展示当前Unknown原披露，不重复列有效Fact。默认每批最多8项。同一原件、期间、主体、单位、币种与报表范围才合组，字段定义与脚注仍须逐项核对。</p><p>先下载固化展示，再逐批回复“本批全部正确”或列出例外并明确其余正确。用户真实答复到达后，Agent仍须重检来源，按原接口与展示binding逐项提交。口径裁决、研究意见、预测和签署分别处理。</p><button id="freeze">下载固化批次展示</button>'+(''.join(body) if groups else '<section class="box"><h2>当前没有待核的新原披露</h2><p>可以继续分析现有有效事实。确需新增原数时，先登记候选与完整来源。</p></section>')+'<p>本页和下载都不提交Fact、不伪造本人点击。下载文件只是展示快照，变化后的来源须重新展示。</p></main><script id="batch-data" type="application/json">'+payload+'</script><script>'+js+'</script></html>'
