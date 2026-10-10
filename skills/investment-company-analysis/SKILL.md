---
name: investment-company-analysis
description: 建立或继续基于原始年报和任务材料的公司分析，完成来源核验、指标口径与可比性、商业模式/行业竞争/竞争优势研究，以及中文报告和精简交接。用于跨公司复用研究工作台；不以公司叙事、算术或上一家公司授权代替当前项目证据。
---

# 投资学公司分析

目标是交付用户能读懂、可复核、可继续使用的公司分析。先直接回答当前问题，再展示证据、机制与边界；完成实际要求，不以模板文件齐全代表分析完成。

## 进入项目

先读当前公司会话交接/CURRENT.md、project.json与实际任务。已有项目按摘要索引读本次相关文件，不全文重读日志或重扫原件。新公司用通用根目录的`python workbench.py new --company ...`建立；CLI和本地窗口无需额外包，每个项目包含程序及方法快照。

没有具体公司时只准备框架，不生成Fact或结论。没有教师合同时使用通用研究计划，不把自己写的计划冒充已发合同。姓名和真实签署另行安排。实际用户指令优先于模板与旧MD限制；在当前项目记录已给的授权并继续执行，不重复请求。

## 按问题加载参考

| 当前工作 | 只需读取的参考 |
| --- | --- |
| 充分学习课程、初学者公式理解或行业/优势方法 | [course-learning.md](references/course-learning.md) |
| 多合同逐项执行、年度变化、清洗与签署流程 | [research-operations.md](references/research-operations.md) |
| 新公司/新增材料/任务映射 | [workflow.md](references/workflow.md) |
| 原值、聊天核准、代理核准、Fact失效或撤回 | [evidence-and-review.md](references/evidence-and-review.md) |
| 口径、同比、均价毛利、生产成本或现金转换 | [calculations-and-comparability.md](references/calculations-and-comparability.md) |
| 商业模式、行业竞争和优势链 | [analysis-framework.md](references/analysis-framework.md) |
| 金融/工业/消费等行业迁移 | [industry-adapters.md](references/industry-adapters.md) |
| 曾遇到的易错点与操作体验 | [experience-and-failure-modes.md](references/experience-and-failure-modes.md) |
| 命令、报告、验收、Git和会话交接 | [operations-and-reporting.md](references/operations-and-reporting.md) |
| 有课程合同、披露地图、研究卡或工具组件要求 | [course-and-tool-adapters.md](references/course-and-tool-adapters.md) |

## 必须保留的分析与核准关系

1. 原件、版本、期间、单位、主体、合并范围和具体表行列共同定义一条证据。解包及乱码名称按正文识别；检索缓存和文件名不能证明内容。
2. 提取候选先为Unknown。统一用`companybench.core.ReviewStore(project).facts()`对当前原件和计算依赖核有效Fact；导出Markdown、交接和上次结果不单独证明Fact。明确区分原披露与派生算术。
3. 用户实际窗口确认或真实聊天答复可核准对应已呈现记录；不把开窗、机器匹配、选择研究题、逻辑认可或润色变为新数值确认。用户明确委托Agent原文核准时，登记本公司授权，执行真实检查，如实标Agent。新公司不继承旧项目授权。
4. 事实真实与研究用途合适是不同判断。保留被排除原值、旧版本、真实修正/撤回与Unknown；不要强制重建含人工修改的旧成果。
5. 统计和算术的支持边界不能扩大为终端需求、品牌因果、生命周期Fact或真实生产成本。五种状态分开，允许有证据的暂定Interpretation，同时明确反证；不因缺少因果识别否定可计算的描述统计。
6. 在当前要求和授权内自主完成所有独立工作。确需用户判断时给一个集中、可审阅的入口，已确认内容和未变输入不重复操作。不把日志或完整历史塞入下次默认上下文。

## 完成标准

有来源/要求地图、带边界的已核数据和真实口径修正；有与任务匹配的变化核验；三个维度得到直接回答、可观察变量、替代解释、反方及反证；Unknown说明影响和补证；报告配适当图表、原文定位、复算路径及文件导航。逐项记录内容验收依据和实际核准身份，正式签署单列。

完成节点更新精简CURRENT.md与当前报告入口。代码或计算改动做有意义的验证，原件/历史/链接与Git范围核查一次；通过后推进交付，不反复扩大全套测试。外部发布只按用户实际指令执行，先确认项目独立Git与远程，中文提交，保留弃用版本或标签，不自动强推。
