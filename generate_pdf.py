from weasyprint import HTML

INPUT_FILE = "index.html"
OUTPUT_FILE = "html_code.pdf"

with open(INPUT_FILE, "r", encoding="utf-8") as f:
    code = f.read()

# escape HTML so it prints as text
import html
escaped_code = html.escape(code)

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
</style>
</head>
<body>
<pre>{escaped_code}</pre>
</body>
</html>
"""

HTML(string=document).write_pdf(OUTPUT_FILE)

print("PDF created:", OUTPUT_FILE)