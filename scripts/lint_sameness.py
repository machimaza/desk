#!/usr/bin/env python3
"""반복 패턴 검사 — 글이 서로 닮아가는 것을 막습니다.

왜 필요한가
  첫 글과 두 번째 글을 나란히 놓고 보니 거의 같은 물건이었습니다.
  layout·video_structure 가 같고, flow 장면 순서가 같고,
  '3줄 요약'으로 열어 '정리하면'으로 닫는 것까지 같았습니다.

  원인은 제가 템플릿을 하나만 만든 것입니다. CLAUDE.md 3장은
  '레이아웃 3종 로테이션 — 통일성 제거'를, 9장은 '구조 3종 로테이션'을
  요구하는데, 템플릿이 그걸 어기도록 되어 있었습니다.

  같은 틀이 반복되면 두 가지가 나빠집니다.
   ① 플랫폼이 '고정된 패턴 반복'으로 읽습니다 (틱톡 unoriginal · 유튜브 채널 패턴)
   ② 독자가 두 번째 글에서 새로움을 못 느낍니다

검사 항목 (기존 글들과 비교)
  1. layout 이 직전 글과 같은가
  2. flow 장면 순서가 기존 글과 완전히 같은가
  3. 여는 장치 / 닫는 장치가 3편 연속 같은가
  4. 문장 재사용 (8글자 연속) 비율 — 목표 4% 미만.
     3%로 잡았더니 필수 문구만으로 초과했습니다. 신뢰 문구를 빼는 건 손해입니다.

사용:  python3 scripts/lint_sameness.py <콘텐츠폴더>
"""
import sys, json, re, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
CONTENT = ROOT / "content"

# 매번 같아야 하는 것 — 신뢰의 근거이므로 검사에서 뺍니다.
EXEMPT = ["공식 출처 및 확인 링크", "이 글은 일반적인 정보", "— 마치마자",
          "문의: 국민건강보험공단", "자주 묻는 질문",
          "이 글의 모든 수치는 아래 원문에서 직접 확인했습니다",
          "정부·공공기관 원문을 직접 확인해 정리하며, 제도 개정 시 갱신합니다",
          "개인의 상태에 따라 다를 수 있습니다"]

OPENERS = {"3줄 요약": r"> \*\*3줄 요약\*\*", "요약 상자": r"> \*\*요약",
           "질문 던지기": r"^.{0,40}\?\s*$", "숫자 먼저": r"^\*\*[\d가-힣 ]*[\d,]+원"}
CLOSERS = {"정리하면": r"\*\*정리하면\*\*", "한 문장": r"\*\*결론\*\*", "체크리스트": r"^- \[ \]"}


def load_all(exclude=None):
    out = []
    for p in sorted(CONTENT.iterdir()):
        if not p.is_dir() or p.name.startswith("_") or p.resolve() == exclude:
            continue
        if not (p / "data.json").exists() or not (p / "blog.md").exists():
            continue
        out.append((p, json.loads((p / "data.json").read_text(encoding="utf-8")),
                    (p / "blog.md").read_text(encoding="utf-8")))
    return out


def device(txt, table):
    for name, pat in table.items():
        if re.search(pat, txt, re.M):
            return name
    return "없음"


def ngrams(t, n=8):
    t = re.sub(r"\s+", "", re.sub(r"[#*|>\[\]()\-]", "", t))
    for e in EXEMPT:
        t = t.replace(re.sub(r"\s+", "", e), "")
    return {t[i:i+n] for i in range(len(t) - n)}


def check(base):
    base = pathlib.Path(base).resolve()
    d = json.loads((base / "data.json").read_text(encoding="utf-8"))
    txt = (base / "blog.md").read_text(encoding="utf-8")
    others = load_all(exclude=base)
    E, W = [], []
    if not others:
        return E, W        # 첫 글은 비교 대상이 없습니다

    seq = [s["type"] for s in d.get("flow", {}).get("scenes", [])]
    lay = d["meta"].get("layout")
    op, cl = device(txt, OPENERS), device(txt, CLOSERS)

    for p, od, otxt in others:
        if seq and seq == [s["type"] for s in od.get("flow", {}).get("scenes", [])]:
            E.append(f"flow 장면 순서가 '{p.name}' 와 완전히 같습니다 "
                     f"({' → '.join(seq)}) — 순서나 장면 유형을 바꾸세요")
        ov = ngrams(txt) & ngrams(otxt)
        base_n = min(len(ngrams(txt)), len(ngrams(otxt)))
        if base_n and len(ov) / base_n > 0.04:
            W.append(f"'{p.name}' 와 문장 재사용 {len(ov)/base_n*100:.1f}% "
                     f"(목표 4% 미만 — 출처·고지·서명은 계산에서 제외됨)")

    lays = [od["meta"].get("layout") for _, od, _ in others] + [lay]
    if len(lays) >= 3 and len(set(lays[-3:])) == 1:
        E.append(f"layout '{lay}' 이 3편 연속입니다 — CLAUDE.md 3장은 3종 로테이션을 요구합니다")
    elif others and others[-1][1]["meta"].get("layout") == lay:
        W.append(f"layout 이 직전 글('{others[-1][0].name}')과 같습니다 — '{lay}'")

    ops = [device(o, OPENERS) for _, _, o in others] + [op]
    cls_ = [device(o, CLOSERS) for _, _, o in others] + [cl]
    if len(ops) >= 3 and len(set(ops[-3:])) == 1 and op != "없음":
        E.append(f"여는 장치 '{op}' 가 3편 연속입니다")
    if len(cls_) >= 3 and len(set(cls_[-3:])) == 1 and cl != "없음":
        E.append(f"닫는 장치 '{cl}' 가 3편 연속입니다")
    return E, W


def main(base):
    E, W = check(base)
    for w in W:
        print(f"  ⚠ {w}")
    for e in E:
        print(f"  ✗ {e}")
    if not E and not W:
        print("  ✓ 반복 패턴 없음 — 기존 글과 충분히 다릅니다")
    return 1 if E else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
