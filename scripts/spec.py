"""spec.py — Template Spec schema 定义与校验（唯一契约）"""
import json

SPEC_VERSION = "2.0"

REQUIRED_TOP = ["spec_version", "spec_id", "source", "capability", "strategy", "extract", "render"]
REQUIRED_SOURCE = ["file", "type", "sha256"]
REQUIRED_EXTRACT = ["paragraph_styles", "skeleton"]
REQUIRED_RENDER = ["target_format", "output_dir", "overwrite_policy"]

CAPABILITY_KEYS = ["skeleton", "typography", "layout", "pixel"]

# 源类型 → 能力上限（与 references/capability-matrix.md 一致）
CAP_BY_SOURCE = {
    "docx":  {"skeleton": True, "typography": True,  "layout": True,  "pixel": False},
    "pptx":  {"skeleton": True, "typography": True,  "layout": True,  "pixel": False},
    "html":  {"skeleton": True, "typography": True,  "layout": True,  "pixel": False},
    "pdf":   {"skeleton": True, "typography": "approx", "layout": "approx", "pixel": False},
    "md":    {"skeleton": True, "typography": False, "layout": False, "pixel": False},
}


def new_spec(src_file: str, src_type: str, sha256: str, strategy: str = "clone-and-fill") -> dict:
    return {
        "spec_version": SPEC_VERSION,
        "spec_id": None,
        "source": {"file": src_file, "type": src_type, "sha256": sha256},
        "capability": dict(CAP_BY_SOURCE[src_type]),
        "strategy": strategy,
        "extract": {"paragraph_styles": {}, "theme_fonts": {}, "skeleton": []},
        "render": {"target_format": None, "output_dir": "./output/",
                   "overwrite_policy": "GATE-1 源只读；覆盖需确认"},
        "probe_skipped": False,
        "deviated_from": [],   # [{field, source_value, new_value, user_words}]
    }


def validate(spec: dict) -> tuple:
    """返回 (ok, missing[])。"""
    missing = []
    for k in REQUIRED_TOP:
        if k not in spec:
            missing.append(k)
    if "source" in spec:
        missing += [f"source.{k}" for k in REQUIRED_SOURCE if k not in spec["source"]]
    if "extract" in spec:
        missing += [f"extract.{k}" for k in REQUIRED_EXTRACT if k not in spec["extract"]]
    if "render" in spec:
        missing += [f"render.{k}" for k in REQUIRED_RENDER if k not in spec["render"]]
    if "capability" in spec:
        missing += [f"capability.{k}" for k in CAPABILITY_KEYS if k not in spec["capability"]]
    # deviated_from 完整性：有偏离记录时每条必须四要素
    for i, d in enumerate(spec.get("deviated_from", [])):
        for f in ("field", "source_value", "new_value", "user_words"):
            if f not in d:
                missing.append(f"deviated_from[{i}].{f}")
    return (len(missing) == 0, missing)


def load(path: str) -> dict:
    return json.load(open(path, encoding="utf-8"))


def save(spec: dict, path: str):
    json.dump(spec, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
