"""용어 린터 회귀 테스트.

린터가 살아 있는지 매번 확인합니다. 검사기가 조용히 고장 나면
'통과'는 계속 뜨지만 실제로는 아무것도 안 걸러집니다 —
'섬·벽지'가 게이트를 통과했던 것과 같은 상황이 반복됩니다.
"""
import sys, json, pathlib, tempfile, shutil, importlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
REAL = ROOT / "content" / "2026-08-24-퇴직후-건강보험료"

CASES = [
    ("뜻풀이 없는 '섬·벽지'",
     [("섬·벽지(외딴 지역) 거주 | 50% | 벽지는 도배지가 아니라 僻地, 도시에서 멀고 교통이 불편한 지역입니다. 지정 지역 목록이 따로 있으므로 주소지로 공단에 확인",
       "섬·벽지 거주 | 50% | 공단에 확인"),
      ("- **깎아주는 대상인지**: 지역가입자는 농어촌 22%, 섬·벽지 50%",
       "- **깎아주는 대상인지**: 지역가입자는 농어촌 22%, 섬벽지 50%")],
     "섬·벽지"),
    ("뜻풀이 없는 '통산'",
     [('핵심은 **"통산"** 입니다. 通算, 즉 **여러 회사를 다녔더라도 기간을 합쳐서 센다**는 뜻입니다.',
       '핵심은 **"통산"** 입니다.'),
      ("| A사 8개월 → 공백 2개월 → B사 7개월 후 퇴직 | ✅ 합쳐서 15개월 |",
       "| A사 8개월 → 공백 2개월 → B사 7개월 후 퇴직 | ✅ 통산 15개월 |"),
      ("합쳐서(통산) 1년 이상", "통산 1년 이상"),
      ("이직을 반복했더라도 **최종 퇴직일 기준 이전 18개월 안에서 합산해 1년 이상이면**",
       "이직을 반복했더라도 **최종 퇴직일 기준 이전 18개월 안에서 1년 이상이면**")],
     "통산"),
    ("뜻풀이 없는 '세대'",
     [("| 부과 단위 | 개인 | **세대 합산** — 주민등록상 함께 묶인 가구 |",
       "| 부과 단위 | 개인 | **세대 합산** |"),
      ("표의 **세대**는 世代(젊은 세대)가 아닙니다. 지역보험료는 개인이 아니라 이 가구 단위로 합산되므로, ",
       "")],
     "세대"),
]


def run():
    import lint_terms
    fails = []

    e, _ = lint_terms.check(REAL)
    if e:
        fails.append(f"정상 원고에서 오탐 {len(e)}건: {e[0]}")
    else:
        print("  ✓ 정상 원고 통과 (오탐 없음)")

    for name, subs, expect in CASES:
        with tempfile.TemporaryDirectory() as td:
            d = pathlib.Path(td) / "c"
            shutil.copytree(REAL, d)
            b = d / "blog.md"
            s = b.read_text(encoding="utf-8")
            for old, new in subs:
                if old not in s:
                    fails.append(f"[{name}] 테스트 픽스처가 원고와 어긋남: {old[:40]}")
                s = s.replace(old, new)
            b.write_text(s, encoding="utf-8")
            importlib.reload(lint_terms)
            e, _ = lint_terms.check(d)
            if any(expect in x for x in e):
                print(f"  ✓ {name}")
            else:
                fails.append(f"[{name}] 잡아내지 못함 (검출: {e})")

    print()
    if fails:
        for f in fails:
            print(f"  ✗ {f}")
        print("\n🔴 용어 린터 회귀 테스트 실패")
        return 1
    print("🟢 용어 린터 회귀 테스트 전부 통과")
    return 0


if __name__ == "__main__":
    sys.exit(run())
