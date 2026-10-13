from pathlib import Path
from argparse import ArgumentParser
import importlib.util,json,shutil,subprocess,sys
from .core import ROOT,ReviewStore,WorkbenchError,create_project,import_sources,index_sources,validate_project,read_json,atomic_text

def find_git():
    found=shutil.which('git')
    if found:return found
    for p in [Path('C:/Program Files/Git/cmd/git.exe'),Path.home()/'AppData/Local/Programs/Git/cmd/git.exe']:
        if p.is_file():return str(p)
    return None

def git_call(executable,project,*args):
    r=subprocess.run([executable,'-C',str(project),*args],capture_output=True,text=True,encoding='utf-8',errors='replace')
    if r.returncode:raise WorkbenchError(r.stdout+r.stderr)
    return r.stdout.strip()

def main(argv=None):
    if hasattr(sys.stdout,'reconfigure'):sys.stdout.reconfigure(encoding='utf-8')
    if hasattr(sys.stderr,'reconfigure'):sys.stderr.reconfigure(encoding='utf-8')
    if sys.version_info<(3,10):print('需要Python 3.10或更新版本');return 1
    parser=ArgumentParser(description='公司分析通用工作台：无需额外包的项目创建、来源归档和证据核准')
    sub=parser.add_subparsers(dest='command',required=True)
    p=sub.add_parser('serve',help='打开本地操作窗口');p.add_argument('--root',type=Path,default=ROOT);p.add_argument('--port',type=int,default=0);p.add_argument('--no-browser',action='store_true')
    p=sub.add_parser('new',help='创建独立公司项目');p.add_argument('--company',required=True);p.add_argument('--code',default='');p.add_argument('--profile',choices=['general','consumer','industrial','financial'],default='general');p.add_argument('--path',type=Path)
    sub.add_parser('doctor',help='检查Python、Git及可选PDF工具')
    p=sub.add_parser('series-audit',help='只读检查附件CSV，不确认Fact');p.add_argument('--source',type=Path,required=True);p.add_argument('--cutoff');p.add_argument('--output',type=Path)
    p=sub.add_parser('link',help='连接已有项目，不迁移事实账本');p.add_argument('--root',type=Path,default=ROOT);p.add_argument('--directory',type=Path,required=True);p.add_argument('--name',default='')
    for name in ('draft','model','report'):
        p=sub.add_parser(name,help={'draft':'保存结构化研究草稿','model':'以明确假设计算FCFF情景','report':'生成版本化报告与依据快照'}[name]);p.add_argument('--project',type=Path,default=ROOT)
        if name!='report':p.add_argument('--file',type=Path,required=True)
    for name,description in [('import','归档原件并解包ZIP'),('index','生成只用于检索的文字缓存'),('candidate','新增或修订候选'),('status','查看当前来源绑定状态'),('validate','核查来源、历史与有效状态'),('confirm','记录实际聊天确认或授权Agent核准'),('withdraw','撤回为Unknown'),('delegate','登记用户明确代理授权'),('revoke','撤销代理授权'),('review-ready','将报告标为可审阅'),('approve','登记报告内容确认'),('handoff','更新精简当前交接'),('classify','按正文标注资料用途'),('git-init','明确创建本项目独立Git'),('git-status','查看本项目Git状态'),('git-save','保存中文本地提交，不推送')]:
        p=sub.add_parser(name,help=description);p.add_argument('--project',type=Path,default=ROOT)
        if name=='import':p.add_argument('--source',type=Path,required=True)
        if name=='candidate':p.add_argument('--file',type=Path,required=True)
        if name in ('confirm','withdraw','revoke'):p.add_argument('--id',required=True)
        if name in ('confirm','approve'):p.add_argument('--actor',choices=['human-chat','agent'],required=True);p.add_argument('--delegation-id');p.add_argument('--statement-file',type=Path,required=True);p.add_argument('--binding')
        if name=='delegate':p.add_argument('--statement-file',type=Path,required=True);p.add_argument('--content',action='store_true')
        if name=='withdraw':p.add_argument('--reason',default='');p.add_argument('--actor',choices=['human-chat','agent'],default='agent')
        if name=='review-ready':p.add_argument('--ids',nargs='*',default=[]);p.add_argument('--report',default='outputs/analysis-report.md')
        if name=='handoff':p.add_argument('--summary-file',type=Path,required=True);p.add_argument('--next',required=True)
        if name=='classify':p.add_argument('--id',required=True);p.add_argument('--role',required=True);p.add_argument('--purpose',required=True)
        if name=='git-save':p.add_argument('--message',required=True)
    args=parser.parse_args(argv)
    try:
        command=args.command;result=None
        if command=='serve':
            from .portal import serve
            serve(args.root,args.port,not args.no_browser);return 0
        if command=='new':
            if not (ROOT/'templates').exists() or (ROOT/'project.json').exists():raise WorkbenchError('请从通用工作台主目录新建公司项目')
            result={'project':str(create_project(args.company,args.code,args.profile,args.path))}
        elif command=='link':
            from .workspace import link_project
            result={'project':link_project(args.root,args.directory,args.name)}
        elif command in ('draft','model','report'):
            from .workflow import save_draft,scenario,generate_report
            from .workspace import selected_state
            if command=='draft':result=save_draft(args.project,read_json(args.file))
            elif command=='model':result=scenario(args.project,read_json(args.file))
            else:
                entry={'mode':'generic','path':args.project.resolve()}
                result=generate_report(ROOT,entry,selected_state(entry,args.project.name))
        elif command=='series-audit':
            from .series import profile_series
            result=profile_series(args.source,args.cutoff)
            if args.output:
                if args.output.resolve()==args.source.resolve():raise WorkbenchError('不得覆盖CSV原件')
                if args.output.suffix.lower()!='.json':raise WorkbenchError('检查输出须为JSON，不覆盖其他原件')
                if args.output.exists():raise WorkbenchError('输出已存在，请选择新版本路径保留历史')
                atomic_text(args.output,json.dumps(result,ensure_ascii=False,indent=2)+'\n')
                result={k:v for k,v in result.items() if k!='catalog'}
                result['output']=str(args.output)
        elif command=='doctor':
            result={'python':sys.version.split()[0],'python_path':sys.executable,'git':find_git(),
                    'optional_pypdf':importlib.util.find_spec('pypdf') is not None,'optional_pymupdf':importlib.util.find_spec('pymupdf') is not None,
                    'core_dependencies':'Python标准库；未下载软件或修改全局环境'}
        else:
            store=ReviewStore(args.project)
            statement=args.statement_file.read_text(encoding='utf-8-sig') if getattr(args,'statement_file',None) else ''
            if command=='import':result={'added_sources':import_sources(args.project,args.source)}
            elif command=='index':result=index_sources(args.project)
            elif command=='candidate':
                value=read_json(args.file);values=value if isinstance(value,list) else [value]
                result={'event_ids':[store.upsert(r) for r in values]}
            elif command=='status':result={**store.sync(),'records':store.records(),'report_content_approved':store.report_approved()}
            elif command=='validate':
                result=validate_project(args.project);print(json.dumps(result,ensure_ascii=False,indent=2));return 1 if result['errors'] else 0
            elif command=='confirm':result={'event':store.confirm(args.id,args.actor,statement,args.delegation_id,args.binding)}
            elif command=='withdraw':result={'event':store.withdraw(args.id,args.reason,args.actor)}
            elif command=='delegate':result={'delegation_id':store.delegate(statement,content=args.content)}
            elif command=='revoke':store.revoke_delegation(args.id);result={'revoked':args.id}
            elif command=='review-ready':store.review_ready(args.ids,args.report);result={'report_binding':store.report_binding()}
            elif command=='approve':store.approve_report(args.actor,statement,args.delegation_id,args.binding);result={'content_approved':store.report_approved(),'signature_status':'pending'}
            elif command=='classify':store.classify_source(args.id,args.role,args.purpose);result={'classified':args.id}
            elif command=='handoff':
                summary=args.summary_file.read_text(encoding='utf-8-sig').strip()
                if len(summary)>2200:raise WorkbenchError('交接正文限制2200字符；把细节放引用底稿')
                settings=read_json(store.root/'project.json')
                atomic_text(store.root/'会话交接/CURRENT.md',f'# 当前交接：{settings["company"]}\n\n'+summary+'\n\n下一步：'+args.next+'\n\n先查当前Fact接口及来源绑定，不全文重读历史。细节从outputs/analysis-report.md、docs/source-map.md、tasks/research-plan.md按需进入。\n')
                result=store.sync()
            elif command.startswith('git-'):
                executable=find_git()
                if not executable:raise WorkbenchError('未找到Git；可先使用工作台，安装Git须按用户任务授权处理')
                if command=='git-init':
                    if (store.root/'.git').exists():raise WorkbenchError('本项目Git已存在，保留现有配置')
                    result={'output':git_call(executable,store.root,'init','-b','main')}
                elif not (store.root/'.git').exists():raise WorkbenchError('本项目没有独立Git，不能误用父目录仓库；先明确执行git-init')
                elif command=='git-status':result={'status':git_call(executable,store.root,'status','--short')}
                else:
                    if not args.message.strip():raise WorkbenchError('提交信息不能为空')
                    checks=validate_project(store.root)
                    if checks['errors']:raise WorkbenchError('来源/历史检查失败，不提交：'+'；'.join(checks['errors']))
                    for field,default in [('user.name','Company Analysis Workbench Agent'),('user.email','company-workbench@localhost.invalid')]:
                        r=subprocess.run([executable,'-C',str(store.root),'config','--get',field],capture_output=True)
                        if r.returncode:git_call(executable,store.root,'config','--local',field,default)
                    git_call(executable,store.root,'add','--','.')
                    git_call(executable,store.root,'diff','--cached','--check')
                    result={'output':git_call(executable,store.root,'commit','-m',args.message),'pushed':False}
        if result is not None:print(json.dumps(result,ensure_ascii=False,indent=2))
        return 0
    except (WorkbenchError,OSError,KeyError,ValueError,json.JSONDecodeError) as exc:
        print('操作未完成：'+str(exc),file=sys.stderr);return 1
