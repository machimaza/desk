#!/usr/bin/env python3
"""브랜드가 한 곳에서만 정해지는지 확인합니다 — 색과 채널 핸들.

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
import json
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


# ── 채널 핸들 ─────────────────────────────────────────────────────────
# 인스타·쓰레드만 @machi_maza 입니다(machimaza 가 이미 있었습니다).
# 이 사실이 세 파일에 흩어져 있었습니다 — publish_youtube.py · docs/index.html · BRAND.md.
# 한 곳만 고치고 나머지를 잊으면, 사람들이 검색해서 못 찾습니다.
# 이제 channels.json 이 유일한 출처이고, 여기서 대조합니다.
CHANNELS = ROOT / "channels.json"
DOCS = ROOT / "docs" / "index.html"


def check_channels():
    bad = []
    if not CHANNELS.exists():
        return ["channels.json 이 없습니다"]
    d = json.loads(CHANNELS.read_text(encoding="utf-8"))

    # 홈페이지에 적힌 주소가 원장과 같은가
    if DOCS.exists():
        html = DOCS.read_text(encoding="utf-8")
        for c in d["채널"]:
            if c["주소"].rstrip("/") not in html.replace("/\"", "\""):
                bad.append(f'docs/index.html 에 {c["이름"]} 주소가 없습니다 — {c["주소"]}')

    # 핸들을 코드에 직접 적어두지 않았는가
    for name in ("motion.py", "pipeline.py", "publish_youtube.py", "publish_threads.py"):
        f = ROOT / "scripts" / name
        if not f.exists():
            continue
        for i, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            if line.lstrip().startswith("#") or "channels.json" in line:
                continue
            for h in ("@machimaza", "@machi_maza", "machimaza.tistory", "blog.naver.com/machimaza"):
                if h in line:
                    bad.append(f"{name}:{i} 에 핸들/주소가 직접 적혀 있습니다 — channels.json 을 쓰세요")
                    break
    return bad


def main():
    if not TOKENS.exists():
        print(f"[실패] {TOKENS} 가 없습니다")
        return 1

    known = {norm(h) for h in HEX.findall(TOKENS.read_text(encoding="utf-8"))}
    known |= {norm(h) for h in ALLOWED}

    bad = []

    # categories.json 의 색도 tokens.css 안에 있어야 합니다.
    # 카테고리를 늘리다 보면 여기에만 색을 추가하고 tokens.css 를 잊습니다 —
    # 그러면 "색의 기준값"이라는 말이 다시 거짓말이 됩니다.
    cats = ROOT / "categories.json"
    if cats.exists():
        cd = json.loads(cats.read_text(encoding="utf-8"))
        for cname, c in (cd.get("카테고리") or {}).items():
            if not isinstance(c, dict):
                continue
            for h in ([c.get("색")] if c.get("색") else []) + (c.get("강조색") or []):
                if norm(h) not in known:
                    bad.append(("categories.json", 0, h, f"카테고리 {cname}"))

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

    ch = check_channels()
    if ch:
        print("[실패] 채널 핸들이 channels.json 과 어긋납니다")
        for m in ch:
            print("  " + m)
        return 1

    n = len(json.loads(CHANNELS.read_text(encoding="utf-8"))["채널"])
    print(f"[통과] 색 {len(known)}개 · 렌더러 {len(RENDERERS)}개 · 채널 {n}개 — 어긋남 없음")
    return 0


if __name__ == "__main__":
    sys.exit(main())
