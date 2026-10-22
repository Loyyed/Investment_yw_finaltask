"""Project discovery and explicit legacy links, without migrating authority."""
from pathlib import Path
import hashlib,json,subprocess,sys
from .core import ReviewStore,WorkbenchError,read_json,save_json,sha,contained
from .research import research_summary

def links(root):
    return read_json(Path(root)/'runtime/linked-projects.json',{'projects':[]})['projects']

def inventory(root):
    root=Path(root).resolve(); result={}
    if (root/'project.json').is_file():result[root.name]={'path':root,'mode':'generic'}
    elif (root/'projects').exists():
        for p in sorted((root/'projects').iterdir()):
            if p.is_dir() and not p.is_symlink() and (p/'project.json').is_file():result[p.name]={'path':p,'mode':'generic'}
    for r in links(root):
        p=Path(r['path']).resolve()
        if p.is_dir():result[r['id']]={'path':p,'mode':r['mode'],'label':r['label']}
    return result

def link_project(root,path,label):
    p=Path(path).resolve()
    if not p.is_dir():raise WorkbenchError('请选择已经存在的公司工作空间目录')
    mode='generic' if (p/'project.json').is_file() else 'legacy' if (p/'scripts/review_store.py').is_file() and (p/'evidence/review-state.json').is_file() else None
    if not mode:raise WorkbenchError('目录须包含本工作台的project.json，或原工作空间的ReviewStore与核验账本')
    if mode=='legacy' and not label.strip():raise WorkbenchError('请填写公司显示名称')
    rows=links(root); key='linked-'+hashlib.sha256(str(p).encode()).hexdigest()[:12]
    rows=[r for r in rows if r['id']!=key]+[{'id':key,'path':str(p),'label':label.strip() or p.name,'mode':mode}]
    save_json(Path(root)/'runtime/linked-projects.json',{'projects':rows})
    return key

def project_info(entry):
    if entry['mode']=='generic':return read_json(entry['path']/'project.json')
    return {'company':entry.get('label',entry['path'].name),'code':'','profile':'existing','signature_status':'查看原项目真实签署记录'}

def selected_state(entry,key):
    p=entry['path'];settings=project_info(entry)
    if entry['mode']=='legacy':
        try:process=subprocess.run([sys.executable,str(Path(__file__).with_name('legacy_reader.py')),str(p)],capture_output=True,text=True,encoding='utf-8',timeout=90)
        except subprocess.TimeoutExpired:raise WorkbenchError('原工作空间读取超过90秒，请检查原接口；不使用旧缓存冒充当前Fact')
        try:data=json.loads(process.stdout)
        except ValueError:raise WorkbenchError('原工作空间读取失败：'+process.stderr[-1000:])
        if process.returncode or data.get('error'):raise WorkbenchError('原项目动态核验接口失败：'+data.get('error',process.stderr[-1000:]))
        records=data['records'];result={**data,'delegations':[],'report_binding':None,'content_approved':False}
    else:
        s=ReviewStore(p);records=s.records()
        try:binding=s.report_binding()
        except (WorkbenchError,OSError,KeyError):binding=None
        result={'records':records,'sources':s.source_rows(),'delegations':s._read()['delegations'],'report_binding':binding,
                'content_approved':s.report_approved(),'contracts':read_json(p/'work/workbench-contracts.json',{'contracts':[]})['contracts'],
                'documents':[{'path':r,'title':Path(r).stem} for r in ('work/yearly-changes.md','work/claim-notes.md','docs/acceptance.md') if (p/r).is_file()]}
        result['signatures']=[e['data'] for e in s._read()['events'] if e['action']=='report-signature-recorded']
        result['current_signature']=next((r for r in reversed(result['signatures']) if r['report_binding']==binding and result['content_approved']),None)
        for source in result['sources']:
            try:source['intact']=sha(contained(p,source['path']))==source['sha256']
            except OSError:source['intact']=False
    result.update({'id':key,'mode':entry['mode'],'path':str(p),'settings':settings,
                   'next_review_id':read_json(p/'work/workbench-ui-navigation.json',{}).get('next_review_id',''),
                   'counts':{'Fact':sum(r['effective_state']=='Fact' for r in records),'Unknown':sum(r['effective_state']=='Unknown' for r in records),'total':len(records)},
                   'research':research_summary(p,records),'draft':read_json(p/'work/report-draft.json',{}),
                   'models':read_json(p/'work/model-scenarios.json',{'scenarios':[]})['scenarios'],
                   'prompt':f'请读取 {p.as_posix()}/AGENTS.md 和会话交接/CURRENT.md，使用本项目当前ReviewStore核验有效事实与来源。按实际合同执行，记录年度重大变化、修正和Unknown，完成经营、财务、行业、情景及报告。先保留可复查底稿，最终意见由我确认。'})
    from .methods import plan_view
    result["research_plan"]=plan_view(p,records)
    from .materials import material_view
    result["materials"]=material_view(p)
    return result
