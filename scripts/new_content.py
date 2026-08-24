#!/usr/bin/env python3
"""새 글 폴더 만들기 — 규칙을 갖춘 상태에서 시작하게.

왜 있나
  첫 글에서 나온 지적들(가격표만 있음 · 모호한 라벨 · 관통 단어 없음)은
  전부 "빈 파일에서 시작해서" 생긴 문제입니다. 문서에 적어두는 것만으로는
  다음 글에서 또 샙니다. 템플릿이 필요한 필드를 미리 들고 있어야 합니다.

사용:  python3 scripts/new_content.py <슬러그> [--date YYYY-MM-DD]
"""
import sys, json, shutil, pathlib, datetime as dt

ROOT = pathlib.Path(__file__).resolve().parent.parent
TPL = ROOT / "content" / "_template"


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 1
    slug = argv[1]
    date = argv[argv.index("--date") + 1] if "--date" in argv else dt.date.today().isoformat()
    name = f"{date}-{slug}"
    dst = ROOT / "content" / name
    if dst.exists():
        print(f"이미 있습니다: {dst}")
        return 1
    dst.mkdir(parents=True)
    d = json.loads((TPL / "data.json").read_text(encoding="utf-8"))
    d["meta"]["id"] = name
    d["meta"]["publish_date"] = date
    (dst / "data.json").write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n",
                                   encoding="utf-8")

    rates = json.loads((ROOT / "rates.json").read_text(encoding="utf-8"))
    yr = date[:4]
    R = rates.get(yr, {})
    (dst / "NOTES.md").write_text(f"""# {name} — 작업 메모

## 시작 전 확인
- [ ] `rates.json` 의 {yr} 값이 최신인가 (요율 {R.get('요율','?')} · 부과점수당 {R.get('재산보험료부과점수당','?')}원)
- [ ] 이 주제가 이미 쓴 글과 겹치지 않는가
- [ ] tier 1 원문(.go.kr / .or.kr)을 직접 열어봤는가

## 순서
1. 원문 확인 → `sources` 채우기
2. `items` — wage 먼저 넣고 금액은 산식으로 계산
3. `flow.scenes` — **자격 → 금액 → 기한 → 신청 방법 → 지금 할 일**
   금액 장면만 채우면 게이트가 막습니다
4. `blog.md` 작성
5. 검사 3종:
   ```
   python3 scripts/check_numbers.py content/{name}
   python3 scripts/lint_terms.py    content/{name}
   python3 scripts/verify.py        content/{name}
   ```
6. 생성:
   ```
   python3 scripts/pipeline.py       content/{name}
   python3 scripts/build_narration.py content/{name}
   python3 scripts/build_publish.py   content/{name}
   ```

## 자주 걸리는 것
- 라벨이 그 화면만 보고 안 통함 (`깎기 전` → `월급 × 7.19%`)
- 음성이 화면 자막을 그대로 읽음
- 등록 용어를 뜻풀이 없이 씀 → `terms.json` 확인
- 작년 요율을 올해라고 씀
""", encoding="utf-8")
    print(f"만들었습니다: content/{name}/")
    print("  data.json  — 템플릿 (필수 필드가 미리 들어 있습니다)")
    print("  NOTES.md   — 순서와 자주 걸리는 것")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
