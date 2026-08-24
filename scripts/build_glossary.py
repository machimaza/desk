"""terms.json → 용어 사전 페이지(HTML).

손으로 쓰지 않고 원장에서 생성합니다. 숫자는 rates.json, 용어는 terms.json이
유일한 출처라는 규칙을 문서 생성에도 그대로 적용합니다.

디자인 근거
  법조문의 언어(명조)와 말의 언어(고딕)를 서체로 갈라놓았습니다.
  이 사전이 하는 일 자체가 그 둘 사이를 옮기는 것이므로,
  서체 대비가 곧 내용입니다. 인용 조문은 등폭으로 두어 '출처' 층을 분리했습니다.
  레이아웃은 둥근 카드가 아니라 법령 '별표'의 괘선 장부를 따랐습니다.

사용:  python3 scripts/build_glossary.py [출력경로]
"""
import json, sys, html, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
T = json.loads((ROOT / "terms.json").read_text(encoding="utf-8"))
TERMS = T["용어"]

CSS = """
:root{
  --paper:#F6F7F9; --raise:#FFFFFF; --ink:#171A20; --ink-2:#5C6572;
  --rule:#D6DBE3; --rule-soft:#E6EAEF;
  --accent:#1B5FA8; --risk:#9E4429; --risk-bg:#F3E7E2;
}
@media (prefers-color-scheme:dark){
  :root:not([data-theme="light"]){
    --paper:#111419; --raise:#171B21; --ink:#E3E7ED; --ink-2:#98A2B0;
    --rule:#262C35; --rule-soft:#1D222A;
    --accent:#78ADDD; --risk:#D08C72; --risk-bg:#2A1D18;
  }
}
:root[data-theme="dark"]{
  --paper:#111419; --raise:#171B21; --ink:#E3E7ED; --ink-2:#98A2B0;
  --rule:#262C35; --rule-soft:#1D222A;
  --accent:#78ADDD; --risk:#D08C72; --risk-bg:#2A1D18;
}
*{box-sizing:border-box}
body{
  margin:0; background:var(--paper); color:var(--ink);
  font-family:"IBM Plex Sans KR","Apple SD Gothic Neo",system-ui,sans-serif;
  font-size:16px; line-height:1.7; -webkit-text-size-adjust:100%;
}
.wrap{max-width:44rem; margin:0 auto; padding:2.5rem 1.25rem 4rem}
header{border-bottom:2px solid var(--ink); padding-bottom:1.25rem; margin-bottom:.5rem}
.eyebrow{
  font-family:"IBM Plex Mono",ui-monospace,monospace;
  font-size:.7rem; letter-spacing:.14em; text-transform:uppercase;
  color:var(--ink-2); margin:0 0 .6rem;
}
h1{
  font-family:"Noto Serif KR",serif; font-weight:600;
  font-size:clamp(1.6rem,5.5vw,2.1rem); line-height:1.3;
  margin:0; text-wrap:balance;
}
.lede{margin:.9rem 0 0; color:var(--ink-2); font-size:.95rem}
.rule-note{
  margin:1.5rem 0 2.25rem; padding:.9rem 1rem;
  background:var(--raise); border:1px solid var(--rule-soft);
  border-left:3px solid var(--accent);
  font-size:.87rem; color:var(--ink-2);
}
.rule-note b{color:var(--ink); font-weight:600}
.count{
  display:flex; gap:1.25rem; flex-wrap:wrap;
  font-family:"IBM Plex Mono",ui-monospace,monospace;
  font-size:.72rem; letter-spacing:.06em; color:var(--ink-2);
  border-top:1px solid var(--rule); border-bottom:1px solid var(--rule);
  padding:.6rem 0; margin-bottom:2rem;
}
.count b{color:var(--ink); font-variant-numeric:tabular-nums}

/* 법령 별표의 괘선 장부 — 둥근 카드가 아니라 줄로 나눕니다 */
.ledger{display:flex; flex-direction:column}
.entry{border-top:1px solid var(--rule); padding:1.6rem 0}
.entry:last-child{border-bottom:1px solid var(--rule)}
.term{
  font-family:"Noto Serif KR",serif; font-weight:600;
  font-size:1.35rem; line-height:1.35; margin:0;
  display:flex; align-items:baseline; gap:.6rem; flex-wrap:wrap;
}
.risk-tag{
  font-family:"IBM Plex Mono",ui-monospace,monospace;
  font-size:.65rem; letter-spacing:.1em; font-weight:500;
  color:var(--risk); background:var(--risk-bg);
  padding:.18rem .45rem; white-space:nowrap;
}
.gloss{margin:.55rem 0 0; font-size:1rem}
.risk{
  margin:.75rem 0 0; padding-left:.85rem;
  border-left:2px solid var(--risk); color:var(--ink-2); font-size:.88rem;
}
.risk b{color:var(--risk); font-weight:600}
.pending{
  margin:.75rem 0 0; padding:.5rem .7rem; background:var(--risk-bg);
  color:var(--ink-2); font-size:.82rem;
}
dl.meta{
  margin:1rem 0 0; display:grid; grid-template-columns:5.5rem 1fr;
  gap:.3rem .9rem; font-size:.82rem;
}
dl.meta dt{
  font-family:"IBM Plex Mono",ui-monospace,monospace;
  font-size:.68rem; letter-spacing:.08em; color:var(--ink-2);
  padding-top:.24rem;
}
dl.meta dd{margin:0; color:var(--ink)}
dl.meta dd.src{
  font-family:"IBM Plex Mono",ui-monospace,monospace;
  font-size:.76rem; color:var(--ink-2); line-height:1.55;
}
footer{
  margin-top:3rem; padding-top:1.25rem; border-top:1px solid var(--rule);
  font-size:.8rem; color:var(--ink-2);
}
footer p{margin:.4rem 0}
@media (min-width:38rem){
  dl.meta{grid-template-columns:6.5rem 1fr}
}
"""


def entry(name, s):
    risky = bool(s.get("오독위험"))
    tag = '<span class="risk-tag">오독 주의</span>' if risky else ""
    out = [f'<article class="entry">',
           f'<h2 class="term">{html.escape(s["표기"])}{tag}</h2>',
           f'<p class="gloss">{html.escape(s["뜻"])}</p>']
    if risky:
        out.append(f'<p class="risk"><b>왜 헷갈리나</b> — {html.escape(s["오독위험"])}</p>')
    if s.get("확인필요"):
        out.append(f'<p class="pending">아직 확인 못 한 것 — {html.escape(s["확인필요"])}</p>')
    out.append('<dl class="meta">')
    out.append(f'<dt>카드</dt><dd>{html.escape(s["카드"])}</dd>')
    out.append(f'<dt>음성</dt><dd>{html.escape(s["나레이션"])}</dd>')
    out.append(f'<dt>근거</dt><dd class="src">{html.escape(s["근거"])}</dd>')
    out.append('</dl></article>')
    return "\n".join(out)


def build():
    risky = sum(1 for s in TERMS.values() if s.get("오독위험"))
    pending = sum(1 for s in TERMS.values() if s.get("확인필요"))
    body = "\n".join(entry(k, v) for k, v in TERMS.items())
    return f"""<title>마치마자 용어 사전</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Noto+Serif+KR:wght@500;600&family=IBM+Plex+Sans+KR:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>{CSS}</style>
<div class="wrap">
<header>
  <p class="eyebrow">마치마자 · 건강보험료</p>
  <h1>고지서에 적힌 말, 뜻은 이렇습니다</h1>
  <p class="lede">건강보험 관련 글에 쓰는 제도 용어를 한곳에 모았습니다.
  법이 쓰는 표기를 앞에, 쉬운 말을 괄호에 뒀습니다 —
  고지서에서 만날 단어를 못 알아보면 정작 본인 고지서를 못 읽기 때문입니다.</p>
</header>

<p class="rule-note"><b>이 사전을 만든 이유.</b>
「섬·벽지 거주 50%」를 표에 그대로 넣고 발행 직전까지 갔습니다.
법조문조차 <b>섬·벽지(僻地)</b>라고 한자를 병기하는 단어인데,
그 괄호를 떼서 원문보다 불친절한 글을 만든 셈이었습니다.
지금은 등록된 용어가 본문에 처음 나올 때 뜻풀이가 없으면 발행 자체가 막힙니다.</p>

<div class="count">
  <span>등록 용어 <b>{len(TERMS)}</b></span>
  <span>오독 주의 <b>{risky}</b></span>
  <span>확인 대기 <b>{pending}</b></span>
</div>

<div class="ledger">
{body}
</div>

<footer>
  <p>표기·뜻·근거는 <code>terms.json</code> 한 곳에서만 관리하며, 이 페이지는 거기서 생성됩니다.</p>
  <p>수치가 아닌 용어만 다룹니다. 보험료 금액과 요율은 각 글의 원문 출처를 확인하세요.</p>
  <p>— 마치마자 · 정부·공공기관 원문을 직접 확인해 정리하며, 제도 개정 시 갱신합니다.</p>
</footer>
</div>
"""


if __name__ == "__main__":
    out = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ROOT / "glossary.html")
    out.write_text(build(), encoding="utf-8")
    print(f"{out} — 용어 {len(TERMS)}건")
