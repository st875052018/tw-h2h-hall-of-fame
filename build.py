"""把 page_data.json 塞進 template.html，產生 index.html（GitHub Pages 直接用）。"""
import json
from pathlib import Path

here = Path(__file__).parent
data = json.loads((here / "page_data.json").read_text())
html = (here / "template.html").read_text().replace("__DATA__", json.dumps(data, ensure_ascii=False), 1)
(here / "index.html").write_text(html)
print("index.html", len(html))
