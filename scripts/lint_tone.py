"""톤 규칙(CLAUDE.md 6장)을 코드로 집행합니다. 어기면 빌드 실패."""
import re, sys, pathlib

FAIL = {
    "과장 후킹": r"충격|이것만 알면|99%가 모르는|반드시 알아야|절대 놓치|미쳤|소름",
    "단정 표현": r"100% 보장|무조건 (되|받|낫)|확실히 (낫|오릅)|반드시 (낫|수익)",
    "권유 표현": r"매수하세요|매도하세요|추천 종목|지금 사세요",
}
WARN = {
    "AI 상투구": r"에 대해 알아보겠습니다|결론적으로|오늘은 .{0,12}에 대해|~하시기 바랍니다|살펴보도록",
    "여러분 호칭": r"여러분",
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
