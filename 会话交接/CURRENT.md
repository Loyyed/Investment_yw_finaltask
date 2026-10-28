> 2026-10-28发布完成：按本人确认的64文件范围及明确分仓要求，本通用仓库4份（Python/JS条件供给引擎、通用方法、交接）已推Loyyed/Investment_yw_finaltask/main，主体提交0f435163faedd79dec2feb913099a96493585f81，并核对远端一致。公司专属数据、参数与授权未注入通用引擎。本交接后续仅同步该发布状态；既有核验核心、Fact与签署未改。

> 2026-10-27 t−5模型：insight新增opt-in volume_drivers，以实际年份生产量建立滞后供给参照，再经成熟相对修正、额外净库存、投放和承接推演销量。输入公司各自维护，未嵌入案例数据。Python/JS同算，缺原量停止、禁止自由销量增速绕开供给；旧模型回归保持。方法见docs/2026-10-27-t5-conditional-volume.md。本轮引擎/方法已按2026-10-28明确授权推送；旧53清单仅留历史。

# 通用工作台当前交接
> 2026-10-27发布完成：本人明确确认69文件与既定两仓库，通用13个代码/方法已推main 28b6a6e并核远端一致；公司56个成品/说明/索引已推main 994f4ca。原件/合同字节副本/内部底稿仍本地；本次仅发布成果，不产生新Fact、采纳或签署。
> 2026-10-27合同完整性：delivery新增reader_v2.contract_checks可见逐问回答/表格/来源与底稿组件；交付skill新增原文版本—必答条款—正文锚点—底稿—实际关口对照，非列表提问/表格/公式亦查，不以文末文件名代正文答案。原数或模型变更须重审答案；归档、内容覆盖、人审、正式签署、Git发布分别验收。公司案例数字/授权未注入通用代码，核验核心未改。
> 2026-10-25图册增补：V2.0全部14章在“这章在回答什么”后增加“本章的结论与判断”，含直接结论、研究判断、边界/后续观察及来源跳转；原数、图表和原三年情景未变，新文字不继承旧人审。底稿见公司work/research-delivery-v2-20261025/chapter-answers.json。
> 最终入口：公司outputs/投资研究系统_V2.0_总入口.html；18页PPTX/HTML、讲稿、四张PNG/SVG导图齐备。工作台已接同源批次预览与冻结导出，预览不写Fact。验证见公司work/research-delivery-v2-20261025/validation.json。
> 2026-10-25 V2.0交付新增：skills/investment-research-delivery整合确认逻辑、逐合同表达、路演和行业迁移。companybench.delivery提供白话导读/导图/研究起步台；insight对reader_v2规格叠加导读并继续当前来源校验。网页首页“填写研究简报”，new默认生成起步台，start --project可补已有普通项目；草稿/个人勾选不写Fact。core.py原字节保持，新公司不含案例数据/参数/授权。使用见docs/2026-10-25-研究交付V2与起步台.md。

2026-10-25。目标是本目录投资学公司分析通用工作台，远端Loyyed/Investment_yw_finaltask；公司数据在各自独立项目，案例授权与数值不迁移。

- 主方法skills/investment-company-analysis/SKILL.md按题路由。原年报证据链、商业模式、复现审计、研究预测skill保留；本轮新增investment-insight-forecast/references/story-synthesis.md，吸收经营闭环、行动者/责任/时间、价值创造/交付/获取和市场叙事反馈。
- 核验核心companybench/core.py保持原字节。普通项目通过本地UI/真实授权核准；旧项目由legacy_reader隔离调用其原ReviewStore，不改原账本、actor、人审或签名；各独立事实域不合计独立数量。
- 网页流程覆盖材料、核验、计算/情景、研究/合同、方法、报告。报告页优先研究图册，旧依据汇编保留。companybench/insight.py按spec生成离线SVG/图表分析/交互预测，/api/insight打开前核当前权威域和依赖SHA；离线副本标生成快照。nonce沙箱不授同源权限，原导入HTML不变执行策略。
- 图册story_beats解释经营过程，transition连接下一章；apply_story_enrichment叠加作者写的专题和说明，可重复运行，不改原图数据/旧依据绑定或Forecast。公司自己维护版本化叙事JSON，不由工具凭数字生成因果。说明见docs/2026-10-25-故事融合与专题.md。
- 每图analysis含meaning/use/inference，默认折叠；数据口径另层。预测图/表解读随参数变化并保留展开状态，未来仍Forecast。新解释不继承旧认可，正式签署按实际授权和本版另记，同人复核注明。
- 批核默认按来源/口径集中展示，未变有效Fact不重复人审。已核定义直接复用，不把尚未分业态或因果的缺口扩大为定义未知。参考材料身份、分母、单位和样本不自动迁入。
- 原件/完整载荷本地，发布按用户实际授权，只推成果；不强推或处理他人改动。当前已授权两个项目成果同步，最新提交看git log/远端refs。GitHub About字段未通过设置接口修改，不能以中文README替代声称已改About。
- 已通过4项叙事组合合成检查及15页桌面/窄屏、引用/过渡与预测交互；之前22工作流/7状态/5模型检查历史保持。原始项目facts、计算、认可、原件与新解释分别维护；不以测试通过代替公司数据核验。

- 2026-10-25视觉升级：新增visual_charts.py及insight的apply_chart_designs/render_visual_gallery，支持9种青瓷蓝复刻/转译图型、重播、编码说明、可读窄屏横向图形及打印/减少动画。设计层在叙事层之后，不覆盖旧数值，配置与新图仅属公司项目。新增7项几何/数据保护检查，16页实际浏览器通过。方法见research skill的references/visual-replication.md。

- 内容融合纠偏：新增references/content-fusion.md；以研究问题/数据/统计量/机制缺口做覆盖表，不以换皮宣称吸收内容。render新增mind_maps（7节点、章节跳转、证据身份、分析层）；青瓷/常规图同数切换；多断点/刻度密度/点标签控制；双列标签防重叠。公司内容层在设计层之后叠加，旧核心与核验记录不变。详见docs/2026-10-25-内容融合与机制导图.md。

- 方法总结入口：skills/investment-insight-forecast/references/research-playbook.md，整合全景框架、变化/分化、量价/结构/现金/滞后、机制叙事、条件预测、图形及交接；具体专题继续按SKILL路由，不全读。无公司数据/参数/授权迁入；本轮仅文档，无核验核心或模型改动。
