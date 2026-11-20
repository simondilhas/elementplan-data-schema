"""Compile rule YAML to plain W3C SHACL Turtle via pattern templates.

    python scripts/generate_shacl.py
    python scripts/generate_shacl.py examples/rules/fr-wh-01-tragende-treppenhauswaende.yaml

Writes shacl/generated/<slug>.ttl for every rule that names a pattern. Rules
with a hand-written shacl path are copied as-is when the path exists under
shacl/.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape

ROOT = Path(__file__).resolve().parent.parent
RULES = ROOT / "examples" / "rules"
PATTERNS = ROOT / "shacl" / "patterns"
OUT = ROOT / "shacl" / "generated"


def slug(rule_id: str) -> str:
    return rule_id.rsplit("/", 1)[-1]


def load_pattern(pattern_id: str) -> dict:
    meta = PATTERNS / f"{pattern_id}.json"
    if not meta.exists():
        raise SystemExit(f"unknown pattern {pattern_id!r} (missing {meta})")
    return yaml.safe_load(meta.read_text(encoding="utf-8"))


def render(rule: dict) -> str:
    pattern_id = rule.get("pattern")
    if not pattern_id:
        raise SystemExit(f"{rule['id']}: no pattern (use shacl escape hatch instead)")
    meta = load_pattern(pattern_id)
    env = Environment(
        loader=FileSystemLoader(str(PATTERNS)),
        autoescape=select_autoescape(enabled_extensions=()),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    template = env.get_template(meta["template"])
    return template.render(rule=rule, rule_slug=slug(rule["id"]))


def write_rule(path: Path) -> Path:
    rule = yaml.safe_load(path.read_text(encoding="utf-8"))
    out = OUT / f"{slug(rule['id'])}.ttl"
    OUT.mkdir(parents=True, exist_ok=True)
    if rule.get("shacl") and not rule.get("pattern"):
        src = ROOT / rule["shacl"]
        if not src.exists():
            raise SystemExit(f"{rule['id']}: shacl file {src} not found")
        shutil.copy(src, out)
    else:
        out.write_text(render(rule), encoding="utf-8")
    return out


def main(argv: list[str]) -> int:
    paths = [Path(a) for a in argv] if argv else sorted(RULES.glob("*.yaml"))
    if not paths:
        print("no rule files found")
        return 1
    for path in paths:
        out = write_rule(path)
        print(f"wrote {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
