---
name: template-forge
description: >-
  做什么：把一份参考文档的外观（骨架 + 字体色板 + 版式）提取成可复用的 Template Spec
  (JSON)，再用它渲染 docx/pptx/html/md 新文档——一次提取、多处渲染，数值全部来自
  spec、零硬编码。何时用：用户说「以这份为模板做一份…」「照这个格式出一份…」
  「把这个的样式套到…」「提取这个文档的字体和版式」「按这个模板批量…」，且手里有参考文档。
  何时不用：纯内容创作（无参考件）、无参考件的审美改造、网页开发、修改原件本身。
  触发词：模板/参考文档/样板/这个格式/这套样式/版式 + 做成/照这个/按这个来/沿用/套用/提取样式/生成一份。
  反触发：「帮我写一份方案」「这个 PPT 帮我改好看点」「做个网站」。语言：中文为主，技术术语保留英文。
---

# template-forge — 模板规格提取与跨格式渲染

一次提取、多处渲染：把「这份文档的样子」变成一份可复用的规格（Template Spec JSON），
再用规格驱动渲染出新文档。核心不是写文档，是把外观变成规格。

## 核心主张（不可违背）

1. **clone-and-fill 优先，rebuild 兜底，degrade 明示**——同源复制底稿继承 styles.xml /
   slideMaster / CSS 才能保真；跨源重建只到样式级；物理不可达的组合直接声明并给替代建议
2. **渲染数值只能来自 spec.json**——脚本内不得硬编码字号/色值/边距
3. **源文件只读**（GATE-1）——产物永远写 `./output/`，写操作命中源路径即 `E-SRC-WRITE` 阻断
4. **零占位符残留**——交付物中 `{{槽位}}`/「内容待补」即 `E-TEMPLATE-LEFTOVER`，verify 拦截
5. **偏离必须留痕**——任何偏离源模板的 token 改动写进 `spec.deviated_from`（字段/源值/新值/用户原话）

## Workflow（六步，严格顺序）

1. **收件与判型**：确认源文件格式、目标格式、文本层可读性。源为 pdf 时先跑
   `python scripts/extract.py <src> --probe-only`——无文本层立即 `E-SRC-NOTEXT`（见
   references/error-codes.md），给出「提供可复制文本版 / 先 OCR / 仅视觉配色参考」三选一
2. **澄清（第 0 问 + 四问，一次性问完）**：
   - **第 0 问（必问，教训 #1）**：这份文档给谁看、拿来做什么？（决定详细度与保真取向）
   - Q1 目标格式（docx/pptx/html/md）｜Q2 保真级别（选项式：结构像/样式像/版式像/一模一样，
     每项注明该源×目标组合能否达到，见 references/capability-matrix.md）｜
     Q3 内容与槽位（新内容从哪来；骨架哪些节保留/替换/删除）｜Q4 固定块（页眉页脚/
     免责声明/公司名等必须原样保留的）
   - 用户说「就这样直接出」→ 跳过打样，spec 记 `probe_skipped: true`
3. **extract**：`python scripts/extract.py <src> --out <spec路径>` 抽取样式定义层 +
   主题字体 + 骨架 → `template-spec.json`（schema 见 scripts/spec.py；这是唯一契约，
   其他 skill 可直接复用）。**先报能力上限再干活**（capability 声明随 spec 输出）
4. **打样环（probe，最多 2 轮）**：出 1–2 页样片（**与目标格式同通道**，html 冒充 docx
   样片即违规）+ 按 references/style-negotiation.md 的维度议价（md 等无样式格式自动降维，
   只议结构维度）。用户指着改 → 改动回写 spec 并记 `deviated_from`。第 3 轮起按第 2 轮
   定稿并声明「基于第 2 轮样片，未经本轮确认」
5. **render**：按目标格式调度 `scripts/render_docx.py`（clone）/ `render_html.py`（rebuild）/
   `render_md.py`（内容层）。渲染前必须通过：槽数断言（骨架节数 = 内容条数，教训 #3）、
   覆盖确认（目标已存在列文件等确认）。产物写 `./output/`（`.staging/` 中转，验收后移出）
6. **verify**：`python scripts/verify.py <spec> <产物>` 八项判定——schema / 结构命中率≥0.8 /
   样式 diff（规范化语义比较，教训 #5：XML 不得逐字节比）/ 残留零命中 / 槽位完整性 /
   源件哈希未变 / deviated_from 完整 / 样片同通道。通过才交付；未通过写 `.error.md`
   （失败阶段/原因/已完成中间产物/下一步）

## 能力上限（对用户诚实声明，详见 references/capability-matrix.md）

| 源 → 目标 | 能做到 |
|---|---|
| docx→docx / pptx→pptx / html→html | **克隆级**（样式定义层逐项继承） |
| docx→html、html→docx 等 | **样式级**（token 映射，字号±1px、色差可辨） |
| pdf 作源 | **近似**（无样式层，靠视觉反推；一律先声明） |
| md 作源/目标 | 仅**内容层**（无字体色板概念，不承诺样式） |
| 任意源 → md | 内容搬运 + 结构映射 |
| pdf→pptx 要「一模一样」 | `E-FIDELITY-EXCEEDED`：给近似+差异声明，或建议改用 docx/pptx 源 |

## 失败处理

8 个错误码三问齐全（原因/下一步/替代渠道），见 references/error-codes.md 与
scripts/errors.py。原则：fail-with-direction——每个错误都要告诉用户现在怎么办；
完全不可达才拒收（如扫描件），近似可达一律降级交付+声明（用户已拍板策略）。

## 依赖

纯 Python：python-docx（docx 读写）、python-pptx（pptx，缺失时该格式降级）、
lxml（XML 规范化比较）。**安装一律用 `python -m pip install <pkg>`**
（教训 #6：裸 `pip` 可能落到另一个解释器）。缺库时 `E-DEPS-MISSING` 并打印安装命令，
不静默降级。

## 硬边界（不做的事）

- 不修改原件——「把这个文档更新一下」类请求一律分叉到「先另存副本」
- 不做品牌 VI 设计——打样只在 8 维议价清单内受控调整
- 不承诺 md 的样式保真（无字体概念）
- 不在渲染数值上临场发挥——一切来自 spec
- pdf 源不承诺版式级以上保真——物理不可达，先声明再干活
