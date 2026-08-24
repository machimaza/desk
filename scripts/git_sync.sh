#!/usr/bin/env bash
# 토큰을 .git/config 에 남기지 않고 push 합니다.
# 사용: GH_TOKEN=xxx GH_USER=xxx GH_REPO=machimaza ./scripts/git_sync.sh [브랜치]
set -euo pipefail
: "${GH_TOKEN:?GH_TOKEN 환경변수 필요}"
: "${GH_USER:?GH_USER 환경변수 필요}"
REPO="${GH_REPO:-machimaza}"
BRANCH="${1:-$(git rev-parse --abbrev-ref HEAD)}"
URL="https://x-access-token:${GH_TOKEN}@github.com/${GH_USER}/${REPO}.git"

# 원격은 토큰 없는 URL 로만 저장합니다 (.git/config 유출 방지)
git remote get-url origin >/dev/null 2>&1 \
  && git remote set-url origin "https://github.com/${GH_USER}/${REPO}.git" \
  || git remote add origin "https://github.com/${GH_USER}/${REPO}.git"

git push "$URL" "$BRANCH" "$@" 2>&1 | sed "s|${GH_TOKEN}|***|g"
echo "push 완료: ${GH_USER}/${REPO} @ ${BRANCH}"
