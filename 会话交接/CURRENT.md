# 通用工作台当前交接

- 这是可复用工具包，尚未选公司、导入来源或登记Fact，没有签署和公司研究结论。
- 从README.md进入；Agent使用skills/investment-company-analysis/SKILL.md，参考按需读，不全文扫描旧项目或日志。
- 启动工作台创建项目、添加材料，再复制开工指令给Agent。项目默认在projects，复制后可独立运行。
- 事实接口为companybench.core.ReviewStore(project).facts()，按当前原件、口径及依赖核有效状态。人工确认、用户授权Agent核准与逻辑认可分开记录；新公司默认无代理授权。
- 最终框架覆盖资料与要求、定位/提取、口径、可比性/变化、商业模式/行业竞争/竞争优势、财务接续、验收/报告/交接；不照搬原公司专用数值或结论。
- 下一步：填写公司名称、提供原件与目标。Git/外部发布以本次实际指令为准，不继承此前项目权限。
- 工具包交付节点：skill-creator结构验证、32项隔离测试、本地浏览器首页与空白项目核查；验证细节见docs/验证记录.md。仓库为Loyyed/Investment_yw_finaltask，发布状态以Git当前HEAD和远程为准。
