# 通用工作台当前交接

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
