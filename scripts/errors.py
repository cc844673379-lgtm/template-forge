"""errors.py — 错误码统一出口（教训 #8：三问字段 schema 化，verify 校验错误响应也走 schema）

每个错误必须能回答三问：原因是什么 / agent 下一步做什么 / 有没有替代渠道。
输出结构 conform error.schema.json。
"""

E_CODES = {
    "E-SRC-NOTEXT": {
        "reason": "pdf 无文本层（扫描件或纯图像导出），无法读取内容与字号",
        "next_action": "请提供可复制文本版 pdf，或先 OCR 后再作为模板源",
        "alternative": "仅可做视觉配色参考（人工读图提取色板），不承诺内容与版式",
        "blocked": True,
    },
    "E-SRC-WRITE": {
        "reason": "写操作命中源文件路径，已阻断（GATE-1：源文件只读）",
        "next_action": "改 --out 指向 ./output/ 下的新路径后重跑",
        "alternative": None,  # 安全底线，不给替代
        "blocked": True,
    },
    "E-DEPS-MISSING": {
        "reason": "缺少渲染所需依赖（python-docx / python-pptx / lxml）",
        "next_action": "执行打印出的 python -m pip install 命令后重跑",
        "alternative": "改用已装依赖支持的目标格式（如 md/html）",
        "blocked": True,
    },
    "E-SPEC-SCHEMA": {
        "reason": "template-spec.json 字段缺失或类型错误",
        "next_action": "按提示的缺失字段重跑 extract.py",
        "alternative": "手工补 spec 后用 --spec 直接渲染",
        "blocked": True,
    },
    "E-FIDELITY-EXCEEDED": {
        "reason": "该 源×目标 组合达不到用户所请求的保真级",
        "next_action": "接受降级（随附差异声明）或更换目标格式/源格式",
        "alternative": "同源组合可保克隆级；提供 docx/pptx 原始版本可保样式级以上",
        "blocked": False,  # 拍板策略：近似可达 → 降级交付 + 声明，不拒收
    },
    "E-FONT-MISSING": {
        "reason": "spec 指定字体在本机不存在",
        "next_action": "从替代清单选一个确认（思源黑体→Noto Sans SC/微软雅黑；宋体→SimSun/Noto Serif SC）",
        "alternative": "用系统默认字体并将缺口写进待补清单",
        "blocked": False,
    },
    "E-TEMPLATE-LEFTOVER": {
        "reason": "交付物残留模板语法（{{槽位}} / 内容待补 / 内容缺失）",
        "next_action": "补齐内容或置空后重跑 verify",
        "alternative": "交付时明确标注待补位置（须用户确认）",
        "blocked": True,
    },
    "E-OVERWRITE-DENIED": {
        "reason": "目标文件已存在且未获覆盖确认",
        "next_action": "列出文件等用户确认，或换输出名",
        "alternative": "加 --suffix 自动生成新文件名",
        "blocked": True,
    },
}

REQUIRED_FIELDS = ("error", "reason", "next_action", "alternative", "blocked")


def fail(code: str, **extra) -> dict:
    """返回符合 error.schema.json 的错误对象；exit code 由调用方控制。"""
    if code not in E_CODES:
        raise ValueError(f"未知错误码: {code}")
    obj = {"error": code, **E_CODES[code]}
    obj.update(extra)  # 允许附加上下文（如 missing_fields、fidelity_detail）
    return obj


def is_valid_error(obj: dict) -> bool:
    """verify 用：错误响应是否三问齐全。"""
    return all(f in obj for f in REQUIRED_FIELDS) and obj.get("error") in E_CODES
