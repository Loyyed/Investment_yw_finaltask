"""Non-authoritative research plans connecting financial evidence to narratives."""
from pathlib import Path
from copy import deepcopy
from datetime import date
import re
from .core import WorkbenchError,read_json,save_json,digest,now,locked

FINANCIAL=[('revenue','收入','谁购买什么，量、价与结构如何形成收入？'),('cost','成本','毛利怎样经过税费与组织费用形成经营收益？'),
           ('capital','资本投入','增长需提前投入哪些库存、产能和经营资金？'),('cash','现金流','利润怎样经过营运资本和长期投入转为现金？')]
VALUE=[('proposition','候选价值主张','客户为何持续付费？'),('creation','价值创造','资源、活动与时间如何形成产品？'),
       ('delivery','价值交付','渠道、交易及收款安排如何交付？'),('capture','价值获取','公司保留多少收入、利润、现金与资本回报？')]

def template():
    return {'schema_version':1,'information_cutoff':'','analysis_mode':'事后研究','nodes':[
        {'id':key,'layer':layer,'title':title,'question':question,'evidence_ids':[],'evidence_bindings':{},'interpretation':'',
         'alternative':'','unknown':'尚未形成当前项目依据','next_action':'按当前问题定位原件','refutation':'','source_date':'','source_role':'原始披露'}
        for layer,group in [('financial',FINANCIAL),('value',VALUE)] for key,title,question in group],
        'parameters':[],'contract_updates':[],'material_catalog':[]}

def text(v,limit=12000):return str(v if v is not None else '')[:limit]

def save_plan(project,data,records,actor='human-ui'):
    """Save a plan and frozen references, never a Fact/approval/signature."""
    if not isinstance(data,dict):raise WorkbenchError('研究计划须为对象')
    rows={r['id']:r for r in records};plan=template();plan['nodes']=[]
    plan['information_cutoff']=text(data.get('information_cutoff'),50)
    plan['analysis_mode']=text(data.get('analysis_mode','事后研究'),100)
    if plan['analysis_mode'] not in ('事后研究','历史时点决策'):raise WorkbenchError('研究用途须选择事后研究或历史时点决策')
    if plan['information_cutoff']:
        try:date.fromisoformat(plan['information_cutoff'])
        except ValueError:raise WorkbenchError('截止日须为YYYY-MM-DD')
    seen=set()
    for n in data.get('nodes',[]):
        ident=text(n.get('id'),80)
        if not re.fullmatch(r'[A-Za-z0-9_-]+',ident) or ident in seen:raise WorkbenchError('环节编号应唯一且仅含字母、数字、下划线、短横线')
        seen.add(ident)
        if n.get('layer') not in ('financial','value'):raise WorkbenchError('请选择财务经济逻辑或价值叙事')
        ids=n.get('evidence_ids',[])
        if not isinstance(ids,list) or any(not isinstance(i,str) for i in ids):raise WorkbenchError('依据编号须为列表')
        ids=list(dict.fromkeys(ids))
        if any(i not in rows for i in ids):raise WorkbenchError('所选依据编号不存在于当前项目')
        node={k:text(n.get(k)) for k in ['id','layer','title','question','interpretation','alternative','unknown','next_action','refutation','source_date','source_role']}
        node['evidence_ids']=ids;node['evidence_bindings']={i:rows[i].get('binding') for i in ids}
        if node['source_date']:
            try:date.fromisoformat(node['source_date'])
            except ValueError:raise WorkbenchError('来源可获日须为YYYY-MM-DD；未确定可留空')
        plan['nodes'].append(node)
    for key in ('parameters','contract_updates','material_catalog'):
        value=data.get(key,[])
        if not isinstance(value,list) or any(not isinstance(x,dict) for x in value):raise WorkbenchError('计划列表须由对象组成')
        # Persist only explicitly allowed schema fields; caller-provided Fact flags never apply.
        fields={'parameters':['id','label','type','purpose','location','unit','value','record_id','contracts','priority','missing','formula','source_date'],
                'contract_updates':['name','baseline_status','enhancement','gap','parameter_ids','outputs','source_sha256'],
                'material_catalog':['name','role','sha256','location','period','boundary']}[key]
        plan[key]=[{k:(list(map(str,x[k])) if isinstance(x.get(k),list) else text(x[k])) for k in fields if k in x} for x in value]
    plan.update({'updated_at':now(),'author':actor,'status':'研究计划与解释草稿；不新增原值/算术/内容验收或签署'})
    p=Path(project).resolve()
    with locked(p):
        old=read_json(p/'work/research-plan.json',None)
        if old:save_json(p/'work/research-plan-history'/(digest(old)+'.json'),old)
        save_json(p/'work/research-plan.json',plan)
    return plan

def plan_view(project,records):
    value=deepcopy(read_json(Path(project)/'work/research-plan.json',template()));rows={r['id']:r for r in records}
    cutoff=value.get('information_cutoff','')
    for n in value.get('nodes',[]):
        ids=n.get('evidence_ids',[]);issues=[];valid=[]
        for i in ids:
            r=rows.get(i)
            if not r or r.get('effective_state')!='Fact':issues.append(i+' 未获当前有效核准');continue
            if n.get('evidence_bindings',{}).get(i)!=r.get('binding'):issues.append(i+' 引用绑定变化，需重查支持边界');continue
            valid.append(i)
        dated=n.get('source_date','')
        historical=value.get('analysis_mode')=='历史时点决策'
        date_missing=historical and (not cutoff or not dated)
        future=bool(historical and cutoff and dated and dated>cutoff)
        if date_missing:issues.append('历史时点所需的截止日或来源实际可获日期未确定')
        if future:issues.append('材料日期晚于信息截止，不纳入历史时点判断')
        n['valid_evidence_ids']=valid;n['issues']=issues;n['evidence_ready']=bool(ids) and not issues
        n['reasoning_ready']=bool(n.get('interpretation') and n.get('alternative') and n.get('refutation'))
        n['state']='Interpretation' if n['evidence_ready'] and n['reasoning_ready'] else 'Unknown'
        n['boundary']='依据就绪不等同机制成立；最终研究判断由人工确认'
    for q in value.get('parameters',[]):
        rid=q.get('record_id','');r=rows.get(rid)
        q['state']='Fact' if rid and r and r.get('effective_state')=='Fact' else 'Unknown'
        # Predictions and scope decisions cannot be confirmed by attaching an unrelated raw Fact.
        if q.get('type') not in ('原值','已核指标复用'):q['state']='待人工选择' if q.get('value') else 'Unknown'
        elif q['state']=='Fact':
            # Render the authoritative record, not an editable value mislabeled as Fact.
            q['proposed_label']=q.get('label','');q['label']=r.get('claim',rid)
            q['value']=r.get('value');q['unit']=r.get('scope',{}).get('unit','')
            q['input_binding']=r.get('binding');q['support_boundary']=r.get('support_boundary','')
    value['counts']={'nodes':len(value.get('nodes',[])),'evidence_ready':sum(n['evidence_ready'] for n in value.get('nodes',[])),
                     'pending_parameters':sum(q['state']!='Fact' for q in value.get('parameters',[]))}
    return value

def plan_report(plan):
    out=['## 两层商业模式研究与核验计划','',
         '信息截止：'+(plan.get('information_cutoff') or 'Unknown')+'；用途：'+plan.get('analysis_mode','事后研究')+'。计划不是核验账本，新增解释不继承旧签署。','']
    for n in plan.get('nodes',[]):
        out+=['### '+text(n.get('title')),'','问题：'+text(n.get('question')),'',
              '状态：'+n.get('state','Unknown')+'；当前有效引用：'+', '.join(n.get('valid_evidence_ids',[]))+'。','']
        for key,label in [('interpretation','解释草稿'),('alternative','替代解释'),('unknown','Unknown'),('refutation','反证条件'),('next_action','下一步')]:
            out+=[label+'：'+(text(n.get(key)) or '尚未填写'),'']
        if n.get('issues'):out+=['引用问题：'+'；'.join(n['issues']),'']
    out+=['### 尚需核验的指标与参数','', '| 编号 | 指标／参数 | 类型与状态 | 定位／缺口 | 用途 |','| --- | --- | --- | --- | --- |']
    def cell(x):return text(x).replace('|','／').replace('\n','；')
    for q in plan.get('parameters',[]):out+=['| '+' | '.join(cell(v) for v in [q.get('id'),q.get('label'),q.get('type','')+'／'+q.get('state','Unknown'),q.get('location') or q.get('missing'),q.get('purpose')])+' |']
    out+=['','### 原合同状态与本轮优化','']
    for c in plan.get('contract_updates',[]):
        out+=['- '+cell(c.get('name'))+'：旧状态 '+cell(c.get('baseline_status'))+'；本轮 '+cell(c.get('enhancement'))+'；待补 '+cell(c.get('gap'))]
    return '\n'.join(out)+'\n'
