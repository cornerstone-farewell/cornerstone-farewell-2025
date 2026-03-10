from weasyprint import HTML
from pathlib import Path
import html

INPUT_HTML = "index.html"
INPUT_JS = "server.js"
OUTPUT_FILE = "html_code.pdf"


def read_file(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def add_file_block(parts: list[str], title: str, content: str) -> None:
    escaped = html.escape(content)
    parts.append(f"<h3>{html.escape(title)}</h3>")
    parts.append(f"<pre>{escaped}</pre>")
    parts.append('<div class="separator"><hr></div>')


html_path = Path(INPUT_HTML)
js_path = Path(INPUT_JS)

document_parts = [
    """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
body {
    font-size: 1pt;
    font-family: monospace;
}

pre {
    white-space: pre-wrap;
    word-break: break-word;
}

.separator {
    margin-top: 20px;
    margin-bottom: 20px;
}
</style>
</head>
<body>
"""
]

if html_path.exists():
    add_file_block(document_parts, html_path.name, read_file(html_path))
else:
    add_file_block(document_parts, html_path.name, "FILE NOT FOUND")

if js_path.exists():
    add_file_block(document_parts, js_path.name, read_file(js_path))
else:
    add_file_block(document_parts, js_path.name, "FILE NOT FOUND")

document_parts.append("</body></html>")
document = "\n".join(document_parts)

HTML(string=document).write_pdf(OUTPUT_FILE)

print("PDF created:", OUTPUT_FILE)