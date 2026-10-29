# 错误码手册（8 码 · 三问齐全）

> 每个 error 输出必须符合 `error.schema.json`（字段：error / reason / next_action / alternative / blocked）。
> 原则 fail-with-direction：用户看完知道**现在怎么办**。`blocked:false` = 降级可继续（必须附声明）。

| 码 | 触发场景 | 原因 | 下一步 | 替代 | blocked | 实证 |
|---|---|---|---|---|---|---|
| `E-SRC-NOTEXT` | pdf 源无文本层（扫描件/纯图导出） | 无法读取内容与字号 | 提供可复制文本版 / 先 OCR | 仅视觉配色参考（人工读图） | true | ✅ S4（2026-10-29） |
| `E-SRC-WRITE` | 写路径命中源文件（GATE-1） | 源文件只读 | 改 `--out` 到 ./output/ | 无（安全底线） | true | — |
| `E-DEPS-MISSING` | 缺 python-docx/pptx/lxml | 依赖未装（注意：**安装必须 `python -m pip`**——裸 pip 可能落到别的解释器） | 执行打印出的安装命令 | 换已装依赖支持的格式 | true | ✅ 环境实证（pip 错位，教训 #6） |
| `E-SPEC-SCHEMA` | spec 缺字段/类型错 | 契约不完整无法渲染 | 按缺失字段重跑 extract | 手工补 spec 后 --spec 直渲 | true | — |
| `E-FIDELITY-EXCEEDED` | 源×目标达不到请求保真级（如 pdf→pptx 要"一模一样"） | 物理上限：无样式源跨源只能近似 | 接受降级（附差异声明）或换源/目标 | 同源可克隆；给 docx/pptx 原版可样式级 | **false**（拍板：近似可达→降级交付+声明） | ✅ S5 |
| `E-FONT-MISSING` | spec 字体本机不存在 | 环境缺字体 | 替代清单确认（思源黑体→Noto Sans SC/微软雅黑；宋体→SimSun/Noto Serif SC） | 系统默认+写待补清单 | false | — |
| `E-TEMPLATE-LEFTOVER` | 交付物残留 `{{}}`/内容待补/内容缺失 | 填充不全（含槽数≠条数前置拦截，教训 #3） | 补齐内容置空重跑 | 标注待补位置（须用户确认） | true | ✅ S2 首轮（2026-10-29） |
| `E-OVERWRITE-DENIED` | 目标已存在未确认 | 防不可逆覆盖 | 列文件等确认 / 换名 | `--suffix` 自动新名 | true | — |

## 使用约定（scripts/errors.py）

```python
from errors import fail, is_valid_error
print(json.dumps(fail("E-SRC-NOTEXT"), ensure_ascii=False))   # 三问字段自动带齐
assert is_valid_error(obj)                                     # verify 校验错误响应也走 schema
```

额外上下文用 kwargs 附加（如 `missing_fields=[...]`、`fidelity_detail={...}`），schema 允许 additionalProperties。
