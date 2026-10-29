"""probe.py — 打样环：出 1–2 页目标通道样片（与成品同渲染通道，硬约束）

用法: python probe.py <spec.json> --content <content.json> --format docx|html [--out 样片路径]
行为: 取 content 的前 1–2 节渲染样片；轮次与 deviated_from 由 SKILL.md 工作流管理（至多 2 轮）。
"""
import sys, os, json, argparse, subprocess

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from errors import fail

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("spec")
    ap.add_argument("--content", required=True)
    ap.add_argument("--format", choices=["docx", "html", "md"], required=True)
    ap.add_argument("--sections", type=int, default=2, help="样片取前 N 节（默认 2）")
    a = ap.parse_args()

    content = json.load(open(a.content, encoding="utf-8"))
    probe_content = {"title": content["title"],
                     "sections": content["sections"][:a.sections]}
    if not probe_content["sections"]:
        print(json.dumps(fail("E-SPEC-SCHEMA",
                              reason="content.sections 为空，无法打样",
                              next_action="至少提供 1 节内容用于样片"), ensure_ascii=False))
        sys.exit(2)
    probe_path = a.content + ".probe.json"
    json.dump(probe_content, open(probe_path, "w", encoding="utf-8"), ensure_ascii=False)

    renderer = {"docx": "render_docx.py", "html": "render_html.py", "md": "render_md.py"}[a.format]
    out = os.path.join(os.path.dirname(a.spec) or ".", f"probe-sample.{a.format}")
    res = subprocess.run([sys.executable, os.path.join(HERE, renderer),
                          a.spec, "--content", probe_path, "--out", out],
                         capture_output=True, text=True)
    os.remove(probe_path)
    print(res.stdout.strip())
    if res.returncode != 0:
        print(res.stderr.strip())
        sys.exit(res.returncode)
    print(json.dumps({"probe_sample": out, "channel": a.format,
                      "note": "样片与成品同通道；确认后进入全量渲染；改动回写 spec.deviated_from"},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
