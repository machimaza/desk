"""콘텐츠 노후화 레이더 — 전체 content/ 를 훑어 갱신 대상을 뽑습니다.

YMYL에서 낡은 정보는 없는 정보보다 나쁩니다.
갱신은 신규보다 싸고(구조·출처·이미지 재사용), 구글이 더 빨리 올려줍니다.
"""
import json, pathlib, datetime as dt, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
WARN_DAYS, STALE_DAYS = 365, 730

def main():
    today = dt.date.today()
    rows = []
    for dj in sorted(ROOT.glob("content/*/data.json")):
        if dj.parent.name.startswith("_"):
            continue
        try:
            d = json.loads(dj.read_text(encoding="utf-8"))
        except Exception as e:
            rows.append((999, dj.parent.name, "-", f"data.json 파싱 실패: {e}")); continue
        for s in d.get("sources", []):
            try:
                eff = dt.date.fromisoformat(s["effective_date"])
            except Exception:
                rows.append((900, dj.parent.name, s.get("id","?"),
                             f"시행일 형식 오류: {s.get('effective_date')}")); continue
            age = (today - eff).days
            if age > STALE_DAYS:
                rows.append((age, dj.parent.name, s["id"],
                             f"🔴 {age}일 경과 ({eff}) · {s['issuer']} · {s['url']}"))
            elif age > WARN_DAYS:
                rows.append((age, dj.parent.name, s["id"],
                             f"🟡 {age}일 경과 ({eff}) · {s['issuer']}"))
    rows.sort(reverse=True)
    if not rows:
        print("갱신이 필요한 콘텐츠가 없습니다."); return 0
    print(f"# 콘텐츠 노후화 스캔 ({today})\n")
    print(f"갱신 검토 대상 **{len(rows)}건**\n")
    print("| 경과 | 콘텐츠 | 출처 | 상태 |")
    print("|---|---|---|---|")
    for age, name, sid, msg in rows:
        print(f"| {age}일 | `{name}` | {sid} | {msg} |")
    print("\n> 갱신은 신규 제작보다 쌉니다. 숫자만 바꾸면 되고, 구글은 갱신 문서를 더 빨리 올려줍니다.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
