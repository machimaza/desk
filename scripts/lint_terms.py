"""용어 린터 — 제도 용어를 뜻풀이 없이 통과시키지 않습니다.

만든 이유
  '섬·벽지'를 표에 그대로 넣어 발행 직전까지 갔습니다. 법조문조차 '섬·벽지(僻地)'라고
  한자를 병기하는 단어인데, 저는 그 괄호를 떼서 원문보다 불친절한 글을 만들었습니다.
  틀린 글과 안 읽히는 글은 독자에게 똑같이 쓸모없으므로, 숫자와 같은 급으로 검사합니다.

규칙
  1. terms.json 에 등록된 용어가 본문에 나오면, **첫 등장 앞뒤 80자 안**에
     '쉬운말' 중 하나가 있어야 합니다. 없으면 FAIL.
  2. 오독위험이 기록된 용어는 실패 메시지에 그 위험을 함께 출력합니다.
  3. 등록되지 않은 한자어 후보는 WARN 으로만 알립니다 (사전 확장 후보).

사용:  python3 scripts/lint_terms.py <content_dir 또는 blog.md>
"""
import sys, json, re, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
TERMS = json.loads((ROOT / "terms.json").read_text(encoding="utf-8"))["용어"]
WINDOW = 80

# 헤더·이미지 줄은 뜻풀이를 넣을 자리가 아닙니다.
# 표는 제외하지 않습니다 — 독자는 본문보다 표를 먼저 읽고, 표 안의 괄호도 진짜 뜻풀이입니다.
SKIP = re.compile(r"^\s*(#{1,6}\s|!\[|```)")


def _prose(body):
    """산문 줄만 남기되 원본 줄번호를 유지합니다."""
    out, fence = [], False
    for i, ln in enumerate(body.split("\n"), 1):
        if ln.strip().startswith("```"):
            fence = not fence
            out.append((i, ""))
            continue
        out.append((i, "" if fence or SKIP.match(ln) else ln))
    return out


def check(target):
    p = pathlib.Path(target)
    if p.is_dir():
        p = p / "blog.md"
    body = p.read_text(encoding="utf-8")
    lines = _prose(body)
    # 산문만 이어붙인 텍스트와, 각 위치가 원래 몇 번째 줄인지의 대응표
    flat, pos2line = [], []
    for ln_no, ln in lines:
        flat.append(ln)
        pos2line += [ln_no] * (len(ln) + 1)
    text = "\n".join(flat)

    E, W = [], []
    for term, spec in TERMS.items():
        # 표기형('섬·벽지(외딴 지역)')이 아니라 맨 용어로 찾습니다.
        i = text.find(term)
        if i < 0:
            continue
        near = text[max(0, i - WINDOW): i + len(term) + WINDOW]
        if any(e in near for e in spec["쉬운말"]):
            continue
        ln_no = pos2line[i] if i < len(pos2line) else "?"
        msg = f"L{ln_no}: '{term}' 첫 등장에 뜻풀이가 없음 → 권장 표기 「{spec['표기']}」"
        if spec.get("오독위험"):
            msg += f"  [오독위험: {spec['오독위험']}]"
        E.append(msg)

    # 미등록 한자어 후보 — 사전을 넓힐 재료로만 씁니다.
    CAND = ["산정", "부과", "환산", "등재", "요건", "차등", "실익", "구제", "비과세", "준용"]
    for c in CAND:
        if c in text and c not in TERMS:
            W.append(f"'{c}' — terms.json 미등록. 뜻풀이가 필요한지 판단하세요")
    return E, W


def main(target):
    E, W = check(target)
    for w in W:
        print(f"  ⚠ {w}")
    for e in E:
        print(f"  ✗ {e}")
    if not E:
        print(f"  ✓ 용어 규칙 통과 — 등록 용어 {len(TERMS)}개 모두 첫 등장에 뜻풀이 있음")
    return 1 if E else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
