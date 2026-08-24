"""HTML -> PNG 렌더 공용 모듈. 모든 이미지는 이 경로로만 생성됩니다."""
import pathlib, json, re
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent
TOKENS = (ROOT / "brand" / "tokens.css").read_text(encoding="utf-8")

def fill(template_name: str, mapping: dict) -> str:
    html = (ROOT / "templates" / template_name).read_text(encoding="utf-8")
    html = html.replace("__TOKENS__", TOKENS)
    for k, v in mapping.items():
        html = html.replace(f"__{k}__", str(v))
    return re.sub(r"__[A-Z0-9_]+__", "", html)   # 미사용 슬롯 제거

def shoot(pages, outdir: pathlib.Path, w: int, h: int):
    """pages: [(filename, html), ...]"""
    outdir.mkdir(parents=True, exist_ok=True)
    written = []
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": w, "height": h}, device_scale_factor=1)
        for name, html in pages:
            pg.set_content(html, wait_until="load")
            pg.wait_for_timeout(120)
            path = outdir / name
            pg.screenshot(path=str(path), clip={"x":0,"y":0,"width":w,"height":h})
            written.append(path)
        b.close()
    return written

def autosize(text: str, base: int, per_char: float, floor: int) -> int:
    """글자 수에 따라 폰트 크기를 줄여 오버플로를 막습니다."""
    return max(floor, int(base - max(0, len(text)) * per_char))

def load(data_path) -> dict:
    return json.loads(pathlib.Path(data_path).read_text(encoding="utf-8"))
