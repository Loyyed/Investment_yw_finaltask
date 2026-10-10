from pathlib import Path
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs, urlencode
import base64, html, json, mimetypes, secrets, sys, webbrowser, re
from .core import ROOT, ReviewStore, WorkbenchError, create_project, import_sources, contained, file_name, atomic_text, read_json

from .research import research_summary

def projects(root):
    root=Path(root).resolve()
    if (root/'project.json').exists():return {root.name:root}
    directory=root/'projects'
    return {p.name:p for p in sorted(directory.iterdir()) if p.is_dir() and not p.is_symlink() and (p/'project.json').is_file()} if directory.exists() else {}

def markdown_html(text,base,project):
    def inline(s):
        s=html.escape(s)
        def link(m):
            image,label,url=m.group(1),m.group(2),html.unescape(m.group(3)).strip('<>')
            if url.startswith(('https://','http://')):href=url
            elif url.startswith('#'):href=url
            else:
                relative=(base/url.split('#')[0]).as_posix()
                href='/file?'+urlencode({'project':project,'path':relative})
                if '#' in url:href+='#'+url.split('#',1)[1]
            if image:return '<img src="'+html.escape(href,quote=True)+'" alt="'+label+'" style="max-width:100%">'
            return '<a href="'+html.escape(href,quote=True)+'" target="_blank" rel="noopener">'+label+'</a>'
        s=re.sub(r'(!?)\[([^\]]+)\]\(([^)]+)\)',link,s)
        s=re.sub(r'\*\*(.+?)\*\*',r'<strong>\1</strong>',s)
        s=re.sub(r'`([^`]+)`',r'<code>\1</code>',s)
        return s
    lines=text.splitlines();out=[];code=False;table=False;listing=False
    for line in lines:
        if line.startswith('```'):
            if table:out.append('</tbody></table></div>');table=False
            out.append('</code></pre>' if code else '<pre><code>');code=not code;continue
        if code:out.append(html.escape(line)+'\n');continue
        if line.strip().startswith('|'):
            cells=[v.strip() for v in line.strip().strip('|').split('|')]
            if all(re.fullmatch(r':?-+:?',v) for v in cells):continue
            if not table:out.append('<div class="table"><table><tbody>');table=True
            out.append('<tr>'+''.join('<td>'+inline(v)+'</td>' for v in cells)+'</tr>');continue
        if table:out.append('</tbody></table></div>');table=False
        if line.startswith('<!--'):continue
        heading=re.match(r'^(#{1,6})\s+(.*)',line)
        if heading:
            level=len(heading[1]);out.append(f'<h{level}>'+inline(heading[2])+f'</h{level}>')
        elif line.strip():out.append('<p>'+inline(line)+'</p>')
    if table:out.append('</tbody></table></div>')
    if code:out.append('</code></pre>')
    return '<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>工作台文档</title><style>body{font:16px/1.8 "Microsoft YaHei",sans-serif;margin:32px auto;max-width:1080px;padding:0 24px;color:#21334a}h1,h2{line-height:1.4}a{color:#176874}code,pre{background:#f1f5f8;overflow:auto}pre{padding:16px}.table{overflow:auto}table{border-collapse:collapse;font-size:14px;width:100%}td{border:1px solid #d7e1e8;padding:8px;vertical-align:top}tr:first-child{font-weight:bold;background:#edf3f5}strong{color:#164b56}</style><body>'+''.join(out)+'</body></html>'

def make_server(root=ROOT,port=0):
    root=Path(root).resolve();token=secrets.token_hex(24)
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,format,*args):pass
        def send(self,data,status=200,content='application/json; charset=utf-8',disposition=None):
            if isinstance(data,(dict,list)):data=json.dumps(data,ensure_ascii=False).encode('utf-8')
            elif isinstance(data,str):data=data.encode('utf-8')
            self.send_response(status);self.send_header('Content-Type',content);self.send_header('Content-Length',str(len(data)))
            self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff')
            self.send_header('Content-Security-Policy',"default-src 'self'; style-src 'unsafe-inline'; script-src 'nonce-"+token+"'; connect-src 'self'; frame-ancestors 'none'" if self.path.split('?')[0]=='/' else "default-src 'none'; style-src 'unsafe-inline'; img-src 'self' data:; sandbox allow-popups allow-top-navigation-by-user-activation")
            if disposition:self.send_header('Content-Disposition',disposition)
            self.end_headers();self.wfile.write(data)
        def host_ok(self):
            port=self.server.server_address[1]
            return self.headers.get('Host') in ('127.0.0.1:'+str(port),'localhost:'+str(port))
        def project(self,name):
            p=projects(root).get(name)
            if p is None:raise WorkbenchError('项目不存在，请刷新后选择')
            return p
        def do_GET(self):
            if not self.host_ok():self.send({'error':'不允许的Host'},403);return
            route=urlparse(self.path);query=parse_qs(route.query)
            try:
                if route.path=='/':
                    page=(Path(__file__).parent/'ui.html').read_text(encoding='utf-8').replace('__TOKEN__',token)
                    self.send(page,content='text/html; charset=utf-8');return
                if route.path=='/api/state':
                    inventory=projects(root);selected=query.get('project',[''])[0];value={'projects':[{'id':k,**read_json(p/'project.json')} for k,p in inventory.items()], 'single_project':(root/'project.json').exists()}
                    if selected:
                        p=self.project(selected);store=ReviewStore(p);records=store.records();settings=read_json(p/'project.json')
                        try:binding=store.report_binding()
                        except (WorkbenchError,OSError,KeyError):binding=None
                        value['selected']={'id':selected,'settings':settings,'records':records,'sources':store.source_rows(),
                            'counts':{'Fact':sum(r['effective_state']=='Fact' for r in records),'Unknown':sum(r['effective_state']=='Unknown' for r in records),'total':len(records)},
                            'research':research_summary(p,records),
                            'delegations':store._read()['delegations'],'report_binding':binding,'content_approved':store.report_approved(),
                            'prompt':f'请先读取 {p.as_posix()}/AGENTS.md 和会话交接/CURRENT.md，再使用 skills/investment-company-analysis/SKILL.md 分析{settings["company"]}。先读docs/learning-path.md并核材料和实际要求，按work/contract-acceptance.md逐条执行；检查work/yearly-changes.md各年重大变化，完整推进原值、口径、变化及三维研究；在我的授权范围内执行，核验时给我简洁的本地入口，保留Unknown与真实历史，最后给中文报告和精简交接。'}
                    self.send(value);return
                if route.path=='/file':
                    selected=query.get('project',[''])[0]
                    base=self.project(selected) if selected else root
                    relative=query.get('path',[''])[0]
                    if not relative:raise WorkbenchError('该路径不提供浏览器访问')
                    path=contained(base,relative)
                    if any(part.startswith('.') or part in ('runtime','__pycache__') for part in path.relative_to(base.resolve()).parts):raise WorkbenchError('该路径不提供浏览器访问')
                    if not path.is_file():raise WorkbenchError('文件尚未生成')
                    suffix=path.suffix.lower()
                    if suffix=='.md':self.send(markdown_html(path.read_text(encoding='utf-8-sig'),Path(relative).parent,selected),content='text/html; charset=utf-8');return
                    if suffix in ('.pdf','.png','.jpg','.jpeg','.svg'):
                        self.send(path.read_bytes(),content=mimetypes.guess_type(path.name)[0] or 'application/octet-stream');return
                    self.send(path.read_bytes(),content='application/octet-stream',disposition='attachment');return
                self.send({'error':'页面不存在'},404)
            except (WorkbenchError,OSError,KeyError,ValueError) as exc:self.send({'error':str(exc)},400)
        def do_POST(self):
            port=self.server.server_address[1]
            allowed_origins={'http://127.0.0.1:'+str(port),'http://localhost:'+str(port)}
            if not self.host_ok() or self.headers.get('X-Workbench-Token')!=token or self.headers.get('Origin') not in allowed_origins|{None}:
                # Drain small rejected requests so Windows clients receive the 403
                # rather than an abrupt reset caused by an unread request body.
                try: rejected_length=int(self.headers.get('Content-Length','0'))
                except ValueError: rejected_length=0
                if 0<rejected_length<=1024*1024:self.rfile.read(rejected_length)
                self.send({'error':'请求身份或来源不符'},403);return
            try:
                length=int(self.headers.get('Content-Length','0'))
                if not 0<length<=75*1024*1024:raise WorkbenchError('请求大小须为1字节—75MB；大量资料使用目录导入')
                data=json.loads(self.rfile.read(length));action=urlparse(self.path).path
                if action=='/api/new':
                    if (root/'project.json').exists():raise WorkbenchError('独立公司项目内不创建其他公司；请从通用工作台新建')
                    p=create_project(data['company'],data.get('code',''),data.get('profile','general'),kit=root)
                    self.send({'project':p.name});return
                p=self.project(data['project']);store=ReviewStore(p)
                if action=='/api/import':
                    if data.get('folder'):added=import_sources(p,data['folder'])
                    else:
                        folder=p/'runtime/uploads'/secrets.token_hex(8);folder.mkdir(parents=True)
                        for f in data.get('files',[]):
                            target=contained(folder,file_name(f['name']))
                            if target.exists():raise WorkbenchError('上传文件重名，请分批导入')
                            content=base64.b64decode(f['base64'],validate=True)
                            if len(content)>50*1024*1024:raise WorkbenchError('单文件超过50MB，改用目录导入')
                            target.write_bytes(content)
                        added=import_sources(p,folder)
                    self.send({'added':len(added)});return
                if action=='/api/confirm':store.confirm(data['id'],'human-ui',expected_binding=data['binding'])
                elif action=='/api/unknown':store.withdraw(data['id'],data.get('reason','用户选择保留Unknown，未确认原值'))
                elif action=='/api/delegate':
                    scope='用户在本项目窗口点击授权：允许Agent核准本公司项目当前及后续原始披露与计算，需核原文、口径、算术和支持边界，不伪造本人点击或签名。'
                    if data.get('content'):scope+='同时允许Agent完成本项目内容验收。'
                    store.delegate(scope,'human-ui',content=bool(data.get('content')))
                elif action=='/api/revoke':store.revoke_delegation(data['id'])
                elif action=='/api/approve':store.approve_report('human-ui',expected_binding=data['binding'])
                else:raise WorkbenchError('未知操作')
                self.send({'ok':True})
            except (WorkbenchError,OSError,ValueError,KeyError,TypeError) as exc:self.send({'error':str(exc)},400)
    server=ThreadingHTTPServer(('127.0.0.1',port),Handler);server.daemon_threads=True
    server.workbench_token=token
    return server

def serve(root=ROOT,port=0,open_browser=True):
    server=make_server(root,port);url='http://127.0.0.1:'+str(server.server_address[1])
    print('工作台：'+url,flush=True);print('仅本机访问；关闭本窗口或按Ctrl+C结束。',flush=True)
    if open_browser:webbrowser.open(url)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()
