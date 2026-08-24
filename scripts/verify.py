"""발행 전 검수 게이트 (CLAUDE.md 7장). 7개 항목 중 5개를 자동 판정합니다.

사람이 판단할 항목 2개는 [MANUAL]로 남겨 마지막에 출력합니다.
"""
import sys, json, re, pathlib, subprocess, datetime as dt
import lint_tone, check_numbers, lint_terms

# CLAUDE.md v3 §8 "고정 문구"와 1:1 대응. 여기를 고칠 때는 CLAUDE.md도 같이 고칠 것.
DISC = {
 # 건강보험료 니치는 의료 콘텐츠가 아니라 제도 콘텐츠다.
 # 증상 상담 문구가 아니라 기관 확인 문구를 요구한다.
 "health": "국민건강보험공단(1577-1000)에 확인",
 "money":  "투자 권유가 아닙니다",
}
# 니치를 건강보험료 하나로 좁힌 뒤, 3개 카테고리 체계는 잔재만 남았습니다.
# "건강"은 의료 콘텐츠로 오해되므로 씁니다: 제도 콘텐츠임을 배지가 드러내야 합니다.
CAT2KEY = {"건강보험료":"health", "재테크":"money", "생활꿀팁":"none"}
AXES = {"소득구간","연령대","가구형태","지역","직업형태","생활패턴"}
BANNED_AXIS = {
 "자산순위":"상대적 박탈감 — 톤 규칙 위반",
 "자산 순위":"상대적 박탈감 — 톤 규칙 위반",
 "질병위험도":"진단 단정 — 가드레일 위반",
 "질병 위험도":"진단 단정 — 가드레일 위반",
 "외모":"브랜드 무관, 니치 훼손",
 "체형":"브랜드 무관, 니치 훼손",
}
STALE_DAYS = 730

def main(base):
    base = pathlib.Path(base)
    E, W, M = [], [], []
    ok = lambda s: print(f"  ✓ {s}")

    # --- 1. data.json 무결성 / 출처 연결 ---
    d = json.loads((base/"data.json").read_text(encoding="utf-8"))
    sids = {s["id"]: s for s in d["sources"]}
    for it in d["items"]:
        if it["source_id"] not in sids:
            E.append(f"항목 '{it['label']}' 의 source_id({it['source_id']})가 sources에 없음")
    # 출처는 items에 붙지 않아도 본문에서 인용되면 "사용된" 것으로 본다.
    # (근거 문단·표·FAQ에서만 쓰이는 원문이 실제로 있다)
    body = ""
    bp = base / "blog.md"
    if bp.exists(): body = bp.read_text(encoding="utf-8")
    used = {i["source_id"] for i in d["items"]}
    for sid, s_ in sids.items():
        if s_.get("url") and s_["url"] in body: used.add(sid)
    unused = set(sids) - used
    if unused: W.append(f"본문·항목 어디에도 인용되지 않은 출처: {', '.join(sorted(unused))}")
    if not E: ok("모든 항목에 출처가 연결됨")

    # --- 1b. 자기 대입 축 검사 ---
    ax = d["meta"].get("axis")
    if ax:
        at = ax.get("type","")
        if at in BANNED_AXIS:
            E.append(f"금지 축 '{at}' 사용 — {BANNED_AXIS[at]}")
        elif at not in AXES:
            E.append(f"허용되지 않은 축 '{at}' — 허용: {', '.join(sorted(AXES))}")
        elif len(ax.get("buckets",[])) < 3:
            W.append(f"축 '{at}' 구간이 3개 미만 — 자기 대입 효과가 약합니다")
        else:
            ok(f"자기 대입 축 '{at}' ({len(ax['buckets'])}구간)")
    else:
        W.append("axis 없음 — 자기 대입 장치가 없어 저장·공유율이 낮을 수 있습니다")

    # --- 2. 출처 등급 / 최신성 ---
    today = dt.date.today()
    for s in d["sources"]:
        if s.get("tier", 4) >= 4:
            E.append(f"{s['id']} 출처 등급 4 (사용 불가): {s['issuer']}")
        url = s.get("url","")
        if not re.match(r"^https?://", url):
            E.append(f"{s['id']} 원문 링크 없음")
        elif s.get("tier",4) <= 2 and not re.search(r"\.(go|or|re)\.kr", url):
            E.append(f"{s['id']} tier {s['tier']} 인데 공공 도메인(.go.kr/.or.kr/.re.kr)이 아님: {url}")
        try:
            eff = dt.date.fromisoformat(s["effective_date"])
            if (today - eff).days > STALE_DAYS:
                # 오래된 자료라도 더 상위 근거(조문 등)와 대조해 두었다면 경고를 내리지 않습니다.
                # 대신 무엇과 대조했는지 반드시 기록으로 남게 합니다.
                rc = s.get("rechecked_against")
                if rc and rc in {x["id"] for x in d["sources"]}:
                    ok(f"{s['id']} 시행일 {eff} (오래됨) — {rc} 조문과 대조 확인됨")
                else:
                    W.append(f"{s['id']} 시행일 {eff} — {(today-eff).days}일 경과, 개정 여부 확인 필요")
        except Exception:
            W.append(f"{s['id']} effective_date 형식 확인 필요: {s.get('effective_date')}")
    ok("출처 등급·링크·최신성 검사 완료")

    # --- 3. 카테고리 고지 문구 ---
    key = CAT2KEY[d["meta"]["category"]]
    blog = base/"blog.md"
    if blog.exists():
        txt = blog.read_text(encoding="utf-8")
        if key != "none" and DISC[key] not in txt:
            E.append(f"'{d['meta']['category']}' 카테고리 고지 문구 누락")
        else: ok("카테고리 고지 문구 확인")
        # --- 4. 텍스트 표 존재 (검색엔진은 이미지 속 글자를 못 읽음) ---
        if not re.search(r"^\|.+\|\s*$", txt, re.M):
            E.append("블로그 본문에 마크다운 텍스트 표가 없음 (이미지로만 대체됨)")
        else: ok("본문 텍스트 표 확인")
        # --- 5. 항목별 해설 분량 ---
        if len(txt) < 1200: W.append(f"본문 {len(txt)}자 — 항목별 해설이 부족할 수 있음")
        # --- 6. 톤 린트 ---
        te, tw = lint_tone.check(blog)
        E += te; W += tw
        if not te: ok("톤 규칙 통과")
        # --- 6b. 수치 정합성 (이 프로젝트의 해자) ---
        ne, nw = check_numbers.check(base)
        E += ne; W += nw
        if not ne: ok("수치 정합성 통과 — 본문 숫자가 원장과 일치")
        # --- 6c. 용어 뜻풀이 (틀린 글과 안 읽히는 글은 똑같이 쓸모없음) ---
        ge, _ = lint_terms.check(base)
        E += ge
        if not ge: ok("용어 규칙 통과 — 등록 용어 첫 등장에 뜻풀이 있음")
        # --- 6d. 나레이션 대본 (영상이 있을 때만) ---
        if (base/"video.mp4").exists():
            import build_narration
            _, _, nre = build_narration.build(base)
            E += nre
            if not nre: ok("나레이션 대본 통과 — 길이·중복·순화어")
    else:
        E.append("blog.md 없음")

    # --- 7. 영상 규격 ---
    vid = base/"video.mp4"
    if vid.exists():
        # 오디오 스트림 — 없으면 쇼츠·틱톡에서 불리하거나 거부됩니다
        a = subprocess.run(["ffprobe","-v","error","-select_streams","a",
            "-show_entries","stream=codec_name","-of","csv=p=0",str(vid)],
            capture_output=True,text=True).stdout.strip()
        if not a: E.append("영상에 오디오 스트림이 없음 — 쇼츠·틱톡 업로드 시 불리")
        else: ok(f"오디오 스트림 있음 ({a})")
        if not (base/"video.srt").exists(): W.append("video.srt 없음 — 유튜브 자막 업로드 불가")
        if not (base/"cover.png").exists(): W.append("cover.png 없음 — 썸네일 지정 불가")
        p = subprocess.run(["ffprobe","-v","error","-select_streams","v:0",
            "-show_entries","stream=width,height:format=duration","-of","json",str(vid)],
            capture_output=True,text=True)
        j = json.loads(p.stdout); st = j["streams"][0]
        dur = float(j["format"]["duration"])
        if (st["width"], st["height"]) != (1080,1920):
            E.append(f"영상 해상도 {st['width']}x{st['height']} (1080x1920 아님)")
        # CLAUDE.md 9장 — 리워드(60초 하한)를 포기하고 완주율을 택했습니다.
        if dur < 40: E.append(f"영상 {dur:.1f}초 — 40초 미만 (내용이 얕다는 신호)")
        elif dur > 55: E.append(f"영상 {dur:.1f}초 — 55초 초과 (완주율 급락 구간)")
        else: ok(f"영상 규격 통과 ({dur:.1f}초, {st['width']}x{st['height']})")
    else:
        W.append("video.mp4 없음 (영상 트랙 미생성)")

    # --- 조판 규칙 (CLAUDE.md 5장) ---
    if not d["meta"].get("dday"):
        W.append("meta.dday 없음 — D-day 배지가 빠집니다 (브랜드 시그니처)")
    nocap = [i["label"] for i in d["items"] if not i.get("caption")]
    if nocap:
        W.append(f"caption 없는 항목 {len(nocap)}개 — 영상 자막이 화면 텍스트와 중복됩니다")
    else: ok("영상 자막이 화면 텍스트와 분리됨")
    if not (base/"images"/"alt.txt").exists():
        W.append("images/alt.txt 없음 — 인스타 대체 텍스트 미생성")

    # --- 사람 판단 항목 ---
    M.append("이미지 저작권 — 생성/공공누리 자료만 사용했는가")
    M.append("과장·불안 조성 뉘앙스 — 린터가 못 잡는 맥락상 문제는 없는가")
    if d["meta"]["category"] in ("건강보험료","재테크"):
        M.append("YMYL — 진단/처방/수익 단정으로 읽힐 문장은 없는가")

    print("\n" + "─"*54)
    for x in W: print("  ⚠", x)
    for x in E: print("  ✗", x)
    print("─"*54)
    print(f"자동 판정: 실패 {len(E)}건 / 경고 {len(W)}건")
    print("\n[사람이 확인할 항목]")
    for m in M: print("  [ ]", m)
    print("\n" + ("🟢 자동 게이트 통과 — 위 수동 항목만 확인 후 발행하세요."
                  if not E else "🔴 발행 불가 — 실패 항목을 먼저 해결하세요."))
    return 1 if E else 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
