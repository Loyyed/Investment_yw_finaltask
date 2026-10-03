from __future__ import annotations
from pathlib import Path, PurePosixPath
from decimal import Decimal, localcontext, InvalidOperation, ROUND_HALF_UP
from contextlib import contextmanager
from datetime import datetime, timezone
import copy, hashlib, json, os, re, shutil, stat, sys, tempfile, time, zipfile

ROOT = Path(__file__).resolve().parents[1]
IDENTIFIER = re.compile(r'^[A-Za-z][A-Za-z0-9_-]{0,79}$')
STATES = {'Fact', 'Interpretation', 'Forecast', 'Decision', 'Unknown'}
COMPARABILITY = ('version', 'period', 'currency_unit', 'entity', 'scope', 'definition', 'restatement')

class WorkbenchError(ValueError):
    pass

def now():
    return datetime.now(timezone.utc).astimezone().isoformat(timespec='seconds')

def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()

def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')).hexdigest()

def read_json(path, default=None):
    path = Path(path)
    return json.loads(path.read_text(encoding='utf-8-sig')) if path.exists() else copy.deepcopy(default)

def atomic_text(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temp = tempfile.mkstemp(prefix='.write-', dir=path.parent)
    try:
        with os.fdopen(descriptor, 'w', encoding='utf-8', newline='\n') as out:
            out.write(value); out.flush(); os.fsync(out.fileno())
        os.replace(temp, path)
    finally:
        if os.path.exists(temp): os.unlink(temp)

def save_json(path, value):
    atomic_text(path, json.dumps(value, ensure_ascii=False, indent=2) + '\n')

def contained(root, relative):
    root = Path(root).resolve(); candidate = (root / relative).resolve()
    if not candidate.is_relative_to(root): raise WorkbenchError('路径越界：' + str(relative))
    return candidate

def identifier(value):
    if not isinstance(value, str) or not IDENTIFIER.fullmatch(value):
        raise WorkbenchError('编号须以英文字母开头，仅用字母、数字、下划线或短横线，最长80字符')
    return value

def file_name(value):
    value = re.sub(r'[\x00-\x1f<>:"/\\|?*]', '_', str(value)).strip(' .')[:100]
    if not value: raise WorkbenchError('名称不能为空')
    if value.split('.')[0].upper() in {'CON','PRN','AUX','NUL', *{'COM'+str(i) for i in range(1,10)}, *{'LPT'+str(i) for i in range(1,10)}}:
        value = '_' + value
    return value

def number(value):
    if isinstance(value, (float, bool)): raise WorkbenchError('数值请传十进制字符串，不使用浮点或布尔值')
    try: n = Decimal(str(value).replace(',', ''))
    except InvalidOperation as exc: raise WorkbenchError('无法识别精确数值：' + str(value)) from exc
    if not n.is_finite(): raise WorkbenchError('数值必须有限')
    return n

@contextmanager
def locked(project):
    path = Path(project) / 'runtime/ledger.lock'; path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a+b') as stream:
        stream.seek(0, os.SEEK_END)
        if not stream.tell(): stream.write(b'0'); stream.flush()
        deadline = time.monotonic() + 5
        while True:
            try:
                stream.seek(0)
                if os.name == 'nt':
                    import msvcrt; msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl; fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except OSError:
                if time.monotonic() > deadline: raise WorkbenchError('另一个操作正在保存，请稍后重试')
                time.sleep(.05)
        try: yield
        finally:
            stream.seek(0)
            if os.name == 'nt':
                import msvcrt; msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl; fcntl.flock(stream, fcntl.LOCK_UN)

def create_project(company, code='', profile='general', destination=None, kit=ROOT):
    company = str(company).strip()
    if not company or '\n' in company: raise WorkbenchError('请填写单行公司名称')
    if profile not in ('general','consumer','industrial','financial'): raise WorkbenchError('未知行业适配类型')
    kit = Path(kit).resolve()
    target = Path(destination).resolve() if destination else kit/'projects'/file_name(company + ('_'+code if code else ''))
    if target.exists(): raise WorkbenchError('目标已存在，保留其资料，请另选目录：' + str(target))
    target.parent.mkdir(parents=True, exist_ok=True)
    temp = Path(tempfile.mkdtemp(prefix='.new-project-', dir=target.parent))
    try:
        settings = {'schema_version':1,'company':company,'code':str(code),'profile':profile,
                    'created_at':now(),'information_cutoff':'','research_purpose':'公司分析',
                    'source_scope':'用户提供资料；按后续实际任务授权扩展',
                    'review_mode':'human-first','reviewer':'','executor':'','signature_status':'pending',
                    'required_dimensions':['商业模式','行业竞争','竞争优势']}
        save_json(temp/'project.json',settings)
        for d in ['sources/raw','sources/unpacked','sources/text','tasks','work','evidence','outputs','docs/images','会话交接','runtime']:
            (temp/d).mkdir(parents=True,exist_ok=True)
        save_json(temp/'sources/manifest.json',{'schema_version':1,'sources':[]})
        save_json(temp/'evidence/ledger.json',{'schema_version':1,'records':{},'events':[],'delegations':[],'approvals':[]})
        save_json(temp/'work/report-scope.json',{'ready':False,'path':'outputs/analysis-report.md','record_ids':[]})
        if os.name=='nt':atomic_text(temp/'runtime/python-path.txt',sys.executable+'\n')
        for source in (kit/'templates').glob('*.md'):
            mapping={'研究计划.md':'tasks/research-plan.md','口径裁决.md':'work/metric-scope.md','机制底稿.md':'work/claim-notes.md',
                     '最终报告.md':'outputs/analysis-report.md','内容验收.md':'docs/acceptance.md','会话交接.md':'会话交接/CURRENT.md','稳定约定.md':'会话交接/DECISIONS.md'}
            text=source.read_text(encoding='utf-8').replace('{{公司}}',company).replace('{{代码}}',str(code)).replace('{{行业适配}}',profile)
            atomic_text(temp/mapping[source.name],text)
        for f in ['workbench.py','启动工作台.cmd','启动工作台.sh','AGENTS.md']:
            shutil.copyfile(kit/f,temp/f)
        shutil.copytree(kit/'companybench',temp/'companybench',ignore=shutil.ignore_patterns('__pycache__'))
        shutil.copytree(kit/'skills',temp/'skills',ignore=shutil.ignore_patterns('__pycache__'))
        shutil.copytree(kit/'templates',temp/'templates')
        atomic_text(temp/'.gitignore','runtime/\nsources/text/\n__pycache__/\n*.py[cod]\n.venv/\n.env\n会话交接/logs/\n会话交接/tmp/\n')
        atomic_text(temp/'.gitattributes','* text=auto\n*.py text eol=lf\n*.md text eol=lf\n*.html text eol=lf\n*.json text eol=lf\n*.yaml text eol=lf\n*.sh text eol=lf\n*.cmd text eol=crlf\nsources/raw/** -text -diff\nsources/unpacked/** -text -diff\n*.png binary\n*.pdf binary\n')
        atomic_text(temp/'README.md',f'''# {company}公司分析项目

代码：{code or '待补'}；行业适配：{profile}。这是独立项目，初始没有来源、Fact或公司结论。

双击“启动工作台.cmd”，或运行 `python workbench.py serve`。导入资料后，让Agent先读AGENTS.md和会话交接/CURRENT.md，再按技能开始分析；核验时在窗口点击“确认原文与口径”。不需要手动改JSON。

当前报告：[分析报告](outputs/analysis-report.md)；核验记录：[当前证据](evidence/facts.md)；计划：[研究计划](tasks/research-plan.md)。

项目复制后仍可单独运行，包含本次方法与程序快照；以相对路径绑定原件。Python需3.10或更新，核心操作无需额外包。PDF自动文字索引仅在已有pypdf时启用，原PDF仍是核验来源。

原件在sources，底稿在work，真实核验历史在evidence，报告在outputs，内容验收在docs，精简交接在会话交接。签署与内容确认分开，初始签名空白。
''')
        os.replace(temp,target)
    except Exception:
        if temp.resolve().is_relative_to(target.parent.resolve()) and temp.name.startswith('.new-project-'):
            shutil.rmtree(temp)
        raise
    ReviewStore(target).sync()
    return target

def decoded_zip_name(info):
    if info.flag_bits & 0x800: return info.filename
    try: raw=info.filename.encode('cp437')
    except UnicodeEncodeError: return info.filename
    for encoding in ('utf-8','gb18030'):
        try: return raw.decode(encoding)
        except UnicodeDecodeError: pass
    return info.filename

def zip_members(path):
    with zipfile.ZipFile(path) as archive:
        members=[];total=0
        for info in archive.infolist():
            name=decoded_zip_name(info).replace('\\','/')
            member=PurePosixPath(name)
            if member.is_absolute() or '..' in member.parts or any(':' in part or '\x00' in part for part in member.parts):
                raise WorkbenchError('压缩包存在越界成员，保留原包并停止解包：'+name)
            if stat.S_ISLNK(info.external_attr>>16): raise WorkbenchError('压缩包软链接不能作为普通资料解包：'+name)
            if info.flag_bits & 1: raise WorkbenchError('压缩包加密，需先由用户解密：'+name)
            if info.is_dir() or name.startswith('__MACOSX/') or member.name.startswith('._'): continue
            total+=info.file_size
            if info.file_size>512*1024*1024 or total>2*1024**3: raise WorkbenchError('压缩包展开量超过单文件512MB/总量2GB，请分批处理')
            if info.file_size>20*1024*1024 and info.file_size/max(info.compress_size,1)>1000: raise WorkbenchError('压缩成员异常高压缩比，先核查用途')
            members.append((info,name))
        return members

def import_sources(project, location):
    store=ReviewStore(project);location=Path(location).resolve()
    if not location.exists(): raise WorkbenchError('资料路径不存在')
    items=[location] if location.is_file() else sorted(p for p in location.rglob('*') if p.is_file())
    if location.is_dir() and (store.root==location or store.root.is_relative_to(location)):
        raise WorkbenchError('不能把包含当前项目的目录再导入，避免递归复制；请选择原始资料目录')
    for path in items:
        if path.is_symlink() or (location.is_dir() and not path.resolve().is_relative_to(location)):
            raise WorkbenchError('资料目录含链接到外部的文件，请改选明确的原文件')
        if path.suffix.lower()=='.zip': zip_members(path)
    added=[]
    with locked(store.root):
        manifest=read_json(store.root/'sources/manifest.json')
        def add(path,original,archive_id=None,member=None):
            value=sha(path)
            existing=next((r for r in manifest['sources'] if r['sha256']==value),None)
            if existing:
                if sha(contained(store.root,existing['path']))!=value: raise WorkbenchError('已归档原件被改变，不能静默覆盖：'+existing['id'])
                return existing
            sid='S'+value[:16];name=file_name(Path(original).name)
            relative='sources/raw/'+sid+'_'+name
            if any(r['id']==sid and r['sha256']!=value for r in manifest['sources']): raise WorkbenchError('来源编号碰撞，需人工处理')
            target=contained(store.root,relative)
            if target.exists() and sha(target)!=value: raise WorkbenchError('归档目标已有不同内容，停止覆盖')
            if not target.exists(): shutil.copyfile(path,target)
            row={'id':sid,'path':relative,'original_name':original,'sha256':value,'bytes':path.stat().st_size,
                 'format':path.suffix.lower(),'role':'待按正文识别','purpose':'','imported_at':now(),
                 'archive_id':archive_id,'archive_member':member}
            manifest['sources'].append(row);added.append(row);return row
        for path in items:
            if path.name.startswith('._') or '__MACOSX' in path.parts: continue
            original=path.relative_to(location).as_posix() if location.is_dir() else path.name
            row=add(path,original)
            if path.suffix.lower()=='.zip':
                with zipfile.ZipFile(path) as archive:
                    for info,name in zip_members(path):
                        # Normalize output names independently from member paths; never traverse.
                        target=contained(store.root,'sources/unpacked/'+row['id']+'/'+hashlib.sha256(info.filename.encode()).hexdigest()[:12]+'_'+file_name(PurePosixPath(name).name))
                        target.parent.mkdir(parents=True,exist_ok=True)
                        if not target.exists():
                            descriptor,tmp=tempfile.mkstemp(dir=target.parent)
                            try:
                                with os.fdopen(descriptor,'wb') as out,archive.open(info) as source: shutil.copyfileobj(source,out)
                                os.replace(tmp,target)
                            finally:
                                if os.path.exists(tmp):os.unlink(tmp)
                        # Recheck bytes on repeat import instead of trusting an edited extraction.
                        with archive.open(info) as source:
                            h=hashlib.sha256()
                            for chunk in iter(lambda:source.read(1024*1024),b''):h.update(chunk)
                        if sha(target)!=h.hexdigest():raise WorkbenchError('解包副本发生变化，保留并停止：'+name)
                        add(target,name,row['id'],info.filename)
        save_json(store.root/'sources/manifest.json',manifest)
        ledger=store._read();store._event(ledger,'sources-imported',{'source_ids':[r['id'] for r in added]});store._save(ledger)
    store.sync();return added

def index_sources(project):
    store=ReviewStore(project);rows=read_json(store.root/'sources/manifest.json')['sources'];indexed=[];skipped=[]
    for row in rows:
        path=contained(store.root,row['path'])
        if sha(path)!=row['sha256']:raise WorkbenchError('归档原件已改变：'+row['id'])
        if row['format'] in ('.txt','.md'):
            text=None
            for enc in ('utf-8-sig','gb18030','utf-16'):
                try:text=path.read_text(encoding=enc);break
                except UnicodeError:pass
            if text is None: skipped.append({'id':row['id'],'reason':'文字编码待识别'});continue
            body='\n'.join(f'{i}: {line}' for i,line in enumerate(text.splitlines(),1))
        elif row['format']=='.pdf':
            try:from pypdf import PdfReader
            except ImportError:skipped.append({'id':row['id'],'reason':'无现有pypdf，仍可查看原PDF；未下载依赖'});continue
            try:body='\n\n'.join(f'## PDF页 {i}\n\n{page.extract_text() or "[本页未提取到文字，需图像/OCR核查]"}' for i,page in enumerate(PdfReader(path).pages,1))
            except Exception as exc:skipped.append({'id':row['id'],'reason':'提取失败：'+str(exc)});continue
        else:skipped.append({'id':row['id'],'reason':'原件已归档，按相应文档/表格/幻灯片工具读取'});continue
        atomic_text(store.root/'sources/text'/f"{row['id']}.md",f"# 来源检索缓存 {row['id']}\n\n原件SHA-256：{row['sha256']}；缓存只能定位，不能代替原件核验。\n\n"+body+'\n')
        indexed.append(row['id'])
    return {'indexed':indexed,'skipped':skipped}

class ReviewStore:
    """Source-bound records. Exported Markdown and handoff never establish Fact."""
    def __init__(self,project):
        self.root=Path(project).resolve();self.path=self.root/'evidence/ledger.json'
        if not (self.root/'project.json').is_file() or not self.path.is_file():raise WorkbenchError('不是已初始化的公司项目')
    def _read(self):return read_json(self.path)
    def _save(self,ledger):save_json(self.path,ledger)
    def _event(self,ledger,action,data):
        event={'id':'E'+str(len(ledger['events'])+1).zfill(6),'time':now(),'action':action,'data':data,
               'previous_hash':ledger['events'][-1]['hash'] if ledger['events'] else None}
        event['hash']=digest(event);ledger['events'].append(event);return event
    def history_valid(self,ledger=None):
        ledger=ledger or self._read();records={};delegations=[];approvals=[]
        previous=None
        for event in ledger['events']:
            value=copy.deepcopy(event);recorded=value.pop('hash',None)
            if value.get('previous_hash')!=previous or digest(value)!=recorded:return False
            previous=recorded
            if event['action'] in ('candidate-created','candidate-revised'):
                records[event['data']['record']['id']]=event['data']['record']
            elif event['action']=='delegation-granted':delegations.append(copy.deepcopy(event['data']))
            elif event['action']=='delegation-revoked':
                row=next((d for d in delegations if d['id']==event['data']['id']),None)
                if not row:return False
                row['active']=False
            elif event['action']=='report-content-approved':approvals.append(event['data'])
        return records==ledger['records'] and delegations==ledger['delegations'] and approvals==ledger['approvals']
    def source_rows(self):return read_json(self.root/'sources/manifest.json')['sources']
    def classify_source(self,sid,role,purpose):
        with locked(self.root):
            value=read_json(self.root/'sources/manifest.json');row=next((r for r in value['sources'] if r['id']==sid),None)
            if not row:raise WorkbenchError('找不到来源编号')
            row.update(role=str(role),purpose=str(purpose));save_json(self.root/'sources/manifest.json',value)
        self.sync()
    def upsert(self,record):
        record=copy.deepcopy(record);identifier(record.get('id'))
        kind=record.get('kind','disclosure')
        if kind not in ('disclosure','derived','interpretation','forecast','decision','unknown'):raise WorkbenchError('未知记录类型')
        if not str(record.get('claim','')).strip():raise WorkbenchError('主张不能为空')
        if record.get('value') is not None:number(record['value']);record['value']=str(record['value'])
        for ref in record.get('sources',[]):
            identifier(ref.get('source_id'))
            if not isinstance(ref.get('location'),str) or not ref['location'].strip():raise WorkbenchError('来源必须写页码/表格/行列定位')
        record['kind']=kind
        record.setdefault('state',{'interpretation':'Interpretation','forecast':'Forecast','decision':'Decision'}.get(kind,'Unknown'))
        if record['state']=='Fact':raise WorkbenchError('新增候选不能自行标Fact；请先登记，再走核准接口')
        if record['state'] not in STATES:raise WorkbenchError('未知状态')
        if kind=='derived':
            formula=record.get('formula',{})
            if formula.get('op') not in ('sum','difference','ratio','margin','growth','blank-zero'):raise WorkbenchError('不支持的算术运算')
            ids=formula.get('inputs',[])
            if not isinstance(ids,list) or not ids:raise WorkbenchError('计算必须明确输入编号')
            for rid in ids:
                identifier(rid)
                if rid==record['id']:raise WorkbenchError('计算不能直接依赖自身')
            if 'scale' in formula:number(formula['scale'])
            precision=formula.get('precision',2)
            if not isinstance(precision,int) or not 0<=precision<=12:raise WorkbenchError('舍入位数须为0—12')
        with locked(self.root):
            ledger=self._read();previous=ledger['records'].get(record['id'])
            event=self._event(ledger,'candidate-created' if previous is None else 'candidate-revised',{'record':record,'previous':previous})
            ledger['records'][record['id']]=record;self._save(ledger)
        self.sync();return event['id']
    def _calculate(self,record,inputs):
        f=record['formula'];op=f['op']
        if op=='blank-zero':
            if len(inputs)!=1 or inputs[0].get('blank_cell') is not True or inputs[0].get('value') is not None:
                raise WorkbenchError('空白按零仅接受已明确登记为原表空白的单项输入')
            if not record.get('support_boundary'):raise WorkbenchError('必须说明只在该算术中按零处理，不是原报披露为0')
            return str(Decimal(0).quantize(Decimal(1).scaleb(-f.get('precision',2))))
        values=[number(r['value']) for r in inputs]
        if op!='sum' and len(values)!=2:raise WorkbenchError('该运算要求两个输入')
        with localcontext() as ctx:
            ctx.prec=40
            if op=='sum':value=sum(values,Decimal(0))
            elif op=='difference':value=values[0]-values[1]
            else:
                denominator=values[1] if op in ('ratio','growth') else values[0]
                if denominator<=0:raise WorkbenchError('分母须为正，零/负基数须另作解释')
                value=values[0]/denominator if op=='ratio' else ((values[0]-values[1])/denominator)
            value*=number(f.get('scale','1' if op in ('sum','difference','ratio') else '100'))
            return str(value.quantize(Decimal(1).scaleb(-f.get('precision',2)),rounding=ROUND_HALF_UP))
    def _views(self,ledger):
        if not self.history_valid(ledger):raise WorkbenchError('事件历史校验失败，停止作为有效Fact使用')
        source_map={r['id']:r for r in self.source_rows()};memo={};source_hashes={}
        def visit(rid,stack=()):
            if rid in memo:return memo[rid]
            if rid in stack:raise WorkbenchError('计算依赖循环：'+rid)
            if rid not in ledger['records']:raise WorkbenchError('缺少计算输入：'+rid)
            raw=ledger['records'][rid];view=copy.deepcopy(raw);issues=[];dependency=[];value=raw.get('value');scope=raw.get('scope',{})
            sources=[]
            for ref in raw.get('sources',[]):
                source=source_map.get(ref['source_id'])
                if not source:issues.append('来源未登记：'+ref['source_id']);continue
                try:
                    path=contained(self.root,source['path'])
                    if source['id'] not in source_hashes:source_hashes[source['id']]=sha(path)
                    current=source_hashes[source['id']]
                    if current!=source['sha256']:issues.append('归档原件改变，请导入新版：'+source['id'])
                    sources.append({'source_id':source['id'],'sha256':current,'location':ref['location']})
                except (OSError,WorkbenchError):issues.append('来源缺失：'+source['id'])
            if raw['kind']=='disclosure' and not sources:issues.append('原披露缺少原始来源与定位')
            if raw['kind'] in ('disclosure','derived'):
                for field in ('period','entity','basis','definition'):
                    if not scope.get(field):issues.append('缺少口径：'+field)
                if (raw.get('value') is not None or raw['kind']=='derived') and not scope.get('unit'):issues.append('数值缺少单位')
            if raw['kind']=='derived':
                try:
                    inputs=[visit(i,stack+(rid,)) for i in raw['formula']['inputs']]
                    if any(r['effective_state']!='Fact' for r in inputs):issues.append('计算输入尚未全部成为当前有效Fact')
                    dependency=[{'id':r['id'],'binding':r['binding'],'confirmation':r.get('confirmation_event')} for r in inputs]
                    op=raw['formula']['op']
                    if op in ('sum','difference','margin'):
                        for field in ('unit','currency','period','entity','basis'):
                            if len({r.get('scope',{}).get(field) for r in inputs})>1:issues.append('运算输入口径不同：'+field)
                    if op=='ratio':
                        for field in ('period','entity','basis'):
                            if len({r.get('scope',{}).get(field) for r in inputs})>1:issues.append('比率输入范围不同：'+field)
                    if op=='growth' and not all(raw['formula'].get('comparability',{}).get(k) is True for k in COMPARABILITY):
                        issues.append('同比七项可比性尚未明确核准')
                    if op=='growth':
                        for field in ('unit','currency','entity','basis','definition'):
                            if len({r.get('scope',{}).get(field) for r in inputs})>1:issues.append('同比输入口径不同：'+field)
                        if len({r.get('scope',{}).get('period') for r in inputs})!=2:issues.append('同比须为两个明确且不同的报告期')
                    value=self._calculate(raw,inputs)
                except (WorkbenchError,ArithmeticError,KeyError,TypeError) as exc:issues.append(str(exc));value=None
            binding=digest({'record':raw,'source_versions':sources,'dependencies':dependency,'computed_value':value,
                            'calculation_engine_sha256':sha(Path(__file__)) if raw['kind']=='derived' else None})
            confirmation=None;withdrawn=False
            for event in reversed(ledger['events']):
                if event['action'] in ('record-confirmed','record-withdrawn') and event['data'].get('record_id')==rid:
                    if event['action']=='record-withdrawn':withdrawn=True
                    else:confirmation=event
                    break
            state={'interpretation':'Interpretation','forecast':'Forecast','decision':'Decision'}.get(raw['kind'],'Unknown')
            if confirmation and not withdrawn and confirmation['data']['binding']==binding and not issues:
                permitted=True
                if confirmation['data']['actor']=='agent':
                    permitted=any(d['id']==confirmation['data'].get('delegation_id') and d['active'] and raw['kind'] in d['kinds'] for d in ledger['delegations'])
                if permitted and raw['kind'] in ('disclosure','derived'):state='Fact'
                elif not permitted:issues.append('Agent核准授权已撤销或不覆盖该记录')
            elif confirmation and confirmation['data']['binding']!=binding:issues.append('来源、口径或计算依赖变化，需要对应复核')
            view.update(value=value,effective_state=state,binding=binding,issues=issues,
                        verifier=confirmation['data']['actor'] if state=='Fact' else None,
                        confirmation_event=confirmation['id'] if state=='Fact' else None,
                        human_confirmation=bool(state=='Fact' and confirmation['data']['actor'] in ('human-ui','human-chat')) if confirmation else False)
            memo[rid]=view;return view
        return [visit(rid) for rid in ledger['records']]
    def records(self):return self._views(self._read())
    def facts(self):return [r for r in self.records() if r['effective_state']=='Fact']
    def confirm(self,rid,actor,statement='',delegation_id=None,expected_binding=None):
        identifier(rid)
        if actor not in ('human-ui','human-chat','agent'):raise WorkbenchError('未知核准身份')
        if actor=='human-chat' and not statement.strip():raise WorkbenchError('聊天确认必须保留真实原话')
        if actor=='agent' and not statement.strip():raise WorkbenchError('Agent核准须说明已进行的原文/算术检查，不能仅因有授权就确认')
        with locked(self.root):
            ledger=self._read();view=next((r for r in self._views(ledger) if r['id']==rid),None)
            if not view:raise WorkbenchError('找不到候选')
            if expected_binding and expected_binding!=view['binding']:raise WorkbenchError('您查看后内容发生变化，请刷新后核对')
            if view['kind'] not in ('disclosure','derived'):raise WorkbenchError('解释/预测/Decision不经数字核验自动升级为Fact，请走报告内容确认')
            # Stale confirmations are allowed to be superseded; source/input failures are not.
            blocking=[i for i in view['issues'] if not i.startswith(('来源、口径或计算依赖变化','Agent核准授权'))]
            if blocking:raise WorkbenchError('；'.join(blocking))
            if actor=='agent':
                delegation=next((d for d in ledger['delegations'] if d['id']==delegation_id and d['active']),None)
                if not delegation or view['kind'] not in delegation['kinds']:raise WorkbenchError('没有覆盖本记录类型的明确Agent原文核准授权')
            event=self._event(ledger,'record-confirmed',{'record_id':rid,'binding':view['binding'],'actor':actor,
                'statement_original':statement if actor!='human-ui' else '用户在本地核验窗口点击：确认原文与口径',
                'delegation_id':delegation_id if actor=='agent' else None,
                'reviewed_record':{k:view.get(k) for k in ('id','claim','value','scope','sources','formula')},'reviewer_name':''})
            self._save(ledger)
        self.sync();return event['id']
    def withdraw(self,rid,reason='',actor='human-ui'):
        with locked(self.root):
            ledger=self._read()
            if rid not in ledger['records']:raise WorkbenchError('找不到记录')
            event=self._event(ledger,'record-withdrawn',{'record_id':rid,'reason':reason,'actor':actor});self._save(ledger)
        self.sync();return event['id']
    def delegate(self,statement,actor='human-chat',kinds=None,content=False):
        if actor not in ('human-ui','human-chat') or not statement.strip():raise WorkbenchError('必须记录用户实际授权动作或原话')
        kinds=kinds or ['disclosure','derived']
        if not kinds or not set(kinds)<={'disclosure','derived'}:raise WorkbenchError('事实代理授权仅支持原始披露及可复核算术')
        with locked(self.root):
            ledger=self._read();row={'id':'D'+str(len(ledger['delegations'])+1).zfill(4),'time':now(),'actor':actor,
                'statement_original':statement,'kinds':kinds,'content_acceptance':bool(content),'active':True,
                'scope':'本公司项目当前及后续资料中的指定披露和计算；不确认因果，不伪造本人签署'}
            ledger['delegations'].append(row);self._event(ledger,'delegation-granted',row);self._save(ledger)
        self.sync();return row['id']
    def revoke_delegation(self,did):
        with locked(self.root):
            ledger=self._read();row=next((d for d in ledger['delegations'] if d['id']==did),None)
            if not row:raise WorkbenchError('找不到授权')
            row['active']=False;self._event(ledger,'delegation-revoked',{'id':did});self._save(ledger)
        self.sync()
    def review_ready(self,record_ids,relative='outputs/analysis-report.md'):
        records={r['id']:r for r in self.records()}
        for rid in record_ids:
            if rid not in records:raise WorkbenchError('报告引用编号不存在：'+rid)
        if not contained(self.root,relative).is_file():raise WorkbenchError('待审报告不存在')
        save_json(self.root/'work/report-scope.json',{'ready':True,'path':relative,'record_ids':list(dict.fromkeys(record_ids))})
    def report_binding(self):
        scope=read_json(self.root/'work/report-scope.json');rows={r['id']:r for r in self.records()}
        if not scope['ready']:raise WorkbenchError('Agent尚未将报告标为可审阅')
        binding={'report_sha256':sha(contained(self.root,scope['path'])),'record_ids':scope['record_ids'],
            'records':[{k:rows[rid].get(k) for k in ('id','binding','effective_state','confirmation_event')} for rid in scope['record_ids']]}
        return digest(binding)
    def approve_report(self,actor,statement='',delegation_id=None,expected_binding=None):
        if actor not in ('human-ui','human-chat','agent'):raise WorkbenchError('未知身份')
        if actor=='human-chat' and not statement.strip():raise WorkbenchError('保留实际内容审阅原话')
        if actor=='agent' and not statement.strip():raise WorkbenchError('Agent内容验收须说明实际检查，不能冒充用户点击')
        with locked(self.root):
            ledger=self._read();binding=self.report_binding()
            if expected_binding and expected_binding!=binding:raise WorkbenchError('报告或引用证据已改变，请刷新再审阅')
            if actor=='agent' and not any(d['id']==delegation_id and d['active'] and d['content_acceptance'] for d in ledger['delegations']):
                raise WorkbenchError('没有明确授权Agent完成内容验收')
            row={'binding':binding,'time':now(),'actor':actor,'statement_original':statement or '用户点击：本版结论与Unknown边界审核通过',
                 'delegation_id':delegation_id if actor=='agent' else None,'signature_status':'pending'}
            ledger['approvals'].append(row);self._event(ledger,'report-content-approved',row);self._save(ledger)
        self.sync()
    def report_approved(self):
        ledger=self._read()
        try:binding=self.report_binding()
        except (WorkbenchError,OSError,KeyError):return False
        return any(r['binding']==binding and (r['actor']!='agent' or any(d['id']==r['delegation_id'] and d['active'] and d['content_acceptance'] for d in ledger['delegations'])) for r in ledger['approvals'])
    def sync(self):
        rows=self.records();sources=self.source_rows()
        def cell(v):return str(v).replace('|','／').replace('\n','；')
        lines=['# 当前来源绑定的证据视图','','本文件为导出；使用事实必须重新调用ReviewStore(project).facts()。来源、口径、公式或输入确认改变后，旧确认不能继续当Fact。','',
               '| 编号 | 主张 | 数值 | 状态 | 核准身份 | 支持边界 / 当前问题 |','| --- | --- | --- | --- | --- | --- |']
        for r in rows:lines.append('| '+' | '.join(cell(v) for v in [r['id'],r['claim'],r.get('value') or '',r['effective_state'],r.get('verifier') or '',r.get('support_boundary','')+('；'+'；'.join(r['issues']) if r['issues'] else '')])+' |')
        if not rows:lines+=['','尚未登记候选，Fact为0。']
        atomic_text(self.root/'evidence/facts.md','\n'.join(lines)+'\n')
        catalog=['# 原始资料目录与用途','','用途按正文识别，不因文件名乱码或不含公司名而忽略。','', '| 编号 | 原名 / 归档 | 内容角色 | 用途 | SHA-256 |','| --- | --- | --- | --- | --- |']
        for s in sources:catalog.append('| '+' | '.join(cell(v) for v in [s['id'],f"[{s['original_name']}](../{s['path']})",s['role'],s['purpose'],s['sha256']])+' |')
        atomic_text(self.root/'docs/source-map.md','\n'.join(catalog)+'\n')
        handoff=self.root/'会话交接/CURRENT.md'
        if handoff.exists():
            begin='<!-- live-status:start -->';end='<!-- live-status:end -->'
            body=begin+'\n当前自动状态：来源'+str(len(sources))+'份，候选'+str(len(rows))+'条，有效Fact '+str(sum(r['effective_state']=='Fact' for r in rows))+'条。使用事实须重新调用ReviewStore(...).facts()，此摘要不能证明Fact。\n'+end
            text=handoff.read_text(encoding='utf-8');pattern=re.escape(begin)+r'.*?'+re.escape(end)
            text=re.sub(pattern,lambda _:body,text,flags=re.S) if begin in text else text.rstrip()+'\n\n'+body+'\n'
            atomic_text(handoff,text)
        return {'records':len(rows),'facts':sum(r['effective_state']=='Fact' for r in rows),'unknown':sum(r['effective_state']=='Unknown' for r in rows),'sources':len(sources)}

def validate_project(project):
    store=ReviewStore(project);errors=[];warnings=[]
    try:
        if not store.history_valid():errors.append('事件历史完整性失败')
        rows=store.records()
    except (WorkbenchError,OSError,KeyError,ValueError) as exc:errors.append(str(exc));rows=[]
    for source in store.source_rows():
        try:
            if sha(contained(store.root,source['path']))!=source['sha256']:errors.append('原件字节变化：'+source['id'])
        except OSError:errors.append('原件缺失：'+source['id'])
    for r in rows:
        if r['issues']:warnings.append(r['id']+'：'+'；'.join(r['issues']))
        if r['effective_state']=='Fact' and not r.get('support_boundary'):warnings.append(r['id']+'：建议补充事实支持边界')
    result={'checked_at':now(),'errors':errors,'warnings':warnings,'current_fact_count':sum(r['effective_state']=='Fact' for r in rows),
            'record_count':len(rows),'report_content_approved':store.report_approved(),'signature_status':read_json(store.root/'project.json').get('signature_status','pending')}
    save_json(store.root/'runtime/latest-validation.json',result)
    return result
