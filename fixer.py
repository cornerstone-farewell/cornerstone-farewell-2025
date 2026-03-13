#!/usr/bin/env python3
from __future__ import annotations

import re
import shutil
from pathlib import Path
from datetime import datetime

ROOT = Path.cwd()

FILES = {
    "admin_nav": ROOT / "fragments" / "admin" / "admin_navbar_top.html",
    "funfeatures": ROOT / "fragments" / "admin" / "funfeatures.html",
    "compilations_admin": ROOT / "fragments" / "admin" / "compilations.html",
    "index_template": ROOT / "index.template.html",
    "teachers_admin": ROOT / "fragments" / "admin" / "teachers.html",
    "moderation": ROOT / "fragments" / "admin" / "moderation.html",
    "students": ROOT / "fragments" / "admin" / "students.html",
    "server": ROOT / "server.js",
}


def backup_file(path: Path) -> None:
    if not path.exists():
        return
    backup_dir = path.parent / "_backups_sniper"
    backup_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    shutil.copy2(path, backup_dir / f"{path.name}.{ts}.bak")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8", newline="\n")


def fail(msg: str) -> None:
    raise RuntimeError(msg)


def remove_gmail_garbage(text: str) -> str:
    markers = [
        "Skip to content\nUsing Gmail with screen readers",
        "Conversations\n65% of 15 GB used",
        "Last account activity:",
        "Displaying moderations.html.",
    ]
    changed = False
    for marker in markers:
        if marker in text:
            changed = True
            text = text.replace(marker, "")
    # remove leading junk before first fragment/style/script/comment
    first_positions = []
    for token in ["<!--", "<style", "<script", "<section", "<div"]:
        idx = text.find(token)
        if idx != -1:
            first_positions.append(idx)
    if first_positions:
        first = min(first_positions)
        prefix = text[:first]
        if "Gmail" in prefix or "Skip to content" in prefix or "Conversations" in prefix:
            text = text[first:]
            changed = True
    return text.strip() + "\n" if changed else text


def patch_admin_navbar() -> None:
    path = FILES["admin_nav"]
    if not path.exists():
        fail(f"Missing file: {path}")
    text = read_text(path)

    # Remove duplicate .admin-content block; keep slim one
    text = re.sub(
        r"\n\.admin-content\s*\{\s*padding:\s*20px;\s*background:\s*#1a1a2e;\s*min-height:\s*calc\(100vh - 70px\);\s*\}\n",
        "\n",
        text,
        flags=re.S,
    )

    # Remove Teachers tab
    text = re.sub(
        r'\n\s*<div class="admin-tab" onclick="switchAdminTab\(\'teachers\'\)">\s*Teachers\s*</div>\s*',
        "\n",
        text,
    )

    # Ensure no panelTeachers exists
    text = re.sub(
        r'\n\s*<div class="admin-panel" id="panelTeachers" data-initialized="false"></div>\s*',
        "\n",
        text,
    )

    # Ensure panelFunFeatures exists and not panelFunfeatures
    text = text.replace('id="panelFunfeatures"', 'id="panelFunFeatures"')

    # Replace switchAdminTab function robustly
    new_switch = """function switchAdminTab(tab) {
 console.log('switchAdminTab:', tab);
 document.querySelectorAll('.admin-tab').forEach(t => t.classList.remove('active'));
 document.querySelectorAll('.admin-panel').forEach(p => p.classList.remove('active'));

 const tabMap = {
  moderation: { panelId: 'panelModeration', init: 'initModerationPanelContent' },
  settings: { panelId: 'panelSettings', init: 'initSettingsPanelContent' },
  theme: { panelId: 'panelTheme', init: 'initThemePanelContent' },
  users: { panelId: 'panelUsers', init: 'initUsersPanelContent' },
  compilations: { panelId: 'panelCompilations', init: 'initCompilationsPanelContent' },
  funfeatures: { panelId: 'panelFunFeatures', init: 'initFunfeaturesPanelContent' },
  destinations: { panelId: 'panelDestinations', init: 'initDestinationsPanelContent' },
  advice: { panelId: 'panelAdvice', init: 'initAdvicePanelContent' },
  papernotes: { panelId: 'panelPapernotes', init: 'initPapernotesPanelContent' },
  students: { panelId: 'panelStudents', init: 'initStudentsPanelContent' },
  security: { panelId: 'panelSecurity', init: 'initSecurityPanelContent' }
 };

 const cfg = tabMap[tab];
 if (!cfg) {
  console.warn('Unknown admin tab:', tab);
  return;
 }

 document.querySelectorAll('.admin-tab').forEach(t => {
  const onclick = t.getAttribute('onclick') || '';
  if (onclick.includes(`'${tab}'`)) t.classList.add('active');
 });

 const panel = document.getElementById(cfg.panelId);
 if (panel) {
  panel.classList.add('active');
 } else {
  console.warn('Panel not found:', cfg.panelId);
 }

 if (typeof window[cfg.init] === 'function') {
  window[cfg.init]();
 } else {
  console.warn('Init function not found:', cfg.init);
 }
}"""
    text = re.sub(
        r"function switchAdminTab\(tab\)\s*\{.*?\n\}",
        new_switch,
        text,
        flags=re.S,
        count=1,
    )

    write_text(path, text)


def patch_funfeatures() -> None:
    path = FILES["funfeatures"]
    if not path.exists():
        fail(f"Missing file: {path}")
    text = read_text(path)
    text = text.replace("panelFunfeatures", "panelFunFeatures")
    write_text(path, text)


def patch_compilations_admin() -> None:
    path = FILES["compilations_admin"]
    if not path.exists():
        fail(f"Missing file: {path}")
    text = read_text(path)

    # If initCompilationsPanelContent missing, add it before closing script for admin block
    if "function initCompilationsPanelContent()" not in text:
        insert = """
function initCompilationsPanelContent() {
 const panel = document.getElementById('panelCompilations');
 if (!panel) {
  console.error('panelCompilations not found');
  return;
 }
 if (panel.dataset.initialized !== 'true') {
  panel.innerHTML = renderCompilationsPanelHtml();
  panel.dataset.initialized = 'true';
 }
 loadCompilationsAdmin();
}
window.initCompilationsPanelContent = initCompilationsPanelContent;
"""
        # add near the first admin-ish compilations script end
        text = re.sub(
            r"(async function deleteCompilationAdmin\(id\)\s*\{.*?\n\})",
            r"\1\n" + insert.rstrip(),
            text,
            flags=re.S,
            count=1,
        )

    write_text(path, text)


def patch_index_template() -> None:
    path = FILES["index_template"]
    if not path.exists():
        fail(f"Missing file: {path}")
    text = read_text(path)
    text = re.sub(
        r"\n<!-- @include: fragments/admin/teachers\.html -->\s*",
        "\n",
        text,
    )
    write_text(path, text)


def patch_corrupted_fragment(path: Path) -> None:
    if not path.exists():
        fail(f"Missing file: {path}")
    text = read_text(path)
    cleaned = remove_gmail_garbage(text)
    write_text(path, cleaned)


def patch_server_route_order() -> None:
    path = FILES["server"]
    if not path.exists():
        fail(f"Missing file: {path}")
    text = read_text(path)

    root_route = "app.get('/', (req, res) => res.sendFile(path.join(__dirname, 'index.html')));"
    catch_all = "app.get('*', (req, res) => res.sendFile(path.join(__dirname, 'index.html')));"

    if root_route not in text or catch_all not in text:
        fail("Could not find frontend catch-all routes in server.js")

    # Remove both existing occurrences
    text = text.replace(root_route, "")
    text = text.replace(catch_all, "")

    listen_idx = text.find("server.listen(PORT, '0.0.0.0'")
    if listen_idx == -1:
        fail("Could not find server.listen(...) in server.js")

    insertion = "\n// ═══════════════════════════════════════════════════════════════════════════════\n" \
                "// SERVE FRONTEND\n" \
                "// ═══════════════════════════════════════════════════════════════════════════════\n" \
                + root_route + "\n" + catch_all + "\n\n"

    text = text[:listen_idx] + insertion + text[listen_idx:]
    write_text(path, text)


def main() -> None:
    targets = [
        FILES["admin_nav"],
        FILES["funfeatures"],
        FILES["compilations_admin"],
        FILES["index_template"],
        FILES["moderation"],
        FILES["students"],
        FILES["server"],
    ]

    for p in targets:
        backup_file(p)

    patch_admin_navbar()
    patch_funfeatures()
    patch_compilations_admin()
    patch_index_template()
    patch_corrupted_fragment(FILES["moderation"])
    patch_corrupted_fragment(FILES["students"])
    patch_server_route_order()

    # Optional cleanup: do not modify teachers file content, just leave it unused
    print("SNIPER PATCH COMPLETE")
    print("Changed:")
    print(f" - {FILES['admin_nav']}")
    print(f" - {FILES['funfeatures']}")
    print(f" - {FILES['compilations_admin']}")
    print(f" - {FILES['index_template']}")
    print(f" - {FILES['moderation']}")
    print(f" - {FILES['students']}")
    print(f" - {FILES['server']}")
    print("Next:")
    print(" - rebuild index if your workflow needs it")
    print(" - restart backend server")


if __name__ == "__main__":
    main()