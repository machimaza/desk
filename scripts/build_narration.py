#!/usr/bin/env python3
"""나레이션 대본 검사기 — AI 음성으로 읽을 원고를 검사합니다.

설계 변경 기록 (2026-08-24)
  처음에는 detail 문장을 기계적으로 치환해 대본을 '생성'하려 했습니다.
  결과가 "경감받아" → "깎아주는받아" 였습니다. 한국어 활용을 깨뜨립니다.
  게다가 화면 자막을 그대로 읽어 버려, 자막≠화면 규칙을 스스로 어겼습니다.

  그래서 생성을 포기하고 **검사**로 바꿨습니다. 다른 린터들과 같은 원칙입니다.
  대본은 data.json 의 narration 필드에 사람이 씁니다. 이 스크립트는
  그것이 읽을 만한지 판정만 합니다.

검사 항목
  1. 화면 자막과 겹침 — 음성이 화면을 그대로 읽으면 실패
  2. 장면 길이 초과 — 한국어 나레이션 초당 5.5음절 기준
  3. 오독 위험 용어를 순화하지 않고 쓴 경우 (귀로는 동음이의어가 구분 안 됨)
  4. 대본 누락

사용:  python3 scripts/build_narration.py <콘텐츠폴더>
출력:  narration.txt — 음성 서비스에 붙여 넣을 원고
"""
import sys, json, re, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
TERMS = json.loads((ROOT / "terms.json").read_text(encoding="utf-8"))["용어"]
SYL_PER_SEC = 5.5

_D1 = ["", "일", "이", "삼", "사", "오", "육", "칠", "팔", "구"]
_U4 = ["", "만", "억", "조"]
_U1 = ["", "십", "백", "천"]


def kor_number(n):
    """숫자를 소리 나는 대로 — 음절 수를 세기 위한 것입니다."""
    if n == 0:
        return "영"
    out, gi = [], 0
    while n > 0:
        chunk, part = n % 10000, []
        for i in range(4):
            dg = (chunk // (10 ** i)) % 10
            if dg:
                part.insert(0, ("" if dg == 1 and i else _D1[dg]) + _U1[i])
        if part:
            out.insert(0, "".join(part) + _U4[gi])
        n //= 10000
        gi += 1
    return "".join(out)


def spoken_form(text):
    """읽을 때의 형태로 바꿔 음절을 셉니다. 원문을 고치지는 않습니다."""
    t = re.sub(r"(\d[\d,]*)\.(\d+)\s*%",
               lambda m: kor_number(int(m.group(1).replace(",", ""))) + "쩜"
                         + "".join(_D1[int(c)] or "영" for c in m.group(2)) + "퍼센트", text)
    t = re.sub(r"(\d[\d,]*)\s*%",
               lambda m: kor_number(int(m.group(1).replace(",", ""))) + "퍼센트", t)
    t = re.sub(r"(\d[\d,]*)", lambda m: kor_number(int(m.group(1).replace(",", ""))), t)
    return t


def syllables(s):
    return len(re.findall(r"[가-힣]", spoken_form(s)))


def overlap(a, b):
    """두 문장이 얼마나 겹치는지 — 2글자 단위 비교."""
    A = {a[i:i+2] for i in range(len(a) - 1)}
    B = {b[i:i+2] for i in range(len(b) - 1)}
    return 2 * len(A & B) / max(1, len(A) + len(B))   # Dice 계수


def build(base):
    base = pathlib.Path(base)
    d = json.loads((base / "data.json").read_text(encoding="utf-8"))
    import motion
    scenes = motion.build_scenes(d)
    m = d["meta"]

    caps = []
    for html, anim, hold in scenes:
        c = re.search(r'<div class="cap"[^>]*>(.*?)</div>', html, re.S)
        caps.append((re.sub(r"<[^>]+>", "", c.group(1)).strip() if c else "", anim + hold))

    flow = m.get("video_structure") == "flow"
    seq = list(reversed(d["items"])) if m.get("video_structure") == "countdown" else d["items"]
    E, rows = [], []
    for i, (cap, dur) in enumerate(caps):
        if flow:
            # flow 에서는 장면마다 음성이 명시돼 있습니다.
            voice = d["video"]["scenes"][i].get("voice", "")
            where = f"video.scenes[{i}].voice"
        elif i == 0:
            voice = d.get("narration_hook", "")
            where = "narration_hook"
        elif i == len(caps) - 1:
            voice = d.get("narration_outro", "")
            where = "narration_outro"
        else:
            it = seq[i - 1]
            voice = it.get("narration", "")
            where = f"items[{d['items'].index(it)}].narration"

        budget = int(dur * SYL_PER_SEC)
        syl = syllables(voice)
        if not voice.strip():
            E.append(f"[{i+1:02d}] 대본 없음 — data.json {where} 를 채우세요")
        else:
            if syl > budget:
                E.append(f"[{i+1:02d}] {syl}음절 / 장면 {dur:.1f}초에 맞는 한도 {budget} — 줄이세요")
            if cap and overlap(voice, cap) > 0.45:
                E.append(f"[{i+1:02d}] 음성이 화면 자막과 겹침 — 화면은 사실, 음성은 해석이어야 합니다")
            for t, spec in TERMS.items():
                if spec.get("오독위험") and t in voice and spec["나레이션"] not in voice:
                    E.append(f"[{i+1:02d}] '{t}' 을(를) 그대로 읽음 — 귀로는 구분되지 않습니다. "
                             f"'{spec['나레이션']}' 으로 바꾸세요")
        rows.append({"no": i + 1, "sec": round(dur, 1), "budget": budget,
                     "syl": syl, "screen": cap, "voice": voice})

    out = [f"# {m['title']} — 나레이션 대본",
           f"# 구조 {m.get('video_structure','countdown')} · 장면 {len(rows)}개 · "
           f"총 {sum(r['sec'] for r in rows):.1f}초",
           "# 화면=사실, 음성=해석. 같은 문장을 읽지 마세요.",
           "# 음성 캐릭터는 한 번 정하면 고정합니다. 흔한 무료 음성은 피하세요.", ""]
    for r in rows:
        out += [f"[{r['no']:02d}] {r['sec']}초 · {r['syl']}/{r['budget']}음절",
                f"  (화면) {r['screen']}",
                f"  (음성) {r['voice']}", ""]
    p = base / "narration.txt"
    p.write_text("\n".join(out), encoding="utf-8")
    return p, rows, E


def main(argv):
    p, rows, E = build(argv[1])
    for e in E:
        print(f"  ✗ {e}")
    if not E:
        print(f"  ✓ 대본 검사 통과 — 장면 {len(rows)}개, "
              f"총 {sum(r['syl'] for r in rows)}음절")
    print(f"[narration] {p}")
    return 1 if E else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
