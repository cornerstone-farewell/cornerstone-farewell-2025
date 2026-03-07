from pathlib import Path
import re

INPUT_FILE = "index.html"
OUTPUT_FILE = "index.fixed.html"


def replace_function(source: str, func_name: str, new_code: str) -> str:
    pattern = re.compile(
        rf"function\s+{re.escape(func_name)}\s*\([^)]*\)\s*\{{",
        re.MULTILINE
    )
    match = pattern.search(source)
    if not match:
        raise ValueError(f"Could not find function: {func_name}")

    start = match.start()
    i = match.end() - 1
    depth = 0
    in_single = False
    in_double = False
    in_template = False
    in_line_comment = False
    in_block_comment = False
    escape = False

    while i < len(source):
        ch = source[i]
        nxt = source[i + 1] if i + 1 < len(source) else ""

        if in_line_comment:
            if ch == "\n":
                in_line_comment = False
            i += 1
            continue

        if in_block_comment:
            if ch == "*" and nxt == "/":
                in_block_comment = False
                i += 2
                continue
            i += 1
            continue

        if in_single:
            if not escape and ch == "\\":
                escape = True
            elif escape:
                escape = False
            elif ch == "'":
                in_single = False
            i += 1
            continue

        if in_double:
            if not escape and ch == "\\":
                escape = True
            elif escape:
                escape = False
            elif ch == '"':
                in_double = False
            i += 1
            continue

        if in_template:
            if not escape and ch == "\\":
                escape = True
                i += 1
                continue
            if escape:
                escape = False
                i += 1
                continue
            if ch == "`":
                in_template = False
                i += 1
                continue
            i += 1
            continue

        if ch == "/" and nxt == "/":
            in_line_comment = True
            i += 2
            continue

        if ch == "/" and nxt == "*":
            in_block_comment = True
            i += 2
            continue

        if ch == "'":
            in_single = True
            i += 1
            continue

        if ch == '"':
            in_double = True
            i += 1
            continue

        if ch == "`":
            in_template = True
            i += 1
            continue

        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                return source[:start] + new_code + source[end:]

        i += 1

    raise ValueError(f"Could not parse function body for: {func_name}")


def remove_block(source: str, start_marker: str, end_marker: str) -> str:
    start = source.find(start_marker)
    if start == -1:
        return source
    end = source.find(end_marker, start)
    if end == -1:
        raise ValueError(f"Could not find end marker after {start_marker!r}")
    return source[:start] + source[end:]


def main():
    html = Path(INPUT_FILE).read_text(encoding="utf-8")

    teacher_row_html = """function teacherRowHtml(t = {}, idx = 0) {
  return `<div class="admin-memory-card" style="padding:12px;">
    <div style="display:flex; justify-content:space-between; align-items:center; gap:10px;">
      <div style="font-weight:800;">Teacher #${idx + 1}</div>
      <button class="admin-btn admin-btn-danger" type="button" onclick="removeTeacherRow(${idx})">Remove</button>
    </div>
    <div style="margin-top:10px; display:grid; grid-template-columns: 1fr 1fr; gap:12px;">
      <div class="form-group">
        <label>Name</label>
        <input class="form-input" data-teacher-field="name" data-teacher-idx="${idx}" value="${escapeAttr(t.name || '')}" />
      </div>
      <div class="form-group">
        <label>Subject</label>
        <input class="form-input" data-teacher-field="subject" data-teacher-idx="${idx}" value="${escapeAttr(t.subject || '')}" />
      </div>
    </div>
    <div class="form-group" style="margin-top:10px;">
      <label>Quote</label>
      <textarea class="form-textarea" data-teacher-field="quote" data-teacher-idx="${idx}" maxlength="250">${escapeHtml(t.quote || '')}</textarea>
    </div>
    <div class="form-group" style="margin-top:10px;">
      <label>Image URL (optional)</label>
      <input class="form-input" data-teacher-field="imageUrl" data-teacher-idx="${idx}" value="${escapeAttr(t.imageUrl || '')}" placeholder="https://..." />
    </div>
  </div>`;
}"""

    timeline_row_html = """function timelineRowHtml(x = {}, idx = 0) {
  return `<div class="admin-memory-card" style="padding:12px;">
    <div style="display:flex; justify-content:space-between; align-items:center; gap:10px;">
      <div style="font-weight:800;">Item #${idx + 1}</div>
      <button class="admin-btn admin-btn-danger" type="button" onclick="removeTimelineRow(${idx})">Remove</button>
    </div>
    <div style="margin-top:10px; display:grid; grid-template-columns: 1fr 1fr; gap:12px;">
      <div class="form-group">
        <label>Year</label>
        <input class="form-input" data-timeline-field="year" data-timeline-idx="${idx}" value="${escapeAttr(x.year || '')}" placeholder="2022" />
      </div>
      <div class="form-group">
        <label>Title</label>
        <input class="form-input" data-timeline-field="title" data-timeline-idx="${idx}" value="${escapeAttr(x.title || '')}" />
      </div>
    </div>
    <div class="form-group" style="margin-top:10px;">
      <label>Description</label>
      <textarea class="form-textarea" data-timeline-field="description" data-timeline-idx="${idx}" maxlength="350">${escapeHtml(x.description || '')}</textarea>
    </div>
  </div>`;
}"""

    html = replace_function(html, "teacherRowHtml", teacher_row_html)
    html = replace_function(html, "timelineRowHtml", timeline_row_html)

    html = remove_block(
        html,
        "function removeSlideFromDraft(index) {",
        "// This forces the compilations to load the second the website opens!"
    )

    Path(OUTPUT_FILE).write_text(html, encoding="utf-8")
    print(f"Fixed file written to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()