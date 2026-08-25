# 음성 키 만들기 — Azure Speech

한국어 음성 열 개를 전부 쓰려면 키가 하나 필요합니다.
무료 등급(F0)은 **월 50만 자**까지 공짜입니다. 우리 분량으로 환산하면

- 영상 한 편 나레이션 ≈ 200~250자
- 월 50만 자 ÷ 250자 = **월 2,000편**

하루 한 편씩 올려도 한도의 1.5% 를 씁니다. 넘길 일이 없습니다.

키는 **저장소에 적지 않습니다.** GitHub Secrets 에 넣고 러너가 환경변수로만 받습니다.
이 저장소는 공개라 더더욱 그렇습니다.

---

## 1단계 — Azure 계정

<https://azure.microsoft.com/free> 에서 가입합니다.

- 카드 등록이 필요합니다. **F0 등급은 과금되지 않습니다.**
- 무료 체험 크레딧과 별개로, F0 는 기간 제한 없이 매달 초기화됩니다.

## 2단계 — Speech 리소스 만들기

포털(<https://portal.azure.com>)에서 **리소스 만들기 → Speech** 를 찾습니다.

| 칸 | 넣을 값 |
|---|---|
| 구독 | 방금 만든 것 |
| 리소스 그룹 | 새로 만들기 · 이름은 `machimaza` |
| 지역 | **Korea Central** |
| 이름 | `machimaza-voice` |
| 가격 책정 계층 | **Free F0** ← 이걸 꼭 확인하세요 |

`Free F0` 가 안 보이면 그 구독에 이미 F0 가 하나 있는 겁니다 (구독당 하나).

## 3단계 — 키 복사

만들어진 리소스에서 **키 및 엔드포인트** 를 엽니다.

- `키 1` 을 복사합니다 (32자리)
- `위치/지역` 도 적어둡니다 — Korea Central 이면 `koreacentral`

키는 비밀번호와 같습니다. 화면 공유나 채팅에 붙여넣지 마세요.

## 4단계 — GitHub Secrets 에 넣기

<https://github.com/machimaza/desk/settings/secrets/actions>

**New repository secret** 을 눌러 **두 개** 만듭니다.

| Name | Secret |
|---|---|
| `AZURE_SPEECH_KEY` | 복사한 키 1 |
| `AZURE_SPEECH_REGION` | `koreacentral` |

이름을 정확히 이대로 써야 합니다. 대소문자도 같아야 합니다.

한 번 넣으면 **다시 볼 수 없습니다.** 값이 필요하면 Azure 포털에서 다시 복사하면 됩니다.

## 5단계 — 확인

Actions → **음성·영상** → Run workflow

- `mode` = `samples`
- `samples` = `korean`
- `engine` = **`azure`**

돌린 뒤 로그의 "한국어 음성 목록"에 **열 개**가 나오면 성공입니다.
세 개만 나오면 키가 안 붙은 겁니다.

---

## 문제가 생기면

| 증상 | 원인 |
|---|---|
| `Azure 응답 401` | 키가 틀렸거나 Secrets 이름이 다릅니다 |
| `Azure 응답 403` | 지역이 다르거나 월 한도를 넘겼습니다 |
| `Azure 응답 400` | 음성 이름 오타 — `ko-KR-SeoHyeonNeural` 처럼 정확히 |
| 음성이 세 개만 나옴 | `engine` 을 `azure` 로 안 골랐거나 키가 비었습니다 |

## 키 없이 쓰던 길도 그대로입니다

`engine` 을 `edge` 로 두면 예전처럼 무료로 돕니다. 한국어는 세 개뿐이지만
키가 막히거나 한도를 넘겼을 때 돌아갈 자리가 됩니다.
