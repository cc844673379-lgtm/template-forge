"""extract.py — 从参考文档提取 Template Spec（docx / md / html / pdf 文本层探测）

用法:
  python extract.py <src> [--out spec.json] [--probe-only]
行为:
  --probe-only : 只判文本层/可读性，不写 spec（pdf 源第一步必跑）
  docx  : 样式定义层 + 主题字体 + 骨架（python-docx）
  md    : 仅结构层（标题层级 / 列表 / 表格计数）——md 无样式概念（铁律）
  html  : CSS 变量/类抽取 + 结构
  pdf   : 无文本层 → E-SRC-NOTEXT（fail）；有文本层 → 近似能力声明 + 内容层骨架
"""
import sys, os, json, hashlib, re, argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import spec as specmod
from errors import fail

READABLE = {"docx", "md", "html", "htm"}


def sha256_of(path: str) -> str:
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def probe_pdf_text(path: str) -> bool:
    """粗判 pdf 是否含文本层：PDF 内容流出现文本算子。"""
    raw = open(path, "rb").read()
    return (b"Tj" in raw) or (b"TJ" in raw) or (b"BT" in raw and b"ET" in raw)


def extract_docx(path: str) -> dict:
    import docx as pydocx  # E-DEPS-MISSING 由 main 捕获
    import zipfile
    d = pydocx.Document(path)
    # 先从 styles.xml 建 styleId→sz 半点映射——python-docx 的 styles API 读不到
    # 部分样式的直接 rPr（如本文档 heading 的 sz），必须 XML 兜底。
    # 注意：WPS 等工具的 styleId 可能是纯数字、w:name 是小写 "heading 1"，
    # 与 python-docx 显示名（"Heading 2"）存在错位——所以按 style_id 对齐，不按 name。
    z0 = zipfile.ZipFile(path)
    sx = z0.read("word/styles.xml").decode("utf-8", "ignore")
    xml_sz_by_id = {}
    for m in re.finditer(r'<w:style\s[^>]*w:styleId="([^"]*)"[^>]*>(.*?)</w:style>', sx, re.S):
        blk = m.group(2)
        szs = re.findall(r'<w:sz w:val="(\d+)"', blk)
        if not szs:
            szs = re.findall(r'<w:szCs w:val="(\d+)"', blk)  # WPS 导出常把尺寸写进 szCs（实测：本文档 Heading 2）
        if szs:
            xml_sz_by_id[m.group(1)] = int(szs[-1]) / 2.0  # 半点 → pt
    styles = {}
    for st in d.styles:
        try:
            if st.type == 1:
                f = st.font
                size = f.size.pt if f.size else None
                if size is None:
                    sid = getattr(st, "style_id", None)
                    if sid in xml_sz_by_id:
                        size = xml_sz_by_id[sid]  # XML 兜底：API 与 XML 双源合流
                styles[st.name] = {
                    "font": f.name, "size": size,
                    "bold": f.bold,
                    "color": str(f.color.rgb) if (f.color and f.color.rgb) else None,
                }
        except Exception:
            pass
    theme_fonts = {}
    try:
        z = zipfile.ZipFile(path)
        theme = z.read("word/theme/theme1.xml").decode("utf-8", "ignore")
        def g(p):
            m = re.search(p, theme)
            return m.group(1) if m else None
        theme_fonts = {
            "major_latin": g(r'<a:majorFont><a:latin typeface="([^"]*)"'),
            "minor_latin": g(r'<a:minorFont><a:latin typeface="([^"]*)"'),
            "major_ea": g(r'<a:majorFont>.*?<a:ea typeface="([^"]*)"'),
            "minor_ea": g(r'<a:minorFont>.*?<a:ea typeface="([^"]*"'),
        }
    except Exception:
        pass
    # 骨架：标题层级序列 + 段落样式分布
    skeleton = []
    for i, p in enumerate(d.paragraphs):
        name = p.style.name if p.style else ""
        if name.startswith("Heading"):
            level = name.split()[-1]
            skeleton.append({"i": i, "type": "heading", "level": int(level), "text": p.text[:60]})
        elif p.text.strip() and (not skeleton or skeleton[-1]["type"] != "para"):
            skeleton.append({"i": i, "type": "para"})
    # 页边距（layout token）
    import zipfile as zf
    docxml = zf.ZipFile(path).read("word/document.xml").decode("utf-8", "ignore")
    mar = re.search(r'<w:pgMar[^/]*/>', docxml)
    margins = None
    if mar:
        v = dict(re.findall(r'w:(top|right|bottom|left)="(\d+)"', mar.group(0)))
        margins = {k: int(x) for k, x in v.items()}
    # 直接格式抽样（run 级 override 检测）
    samples = []
    for i, p in enumerate(d.paragraphs[:80]):
        if not p.text.strip() or not p.runs:
            continue
        r0 = p.runs[0]
        samples.append({"i": i, "style": p.style.name if p.style else None,
                        "run0": {"font": r0.font.name,
                                 "size": r0.font.size.pt if r0.font.size else None,
                                 "bold": r0.font.bold,
                                 "color": str(r0.font.color.rgb) if (r0.font.color and r0.font.color.rgb) else None}})
        if len(samples) >= 20:
            break
    return {"paragraph_styles": styles, "theme_fonts": theme_fonts,
            "skeleton": skeleton, "margins_twips": margins, "run_samples": samples}


def extract_md(path: str) -> dict:
    skeleton = []
    for i, ln in enumerate(open(path, encoding="utf-8")):
        m = re.match(r"^(#{1,6})\s+(.*)", ln)
        if m:
            skeleton.append({"i": i, "type": "heading", "level": len(m.group(1)),
                             "text": m.group(2).strip()[:60]})
    n_tables = sum(1 for ln in open(path, encoding="utf-8") if ln.strip().startswith("|"))
    return {"paragraph_styles": {"__note__": "md 无样式定义层（capability.typography=false）"},
            "skeleton": skeleton, "table_lines": n_tables}


def extract_html(path: str) -> dict:
    h = open(path, encoding="utf-8", errors="ignore").read()
    css_vars = dict(re.findall(r"(--[\w-]+)\s*:\s*([^;]+);", h))
    skeleton = [{"type": "heading", "level": len(m.group(1)), "text": re.sub(r"<[^>]+>", "", m.group(2)).strip()[:60]}
                for m in re.finditer(r"<(h[1-6])[^>]*>(.*?)</\1>", h, re.S)
                for m in [re.match(r"(h[1-6])", m.group(1)) and m]][:0]  # placeholder
    # 简化：直接数 h1-h6
    skeleton = []
    for m in re.finditer(r"<h([1-6])[^>]*>(.*?)</h\1>", h, re.S):
        skeleton.append({"type": "heading", "level": int(m.group(1)),
                         "text": re.sub(r"<[^>]+>", "", m.group(2)).strip()[:60]})
    return {"paragraph_styles": {"css_vars": css_vars},
            "skeleton": skeleton}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("--out", default=None)
    ap.add_argument("--probe-only", action="store_true")
    a = ap.parse_args()

    src = a.src
    ext = os.path.splitext(src)[1].lower().lstrip(".")
    sha = sha256_of(src)

    if a.probe_only:
        if ext == "pdf" and not probe_pdf_text(src):
            print(json.dumps(fail("E-SRC-NOTEXT"), ensure_ascii=False))
            sys.exit(2)
        print(json.dumps({"readable": True, "type": ext, "sha256": sha}, ensure_ascii=False))
        return

    if ext == "pdf":
        if not probe_pdf_text(src):
            print(json.dumps(fail("E-SRC-NOTEXT"), ensure_ascii=False))
            sys.exit(2)
        s = specmod.new_spec(src, "pdf", sha, strategy="rebuild")
        s["capability"]["note"] = "pdf 无样式定义层：字号色值为视觉反推近似，一律声明"
        s["extract"] = extract_md.__wrapped__ if False else s["extract"]  # pdf 内容层走 md 简化：占位
        # pdf 文本内容层骨架：留待 pypdf 可用时扩展；当前以近似声明 + 人工确认为主
        s["extract"]["skeleton"] = []
    else:
        if ext not in READABLE:
            print(json.dumps(fail("E-DEPS-MISSING",
                                  reason=f"不支持的源格式 .{ext}（支持 docx/md/html/pdf）",
                                  next_action="转换为 docx 或 html 后重试"), ensure_ascii=False))
            sys.exit(2)
        s = specmod.new_spec(src, "html" if ext == "htm" else ext, sha,
                             strategy="clone-and-fill" if ext in ("docx", "pptx", "html") else "rebuild")
        if ext == "docx":
            s["extract"] = extract_docx(src)
        elif ext == "md":
            s["extract"] = extract_md(src)
        else:
            s["extract"] = extract_html(src)

    ok, missing = specmod.validate(s)
    if not ok:
        print(json.dumps(fail("E-SPEC-SCHEMA", missing_fields=missing), ensure_ascii=False))
        sys.exit(2)

    out = a.out or os.path.join("./output", "template-spec.json")
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    specmod.save(s, out)
    cap = s["capability"]
    print(json.dumps({"spec": out, "sha256": sha[:16] + "...",
                      "capability": {k: cap[k] for k in ("skeleton", "typography", "layout", "pixel")},
                      "skeleton_nodes": len(s["extract"]["skeleton"]),
                      "note": cap.get("note")}, ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except ImportError as e:
        print(json.dumps(fail("E-DEPS-MISSING",
                              reason=f"缺少依赖：{e}",
                              next_action=f"python -m pip install python-docx lxml"), ensure_ascii=False))
        sys.exit(2)
