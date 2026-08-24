# machimaza 파이프라인 실행 가이드

```bash
pip install playwright --break-system-packages   # 최초 1회
python3 -m playwright install chromium           # 최초 1회 (로컬 환경만)

# 한 건 만들기
python3 scripts/make_images.py content/2026-08-26-주제명   # → images/  (pipeline.py 위임)
python3 scripts/test_check_numbers.py                         # 수치 게이트 회귀 테스트
# 영상은 CLAUDE.md 9장에 따라 실제 모션 구현 전까지 생성하지 않습니다
python3 scripts/verify.py      content/2026-08-26-주제명   # → 게이트 판정
```

필요: Python 3.10+, ffmpeg, Noto Sans CJK KR 폰트.

## 새 콘텐츠 시작하기
1. `content/YYYY-MM-DD-주제명/` 생성
2. 리서치 후 `data.json` 작성 (`schema/data.schema.json` 준수)
3. 위 3개 명령 실행
4. 게이트 🟢 확인 후 발행

## 디자인 바꾸기
색·폰트·간격은 전부 `brand/tokens.css` 한 파일에 있습니다.
여기를 고치면 포스터·카드·영상이 동시에 바뀝니다.
