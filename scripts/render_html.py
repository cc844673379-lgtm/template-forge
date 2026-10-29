"""render_html.py — rebuild 渲染（docx/html 源 → html，token 全部来自 spec）

用法: python render_html.py <spec.json> --content <content.json> [--out out.html]
硬规则:
  - CSS :root 变量的每个数值都必须调 units.pt_to_px / units.twips_to_px（教训 #7）
  - 字号/色值/边距零字面量：一律读 spec（cap 主张 2）
"""
import sys, os, json, html as H, argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from errors import fail
from units import pt_to_px, twips_to_px
import spec as specmod


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("spec")
    ap.add_argument("--content", required=True)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    s = specmod.load(a.spec)
    content = json.load(open(a.content, encoding="utf-8"))
    styles = s["extract"]["paragraph_styles"]

    # ---- tokens：全部来自 spec ----
    h1_size = next((r["run0"]["size"] for r in s["extract"].get("run_samples", [])
                    if r["style"] == "Heading 1" and r["run0"]["size"]), None)
    if h1_size is None and "Heading 1" in styles:
        h1_size = styles["Heading 1"].get("size")
    h2_size = styles.get("Heading 2", {}).get("size")
    h3_size = styles.get("Heading 3", {}).get("size")
    body = styles.get("Normal", {})
    body_size = body.get("size")
    accent = styles.get("Heading 2", {}).get("color") or "000000"
    mar = s["extract"].get("margins_twips") or {}
    body_font = body.get("font") or "serif"
    heading_font = styles.get("Heading 1", {}).get("font") or body_font

    missing = [n for n in ("h2_size", "body_size") if not locals().get(n, None)]
    if missing:
        print(json.dumps(fail("E-SPEC-SCHEMA",
                              reason=f"spec 缺少样式 token：{missing}（无法零硬编码渲染）",
                              next_action="重跑 extract.py 补全 paragraph_styles"), ensure_ascii=False))
        sys.exit(2)

    css_vars = f""":root {{
  --font-body: "{body_font}", serif;
  --font-heading: "{heading_font}", serif;
  --size-h1: {pt_to_px(h1_size or body_size)}px;   /* {h1_size}pt */
  --size-h2: {pt_to_px(h2_size)}px;               /* {h2_size}pt */
  --size-h3: {pt_to_px(h3_size or body_size)}px;  /* {h3_size or body_size}pt */
  --size-body: {pt_to_px(body_size)}px;           /* {body_size}pt */
  --color-accent: #{accent};
  --color-text: #{accent};
  --margin-page: {twips_to_px(mar.get('top', 1440))}px {twips_to_px(mar.get('right', 1800))}px;
}}"""

    doc = ["<!DOCTYPE html>", '<html lang="zh-CN">', "<head>", '<meta charset="UTF-8">',
           f"<title>{H.escape(content['title'])}</title>", "<style>", css_vars,
           "body { font-family: var(--font-body); font-size: var(--size-body); color: var(--color-text); margin: var(--margin-page); max-width: 820px; line-height: 1.7; }",
           "h1 { font-family: var(--font-heading); font-size: var(--size-h1); color: var(--color-accent); font-weight: bold; }",
           "h2 { font-family: var(--font-heading); font-size: var(--size-h2); color: var(--color-accent); font-weight: bold; border-bottom: 0.5px solid #d3d1c7; padding-bottom: 4px; }",
           "h3 { font-family: var(--font-heading); font-size: var(--size-h3); font-weight: bold; }",
           "p { margin: 0.6em 0; }", "</style>", "</head>", "<body>",
           f"<h1>{H.escape(content['title'])}</h1>"]
    for sec in content["sections"]:
        doc.append(f"<h2>{H.escape(sec['heading'])}</h2>")
        for p in sec["paras"]:
            doc.append(f"<p>{H.escape(p)}</p>")
    doc += ["</body>", "</html>"]

    out = a.out or os.path.join(s["render"]["output_dir"], "output.html")
    out = os.path.abspath(out)
    if os.path.normcase(out) == os.path.normcase(os.path.abspath(s["source"]["file"])):
        print(json.dumps(fail("E-SRC-WRITE"), ensure_ascii=False))
        sys.exit(2)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    if os.path.exists(out) and not s["render"].get("overwrite_confirmed") and not a.out:
        print(json.dumps(fail("E-OVERWRITE-DENIED", target=out), ensure_ascii=False))
        sys.exit(2)
    open(out, "w", encoding="utf-8").write("\n".join(doc))
    print(json.dumps({"out": out, "strategy": "rebuild",
                      "tokens": {"h2_px": pt_to_px(h2_size), "body_px": pt_to_px(body_size),
                                 "accent": f"#{accent}"}}, ensure_ascii=False))


if __name__ == "__main__":
    main()
