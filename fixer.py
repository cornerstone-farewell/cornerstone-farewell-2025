#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from pathlib import Path


ROOT = Path.cwd()
INDEX_PATH = ROOT / "index.html"
SERVER_PATH = ROOT / "server.js"


def fail(message: str) -> None:
    print(json.dumps({"success": False, "error": message}), file=sys.stderr)
    sys.exit(1)


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception as exc:
        fail(f"Could not read {path.name}: {exc}")


def write_text(path: Path, content: str) -> None:
    try:
        path.write_text(content, encoding="utf-8", newline="\n")
    except Exception as exc:
        fail(f"Could not write {path.name}: {exc}")


def backup(path: Path) -> str:
    bak = path.with_suffix(path.suffix + ".sniper_bulk_patch.bak")
    if not bak.exists():
        write_text(bak, read_text(path))
    return bak.name


def replace_function(text: str, name: str, replacement: str) -> str:
    pattern = re.compile(rf"function\s+{re.escape(name)}\s*\([^)]*\)\s*\{{", re.S)
    m = pattern.search(text)
    if not m:
        return text
    start = m.start()
    brace_start = text.find("{", m.start())
    depth = 0
    end = None
    for i in range(brace_start, len(text)):
        ch = text[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    if end is None:
        return text
    return text[:start] + replacement + text[end:]


def inject_before(text: str, marker: str, block: str) -> str:
    if block.strip() in text:
        return text
    pos = text.find(marker)
    if pos == -1:
        return text
    return text[:pos] + block + "\n" + text[pos:]


def patch_index(text: str) -> tuple[str, list[str]]:
    changes: list[str] = []
    out = text.replace("\r\n", "\n")

    nav_target = '<li><a href="#adviceWall">Senior Advice</a></li>'
    if nav_target in out:
        extra_items = """
 <li><a href="#gratitudeWall">Gratitude</a></li>
 <li><a href="#superlativesSection">Superlatives</a></li>
 <li><a href="#wishJarSection">Wish Jar</a></li>
 <li><a href="#songDedicationsSection">Songs</a></li>
 <li><a href="#moodBoardSection">Mood</a></li>
 <li><a href="#timeCapsuleSection">Time Capsule</a></li>
 <li><a href="#memoryMosaicSection">Mosaic</a></li>
 <li><a href="#distanceMapSection">Future Map</a></li>"""
        if '#gratitudeWall' not in out:
            out = out.replace(nav_target, nav_target + extra_items, 1)
            changes.append("Expanded navbar for all sections")

    if 'id="memoriesPageOnly"' not in out:
        page_block = """
<section id="memoriesPageOnly" class="memories-page hidden">
 <div class="memories-page-header">
  <div>
   <span class="section-badge">Memory Archive</span>
   <h2 class="section-title">All <span class="highlight">Memories</span></h2>
   <p class="section-description" style="margin:0;">A dedicated full page that shows only memories from top to bottom.</p>
  </div>
  <button class="btn btn-secondary" id="backFromMemoriesOnlyPage" type="button">Back to Home</button>
 </div>
 <div class="container">
  <div class="memory-filters" id="memoryFiltersOnlyPage"></div>
  <div class="memory-grid" id="memoryGridOnlyPage"></div>
  <div class="load-more-wrap" id="loadMoreWrapOnlyPage" style="display:none;">
   <button class="btn btn-secondary load-more-btn" id="loadMoreBtnOnlyPage" type="button">Load More</button>
  </div>
 </div>
</section>
"""
        marker = "</section>\n <!-- Teachers / Timeline / Quote / Footer kept from previous version (rendered from settings) -->"
        if marker in out:
            out = out.replace(marker, "</section>\n" + page_block + "\n <!-- Teachers / Timeline / Quote / Footer kept from previous version (rendered from settings) -->", 1)
            changes.append("Added separate memories-only page shell")

    render_memories_page_only = """
function cloneMemoryFiltersToOnlyPage() {
 const src = document.getElementById('memoryFilters');
 const dst = document.getElementById('memoryFiltersOnlyPage');
 if (!src || !dst) return;
 dst.innerHTML = src.innerHTML;
 dst.querySelectorAll('.filter-btn').forEach(btn => {
  btn.classList.toggle('active', btn.dataset.filter === state.currentFilter);
  btn.addEventListener('click', async () => {
   document.querySelectorAll('#memoryFilters .filter-btn, #memoryFiltersOnlyPage .filter-btn').forEach(b => b.classList.remove('active'));
   document.querySelectorAll(`#memoryFilters .filter-btn[data-filter="${btn.dataset.filter}"], #memoryFiltersOnlyPage .filter-btn[data-filter="${btn.dataset.filter}"]`).forEach(b => b.classList.add('active'));
   state.currentFilter = btn.dataset.filter;
   await loadMemories(true);
   renderMemoriesOnlyPage();
  });
 });
}
function renderMemoriesOnlyPage() {
 const grid = document.getElementById('memoryGridOnlyPage');
 const wrap = document.getElementById('loadMoreWrapOnlyPage');
 if (!grid) return;
 cloneMemoryFiltersToOnlyPage();
 if (!state.memories.length) {
  grid.innerHTML = `<div class="memory-empty" style="grid-column:1/-1;"><div class="memory-empty-icon">📷</div><h3>No Memories Yet</h3><p>Be the first to share!</p></div>`;
  if (wrap) wrap.style.display = 'none';
  return;
 }
 grid.innerHTML = state.memories.map((memory, index) => `
 <div class="memory-card" data-index="${index}">
  <div class="memory-media" onclick="openLightbox(${index})">
   ${memory.file_type === 'video'
    ? `<video src="${memory.file_url}" preload="metadata"></video><div class="play-button">▶</div>`
    : `<img src="${memory.file_url}" alt="${escapeAttr(memory.caption)}" loading="lazy" />`}
   <span class="memory-type-badge">${escapeHtml(memory.memory_type)}</span>
   ${memory.featured ? `<span class="memory-featured-badge">Featured</span>` : ''}
  </div>
  <div class="memory-content">
   <div class="memory-author">
    <div class="memory-avatar">${escapeHtml((memory.student_name || '').charAt(0).toUpperCase())}</div>
    <div class="memory-author-info">
     <div class="memory-author-name">${escapeHtml(memory.student_name || '')}</div>
     <div class="memory-time">${timeAgo(memory.created_at)}</div>
    </div>
   </div>
   <p class="memory-caption">${escapeHtml(memory.caption || '')}</p>
   <div class="memory-actions">
    <div class="action-row">
     <button class="like-btn ${isLiked(memory.id) ? 'liked' : ''}" onclick="likeMemory(${memory.id}, this)">
      <span class="heart-icon">${isLiked(memory.id) ? '♥' : '♡'}</span>
      <span class="like-count">${memory.likes || 0}</span>
     </button>
     <button class="comments-open-btn" onclick="openLightbox(${index}); setTimeout(() => scrollCommentsTop(), 50);">Comments</button>
    </div>
    <div class="react-group">${renderReactionButtons(memory)}</div>
   </div>
  </div>
 </div>
 `).join('');
 if (wrap) wrap.style.display = state.memHasMore ? 'flex' : 'none';
}
function openMemoriesOnlyPage() {
 state.viewingAllMemoriesPage = true;
 const page = document.getElementById('memoriesPageOnly');
 if (page) page.classList.remove('hidden');
 history.pushState({ memoriesOnlyPage: true }, '', '#memories-only');
 renderMemoriesOnlyPage();
 window.scrollTo({ top: 0, behavior: 'smooth' });
}
function closeMemoriesOnlyPage() {
 state.viewingAllMemoriesPage = false;
 const page = document.getElementById('memoriesPageOnly');
 if (page) page.classList.add('hidden');
 if (location.hash === '#memories-only') history.pushState({}, '', '#home');
 const home = document.getElementById('home');
 if (home) home.scrollIntoView({ behavior: 'smooth', block: 'start' });
 renderMemories();
}
"""
    if "function openMemoriesOnlyPage()" not in out:
        out = inject_before(out, "document.addEventListener('keydown'", render_memories_page_only)
        if "function openMemoriesOnlyPage()" in out:
            changes.append("Added separate memories-only page logic")

    handler_pattern = re.compile(
        r"document\.addEventListener\('DOMContentLoaded', \(\) => \{\n const viewAllBtn = document\.getElementById\('viewAllMemoriesBtn'\);.*?window\.addEventListener\('popstate', \(\) => \{\n const page = document\.getElementById\('memoriesPage'\);.*?\n \}\);",
        re.S,
    )
    replacement_handler = """document.addEventListener('DOMContentLoaded', () => {
 const viewAllBtn = document.getElementById('viewAllMemoriesBtn');
 if (viewAllBtn) viewAllBtn.addEventListener('click', openMemoriesOnlyPage);
 const backBtn = document.getElementById('backFromMemoriesOnlyPage');
 if (backBtn) backBtn.addEventListener('click', closeMemoriesOnlyPage);
 const loadMoreBtnPage = document.getElementById('loadMoreBtnOnlyPage');
 if (loadMoreBtnPage) loadMoreBtnPage.addEventListener('click', async () => {
  await loadMemories(false);
  renderMemoriesOnlyPage();
 });
 document.querySelectorAll('a[href="#home"]').forEach(el => {
  el.addEventListener('click', (evt) => {
   evt.preventDefault();
   closeMemoriesOnlyPage();
  });
 });
});
window.addEventListener('popstate', () => {
 const page = document.getElementById('memoriesPageOnly');
 if (!page) return;
 if (location.hash === '#memories-only') {
  state.viewingAllMemoriesPage = true;
  page.classList.remove('hidden');
  renderMemoriesOnlyPage();
 } else {
  state.viewingAllMemoriesPage = false;
  page.classList.add('hidden');
  renderMemories();
 }
});"""
    out = handler_pattern.sub(replacement_handler, out)

    out = out.replace(
        "if (state.viewingAllMemoriesPage) renderMemoriesPage();",
        "if (state.viewingAllMemoriesPage) renderMemoriesOnlyPage();",
    )

    if "loadStudentDirectoryIntoAdmin()" not in out:
        helper_block = """
async function loadStudentDirectoryIntoAdmin() {
 try {
  const res = await fetch(apiUrl('/api/student-directory'));
  const data = await res.json();
  return data.success && Array.isArray(data.students) ? data.students : [];
 } catch (_) {
  return [];
 }
}
function buildStudentDirectoryCsvTemplate(students) {
 const rows = [['name','section']];
 (students || []).forEach(s => rows.push([s.name || '', s.section || '']));
 return rows.map(r => r.map(v => `"${String(v).replaceAll('"','""')}"`).join(',')).join('\\n');
}
async function downloadStudentDirectoryTemplate() {
 const students = await loadStudentDirectoryIntoAdmin();
 const csv = buildStudentDirectoryCsvTemplate(students);
 const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' });
 const a = document.createElement('a');
 a.href = URL.createObjectURL(blob);
 a.download = 'student-directory-template.csv';
 a.click();
 URL.revokeObjectURL(a.href);
}
async function uploadStudentDirectoryCsv(file) {
 if (!file) return showNotification('error', 'Missing file', 'Choose a CSV file first.');
 const text = await file.text();
 const lines = text.split(/\\r?\\n/).map(x => x.trim()).filter(Boolean);
 if (!lines.length) return showNotification('error', 'Empty file', 'CSV file is empty.');
 const rows = lines.slice(1).map(line => {
  const parts = line.split(',').map(x => x.trim().replace(/^"|"$/g, ''));
  return { name: parts[0] || '', section: parts[1] || '' };
 }).filter(r => r.name && r.section);
 const res = await fetch(apiUrl('/api/admin/student-directory'), {
  method:'POST',
  headers:{'Content-Type':'application/json','Authorization':`Bearer ${state.adminToken}`},
  body:JSON.stringify({ students: rows })
 });
 const data = await res.json();
 if (!data.success) return showNotification('error', 'Failed', data.error || 'Could not update student directory.');
 showNotification('success', 'Updated', `${rows.length} students imported.`);
 await reloadSettingsAdmin();
}
async function bulkApplyStudentsToSuperlatives() {
 const students = await loadStudentDirectoryIntoAdmin();
 if (!students.length) return showNotification('error', 'No students', 'Student directory is empty.');
 const categories = Array.isArray(window.supData) ? window.supData : [];
 categories.forEach(cat => {
  cat.nominees = students.map(s => ({
   id: `${cat.id}_${s.name}`,
   name: s.name,
   votes: 0
  }));
 });
 showNotification('success', 'Applied', 'Student directory has been copied into all superlative categories.');
 if (typeof renderSuperlatives === 'function') renderSuperlatives();
}
"""
        out = inject_before(out, "function renderUsersPanelHtml()", helper_block)
        if "loadStudentDirectoryIntoAdmin()" in out:
            changes.append("Added student directory bulk helpers")

    if "Student Directory CSV" not in out and "function renderSettingsPanelHtml()" in out:
        old = "<div style=\"margin-top:16px; border:1px solid var(--glass-border); border-radius:16px; padding:14px; background:rgba(255,255,255,0.03);\"><div style=\"display:flex; justify-content:space-between; align-items:center; gap:10px; flex-wrap:wrap;\"><h4 style=\"font-family:var(--font-display); color:var(--primary-gold); margin-bottom:6px;\">Timeline Editor</h4><button class=\"admin-btn admin-btn-secondary\" type=\"button\" onclick=\"addTimelineRow()\">+ Add Timeline Item</button></div><div class=\"mini-pill\">Fields: year, title, description</div><div id=\"timelineEditor\" style=\"margin-top:12px; display:grid; gap:12px;\"></div></div></div></div></div>`;"
        new = "<div style=\"margin-top:16px; border:1px solid var(--glass-border); border-radius:16px; padding:14px; background:rgba(255,255,255,0.03);\"><div style=\"display:flex; justify-content:space-between; align-items:center; gap:10px; flex-wrap:wrap;\"><h4 style=\"font-family:var(--font-display); color:var(--primary-gold); margin-bottom:6px;\">Timeline Editor</h4><button class=\"admin-btn admin-btn-secondary\" type=\"button\" onclick=\"addTimelineRow()\">+ Add Timeline Item</button></div><div class=\"mini-pill\">Fields: year, title, description</div><div id=\"timelineEditor\" style=\"margin-top:12px; display:grid; gap:12px;\"></div></div><div style=\"margin-top:16px; border:1px solid var(--glass-border); border-radius:16px; padding:14px; background:rgba(255,255,255,0.03);\"><div style=\"display:flex; justify-content:space-between; align-items:center; gap:10px; flex-wrap:wrap;\"><h4 style=\"font-family:var(--font-display); color:var(--primary-gold); margin-bottom:6px;\">Student Directory CSV</h4><div style=\"display:flex; gap:10px; flex-wrap:wrap;\"><button class=\"admin-btn admin-btn-secondary\" type=\"button\" onclick=\"downloadStudentDirectoryTemplate()\">Download Template</button><label class=\"admin-btn admin-btn-secondary\" style=\"cursor:pointer;\">Import CSV<input type=\"file\" accept=\".csv\" style=\"display:none;\" onchange=\"uploadStudentDirectoryCsv(this.files[0])\"></label><button class=\"admin-btn admin-btn-primary\" type=\"button\" onclick=\"bulkApplyStudentsToSuperlatives()\">Use in Superlatives</button></div></div><div class=\"mini-pill\">Bulk update students with columns: name, section</div></div></div></div></div>`;"
        if old in out:
            out = out.replace(old, new, 1)
            changes.append("Added student directory CSV controls to admin settings")

    if "function renderSuperlativesAdminPanel()" not in out and "function buildAdminPanels()" in out:
        super_admin_block = """
function renderSuperlativesAdminPanel() {
 const panel = document.getElementById('panelFunFeatures');
 if (!panel) return;
 if (!panel.innerHTML.includes('Bulk Superlatives Control')) return;
}
"""
        out = inject_before(out, "function buildAdminPanels()", super_admin_block)

    if "name:' Senior Advice'" not in out and "const features=[{key:'gratitudeWall'" in out:
        out = out.replace(
            "const features=[{key:'gratitudeWall',name:' Gratitude Wall',desc:'Students post sticky note thank-you messages'},{key:'superlatives',name:' Class Superlatives',desc:'Students nominate and vote for classmates'},{key:'wishJar',name:' Wish Jar',desc:'Students drop dreams, hopes and advice'},{key:'songDedications',name:' Song Dedications',desc:'Students dedicate songs to friends'},{key:'moodBoard',name:' Mood Board',desc:'Students vote on how they feel about Farewell'},{key:'timeCapsule',name:' Time Capsule',desc:'Students write sealed letters to their future selves'},{key:'memoryMosaic',name:' Memory Mosaic',desc:'Auto leaderboard of top memory contributors'}];",
            "const features=[{key:'gratitudeWall',name:' Gratitude Wall',desc:'Students post sticky note thank-you messages'},{key:'superlatives',name:' Class Superlatives',desc:'Students nominate and vote for classmates'},{key:'wishJar',name:' Wish Jar',desc:'Students drop dreams, hopes and advice'},{key:'songDedications',name:' Song Dedications',desc:'Students dedicate songs to friends'},{key:'moodBoard',name:' Mood Board',desc:'Students vote on how they feel about Farewell'},{key:'timeCapsule',name:' Time Capsule',desc:'Students write sealed letters to their future selves'},{key:'seniorAdvice',name:' Senior Advice',desc:'Seniors leave advice for juniors'},{key:'memoryMosaic',name:' Memory Mosaic',desc:'Auto leaderboard of top memory contributors'}];",
            1,
        )

    return out, changes


def patch_server(text: str) -> tuple[str, list[str]]:
    changes: list[str] = []
    out = text.replace("\r\n", "\n")

    if "const studentDirectoryPath = path.join(databaseDir, 'student_directory.json');" not in out:
        insert_point = "const auditPath = path.join(databaseDir, 'audit.json');"
        if insert_point in out:
            out = out.replace(
                insert_point,
                insert_point + "\nconst studentDirectoryPath = path.join(databaseDir, 'student_directory.json');\nconst superlativeVotesPath = path.join(databaseDir, 'superlative_votes.json');",
                1,
            )
            changes.append("Added student directory and superlative vote storage constants")

    if "function readStudentDirectory()" not in out:
        helper_block = """
function readStudentDirectory() {
 return safeReadJson(studentDirectoryPath, { students: [] });
}
function writeStudentDirectory(data) {
 safeWriteJson(studentDirectoryPath, data);
}
function readSuperlativeVotes() {
 return safeReadJson(superlativeVotesPath, { votes: [] });
}
function writeSuperlativeVotes(data) {
 safeWriteJson(superlativeVotesPath, data);
}
"""
        marker = "function writeAudit(data) {\n safeWriteJson(auditPath, data);\n}"
        if marker in out:
            out = out.replace(marker, marker + helper_block, 1)
            changes.append("Added student directory and superlative vote helpers")

    if "student_directory.json" in out and "superlative_votes.json" in out and "if (!fs.existsSync(studentDirectoryPath)) {" not in out:
        old = " if (!fs.existsSync(adminPath)) {"
        new = """ if (!fs.existsSync(studentDirectoryPath)) {
  fs.writeFileSync(studentDirectoryPath, JSON.stringify({ students: [] }, null, 2));
  console.log(' Created student directory database');
 }
 if (!fs.existsSync(superlativeVotesPath)) {
  fs.writeFileSync(superlativeVotesPath, JSON.stringify({ votes: [] }, null, 2));
  console.log(' Created superlative votes database');
 }
 if (!fs.existsSync(adminPath)) {"""
        if old in out:
            out = out.replace(old, new, 1)
            changes.append("Added database initialization for student directory and superlative votes")

    if "app.get('/api/student-directory'" not in out:
        student_routes = """
app.get('/api/student-directory', (req, res) => {
 try {
  const db = readStudentDirectory();
  res.json({ success: true, students: db.students || [] });
 } catch (e) { res.status(500).json({ success: false, error: e.message }); }
});
app.post('/api/admin/student-directory', (req, res) => {
 try {
  const auth = requireAdmin(req, res); if (!auth) return;
  if (!hasPerm(auth.user, 'settings')) return res.status(403).json({ success: false, error: 'Forbidden' });
  const students = Array.isArray(req.body?.students) ? req.body.students : [];
  const cleaned = students.map(s => ({
   name: String(s?.name || '').trim().substring(0, 80),
   section: String(s?.section || '').trim().substring(0, 20)
  })).filter(s => s.name && s.section);
  writeStudentDirectory({ students: cleaned });
  audit(auth.user.id, 'save-student-directory', { count: cleaned.length });
  res.json({ success: true, count: cleaned.length });
 } catch (e) { res.status(500).json({ success: false, error: e.message }); }
});
"""
        out = inject_before(out, "// ═══════════════════════════════════════════════════════════════════════════════\n// SERVE FRONTEND", student_routes)
        if "app.get('/api/student-directory'" in out:
            changes.append("Added student directory API")

    if "const superlativeVotes = readSuperlativeVotes();" not in out and "app.post('/api/fun/superlatives/vote'" in out:
        vote_route = """app.post('/api/fun/superlatives/vote', (req, res) => {
 const { categoryId, nomineeName, voterId } = req.body || {};
 const db = ffRead('superlatives');
 const cat = db.categories.find(c => c.id === Number(categoryId));
 if (!cat) return res.status(404).json({ success: false, error: 'Category not found' });
 const nom = cat.nominees.find(n => n.name === nomineeName || String(n.id) === String(req.body?.nomineeId));
 if (!nom) return res.status(404).json({ success: false, error: 'Nominee not found' });
 const superlativeVotes = readSuperlativeVotes();
 const voterKey = String(voterId || req.headers['x-forwarded-for'] || req.socket.remoteAddress || '').trim();
 if (!voterKey) return res.status(400).json({ success: false, error: 'voterId required' });
 const already = superlativeVotes.votes.find(v => v.categoryId === Number(categoryId) && v.voterId === voterKey);
 if (already) return res.status(409).json({ success: false, error: 'You already voted in this category' });
 superlativeVotes.votes.push({ categoryId: Number(categoryId), nomineeName: nom.name, voterId: voterKey, createdAt: nowIso() });
 writeSuperlativeVotes(superlativeVotes);
 nom.votes++;
 ffWrite('superlatives', db);
 broadcast('ff:superlatives:vote', { categoryId, nomineeName: nom.name });
 res.json({ success: true });
});"""
        pattern = re.compile(r"app\.post\('/api/fun/superlatives/vote', \(req, res\) => \{.*?\n \}\);", re.S)
        out = pattern.sub(vote_route, out, count=1)
        changes.append("Made superlative voting enforce one vote per user per category")

    if "caption: String(caption).trim().substring(0, 500)," in out:
        out = out.replace("caption: String(caption).trim().substring(0, 500),", "caption: String(caption).trim().substring(0, 1000),")
    if "caption: caption.trim().substring(0, 500)," in out:
        out = out.replace("caption: caption.trim().substring(0, 500),", "caption: caption.trim().substring(0, 1000),")

    return out, changes


def main() -> None:
    if not INDEX_PATH.exists():
        fail("index.html not found")
    if not SERVER_PATH.exists():
        fail("server.js not found")

    old_index = read_text(INDEX_PATH)
    old_server = read_text(SERVER_PATH)

    new_index, index_changes = patch_index(old_index)
    new_server, server_changes = patch_server(old_server)

    modified = []
    backups = []

    if new_index != old_index:
        backups.append(backup(INDEX_PATH))
        write_text(INDEX_PATH, new_index)
        modified.append("index.html")

    if new_server != old_server:
        backups.append(backup(SERVER_PATH))
        write_text(SERVER_PATH, new_server)
        modified.append("server.js")

    print(json.dumps({
        "success": True,
        "modified": modified,
        "backups": backups,
        "changes": index_changes + server_changes
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()