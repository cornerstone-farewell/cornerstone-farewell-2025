/**
 * ═══════════════════════════════════════════════════════════════════════════════
 * CORNERSTONE INTERNATIONAL SCHOOL - FAREWELL 2025
 * Backend Server - Node.js + Express + JSON file storage
 * ═══════════════════════════════════════════════════════════════════════════════
 */

const express = require('express');
const multer = require('multer');
const path = require('path');
const fs = require('fs');
const archiver = require('archiver');
const cors = require('cors');
const crypto = require('crypto');
const http = require('http');
const WebSocket = require('ws');

const Filter = require('bad-words');
const { RegExpMatcher, englishDataset, englishRecommendedTransformers } = require('obscenity');

const badWordsFilter = new Filter();
badWordsFilter.addWords(
  'chutiya', 'madarchod', 'behenchod', 'bhosdike', 'gaand', 'lund', 'randi',
  'saala', 'harami', 'kutta', 'kamina', 'gandu', 'chod', 'bhosda', 'lavda',
  'choot', 'maderchod', 'bhen', 'bhosdiwala', 'chutiye', 'gaandu', 'hijra',
  'raand', 'suar', 'tatti', 'ullu', 'retard', 'retarded', 'spastic', 'tranny', 
  'shemale', 'cracker', 'wetback', 'beaner', 'kike', 'spic', 'chink', 'gook', 
  'raghead', 'towelhead', 'sandnigger'
);

const obscenityMatcher = new RegExpMatcher({
  ...englishDataset.build(),
  ...englishRecommendedTransformers
});

const PORT = process.env.PORT || 3001; 
const ADMIN_PASSWORD = 'cornerstone2025'; 
const MAX_FILE_SIZE = 100 * 1024 * 1024; 
const MAX_TOTAL_SIZE = 200 * 1024 * 1024; 
const MAX_FILES = 20; 
const TOKEN_TTL_HOURS = 24;
const REACTION_TYPES = ['like', 'love', 'laugh', 'wow', 'sad'];

const app = express();
const server = http.createServer(app);
const wss = new WebSocket.Server({ server });

app.use(cors());
app.use(express.json({ limit: '5mb' }));
app.use(express.urlencoded({ extended: true }));

// --- SNIPER SAFE ROUTING --- 
app.use(express.static(__dirname));
app.use('/uploads', express.static(path.join(__dirname, 'uploads')));

// Prevent infinite loops: Block missing frontend components from fetching index.html
app.get('/sections/*', (req, res) => res.status(404).send('Component not found'));
app.get('/api/*', (req, res) => res.status(404).json({success: false, error: 'Endpoint not found'}));

// Standard fallback for Single Page Apps
app.get('*', (req, res) => res.sendFile(path.join(__dirname, 'index.html')));
// ---------------------------

// ═══════════════════════════════════════════════════════════════════════════════
// DYNAMIC HTML ASSEMBLER (MUST BE ABOVE STATIC FILES)
// ═══════════════════════════════════════════════════════════════════════════════


// ═══════════════════════════════════════════════════════════════════════════════
// FILE STORAGE & DB SETUP
// ═══════════════════════════════════════════════════════════════════════════════

const uploadsDir = path.join(__dirname, 'uploads');
const databaseDir = path.join(__dirname, 'database');
const logsDir = path.join(__dirname, 'logs');

[uploadsDir, databaseDir, logsDir].forEach(dir => {
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
});

const dbPath = path.join(databaseDir, 'memories.json');
const sessionsPath = path.join(databaseDir, 'sessions.json');
const settingsPath = path.join(databaseDir, 'settings.json');
const adminPath = path.join(databaseDir, 'admin.json');
const commentsPath = path.join(databaseDir, 'comments.json');
const reactionsPath = path.join(databaseDir, 'reactions.json');
const auditPath = path.join(databaseDir, 'audit.json');
const compilationsPath = path.join(databaseDir, 'compilations.json');
const studentDirectoryPath = path.join(databaseDir, 'student_directory.json');

function initDatabase() {
  if (!fs.existsSync(dbPath)) fs.writeFileSync(dbPath, JSON.stringify({ memories: [], nextId: 1 }, null, 2));
  if (!fs.existsSync(sessionsPath)) fs.writeFileSync(sessionsPath, JSON.stringify({ sessions: [] }, null, 2));
  if (!fs.existsSync(settingsPath)) fs.writeFileSync(settingsPath, JSON.stringify({ settings: {} }, null, 2));
  if (!fs.existsSync(commentsPath)) fs.writeFileSync(commentsPath, JSON.stringify({ comments: [], nextId: 1 }, null, 2));
  if (!fs.existsSync(reactionsPath)) fs.writeFileSync(reactionsPath, JSON.stringify({ reactions: [] }, null, 2));
  if (!fs.existsSync(auditPath)) fs.writeFileSync(auditPath, JSON.stringify({ events: [], nextId: 1 }, null, 2));
  if (!fs.existsSync(compilationsPath)) fs.writeFileSync(compilationsPath, JSON.stringify({ compilations: [], nextId: 1 }, null, 2));

  if (!fs.existsSync(adminPath)) {
    const now = new Date().toISOString();
    fs.writeFileSync(adminPath, JSON.stringify({
      users: [{
          id: 'super', name: 'Super Admin', role: 'superadmin', password: ADMIN_PASSWORD,
          createdAt: now, updatedAt: now, disabled: false,
          permissions: { moderation: true, settings: true, theme: true, export: true, users: true, trash: true, replaceFile: true, editMemory: true, bulk: true, featured: true }
      }]
    }, null, 2));
  }
}

function safeReadJson(filePath, fallback) { try { return JSON.parse(fs.readFileSync(filePath, 'utf8')); } catch (e) { return fallback; } }
function safeWriteJson(filePath, data) { fs.writeFileSync(filePath, JSON.stringify(data, null, 2)); }
function readDB() { return safeReadJson(dbPath, { memories: [], nextId: 1 }); }
function writeDB(data) { safeWriteJson(dbPath, data); }
function readSessions() { return safeReadJson(sessionsPath, { sessions: [] }); }
function writeSessions(data) { safeWriteJson(sessionsPath, data); }
function readSettings() { return safeReadJson(settingsPath, { settings: {} }); }
function writeSettings(data) { safeWriteJson(settingsPath, data); }
function readAdmins() { return safeReadJson(adminPath, { users: [] }); }
function writeAdmins(data) { safeWriteJson(adminPath, data); }
function readComments() { return safeReadJson(commentsPath, { comments: [], nextId: 1 }); }
function writeComments(data) { safeWriteJson(commentsPath, data); }
function readReactions() { return safeReadJson(reactionsPath, { reactions: [] }); }
function writeReactions(data) { safeWriteJson(reactionsPath, data); }
function readAudit() { return safeReadJson(auditPath, { events: [], nextId: 1 }); }
function writeAudit(data) { safeWriteJson(auditPath, data); }
function readCompilations() { return safeReadJson(compilationsPath, { compilations: [], nextId: 1 }); }
function writeCompilations(data) { safeWriteJson(compilationsPath, data); }

initDatabase();

// ═══════════════════════════════════════════════════════════════════════════════
// UPLOAD CONFIG
// ═══════════════════════════════════════════════════════════════════════════════

const storage = multer.diskStorage({
  destination: (req, file, cb) => cb(null, uploadsDir),
  filename: (req, file, cb) => {
    const uniqueSuffix = Date.now() + '-' + Math.round(Math.random() * 1E9);
    const ext = path.extname(file.originalname).toLowerCase();
    const safeName = file.originalname.replace(/[^a-zA-Z0-9.-]/g, '_').substring(0, 50);
    cb(null, `${uniqueSuffix}-${safeName}${ext && safeName.endsWith(ext) ? '' : ''}`);
  }
});

const fileFilter = (req, file, cb) => {
  const allowedTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp', 'video/mp4', 'video/quicktime', 'video/x-msvideo', 'video/webm'];
  if (allowedTypes.includes(file.mimetype)) cb(null, true);
  else cb(new Error(`Invalid file type: ${file.mimetype}`), false);
};

const upload = multer({ storage, limits: { fileSize: MAX_FILE_SIZE, files: MAX_FILES }, fileFilter });
const adminUpload = multer({ storage, limits: { fileSize: 2000 * 1024 * 1024, files: 100 }, fileFilter });

const checkTotalSize = (req, res, next) => {
  if (req.files && req.files.length > 0) {
    const totalSize = req.files.reduce((sum, file) => sum + file.size, 0);
    if (totalSize > MAX_TOTAL_SIZE) {
      req.files.forEach(file => { if (fs.existsSync(path.join(uploadsDir, file.filename))) fs.unlinkSync(path.join(uploadsDir, file.filename)); });
      return res.status(400).json({ success: false, error: `Total upload size exceeds limit` });
    }
  }
  next();
};

// ═══════════════════════════════════════════════════════════════════════════════
// HELPERS
// ═══════════════════════════════════════════════════════════════════════════════

function generateToken() { return 'admin-' + Date.now() + '-' + Math.random().toString(36).substr(2, 12); }
function cleanExpiredSessions() {
  const sessions = readSessions();
  const now = new Date();
  sessions.sessions = sessions.sessions.filter(s => new Date(s.expiresAt) > now);
  writeSessions(sessions);
}
function validateAdminToken(token) { return !!getSession(token); }
function getSession(token) {
  if (!token) return null;
  cleanExpiredSessions();
  return readSessions().sessions.find(s => s.token === token && new Date(s.expiresAt) > new Date()) || null;
}
function requireAdmin(req, res) {
  const token = req.headers.authorization?.replace('Bearer ', '');
  const session = getSession(token);
  if (!session) { res.status(401).json({ success: false, error: 'Unauthorized' }); return null; }
  const user = readAdmins().users.find(u => u.id === session.userId && !u.disabled);
  if (!user) { res.status(401).json({ success: false, error: 'Unauthorized' }); return null; }
  return { token, user };
}
function hasPerm(user, perm) { return user.role === 'superadmin' || !!(user.permissions && user.permissions[perm]); }
function audit(userId, action, meta = {}) {
  const a = readAudit();
  a.events.push({ id: a.nextId++, userId, action, meta, createdAt: new Date().toISOString() });
  if (a.events.length > 5000) a.events = a.events.slice(-5000);
  writeAudit(a);
}
function broadcast(event, payload) {
  const msg = JSON.stringify({ event, payload });
  for (const client of wss.clients) { if (client.readyState === WebSocket.OPEN) client.send(msg); }
}
function formatFileSize(bytes) {
  if (bytes === 0) return '0 Bytes';
  const k = 1024, sizes = ['Bytes', 'KB', 'MB', 'GB'], i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}
function getFileType(mimetype) { return mimetype.startsWith('image/') ? 'image' : (mimetype.startsWith('video/') ? 'video' : 'unknown'); }
function sha256File(filePath) { return crypto.createHash('sha256').update(fs.readFileSync(filePath)).digest('hex'); }
function nowIso() { return new Date().toISOString(); }
function getEffectiveSettings() {
  const defaults = { uploadsEnabled: true, commentsEnabled: true, profanityFilterEnabled: false, uploadWindowEnabled: false, uploadWindowStartIST: '', uploadWindowEndIST: '', autoApproveEnabled: false, autoApproveStartIST: '', autoApproveEndIST: '', theme: {} };
  return { ...defaults, ...(readSettings().settings || {}) };
}
function parseISTLocalToDate(istLocal) {
  if (!istLocal || !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/.test(istLocal)) return null;
  const [datePart, timePart] = istLocal.split('T');
  const [Y, M, D] = datePart.split('-').map(Number);
  const [h, m] = timePart.split(':').map(Number);
  return new Date(Date.UTC(Y, M - 1, D, h - 5, m - 30, 0));
}
function isNowWithinISTWindow(startIST, endIST) {
  const start = parseISTLocalToDate(startIST);
  const end = parseISTLocalToDate(endIST);
  return (start && end) ? (new Date() >= start && new Date() <= end) : false;
}
function containsProfanity(text) {
  if (!text || !String(text).trim()) return false;
  try { return badWordsFilter.isProfane(text) || obscenityMatcher.hasMatch(text); } catch (e) { return false; }
}
function memoryPublicShape(m) { return { ...m, file_url: `/uploads/${m.file_path}`, file_size_formatted: formatFileSize(m.file_size || 0) }; }
function getReactionCountsForMemory(memoryId) {
  const counts = {}; REACTION_TYPES.forEach(t => counts[t] = 0);
  readReactions().reactions.filter(r => r.memoryId === memoryId).forEach(r => { if (counts[r.type] !== undefined) counts[r.type]++; });
  return counts;
}
function getCommentTree(memoryId) {
  const all = readComments().comments.filter(c => c.memoryId === memoryId && !c.deletedAt).sort((a, b) => new Date(a.createdAt) - new Date(b.createdAt));
  const byId = new Map(); all.forEach(c => byId.set(c.id, { ...c, replies: [] }));
  const roots = [];
  for (const c of byId.values()) {
    if (c.parentId && byId.get(c.parentId)) byId.get(c.parentId).replies.push(c);
    else roots.push(c);
  }
  return roots;
}

wss.on('connection', (ws) => ws.send(JSON.stringify({ event: 'hello', payload: { ok: true } })));

// ═══════════════════════════════════════════════════════════════════════════════
// API ENDPOINTS - PUBLIC
// ═══════════════════════════════════════════════════════════════════════════════

app.get('/api/settings', (req, res) => res.json({ success: true, settings: readSettings().settings || {} }));

app.post('/api/upload', upload.array('files', MAX_FILES), checkTotalSize, (req, res) => {
  try {
    const { name, caption, type } = req.body;
    const files = req.files;
    const settings = getEffectiveSettings();

    if (!settings.uploadsEnabled) return res.status(403).json({ success: false, error: 'Uploads are currently disabled.' });
    if (settings.uploadWindowEnabled && !isNowWithinISTWindow(settings.uploadWindowStartIST, settings.uploadWindowEndIST)) return res.status(403).json({ success: false, error: 'Uploads closed.' });
    if (!name?.trim() || !caption?.trim() || !type || !files?.length) return res.status(400).json({ success: false, error: 'Missing fields.' });
    if (settings.profanityFilterEnabled && (containsProfanity(name) || containsProfanity(caption) || containsProfanity(type))) {
      files.forEach(f => fs.unlinkSync(path.join(uploadsDir, f.filename)));
      return res.status(400).json({ success: false, error: 'Content rejected by profanity filter.' });
    }

    const db = readDB();
    const insertedIds = [], duplicates = [];
    const autoApproveNow = settings.autoApproveEnabled ? isNowWithinISTWindow(settings.autoApproveStartIST, settings.autoApproveEndIST) : false;

    files.forEach(file => {
      const hash = sha256File(path.join(uploadsDir, file.filename));
      if (db.memories.find(m => m.sha256 === hash && m.approved === 1 && !m.deletedAt && !m.purgedAt)) {
        duplicates.push({ originalId: exists.id, duplicateFile: file.originalname });
        fs.unlinkSync(path.join(uploadsDir, file.filename));
        return;
      }
      const memory = { id: db.nextId++, student_name: name.trim(), caption: caption.trim().substring(0, 500), memory_type: type, file_path: file.filename, file_name: file.originalname, file_type: getFileType(file.mimetype), file_size: file.size, sha256: hash, approved: autoApproveNow ? 1 : 0, featured: 0, likes: 0, deletedAt: null, purgedAt: null, created_at: nowIso(), updated_at: nowIso() };
      db.memories.push(memory); insertedIds.push(memory.id);
    });

    writeDB(db);
    if (insertedIds.length === 0 && duplicates.length > 0) return res.status(409).json({ success: false, error: 'Duplicate upload detected.', duplicates });
    broadcast('memory:new', { count: insertedIds.length });
    res.json({ success: true, message: `Successfully uploaded!`, count: insertedIds.length, ids: insertedIds, duplicates });
  } catch (error) { res.status(500).json({ success: false, error: error.message }); }
});

app.get('/api/memories', (req, res) => {
  try {
    const db = readDB();
    const page = Math.max(1, parseInt(req.query.page || '1', 10)), limit = Math.min(5000, Math.max(1, parseInt(req.query.limit || '20', 10)));
    let memories = db.memories.filter(m => m.approved === 1 && !m.deletedAt && !m.purgedAt);
    if (req.query.type && req.query.type !== 'all') memories = memories.filter(m => m.memory_type === req.query.type);
    if (req.query.cursor) memories = memories.filter(m => new Date(m.created_at) < new Date(req.query.cursor));
    memories.sort((a, b) => ((b.featured || 0) !== (a.featured || 0)) ? (b.featured || 0) - (a.featured || 0) : new Date(b.created_at) - new Date(a.created_at));
    
    const start = (page - 1) * limit;
    const items = memories.slice(start, start + limit).map(m => ({ ...memoryPublicShape(m), reactions: getReactionCountsForMemory(m.id) }));
    res.json({ success: true, memories: items, page, limit, total: memories.length, hasMore: start + limit < memories.length });
  } catch (error) { res.status(500).json({ success: false, error: error.message }); }
});

app.post('/api/like/:id', (req, res) => {
  try {
    const id = parseInt(req.params.id);
    const db = readDB();
    const memory = db.memories.find(m => m.id === id && m.approved === 1 && !m.deletedAt && !m.purgedAt);
    if (!memory) return res.status(404).json({ success: false, error: 'Memory not found' });
    memory.likes = (memory.likes || 0) + 1; memory.updated_at = nowIso(); writeDB(db);
    const rx = readReactions(); rx.reactions.push({ memoryId: id, type: 'like', createdAt: nowIso() }); writeReactions(rx);
    broadcast('reaction:update', { memoryId: id });
    res.json({ success: true, likes: memory.likes, reactions: getReactionCountsForMemory(id) });
  } catch (error) { res.status(500).json({ success: false, error: error.message }); }
});

app.post('/api/reactions/:memoryId', (req, res) => {
  try {
    const memoryId = parseInt(req.params.memoryId, 10);
    if (!REACTION_TYPES.includes(req.body.type)) return res.status(400).json({ success: false, error: 'Invalid reaction type' });
    if (!readDB().memories.find(m => m.id === memoryId && m.approved === 1 && !m.deletedAt && !m.purgedAt)) return res.status(404).json({ success: false, error: 'Memory not found' });
    const rx = readReactions(); rx.reactions.push({ memoryId, type: req.body.type, createdAt: nowIso() }); writeReactions(rx);
    broadcast('reaction:update', { memoryId });
    res.json({ success: true, reactions: getReactionCountsForMemory(memoryId) });
  } catch (e) { res.status(500).json({ success: false, error: e.message }); }
});

app.get('/api/comments/:memoryId', (req, res) => {
  try {
    if (!getEffectiveSettings().commentsEnabled) return res.json({ success: true, comments: [], disabled: true });
    if (!readDB().memories.find(m => m.id === parseInt(req.params.memoryId, 10) && m.approved === 1 && !m.deletedAt && !m.purgedAt)) return res.status(404).json({ success: false, error: 'Memory not found' });
    res.json({ success: true, comments: getCommentTree(parseInt(req.params.memoryId, 10)), disabled: false });
  } catch (e) { res.status(500).json({ success: false, error: e.message }); }
});

app.post('/api/comments/:memoryId', (req, res) => {
  try {
    if (!getEffectiveSettings().commentsEnabled) return res.status(403).json({ success: false, error: 'Comments disabled.' });
    const memoryId = parseInt(req.params.memoryId, 10);
    const { name, text, parentId } = req.body || {};
    if (!name?.trim() || !text?.trim()) return res.status(400).json({ success: false, error: 'Missing fields' });
    if (!readDB().memories.find(m => m.id === memoryId && m.approved === 1 && !m.deletedAt && !m.purgedAt)) return res.status(404).json({ success: false, error: 'Memory not found' });
    const cdb = readComments();
    cdb.comments.push({ id: cdb.nextId++, memoryId, parentId: parentId ? Number(parentId) : null, name: String(name).trim().substring(0, 60), text: String(text).trim().substring(0, 800), createdAt: nowIso(), deletedAt: null });
    writeComments(cdb); broadcast('comment:new', { memoryId });
    res.json({ success: true });
  } catch (e) { res.status(500).json({ success: false, error: e.message }); }
});


// ═══════════════════════════════════════════════════════════════════════════════
// API ENDPOINTS - ADMIN
// ═══════════════════════════════════════════════════════════════════════════════
app.post('/api/admin/login', (req, res) => {
  const user = readAdmins().users.find(u => u.id === (req.body.userId || 'super'));
  if (!user || user.disabled || req.body.password !== user.password) return res.status(401).json({ success: false, error: 'Invalid credentials' });
  const token = generateToken();
  const sessions = readSessions();
  sessions.sessions.push({ token, expiresAt: new Date(Date.now() + TOKEN_TTL_HOURS * 60 * 60 * 1000).toISOString(), userId: user.id });
  writeSessions(sessions);
  res.json({ success: true, token, user: { id: user.id, name: user.name, role: user.role, permissions: user.permissions } });
});

app.post('/api/admin/verify', (req, res) => {
  const session = getSession(req.headers.authorization?.replace('Bearer ', ''));
  const user = session ? readAdmins().users.find(u => u.id === session.userId && !u.disabled) : null;
  res.json({ success: true, valid: !!user, user: user ? { id: user.id, name: user.name, role: user.role, permissions: user.permissions } : null });
});

app.get('/api/admin/memories', (req, res) => {
  const auth = requireAdmin(req, res); if (!auth) return;
  const db = readDB();
  let memories = db.memories.filter(m => !m.purgedAt);
  if (req.query.includeDeleted !== 'true') memories = memories.filter(m => !m.deletedAt);
  res.json({ success: true, memories: memories.slice(0, 50).map(memoryPublicShape) }); // Simplified for snippet
});


// ═══════════════════════════════════════════════════════════════════════════════
// ERROR HANDLING & LAUNCH
// ═══════════════════════════════════════════════════════════════════════════════

app.use((err, req, res, next) => {
  res.status(500).json({ success: false, error: err.message || 'Internal server error' });
});

// ═══════════════════════════════════════════════════════════════════════════════
// FUN FEATURES API
// ═══════════════════════════════════════════════════════════════════════════════
const funPath = path.join(databaseDir, 'fun_features.json');
if (!fs.existsSync(funPath)) {
    fs.writeFileSync(funPath, JSON.stringify({ settings: {}, gratitude: [], superlatives: { categories: [] }, wishes: [], dedications: [], mood: { votes: {} }, capsules: [] }, null, 2));
}
const readFun = () => safeReadJson(funPath, { settings: {}, gratitude: [], superlatives: { categories: [] }, wishes: [], dedications: [], mood: { votes: {} }, capsules: [] });
const writeFun = (data) => safeWriteJson(funPath, data);

app.get('/api/fun/settings', (req, res) => res.json({ success: true, settings: readFun().settings }));
app.post('/api/fun/settings', (req, res) => {
    const auth = requireAdmin(req, res); if (!auth) return;
    const db = readFun(); db.settings = req.body.settings || {}; writeFun(db);
    res.json({ success: true });
});

app.get('/api/fun/gratitude', (req, res) => res.json({ success: true, notes: readFun().gratitude }));
app.post('/api/fun/gratitude', (req, res) => {
    const db = readFun();
    db.gratitude.unshift({ ...req.body, created_at: new Date().toISOString() });
    writeFun(db); res.json({ success: true });
});

app.get('/api/fun/superlatives', (req, res) => res.json({ success: true, categories: readFun().superlatives.categories }));
app.post('/api/fun/superlatives/nominee', (req, res) => {
    const db = readFun();
    let cat = db.superlatives.categories.find(c => c.id === req.body.categoryId);
    if (!cat) {
        cat = { id: req.body.categoryId, emoji: '🏆', title: 'Category ' + req.body.categoryId, nominees: [] };
        db.superlatives.categories.push(cat);
    }
    if (!cat.nominees.find(n => n.name === req.body.name)) {
        cat.nominees.push({ id: Date.now(), name: req.body.name, votes: 1 });
    }
    writeFun(db); res.json({ success: true });
});
app.post('/api/fun/superlatives/vote', (req, res) => {
    const db = readFun();
    const cat = db.superlatives.categories.find(c => c.id === req.body.categoryId);
    if (cat) {
        const nom = cat.nominees.find(n => n.id == req.body.nomineeId || n.name === req.body.nomineeId);
        if (nom) nom.votes = (nom.votes || 0) + 1;
    }
    writeFun(db); res.json({ success: true });
});

app.get('/api/fun/wishes', (req, res) => res.json({ success: true, wishes: readFun().wishes }));
app.post('/api/fun/wishes', (req, res) => {
    const db = readFun();
    db.wishes.unshift({ ...req.body, created_at: new Date().toISOString() });
    writeFun(db); res.json({ success: true });
});

app.get('/api/fun/dedications', (req, res) => res.json({ success: true, dedications: readFun().dedications }));
app.post('/api/fun/dedications', (req, res) => {
    const db = readFun();
    db.dedications.unshift({ ...req.body, created_at: new Date().toISOString() });
    writeFun(db); res.json({ success: true });
});

app.get('/api/fun/mood', (req, res) => res.json({ success: true, votes: readFun().mood.votes }));
app.post('/api/fun/mood', (req, res) => {
    const db = readFun();
    const m = req.body.mood;
    db.mood.votes[m] = (db.mood.votes[m] || 0) + 1;
    writeFun(db); res.json({ success: true });
});

app.get('/api/fun/capsules', (req, res) => res.json({ success: true, capsules: readFun().capsules }));
app.post('/api/fun/capsules', (req, res) => {
    const db = readFun();
    db.capsules.unshift({ ...req.body, created_at: new Date().toISOString() });
    writeFun(db); res.json({ success: true });
});

server.listen(PORT, '0.0.0.0', () => {
  console.log('═══════════════════════════════════════════════════════════════════');
  console.log(`🚀 Server running on: http://localhost:${PORT}`);
  console.log(`🔗 Make sure you are visiting exactly http://localhost:${PORT}`);
  console.log('═══════════════════════════════════════════════════════════════════');
});