"""units.py — 单位换算公共模块（教训 #7：render 与 verify 必须 import 同一份，禁止各自实现）"""

TWIPS_PER_INCH = 1440
PX_PER_INCH = 96          # CSS 基准 96dpi
PT_PER_INCH = 72


def twips_to_px(twips: int) -> int:
    """docx 页边距 twips → CSS px（1440 twips = 96px）"""
    return round(twips / TWIPS_PER_INCH * PX_PER_INCH)


def pt_to_px(pt: float) -> int:
    """pt → CSS px（1pt = 4/3 px）。render 写入与 verify 期望都必须调用本函数。"""
    return round(pt * PX_PER_INCH / PT_PER_INCH)


def half_points_to_pt(hp: int) -> float:
    """docx w:sz 半点 → pt"""
    return hp / 2.0


def emu_to_px(emu: int) -> int:
    """pptx EMU → px（914400 EMU = 1in）"""
    return round(emu / 914400 * PX_PER_INCH)
