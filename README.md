# template-forge

把一份参考文档的外观（骨架 + 字体色板 + 版式）提取成可复用的 **Template Spec (JSON)**，
再用它渲染 docx / html / md 新文档。一次提取、多处渲染；渲染数值全部来自 spec，零硬编码。

## 安装

本目录即完整 skill（用户级：`~/.workbuddy/skills/template-forge/`），WorkBuddy 会自动发现。
跨 agent（Codex / Claude Code）：把本目录放入对应 skills 目录即可，无平台依赖。

依赖（Python ≥3.10）：

```
python -m pip install python-docx lxml
```

（注意用 `python -m pip`，避免裸 `pip` 装到别的解释器。）

## 快速验证

```
cd <任意工作目录>
python <skill目录>/scripts/extract.py <参考文档.docx> --out spec.json
python <skill目录>/scripts/render_docx.py spec.json --content <skill目录>/assets/sample-content.json --out out.docx
python <skill目录>/scripts/verify.py spec.json out.docx
```

verify 输出 `PASS` 即链路可用。

## 目录

```
template-forge/
├── SKILL.md                     # 工作流与硬规则（agent 阅读入口）
├── manifest.json
├── scripts/
│   ├── units.py                 # 单位换算公共模块（render/verify 共用，教训 #7）
│   ├── errors.py                # 8 错误码三问齐全（教训 #8）
│   ├── spec.py                  # Template Spec schema（唯一契约，含 deviated_from）
│   ├── extract.py               # docx/md/html 源提取 + pdf 文本层探测
│   ├── probe.py                 # 打样环：目标通道样片
│   ├── render_docx.py           # clone-and-fill（槽数断言，教训 #3）
│   ├── render_html.py           # rebuild（token 全来自 spec）
│   ├── render_md.py             # 内容层（md 无样式，铁律）
│   └── verify.py                # 八项判定（规范化语义比较，教训 #5）
├── references/
│   ├── capability-matrix.md     # 25 组合保真上限（含实证记录）
│   ├── clarify-playbook.md      # 第 0 问 + 四问 + 打样协议
│   ├── style-negotiation.md     # 8 维议价（按格式降维）
│   ├── fidelity.md              # 降级声明模板
│   ├── error-codes.md           # 8 码三问表
│   └── error.schema.json        # 错误响应 schema
└── assets/
    ├── sample-spec.json         # 真实 docx 提取的样例规格
    └── sample-content.json      # 配套样例内容（9 节）
```

## 实证状态（2026-10-29）

- 三链 PASS：docx→docx（克隆，样式层语义一致）、docx→html（token 逐项对上）、→md（内容层）
- 错误码 4/8 实证：E-SRC-NOTEXT / E-FIDELITY-EXCEEDED / E-TEMPLATE-LEFTOVER / E-OVERWRITE-DENIED
- 施工期修复 3 个真 bug：WPS 的 szCs 字号兜底、styleId 数字映射、locals/globals 检查笔误
- 未实证：pptx 渲染器、pdf 目标渲染器（需求出现时立项，见 capability-matrix.md）
