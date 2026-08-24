#!/usr/bin/env python3
"""표현 린터 — 널리 사용하는 표준 표현을 지킵니다.

terms.json 과 방향이 반대입니다.
  terms.json  오독 위험이 있는 제도어를 **풀어쓰게** 합니다 (섬·벽지 → 외딴 지역)
  style.json  널리 쓰는 표준 표현을 **그대로 쓰게** 합니다 (빠집니다 → 제외됩니다)

모순이 아닙니다. 기준은 하나입니다 —
**독자가 고지서와 공단 안내에서 실제로 만나는 말인가.**
'제외'와 '사용'은 만나는 말이고, '섬·벽지'는 만나지만 뜻이 안 통하는 말입니다.

사용:  python3 scripts/lint_style.py <콘텐츠폴더 또는 blog.md>
"""
import sys, json, re, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
ST = json.loads((ROOT / "style.json").read_text(encoding="utf-8"))
REP = ST["교체"]

SKIP = re.compile(r"^\s*(\||!\[|```)")


def check(target):
    p = pathlib.Path(target)
    if p.is_dir():
        files = [p / "blog.md", p / "data.json"]
    else:
        files = [p]
    E = []
    for f in files:
        if not f.exists():
            continue
        for i, ln in enumerate(f.read_text(encoding="utf-8").split("\n"), 1):
            if SKIP.match(ln):
                continue
            for a, b in REP.items():
                if a in ln:
                    E.append(f"{f.name} L{i}: '{a}' → '{b}'")
    return E, []


def main(target):
    E, _ = check(target)
    for e in E:
        print(f"  ✗ {e}")
    if not E:
        print(f"  ✓ 표현 규칙 통과 — 교체 대상 {len(REP)}종 없음")
    return 1 if E else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
