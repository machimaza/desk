#!/usr/bin/env python3
"""워크플로 검사 — 두 번 연속 CI 를 죽인 실수를 막습니다.

사고 1 (2026-08-24, exit 2)
  워크플로 표현식으로 여러 줄 값을 for 목록에 직접 넣었습니다.
  목록 안의 줄바꿈이 목록을 끝내 bash 문법 오류가 났습니다.

사고 2 (2026-08-25, Invalid workflow file)
  사고 1을 설명하는 **주석**에 표현식 리터럴을 적었습니다.
  GitHub 은 표현식을 bash 보다 먼저 처리하므로 **주석이 보호해 주지 않습니다.**
  내용이 빈 표현식이라 "An expression was expected" 로 파일 자체가 거부됐습니다.

교훈: 표현식은 YAML 문자열 전체에서 먼저 치환됩니다. bash 문맥은 무의미합니다.
"""
import re, sys, pathlib, subprocess

ROOT = pathlib.Path(__file__).resolve().parent.parent
WF = sorted((ROOT / ".github" / "workflows").glob("*.yml"))

EXPR = re.compile(r"\$\{\{(.*?)\}\}", re.S)
# 표현식으로 인정할 최소 형태 — 식별자·점·괄호·따옴표·연산자
VALID = re.compile(r"^[\w\s.\[\]()'\"!=<>&|,+*/%-]+$")


def check_file(f):
    y = f.read_text(encoding="utf-8")
    bad = []

    # (1) 표현식 자체가 유효한가 — 주석 안이라도 검사합니다
    for m in EXPR.finditer(y):
        inner = m.group(1).strip()
        line = y[:m.start()].count("\n") + 1
        if not inner:
            bad.append(f"L{line}: 빈 표현식 — GitHub 이 파일 전체를 거부합니다. "
                       f"주석 안이어도 마찬가지입니다")
        elif not VALID.match(inner):
            bad.append(f"L{line}: 표현식에 허용되지 않은 문자 — {inner[:40]!r}")

    # (2) for/while 목록에 표현식을 직접 넣지 않았는가
    for m in re.finditer(r"(for\s+\w+\s+in|while)[^\n]*\$\{\{", y):
        line = y[:m.start()].count("\n") + 1
        bad.append(f"L{line}: for/while 목록에 표현식 직접 사용 — "
                   f"여러 줄이면 문법 오류(exit 2). 파일로 넘기세요")

    # (3) run 블록의 bash 문법
    for i, blk in enumerate(re.findall(r"run: \|\n((?:          .*\n|\n)+)", y), 1):
        body = "\n".join(l[10:] for l in blk.split("\n"))
        body = EXPR.sub("EXPR", body)          # 표현식은 치환된 셈 치고 문법만 봅니다
        p = subprocess.run(["bash", "-n"], input=body, capture_output=True, text=True)
        if p.returncode:
            bad.append(f"run#{i}: {p.stderr.strip()[:140]}")
    return bad


def main():
    total = 0
    for f in WF:
        bad = check_file(f)
        total += len(bad)
        if bad:
            for b in bad:
                print(f"  \u2717 {f.name} {b}")
        else:
            print(f"  \u2713 {f.name}")
    print()
    if total:
        print("\U0001F534 워크플로 검사 실패")
        return 1
    print("\U0001F7E2 워크플로 검사 통과")
    return 0


if __name__ == "__main__":
    sys.exit(main())
