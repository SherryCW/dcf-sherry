# dcf-sherry — 高增长股估值治理框架 / Governed Valuation for Growth Stocks

> 双语文档 / Bilingual README：[中文](#中文) ｜ [English](#english)

fork 自 `dcf-valuation-governance` v1.0.1（sha256
`d110c1811877298f2bed958c93353cc3cbee1309211780b3955b9888423672d4`）。

原版回答的是「怎么搭一个 DCF，并审计它」。这个 fork 补上排在它前面的那个问题：**这只高增长股配得上哪种估值方法？它现在的价格到底在要求什么？**

A fork of `dcf-valuation-governance` v1.0.1. The original answered *how do we build and audit a
DCF?* This fork adds the question that comes first: **which method does this growth stock deserve,
and what does its price actually require?**

---

<a id="中文"></a>
## 中文

### 三层架构

| 层 | 要回答的问题 | 工具 | 细则 |
|---|---|---|---|
| 0 — 粗筛 | 这只票配哪种方法？ | PEG 只作粗筛，分母用前瞻共识增速；按「久期 × 质量」分类 | `references/growth-triage.md` |
| 1 — 定价 | 现价已经隐含了什么？ | 反向 DCF：反推隐含永续增速 + 隐含增长久期 | `references/valuation-routing.md` |
| 2 — 闸门 | 这个增长假设站得住吗？ | ROIC − WACC、利润→现金转化、杠杆与稀释、久期一致性 | `references/growth-quality-gates.md` |

### 五条非协商原则（继承并扩展）

1. 高增长股永远不看静态 PE。
2. PEG 的分母必须是前瞻预期。历史 CAGR 只能当验证输入——CLI 会输出 `used_as_peg_denominator: false`，让这点可审计。
3. 分类标准是久期与质量，不是增速高低。
4. 闸门只能拦住或放行一个结果，不能决定数值。
5. 粗筛结果不是估值，更不是买卖指令。

### 相对原版改了什么

- **新增** `references/growth-triage.md`：第 0 层粗筛、红旗清单、正常化盈利路由。
- **新增** `references/growth-quality-gates.md`：增长质量闸门，pass / warn / fail 三态。
- **新增** CLI 的 `screen` 子命令，以及 `run` 的 `growth_quality` 检查块。
- **新增** `reverse` 的隐含增长久期：现价要求共识增速再撑几年，并与声明的竞争优势久期对比。
- **扩展** 方法路由（正常化盈利、周期中枢倍数）、治理闸门（前瞻 G 规则、ROIC − WACC、终值增速须与再投资一致）、工作簿合同（32 个模块，含粗筛表与久期表）。
- **修好** 测试脚手架：上游测试从一个「装成 skill 后并不存在」的仓库路径导入 CLI，导致 `unittest discover` 实际跑 0 个有效测试（1 个 error）。现在改为按 skill 根目录解析。
- **删掉** 原版反向 DCF 里一个苹果比橘子的比较：拿隐含**永续**增速去比**近端**共识增速。现在近端共识只进入久期计算。

### 快速开始

```bash
PY=python3
$PY scripts/dcf_cli.py screen --input examples/synthetic-growth-screen.json
$PY scripts/dcf_cli.py screen --input examples/synthetic-cyclical-screen.json
$PY scripts/dcf_cli.py validate --input examples/synthetic-consumer-case.json
$PY scripts/dcf_cli.py run --input examples/synthetic-growth-case.json
$PY scripts/dcf_cli.py reverse --input examples/synthetic-growth-case.json \
  --scenario base --target-price 42 --sustained-growth 0.18
$PY -m unittest discover -s tests -v
```

### 三个示例各自在证明什么

**`synthetic-growth-screen.json`** — 前瞻增速 50%、ROIC − WACC 差 13%、无红旗、优势久期 6 年。粗筛结论 `structural_growth` → `reverse_dcf_pricing`，状态 `PASS`，中性 PEG 0.67。

**`synthetic-cyclical-screen.json`** — 从低谷年份反弹。中性 PEG **0.30，全书最便宜**，但它根本不是成长股：`cyclical_normalize` → `normalized_earnings`，状态 `DRAFT_REVIEW`。**这就是第 0 层存在的全部理由。**

**`synthetic-growth-case.json`** — 结构性成长股的 DCF，十项增长质量检查全部通过。但状态仍是 `DRAFT_REVIEW`：牛市情景下终值占企业价值 85%。**成长股 DCF 被终值主导，恰恰是第 1 层必须改用反向 DCF 定价的原因。**

价格取 42 时，反推结果：

```text
隐含永续增速            6.62%   （模型假设 3.00%）
再投资可支撑增速        3.08%   （ROIC 22% × 再投资率 14%）
是否由再投资支撑        false
隐含增长久期            7.3 年  （按 18% 增速外推）
声明的竞争优势久期      7.0 年
久期是否落在优势期内    false
```

这就是整个 skill 想说出的那句话——不是「增速有没有超过 30%」，而是：

> **这个价格需要 18% 的增速再撑 7.3 年，而你说你的优势只能撑 7 年。**

### 什么被有意留在外面

这是一份清洗过的公开 skill，不是任何生产引擎的导出。真实公司案例、持仓、授权研究、参考模型、源文件、生成的工作簿、本地运行日志、机器身份与凭据，全部刻意排除。

### 局限，如实说明

- CLI 是一份基于固定预测结构的参考实现，不能替代完整的工作簿。
- 隐含久期的求解是把末年经济指标按固定增速外推。它是反推，不是预测——输出里也这么标注。
- 粗筛只依据你提供的证据做分类，不去抓取或核实来源；核实由治理闸门负责。
- 增长久期是判断。这个 skill 只能逼你把它写明确、给出处、可证伪——它无法替你判断对不对。

### 归属

上游：`dcf-valuation-governance` v1.0.1。`SECURITY.md` 与披露边界原样保留。

### 许可

MIT —— 见 [LICENSE](LICENSE)。

### 免责声明

仅供教育与研究。这里没有任何内容是投资建议、推荐或收益承诺。

---

<a id="english"></a>
## English

### The three layers

| Layer | Question | Tool | Reference |
|---|---|---|---|
| 0 — Triage | Which method does this name deserve? | PEG as a coarse filter, with forward-consensus growth; classification by growth duration × quality | `references/growth-triage.md` |
| 1 — Pricing | What does the price already assume? | Reverse DCF: implied perpetual growth, and implied growth duration | `references/valuation-routing.md` |
| 2 — Gates | Is the growth assumption admissible? | ROIC − WACC, cash conversion, leverage and dilution, duration consistency | `references/growth-quality-gates.md` |

### Non-negotiables, inherited and extended

1. Growth stocks are never priced off a static P/E.
2. PEG denominators are forward expectations. Historical CAGR is a verification input only — the CLI records `used_as_peg_denominator: false` to make that auditable.
3. Classification is by duration and quality, never by a growth threshold.
4. Gates can hold or block a result. They never set a value.
5. A screen result is never a valuation, and neither is a trade instruction.

### What the fork changed

- **New** `references/growth-triage.md` — Layer 0 screen, red flags, normalization routing.
- **New** `references/growth-quality-gates.md` — growth-quality gates, pass/warn/fail.
- **New** `screen` command in the CLI, plus a `growth_quality` block for `run`.
- **New** implied growth duration in `reverse`: how many further years of consensus growth the price requires, compared against the stated duration of the advantage.
- **Extended** routing (normalized earnings and mid-cycle multiples), governance gates (forward-G rule, ROIC − WACC, reinvestment-consistent terminal growth), and the workbook contract (32 modules, including a triage sheet and a growth-duration schedule).
- **Fixed** the test harness: the upstream tests imported the CLI from a repository path that does not exist once the skill is installed, so `unittest discover` failed on 1 error and ran 0 real tests. The suite now resolves the script relative to the skill root.
- **Removed** an apples-to-oranges comparison in the original reverse DCF design, where an implied *perpetual* growth rate was compared against a *near-term* consensus rate. Near-term consensus now enters the duration calculation instead.

### Quick start

```bash
PY=python3
$PY scripts/dcf_cli.py screen --input examples/synthetic-growth-screen.json
$PY scripts/dcf_cli.py screen --input examples/synthetic-cyclical-screen.json
$PY scripts/dcf_cli.py validate --input examples/synthetic-consumer-case.json
$PY scripts/dcf_cli.py run --input examples/synthetic-growth-case.json
$PY scripts/dcf_cli.py reverse --input examples/synthetic-growth-case.json \
  --scenario base --target-price 42 --sustained-growth 0.18
$PY -m unittest discover -s tests -v
```

### What the examples demonstrate

**`synthetic-growth-screen.json`** — a 50% forward grower with a 13% ROIC − WACC spread, no red flags, and a 6-year advantage. Screen: `structural_growth` → `reverse_dcf_pricing`, status `PASS`. PEG 0.67 base.

**`synthetic-cyclical-screen.json`** — a rebound off a trough year. Base PEG is **0.30**, the cheapest name in the book, and it is not a growth stock at all: `cyclical_normalize` → `normalized_earnings`, status `DRAFT_REVIEW`. This is the whole point of Layer 0.

**`synthetic-growth-case.json`** — the DCF for a structural grower with all ten growth-quality checks passing. Its status is still `DRAFT_REVIEW`, because terminal value is 85% of enterprise value in the bull case. A growth DCF dominated by its terminal value is exactly why Layer 1 prices with a reverse DCF instead.

At a price of 42 on that case:

```text
implied_terminal_growth                     6.62%   (model assumes 3.00%)
sustainable_growth_reference                3.08%   (ROIC 22% x reinvestment 14%)
funded_by_reinvestment                      false
implied_growth_duration_years               7.3     (at 18% sustained growth)
stated_growth_duration_years                7.0
duration_within_stated_advantage            false
```

Which is the sentence the whole skill exists to produce: not "is growth above 30%", but **"this price needs 18% growth for 7.3 more years, and the advantage is argued to last 7."**

### What remains private

This is a sanitized public skill, not a dump of any production engine. Real company cases, holdings, licensed research, reference models, source documents, generated workbooks, local run logs, machine identity, and credentials are deliberately excluded.

### Limitations, stated honestly

- The CLI is a reference implementation on a fixed forecast structure. It is not a substitute for an integrated workbook.
- The implied-duration solve extrapolates final-year economics at a constant growth rate. It is an inverse, not a forecast, and it is labelled as such in the output.
- The screen classifies from supplied evidence. It does not fetch or verify sources; the governance gates do that.
- Growth duration is a judgment. The skill forces it to be explicit, sourced, and falsifiable — it cannot make it correct.

### Attribution

Upstream: `dcf-valuation-governance` v1.0.1. `SECURITY.md` and the disclosure boundary are carried over unchanged.

### License

MIT — see [LICENSE](LICENSE).

### Disclaimer

Educational and research use only. Nothing here is investment advice, a recommendation, or a promise of returns.
