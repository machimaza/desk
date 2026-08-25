#!/usr/bin/env python3
"""원격 저장소가 로컬과 글자 하나까지 같은지 확인합니다.

커넥터(REST API)로 파일을 올릴 때는 내용을 통째로 다시 써 넣습니다.
사람이나 모델이 옮겨 적는 순간 글자가 바뀔 수 있고, 바뀌어도 아무 오류가 나지 않습니다.
실제로 build_voice.py 의 "장면보다 김" 이 "장면보다 길" 로 바뀐 채 올라간 적이 있습니다.

git 의 blob 해시를 양쪽에서 비교하면 그 사고가 조용히 지나가지 못합니다.
raw.githubusercontent.com 은 CDN 캐시라 방금 올린 내용이 늦게 보입니다.
그래서 여기서는 raw 를 쓰지 않고 git 이 받아온 객체를 봅니다.

  python scripts/check_remote.py
  python scripts/check_remote.py CLAUDE.md scripts/build_voice.py
"""
import subprocess
import sys

REMOTE, BRANCH = "origin", "main"


def run(*args):
    r = subprocess.run(args, capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(f"{' '.join(args)} 실패\n{r.stderr.strip()}")
    return r.stdout


def blobs(ref):
    out = run("git", "ls-tree", "-r", ref, "--format=%(objectname)\t%(path)")
    return dict(
        (path, sha)
        for sha, path in (line.split("\t", 1) for line in out.splitlines() if line)
    )


def main(argv):
    want = argv[1:]
    run("git", "fetch", "-q", REMOTE, BRANCH)
    local, remote = blobs("HEAD"), blobs("FETCH_HEAD")

    if want:
        local = {p: local.get(p) for p in want}

    missing, differs = [], []
    for path, sha in sorted(local.items()):
        if sha is None:
            print(f"  ? {path} — 로컬에서 추적되지 않는 경로")
            missing.append(path)
        elif path not in remote:
            print(f"  ✗ {path} — 원격에 없음 (아직 안 올렸습니다)")
            missing.append(path)
        elif remote[path] != sha:
            print(f"  ✗ {path}")
            print(f"      로컬 {sha}")
            print(f"      원격 {remote[path]}")
            differs.append(path)

    extra = [] if want else sorted(set(remote) - set(local))
    for path in extra:
        print(f"  ! {path} — 원격에만 있음")

    if missing or differs or extra:
        print(f"\n{len(local)}개 중 {len(missing) + len(differs)}개가 원격과 다릅니다.")
        if differs:
            print("내용이 다른 파일은 올릴 때 글자가 바뀌었을 수 있습니다. 원본을 다시 올리세요.")
        return 1
    print(f"✓ {len(local)}개 파일이 원격과 동일합니다.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
