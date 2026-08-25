# 2026-08-25-근로장려금-반기신청 — 작업 메모

## 시작 전 확인
- [ ] `rates.json` 의 2026 값이 최신인가 (요율 0.0719 · 부과점수당 211.5원)
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
   python3 scripts/check_numbers.py content/2026-08-25-근로장려금-반기신청
   python3 scripts/lint_terms.py    content/2026-08-25-근로장려금-반기신청
   python3 scripts/verify.py        content/2026-08-25-근로장려금-반기신청
   ```
6. 생성:
   ```
   python3 scripts/pipeline.py       content/2026-08-25-근로장려금-반기신청
   python3 scripts/build_narration.py content/2026-08-25-근로장려금-반기신청
   python3 scripts/build_publish.py   content/2026-08-25-근로장려금-반기신청
   ```

## 자주 걸리는 것
- 라벨이 그 화면만 보고 안 통함 (`깎기 전` → `월급 × 7.19%`)
- 음성이 화면 자막을 그대로 읽음
- 등록 용어를 뜻풀이 없이 씀 → `terms.json` 확인
- 작년 요율을 올해라고 씀
