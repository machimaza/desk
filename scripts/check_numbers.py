"""수치 정합성 검사 — CLAUDE.md 4장 "수치 원장".

이 프로젝트의 해자는 "숫자가 맞다"는 것 하나뿐입니다.
경쟁 글들이 틀리는 지점은 전부 같습니다: 작년 값을 올해 값이라고 쓰는 것.
그래서 이 검사기는 문법이 아니라 **연도 오염**을 잡습니다.

검사 항목
  1. 과거연도 값 오염 — 2025/2024 값이 연도 언급 없이 본문에 등장
  2. 유령 비율      — rates.json 어디에도 없는 %가 본문에 등장
  3. 항목 금액 불일치 — data.json items[].value 가 산식과 어긋남
  4. 유령 금액      — 1만원 이상인데 data.json·rates.json 어디에도 없음

사용:  python3 scripts/check_numbers.py <content_dir>
"""
import sys, json, re, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
RATES = json.loads((ROOT / "rates.json").read_text(encoding="utf-8"))

# 본문에서 이 값들은 수치가 아니라 문서 구조입니다. 검사 대상에서 제외합니다.
STRUCTURAL = re.compile(r"^(#{1,6}\s|\||!\[|\[.*\]\(|>\s*\*\*Q\d)")


def _num(tok):
    return float(tok.replace(",", ""))


def _year_rate_map():
    """연도별 '이 연도에만 유효한 값' 목록. 과거연도 값이 본문에 오면 오염."""
    m = {}
    for y, blk in RATES.items():
        if not y.isdigit():
            continue
        vals = set()
        if "요율" in blk:
            vals.add(round(blk["요율"] * 100, 4))          # 7.19 형태
        if "재산보험료부과점수당" in blk:
            vals.add(float(blk["재산보험료부과점수당"]))     # 211.5 형태
        m[y] = vals
    return m


def check(base):
    base = pathlib.Path(base)
    d = json.loads((base / "data.json").read_text(encoding="utf-8"))
    body = (base / "blog.md").read_text(encoding="utf-8")
    cur = str(d["meta"]["publish_date"])[:4]
    R = RATES.get(cur)
    if R is None:
        return [f"rates.json에 {cur}년 블록이 없습니다"], []
    E, W = [], []

    # ---- 1. 과거연도 값 오염 -------------------------------------------
    ymap = _year_rate_map()
    cur_vals = ymap.get(cur, set())
    lines = body.split("\n")
    # 같은 값을 여러 연도가 공유할 수 있습니다(요율 7.09%는 2024·2025 공통).
    # 그 중 한 연도라도 줄에 적혀 있으면 의도된 비교 서술로 봅니다.
    owners = {}
    for y, vals in ymap.items():
        for v in vals:
            owners.setdefault(v, set()).add(y)
    past_vals = set()
    for y, vals in ymap.items():
        if y < cur:
            past_vals |= vals - cur_vals
    for v in past_vals:
        pat = re.compile(r"(?<![\d.])" + re.escape(f"{v:g}") + r"(?![\d.])")
        ys = sorted(owners[v])
        for i, ln in enumerate(lines, 1):
            for m in pat.finditer(ln):
                # 면제 판정은 줄 전체가 아니라 숫자 **바로 앞 12자**로 좁힙니다.
                # "2026년 요율은 7.09%입니다. 2025년 7.09%에서 올랐습니다" 같은 문장에서
                # 뒤쪽 연도 표기가 앞쪽 오염을 가려주는 일을 막기 위해서입니다.
                near = ln[max(0, m.start() - 12):m.start()]
                if any(y in near for y in ys) or "전년" in near or "작년" in near:
                    continue
                E.append(f"L{i}: {'·'.join(ys)}년 값 {v:g} 이(가) 연도 표기 없이 사용됨 — …{ln[max(0,m.start()-25):m.end()+15].strip()}…")

    # 올해 값에 대한 적극적 확인 — "2026년 …요율은 X%" 라고 썼다면 X는 반드시 올해 값이어야 합니다.
    HEAD = [("건강보험료율", r"(?<!장기요양)(?:건강)?보험료율|(?<!장기요양)요율",
             round(R["요율"] * 100, 4), "%"),
            ("장기요양보험료율", r"장기요양보험료율",
             round(R["장기요양보험료율"] * 100, 4), "%"),
            ("재산보험료부과점수당", r"부과점수당",
             float(R["재산보험료부과점수당"]), "원")]
    for name, kw, want, unit in HEAD:
        for i, ln in enumerate(lines, 1):
            for m in re.finditer(cur + r"년[^\n]{0,25}?(?:" + kw + r")[^\n]{0,25}?([\d,]+(?:\.\d+)?)\s*" + unit, ln):
                got = _num(m.group(1))
                if abs(got - want) > 1e-6:
                    E.append(f"L{i}: {cur}년 {name} 을(를) {got:g}{unit} 로 표기 — 원장 값은 {want:g}{unit}")

    # ---- 2. 유령 비율 ---------------------------------------------------
    allowed_pct = {round(R["요율"] * 100, 4), round(R["직장_본인부담률"] * 100, 4),
                   round(R["장기요양보험료율"] * 100, 4), round(R["장기요양_건보료대비"] * 100, 4)}
    for v in R.get("소득평가율", {}).values():
        if isinstance(v, (int, float)):
            allowed_pct.add(round(v * 100, 4))
    ik = R.get("임의계속가입", {})
    if "경감률" in ik:
        allowed_pct.add(round(ik["경감률"] * 100, 4))
    allowed_pct.add(30.0)                      # 전월세 평가율
    # 글 단위 예외는 data.json 에 명시적으로 적어야 통과시킵니다.
    allowed_pct |= {float(x) for x in d.get("allow_pct", [])}
    # 전년 대비 증감폭(0.1%p 등)은 별도 표기이므로 %p 는 검사에서 제외합니다.
    # 본문은 13.1405%를 13.14%로 줄여 쓰는 게 정상입니다. 자리수를 줄인 형태도 허용합니다.
    def _pct_ok(x):
        return any(abs(x - a) < 1e-9 or abs(x - round(a, len(f"{x:g}".split(".")[-1]) if "." in f"{x:g}" else 0)) < 1e-9
                   for a in allowed_pct)
    past_pct = {v for v in past_vals if v < 100}
    for i, ln in enumerate(lines, 1):
        if STRUCTURAL.match(ln.strip()):
            continue
        for tok in re.findall(r"(\d+(?:\.\d+)?)\s*%(?!p)", ln):
            x = round(_num(tok), 4)
            if _pct_ok(x):
                continue
            if x in past_pct:
                continue   # 위 1번 검사가 연도 표기까지 이미 판정했습니다
            W.append(f"L{i}: 원장에 없는 비율 {tok}% — 출처를 확인하거나 data.json allow_pct 에 등록하세요")

    # ---- 3. 항목 금액 불일치 ---------------------------------------------
    # detail 안의 "A × B% = C" 서술을 실제로 계산해 검산합니다.
    for it in d["items"]:
        m = re.search(r"([\d,]+)\s*×\s*([\d.]+)\s*%\s*=\s*([\d,]+)", it.get("detail", ""))
        if not m:
            continue
        a, r, c = _num(m.group(1)), _num(m.group(2)) / 100, _num(m.group(3))
        if abs(a * r - c) > 10:
            E.append(f"항목 '{it['label']}' 산식 불일치: {m.group(1)}×{m.group(2)}% = {a*r:,.0f} ≠ {m.group(3)}")
        if "경감률" in ik:
            half = int(c * ik["경감률"] // 10 * 10)
            shown = _num(re.sub(r"[^\d,]", "", it["value"]))
            if abs(half - shown) > 10:
                E.append(f"항목 '{it['label']}' 경감 후 금액 불일치: 계산 {half:,} ≠ 표기 {shown:,.0f}")

    # ---- 3b. 폐지된 제도를 현행처럼 서술 ----------------------------------
    # 2024.2 자동차 부과 폐지처럼, 폐지 사실을 모르고 쓴 글이 상위에 그대로 남아 있습니다.
    ABOLISHED = {"자동차": (r"자동차[^.\n]{0,30}(부과|점수|배기량|차량가액)",
                          "자동차 부과는 2024.2 폐지됨 (rates.json 자동차.부과=false)")}
    for key, (pat, msg) in ABOLISHED.items():
        blk = R.get(key)
        if not isinstance(blk, dict) or blk.get("부과") is not False:
            continue
        for i, ln in enumerate(lines, 1):
            if not re.search(pat, ln):
                continue
            if "폐지" in ln or "제외" in ln or "빠졌" in ln or "부과되지" in ln:
                continue   # 폐지 사실을 설명하는 문장은 정상입니다
            E.append(f"L{i}: {msg} — {ln.strip()[:60]}")

    # ---- 4. 유령 금액 ----------------------------------------------------
    known = set()
    for k, v in R.items():
        if isinstance(v, (int, float)):
            known.add(float(v))
    for it in d["items"]:
        for tok in re.findall(r"[\d,]+", it.get("value", "") + " " + it.get("detail", "")):
            if tok.strip(","):
                known.add(_num(tok))
    # items[].wage 가 있으면 금액을 산식으로 직접 검산합니다 (detail 정규식보다 확실).
    # employed(재직 중 본인부담분)가 임의계속 금액과 같다는 주장도 여기서 확인합니다 —
    # 화면에 "금액이 바뀌지 않습니다"라고 쓰는 근거이므로 말로 두면 안 됩니다.
    for it in d["items"]:
        w = it.get("wage")
        if not w:
            continue
        shown = _num(re.sub(r"[^\d,]", "", it["value"]))
        want = int(w * R["요율"] * ik.get("경감률", 0.5) // 10 * 10)
        if abs(want - shown) > 10:
            E.append(f"'{it['label']}' 임의계속 금액 불일치: 산식 {want:,} ≠ 표기 {shown:,.0f}")
        if it.get("employed"):
            emp = _num(re.sub(r"[^\d,]", "", it["employed"]))
            want_e = int(w * R["직장_본인부담률"] // 10 * 10)
            if abs(want_e - emp) > 10:
                E.append(f"'{it['label']}' 재직 중 본인부담 불일치: 산식 {want_e:,} ≠ 표기 {emp:,.0f}")
            if abs(emp - shown) > 10:
                E.append(f"'{it['label']}' 재직 중({emp:,.0f})과 임의계속({shown:,.0f})이 다른데 "
                         f"화면은 '금액이 바뀌지 않는다'고 말하고 있습니다")

    # 영상 장면의 금액도 검산합니다. 영상은 블로그보다 오래 남고 고치기 어려우므로
    # 여기서 틀리면 회수 비용이 훨씬 큽니다.
    for i, sc in enumerate(d.get("video", {}).get("scenes", [])):
        for side in ("before", "after"):
            if side in sc:
                v = _num(re.sub(r"[^\d,]", "", sc[side]["value"]))
                known.add(v)
        if "before" in sc and "after" in sc and "경감률" in ik:
            nb = _num(re.sub(r"[^\d,]", "", sc["before"]["value"]))
            na = _num(re.sub(r"[^\d,]", "", sc["after"]["value"]))
            want = int(nb * ik["경감률"] // 10 * 10)
            if abs(want - na) > 10:
                E.append(f"video.scenes[{i}] 경감 후 금액 불일치: 계산 {want:,} ≠ 표기 {na:,.0f}")
        if sc.get("big"):
            for tok in re.findall(r"[\d,]+", sc["big"]):
                if tok.strip(","):
                    known.add(_num(tok))

    # derived: 본문에 등장하지만 items 가 아닌 파생 금액. 산식을 실제로 계산해 검산합니다.
    for dv in d.get("derived", []):
        if not re.fullmatch(r"[\d\s.*/+()-]+", dv["formula"]):
            E.append(f"derived '{dv['label']}' 산식에 허용되지 않은 문자")
            continue
        got = eval(dv["formula"], {"__builtins__": {}})
        if dv.get("round") == "floor10":
            got = int(got // 10 * 10)
        shown = _num(re.sub(r"[^\d,]", "", dv["value"]))
        if abs(got - shown) > 10:
            E.append(f"derived '{dv['label']}' 불일치: 계산 {got:,.0f} ≠ 표기 {shown:,.0f}")
        known.add(shown)
    for i, ln in enumerate(lines, 1):
        if STRUCTURAL.match(ln.strip()):
            continue
        for tok in re.findall(r"([\d,]{5,})\s*원", ln):
            v = _num(tok)
            if v >= 10000 and v not in known:
                W.append(f"L{i}: data.json·rates.json 어디에도 없는 금액 {tok}원")
    return E, W


def main(base):
    E, W = check(base)
    for w in W:
        print(f"  ⚠ {w}")
    for e in E:
        print(f"  ✗ {e}")
    if not E and not W:
        print("  ✓ 수치 정합성 통과 — 본문 숫자가 모두 원장과 일치")
    elif not E:
        print(f"  ✓ 수치 오류 0건 (경고 {len(W)}건)")
    return 1 if E else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
