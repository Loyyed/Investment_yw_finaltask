"""Read current project validators; never infer adoption from a cached summary."""
from pathlib import Path
import hashlib,importlib.util

SPECS=[('P03','年度资本增量意见','cash_path_review.py','current_p03_adoption','evidence/cash-path-content-review.json'),('P04','新版第六七增量内容','task67_content_review.py','current_p04_adoption','evidence/task67-content-review.json')]

def current_reviews(root):
    root=Path(root);result=[]
    for ident,label,filename,callback,ledger in SPECS:
        script=root/'scripts'/filename
        if not (root/ledger).is_file():continue
        status={'status':'unavailable','reason':'当前项目缺少独立认可校验器'}
        if script.is_file():
            try:
                name='_project_review_'+hashlib.sha256(str(script.resolve()).encode()).hexdigest()[:16]
                spec=importlib.util.spec_from_file_location(name,script);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
                status=getattr(module,callback)(root)
                if not isinstance(status,dict):raise TypeError('认可接口未返回对象')
            except Exception as exc:status={'status':'unavailable','reason':type(exc).__name__+': '+str(exc)}
        result.append({'id':ident,'label':label,'status':status.get('status','unavailable'),'source':ledger,'validator':'scripts/'+filename,'details':status,'new_signature_created':status.get('new_signature_created'),'formally_closed':status.get('contracts_formally_closed',status.get('contract_formally_closed'))})
    return result
