#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from pathlib import Path


def die(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    sys.exit(1)


def read_file(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        die(f"Missing file: {path}")
    except Exception as exc:
        die(f"Could not read {path}: {exc}")


def write_file(path: Path, content: str) -> None:
    try:
        path.write_text(content, encoding="utf-8", newline="\n")
    except Exception as exc:
        die(f"Could not write {path}: {exc}")


def backup(path: Path) -> None:
    bak = path.with_suffix(path.suffix + ".blindrun.bak")
    if not bak.exists():
        write_file(bak, read_file(path))


def inject_after_line_if_found(text: str, exact_line: str, block: str) -> str:
    if block.strip() in text:
        return text
    marker = exact_line + "\n"
    idx = text.find(marker)
    if idx == -1:
        return text
    pos = idx + len(marker)
    return text[:pos] + block + "\n" + text[pos:]


def inject_before_if_found(text: str, marker: str, block: str) -> str:
    if block.strip() in text:
        return text
    idx = text.find(marker)
    if idx == -1:
        return text
    return text[:idx] + block + "\n" + text[idx:]


def inject_after_function_if_found(text: str, function_name: str, block: str) -> str:
    if block.strip() in text:
        return text
    needle = f"function {function_name}("
    start = text.find(needle)
    if start == -1:
        return text
    brace_start = text.find("{", start)
    if brace_start == -1:
        return text
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
    return text[:end] + block + "\n" + text[end:]


def replace_route_if_found(text: str, route_signature: str, replacement: str) -> str:
    start = text.find(route_signature)
    if start == -1:
        return text
    brace_start = text.find("{", start)
    if brace_start == -1:
        return text
    depth = 0
    end = None
    i = brace_start
    while i < len(text):
        ch = text[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                semi = text.find(");", i)
                if semi == -1:
                    return text
                end = semi + 2
                break
        i += 1
    if end is None:
        return text
    return text[:start] + replacement + text[end:]


def patch_server_js(server_path: Path) -> None:
    original = read_file(server_path).replace("\r\n", "\n")
    text = original

    if "app.use('/music', express.static(path.join(__dirname, 'music')));" not in text:
        text = text.replace(
            "app.use('/uploads', express.static(path.join(__dirname, 'uploads')));",
            "app.use('/uploads', express.static(path.join(__dirname, 'uploads')));\napp.use('/music', express.static(path.join(__dirname, 'music')));",
            1,
        )

    extra_paths_block = """const funPath = path.join(databaseDir, 'fun_features.json');
const teacherAudioPath = path.join(databaseDir, 'teacher_audio.json');
const paperNotesPath = path.join(databaseDir, 'paper_notes.json');
const destinationsPath = path.join(databaseDir, 'destinations.json');"""
    text = inject_after_line_if_found(
        text,
        "const studentDirectoryPath = path.join(databaseDir, 'student_directory.json');",
        extra_paths_block,
    )

    helper_block = """
function readStudentDirectory() {
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
}"""
    if "function readStudentDirectory()" not in text:
        text = inject_after_function_if_found(text, "writeCompilations", helper_block)

    init_insert = """
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
 }"""
    if "if (!fs.existsSync(studentDirectoryPath)) {" not in text:
        text = inject_after_function_if_found(text, "initDatabase", init_insert)

    text = text.replace(
        "transitionType: ['fade', 'slide', 'zoom', 'flip'].includes(transitionType) ? transitionType : 'fade',",
        "transitionType: ['fade', 'slide', 'zoom', 'flip', 'blur'].includes(transitionType) ? transitionType : 'fade',",
    )
    text = text.replace(
        "if (transitionType && ['fade', 'slide', 'zoom', 'flip'].includes(transitionType)) {",
        "if (transitionType && ['fade', 'slide', 'zoom', 'flip', 'blur'].includes(transitionType)) {",
    )

    compilations_list_route = """app.get('/api/compilations', (req, res) => {
 try {
 const data = readCompilations();
 const db = readDB();
 const compilations = (data.compilations || []).map(comp => ({
  ...comp,
  slides: (comp.slides || []).map(s => {
   const memory = db.memories.find(m => m.id === Number(s.memoryId) && !m.purgedAt);
   return { ...s, file_url: memory ? `/uploads/${memory.file_path}` : null };
  })
 }));
 res.json({ success: true, compilations });
 } catch (e) {
 res.status(500).json({ success: false, error: e.message });
 }
});"""
    if "app.get('/api/compilations', (req, res) => {" in text and "const db = readDB();" not in text[text.find("app.get('/api/compilations', (req, res) => {"):text.find("app.get('/api/compilations/:id', (req, res) => {") if "app.get('/api/compilations/:id', (req, res) => {" in text else len(text)]:
        text = replace_route_if_found(text, "app.get('/api/compilations', (req, res) => {", compilations_list_route)

    compilations_single_route = """app.get('/api/compilations/:id', (req, res) => {
 try {
 const id = parseInt(req.params.id, 10);
 const data = readCompilations();
 const db = readDB();
 const comp = data.compilations.find(c => c.id === id);
 if (!comp) return res.status(404).json({ success: false, error: 'Not found' });
 const slides = (comp.slides || []).map(s => {
  const memory = db.memories.find(m => m.id === Number(s.memoryId) && !m.purgedAt);
  return { ...s, file_url: memory ? `/uploads/${memory.file_path}` : null };
 });
 res.json({ success: true, compilation: { ...comp, slides } });
 } catch (e) {
 res.status(500).json({ success: false, error: e.message });
 }
});"""
    if "app.get('/api/compilations/:id', (req, res) => {" in text:
        start = text.find("app.get('/api/compilations/:id', (req, res) => {")
        chunk = text[start:start + 1200]
        if "const db = readDB();" not in chunk:
            text = replace_route_if_found(text, "app.get('/api/compilations/:id', (req, res) => {", compilations_single_route)

    fun_block = """// --- FUN FEATURES API INJECTED ---
app.get('/api/fun/settings', (req, res) => res.json({ success: true, settings: readFun().settings || {} }));
app.post('/api/fun/settings', (req, res) => {
 try {
  const auth = requireAdmin(req, res); if (!auth) return;
  if (!hasPerm(auth.user, 'settings')) return res.status(403).json({ success: false, error: 'Forbidden' });
  const db = readFun();
  db.settings = req.body?.settings || {};
  writeFun(db);
  res.json({ success: true });
 } catch (e) {
  res.status(500).json({ success: false, error: e.message });
 }
});
app.get('/api/fun/gratitude', (req, res) => res.json({ success: true, notes: readFun().gratitude || [] }));
app.post('/api/fun/gratitude', (req, res) => {
 try {
  const db = readFun();
  db.gratitude = Array.isArray(db.gratitude) ? db.gratitude : [];
  db.gratitude.unshift({ ...req.body, created_at: new Date().toISOString() });
  db.gratitude = db.gratitude.slice(0, 500);
  writeFun(db);
  res.json({ success: true });
 } catch (e) {
  res.status(500).json({ success: false, error: e.message });
 }
});
app.get('/api/fun/superlatives', (req, res) => {
 try {
  const db = readFun();
  res.json({ success: true, categories: Array.isArray(db.superlatives?.categories) ? db.superlatives.categories : [] });
 } catch (e) {
  res.status(500).json({ success: false, error: e.message });
 }
});
app.post('/api/fun/superlatives/nominee', (req, res) => {
 try {
  const db = readFun();
  db.superlatives = db.superlatives || { categories: [] };
  db.superlatives.categories = Array.isArray(db.superlatives.categories) ? db.superlatives.categories : [];
  let cat = db.superlatives.categories.find(c => Number(c.id) === Number(req.body?.categoryId));
  if (!cat) {
   cat = { id: Number(req.body?.categoryId), emoji: '🏆', title: 'Category ' + String(req.body?.categoryId || ''), nominees: [] };
   db.superlatives.categories.push(cat);
  }
  cat.nominees = Array.isArray(cat.nominees) ? cat.nominees : [];
  const name = String(req.body?.name || '').trim().substring(0, 60);
  if (!name) return res.status(400).json({ success: false, error: 'name required' });
  if (!cat.nominees.find(n => String(n.name || '').toLowerCase() === name.toLowerCase())) {
   cat.nominees.push({ id: Date.now(), name, votes: 0 });
  }
  writeFun(db);
  res.json({ success: true });
 } catch (e) {
  res.status(500).json({ success: false, error: e.message });
 }
});
app.post('/api/fun/superlatives/vote', (req, res) => {
 try {
  const db = readFun();
  const cat = db.superlatives?.categories?.find(c => Number(c.id) === Number(req.body?.categoryId));
  if (!cat) return res.status(404).json({ success: false, error: 'Category not found' });
  const nom = (cat.nominees || []).find(n => String(n.id) === String(req.body?.nomineeId) || String(n.name) === String(req.body?.nomineeId));
  if (!nom) return res.status(404).json({ success: false, error: 'Nominee not found' });
  nom.votes = (nom.votes || 0) + 1;
  writeFun(db);
  res.json({ success: true });
 } catch (e) {
  res.status(500).json({ success: false, error: e.message });
 }
});
app.get('/api/fun/wishes', (req, res) => res.json({ success: true, wishes: readFun().wishes || [] }));
app.post('/api/fun/wishes', (req, res) => {
 try {
  const db = readFun();
  db.wishes = Array.isArray(db.wishes) ? db.wishes : [];
  db.wishes.unshift({ ...req.body, created_at: new Date().toISOString() });
  db.wishes = db.wishes.slice(0, 500);
  writeFun(db);
  res.json({ success: true });
 } catch (e) {
  res.status(500).json({ success: false, error: e.message });
 }
});
app.get('/api/fun/dedications', (req, res) => res.json({ success: true, dedications: readFun().dedications || [] }));
app.post('/api/fun/dedications', (req, res) => {
 try {
  const db = readFun();
  db.dedications = Array.isArray(db.dedications) ? db.dedications : [];
  db.dedications.unshift({ ...req.body, created_at: new Date().toISOString() });
  db.dedications = db.dedications.slice(0, 500);
  writeFun(db);
  res.json({ success: true });
 } catch (e) {
  res.status(500).json({ success: false, error: e.message });
 }
});
app.get('/api/fun/mood', (req, res) => res.json({ success: true, votes: (readFun().mood || {}).votes || {} }));
app.post('/api/fun/mood', (req, res) => {
 try {
  const db = readFun();
  db.mood = db.mood || { votes: {} };
  db.mood.votes = db.mood.votes || {};
  const mood = String(req.body?.mood || '').trim();
  if (!mood) return res.status(400).json({ success: false, error: 'mood required' });
  db.mood.votes[mood] = (db.mood.votes[mood] || 0) + 1;
  writeFun(db);
  res.json({ success: true });
 } catch (e) {
  res.status(500).json({ success: false, error: e.message });
 }
});
app.get('/api/fun/capsules', (req, res) => res.json({ success: true, capsules: readFun().capsules || [] }));
app.post('/api/fun/capsules', (req, res) => {
 try {
  const db = readFun();
  db.capsules = Array.isArray(db.capsules) ? db.capsules : [];
  db.capsules.unshift({ ...req.body, created_at: new Date().toISOString() });
  db.capsules = db.capsules.slice(0, 500);
  writeFun(db);
  res.json({ success: true });
 } catch (e) {
  res.status(500).json({ success: false, error: e.message });
 }
});
// ----------------------------------"""
    if "app.get('/api/fun/settings', (req, res) => res.json({ success: true, settings: readFun().settings || {} }));" not in text:
        if "// --- FUN FEATURES API INJECTED ---" in text and "// ----------------------------------" in text:
            text = re.sub(
                r"// --- FUN FEATURES API INJECTED ---.*?// ----------------------------------",
                fun_block,
                text,
                count=1,
                flags=re.S,
            )
        else:
            text = inject_before_if_found(
                text,
                "// ═══════════════════════════════════════════════════════════════════════════════\n// START SERVER",
                fun_block,
            )

    addon_block = """
function getClientIp(req) {
 return String(req.headers['x-forwarded-for'] || req.socket.remoteAddress || '').split(',')[0].trim();
}
function isRateLimited(items, ip, maxCount, windowMs) {
 const now = Date.now();
 return items.filter(x => String(x.ip || '') === ip && (now - new Date(x.createdAt).getTime()) <= windowMs).length >= maxCount;
}
app.get('/api/teacher-audio', (req, res) => {
 try {
  const db = readTeacherAudio();
  res.json({ success: true, items: db.items || [] });
 } catch (e) {
  res.status(500).json({ success: false, error: e.message });
 }
});
app.post('/api/admin/teacher-audio', adminUpload.single('audio'), (req, res) => {
 try {
  const auth = requireAdmin(req, res);
  if (!auth) return;
  if (!hasPerm(auth.user, 'settings')) return res.status(403).json({ success: false, error: 'Forbidden' });
  const teacherName = String(req.body?.teacherName || '').trim().substring(0, 80);
  const file = req.file;
  if (!teacherName) return res.status(400).json({ success: false, error: 'teacherName required' });
  if (!file) return res.status(400).json({ success: false, error: 'audio file required' });
  const db = readTeacherAudio();
  let item = db.items.find(x => String(x.teacherName || '').toLowerCase() === teacherName.toLowerCase());
  if (!item) {
   item = { id: db.nextId++, teacherName, audioPath: file.filename, createdAt: nowIso(), updatedAt: nowIso() };
   db.items.push(item);
  } else {
   const old = item.audioPath;
   item.audioPath = file.filename;
   item.updatedAt = nowIso();
   if (old) {
    const fp = path.join(uploadsDir, old);
    if (fs.existsSync(fp)) {
     try { fs.unlinkSync(fp); } catch (_) {}
    }
   }
  }
  writeTeacherAudio(db);
  const settings = readSettings();
  settings.settings = settings.settings || {};
  settings.settings.teachers = Array.isArray(settings.settings.teachers) ? settings.settings.teachers : [];
  const teacher = settings.settings.teachers.find(t => String(t.name || '').toLowerCase() === teacherName.toLowerCase());
  if (teacher) teacher.audioPath = file.filename;
  writeSettings(settings);
  audit(auth.user.id, 'upload-teacher-audio', { teacherName });
  broadcast('settings:update', {});
  res.json({ success: true, item });
 } catch (e) {
  res.status(500).json({ success: false, error: e.message });
 }
});
app.post('/api/admin/settings/intro-video', adminUpload.single('file'), (req, res) => {
 try {
  const auth = requireAdmin(req, res);
  if (!auth) return;
  if (!hasPerm(auth.user, 'settings')) return res.status(403).json({ success: false, error: 'Forbidden' });
  const file = req.file;
  if (!file) return res.status(400).json({ success: false, error: 'No video file' });
  const settings = readSettings();
  settings.settings = settings.settings || {};
  settings.settings.introVideoPath = file.filename;
  writeSettings(settings);
  audit(auth.user.id, 'upload-intro-video-alias', { filename: file.filename });
  broadcast('settings:update', {});
  res.json({ success: true, path: file.filename });
 } catch (e) {
  res.status(500).json({ success: false, error: e.message });
 }
});
app.delete('/api/admin/settings/intro-video', (req, res) => {
 try {
  const auth = requireAdmin(req, res);
  if (!auth) return;
  if (!hasPerm(auth.user, 'settings')) return res.status(403).json({ success: false, error: 'Forbidden' });
  const settings = readSettings();
  settings.settings = settings.settings || {};
  const old = settings.settings.introVideoPath;
  settings.settings.introVideoPath = null;
  writeSettings(settings);
  if (old) {
   const fp = path.join(uploadsDir, old);
   if (fs.existsSync(fp)) {
    try { fs.unlinkSync(fp); } catch (_) {}
   }
  }
  audit(auth.user.id, 'remove-intro-video-alias', {});
  broadcast('settings:update', {});
  res.json({ success: true });
 } catch (e) {
  res.status(500).json({ success: false, error: e.message });
 }
});
app.get('/api/destinations', (req, res) => {
 try {
  const db = readDestinationsDb();
  const items = (db.destinations || []).map(item => ({
   place: String(item.place || item.name || '').trim(),
   name: String(item.place || item.name || '').trim(),
   lat: Number.isFinite(Number(item.lat)) ? Number(item.lat) : undefined,
   lng: Number.isFinite(Number(item.lng)) ? Number(item.lng) : undefined
  })).filter(item => item.place);
  res.json({ success: true, destinations: items });
 } catch (e) {
  res.status(500).json({ success: false, error: e.message });
 }
});
app.post('/api/admin/destinations', (req, res) => {
 try {
  const auth = requireAdmin(req, res);
  if (!auth) return;
  if (!hasPerm(auth.user, 'settings')) return res.status(403).json({ success: false, error: 'Forbidden' });
  const raw = Array.isArray(req.body?.destinations) ? req.body.destinations : [];
  const cleaned = raw.map(x => ({ place: String(typeof x === 'string' ? x : x?.name || x?.place || '').trim() })).filter(x => x.place).slice(0, 500);
  const db = readDestinationsDb();
  db.destinations = cleaned;
  writeDestinationsDb(db);
  audit(auth.user.id, 'save-destinations', { count: cleaned.length });
  res.json({ success: true, count: cleaned.length });
 } catch (e) {
  res.status(500).json({ success: false, error: e.message });
 }
});
app.post('/api/admin/destinations-v2', (req, res) => {
 try {
  const auth = requireAdmin(req, res);
  if (!auth) return;
  if (!hasPerm(auth.user, 'settings')) return res.status(403).json({ success: false, error: 'Forbidden' });
  const places = Array.isArray(req.body?.places) ? req.body.places : [];
  const cleaned = places.map(item => {
   if (typeof item === 'string') return { place: item.trim() };
   return { place: String(item?.place || item?.name || '').trim(), lat: Number(item?.lat), lng: Number(item?.lng) };
  }).filter(item => item.place).slice(0, 1000);
  const db = readDestinationsDb();
  db.destinations = cleaned;
  writeDestinationsDb(db);
  audit(auth.user.id, 'save-destinations-v2-advanced', { count: cleaned.length });
  res.json({ success: true, count: cleaned.length });
 } catch (e) {
  res.status(500).json({ success: false, error: e.message });
 }
});
app.post('/api/destinations/submit', (req, res) => {
 try {
  const destination = String(req.body?.destination || '').trim();
  if (!destination) return res.status(400).json({ success: false, error: 'destination required' });
  const db = readDestinationsDb();
  const ok = (db.destinations || []).find(x => String(x.place || x.name || '').trim().toLowerCase() === destination.toLowerCase());
  if (!ok) return res.status(400).json({ success: false, error: 'Destination is not allowed' });
  db.submissions = Array.isArray(db.submissions) ? db.submissions : [];
  db.submissions.push({ id: db.nextId++, destination, ip: getClientIp(req), createdAt: nowIso() });
  if (db.submissions.length > 5000) db.submissions = db.submissions.slice(-5000);
  writeDestinationsDb(db);
  res.json({ success: true });
 } catch (e) {
  res.status(500).json({ success: false, error: e.message });
 }
});
app.post('/api/destinations/submit-v2', (req, res) => {
 try {
  const studentName = String(req.body?.studentName || '').trim().substring(0, 80);
  const schoolPlace = String(req.body?.schoolPlace || '').trim().substring(0, 120);
  const universityPlace = String(req.body?.universityPlace || '').trim().substring(0, 120);
  if (!studentName) return res.status(400).json({ success: false, error: 'studentName required' });
  if (!schoolPlace && !universityPlace) return res.status(400).json({ success: false, error: 'At least one place is required' });
  const db = readDestinationsDb();
  const allowed = new Set((db.destinations || []).map(x => String(x.place || x.name || '').trim().toLowerCase()));
  if (schoolPlace && !allowed.has(schoolPlace.toLowerCase())) return res.status(400).json({ success: false, error: 'School place is not allowed' });
  if (universityPlace && !allowed.has(universityPlace.toLowerCase())) return res.status(400).json({ success: false, error: 'University place is not allowed' });
  const existing = (db.submissions || []).find(x => String(x.studentName || '').trim().toLowerCase() === studentName.toLowerCase());
  if (existing) {
   existing.schoolPlace = schoolPlace;
   existing.universityPlace = universityPlace;
   existing.updatedAt = nowIso();
  } else {
   db.submissions.push({ id: db.nextId++, studentName, schoolPlace, universityPlace, createdAt: nowIso(), updatedAt: nowIso() });
  }
  if (db.submissions.length > 5000) db.submissions = db.submissions.slice(-5000);
  writeDestinationsDb(db);
  broadcast('destinations:update', { studentName });
  res.json({ success: true });
 } catch (e) {
  res.status(500).json({ success: false, error: e.message });
 }
});
app.get('/api/destinations/submissions', (req, res) => {
 try {
  const db = readDestinationsDb();
  res.json({ success: true, submissions: db.submissions || [] });
 } catch (e) {
  res.status(500).json({ success: false, error: e.message });
 }
});
app.post('/api/destinations/pin-submit', (req, res) => {
 try {
  const studentName = String(req.body?.studentName || '').trim().substring(0, 80);
  const section = String(req.body?.section || '').trim().substring(0, 10);
  const ranking = String(req.body?.ranking || '').trim().substring(0, 120);
  const schoolPlaceName = String(req.body?.schoolPlaceName || '').trim().substring(0, 160);
  const universityPlaceName = String(req.body?.universityPlaceName || '').trim().substring(0, 160);
  const schoolPoint = req.body?.schoolPoint || null;
  const universityPoint = req.body?.universityPoint || null;
  if (!studentName) return res.status(400).json({ success: false, error: 'studentName required' });
  const validPoint = p => p && Number.isFinite(Number(p.lat)) && Number.isFinite(Number(p.lng));
  if (!validPoint(schoolPoint) && !validPoint(universityPoint)) return res.status(400).json({ success: false, error: 'At least one valid point is required' });
  const db = readDestinationsDb();
  let existing = (db.submissions || []).find(x => String(x.studentName || '').trim().toLowerCase() === studentName.toLowerCase());
  const payload = {
   studentName,
   section,
   ranking,
   schoolPlaceName,
   universityPlaceName,
   schoolPoint: validPoint(schoolPoint) ? { lat: Number(schoolPoint.lat), lng: Number(schoolPoint.lng) } : null,
   universityPoint: validPoint(universityPoint) ? { lat: Number(universityPoint.lat), lng: Number(universityPoint.lng) } : null,
   updatedAt: nowIso()
  };
  if (existing) Object.assign(existing, payload);
  else db.submissions.push({ id: db.nextId++, createdAt: nowIso(), ...payload });
  if (db.submissions.length > 5000) db.submissions = db.submissions.slice(-5000);
  writeDestinationsDb(db);
  broadcast('destinations:pin-update', { studentName, section });
  res.json({ success: true });
 } catch (e) {
  res.status(500).json({ success: false, error: e.message });
 }
});
app.get('/api/destinations/pin-submissions', (req, res) => {
 try {
  const db = readDestinationsDb();
  res.json({ success: true, submissions: db.submissions || [] });
 } catch (e) {
  res.status(500).json({ success: false, error: e.message });
 }
});
app.post('/api/paper-notes', (req, res) => {
 try {
  const text = String(req.body?.text || '').trim().substring(0, 400);
  if (!text) return res.status(400).json({ success: false, error: 'text required' });
  const db = readPaperNotes();
  db.notes = Array.isArray(db.notes) ? db.notes : [];
  const note = { id: db.nextId++, text, ip: getClientIp(req), createdAt: nowIso() };
  db.notes.push(note);
  if (db.notes.length > 3000) db.notes = db.notes.slice(-3000);
  writePaperNotes(db);
  broadcast('paper:note', { note });
  res.json({ success: true, note });
 } catch (e) {
  res.status(500).json({ success: false, error: e.message });
 }
});
app.get('/api/paper-notes/random', (req, res) => {
 try {
  const db = readPaperNotes();
  const items = db.notes || [];
  if (!items.length) return res.json({ success: true, note: null });
  const note = items[Math.floor(Math.random() * items.length)];
  res.json({ success: true, note });
 } catch (e) {
  res.status(500).json({ success: false, error: e.message });
 }
});
app.post('/api/paper-notes/from-memory', (req, res) => {
 try {
  const memoryId = Number(req.body?.memoryId);
  const dbMem = readDB();
  const memory = dbMem.memories.find(m => m.id === memoryId && m.approved === 1 && !m.deletedAt && !m.purgedAt);
  if (!memory) return res.status(404).json({ success: false, error: 'Memory not found' });
  const db = readPaperNotes();
  db.notes = Array.isArray(db.notes) ? db.notes : [];
  const ip = getClientIp(req);
  if (isRateLimited(db.notes, ip, 5, 60 * 1000)) return res.status(429).json({ success: false, error: 'Rate limit exceeded. Maximum 5 notes per minute.' });
  const note = { id: db.nextId++, memoryId, caption: String(memory.caption || '').substring(0, 400), text: String(memory.caption || '').substring(0, 400), ip, createdAt: nowIso() };
  db.notes.push(note);
  if (db.notes.length > 3000) db.notes = db.notes.slice(-3000);
  writePaperNotes(db);
  broadcast('paper:note', { note });
  res.json({ success: true, note });
 } catch (e) {
  res.status(500).json({ success: false, error: e.message });
 }
});
app.get('/api/paper-notes/random-memory', (req, res) => {
 try {
  const db = readPaperNotes();
  const notes = (db.notes || []).filter(note => note.memoryId || note.caption || note.text);
  if (!notes.length) return res.json({ success: true, note: null });
  const note = notes[Math.floor(Math.random() * notes.length)];
  res.json({ success: true, note });
 } catch (e) {
  res.status(500).json({ success: false, error: e.message });
 }
});
wss.on('connection', (ws) => {
 ws.on('message', raw => {
  try {
   const data = JSON.parse(String(raw));
   if (!data || typeof data !== 'object') return;
   if (data.type === 'ghost:move') broadcast('ghost:move', data);
   if (data.type === 'paper:note:broadcast' && data.note) broadcast('paper:note', { note: data.note });
  } catch (_) {}
 });
});"""
    if "function getClientIp(req)" not in text:
        text = inject_before_if_found(
            text,
            "// ═══════════════════════════════════════════════════════════════════════════════\n// START SERVER",
            addon_block,
        )

    text = re.sub(
        r"// ═══════════════════════════════════════════════════════════════════════════════\n// SERVE FRONTEND\n// ═══════════════════════════════════════════════════════════════════════════════\napp\.get\('/', \(req, res\) => res\.sendFile\(path\.join\(__dirname, 'index\.html'\)\)\);\napp\.get\('\*', \(req, res\) => res\.sendFile\(path\.join\(__dirname, 'index\.html'\)\)\);",
        "// ═══════════════════════════════════════════════════════════════════════════════\n// SERVE FRONTEND\n// ═══════════════════════════════════════════════════════════════════════════════\napp.get('/', (req, res) => res.sendFile(path.join(__dirname, 'index.html')));",
        text,
        count=1,
        flags=re.S,
    )

    if "app.get('*', (req, res) => {" not in text and "server.listen(PORT, '0.0.0.0', () => {" in text:
        text = text.replace(
            "server.listen(PORT, '0.0.0.0', () => {",
            """app.get('*', (req, res) => {
 if (req.path.startsWith('/api/')) return res.status(404).json({ success: false, error: 'Endpoint not found' });
 if (req.path.startsWith('/uploads/') || req.path.startsWith('/music/')) return res.status(404).send('Not found');
 return res.sendFile(path.join(__dirname, 'index.html'));
});

server.listen(PORT, '0.0.0.0', () => {""",
            1,
        )

    if text != original:
        backup(server_path)
        write_file(server_path, text)


def patch_index_html(index_path: Path) -> None:
    original = read_file(index_path).replace("\r\n", "\n")
    text = original

    text = text.replace(
        "previewLimit: 6,\n viewingAllMemoriesPage: false,\n previewLimit: 6,\n viewingAllMemoriesPage: false,\n previewLimit: 6,\n viewingAllMemoriesPage: false,",
        "previewLimit: 6,\n viewingAllMemoriesPage: false,",
    )

    if "const displayMemories = state.viewingAllMemoriesPage ? state.memories : state.memories.slice(0, state.previewLimit);" not in text:
        text = text.replace(
            " if (displayMemories.length === 0) {",
            " const displayMemories = state.viewingAllMemoriesPage ? state.memories : state.memories.slice(0, state.previewLimit);\n if (displayMemories.length === 0) {",
            1,
        )

    if 'id="viewAllMemoriesBtn"' not in text:
        old = '<div class="load-more-wrap" id="loadMoreWrap" style="display:none;">\n <button class="btn btn-secondary load-more-btn" id="loadMoreBtn" type="button">Load More</button>\n </div>'
        new = '<div class="memories-preview-actions"><button class="btn btn-secondary" id="viewAllMemoriesBtn" type="button">View All Memories</button></div>\n <div class="load-more-wrap" id="loadMoreWrap" style="display:none;">\n <button class="btn btn-secondary load-more-btn" id="loadMoreBtn" type="button">Load More</button>\n </div>'
        if old in text:
            text = text.replace(old, new, 1)

    if 'id="memoriesPage"' not in text:
        marker = "</section>\n <!-- Teachers / Timeline / Quote / Footer kept from previous version (rendered from settings) -->"
        if marker in text:
            text = text.replace(
                marker,
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

    if "API_BASE: localStorage.getItem('farewell_api_base')" not in text:
        text = text.replace(
            'API_BASE: "https://threshold-superb-gasoline-theology.trycloudflare.com",',
            'API_BASE: localStorage.getItem(\'farewell_api_base\') || "https://threshold-superb-gasoline-theology.trycloudflare.com",',
            1,
        )

    text = text.replace(".replace(/\\/+ /g, '/')", ".replace(/\\/+/g, '/')")

    text = text.replace(
        "if (mode === 'maps'){\n window.open('https://www.google.com/maps/search/?api=1&query=' + query, '_blank');\n } else {",
        "if (mode === 'maps'){\n const frame = document.getElementById('distanceRealMapFrame');\n if (frame) frame.src = 'https://www.google.com/maps?q=' + query + '&z=6&output=embed';\n } else {",
    )

    if "function openMemoriesPage()" not in text:
        pattern = r"document\.addEventListener\('DOMContentLoaded', \(\) => \{\n const viewAllBtn = document\.getElementById\('viewAllMemoriesBtn'\);.*?window\.addEventListener\('popstate', \(\) => \{\n const page = document\.getElementById\('memoriesPage'\);.*?\n \}\);"
        replacement = """function renderMemoriesPage() {
 const grid = document.getElementById('memoryGridPage');
 const wrap = document.getElementById('loadMoreWrapPage');
 if (!grid) return;
 if (!state.memories.length) {
  grid.innerHTML = `<div class="memory-empty" style="grid-column: 1/-1;"><div class="memory-empty-icon">📷</div><h3>No Memories Yet</h3><p>Be the first to share!</p></div>`;
  if (wrap) wrap.style.display = 'none';
  return;
 }
 grid.innerHTML = document.getElementById('memoryGrid') ? document.getElementById('memoryGrid').innerHTML : '';
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
document.addEventListener('DOMContentLoaded', () => {
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
});"""
        text, count = re.subn(pattern, replacement, text, count=1, flags=re.S)
        if count == 0 and "function renderMemoriesPage()" not in text:
            text += "\n" + replacement + "\n"

    if "if (state.viewingAllMemoriesPage) renderMemoriesPage();" not in text:
        target = " if (loadMoreWrap) {\n loadMoreWrap.style.display = (!state.infiniteScroll && state.memHasMore && state.viewingAllMemoriesPage) ? 'flex' : 'none';\n }\n}"
        if target in text:
            text = text.replace(
                target,
                " if (loadMoreWrap) {\n loadMoreWrap.style.display = (!state.infiniteScroll && state.memHasMore && state.viewingAllMemoriesPage) ? 'flex' : 'none';\n }\n if (state.viewingAllMemoriesPage) renderMemoriesPage();\n}",
                1,
            )

    text = re.sub(
        r"<script id=\"fixer-tour-script\">.*?</script>\s*<script id=\"fixer-stable-tour-script\">.*?</script>\s*<script id=\"fixer-stable-tour-script\">.*?</script>",
        """<script id="fixer-stable-tour-script">
(function(){
 if (window.__FIXER_STABLE_TOUR__) return;
 window.__FIXER_STABLE_TOUR__ = true;
 const TOUR_KEY = 'cornerstone_tour_seen_v2';
 function addTourFab(){
  if (document.getElementById('featureTourFab')) return;
  const btn = document.createElement('button');
  btn.id = 'featureTourFab';
  btn.className = 'feature-tour-fab';
  btn.type = 'button';
  btn.textContent = 'Tutorial';
  btn.addEventListener('click', startSiteTour);
  document.body.appendChild(btn);
 }
 function ensureTourNodes(){
  if (!document.getElementById('featureTourOverlay')){
   const overlay = document.createElement('div');
   overlay.id = 'featureTourOverlay';
   overlay.className = 'feature-tour-overlay';
   overlay.innerHTML = '<div id="featureTourSpotlight" class="feature-tour-spotlight"></div><div id="featureTourCard" class="feature-tour-card"></div>';
   document.body.appendChild(overlay);
  }
 }
 function buildSteps(){
  return [
   { selector:'#home .hero-buttons', title:'Welcome', text:'Use these buttons to upload a memory or explore the memory wall.' },
   { selector:'#countdown', title:'Countdown', text:'This section shows the live countdown to the farewell event.' },
   { selector:'#memories', title:'Memories Preview', text:'The homepage shows six selected memories only for faster loading.' },
   { selector:'#viewAllMemoriesBtn', title:'View All', text:'Open the full dedicated memories page from here.' },
   { selector:'#upload', title:'Upload', text:'Approved uploads appear after admin review only.' },
   { selector:'#distanceMapSection', title:'Future Path Globe', text:'Select your name and future places, then save them to the globe.' },
   { selector:'#compilations', title:'Compilations', text:'Curated slideshows appear here.' }
  ];
 }
 function stopSiteTour(){
  const overlay = document.getElementById('featureTourOverlay');
  const spot = document.getElementById('featureTourSpotlight');
  const card = document.getElementById('featureTourCard');
  if (overlay) overlay.classList.remove('active');
  if (spot) {
   spot.style.left = '-9999px';
   spot.style.top = '-9999px';
   spot.style.width = '0px';
   spot.style.height = '0px';
  }
  if (card) {
   card.style.left = '-9999px';
   card.style.top = '-9999px';
  }
 }
 function startSiteTour(){
  ensureTourNodes();
  const steps = buildSteps();
  let idx = 0;
  const overlay = document.getElementById('featureTourOverlay');
  const spot = document.getElementById('featureTourSpotlight');
  const card = document.getElementById('featureTourCard');
  function render(){
   if (idx >= steps.length) return stopSiteTour();
   const step = steps[idx];
   const el = document.querySelector(step.selector);
   if (!el) { idx += 1; return render(); }
   el.scrollIntoView({ behavior:'smooth', block:'center' });
   setTimeout(() => {
    const r = el.getBoundingClientRect();
    if (r.width <= 0 || r.height <= 0) { idx += 1; return render(); }
    overlay.classList.add('active');
    spot.style.left = Math.max(8, r.left - 8) + 'px';
    spot.style.top = Math.max(8, r.top - 8) + 'px';
    spot.style.width = Math.max(40, r.width + 16) + 'px';
    spot.style.height = Math.max(40, r.height + 16) + 'px';
    card.style.left = Math.min(window.innerWidth - 380, Math.max(12, r.left)) + 'px';
    card.style.top = Math.min(window.innerHeight - 170, Math.max(12, r.bottom + 12)) + 'px';
    card.innerHTML = `<h3>${step.title}</h3><p>${step.text}</p><div class="feature-tour-actions"><button class="btn btn-secondary" type="button" id="tourSkipBtn">Close</button><button class="btn btn-primary" type="button" id="tourNextBtn">${idx === steps.length - 1 ? 'Done' : 'Next'}</button></div>`;
    document.getElementById('tourSkipBtn')?.addEventListener('click', stopSiteTour);
    document.getElementById('tourNextBtn')?.addEventListener('click', () => { idx += 1; render(); });
   }, 450);
  }
  render();
 }
 window.startSiteTour = startSiteTour;
 document.addEventListener('DOMContentLoaded', () => {
  addTourFab();
  ensureTourNodes();
  if (!localStorage.getItem(TOUR_KEY)) {
   setTimeout(() => {
    startSiteTour();
    localStorage.setItem(TOUR_KEY, '1');
   }, 1200);
  }
 });
})();
</script>""",
        text,
        count=1,
        flags=re.S,
    )

    if text != original:
        backup(index_path)
        write_file(index_path, text)


def main() -> None:
    root = Path.cwd()
    server_js = root / "server.js"
    index_html = root / "index.html"

    if not server_js.exists():
        die("server.js not found in current directory")
    if not index_html.exists():
        die("index.html not found in current directory")

    patch_server_js(server_js)
    patch_index_html(index_html)

    result = {
        "success": True,
        "modified": ["server.js", "index.html"],
        "backups": ["server.js.blindrun.bak", "index.html.blindrun.bak"],
        "mode": "best-effort-nonfatal"
    }
    print(json.dumps(result))


if __name__ == "__main__":
    main()