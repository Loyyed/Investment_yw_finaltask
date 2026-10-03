"""Validate only this reusable toolkit. No reads of previous company projects."""
from pathlib import Path
import json,re,sys
ROOT=Path(__file__).resolve().parents[1]
sys.stdout.reconfigure(encoding='utf-8')
errors=[];checks=[]
files=[p for p in ROOT.rglob('*') if p.is_file() and not any(part in ('runtime','projects','.git','__pycache__') for part in p.relative_to(ROOT).parts)]
for path in files:
    if path.suffix=='.py':
        try:compile(path.read_text(encoding='utf-8'),str(path),'exec')
        except SyntaxError as exc:errors.append(str(exc))
    if path.suffix in ('.md','.py','.html','.json','.yaml','.sh','.cmd'):
        try:text=path.read_text(encoding='utf-8-sig')
        except UnicodeDecodeError:
            if path.suffix=='.cmd':text=path.read_text(encoding='gb18030')
            else:
                errors.append('非UTF-8文本：'+str(path.relative_to(ROOT)));continue
        if path.suffix=='.md':
            for match in re.finditer(r'!?\[[^\]]*\]\(([^)]+)\)',text):
                link=match[1].strip('<>')
                if link.startswith(('https:','http:','#','mailto:')):continue
                if path.parent==ROOT/'templates' and link in ('../docs/source-map.md','../docs/acceptance.md','../evidence/facts.md'):continue # 创建项目时由模板与sync生成
                if not (path.parent/link.split('#')[0]).exists():errors.append('断链：'+str(path.relative_to(ROOT))+' → '+link)
checks.append({'name':'Python语法与Markdown本地链接','pass':not errors})
skill=ROOT/'skills/investment-company-analysis/SKILL.md'
text=skill.read_text(encoding='utf-8')
checks.append({'name':'技能入口及渐进参考','pass':text.startswith('---\nname: investment-company-analysis') and '[TODO' not in text and len(text.splitlines())<150})
kit=json.loads((ROOT/'kit.json').read_text(encoding='utf-8'))
checks.append({'name':'新工作台无公司数据和自动授权','pass':kit['company_data_included'] is False and kit['automatic_agent_authorization'] is False and not (ROOT/'project.json').exists() and not any(p.name in ('ledger.json','manifest.json') or p.suffix.lower() in ('.pdf','.docx','.xlsx','.pptx','.zip','.pem','.key') for p in files)})
checks.append({'name':'报告与操作模板齐全','pass':len(list((ROOT/'templates').glob('*.md')))==7 and all((ROOT/p).is_file() for p in ['README.md','AGENTS.md','workbench.py','启动工作台.cmd','启动工作台.sh','companybench/ui.html','companybench/core.py','companybench/portal.py','docs/操作指南.md'])})
failed=errors+[c['name'] for c in checks if not c['pass']]
value={'checks':checks,'errors':failed,'bundle_file_count':len(files),'company_data_included':False}
print(json.dumps(value,ensure_ascii=False,indent=2))
raise SystemExit(1 if failed else 0)
