#!/usr/bin/env python3
"""렌더러가 브랜드 색을 제멋대로 쓰지 않는지 확인합니다.

왜 필요한가
  `brand/tokens.css` 는 "색의 단일 소스"라고 적혀 있었지만 실제로는
  아무도 읽지 않았습니다. `motion.py` 와 `pipeline.py` 가 같은 값을
  각자 적어 갖고 있었을 뿐입니다. 한쪽만 고치면 카드와 영상의 색이
  갈라지고, 그건 눈으로만 잡히는 종류의 어긋남입니다.

  렌더러를 CSS 를 읽도록 고치는 것이 정공법이지만, 두 렌더러 모두
  HTML 을 문자열로 조립하고 있어 손대는 범위가 큽니다. 대신
  **어긋나면 CI 가 멈추게** 했습니다. 값이 하나뿐이라는 약속은
  파일이 아니라 이 테스트가 지킵니다.

  새 색을 쓰고 싶으면 `brand/tokens.css` 에 먼저 넣으세요.

사용:  python3 scripts/test_brand.py
"""
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
TOKENS = ROOT / "brand" / "tokens.css"
RENDERERS = ["motion.py", "pipeline.py", "make_images.py"]

# 색이 아닌 것들. 흑백과 투명은 토큰에 둘 이유가 없습니다.
ALLOWED = {"#fff", "#ffffff", "#000", "#000000"}

HEX = re.compile(r"#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3}\b")


def norm(h):
    h = h.lower()
    if len(h) == 4:                      # #abc → #aabbcc
        h = "#" + "".join(c * 2 for c in h[1:])
    return h


def main():
    if not TOKENS.exists():
        print(f"[실패] {TOKENS} 가 없습니다")
        return 1

    known = {norm(h) for h in HEX.findall(TOKENS.read_text(encoding="utf-8"))}
    known |= {norm(h) for h in ALLOWED}

    bad = []
    for name in RENDERERS:
        f = ROOT / "scripts" / name
        if not f.exists():
            continue
        for i, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            for h in HEX.findall(line):
                if norm(h) not in known:
                    bad.append((name, i, h, line.strip()[:70]))

    if bad:
        print("[실패] brand/tokens.css 에 없는 색이 렌더러에 있습니다")
        for name, i, h, line in bad:
            print(f"  {name}:{i}  {h}   {line}")
        print("\n  → 이 색을 계속 쓰려면 brand/tokens.css 에 먼저 넣으세요.")
        return 1

    print(f"[통과] 색 {len(known)}개 · 렌더러 {len(RENDERERS)}개 — 어긋남 없음")
    return 0


if __name__ == "__main__":
    sys.exit(main())
