"""Material navigation and conservative proxy descriptions; no Fact ledger writes."""
from pathlib import Path
from .core import read_json

LEVELS={'S0':'精确目标字段','S1':'有边界的窄代理','S2':'交叉解释线索','S3':'背景/目录','S4':'排除'}
def proxy_gate(level,target,observed):
    if level not in LEVELS:raise ValueError('代理等级须为S0—S4')
    return {'level':level,'label':LEVELS[level],'target':target,'observed':observed,
            'state':'排除' if level=='S4' else '待原件及人工裁决' if level=='S0' else 'Unknown（原目标）',
            'can_close_gap':False,'allowed_use':{'S0':'原值须另经当前核验接口确认；等级标签不产生Fact',
             'S1':'只描述改名后的窄变量','S2':'只能结合独立证据解释，不合成需求/品牌指数',
             'S3':'只作背景和取证目录','S4':'不进入目标计算或正式判断'}[level]}

def material_view(project):
    p=Path(project);catalog=read_json(p/'work/materials-catalog.json',{'files':[],'reproductions':[]})
    proxies=read_json(p/'work/proxy-register.json',{'proxies':[]})
    catalog['proxies']=[{**r,**proxy_gate(r['level'],r['target'],r['observed'])} for r in proxies['proxies']]
    return catalog

def materials_report(value):
    lines=['## 材料管理、复现与代理边界','','完整原件留本地；目录哈希、计算复现与人工核验是不同事项。','',
           '| 复现包 | 计算结果 | 展示文件 |','| --- | --- | --- |']
    for r in value.get('reproductions',[]):lines.append('| '+r['package']+' | '+('诊断CSV一致' if r['csv_match'] else '待排差')+' | '+r['html_status']+' |')
    lines+=['','| 目标 | 可观察字段 | 代理分级 | 使用边界 |','| --- | --- | --- | --- |']
    for r in value.get('proxies',[]):lines.append('| '+' | '.join(str(r[k]).replace('|','／') for k in ['target','observed','level','allowed_use'])+' |')
    return '\n'.join(lines)+'\n'
