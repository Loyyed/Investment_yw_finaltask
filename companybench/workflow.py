"""Research drafts, auditable scenario arithmetic and deterministic report assembly."""
from pathlib import Path
from decimal import Decimal,localcontext,ROUND_HALF_UP
import html,re
from .core import ReviewStore,WorkbenchError,read_json,save_json,atomic_text,digest,number,now,locked,sha
from datetime import date

SECTIONS=[('business','商业模式与收入来源'),('financial','成本、资本与现金回报'),('industry','行业、竞争与优势'),
          ('narrative','管理层叙事与反证'),('forecast','预测与情景假设'),('valuation','估值与证券权利'),('risk','风险、替代解释与跟踪条件')]

def save_draft(project,data):
    store=ReviewStore(project)
    draft={'title':str(data.get('title',''))[:200],'summary':str(data.get('summary',''))[:30000],
           'information_cutoff':str(data.get('information_cutoff',''))[:50],
           'sections':{key:str(data.get('sections',{}).get(key,''))[:50000] for key,_ in SECTIONS},
           'updated_at':now(),'status':'研究草稿；尚未形成新的事实或内容审阅'}
    with locked(store.root):
        ledger=store._read();store._event(ledger,'research-draft-saved',{'draft':draft});store._save(ledger)
        save_json(store.root/'work/report-draft.json',draft)
    return draft

def save_contracts(project,data):
    store=ReviewStore(project);contracts=[];sources={s['id'] for s in store.source_rows()}
    for c in data.get('contracts',[]):
        if not str(c.get('name','')).strip():raise WorkbenchError('合同名称不能为空')
        sid=c.get('source_id','')
        if sid and sid not in sources:raise WorkbenchError('合同来源未导入')
        clauses=[]
        for r in c.get('clauses',[]):
            if not str(r.get('requirement','')).strip():continue
            evidence=[str(p) for p in r.get('evidence',[]) if p]
            from .core import contained
            for p in evidence:contained(store.root,p)
            clauses.append({'id':str(r.get('id','')),'requirement':str(r['requirement']),
                            'status':str(r.get('status','待完成')),'evidence':evidence,
                            'checked':bool(r.get('checked')),'review_note':str(r.get('review_note','')),
                            'note':'用户记录的验收状态；不自动核准引用Fact'})
        contracts.append({'name':str(c['name']),'source_id':sid,'clauses':clauses})
    value={'contracts':contracts,'updated_at':now()}
    with locked(store.root):
        ledger=store._read();store._event(ledger,'contract-map-saved',value);store._save(ledger)
        save_json(store.root/'work/workbench-contracts.json',value)
    return value

def scenario(project,data):
    """FCFF model in yuan, shares in shares. Assumptions always remain Forecast."""
    store=ReviewStore(project); rows={r['id']:r for r in store.records()}
    base_id=data.get('base_id','');base=None;binding=None
    if base_id:
        row=rows.get(base_id)
        if not row or row['effective_state']!='Fact':raise WorkbenchError('基期FCFF记录必须是当前有效Fact')
        scope=row.get('scope',{})
        if scope.get('unit') not in ('元','人民币元') or scope.get('currency') not in ('CNY','人民币'):
            raise WorkbenchError('本模型只接收人民币元FCFF；请先明确转换，不能混入亿元或利润')
        if not data.get('fcff_definition_confirmed'):raise WorkbenchError('请确认选中记录是FCFF，而非净利润或经营现金流')
        definition=scope.get('definition','')
        if 'FCFF' not in definition.upper() and '企业自由现金流' not in definition:
            raise WorkbenchError('选中记录的定义没有明确FCFF／企业自由现金流，请先核对指标定义')
        base=number(row.get('value'));binding=row['binding']
    else:base=number(data.get('base_fcff',''))
    reason=str(data.get('assumption_note','')).strip()
    if not reason:raise WorkbenchError('请说明假设来源、范围和失效条件')
    years=int(data.get('years','0'))
    if not 1<=years<=15:raise WorkbenchError('预测期为1—15年')
    growth=number(data.get('growth',''))/100;wacc=number(data.get('wacc',''))/100;terminal=number(data.get('terminal_growth',''))/100
    debt=number(data.get('net_debt',''));shares=number(data.get('shares',''))
    if base<=0 or shares<=0:raise WorkbenchError('本简化模型适用于正的基期FCFF和股数；其他企业需另建模型')
    if growth<=-1 or terminal<=-1 or not 0<wacc<=1 or wacc<=terminal:raise WorkbenchError('增长率须大于-100%，折现率须在0—100%且大于永续增长率')
    with localcontext() as ctx:
        ctx.prec=48;cash=base;flows=[];present=Decimal(0)
        for year in range(1,years+1):
            cash*=1+growth;pv=cash/(1+wacc)**year;present+=pv
            flows.append({'year':year,'fcff':str(cash),'discount_factor':str((1+wacc)**year),'present_value':str(pv)})
        terminal_value=cash*(1+terminal)/(wacc-terminal);terminal_pv=terminal_value/(1+wacc)**years
        ev=present+terminal_pv;equity=ev-debt;price=equity/shares
        result={'enterprise_value_yuan':str(ev),'equity_value_yuan':str(equity),'value_per_share_yuan':str(price),
                'display_per_share':str(price.quantize(Decimal('.01'),rounding=ROUND_HALF_UP)),
                'terminal_share_percent':str(terminal_pv/ev*100)}
    payload={'name':str(data.get('name','未命名情景'))[:100],'kind':'Forecast','base_id':base_id,'base_binding':binding,
             'inputs':{'base_fcff':str(base),'years':years,'growth_percent':str(growth*100),'wacc_percent':str(wacc*100),
                       'terminal_growth_percent':str(terminal*100),'net_debt_yuan':str(debt),'shares':str(shares)},
             'assumption_note':reason,'flows':flows,'result':result,
             'formula':'FCFF_t=FCFF_0*(1+g)^t; EV=ΣFCFF_t/(1+WACC)^t+FCFF_n*(1+g_terminal)/(WACC-g_terminal)/(1+WACC)^n; equity=EV-net_debt; per_share=equity/shares',
             'boundary':'假设情景，不是Fact、目标价或买卖结论；未替代现金流口径、资本结构、非经营资产和证券权利核验',
             'time':now(),'engine_sha256':sha(Path(__file__))}
    payload['id']='MODEL-'+digest(payload)[:12]
    with locked(store.root):
        value=read_json(store.root/'work/model-scenarios.json',{'scenarios':[]});value['scenarios'].append(payload)
        ledger=store._read();store._event(ledger,'forecast-scenario-created',payload);store._save(ledger)
        save_json(store.root/'work/model-scenarios.json',value)
    return payload

def model_current(model,records):
    if model.get('engine_sha256')!=sha(Path(__file__)):return False
    if not model.get('base_id'):return True
    row=next((r for r in records if r['id']==model['base_id']),{})
    return row.get('effective_state')=='Fact' and row.get('binding')==model.get('base_binding')

def cell(value):return str(value if value is not None else '未提供').replace('|','／').replace('\n','；')

def report_text(state):
    d=state.get('draft',{});company=state['settings']['company'];rows=state['records'];sources=state['sources']
    lines=['# '+(d.get('title') or company+'证券投资分析报告'),'',
           '状态：证据与研究草稿的确定性汇编；结论、预测和最终决定等待人工审阅。本版保存生成时的核验状态，后续复用需再次调用当前事实接口。','',
           '研究主体：'+company+'；信息截止：'+(d.get('information_cutoff') or 'Unknown（待确定）')+'。','',
           '## 研究意见摘要','',d.get('summary') or (state.get('opinion_adoption') or {}).get('accepted_opinion') or 'Unknown：尚未填写总判断，系统不从收入增长自动生成投资结论。','',
           '## 研究范围与依据','',f"当前有效Fact {state['counts']['Fact']}条，Unknown {state['counts']['Unknown']}条。事实有效性以当前核验接口为准；原值、计算、研究意见和假设分别保留。",'']
    for key,title in SECTIONS:
        existing=state.get('research_sections',{}).get(key)
        content=d.get('sections',{}).get(key)
        if not content and existing:
            content='原项目研究底稿：'+existing['path']+'；SHA-256 '+existing['sha256']+'。本节保留原文及其状态，来源有效性见当前接口，不因重新汇编新增核准。\n\n'+existing['content']
        lines+=['## '+title,'',content or 'Unknown：本部分尚无研究意见；需补对应材料和过程底稿。','']
    opinions=[r for r in rows if r.get('kind') in ('interpretation','forecast','decision','unknown')]
    lines+=['## 研究命题与反证','']
    if not opinions:lines+=['Unknown：尚未登记研究命题。','']
    for r in opinions:
        lines+=['### '+r['id']+' '+r['claim'],'', '状态：'+r['effective_state']+'。','']
        for key,label in [('evidence_ids','引用证据'),('support','支持'),('challenge','挑战'),('alternative','替代解释'),('invalidation','失效条件'),('support_boundary','支持边界')]:
            if r.get(key):lines += [label+'：'+cell(r[key]),'']
        invalid=[rid for rid in r.get('evidence_ids',[]) if next((a for a in rows if a['id']==rid),{}).get('effective_state')!='Fact']
        if invalid:lines+=['当前未核准引用：'+', '.join(invalid)+'；不能作为已经核验的论据。','']
    lines+=['## 预测与估值计算底稿','']
    if not state.get('models'):lines+=['Unknown：没有情景模型。不得用缺省折现率、增长率和股数补出价格。','']
    for m in state.get('models',[]):
        active=model_current(m,rows)
        lines+=['### '+m['name'],'','状态：Forecast；'+('当前基期引用有效。' if active else '基期事实已变化，本情景需重算。'),'']
        lines+=['输入与单位：'+cell(m['inputs']),'','假设说明：'+m['assumption_note'],'','算式：`'+m['formula']+'`','']
        lines+=['| 预测年 | FCFF（人民币元） | 折现因子 | 现值（人民币元） |','| --- | --- | --- | --- |']
        for f in m['flows']:lines+=['| '+' | '.join(cell(f[k]) for k in ('year','fcff','discount_factor','present_value'))+' |']
        lines+=['','结果（假设情景）：'+cell(m['result']),'',m['boundary'],'']
    lines+=['## 已核验数据与运算','', '| 编号 | 主张 | 数值 | 期间／主体／口径／单位 | 核准身份 | 来源与计算 |','| --- | --- | --- | --- | --- | --- |']
    for r in rows:
        if r['effective_state']!='Fact':continue
        sc=r.get('scope',{});description='；'.join(str(sc.get(k,'')) for k in ('period','entity','basis','definition','unit')) if isinstance(sc,dict) else str(sc)
        proof='；'.join(str(s.get('source_id',''))+' '+str(s.get('location','')) for s in r.get('sources',[]))
        if r.get('formula'):proof+='；算式 '+cell(r['formula'])
        if state['mode']=='legacy' and not proof:proof+='原工作空间独立接口 '+r.get('domain','')+'；对应原核验记录，不扩大为独立因果证明'
        lines+=['| '+' | '.join(cell(v) for v in (r['id'],r['claim'],r.get('value'),description,r.get('verifier',''),proof))+' |']
    lines+=['','## Unknown、待补与停算项','', '| 编号 | 内容 | 原值／状态 | 当前问题／支持边界 |','| --- | --- | --- | --- |']
    for r in rows:
        if r['effective_state']=='Unknown':lines+=['| '+' | '.join(cell(v) for v in (r['id'],r['claim'],r.get('value'),'; '.join(r.get('issues',[])) or r.get('support_boundary','待回到原件核验')))+' |']
    lines+=['','## 材料来源目录','', '| 编号 | 文件 | 角色 | SHA-256 |','| --- | --- | --- | --- |']
    for s in sources:lines+=['| '+' | '.join(cell(v) for v in (s['id'],s.get('original_name',s['path']),s.get('role',''),s.get('sha256','')))+' |']
    if state.get('documents'):
        lines+=['','## 已有底稿与修正记录','']
        lines+=['- '+r['path']+'（原工作空间版本保留；请结合当前有效事实阅读）' for r in state['documents']]
    if state.get('contracts'):
        lines+=['','## 合同执行记录','']
        for c in state['contracts']:
            lines+=['### '+c['name'],'']
            for r in c.get('clauses',[]):lines+=['- '+cell(r.get('id',''))+' '+cell(r.get('requirement',''))+'；'+cell(r.get('status','待完成'))+'；依据 '+cell(r.get('evidence',[]))]
            lines+=['']
    if state.get('research_plan'):
        from .methods import plan_report
        lines+=['',plan_report(state['research_plan'])]
    lines+=['','## 内容审阅与签署','',
           '本版汇编不新增人工确认、不继承历史签名。原事实的核准身份、时间和原授权保持不变；内容审阅与执行／复核签署分别记录。','']
    return '\n'.join(lines)

def export_html(md):
    out=[];table=False
    for line in md.splitlines():
        s=html.escape(line)
        if line.startswith('|'):
            cells=line.strip('|').split('|')
            if all(re.fullmatch(r'\s*:?-+:?\s*',c) for c in cells):continue
            if not table:out.append('<div class="table"><table>');table=True
            out.append('<tr>'+''.join('<td>'+html.escape(c.strip())+'</td>' for c in cells)+'</tr>');continue
        if table:out.append('</table></div>');table=False
        h=re.match(r'^(#{1,3})\s+(.*)',line)
        if h:out.append(f'<h{len(h[1])}>'+html.escape(h[2])+f'</h{len(h[1])}>')
        elif line:out.append('<p>'+s+'</p>')
    if table:out.append('</table></div>')
    return '<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>投资分析报告</title><style>body{font:15px/1.8 "Microsoft YaHei",sans-serif;color:#21312c;max-width:1060px;margin:40px auto;padding:0 28px}h1{font-size:30px}h2{border-top:1px solid #dce4df;padding-top:25px}h3{font-size:17px}table{border-collapse:collapse;width:100%;font-size:12px}td{border:1px solid #dce4df;padding:9px;vertical-align:top;overflow-wrap:anywhere}tr:first-child{background:#eff5f1;font-weight:bold}.table{overflow:auto}p{overflow-wrap:anywhere}@media print{body{margin:0;max-width:none;font-size:11px}h2,h3{break-after:avoid}.table{overflow:visible}tr{break-inside:avoid}@page{size:A4;margin:16mm}}</style><body>'+''.join(out)+'</body></html>'

def generate_report(root,entry,state):
    from .core import contained
    md=report_text(state);fingerprint=report_fingerprint(state,md)
    if state['mode']=='legacy':
        directory=Path(root)/'runtime/generated-reports'/state['id'];relative=''
    else:directory=entry['path']/'outputs/workbench-reports';relative='outputs/workbench-reports/'+fingerprint[:16]+'.md'
    mdpath=directory/(fingerprint[:16]+'.md');htmlpath=mdpath.with_suffix('.html')
    for path,body in ((mdpath,md),(htmlpath,export_html(md))):
        if path.exists() and path.read_text(encoding='utf-8')!=body:raise WorkbenchError('同版本已有不同文件，停止覆盖')
        if not path.exists():atomic_text(path,body)
    snapshot_path=mdpath.with_suffix('.json')
    if not snapshot_path.exists():save_json(snapshot_path,{'schema_version':1,'fingerprint':fingerprint,'state_at_generation':state,
                                                            'note':'报告所用依据快照；当前Fact仍须动态读取，不包含原件文件内容'})
    result={'fingerprint':fingerprint,'path':relative,'md':str(mdpath),'html':str(htmlpath),'record_ids':[r['id'] for r in state['records']],
            'json':str(snapshot_path),
            'status':'待人工内容审阅','generated_at':now(),'mode':state['mode']}
    if state['mode']=='generic':ReviewStore(entry['path']).review_ready(result['record_ids'],relative)
    save_json(Path(root)/'runtime/latest-reports'/f"{state['id']}.json",result)
    return result

def report_fingerprint(state,text=None):
    return digest({'text':report_text(state) if text is None else text,
                   'records':[{k:r.get(k) for k in ('id','binding','effective_state','confirmation_event')} for r in state['records']]})

def record_signature(project,data):
    store=ReviewStore(project)
    if not data.get('authorized'):raise WorkbenchError('需要本人明确确认按所填身份签署')
    executor=str(data.get('executor','')).strip();reviewer=str(data.get('reviewer','')).strip()
    if not executor or not reviewer:raise WorkbenchError('执行人与复核人姓名均需填写')
    try:signature_date=date.fromisoformat(data.get('date',''))
    except (ValueError,TypeError):raise WorkbenchError('请填写真实签署日期，格式YYYY-MM-DD')
    with locked(store.root):
        binding=store.report_binding()
        if data.get('binding')!=binding:raise WorkbenchError('报告或依据已改变，请重新读取并审阅')
        if not store.report_approved():raise WorkbenchError('本版报告内容尚未通过审阅，签署前先完成内容审阅')
        value={'actor':'human-ui','executor':executor,'reviewer':reviewer,'same_person':executor==reviewer,
               'date':str(signature_date),'time':now(),'report_binding':binding,
               'statement_original':'本人在本项目窗口明确授权，按所填执行人与复核人身份签署当前已审阅报告。',
               'identity_note':'执行与复核同人，不作为独立第三方复核' if executor==reviewer else '按本人所填身份记录；不替代核验记录'}
        ledger=store._read();store._event(ledger,'report-signature-recorded',value);store._save(ledger)
    return value
