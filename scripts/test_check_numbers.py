"""check_numbers.py 회귀 테스트.

경쟁자들이 **실제로 발행한** 오류를 원고에 심어 넣고, 게이트가 잡는지 확인합니다.
이 테스트가 깨지면 해자가 뚫린 것입니다. 통과할 때까지 발행하지 않습니다.

실행: python3 scripts/test_check_numbers.py
"""
import json, pathlib, shutil, tempfile, sys, re
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import check_numbers

ROOT = pathlib.Path(__file__).resolve().parent.parent
BASE = ROOT / "content" / "2026-08-24-퇴직후-건강보험료"

# (이름, 본문 치환 규칙, 기대 검출 키워드)
CASES = [
    ("qbr.co.kr 오류 — 2026년이라며 2025 요율",
     [("2026년 건강보험료율은 **7.19%** 입니다.", "2026년 건강보험료율은 **7.09%** 입니다.")],
     "7.09"),
    ("qbr.co.kr 오류 — 어느 연도에도 없는 부과점수당",
     [("2026년 건강보험료율은 **7.19%**", "2026년 재산보험료부과점수당은 218.8원이고 건강보험료율은 **7.19%**")],
     "218.8"),
    ("policy.ambitstock.com 오류 — 2025 값을 2026 가이드에",
     [("2026년 건강보험료율은 **7.19%**", "2026년 재산보험료부과점수당은 208.4원이고 건강보험료율은 **7.19%**")],
     "208.4"),
    ("hi.ozrank.net 오류 — 2024.2 폐지된 자동차 부과",
     [("2026년 건강보험료율은 **7.19%**", "자동차는 배기량에 따라 점수가 부과됩니다. 2026년 건강보험료율은 **7.19%**")],
     "자동차"),
    ("장기요양 환산율 오기",
     [("2026년 장기요양보험료율은 소득 대비 0.9448%", "2026년 장기요양보험료율은 소득 대비 12.95%")],
     "장기요양"),
]


def run():
    fails = []
    # 0. 정상 원고는 반드시 통과해야 합니다 (오탐 방지)
    E, W = check_numbers.check(BASE)
    if E:
        fails.append(f"정상 원고에서 오탐 발생: {E}")
    else:
        print("  ✓ 정상 원고 통과 (오탐 없음)")

    for name, subs, expect in CASES:
        with tempfile.TemporaryDirectory() as td:
            d = pathlib.Path(td) / "c"
            shutil.copytree(BASE, d)
            b = d / "blog.md"
            s = b.read_text(encoding="utf-8")
            for a, c in subs:
                if a not in s:
                    fails.append(f"{name}: 치환 대상 문장을 찾지 못함 — 원고가 바뀌었으면 테스트도 고치세요")
                    break
                s = s.replace(a, c, 1)
            else:
                b.write_text(s, encoding="utf-8")
                E, _W = check_numbers.check(d)
                hit = any(expect in x for x in E)
                print(f"  {'✓' if hit else '✗'} {name}")
                if not hit:
                    fails.append(f"{name}: 검출 실패 (기대 키워드 '{expect}')\n      실제: {E}")

    # 항목 금액 조작도 잡아야 합니다
    with tempfile.TemporaryDirectory() as td:
        d = pathlib.Path(td) / "c"
        shutil.copytree(BASE, d)
        j = json.loads((d / "data.json").read_text(encoding="utf-8"))
        j["items"][0]["value"] = "92,000원"
        (d / "data.json").write_text(json.dumps(j, ensure_ascii=False, indent=2), encoding="utf-8")
        E, _ = check_numbers.check(d)
        hit = any("경감 후 금액 불일치" in x for x in E)
        print(f"  {'✓' if hit else '✗'} data.json 항목 금액 조작")
        if not hit:
            fails.append(f"항목 금액 조작 검출 실패: {E}")

    print()
    if fails:
        for f in fails:
            print(f"  ✗ {f}")
        print(f"\n🔴 회귀 테스트 실패 {len(fails)}건 — 해자가 뚫렸습니다.")
        return 1
    print("🟢 회귀 테스트 전부 통과")
    return 0


if __name__ == "__main__":
    sys.exit(run())
