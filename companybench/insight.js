'use strict';
const atlas=JSON.parse(document.getElementById('atlas-data').textContent);
const model=atlas.forecast;
const fmt=(v,p=2)=>Number(v).toLocaleString('zh-CN',{minimumFractionDigits:p,maximumFractionDigits:p});
let scenario='base';
function calculate(key,overrides={}){
 const b=model.baseline,s=model.scenarios[key];let mq=+b.mt_volume,mp=+b.mt_asp,sq=+b.sr_volume,sp=+b.sr_asp,gm=+b.gross_margin;
 const wr0=mq*mp+sq*sp;return model.years.map((year,i)=>{const v={};for(const k of ['mt_q','mt_p','sr_q','sr_p','gm_delta','selling_rate','retention','cash_ratio'])v[k]=(i===0&&Object.hasOwn(overrides,k))?overrides[k]:s[k][i];mq*=1+v.mt_q;mp*=1+v.mt_p;sq*=1+v.sr_q;sp*=1+v.sr_p;gm+=v.gm_delta;const wr=mq*mp+sq*sp,rev=wr+(+b.other_revenue),se=rev*v.selling_rate,np=(+b.net_profit)+(wr*gm-wr0*(+b.gross_margin)-(se-(+b.selling_expense)))*v.retention;return {year,mt_volume:mq,mt_asp:mp,sr_volume:sq,sr_asp:sp,wine_revenue:wr,revenue:rev,gross_margin:gm,selling_expense:se,net_profit_bridge:np,consolidated_cfo_sensitivity:np*v.cash_ratio};});
}
window.atlasCalculate=calculate;
function redraw(){
 const host=document.getElementById('forecast-output');if(!host)return;
 const q=+document.getElementById('q-input').value/100,p=+document.getElementById('p-input').value/100,s=+document.getElementById('s-input').value/100;
 document.getElementById('q-label').textContent=fmt(q*100,1)+'%';document.getElementById('p-label').textContent=fmt(p*100,1)+'%';document.getElementById('s-label').textContent=fmt(s*100,1)+'%';
 const rows=calculate(scenario,{mt_q:q,mt_p:p,selling_rate:s}),scenarios=Object.keys(model.scenarios).map(k=>({key:k,rows:calculate(k)}));
 const all=[+model.baseline.company_revenue,...scenarios.flatMap(s=>s.rows.map(r=>r.revenue)),...rows.map(r=>r.revenue)];const top=35,bottom=215,left=70,right=700,max=Math.max(...all)/1e8*1.1;
 const yy=v=>bottom-(v/1e8)/max*(bottom-top),xx=i=>left+i*(right-left)/3;let svg='<svg viewBox="0 0 760 275" role="img" aria-label="三种条件收入路径，不含概率"><title>条件营业收入路径（亿元）</title>';
 for(let i=0;i<=4;i++){const n=max*i/4,y=yy(n*1e8);svg+=`<line x1="${left}" x2="${right}" y1="${y}" y2="${y}" stroke="#dbe5df"/><text x="${left-12}" y="${y+4}" text-anchor="end" class="tick">${fmt(n,0)}</text>`;}
 scenarios.forEach((sc,j)=>{const values=[+model.baseline.company_revenue,...sc.rows.map(r=>r.revenue)];svg+=`<polyline points="${values.map((v,i)=>xx(i)+','+yy(v)).join(' ')}" fill="none" stroke="${['#b59c78','#94aaa8','#b0bfca'][j]}" stroke-width="2" stroke-dasharray="5 5"/>`;});
 const values=[+model.baseline.company_revenue,...rows.map(r=>r.revenue)];svg+=`<polyline points="${values.map((v,i)=>xx(i)+','+yy(v)).join(' ')}" fill="none" stroke="#167d8d" stroke-width="4"/>`;values.forEach((v,i)=>{svg+=`<circle cx="${xx(i)}" cy="${yy(v)}" r="5" fill="#167d8d"/><text x="${xx(i)}" y="${yy(v)-12}" text-anchor="middle" class="value">${fmt(v/1e8,0)}</text><text x="${xx(i)}" y="250" text-anchor="middle" class="tick">${i?model.years[i-1]:model.baseline.year}${i?'预测':'实际'}</text>`;});svg+='</svg>';
 const grow=rows[0].revenue/(+model.baseline.company_revenue)-1;
 host.innerHTML=`<div class="forecast-card"><div class="metric-strip"><span>${model.years[0]} 营业收入<strong>${fmt(rows[0].revenue/1e8,1)} 亿</strong></span><span>较${model.baseline.year}变化<strong>${fmt(grow*100,1)}%</strong></span><span>${model.years[0]} 条件净利润桥接<strong>${fmt(rows[0].net_profit_bridge/1e8,1)} 亿</strong></span></div>${svg}<p>实线为所选情景及当前滑块；三条虚线分别为压力、基准、修复原参数路径。纵轴从零开始；这些路径不代表统计置信区间。</p></div><div class="table-wrap"><table><thead><tr><th>年份</th><th>营业收入 / 亿</th><th>核心产品销量 / 吨</th><th>组合ASP / 万元每吨</th><th>酒类毛利率</th><th>条件净利润 / 亿</th><th>合并CFO敏感性 / 亿</th></tr></thead><tbody>${rows.map(r=>`<tr><td>${r.year}预测</td><td>${fmt(r.revenue/1e8)}</td><td>${fmt(r.mt_volume,0)}</td><td>${fmt(r.mt_asp/1e4)}</td><td>${fmt(r.gross_margin*100)}%</td><td>${fmt(r.net_profit_bridge/1e8)}</td><td>${fmt(r.consolidated_cfo_sensitivity/1e8)}</td></tr>`).join('')}</tbody></table></div><p class="scenario-note">净利润为以${model.baseline.year}合并结果锚定的条件桥接，金融及未建模项维持基期；CFO仅套设定转换比率，金融资金变化未独立预测。两者均非实体NOPAT、FCFF或可分配现金。</p>`;
}
function reset(){const s=model.scenarios[scenario];for(const [id,k] of [['q-input','mt_q'],['p-input','mt_p'],['s-input','selling_rate']]){const el=document.getElementById(id);if(el)el.value=s[k][0]*100;}redraw();}
document.querySelectorAll('[data-scenario]').forEach(b=>b.addEventListener('click',()=>{scenario=b.dataset.scenario;document.querySelectorAll('[data-scenario]').forEach(x=>x.setAttribute('aria-pressed',String(x===b)));reset();}));
document.querySelectorAll('input[type=range]').forEach(x=>x.addEventListener('input',redraw));
document.getElementById('reset-forecast')?.addEventListener('click',reset);
document.getElementById('guide-toggle').addEventListener('click',e=>{const show=document.body.classList.toggle('show-guide');e.target.setAttribute('aria-pressed',String(show));});
document.getElementById('print-report').addEventListener('click',()=>window.print());
if('IntersectionObserver' in window){const io=new IntersectionObserver(entries=>{for(const e of entries)if(e.isIntersecting){document.querySelectorAll('.rail nav a').forEach(a=>a.classList.toggle('active',a.hash==='#'+e.target.id));}},{rootMargin:'-5% 0px -65% 0px'});document.querySelectorAll('.chapter').forEach(e=>io.observe(e));}
reset();
