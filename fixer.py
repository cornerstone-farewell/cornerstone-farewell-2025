#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from pathlib import Path


def fail(message: str) -> None:
    print(json.dumps({"success": False, "error": message}, ensure_ascii=False), file=sys.stderr)
    sys.exit(1)


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception as exc:
        fail(f"Could not read {path}: {exc}")


def write_text(path: Path, content: str) -> None:
    try:
        path.write_text(content, encoding="utf-8", newline="\n")
    except Exception as exc:
        fail(f"Could not write {path}: {exc}")


def backup_file(path: Path) -> str:
    backup = path.with_suffix(path.suffix + ".sniperfix.bak")
    if not backup.exists():
        write_text(backup, read_text(path))
    return backup.name


def replace_function(source: str, function_name: str, replacement: str) -> str:
    pattern = re.compile(rf"function\s+{re.escape(function_name)}\s*\([^)]*\)\s*\{{", re.S)
    match = pattern.search(source)
    if not match:
        return source
    start = match.start()
    brace_start = source.find("{", match.start())
    depth = 0
    end = None
    for index in range(brace_start, len(source)):
        ch = source[index]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                end = index + 1
                break
    if end is None:
        return source
    return source[:start] + replacement + source[end:]


def replace_route(source: str, route_signature: str, replacement: str) -> str:
    start = source.find(route_signature)
    if start == -1:
        return source
    brace_start = source.find("{", start)
    if brace_start == -1:
        return source
    depth = 0
    end = None
    for index in range(brace_start, len(source)):
        ch = source[index]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                semi = source.find(");", index)
                if semi == -1:
                    return source
                end = semi + 2
                break
    if end is None:
        return source
    return source[:start] + replacement + source[end:]


def ensure_block_after(source: str, anchor: str, block: str) -> str:
    if block.strip() in source:
        return source
    pos = source.find(anchor)
    if pos == -1:
        return source
    pos += len(anchor)
    return source[:pos] + "\n" + block + "\n" + source[pos:]

def inject_before_if_found(text: str, marker: str, block: str) -> str:
    if block.strip() in text:
        return text
    idx = text.find(marker)
    if idx == -1:
        return text
    return text[:idx] + block + "\n" + text[idx:]
def patch_server_js(server_text: str) -> tuple[str, list[str]]:
    changes: list[str] = []
    text = server_text.replace("\r\n", "\n")

    broken_safe_routing = """// --- SNIPER SAFE ROUTING --- 
app.use(express.static(__dirname));
app.use('/uploads', express.static(path.join(__dirname, 'uploads')));
app.use('/music', express.static(path.join(__dirname, 'music')));
// Prevent infinite loops: Block missing frontend components from fetching index.html
app.get('/sections/*', (req, res) => res.status(404).send('Component not found'));
app.get('/api/*', (req, res) => res.status(404).json({success: false, error: 'Endpoint not found'}));
// Standard fallback for Single Page Apps
app.get('*', (req, res) => res.sendFile(path.join(__dirname, 'index.html')));
// ---------------------------
// Serve static files
app.use('/uploads', express.static(path.join(__dirname, 'uploads')));"""
    fixed_safe_routing = """// --- SNIPER SAFE ROUTING --- 
app.use(express.static(__dirname));
app.use('/uploads', express.static(path.join(__dirname, 'uploads')));
app.use('/music', express.static(path.join(__dirname, 'music')));"""
    if broken_safe_routing in text:
        text = text.replace(broken_safe_routing, fixed_safe_routing, 1)
        changes.append("server: fixed early wildcard routing that broke all API endpoints")

    if "const funPath = path.join(databaseDir, 'fun_features.json');" not in text:
        text = ensure_block_after(
            text,
            "const studentDirectoryPath = path.join(databaseDir, 'student_directory.json');",
            """const funPath = path.join(databaseDir, 'fun_features.json');
const teacherAudioPath = path.join(databaseDir, 'teacher_audio.json');
const paperNotesPath = path.join(databaseDir, 'paper_notes.json');
const destinationsPath = path.join(databaseDir, 'destinations.json');""",
        )
        if "const funPath = path.join(databaseDir, 'fun_features.json');" in text:
            changes.append("server: restored missing extra database path constants")

    broken_init = re.search(
        r"function initDatabase\(\) \{.*?\n\}\n if \(!fs\.existsSync\(studentDirectoryPath\)\) \{.*?function safeReadJson",
        text,
        re.S,
    )
    if broken_init:
        fixed_init = """function initDatabase() {
 if (!fs.existsSync(dbPath)) {
  fs.writeFileSync(dbPath, JSON.stringify({ memories: [], nextId: 1 }, null, 2));
  console.log(' Created memories database');
 }
 if (!fs.existsSync(sessionsPath)) {
  fs.writeFileSync(sessionsPath, JSON.stringify({ sessions: [] }, null, 2));
  console.log(' Created sessions database');
 }
 if (!fs.existsSync(settingsPath)) {
  fs.writeFileSync(settingsPath, JSON.stringify({ settings: {} }, null, 2));
  console.log(' Created settings database');
 }
 if (!fs.existsSync(commentsPath)) {
  fs.writeFileSync(commentsPath, JSON.stringify({ comments: [], nextId: 1 }, null, 2));
  console.log(' Created comments database');
 }
 if (!fs.existsSync(reactionsPath)) {
  fs.writeFileSync(reactionsPath, JSON.stringify({ reactions: [] }, null, 2));
  console.log(' Created reactions database');
 }
 if (!fs.existsSync(auditPath)) {
  fs.writeFileSync(auditPath, JSON.stringify({ events: [], nextId: 1 }, null, 2));
  console.log(' Created audit database');
 }
 if (!fs.existsSync(adminPath)) {
  const now = new Date().toISOString();
  fs.writeFileSync(adminPath, JSON.stringify({
   users: [
    {
     id: 'super',
     name: 'Super Admin',
     role: 'superadmin',
     password: ADMIN_PASSWORD,
     createdAt: now,
     updatedAt: now,
     disabled: false,
     permissions: {
      moderation: true,
      settings: true,
      theme: true,
      export: true,
      users: true,
      trash: true,
      replaceFile: true,
      editMemory: true,
      bulk: true,
      featured: true
     }
    }
   ]
  }, null, 2));
  console.log(' Created admin database with super admin');
 }
 if (!fs.existsSync(compilationsPath)) {
  fs.writeFileSync(compilationsPath, JSON.stringify({ compilations: [], nextId: 1 }, null, 2));
  console.log(' Created compilations database');
 }
 if (!fs.existsSync(studentDirectoryPath)) {
  fs.writeFileSync(studentDirectoryPath, JSON.stringify({ students: [] }, null, 2));
  console.log(' Created student directory database');
 }
 if (!fs.existsSync(funPath)) {
  fs.writeFileSync(funPath, JSON.stringify({ settings: {}, gratitude: [], superlatives: { categories: [] }, wishes: [], dedications: [], mood: { votes: {} }, capsules: [] }, null, 2));
  console.log(' Created fun features database');
 }
 if (!fs.existsSync(teacherAudioPath)) {
  fs.writeFileSync(teacherAudioPath, JSON.stringify({ items: [], nextId: 1 }, null, 2));
  console.log(' Created teacher audio database');
 }
 if (!fs.existsSync(paperNotesPath)) {
  fs.writeFileSync(paperNotesPath, JSON.stringify({ notes: [], nextId: 1 }, null, 2));
  console.log(' Created paper notes database');
 }
 if (!fs.existsSync(destinationsPath)) {
  fs.writeFileSync(destinationsPath, JSON.stringify({ destinations: [], submissions: [], nextId: 1 }, null, 2));
  console.log(' Created destinations database');
 }
}

function safeReadJson"""
        text = re.sub(
            r"function initDatabase\(\) \{.*?\n\}\n if \(!fs\.existsSync\(studentDirectoryPath\)\) \{.*?function safeReadJson",
            fixed_init,
            text,
            count=1,
            flags=re.S,
        )
        changes.append("server: repaired broken initDatabase structure")

    if "function readStudentDirectory()" not in text:
        text = ensure_block_after(
            text,
            """function writeCompilations(data) {
 safeWriteJson(compilationsPath, data);
}""",
            """function readStudentDirectory() {
 return safeReadJson(studentDirectoryPath, { students: [] });
}
function writeStudentDirectory(data) {
 safeWriteJson(studentDirectoryPath, data);
}
function readFun() {
 return safeReadJson(funPath, { settings: {}, gratitude: [], superlatives: { categories: [] }, wishes: [], dedications: [], mood: { votes: {} }, capsules: [] });
}
function writeFun(data) {
 safeWriteJson(funPath, data);
}
function readTeacherAudio() {
 return safeReadJson(teacherAudioPath, { items: [], nextId: 1 });
}
function writeTeacherAudio(data) {
 safeWriteJson(teacherAudioPath, data);
}
function readPaperNotes() {
 return safeReadJson(paperNotesPath, { notes: [], nextId: 1 });
}
function writePaperNotes(data) {
 safeWriteJson(paperNotesPath, data);
}
function readDestinationsDb() {
 return safeReadJson(destinationsPath, { destinations: [], submissions: [], nextId: 1 });
}
function writeDestinationsDb(data) {
 safeWriteJson(destinationsPath, data);
}""",
        )
        if "function readStudentDirectory()" in text:
            changes.append("server: restored helper read/write functions")

    memories_route = """app.get('/api/memories', (req, res) => {
 try {
  const db = readDB();
  const page = Math.max(1, parseInt(req.query.page || '1', 10));
  const limit = Math.min(5000, Math.max(1, parseInt(req.query.limit || '20', 10)));
  const type = req.query.type || 'all';
  let memories = db.memories.filter(m => m.approved === 1 && !m.deletedAt && !m.purgedAt);
  if (type !== 'all') memories = memories.filter(m => m.memory_type === type);
  memories.sort((a, b) => {
   if ((b.featured || 0) !== (a.featured || 0)) return (b.featured || 0) - (a.featured || 0);
   return new Date(b.created_at) - new Date(a.created_at);
  });
  const total = memories.length;
  const start = (page - 1) * limit;
  const items = memories.slice(start, start + limit).map(m => {
   const shaped = memoryPublicShape(m);
   shaped.reactions = getReactionCountsForMemory(m.id);
   return shaped;
  });
  res.json({
   success: true,
   memories: items,
   page,
   limit,
   total,
   nextCursor: items.length ? items[items.length - 1].created_at : null,
   hasMore: start + limit < total
  });
 } catch (error) {
  console.error('Get memories error:', error);
  res.status(500).json({ success: false, error: error.message });
 }
});"""
    text = replace_route(text, "app.get('/api/memories', (req, res) => {", memories_route)

    student_directory_get = """app.get('/api/student-directory', (req, res) => {
 try {
  const db = readStudentDirectory();
  res.json({ success: true, students: db.students || [] });
 } catch (e) {
  res.status(500).json({ success: false, error: e.message });
 }
});"""
    if "app.get('/api/student-directory'" not in text:
        text = inject_before_if_found(text, "// Settings save", student_directory_get)

    student_directory_post = """app.post('/api/admin/student-directory', (req, res) => {
 try {
  const auth = requireAdmin(req, res);
  if (!auth) return;
  if (!hasPerm(auth.user, 'settings')) return res.status(403).json({ success: false, error: 'Forbidden' });
  const students = Array.isArray(req.body?.students) ? req.body.students : [];
  const cleaned = students.map(s => ({
   name: String(s?.name || '').trim().substring(0, 80),
   section: String(s?.section || '').trim().substring(0, 20)
  })).filter(s => s.name && s.section);
  writeStudentDirectory({ students: cleaned });
  audit(auth.user.id, 'save-student-directory', { count: cleaned.length });
  res.json({ success: true, count: cleaned.length });
 } catch (e) {
  res.status(500).json({ success: false, error: e.message });
 }
});"""
    if "app.post('/api/admin/student-directory'" not in text:
        text = inject_before_if_found(text, "// Settings save", student_directory_post)

    if "app.get('/api/settings', (req, res) => {" in text and "studentDirectory:" not in text:
        settings_route = """app.get('/api/settings', (req, res) => {
 try {
  const data = readSettings();
  const settings = data.settings || {};
  const studentDirectory = readStudentDirectory().students || [];
  res.json({ success: true, settings: { ...settings, studentDirectory } });
 } catch (error) {
  console.error('Get settings error:', error);
  res.status(500).json({ success: false, error: error.message });
 }
});"""
        text = replace_route(text, "app.get('/api/settings', (req, res) => {", settings_route)
        changes.append("server: settings endpoint now returns studentDirectory too")

    if "app.post('/api/admin/settings', (req, res) => {" in text and "incoming.studentDirectory" not in text:
        admin_settings_route = """app.post('/api/admin/settings', (req, res) => {
 try {
  const auth = requireAdmin(req, res);
  if (!auth) return;
  if (!hasPerm(auth.user, 'settings')) return res.status(403).json({ success: false, error: 'Forbidden' });
  const incoming = req.body?.settings;
  if (!incoming || typeof incoming !== 'object') return res.status(400).json({ success: false, error: 'Missing settings object' });
  const istFields = ['farewellIST', 'uploadWindowStartIST', 'uploadWindowEndIST', 'autoApproveStartIST', 'autoApproveEndIST'];
  for (const f of istFields) {
   if (incoming[f] && !/^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}$/.test(incoming[f])) {
    return res.status(400).json({ success: false, error: `Invalid ${f} format. Use YYYY-MM-DDTHH:mm` });
   }
  }
  if (incoming.theme && !hasPerm(auth.user, 'theme')) {
   return res.status(403).json({ success: false, error: 'No permission to edit theme' });
  }
  if (Array.isArray(incoming.studentDirectory)) {
   const cleanedStudents = incoming.studentDirectory.map(s => ({
    name: String(s?.name || '').trim().substring(0, 80),
    section: String(s?.section || '').trim().substring(0, 20)
   })).filter(s => s.name && s.section);
   writeStudentDirectory({ students: cleanedStudents });
  }
  const settingsOnly = { ...incoming };
  delete settingsOnly.studentDirectory;
  writeSettings({ settings: settingsOnly });
  audit(auth.user.id, 'save-settings', {});
  broadcast('settings:update', {});
  res.json({ success: true });
 } catch (e) {
  res.status(500).json({ success: false, error: e.message });
 }
});"""
        text = replace_route(text, "app.post('/api/admin/settings', (req, res) => {", admin_settings_route)
        changes.append("server: admin settings save now persists studentDirectory")

    openstreetmap_destinations_block = """
app.post('/api/admin/destinations-search', async (req, res) => {
 try {
  const auth = requireAdmin(req, res);
  if (!auth) return;
  if (!hasPerm(auth.user, 'settings')) return res.status(403).json({ success: false, error: 'Forbidden' });
  const query = String(req.body?.query || '').trim();
  if (!query) return res.status(400).json({ success: false, error: 'query required' });
  const response = await fetch('https://nominatim.openstreetmap.org/search?format=jsonv2&limit=8&q=' + encodeURIComponent(query), {
   headers: { 'User-Agent': 'cornerstone-farewell/1.0', 'Accept': 'application/json' }
  });
  const rows = await response.json();
  const results = Array.isArray(rows) ? rows.map(row => ({
   place: String(row.display_name || '').trim(),
   name: String(row.display_name || '').trim(),
   lat: Number(row.lat),
   lng: Number(row.lon)
  })).filter(x => x.place && Number.isFinite(x.lat) && Number.isFinite(x.lng)) : [];
  res.json({ success: true, results });
 } catch (e) {
  res.status(500).json({ success: false, error: e.message });
 }
});"""
    if "app.post('/api/admin/destinations-search'" not in text:
        text = inject_before_if_found(text, "// ═══════════════════════════════════════════════════════════════════════════════\n// START SERVER", openstreetmap_destinations_block)
        if "app.post('/api/admin/destinations-search'" in text:
            changes.append("server: added OpenStreetMap search proxy for accurate location picker")

    if "app.get('*', (req, res) => res.sendFile(path.join(__dirname, 'index.html')));" in text:
        text = text.replace(
            "app.get('*', (req, res) => res.sendFile(path.join(__dirname, 'index.html')));",
            "",
        )
        changes.append("server: removed duplicate broad wildcard route")

    if "app.get('*', (req, res) => {" not in text:
        text = inject_before_if_found(
            text,
            "server.listen(PORT, '0.0.0.0', () => {",
            """app.get('*', (req, res) => {
 if (req.path.startsWith('/api/')) return res.status(404).json({ success: false, error: 'Endpoint not found' });
 if (req.path.startsWith('/uploads/') || req.path.startsWith('/music/')) return res.status(404).send('Not found');
 return res.sendFile(path.join(__dirname, 'index.html'));
});""",
        )

    return text, changes


def patch_index_html(index_text: str) -> tuple[str, list[str]]:
    changes: list[str] = []
    text = index_text.replace("\r\n", "\n")

    text = text.replace(
        "previewLimit: 6,\n viewingAllMemoriesPage: false,\n previewLimit: 6,\n viewingAllMemoriesPage: false,\n previewLimit: 6,\n viewingAllMemoriesPage: false,",
        "previewLimit: 6,\n viewingAllMemoriesPage: false,",
    )

    if '<li><a href="#teachers">Teachers</a></li>' in text and '<li><a href="#gratitudeWall">Gratitude</a></li>' not in text:
        text = text.replace(
            '<li><a href="#teachers">Teachers</a></li>\n <li><a href="#timeline">Journey</a></li>\n <li><a href="#compilations">Compilations</a></li>',
            '<li><a href="#teachers">Teachers</a></li>\n <li><a href="#timeline">Journey</a></li>\n <li><a href="#gratitudeWall">Gratitude</a></li>\n <li><a href="#superlativesSection">Superlatives</a></li>\n <li><a href="#wishJarSection">Wish Jar</a></li>\n <li><a href="#songDedicationsSection">Songs</a></li>\n <li><a href="#moodBoardSection">Mood</a></li>\n <li><a href="#timeCapsuleSection">Time Capsule</a></li>\n <li><a href="#distanceMapSection">Future Map</a></li>\n <li><a href="#compilations">Compilations</a></li>',
            1,
        )
        changes.append("index: added all feature sections to navbar")

    if 'id="viewAllMemoriesBtn"' not in text and '<div class="load-more-wrap" id="loadMoreWrap"' in text:
        text = text.replace(
            '<div class="load-more-wrap" id="loadMoreWrap" style="display:none;">',
            '<div class="memories-preview-actions"><button class="btn btn-secondary" id="viewAllMemoriesBtn" type="button">View All Memories</button></div>\n <div class="load-more-wrap" id="loadMoreWrap" style="display:none;">',
            1,
        )
        changes.append("index: restored view all memories button")

    if 'id="memoriesPage"' not in text and "<!-- Teachers / Timeline / Quote / Footer kept from previous version (rendered from settings) -->" in text:
        text = text.replace(
            "</section>\n <!-- Teachers / Timeline / Quote / Footer kept from previous version (rendered from settings) -->",
            """</section>
<section id="memoriesPage" class="memories-page hidden">
 <div class="memories-page-header">
  <h2 class="section-title">All <span class="highlight">Memories</span></h2>
  <button class="btn btn-secondary" id="backToHomeFromMemoriesPage" type="button">Back to Home</button>
 </div>
 <div class="container">
  <div class="memory-grid" id="memoryGridPage"></div>
  <div class="load-more-wrap" id="loadMoreWrapPage" style="display:none;">
   <button class="btn btn-secondary load-more-btn" id="loadMoreBtnPage" type="button">Load More</button>
  </div>
 </div>
</section>
 <!-- Teachers / Timeline / Quote / Footer kept from previous version (rendered from settings) -->""",
            1,
        )
        changes.append("index: restored dedicated memories page shell")

    broken_render_teachers = re.search(r"function renderTeachers\(\) \{.*?teacher￾quote.*?\}", text, re.S)
    if broken_render_teachers:
        replacement = """function renderTeachers() { const grid = document.getElementById('teachersGrid'); if (!grid) return; const t = Array.isArray(state.settings.teachers) ? state.settings.teachers : []; if (t.length === 0) { grid.innerHTML = `<div class="memory-empty" style="grid-column:1/-1;"><h3>No teachers configured</h3></div>`; return; } grid.innerHTML = t.map(teacher => { const initials = getInitials(teacher.name || 'T'); const img = (teacher.imageUrl || '').trim(); return `<div class="teacher-card"><div class="teacher-image">${img ? `<img src="${escapeAttr(img)}" alt="${escapeAttr(teacher.name || '')}" />` : escapeHtml(initials)}</div><h3 class="teacher-name">${escapeHtml(teacher.name || '')}</h3><p class="teacher-subject">${escapeHtml(teacher.subject || '')}</p><p class="teacher-quote">${escapeHtml(teacher.quote || '')}</p></div>`; }).join(''); }"""
        text = replace_function(text, "renderTeachers", replacement)
        changes.append("index: fixed broken teachers renderer")

    if "function renderMemoriesPage()" not in text:
        memories_page_js = """
function renderMemoriesPage() {
 const grid = document.getElementById('memoryGridPage');
 const wrap = document.getElementById('loadMoreWrapPage');
 if (!grid) return;
 if (!state.memories.length) {
  grid.innerHTML = `<div class="memory-empty" style="grid-column: 1/-1;"><div class="memory-empty-icon">📷</div><h3>No Memories Yet</h3><p>Be the first to share!</p></div>`;
  if (wrap) wrap.style.display = 'none';
  return;
 }
 const displayMemories = state.memories;
 grid.innerHTML = displayMemories.map((memory, index) => `
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
function openMemoriesPage() {
 state.viewingAllMemoriesPage = true;
 const page = document.getElementById('memoriesPage');
 if (page) page.classList.remove('hidden');
 history.pushState({ memoriesPage: true }, '', '#memories-page');
 renderMemories();
 renderMemoriesPage();
 window.scrollTo({ top: 0, behavior: 'smooth' });
}
function backToMainPage() {
 state.viewingAllMemoriesPage = false;
 const page = document.getElementById('memoriesPage');
 if (page) page.classList.add('hidden');
 if (location.hash === '#memories-page') history.pushState({}, '', '#home');
 const home = document.getElementById('home');
 if (home) home.scrollIntoView({ behavior: 'smooth', block: 'start' });
 renderMemories();
}
"""
        text = text + "\n" + memories_page_js
        changes.append("index: restored memories page logic")

    text = re.sub(
        r"document\.addEventListener\('DOMContentLoaded', \(\) => \{\n const viewAllBtn = document\.getElementById\('viewAllMemoriesBtn'\);.*?window\.addEventListener\('popstate', \(\) => \{\n const page = document\.getElementById\('memoriesPage'\);.*?\n \}\);",
        """document.addEventListener('DOMContentLoaded', () => {
 const viewAllBtn = document.getElementById('viewAllMemoriesBtn');
 if (viewAllBtn) viewAllBtn.addEventListener('click', openMemoriesPage);
 const backBtn = document.getElementById('backToHomeFromMemoriesPage');
 if (backBtn) backBtn.addEventListener('click', backToMainPage);
 const loadMoreBtnPage = document.getElementById('loadMoreBtnPage');
 if (loadMoreBtnPage) loadMoreBtnPage.addEventListener('click', async () => {
  await loadMemories(false);
  renderMemoriesPage();
 });
 document.querySelectorAll('a[href="#home"]').forEach(el => {
  el.addEventListener('click', (evt) => {
   evt.preventDefault();
   backToMainPage();
  });
 });
});
window.addEventListener('popstate', () => {
 const page = document.getElementById('memoriesPage');
 if (!page) return;
 if (location.hash === '#memories-page') {
  state.viewingAllMemoriesPage = true;
  page.classList.remove('hidden');
  renderMemoriesPage();
 } else {
  state.viewingAllMemoriesPage = false;
  page.classList.add('hidden');
  renderMemories();
 }
});""",
        text,
        count=1,
        flags=re.S,
    )

    if "if (state.viewingAllMemoriesPage) renderMemoriesPage();" not in text:
        text = text.replace(
            " if (loadMoreWrap) {\n loadMoreWrap.style.display = (!state.infiniteScroll && state.memHasMore && state.viewingAllMemoriesPage) ? 'flex' : 'none';\n }\n}",
            " if (loadMoreWrap) {\n loadMoreWrap.style.display = (!state.infiniteScroll && state.memHasMore && state.viewingAllMemoriesPage) ? 'flex' : 'none';\n }\n if (state.viewingAllMemoriesPage) renderMemoriesPage();\n}",
            1,
        )

    text = text.replace(
        "if(localStorage.getItem('moodVote'))return ffNotify('info','Already voted','You already shared your mood! ');",
        "if(localStorage.getItem('moodVote'))return ffNotify('info','Already voted','You already shared your mood.');",
    )

    if "async function sniperCollectClientErrors" not in text:
        sniper_error_block = """
async function sniperCollectClientErrors() {
 const issues = [];
 try {
  if (!Array.isArray(state.memories) || state.memories.length === 0) issues.push('Memories list is empty or not loading.');
  const teachersGrid = document.getElementById('teachersGrid');
  if (teachersGrid && !teachersGrid.children.length) issues.push('Teachers section is empty.');
  const timelineList = document.getElementById('timelineList');
  if (timelineList && !timelineList.children.length) issues.push('Timeline section is empty.');
  if (typeof state.settings !== 'object') issues.push('Settings object is missing.');
  if (location.hash === '#memories-page' && typeof renderMemoriesPage !== 'function') issues.push('Dedicated memories page is missing renderer.');
 } catch (e) {
  issues.push('Client inspection failed: ' + e.message);
 }
 return issues;
}
window.sniperCollectClientErrors = sniperCollectClientErrors;"""
        text += "\n" + sniper_error_block
        changes.append("index: added sniper client error collector")

    if "async function loadStudentDirectoryForAdmin()" not in text:
        admin_student_tools = """
async function loadStudentDirectoryForAdmin() {
 try {
  const res = await fetch(apiUrl('/api/student-directory'));
  const data = await res.json();
  if (!data.success) return [];
  return Array.isArray(data.students) ? data.students : [];
 } catch (_) {
  return [];
 }
}
"""
        text += "\n" + admin_student_tools
        changes.append("index: added admin student directory helper")

    if "function openOsmPickerModal" not in text:
        osm_picker_css = """
<style id="sniper-osm-picker-style">
.osm-picker-modal{position:fixed;inset:0;background:rgba(0,0,0,.82);z-index:12050;display:none;align-items:center;justify-content:center;padding:20px}
.osm-picker-modal.active{display:flex}
.osm-picker-card{width:min(1100px,96vw);height:min(760px,90vh);background:var(--navy-medium);border:1px solid var(--glass-border);border-radius:24px;padding:18px;display:grid;grid-template-rows:auto auto 1fr auto;gap:12px}
.osm-picker-top{display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap}
.osm-picker-search{display:grid;grid-template-columns:1fr auto;gap:10px}
.osm-picker-map{border-radius:18px;overflow:hidden;border:1px solid rgba(255,255,255,.12)}
.osm-picker-map-inner{width:100%;height:100%}
.osm-picker-results{display:grid;gap:8px;max-height:120px;overflow:auto}
</style>"""
        if "</head>" in text and "sniper-osm-picker-style" not in text:
            text = text.replace("</head>", osm_picker_css + "\n</head>", 1)

        osm_picker_html = """
<div class="osm-picker-modal" id="osmPickerModal">
 <div class="osm-picker-card">
  <div class="osm-picker-top">
   <div>
    <h3 style="margin:0;color:var(--primary-gold);font-family:var(--font-display);">Future Place Picker</h3>
    <p style="margin:4px 0 0;color:var(--text-muted);">Search like Blinkit style, click result, adjust marker, then confirm.</p>
   </div>
   <button class="btn btn-secondary" type="button" onclick="closeOsmPickerModal()">Close</button>
  </div>
  <div class="osm-picker-search">
   <input class="form-input" id="osmPickerSearchInput" placeholder="Search city, college, locality, address..." />
   <button class="btn btn-primary" type="button" id="osmPickerSearchBtn">Search</button>
  </div>
  <div class="osm-picker-map"><div class="osm-picker-map-inner" id="osmPickerMap"></div></div>
  <div>
   <div class="osm-picker-results" id="osmPickerResults"></div>
   <div style="display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap;align-items:center;margin-top:8px;">
    <div class="mini-pill" id="osmPickerSelectedText">No place selected yet.</div>
    <button class="btn btn-primary" type="button" id="osmPickerConfirmBtn">Use This Place</button>
   </div>
  </div>
 </div>
</div>"""
        if "</body>" in text and 'id="osmPickerModal"' not in text:
            text = text.replace("</body>", osm_picker_html + "\n</body>", 1)

        osm_picker_js = """
<script id="sniper-osm-picker-script">
(function(){
 if (window.__OSM_PICKER_PATCH__) return;
 window.__OSM_PICKER_PATCH__ = true;
 let pickerMap = null;
 let pickerMarker = null;
 let pickerSelection = null;
 let pickerTarget = 'school';
 function ensurePickerMap() {
  if (!window.L) return;
  if (pickerMap) {
   pickerMap.invalidateSize();
   return;
  }
  pickerMap = L.map('osmPickerMap', { center:[20.5937, 78.9629], zoom:4, worldCopyJump:true });
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
   maxZoom: 18,
   attribution: '&copy; OpenStreetMap contributors'
  }).addTo(pickerMap);
  pickerMap.on('click', (e) => {
   setPickerSelection(e.latlng.lat, e.latlng.lng, `${e.latlng.lat.toFixed(6)}, ${e.latlng.lng.toFixed(6)}`);
  });
 }
 function setPickerSelection(lat, lng, label) {
  pickerSelection = { lat:Number(lat), lng:Number(lng), label:String(label || '').trim() };
  if (!pickerMarker) pickerMarker = L.marker([lat, lng], { draggable:true }).addTo(pickerMap);
  pickerMarker.setLatLng([lat, lng]);
  pickerMarker.dragend = null;
  pickerMarker.on('dragend', () => {
   const pos = pickerMarker.getLatLng();
   pickerSelection.lat = Number(pos.lat);
   pickerSelection.lng = Number(pos.lng);
   updatePickerText();
  });
  pickerMap.setView([lat, lng], Math.max(pickerMap.getZoom(), 6));
  updatePickerText();
 }
 function updatePickerText() {
  const el = document.getElementById('osmPickerSelectedText');
  if (!el) return;
  if (!pickerSelection) {
   el.textContent = 'No place selected yet.';
   return;
  }
  el.textContent = `${pickerSelection.label || 'Selected place'} • ${pickerSelection.lat.toFixed(6)}, ${pickerSelection.lng.toFixed(6)}`;
 }
 window.openOsmPickerModal = function(targetType) {
  pickerTarget = targetType === 'university' ? 'university' : 'school';
  const modal = document.getElementById('osmPickerModal');
  if (modal) modal.classList.add('active');
  setTimeout(ensurePickerMap, 50);
 };
 window.closeOsmPickerModal = function() {
  const modal = document.getElementById('osmPickerModal');
  if (modal) modal.classList.remove('active');
 };
 async function doSearch() {
  const q = document.getElementById('osmPickerSearchInput')?.value?.trim();
  if (!q) return;
  const box = document.getElementById('osmPickerResults');
  if (box) box.innerHTML = '<div class="mini-pill">Searching...</div>';
  try {
   const res = await fetch(apiUrl('/api/admin/destinations-search'), {
    method:'POST',
    headers:{'Content-Type':'application/json','Authorization':'Bearer ' + (window.state?.adminToken || '')},
    body:JSON.stringify({ query:q })
   });
   const data = await res.json();
   const results = data.success ? (data.results || []) : [];
   if (!box) return;
   if (!results.length) {
    box.innerHTML = '<div class="mini-pill">No results found.</div>';
    return;
   }
   box.innerHTML = results.map((r, i) => `<button type="button" class="btn btn-secondary" data-index="${i}">${escapeHtml(r.place || r.name || 'Result')}</button>`).join('');
   box.querySelectorAll('button').forEach(btn => {
    btn.addEventListener('click', () => {
     const r = results[Number(btn.dataset.index)];
     setPickerSelection(r.lat, r.lng, r.place || r.name || q);
    });
   });
  } catch (e) {
   if (box) box.innerHTML = `<div class="mini-pill">Search failed: ${escapeHtml(e.message)}</div>`;
  }
 }
 document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('osmPickerSearchBtn')?.addEventListener('click', doSearch);
  document.getElementById('osmPickerConfirmBtn')?.addEventListener('click', () => {
   if (!pickerSelection) return;
   if (pickerTarget === 'school') {
    window.__SNIPER_RUNTIME__ = window.__SNIPER_RUNTIME__ || {};
    window.__SNIPER_RUNTIME__.selectedSchool = { lat: pickerSelection.lat, lng: pickerSelection.lng, label: pickerSelection.label };
   } else {
    window.__SNIPER_RUNTIME__ = window.__SNIPER_RUNTIME__ || {};
    window.__SNIPER_RUNTIME__.selectedUniversity = { lat: pickerSelection.lat, lng: pickerSelection.lng, label: pickerSelection.label };
   }
   if (typeof refreshDistanceReviewV7 === 'function') refreshDistanceReviewV7();
   if (typeof renderGlobeV7 === 'function') loadClassPathsGlobeV7?.();
   closeOsmPickerModal();
  });
 });
})();
</script>"""
        if "</body>" in text and 'id="sniper-osm-picker-script"' not in text:
            text = text.replace("</body>", osm_picker_js + "\n</body>", 1)
        changes.append("index: added accurate OpenStreetMap search picker modal")

    if "upgradeDistanceFlowToMaps" in text:
        upgraded_distance_flow = """function upgradeDistanceFlowToMaps(){
 const section = document.getElementById('distanceMapSection');
 const controls = document.getElementById('distanceControls');
 if (!section || !controls || document.getElementById('distanceMapsFlowCard')) return;
 const info = document.createElement('div');
 info.id = 'distanceMapsFlowCard';
 info.innerHTML = `
 <strong>How this works:</strong>
 pick whether you are saving your 11th / 12th place or your university dream,
 open the built-in accurate place picker, search the place, fine-tune the marker, and save it.
 `;
 controls.insertAdjacentElement('beforebegin', info);
 const panel = document.createElement('div');
 panel.id = 'distanceConfirmPanel';
 panel.innerHTML = `
 <div class="row">
  <div class="form-group">
   <label>Your Name</label>
   <select class="form-select" id="distanceStudentNameV7"><option value="">Select your name</option></select>
  </div>
  <div class="form-group">
   <label>Your Section</label>
   <select class="form-select" id="distanceSectionV7">
    <option value="">Select section</option>
    <option value="10A">10A</option>
    <option value="10B">10B</option>
    <option value="10C">10C</option>
    <option value="10D">10D</option>
   </select>
  </div>
 </div>
 <div class="row">
  <div class="form-group">
   <label>What are you pinning?</label>
   <select class="form-select" id="distancePinTypeV7">
    <option value="school">11th / 12th future place</option>
    <option value="university">University aim place</option>
   </select>
  </div>
  <div class="form-group">
   <label>Search place</label>
   <div style="display:flex;gap:10px;">
    <input class="form-input" id="distancePlaceLabelV7" maxlength="120" placeholder="Search city, college, locality..." />
    <button class="btn btn-primary" type="button" id="distanceOpenMapsV7">Open Picker</button>
   </div>
  </div>
 </div>
 <div style="display:flex; gap:10px; flex-wrap:wrap; justify-content:center; margin-top:12px;">
  <button class="btn btn-secondary" type="button" id="distancePickSchoolBtn">Pick 11th / 12th</button>
  <button class="btn btn-secondary" type="button" id="distancePickUniversityBtn">Pick University</button>
  <button class="btn btn-primary" type="button" id="distanceSavePinsV7">Confirm Future Path</button>
 </div>
 <div class="hint">Every saved location is reflected in the admin dashboard and the public globe.</div>
 <div id="distanceSelectedReview"></div>
 </div>`;
 controls.insertAdjacentElement('afterend', panel);
 controls.innerHTML = `
 <button class="btn btn-primary" type="button" id="distanceLaunchBtnV7">Start Future Pinning</button>
 <button class="btn btn-secondary" type="button" id="distanceRefreshBtnV7">Refresh Globe</button>
 `;
 document.getElementById('distanceLaunchBtnV7')?.addEventListener('click', () => {
  panel.classList.add('active');
  section.scrollIntoView({ behavior: 'smooth', block: 'start' });
  if (typeof loadStudentDirectoryV7 === 'function') loadStudentDirectoryV7();
 });
 document.getElementById('distanceOpenMapsV7')?.addEventListener('click', () => {
  const type = document.getElementById('distancePinTypeV7')?.value || 'school';
  openOsmPickerModal(type);
 });
 document.getElementById('distancePickSchoolBtn')?.addEventListener('click', () => openOsmPickerModal('school'));
 document.getElementById('distancePickUniversityBtn')?.addEventListener('click', () => openOsmPickerModal('university'));
 document.getElementById('distanceSavePinsV7')?.addEventListener('click', saveFuturePathV7);
 document.getElementById('distanceRefreshBtnV7')?.addEventListener('click', () => loadClassPathsGlobeV7());
 loadClassPathsGlobeV7();
}"""
        text = replace_function(text, "upgradeDistanceFlowToMaps", upgraded_distance_flow)
        changes.append("index: replaced inaccurate map flow with built-in OSM picker flow")

    if "async function loadStudentDirectoryV7()" in text and "distanceSectionV7" in text:
        upgraded_directory_loader = """async function loadStudentDirectoryV7(){
 try{
  const res = await fetch(apiUrl('/api/student-directory'));
  const data = await res.json();
  const students = data.success ? (data.students || []) : [];
  const nameSel = document.getElementById('distanceStudentNameV7');
  const sectionSel = document.getElementById('distanceSectionV7');
  if (nameSel) {
   nameSel.innerHTML = '<option value="">Select your name</option>' + students.map(s => `<option value="${escapeAttr(s.name)}" data-section="${escapeAttr(s.section)}">${escapeHtml(s.name)} (${escapeHtml(s.section)})</option>`).join('');
   nameSel.onchange = () => {
    const opt = nameSel.options[nameSel.selectedIndex];
    if (opt && sectionSel && opt.getAttribute('data-section')) sectionSel.value = opt.getAttribute('data-section');
   };
  }
  if (sectionSel) {
   const sections = Array.from(new Set(students.map(s => String(s.section || '').trim()).filter(Boolean)));
   sectionSel.innerHTML = '<option value="">Select section</option>' + sections.map(s => `<option value="${escapeAttr(s)}">${escapeHtml(s)}</option>`).join('');
  }
 }catch(_){}
}"""
        text = replace_function(text, "loadStudentDirectoryV7", upgraded_directory_loader)
        changes.append("index: improved student directory loading for map flow")

    if "async function saveFuturePathV7()" in text:
        upgraded_save_future = """async function saveFuturePathV7(){
 const studentName = document.getElementById('distanceStudentNameV7')?.value?.trim();
 const section = document.getElementById('distanceSectionV7')?.value?.trim();
 const schoolPoint = window.__SNIPER_RUNTIME__?.selectedSchool || null;
 const universityPoint = window.__SNIPER_RUNTIME__?.selectedUniversity || null;
 const schoolPlaceName = schoolPoint?.label || '';
 const universityPlaceName = universityPoint?.label || '';
 if (!studentName) return window.showNotification?.('error', 'Name needed', 'Select your name first.');
 if (!section) return window.showNotification?.('error', 'Section needed', 'Select your section first.');
 if (!schoolPoint && !universityPoint) return window.showNotification?.('error', 'No place selected', 'Open the built-in picker and select at least one place.');
 try{
  const res = await fetch(apiUrl('/api/destinations/pin-submit'), {
   method:'POST',
   headers:{'Content-Type':'application/json'},
   body:JSON.stringify({ studentName, section, schoolPlaceName, universityPlaceName, schoolPoint, universityPoint })
  });
  const data = await res.json();
  if (!data.success) return window.showNotification?.('error', 'Could not save', data.error || 'Save failed.');
  window.showNotification?.('success', 'Saved', 'Your future path is now on the class globe.');
  loadClassPathsGlobeV7();
 }catch(e){
  window.showNotification?.('error', 'Could not save', e.message);
 }
}"""
        text = replace_function(text, "saveFuturePathV7", upgraded_save_future)
        changes.append("index: future path save now includes section and labels")

    if "window.voteMood=async function(key)" in text:
        mood_vote_fixed = """window.voteMood=async function(key){
 if(localStorage.getItem('moodVote'))return ffNotify('info','Already voted','You already shared your mood.');
 moodData[key]=(moodData[key]||0)+1;localStorage.setItem('moodVote',key);renderMoodBoard();
 try{await ffPost('/api/fun/mood',{mood:key})}catch(_){}
 ffNotify('success','Vibe noted!','Your mood has been added.');
};"""
        text = re.sub(r"window\.voteMood=async function\(key\)\{.*?\n \};", mood_vote_fixed, text, count=1, flags=re.S)
        changes.append("index: fixed mood board duplicate message")

    diagnostics_block = """
<script id="sniper-full-diagnostics-script">
(function(){
 if (window.__SNIPER_FULL_DIAGNOSTICS__) return;
 window.__SNIPER_FULL_DIAGNOSTICS__ = true;
 async function sniperCollectClientErrors() {
  const issues = [];
  try {
   if (!Array.isArray(window.state?.memories)) issues.push('Memories state is missing.');
   if (Array.isArray(window.state?.memories) && window.state.memories.length === 0) issues.push('Memories are not loading.');
   const tg = document.getElementById('teachersGrid');
   if (tg && tg.children.length === 0) issues.push('Teachers are not loading.');
   const tl = document.getElementById('timelineList');
   if (tl && tl.children.length === 0) issues.push('Timeline is not loading.');
   if (document.getElementById('viewAllMemoriesBtn') === null) issues.push('View All Memories button is missing.');
  } catch (e) {
   issues.push('Client diagnostics failed: ' + e.message);
  }
  return issues;
 }
 async function sniperShowAllErrors() {
  const issues = await sniperCollectClientErrors();
  if (!issues.length) {
   if (typeof showNotification === 'function') showNotification('success', 'Diagnostics', 'No obvious client issues found.');
   return;
  }
  if (typeof showNotification === 'function') showNotification('error', 'Diagnostics', issues.join(' | '));
  console.error('SNIPER diagnostics:', issues);
 }
 window.sniperCollectClientErrors = sniperCollectClientErrors;
 window.sniperShowAllErrors = sniperShowAllErrors;
 document.addEventListener('DOMContentLoaded', () => {
  setTimeout(() => {
   const fab = document.getElementById('featureTourFab');
   if (fab && !document.getElementById('sniperErrorFab')) {
    const btn = document.createElement('button');
    btn.id = 'sniperErrorFab';
    btn.className = 'feature-tour-fab';
    btn.style.bottom = '66px';
    btn.textContent = 'Errors';
    btn.addEventListener('click', sniperShowAllErrors);
    document.body.appendChild(btn);
   }
  }, 500);
 });
})();
</script>"""
    if 'id="sniper-full-diagnostics-script"' not in text and "</body>" in text:
        text = text.replace("</body>", diagnostics_block + "\n</body>", 1)
        changes.append("index: sniper now shows all client errors together")

    return text, changes


def main() -> None:
    root = Path.cwd()
    index_path = root / "index.html"
    server_path = root / "server.js"

    if not index_path.exists():
        fail("index.html not found in current directory")
    if not server_path.exists():
        fail("server.js not found in current directory")

    original_index = read_text(index_path)
    original_server = read_text(server_path)

    new_index, index_changes = patch_index_html(original_index)
    new_server, server_changes = patch_server_js(original_server)

    backups = []
    modified = []

    if new_index != original_index:
        backups.append(backup_file(index_path))
        write_text(index_path, new_index)
        modified.append("index.html")

    if new_server != original_server:
        backups.append(backup_file(server_path))
        write_text(server_path, new_server)
        modified.append("server.js")

    print(json.dumps({
        "success": True,
        "modified": modified,
        "backups": backups,
        "changes": server_changes + index_changes
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()