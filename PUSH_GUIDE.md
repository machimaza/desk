# GitHub 푸시 방법 — 바탕화면 `machimaza.bundle`

번들 하나에 커밋 33개가 전부 들어 있습니다.
저장소는 지금까지 클라우드 컨테이너에만 있었고, PC에는 처음 내려가는 것입니다.

---

## 0. 먼저 할 일 — 이전 토큰 폐기

대화 중에 만드신 개인 액세스 토큰(`github_pat_11AU54…`)이 채팅 기록에 남아 있고,
만료 없음으로 설정하셨습니다. **지금 폐기하세요.**

`github.com` → 우측 상단 프로필 → **Settings** → 맨 아래 **Developer settings**
→ **Personal access tokens** → **Fine-grained tokens** → 해당 토큰 → **Delete**

아래 방법들은 토큰이 필요 없습니다.

---

## 방법 A — GitHub Desktop (권장, 명령어 없음)

가장 간단합니다. 인증도 알아서 처리됩니다.

1. `desktop.github.com` 에서 설치 후 GitHub 계정으로 로그인
2. 상단 메뉴 **File → Clone repository → URL** 탭
3. 아래처럼 입력
   - Repository URL: `C:\Users\최현우\Desktop\machimaza.bundle`
   - Local path: `C:\Users\최현우\Desktop\machimaza`
4. **Clone** 클릭 → 커밋 33개가 그대로 들어옵니다
5. 상단 **Repository → Repository settings → Remote**
   - Primary remote repository(origin)를 `https://github.com/machimaza/desk.git` 로 변경 → Save
6. 상단 **Push origin** 클릭

끝입니다.

---

## 방법 B — 명령어 (Git 설치되어 있으면)

PowerShell 을 열고 (시작 → `powershell` 입력) 아래를 **한 줄씩** 실행합니다.

### 1) 번들에서 저장소 복원

```powershell
cd $HOME\Desktop
git clone machimaza.bundle machimaza
cd machimaza
```

`Cloning into 'machimaza'...` 가 뜨고 폴더가 생기면 성공입니다.

### 2) 원격 주소를 GitHub 로 변경

번들에서 복원하면 origin 이 번들 파일을 가리킵니다. 실제 저장소로 바꿔줍니다.

```powershell
git remote set-url origin https://github.com/machimaza/desk.git
git remote -v
```

`origin  https://github.com/machimaza/desk.git (fetch)` 가 보이면 됩니다.

### 3) 푸시

```powershell
git push -u origin main
```

브라우저 창이 뜨면서 GitHub 로그인을 요구합니다.
**Windows 용 Git 에 포함된 Credential Manager 가 처리하므로 토큰을 직접 입력할 필요가 없습니다.**
한 번 로그인하면 다음부터는 묻지 않습니다.

---

## 확인

`github.com/machimaza/desk` 에 접속해서 아래가 보이면 완료입니다.

- 커밋 33개
- `CLAUDE.md` · `rates.json` · `terms.json` · `style.json` · `categories.json`
- `scripts/` 아래 검사기 6종
- `content/` 아래 글 2편

그리고 **Actions** 탭에 「검수 게이트」 워크플로가 자동으로 실행됩니다.
초록색이면 검사기가 CI 에서도 정상 동작하는 것입니다.

---

## 자주 막히는 곳

| 증상 | 원인과 해결 |
|---|---|
| `git: 명령을 찾을 수 없습니다` | Git 미설치. `git-scm.com` 에서 설치하거나 방법 A 사용 |
| `Repository not found` | 저장소가 없거나 다른 계정. `github.com/machimaza/desk` 접속해 확인 |
| `refusing to merge unrelated histories` | GitHub 쪽에 이미 커밋이 있는 경우. **저장소가 비어 있어야 합니다.** README 를 자동 생성했다면 GitHub 에서 삭제 후 다시 푸시 |
| 브라우저 로그인 창이 안 뜸 | `git config --global credential.helper manager` 실행 후 재시도 |
| `main` 브랜치가 없다고 함 | `git branch -M main` 실행 후 재시도 |

---

## 다음부터

한 번 연결되면 그다음은 이 폴더에서 작업하시면 됩니다.

```powershell
cd $HOME\Desktop\machimaza
git pull            # 최신 받기
git add -A
git commit -m "메시지"
git push            # 올리기
```

이 세션에서 만든 새 내용은 매번 번들로 다시 전달드립니다.
