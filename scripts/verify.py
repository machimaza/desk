"""발행 전 검수 게이트 (CLAUDE.md 7장). 7개 항목 중 5개를 자동 판정합니다.

사람이 판단할 항목 2개는 [MANUAL]로 남겨 마지막에 출력합니다.
"""
import sys, json, re, pathlib, subprocess, datetime as dt
import lint_tone, check_numbers, lint_terms, lint_sameness, lint_style

# 카테고리·고지문구는 categories.json 이 유일한 출처입니다.
CATS = json.loads((pathlib.Path(__file__).resolve().parent.parent /
                   "categories.json").read_text(encoding="utf-8"))["카테고리"]

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

    # --- 1b. flow — 영상·카드가 공유하는 이야기 구조 ------------------
    # 첫 영상과 첫 카드가 둘 다 "가격 비교만 하고 끝"이었습니다.
    # 원인은 items 를 그대로 찍은 것이고, 그래서 flow 를 필수로 만듭니다.
    if not d["meta"].get("throughline"):
        E.append("meta.throughline 없음 — 상단 배지에 둘 관통 단어가 필요합니다 "
                 "(기준: 공단에 전화해서 말해야 하는 단어)")
    fl = d.get("flow", {}).get("scenes")
    if not fl:
        E.append("flow.scenes 없음 — 영상·카드를 items 로 찍던 방식은 폐기했습니다")
    else:
        if len(fl) < 5:
            E.append(f"flow 장면 {len(fl)}개 — 5개 미만이면 이야기가 되지 않습니다")
        if fl[0].get("type") != "hook":
            E.append("flow 첫 장면이 hook 이 아닙니다")
        kinds = [x.get("type") for x in fl]
        # 이 검사가 존재하는 이유: '가격 비교만 하고 끝' 을 기계가 막기 위해서입니다.
        if "list" not in kinds:
            E.append("flow 에 list 장면이 없음 — '그래서 뭘 해야 하나'에 답하는 장면이 "
                     "하나도 없습니다. 금액만 나열하고 끝나는 구조입니다")
        if kinds.count("compare") + kinds.count("table") == len(fl) - 1:
            E.append("flow 가 금액 장면으로만 이루어져 있습니다")
        for i, x in enumerate(fl):
            for k in ("screen", "voice"):
                if not x.get(k):
                    E.append(f"flow.scenes[{i}]({x.get('type')}) 의 {k} 가 비어 있습니다")
        if not E:
            ok(f"flow {len(fl)}장면 — {' → '.join(kinds)}")
    # wage 는 '월급에서 계산하는' 글에만 해당합니다. 법이 정한 상한액처럼
    # 산식이 없는 금액도 있으므로, 일부만 빠진 경우에만 경고합니다.
    wages = [bool(it.get("wage")) for it in d["items"]]
    if any(wages) and not all(wages):
        miss = [it["label"] for it in d["items"] if not it.get("wage")]
        W.append(f"wage 가 일부 항목에만 있음 {miss} — 검산 기준이 섞입니다")

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
    # 목록에 없는 값이면 예전에는 KeyError 로 죽었습니다. 게이트는 죽지 말고 판정해야 합니다.
    cat = d["meta"]["category"]
    spec = CATS.get(cat)
    if spec is None:
        E.append(f"카테고리 '{cat}' 는 categories.json 에 없습니다. "
                 f"활성: {', '.join(k for k,v in CATS.items() if v['상태']=='활성')}")
        spec = {}
    elif spec["상태"] == "예정":
        E.append(f"카테고리 '{cat}' 는 아직 열지 않았습니다 — {spec.get('조건','')}")
    elif spec["상태"] == "폐기":
        E.append(f"카테고리 '{cat}' 는 폐기됐습니다 — {spec.get('메모','')} 되살리지 않습니다")
    disc = spec.get("고지문구", "")
    blog = base/"blog.md"
    if blog.exists():
        txt = blog.read_text(encoding="utf-8")
        if disc and disc not in txt:
            E.append(f"'{cat}' 고지 문구 누락 — 본문에 \"{disc}\" 가 있어야 합니다")
        elif disc:
            ok("카테고리 고지 문구 확인")
        # --- 3b. 제목 — 슬로건이 정한 규칙 -----------------------------
        # "마침 필요한 정보를, 알맞게" 의 주어는 독자입니다.
        # 제목이 우리 말(총정리·판단법)로 시작하면 슬로건과 어긋납니다.
        h1 = txt.split("\n", 1)[0].lstrip("# ").strip()
        SUPPLIER = ["총정리", "완벽 정리", "완벽정리", "판단법", "알아보기", "파헤",
                    "모든 것", "정리해봤", "낱낱이", "완전정복"]
        hit = [w for w in SUPPLIER if w in h1]
        if hit:
            E.append(f"제목에 공급자 언어 {hit} — 독자는 그렇게 검색하지 않습니다. "
                     f"독자의 질문 형태로 바꾸세요 (얼마 / 언제까지 / 나도 되나)")
        READER = ["얼마", "언제", "어떻게", "되나", "나요", "될까", "받나",
                  "기한", "신청", "조건", "누가", "왜"]
        if not any(w in h1 for w in READER):
            W.append("제목에 독자의 질문 신호가 없음 — 검색어와 멀어질 수 있습니다")
        else:
            ok(f"제목 규칙 통과 — 「{h1[:40]}」")

        # --- 4. 텍스트 표 존재 (검색엔진은 이미지 속 글자를 못 읽음) ---
        if not re.search(r"^\|.+\|\s*$", txt, re.M):
            E.append("블로그 본문에 마크다운 텍스트 표가 없음 (이미지로만 대체됨)")
        else: ok("본문 텍스트 표 확인")
        # --- 5. 항목별 해설 분량 ---
        # CLAUDE.md 3장 규격 — 상위 글 12개 실측 기반
        if len(txt) < 6000:
            E.append(f"본문 {len(txt):,}자 — 6,000자 미만은 깊이가 부족합니다 (목표 8,000자)")
        elif len(txt) < 8000:
            W.append(f"본문 {len(txt):,}자 — 목표는 8,000자입니다")
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
        # --- 6c-1. 표현 (널리 사용하는 표준 표현) ---
        ste, _ = lint_style.check(base)
        E += ste
        if not ste: ok("표현 규칙 통과")
        # --- 6c-2. 반복 패턴 (글이 서로 닮아가는 것) ---
        se, sw = lint_sameness.check(base)
        E += se; W += sw
        if not se and not sw: ok("반복 패턴 없음 — 기존 글과 충분히 다름")
        # --- 6d. 나레이션 대본 (영상이 있을 때만) ---
        if (base/"video.mp4").exists():
            import build_narration
            _, _, nre = build_narration.build(base)
            E += nre
            if not nre: ok("나레이션 대본 통과 — 길이·중복·순화어")
    else:
        E.append("blog.md 없음")

    # --- 6e. 화면 밀도 — 빈 화면은 만들다 만 것처럼 보입니다 ------------
    # 처음 카드는 잉크 4.2%(화면의 95%가 빈 공간)였고, 쇼츠에는 3.6% 프레임도 있었습니다.
    # 특히 인스타는 음성이 없으므로 카드가 내용을 다 짊어져야 합니다.
    try:
        from PIL import Image
        import numpy as np

        def _ink(path, box=None):
            im = Image.open(path).convert("L")
            if box:
                im = im.crop(box)
                a = np.array(im)
            else:
                a = np.array(im)
            bg = np.bincount(a.ravel()).argmax()
            return float((np.abs(a.astype(int) - int(bg)) > 12).mean() * 100)

        cards = sorted((base / "images").glob("card_*.png"))
        if cards:
            vals = [(c.name, _ink(c)) for c in cards]
            thin = [n for n, v in vals if v < 5.0]
            avg = sum(v for _, v in vals) / len(vals)
            if thin:
                E.append(f"카드가 비어 있습니다 {thin} — 잉크 5% 미만. "
                         f"인스타는 음성이 없으므로 points 로 내용을 채우세요")
            elif avg < 6.0:
                W.append(f"카드 평균 밀도 {avg:.1f}% — 6% 이상을 권합니다")
            else:
                ok(f"카드 밀도 평균 {avg:.1f}% (최소 {min(v for _, v in vals):.1f}%)")
    except ImportError:
        W.append("Pillow 없음 — 화면 밀도 검사를 건너뜁니다")

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
    # D-day 배지는 상시 노출을 폐기했습니다 (9장 — 세 번째 장면부터 아무도 안 읽음).
    # 이제 장면이 dday:true 로 요청할 때만 뜹니다. 그래서 없는 것이 정상이고,
    # 요청해 놓고 문구가 없는 경우만 잡습니다.
    wants = [i for i, x in enumerate(d.get("flow", {}).get("scenes", [])) if x.get("dday")]
    if wants and not d["meta"].get("dday"):
        E.append(f"flow.scenes{wants} 가 dday 배지를 요청했는데 meta.dday 가 없습니다")
    nocap = [i["label"] for i in d["items"] if not i.get("caption")]
    if nocap:
        W.append(f"caption 없는 항목 {len(nocap)}개 — 영상 자막이 화면 텍스트와 중복됩니다")
    else: ok("영상 자막이 화면 텍스트와 분리됨")
    if not (base/"images"/"alt.txt").exists():
        W.append("images/alt.txt 없음 — 인스타 대체 텍스트 미생성")

    # --- 사람 판단 항목 ---
    M.append("이미지 저작권 — 생성/공공누리 자료만 사용했는가")
    M.append("과장·불안 조성 뉘앙스 — 린터가 못 잡는 맥락상 문제는 없는가")
    if disc:
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
