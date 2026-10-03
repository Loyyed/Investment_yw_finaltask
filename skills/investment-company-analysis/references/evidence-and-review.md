# 证据、权限与当前有效Fact

## 三种核准方式

默认本人核对原件并在窗口点击；真实聊天答复指向已展示的候选/计算也可登记。明确代理授权只在当前公司项目生效：保留用户原话/实际按钮动作、覆盖范围，核准身份为Agent。授权使Agent可以完成原文核验，不意味着机器候选自然通过，也不自动确认品牌因果、生命周期或签名。

Agent不要调用窗口human-ui确认来模拟本人点击。真实聊天确认用human-chat，保存原话及所指编号/当前绑定；Agent独立核准用agent，必须有有效delegation_id并写实际核查方法。只保存用户真实表达；专业润色可另写，不能把新增限定悄悄署给用户。

内容审阅与数值核准分别维护。批准机制链只表示该逻辑/Unknown处理被接受，不使数字从Unknown变Fact。报告认可绑定本版报告和它实际引用的记录，新增无关候选不会迫使全篇重审。

## 程序接口与记录结构

入口是项目根目录的workbench.py；Agent先看`python workbench.py --help`和相关子命令即可，不必把整个程序读进上下文。

```python
from companybench.core import ReviewStore
store = ReviewStore(project_path)
current_facts = store.facts()        # 每次使用前重核，不相信旧导出
current_records = store.records()    # 包括失效、Unknown及计算问题
```

候选通过candidate命令导入一个JSON对象或对象数组。以下是格式说明，示例值并非真实公司数据，不由工具包预登记：

```json
{
  "id": "R_CURRENT",
  "kind": "disclosure",
  "claim": "研究所采用口径的本期营业收入",
  "value": "120",
  "scope": {
    "period": "本期报告年度",
    "entity": "研究公司",
    "basis": "合并",
    "definition": "商品及服务营业收入",
    "unit": "人民币元",
    "currency": "CNY",
    "version": "指定原年报及发布日期"
  },
  "sources": [{"source_id": "S_SOURCE_ID", "location": "PDF第N页，合并利润表，本期列，营业收入行"}],
  "support_boundary": "仅证明该版本/期间/合并口径原值，不证明增长原因"
}
```

source_id应换成import返回的实际编号。不能凭文件名猜年份/版本；value使用精确十进制字符串，文本主张可省略数值。引用必须定位到PDF页与表行列，或文本行/表格单元格等。record自带的state初始不接受Fact，程序只经核准事件形成当前Fact。

计算例子：

```json
{
  "id": "GROWTH",
  "kind": "derived",
  "claim": "同口径营业收入同比",
  "scope": {"period": "本期相对上期", "entity": "研究公司", "basis": "合并", "definition": "同比变化", "unit": "%"},
  "formula": {
    "op": "growth", "inputs": ["R_CURRENT", "R_PREVIOUS"], "scale": "100", "precision": 2,
    "comparability": {"version": true, "period": true, "currency_unit": true, "entity": true, "scope": true, "definition": true, "restatement": true}
  },
  "support_boundary": "已核输入和明确可比性下的算术，不证明经营原因"
}
```

先登记候选、呈现输入与可比性依据，再核准。七项true须来自实际核查，不能为了让程序通过随意填写。当前支持sum、difference、ratio、margin、growth、blank-zero，依赖必须已为当前Fact才允许结果成Fact；组均价倍率根据原单位选择。

## 当前状态如何形成

evidence/ledger.json保留候选版本、核准/撤回、真实授权和内容审阅；事件含时间、前事件摘要与本次摘要。程序还核候选/授权/内容视图与历史相符，防止只编辑导出或当前列表绕过历史。它是完整性检查，不是对人的密码学身份认证或法律签名。

原披露绑定候选全文、source_id、实际原件SHA、具体位置；计算还绑定公式、输入版本及确认事件、算得值和当前计算代码SHA。源文件缺失/改变、候选口径改变、输入撤回/重核、公式或计算代码变化会使相关旧确认失效。原件修改时应导入新版、保留旧文件，不能“修复”旧原件后覆盖历史。

只有计算相关代码变化影响计算绑定，未变原文确认仍可复用。撤销Agent授权使其有关代理确认不再当前有效；不会伪造新的本人确认。旧事件与原候选保留，facts.md、资料地图和CURRENT为派生视图/索引。

## 各状态的边界

- Fact：核准的原披露、公司确实作出某叙事、或限定算术；不是不带口径的“绝对真相”。
- Interpretation：由数据支持、能反证的机制/行业/竞争判断；写清作者、理由与范围。
- Forecast：向未来延伸的可检验预测，标时点、变量和假设；不能用期后结果偷回填当时判断。
- Decision：实际决策，只有本次任务要求及适当依据支持时形成，不由统计或模板自动产生。
- Unknown：证据/口径/假设仍不足；写缺什么、影响什么与下一动作。

不把多个来源相同引用、多个Agent一致答案或重复年度叙事计算为独立验证。数据组与单个数值的记录数不同，有重叠时分域说明，不能相加为独立证据总数。
