"""render_docx.py — clone-and-fill 渲染（docx→docx 克隆保真）

用法: python render_docx.py <spec.json> --content <content.json> [--out out.docx]
content.json: {"title": str, "sections": [{"heading": str, "paras": [str]}]}
硬规则:
  - 槽数断言（教训 #3）: spec 骨架 H 节数 == sections 条数，不等即 E-TEMPLATE-LEFTOVER 前置拦截
  - GATE-1: 产物绝不写源路径；写命中源文件即 E-SRC-WRITE
  - 数值全部来自 spec：字体/字号读 extract.paragraph_styles 与 run_samples（本函数不出现字号字面量）
"""
import sys, os, json, shutil, argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from errors import fail
import spec as specmod


def clear_runs(p):
    for r in list(p.runs):
        r._element.getparent().remove(r._element)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("spec")
    ap.add_argument("--content", required=True)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    s = specmod.load(a.spec)
    content = json.load(open(a.content, encoding="utf-8"))

    src = s["source"]["file"]
    headings = [n for n in s["extract"]["skeleton"] if n["type"] == "heading"]
    # H2 槽 = 骨架里 level==2 的节点数（docx clone 场景）
    slots = [n for n in headings if n.get("level") == 2]

    # ---- 槽数断言（教训 #3）----
    if len(slots) != len(content["sections"]):
        print(json.dumps(fail(
            "E-TEMPLATE-LEFTOVER",
            reason=f"骨架 H2 槽数({len(slots)}) != 内容条数({len(content['sections'])})——填充必然产生占位残留",
            next_action="增删 content.sections 使条数与骨架一致后重跑",
            fidelity_detail={"slots": len(slots), "sections": len(content["sections"]),
                             "slot_texts": [x["text"] for x in slots][:12]}), ensure_ascii=False))
        sys.exit(2)

    # ---- 输出路径与 GATE ----
    out = a.out or os.path.join(s["render"]["output_dir"], "output.docx")
    out = os.path.abspath(out)
    src_abs = os.path.abspath(src)
    if os.path.normcase(out) == os.path.normcase(src_abs):
        print(json.dumps(fail("E-SRC-WRITE"), ensure_ascii=False))
        sys.exit(2)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    if os.path.exists(out) and not s["render"].get("overwrite_confirmed"):
        print(json.dumps(fail("E-OVERWRITE-DENIED", target=out,
                              next_action=f"确认覆盖 {os.path.basename(out)}（spec.render.overwrite_confirmed=true）或加 --out 新路径"), ensure_ascii=False))
        sys.exit(2)

    # ---- clone: 复制底稿 → 只换内容 ----
    shutil.copyfile(src, out)
    import docx as pydocx
    from docx.shared import Pt
    d = pydocx.Document(out)

    # 数值全部来自 spec：标题字号取 run_samples[0]（H1 直接格式）；正文口径取样式层 Normal 或样本
    h1_size = None
    for r in s["extract"].get("run_samples", []):
        if r["style"] == "Heading 1" and r["run0"]["size"]:
            h1_size = r["run0"]["size"]
            break
    body_style = s["extract"]["paragraph_styles"].get("Normal", {})
    body_font = body_style.get("font") or "宋体"  # fallback 也来自 spec 样式层实测（run_samples 主字体）
    for r in s["extract"].get("run_samples", []):
        if r["style"] == "Normal" and r["run0"]["font"]:
            body_font = r["run0"]["font"]
            break
    body_size = body_style.get("size")

    paras = d.paragraphs
    h1 = [p for p in paras if p.style.name == "Heading 1"]
    if h1 and content.get("title"):
        clear_runs(h1[0])
        run = h1[0].add_run(content["title"])
        if h1_size:
            run.font.size = Pt(h1_size)

    h2_idx = [i for i, p in enumerate(paras) if p.style.name == "Heading 2"]
    assert len(h2_idx) == len(slots)  # spec 骨架与底稿一致性（extract 保证）

    def fill_body(anchor_par, lines):
        first = True
        for ln in lines:
            if first:
                clear_runs(anchor_par)
                anchor_par.add_run(ln)
                first = False
            else:
                np = anchor_par.insert_paragraph_before("")
                np.style = anchor_par.style
                r = np.add_run(ln)
                r.font.name = body_font
                if body_size:
                    r.font.size = Pt(body_size)

    for k, h2i in enumerate(h2_idx):
        clear_runs(paras[h2i])
        paras[h2i].add_run(content["sections"][k]["heading"])
        for j in range(h2i + 1, len(paras)):
            pj = paras[j]
            if pj.style.name.startswith("Heading"):
                break
            if pj.style.name == "Normal" and pj.text.strip():
                fill_body(pj, content["sections"][k]["paras"])
                break

    d.save(out)
    print(json.dumps({"out": out, "strategy": "clone-and-fill",
                      "slots": len(slots), "overwritten": os.path.exists(out)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
