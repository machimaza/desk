"""톤 규칙(CLAUDE.md 6장)을 코드로 집행합니다. 어기면 빌드 실패."""
import re, sys, pathlib

DISEASE = r"(암|당뇨|고혈압|혈압|혈당|아토피|치매|관절염|골다공증|비염|위염|간염|통풍|불면증|우울증|탈모|디스크|염증|콜레스테롤)"
EFFECT  = r"(치료|완치|낫는|낫습|효능|예방|개선|회복|잡아|없애|제거|낮춰|줄여)"

FAIL = {
    # 브랜드 톤
    "과장 후킹": r"충격|이것만 알면|99%가 모르는|반드시 알아야|절대 놓치|미쳤|소름",
    "단정 표현": r"100% 보장|무조건 (되|받|낫)|확실히 (낫|오릅)|반드시 (낫|수익)",
    # 식품표시광고법 제8조 (10년 이하 / 1억) — 가장 무거움
    "질병+효능 조합": DISEASE + r"[^.。\n]{0,20}" + EFFECT,
    "기능성 표방": r"항암|면역력\s*(강화|증진)|염증\s*(제거|완화)|디톡스|해독\s*작용|살균\s*효과",
    "의약품 오인": r"복용|[가-힣]+정을?\s*(드|먹)|약\s*대신|처방받은?\s*것처럼",
    "부작용 부인": r"부작용\s*(이\s*)?없|100%\s*안전|안전성\s*보장",
    # 의료법 제56조① / 제27조③
    "의료광고·유인": r"(병원|의원|클리닉|한의원)\s*(예약|할인|링크|추천)|전후\s*사진|시술\s*후기",
    "진단성 표현": r"이\s*증상이?면\s*[가-힣]+(병|증)|~?라고\s*진단",
    # 자본시장법 / 금소법 제22조
    "투자 권유": r"매수하세요|매도하세요|추천\s*종목|지금\s*사세요|목표가",
    "수익 보장": r"원금\s*보장|확정\s*수익|손실\s*없|수익률\s*보장",
    "개별 자문": r"(DM|디엠|댓글)\s*(주시면|남기시면)\s*[^.\n]{0,15}(상담|봐드|분석해)",
}
WARN = {
    "AI 상투구": r"에 대해 알아보겠습니다|결론적으로|오늘은 .{0,12}에 대해|~하시기 바랍니다|살펴보도록|안녕하세요",
    "여러분 호칭": r"여러분",
    "금융상품 지목": r"(은행|증권|카드사)\s*[가-힣]{0,6}(적금|예금|카드|대출)\s*(가입|신청|추천)",
    "대가성 의심": r"제공받아|협찬|수수료를?\s*지급",
}

def check(path):
    txt = pathlib.Path(path).read_text(encoding="utf-8")
    errs, warns = [], []
    for name, pat in FAIL.items():
        for m in re.finditer(pat, txt):
            errs.append(f"[FAIL] {name}: …{txt[max(0,m.start()-15):m.end()+15]}…")
    for name, pat in WARN.items():
        for m in re.finditer(pat, txt):
            warns.append(f"[WARN] {name}: …{txt[max(0,m.start()-15):m.end()+15]}…")
    body = re.sub(r"^[#>|\-\s].*$", "", txt, flags=re.M)
    sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n", body) if len(s.strip()) > 5]
    if sents:
        long_ratio = sum(1 for s in sents if len(s) > 40) / len(sents)
        if long_ratio > 0.30:
            warns.append(f"[WARN] 긴 문장 비율 {long_ratio:.0%} (40자 초과, 기준 30%)")
    return errs, warns

if __name__ == "__main__":
    e, w = check(sys.argv[1])
    for x in e + w: print(x)
    print(f"\n톤 검사: 실패 {len(e)}건, 경고 {len(w)}건")
    sys.exit(1 if e else 0)
