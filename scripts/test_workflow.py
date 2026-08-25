#!/usr/bin/env python3
"""워크플로 문법 검사.

2026-08-24 첫 CI 실행이 exit code 2 로 죽었습니다.
원인은 ${{ steps.changed.outputs.dirs }} 가 여러 줄인데 그것을 for 목록에 넣은 것입니다.
목록 안의 줄바꿈이 목록을 끝내 bash 문법 오류가 났습니다.

로컬에서는 명령을 하나씩 실행해봐서 잡히지 않았습니다.
워크플로 파일 자체를 검사해야 잡힙니다.
"""
import re, sys, pathlib, subprocess

ROOT = pathlib.Path(__file__).resolve().parent.parent
WF = sorted((ROOT / ".github" / "workflows").glob("*.yml"))


def main():
    bad = 0
    for f in WF:
        y = f.read_text(encoding="utf-8")
        # ${{ }} 를 for/while 목록에 직접 넣으면 여러 줄일 때 깨집니다.
        for m in re.finditer(r"(for\s+\w+\s+in|while)[^\n]*\$\{\{", y):
            print(f"  \u2717 {f.name}: for/while 목록에 ${{{{ }}}} 직접 사용 "
                  f"— 여러 줄이면 문법 오류(exit 2). 파일로 넘기세요")
            bad += 1
        for i, blk in enumerate(re.findall(r"run: \|\n((?:          .*\n|\n)+)", y), 1):
            body = "\n".join(l[10:] for l in blk.split("\n"))
            if "${{" in body and re.search(r"(for\s+\w+\s+in|while)", body):
                continue
            p = subprocess.run(["bash", "-n"], input=body, capture_output=True, text=True)
            if p.returncode:
                print(f"  \u2717 {f.name} run#{i}: {p.stderr.strip()[:140]}")
                bad += 1
        if not bad:
            print(f"  \u2713 {f.name}")
    print()
    if bad:
        print("\U0001F534 워크플로 문법 검사 실패")
        return 1
    print("\U0001F7E2 워크플로 문법 검사 통과")
    return 0


if __name__ == "__main__":
    sys.exit(main())
