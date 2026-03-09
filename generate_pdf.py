from weasyprint import HTML
import html

INPUT_HTML = "index.html"
INPUT_JS = "server.js"
OUTPUT_FILE = "html_code.pdf"

# read html file
with open(INPUT_HTML, "r", encoding="utf-8") as f:
    html_code = f.read()

# read js file
with open(INPUT_JS, "r", encoding="utf-8") as f:
    js_code = f.read()

# escape code so it prints as text
escaped_html = html.escape(html_code)
escaped_js = html.escape(js_code)

document = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
body {{
    font-size: 1pt;
    font-family: monospace;
}}

pre {{
    white-space: pre-wrap;
    word-break: break-word;
}}

.separator {{
    margin-top: 20px;
    margin-bottom: 20px;
}}
</style>
</head>
<body>

<h3>index.html</h3>
<pre>{escaped_html}</pre>

<div class="separator">
<hr>
</div>

<h3>server.js</h3>
<pre>{escaped_js}</pre>

</body>
</html>
"""

HTML(string=document).write_pdf(OUTPUT_FILE)

print("PDF created:", OUTPUT_FILE)