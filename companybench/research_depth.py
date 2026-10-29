"""Exact revenue attribution and a source-linked method library. Never writes reviews."""
from fractions import Fraction as F
from decimal import Decimal, localcontext
from pathlib import Path
import json, argparse

def number(v):
    if isinstance(v, bool) or isinstance(v, float) or v is None:
        raise ValueError('精确输入须为十进制字符串或整数，缺失不补零')
    try:
        d=Decimal(str(v))
        if not d.is_finite(): raise ValueError()
        return F(d)
    except Exception as e: raise ValueError('无效数值') from e

def display(v):
    with localcontext() as ctx:
        ctx.prec=40
        return format(Decimal(v.numerator)/Decimal(v.denominator),'f')

def revenue_bridge(before, after):
    """Each mapping: product -> {revenue, quantity}; same unit and scope required.
    Sequential aggregate: total quantity -> product mix -> within-product ASP.
    Also returns per-product base-period volume/ASP/interaction attribution.
    Fractions preserve an exact identity; ASP includes unobserved within-group mix.
    """
    if not before or set(before)!=set(after):
        raise ValueError('两期产品集合须一致；新业务/退出业务需独立桥接，禁止填零凑齐')
    periods=[]
    for data in (before, after):
        p={}
        for k,row in data.items():
            q=number(row['quantity']);r=number(row['revenue'])
            if q<=0 or r<0:raise ValueError('销量须大于零；负收入/退货须单独建模')
            p[k]=(q,r,r/q)
        periods.append(p)
    b,a=periods;Q0=sum(v[0] for v in b.values());Q1=sum(v[0] for v in a.values())
    R0=sum(v[1] for v in b.values());R1=sum(v[1] for v in a.values())
    volume=(Q1-Q0)*R0/Q0
    mix=Q1*sum((a[k][0]/Q1-b[k][0]/Q0)*b[k][2] for k in b)
    asp=sum(a[k][0]*(a[k][2]-b[k][2]) for k in b)
    per={}
    for k in b:
        q0,r0,p0=b[k];q1,r1,p1=a[k]
        terms={'volume':(q1-q0)*p0,'asp':q0*(p1-p0),'interaction':(q1-q0)*(p1-p0)}
        assert sum(terms.values())==r1-r0
        per[k]={**{n:display(v) for n,v in terms.items()},'change':display(r1-r0),'asp_before':display(p0),'asp_after':display(p1),'quantity_change_percent':display((q1/q0-1)*100),'asp_change_percent':display((p1/p0-1)*100) if p0 else None}
    assert volume+mix+asp==R1-R0
    return {'state':'AgentCalculated','new_fact':False,'order':'总销量→产品销量结构→组内ASP；后序项承接交互，非独立因果贡献',
        'revenue_before':display(R0),'revenue_after':display(R1),'change':display(R1-R0),
        'aggregate':{k:display(v) for k,v in {'volume':volume,'product_mix':mix,'within_product_asp':asp,'residual':R1-R0-volume-mix-asp}.items()},
        'products':per,'exact_identity':True,'boundary':'产品组ASP含渠道、规格、地区及折扣组合；不能命名品牌净贡献。渠道是同一收入另一切面，不能相加。'}

def valuation_audit(model):
    """Check eligibility, not company value. Unknown input stops a formal valuation."""
    problems=[];basis=model.get('basis');discount=model.get('discount_basis')
    if basis not in ('FCFF','FCFE','Dividend'):problems.append('缺少明确FCFF/FCFE/股利口径，利润不能直接改名现金流')
    expected={'FCFF':'WACC','FCFE':'CostOfEquity','Dividend':'CostOfEquity'}.get(basis)
    if expected and discount!=expected:problems.append('现金流与折现率索取权不匹配')
    for key in ('cashflow_defined','reinvestment_defined','financial_scope_defined','asof_defined'):
        if model.get(key) is not True:problems.append('尚未通过：'+key)
    if 'r' not in model or 'g' not in model:problems.append('缺r/g')
    else:
        r=number(model['r']);g=number(model['g'])
        if r<=g or r<=0 or g<=-1:problems.append('终值要求r>g、r>0且g>-1')
    if model.get('risk_free_as_equity_discount'):problems.append('无风险利率不能直接替代股票必要收益率')
    if model.get('double_subtract_working_capital'):problems.append('营运资本重复扣减')
    return {'eligible':not problems,'problems':problems,'state':'MethodCheck','new_fact':False}

def knowledge(query=''):
    rows=json.loads((Path(__file__).parent/'knowledge.json').read_text(encoding='utf-8'))['cards']
    tokens=query.lower().split()
    return [r for r in rows if all(t in json.dumps(r,ensure_ascii=False).lower() for t in tokens)]

def main():
    p=argparse.ArgumentParser(description='研究深化：精确收入桥、估值资格及可检索知识库；不修改Fact')
    p.add_argument('action',choices=['knowledge','bridge','valuation-audit']);p.add_argument('--query',default='');p.add_argument('--input',type=Path)
    a=p.parse_args()
    if a.action=='knowledge':result=knowledge(a.query)
    else:
        if not a.input:p.error('需要--input')
        obj=json.loads(a.input.read_text(encoding='utf-8-sig'))
        result=revenue_bridge(obj['before'],obj['after']) if a.action=='bridge' else valuation_audit(obj)
    print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':main()

def knowledge_page(nonce=''):
    from html import escape
    cards=knowledge()
    body=''.join('<article data-search="'+escape(json.dumps(c,ensure_ascii=False).lower(),quote=True)+'"><small>'+escape(c['id'])+' · '+escape(c['source'])+'</small><h2>'+escape(c['title'])+'</h2><p>'+escape(c['method'])+'</p><p class="stop">边界与停止：'+escape(c['stop'])+'</p><small>书目PDF物理页 '+escape(', '.join(map(str,c['pdf_physical_pages'])) or '不适用')+'</small></article>' for c in cards)
    return '<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>研究方法知识库</title><style>body{font:17px/1.8 system-ui;margin:auto;padding:28px;max-width:1100px;background:#f4f5ef;color:#173c37}h1{font-size:32px}input{box-sizing:border-box;width:100%;padding:16px;font:inherit;position:sticky;top:0}article{background:white;padding:24px;margin:18px 0;border-left:4px solid #467a6a}small{color:#526e67}.stop{background:#f8f3e6;padding:12px}a{color:#245f50}</style><a href="/">返回工作台</a><h1>研究方法知识库</h1><p>20张方法卡；公司数据、真实核验与授权由各项目独立维护。书目页码指原PDF物理页，OCR须回原图。</p><label for="query">搜索问题或术语</label><input id="query" placeholder="例如：收入、现金、估值、反证"><div id="cards">'+body+'</div><script nonce="'+escape(nonce,quote=True)+'">document.getElementById("query").addEventListener("input",e=>{const ts=e.target.value.toLowerCase().split(/\\s+/).filter(Boolean);document.querySelectorAll("article").forEach(a=>a.hidden=!ts.every(t=>a.dataset.search.includes(t)))})</script></html>'
