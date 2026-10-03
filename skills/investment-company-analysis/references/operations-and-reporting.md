# Agent操作、报告、验收与交接

## 开工与候选登记

本地窗口适合用户创建/导入/核验。Agent通过程序执行可复现的后台步骤；各例中的公司名称、路径和编号按本次材料替换。

```bash
python workbench.py new --company "研究公司名称" --profile general
python workbench.py import --project "项目路径" --source "原始资料路径"
python workbench.py index --project "项目路径"
python workbench.py classify --project "项目路径" --id S实际编号 --role "年度报告" --purpose "本期集团经营与合并财务披露"
python workbench.py candidate --project "项目路径" --file "候选对象或数组.json"
python workbench.py status --project "项目路径"
```

候选JSON由Agent准备，用户不用编辑。登记前查表头/主体/本期列，关键数字可用不同提取引擎或原图对照，不能只相信摘要/文件名。index未处理的格式另用可用工具阅读，覆盖说明只写实际读过内容。

真实聊天答复保存成文件，由确认命令引用；不放编造原话：

```bash
python workbench.py confirm --project "项目路径" --id R编号 --actor human-chat --statement-file "真实答复.txt"
python workbench.py delegate --project "项目路径" --statement-file "真实授权.txt"
python workbench.py confirm --project "项目路径" --id R编号 --actor agent --delegation-id D实际编号 --statement-file "实际核查方法.txt"
```

有明确内容验收授权才在delegate时加`--content`，不能从原文核准授权推导内容/签名权限。确认原话应指向刚呈现条目/报告，必要时用`--binding`固定所指版本。没有授权时保持候选Unknown，把相关卡片交用户一次确认；不让机器匹配冒充实际核验。

## 报告与验收

报告在outputs/analysis-report.md，先写直接回答与判断状态，再给原件/版本和可比性、三维结果、替代/反方、Unknown影响及下一动作。使用模板结构时按任务裁剪，避免几十个空表占位；没有结果的初始框架明确为未开始，不给用户假成品。

关键图适配资料：同口径时间序列、产品/业务结构、成本/现金分解与经济链。轴、单位、期间、来源、可比性和图示假设清楚；不对无法桥接行业绝对数画连续趋势。创建独立可导出的图像，查看图表及关键原页，不以画出图就宣称数据正确。

把报告实际引用的全部事实/计算ID列入review-ready；不能省略影响结论的数据来绕过失效检查。没有数据、仅Unknown适用性报告时说明现有覆盖，不冒充完成财务定量分析。

```bash
python workbench.py review-ready --project "项目路径" --ids R编号 C编号
python workbench.py approve --project "项目路径" --actor human-chat --statement-file "实际审阅答复.txt"
python workbench.py validate --project "项目路径"
```

用户可以在窗口直接认可本版结论与Unknown。明确委托Agent内容验收时，用approve的agent身份、有效委托编号及实际验收依据文件，不再次请求同一授权。报告改变、引用证据失效才复核受影响版本；无关新候选不使旧报告全部失效。

docs/acceptance.md逐项说明实际合同/目的、成果路径、核准人类型、真实动作与结果；“内容完成”和“正式签署”单列。没有实际签署不能勾签署项。程序校验通过也不能代替用户/Agent按授权对逻辑和支持边界的实际审阅。

## Git与迁移

工具包Git只维护方法、程序和模板，projects默认忽略。独立公司Git必须位于该项目根，不能误用父仓库。按实际请求可用git-init/git-save保存中文本地提交；git-save不推送，发布目标由用户指定并核对远程/分支/文件范围。已有授权继续执行，不每次重问；当前任务没有发布授权就交付本地可审阅结果。

不复制SSH私钥、密钥、机器缓存或全局配置。项目复制包含原件、程序、技能及相对路径；本机Python路径和文字缓存忽略。原始字节/SHA和Git版本并存，修改原件导入新版、旧结论标弃用或新提交说明，不靠强推删历史。现有远程有内容时先核差异，不覆盖未知项目。

## 交接与用户体验

CURRENT通常只写：公司/目标/截止、当前成果入口、核准与授权索引、关键冲突及边界、完成条件与唯一下一步。稳定偏好放DECISIONS，原话与事件留evidence；临时检查/日志留runtime或忽略目录，不全文重读。

```bash
python workbench.py handoff --project "项目路径" --summary-file "精简节点摘要.txt" --next "一个明确的下一动作"
```

已批准内容及已核数字不要求重复确认。用户提出状态问题时简洁答复再继续；新指令作为当前工作调整。缺证问法说明具体影响，能自主解决的先解决；最终答复给结果、主报告与确需用户操作的事项，文件说明/代码细节放附录。
