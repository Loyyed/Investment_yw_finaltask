"""Isolated, read-only adapter. The legacy project's own ReviewStore is authoritative."""
import hashlib
import json
from pathlib import Path
import sys

def snapshot(path):
    root=Path(path).resolve()
    sys.path.insert(0,str(root/'scripts'))
    from review_store import ReviewStore
    store=ReviewStore(root)
    rows=[]; domains={}
    methods=['facts','change_facts','lec03_agent_facts','m01_scale_facts','m01_metric_facts','m01_disclosure_facts']
    candidates=store.list_candidates()
    valid={r['id'] for r in store.facts()}
    domains['facts']=len(valid)
    def normalize(r,domain,index):
        calc=r.get('calculation',{})
        claim=r.get('claim') or r.get('metric') or r.get('label') or calc.get('label') or r.get('id') or '独立核验记录'
        original_id=r.get('id',str(index))
        source_path=r.get('pdf_path','')
        location=r.get('location') or ('PDF '+str(r['page'])+'页' if r.get('page') else '')
        scope=r.get('scope') or calc.get('scope') or r.get('support_boundary','')
        unit=r.get('unit') or calc.get('unit') or ('%' if 'percent' in r else '')
        value=r.get('value',calc.get('value',r.get('percent')))
        return {'id':original_id if domain=='facts' else domain+':'+original_id,'original_id':original_id,'domain':domain,
                'claim':claim,'kind':'disclosure' if domain=='facts' or domain=='m01_disclosure_facts' else 'derived',
                'value':value,'scope':{'period':r.get('period',str(r.get('year',''))),'entity':'当前项目披露主体','basis':str(scope),'unit':unit,'definition':claim},
                'sources':[{'source_id':source_path,'location':location}] if source_path else [],
                'effective_state':r.get('state','Unknown'),'verifier':r.get('verifier') or r.get('actor',''),'confirmed_at':r.get('confirmed_at',r.get('registered_at','')),
                'binding':r.get('binding',r.get('binding_digest',r.get('source_binding',''))),
                'issues':[r['stale_reason']] if r.get('stale_reason') else [],
                'support_boundary':r.get('support_boundary',''),'unsupported_boundary':r.get('unsupported_boundary',''),
                'formula':calc.get('formula',r.get('formula','')),'details':r}
    for i,r in enumerate(candidates):
        item=normalize(r,'facts',i); item['effective_state']='Fact' if r['id'] in valid else 'Unknown'
        rows.append(item)
    for method in methods[1:]:
        values=getattr(store,method)();domains[method]=len(values)
        rows.extend(normalize(r,method,i) for i,r in enumerate(values))
    manifest=root/'sources/manifest.json'; sources=[]
    if manifest.exists():
        data=json.loads(manifest.read_text(encoding='utf-8-sig'))
        for r in (data if isinstance(data,list) else data.get('sources',[])):
            relative=r.get('pdf',r.get('path',''))
            p=(root/relative).resolve()
            if not relative or not p.is_relative_to(root):continue
            actual=hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else ''
            expected=r.get('pdf_sha256',r.get('sha256',''))
            sources.append({'id':relative,'path':relative,'original_name':p.name,'sha256':expected,
                            'role':'年度报告','purpose':str(r.get('year',''))+'年披露','intact':actual==expected and bool(actual)})
    contracts=[]
    for relative in ('work/20261010-contract-map.json','work/20261012-supplement/contract-map.json'):
        p=root/relative
        if not p.is_file():continue
        data=json.loads(p.read_text(encoding='utf-8-sig'))
        groups=data if isinstance(data,list) else data.get('contracts',[])
        for c in groups:
            clauses=c.get('clauses',[])
            if not isinstance(clauses,list):
                clauses=[r for r in data.get('clauses',[]) if r['id'].startswith(c['name']+'-')]
            contracts.append({'name':c.get('name',c.get('contract','合同')),'path':c.get('current_executed_copy',c.get('executed_copy','')),
                              'original_sha256':c.get('original_sha256',''),'clauses':clauses,'authority':'当前合同映射；验收与数字Fact分别检查'})
    documents=[]
    for relative in ('outputs/lec03-final-results.md','outputs/channel-expense-capital-analysis.md','outputs/task06-industry-advantage.md',
                     'outputs/task05-business-model-map.md','work/20261012-supplement/conflict-register.md','docs/20261012-next-task-checklist.md',
                     'docs/task-status.md','work/yearly-changes.md'):
        p=root/relative
        if p.is_file():documents.append({'path':relative,'title':p.stem,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
    adoption=root/'evidence/20261013-research-opinion-adoption.json'
    sections={}
    for key,relative in [('business','outputs/task05-business-model-map.md'),('financial','outputs/channel-expense-capital-analysis.md'),
                         ('industry','outputs/task06-industry-advantage.md'),('narrative','outputs/lec03-final-results.md')]:
        file=root/relative
        if file.is_file():sections[key]={'path':relative,'content':file.read_text(encoding='utf-8-sig'),'sha256':hashlib.sha256(file.read_bytes()).hexdigest()}
    return {'records':rows,'sources':sources,'domains':domains,'contracts':contracts,'documents':documents,
            'research_sections':sections,
            'opinion_adoption':json.loads(adoption.read_text(encoding='utf-8-sig')) if adoption.is_file() else None}

if __name__=='__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    try: print(json.dumps(snapshot(sys.argv[1]),ensure_ascii=False))
    except Exception as exc:
        print(json.dumps({'error':str(exc)},ensure_ascii=False));sys.exit(1)
