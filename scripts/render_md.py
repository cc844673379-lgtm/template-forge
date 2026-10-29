"""render_md.py — 内容层渲染（任意源 → md；md 只做内容层，不承诺样式——铁律）

用法: python render_md.py <spec.json> --content <content.json> [--out out.md]
"""
import sys, os, json, argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from errors import fail
import spec as specmod


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("spec")
    ap.add_argument("--content", required=True)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    s = specmod.load(a.spec)
    content = json.load(open(a.content, encoding="utf-8"))

    lines = [f"# {content['title']}", "",
             "> 样式说明：markdown 无字体/色板概念，本产物仅承载结构与内容"
             "（模板规格保存在 template-spec.json，样式级渲染请用 docx/html 通道）。", ""]
    for sec in content["sections"]:
        lines.append(f"## {sec['heading']}")
        lines.append("")
        for p in sec["paras"]:
            lines.append(p)
            lines.append("")

    out = a.out or os.path.join(s["render"]["output_dir"], "output.md")
    out = os.path.abspath(out)
    if os.path.normcase(out) == os.path.normcase(os.path.abspath(s["source"]["file"])):
        print(json.dumps(fail("E-SRC-WRITE"), ensure_ascii=False))
        sys.exit(2)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    open(out, "w", encoding="utf-8").write("\n".join(lines))
    print(json.dumps({"out": out, "strategy": "content-only",
                      "note": "md 仅内容层（capability.typography 不适用于 md 目标）"},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
