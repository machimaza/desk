# machimaza — 실행 가이드

한국 생활·행정 정보를 **글 · 카드 · 쇼츠** 세 형태로 만들어 여섯 채널에 올립니다.
왜 그렇게 하는지, 무엇을 지켜야 하는지는 전부 **[`CLAUDE.md`](CLAUDE.md)** 에 있습니다.
이 파일은 "손을 어디에 두는가"만 적습니다.

```bash
pip install -r requirements.txt --break-system-packages   # 최초 1회
python3 -m playwright install chromium                    # 최초 1회
```

필요: Python 3.10+, ffmpeg, Noto Sans CJK KR 폰트.

## 한 건 만들기

```bash
python3 scripts/new_content.py <슬러그>          # 폴더 + 템플릿
# ── data.json 을 채웁니다. 숫자는 rates.json 에서만 옵니다 ──
python3 scripts/check_numbers.py content/<폴더>   # 수치 정합성
python3 scripts/lint_terms.py   content/<폴더>   # 용어 뜻풀이
python3 scripts/verify.py       content/<폴더>   # 게이트 판정 ★
python3 scripts/make_images.py  content/<폴더>   # 포스터 + 카드
```

**🔴이면 발행하지 않습니다.** 기준을 낮추거나 코드를 고쳐 통과시키지 않습니다.

## 음성 · 영상 · 발행 — Actions 에서

이 컨테이너는 프록시가 TTS 를 끊습니다. **러너에서만** 만들어집니다.

| 하는 일 | 어디서 |
|---|---|
| 나레이션 + 배경음 + 영상 | Actions → **음성·영상** → `build` |
| 목소리 후보 듣기 | Actions → **음성·영상** → `samples` |
| 유튜브·쓰레드 발행 | Actions → **발행** |

**발행은 기본이 미리보기입니다.** `publish: true` 를 켜야 실제로 올라갑니다.
티스토리·네이버는 약관상 자동화하지 않습니다 — 발행 키트를 만들어 손으로 올립니다.

## 디자인 바꾸기

색은 [`brand/tokens.css`](brand/tokens.css) 가 기준값입니다.
렌더러(`motion.py` · `pipeline.py`)는 같은 값을 각자 갖고 있고,
어긋나면 `scripts/test_brand.py` 가 CI 를 멈춥니다. **새 색은 여기에 먼저 넣으세요.**

여백·글자 크기는 유튜브 안전영역에 묶여 있습니다 — `CLAUDE.md` §9 를 먼저 읽으세요.

## 설정 문서

| 문서 | 내용 |
|---|---|
| [`VOICE_SETUP.md`](VOICE_SETUP.md) | Azure Speech 키 발급 |
| [`BGM.md`](BGM.md) | 저작권 깨끗한 배경음·알림음 고르는 곳 |
| [`YOUTUBE_SETUP.md`](YOUTUBE_SETUP.md) | 유튜브 OAuth (한 번만) |
| [`PUBLISH_AUTO.md`](PUBLISH_AUTO.md) | 쓰레드 자동 발행 |
| [`PUBLISH.md`](PUBLISH.md) | 손으로 올리는 순서 |

**열쇠는 전부 GitHub Secrets 에 둡니다.** 저장소가 공개라 더더욱 —
키를 채팅이나 파일에 붙여넣지 마세요.
