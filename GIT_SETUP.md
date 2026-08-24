# GitHub 연결 (사용자 PC에서 1회)

이 폴더는 **이미 git 저장소**입니다. 커밋 2개가 들어 있습니다.
원격만 붙이면 끝입니다.

## 1. GitHub에서 빈 저장소 생성

- 이름: `machimaza`
- **Private 권장** (콘텐츠 전략이 공개될 이유가 없습니다)
- README·.gitignore·라이선스 **추가하지 않음** (이미 있습니다 — 충돌 방지)

## 2. 원격 연결 후 push

```bash
cd machimaza
git remote add origin https://github.com/<사용자명>/machimaza.git
git push -u origin main
```

## 3. Actions 권한 켜기

`Settings → Actions → General → Workflow permissions`
→ **Read and write permissions** 선택 (노후화 스캔이 이슈를 생성하려면 필요)

## 4. 확인

- `Actions` 탭에 워크플로 2개가 보이면 성공
- `노후화 스캔` 을 수동 실행(`Run workflow`)해 동작 확인

---

## 다음 세션에서 이어받기

```bash
git clone https://github.com/<사용자명>/machimaza.git
```

또는 코워크에서 이 저장소 zip을 올리면 그대로 이어집니다.

## 번들로 받은 경우

`machimaza.bundle` 파일 하나에 전체 이력이 들어 있습니다.

```bash
git clone machimaza.bundle machimaza
cd machimaza
git remote set-url origin https://github.com/<사용자명>/machimaza.git
git push -u origin main
```

---

## 작업 흐름

```bash
git switch -c draft/2026-09-20-독감백신     # 제작 시작
# data.json 작성 → 커밋 → push
# → Actions 가 이미지·영상 생성 후 게이트 11항목 자동 판정
# → 초록불이면 main 에 머지 → 발행
```

**게이트 통과가 머지 조건입니다.** "검수를 깜빡한다"가 구조적으로 불가능해집니다.
