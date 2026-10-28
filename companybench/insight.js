'use strict';
const atlas=JSON.parse(document.getElementById('atlas-data').textContent);
const model=atlas.forecast;
const fmt=(v,p=2)=>Number(v).toLocaleString('zh-CN',{minimumFractionDigits:p,maximumFractionDigits:p});
let scenario='base';
function lagVolume(key,prefix,i,overrides={}){
 const b=model.baseline,d=model.volume_drivers[prefix],s=model.scenarios[key],lag=+(overrides[prefix+'_lag']??d.lag_years),sy=+model.years[i]-lag,by=+b.year-lag;
 if(lag<(d.minimum_lag||0)||!Object.hasOwn(d.production_by_year,sy)||!Object.hasOwn(d.production_by_year,by))throw Error('滞后窗口缺有效基酒输入');
 const prod=+d.production_by_year[sy],base=+d.production_by_year[by],reference=(+b[prefix+'_volume'])*prod/base,p={};
 for(const k of ['mature','inventory_tonnes','release','acceptance'])p[k]=i===0&&Object.hasOwn(overrides,prefix+'_'+k)?+overrides[prefix+'_'+k]:+s[prefix+'_'+k][i];
 if(p.mature<=0||p.release<0||p.release>1||p.acceptance<0||p.acceptance>1)throw Error('供给参数越界');
 const mature=reference*p.mature,available=mature+p.inventory_tonnes;if(available<0)throw Error('库存调整后规模为负');const planned=available*p.release,sales=planned*p.acceptance;
 return {lag_years:lag,source_year:sy,base_production:base,base_liquor:prod,supply_reference:reference,mature_adjusted:mature,inventory_adjustment:p.inventory_tonnes,planned_release:planned,conditional_sales:sales,release_rate:p.release,acceptance_rate:p.acceptance};
}
function calculate(key,overrides={}){
 const b=model.baseline,s=model.scenarios[key];let mq=+b.mt_volume,mp=+b.mt_asp,sq=+b.sr_volume,sp=+b.sr_asp,gm=+b.gross_margin;const wr0=mq*mp+sq*sp,drivers=model.volume_drivers;
 if(drivers&&('mt_q' in overrides||'sr_q' in overrides))throw Error('销量增速是结果，请调整供给和投放承接条件');
 return model.years.map((year,i)=>{const v={};for(const k of ['mt_q','mt_p','sr_q','sr_p','gm_delta','selling_rate','retention','cash_ratio'])v[k]=(i===0&&Object.hasOwn(overrides,k))?+overrides[k]:+s[k][i];const pm=mq,ps=sq,extra={};
 if(drivers){for(const p of ['mt','sr'])for(const [k,x] of Object.entries(lagVolume(key,p,i,overrides)))extra[p+'_'+k]=x;mq=extra.mt_conditional_sales;sq=extra.sr_conditional_sales;}else{mq*=1+v.mt_q;sq*=1+v.sr_q;}
 mp*=1+v.mt_p;sp*=1+v.sr_p;gm+=v.gm_delta;const wr=mq*mp+sq*sp,rev=wr+(+b.other_revenue),se=rev*v.selling_rate,np=(+b.net_profit)+(wr*gm-wr0*(+b.gross_margin)-(se-(+b.selling_expense)))*v.retention;
 return {year,mt_volume:mq,mt_asp:mp,sr_volume:sq,sr_asp:sp,wine_revenue:wr,revenue:rev,gross_margin:gm,selling_expense:se,net_profit_bridge:np,consolidated_cfo_sensitivity:np*v.cash_ratio,...(drivers?{...extra,mt_volume_growth:mq/pm-1,sr_volume_growth:sq/ps-1}:{})};});
}

window.atlasCalculate=calculate;
function redraw(){
 const host=document.getElementById('forecast-output');if(!host)return;
 const openPanels=new Set([...host.querySelectorAll('details[data-analysis][open]')].map(x=>x.dataset.analysis));
 const panel=(id,title,meaning,use,inference)=>`<details class="chart-analysis" data-analysis="${id}" ${openPanels.has(id)?'open':''}><summary>${title}</summary><dl><dt>图表含义</dt><dd>${meaning}</dd><dt>研究用途</dt><dd>${use}</dd><dt>分析与推断</dt><dd>${inference}</dd></dl></details>`;
 const q=+document.getElementById('q-input').value/100,p=+document.getElementById('p-input').value/100,s=+document.getElementById('s-input').value/100;
 document.getElementById('q-label').textContent=fmt(q*100,1)+'%';document.getElementById('p-label').textContent=fmt(p*100,1)+'%';document.getElementById('s-label').textContent=fmt(s*100,1)+'%';
 const rows=calculate(scenario,{[model.volume_drivers?'mt_release':'mt_q']:q,mt_p:p,selling_rate:s}),scenarios=Object.keys(model.scenarios).map(k=>({key:k,rows:calculate(k)}));
 const all=[+model.baseline.company_revenue,...scenarios.flatMap(s=>s.rows.map(r=>r.revenue)),...rows.map(r=>r.revenue)];const top=35,bottom=215,left=70,right=700,max=Math.max(...all)/1e8*1.1;
 const yy=v=>bottom-(v/1e8)/max*(bottom-top),xx=i=>left+i*(right-left)/3;let svg='<svg viewBox="0 0 760 275" role="img" aria-label="三种条件收入路径，不含概率"><title>条件营业收入路径（亿元）</title>';
 for(let i=0;i<=4;i++){const n=max*i/4,y=yy(n*1e8);svg+=`<line x1="${left}" x2="${right}" y1="${y}" y2="${y}" stroke="#dbe5df"/><text x="${left-12}" y="${y+4}" text-anchor="end" class="tick">${fmt(n,0)}</text>`;}
 scenarios.forEach((sc,j)=>{const values=[+model.baseline.company_revenue,...sc.rows.map(r=>r.revenue)];svg+=`<polyline points="${values.map((v,i)=>xx(i)+','+yy(v)).join(' ')}" fill="none" stroke="${['#b59c78','#94aaa8','#b0bfca'][j]}" stroke-width="2" stroke-dasharray="5 5"/>`;});
 const values=[+model.baseline.company_revenue,...rows.map(r=>r.revenue)];svg+=`<polyline points="${values.map((v,i)=>xx(i)+','+yy(v)).join(' ')}" fill="none" stroke="#167d8d" stroke-width="4"/>`;values.forEach((v,i)=>{svg+=`<circle cx="${xx(i)}" cy="${yy(v)}" r="5" fill="#167d8d"/><text x="${xx(i)}" y="${yy(v)-12}" text-anchor="middle" class="value">${fmt(v/1e8,0)}</text><text x="${xx(i)}" y="250" text-anchor="middle" class="tick">${i?model.years[i-1]:model.baseline.year}${i?'预测':'实际'}</text>`;});svg+='</svg>';
 const grow=rows[0].revenue/(+model.baseline.company_revenue)-1;
 const profitGrow=rows[0].net_profit_bridge/(+model.baseline.net_profit)-1,productGrow=rows[0].mt_volume*rows[0].mt_asp/((+model.baseline.mt_volume)*(+model.baseline.mt_asp))-1;
 const pathAnalysis=panel('forecast-path','图表分析：收入路径的含义、用途与推断',
 `当前假设下，${model.years[0]}营业收入为${fmt(rows[0].revenue/1e8,1)}亿元，较基期变化${fmt(grow*100,1)}%；${model.years.at(-1)}为${fmt(rows.at(-1).revenue/1e8,1)}亿元。实线随当前参数变化，虚线保留三种原参数路径。`,
 '比较量价变化如何改变未来收入水平，检查需要怎样的恢复条件，而不是把某条曲线当确定结果。',
 `首年核心产品销量与组合ASP合成变化为${fmt(productGrow*100,1)}%。${grow<0?'当前公司收入低于基期，量增和其他产品贡献尚不足以抵消价格等模型条件的拖累。':'当前公司收入高于基期，但这一增长依赖所设量价条件兑现。'}后续年份还沿用所选情景参数；路径之间的距离不代表概率或置信区间。`);
 const tableAnalysis=panel('forecast-table','表格分析：利润与现金敏感性的含义、用途与推断',
 `${model.years[0]}条件净利润桥接为${fmt(rows[0].net_profit_bridge/1e8,1)}亿元，较基期变化${fmt(profitGrow*100,1)}%；合并CFO敏感性为${fmt(rows[0].consolidated_cfo_sensitivity/1e8,1)}亿元。表内同时展示核心产品量价、酒类毛利率及三年结果。`,
 '检查收入路径是否同时留住利润，以及在设定现金转换率下会产生怎样的现金结果；可配合费用率滑块辨认利润对销售代价的敏感度。',
 `${profitGrow<grow?'当前条件利润变化弱于收入变化，提示毛利与费用等设定可能吸收收入贡献。':'当前条件利润变化强于或等于收入变化，提示模型内毛利与费用等条件对利润有相对帮助。'}这是以基期合并结果和增量保留率建立的条件桥，未建模金融及其他损益仍取基期；CFO只按设定比率计算，不能据此认定实体FCFF或可分配现金。`);

const volumeTrace=model.volume_drivers?'<h3>供给原数怎样进入本次销量</h3><p>Qref=基期销量×t−lag基酒÷基期对应基酒。它是历史混合库存配比下的供给参照，不是成品率或硬上限。以下成熟修正、额外库存调整、投放和承接均为情景假设；系列酒五年仅为研究时序，另看3/4/5年敏感性。</p><div class="table-wrap"><table><thead><tr><th>年份/产品</th><th>t−lag原量/吨</th><th>供给参照/吨</th><th>成熟勾兑修正后/吨</th><th>额外库存调整/吨</th><th>计划投放/吨</th><th>条件销量/吨</th></tr></thead><tbody>'+rows.flatMap(r=>['mt','sr'].map(p=>'<tr><td>'+r.year+' / '+model.volume_drivers[p].label+'</td>'+['base_liquor','supply_reference','mature_adjusted','inventory_adjustment','planned_release','conditional_sales'].map(k=>'<td>'+fmt(r[p+'_'+k],2)+'</td>').join('')+'</tr>')).join('')+'</tbody></table></div>':'';

 host.innerHTML=`<div class="forecast-card"><div class="metric-strip"><span>${model.years[0]} 营业收入<strong>${fmt(rows[0].revenue/1e8,1)} 亿</strong></span><span>较${model.baseline.year}变化<strong>${fmt(grow*100,1)}%</strong></span><span>${model.years[0]} 条件净利润桥接<strong>${fmt(rows[0].net_profit_bridge/1e8,1)} 亿</strong></span></div>${svg}<p>实线为所选情景及当前滑块；三条虚线分别为压力、基准、修复原参数路径。纵轴从零开始；这些路径不代表统计置信区间。</p>${pathAnalysis}</div><div class="table-wrap"><table><thead><tr><th>年份</th><th>营业收入 / 亿</th><th>核心产品销量 / 吨</th><th>组合ASP / 万元每吨</th><th>酒类毛利率</th><th>条件净利润 / 亿</th><th>合并CFO敏感性 / 亿</th></tr></thead><tbody>${rows.map(r=>`<tr><td>${r.year}预测</td><td>${fmt(r.revenue/1e8)}</td><td>${fmt(r.mt_volume,0)}</td><td>${fmt(r.mt_asp/1e4)}</td><td>${fmt(r.gross_margin*100)}%</td><td>${fmt(r.net_profit_bridge/1e8)}</td><td>${fmt(r.consolidated_cfo_sensitivity/1e8)}</td></tr>`).join('')}</tbody></table></div>${tableAnalysis}${volumeTrace}<p class="scenario-note">净利润为以${model.baseline.year}合并结果锚定的条件桥接，金融及未建模项维持基期；CFO仅套设定转换比率，金融资金变化未独立预测。两者均非实体NOPAT、FCFF或可分配现金。</p>`;
}
function reset(){const s=model.scenarios[scenario];for(const [id,k] of [['q-input',model.volume_drivers?'mt_release':'mt_q'],['p-input','mt_p'],['s-input','selling_rate']]){const el=document.getElementById(id);if(el)el.value=s[k][0]*100;}redraw();}
document.querySelectorAll('[data-scenario]').forEach(b=>b.addEventListener('click',()=>{scenario=b.dataset.scenario;document.querySelectorAll('[data-scenario]').forEach(x=>x.setAttribute('aria-pressed',String(x===b)));reset();}));
document.querySelectorAll('input[type=range]').forEach(x=>x.addEventListener('input',redraw));
document.getElementById('reset-forecast')?.addEventListener('click',reset);
document.getElementById('guide-toggle').addEventListener('click',e=>{const show=document.body.classList.toggle('show-guide');e.target.setAttribute('aria-pressed',String(show));});
document.getElementById('print-report').addEventListener('click',()=>window.print());
if('IntersectionObserver' in window){const io=new IntersectionObserver(entries=>{for(const e of entries)if(e.isIntersecting){document.querySelectorAll('.rail nav a').forEach(a=>a.classList.toggle('active',a.hash==='#'+e.target.id));}},{rootMargin:'-5% 0px -65% 0px'});document.querySelectorAll('.chapter').forEach(e=>io.observe(e));}
reset();

document.addEventListener('click',event=>{const button=event.target.closest('[data-chart-replay]');if(!button)return;const svg=[...button.closest('figure').querySelectorAll('svg')].find(x=>x.getBoundingClientRect().width&&x.getBoundingClientRect().height);if(svg){const clone=svg.cloneNode(true);clone.classList.add('vis-animate');svg.replaceWith(clone);}});
if('IntersectionObserver' in window){const chartObserver=new IntersectionObserver(entries=>{for(const entry of entries)if(entry.isIntersecting){entry.target.classList.add('vis-animate');chartObserver.unobserve(entry.target);}},{threshold:.15});document.querySelectorAll('.vis-svg').forEach(svg=>chartObserver.observe(svg));}

function setPlotStyle(value){value=value==='classic'?'classic':'porcelain';document.body.dataset.plotStyle=value;document.querySelectorAll('button[data-plot-style]').forEach(x=>x.setAttribute('aria-pressed',String(x.dataset.plotStyle===value)));try{localStorage.setItem('investment-plot-style',value);}catch(_){} }
document.querySelectorAll('button[data-plot-style]').forEach(x=>x.addEventListener('click',()=>setPlotStyle(x.dataset.plotStyle)));
try{setPlotStyle(localStorage.getItem('investment-plot-style')||'porcelain');}catch(_){setPlotStyle('porcelain');}
