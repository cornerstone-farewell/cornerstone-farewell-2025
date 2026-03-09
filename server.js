/**
 * ═══════════════════════════════════════════════════════════════════════════════
 * CORNERSTONE INTERNATIONAL SCHOOL - FAREWELL 2025
 * Backend Server - Node.js + Express + JSON file storage
 * Upgrades included:
 *  - Multi-admin users (Super Admin + sub-admins) with permissions + limits
 *  - Site settings + Theme settings (full color palette)
 *  - Upload window controls + event auto-approve window
 *  - Comments (public, name required) + replies (threaded)
 *  - Reactions (multi-type) + legacy likes compatibility
 *  - Edit memory metadata (caption/type) + replace file
 *  - Soft delete (trash) + restore + purge
 *  - Bulk actions (approve/delete/restore/change category)
 *  - Duplicate detection (SHA256)
 *  - Advanced profanity filter (bad-words + obscenity + custom patterns)
 *  - Pagination/infinite scroll support
 *  - CSV export
 *  - WebSocket live updates to clients/admin
 * NOTE: JSON storage is not ideal for heavy concurrency; this is best-effort "production-ish".
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

// Profanity filter libraries
const Filter = require('bad-words');
const { RegExpMatcher, englishDataset, englishRecommendedTransformers } = require('obscenity');

// ═══════════════════════════════════════════════════════════════════════════════
// PROFANITY FILTER SETUP
// ═══════════════════════════════════════════════════════════════════════════════

const badWordsFilter = new Filter();

// Add custom bad words (Hindi/regional + additional English)
badWordsFilter.addWords(
  // Hindi profanity
  'chutiya', 'madarchod', 'behenchod', 'bhosdike', 'gaand', 'lund', 'randi',
  'saala', 'harami', 'kutta', 'kamina', 'gandu', 'chod', 'bhosda', 'lavda',
  'choot', 'maderchod', 'bhen', 'bhosdiwala', 'chutiye', 'gaandu', 'hijra',
  'raand', 'suar', 'tatti', 'ullu',
  // Additional English
  'retard', 'retarded', 'spastic', 'tranny', 'shemale', 'cracker', 'wetback',
  'beaner', 'kike', 'spic', 'chink', 'gook', 'raghead', 'towelhead', 'sandnigger'
);

const obscenityMatcher = new RegExpMatcher({
  ...englishDataset.build(),
  ...englishRecommendedTransformers
});

// ═══════════════════════════════════════════════════════════════════════════════
// CONFIGURATION
// ═══════════════════════════════════════════════════════════════════════════════

const PORT = process.env.PORT || 3000;

// This is ONLY used on first run to create super admin in database/admin.json.
// After that, the password stored in admin.json is used.
const ADMIN_PASSWORD = 'cornerstone2025'; // ⚠️ CHANGE THIS IN PRODUCTION!

const MAX_FILE_SIZE = 100 * 1024 * 1024; // 100MB per file
const MAX_TOTAL_SIZE = 200 * 1024 * 1024; // 200MB total per upload
const MAX_FILES = 20; // Maximum files per upload

const TOKEN_TTL_HOURS = 24;

// Reactions supported
const REACTION_TYPES = ['like', 'love', 'laugh', 'wow', 'sad'];

// ═══════════════════════════════════════════════════════════════════════════════
// INITIALIZE EXPRESS APP + HTTP SERVER (for WebSocket)
// ═══════════════════════════════════════════════════════════════════════════════

const app = express();
const server = http.createServer(app);
const wss = new WebSocket.Server({ server });

// Middleware
app.use(cors());
app.use(express.json({ limit: '5mb' }));
app.use(express.urlencoded({ extended: true }));

// Serve static files
app.use(express.static(__dirname));
app.use('/uploads', express.static(path.join(__dirname, 'uploads')));

// ═══════════════════════════════════════════════════════════════════════════════
// CREATE REQUIRED DIRECTORIES
// ═══════════════════════════════════════════════════════════════════════════════

const uploadsDir = path.join(__dirname, 'uploads');
const databaseDir = path.join(__dirname, 'database');
const logsDir = path.join(__dirname, 'logs');

[uploadsDir, databaseDir, logsDir].forEach(dir => {
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
    console.log(`📁 Created directory: ${dir}`);
  }
});

// ═══════════════════════════════════════════════════════════════════════════════
// JSON FILE-BASED STORAGE
// ═══════════════════════════════════════════════════════════════════════════════

const dbPath = path.join(databaseDir, 'memories.json');
const sessionsPath = path.join(databaseDir, 'sessions.json');
const settingsPath = path.join(databaseDir, 'settings.json');
const adminPath = path.join(databaseDir, 'admin.json');
const commentsPath = path.join(databaseDir, 'comments.json');
const reactionsPath = path.join(databaseDir, 'reactions.json');
const auditPath = path.join(databaseDir, 'audit.json');
const compilationsPath = path.join(databaseDir, 'compilations.json');

function initDatabase() {
  if (!fs.existsSync(dbPath)) {
    fs.writeFileSync(dbPath, JSON.stringify({ memories: [], nextId: 1 }, null, 2));
    console.log('💾 Created memories database');
  }
  if (!fs.existsSync(sessionsPath)) {
    fs.writeFileSync(sessionsPath, JSON.stringify({ sessions: [] }, null, 2));
    console.log('💾 Created sessions database');
  }
  if (!fs.existsSync(settingsPath)) {
    fs.writeFileSync(settingsPath, JSON.stringify({ settings: {} }, null, 2));
    console.log('💾 Created settings database');
  }
  if (!fs.existsSync(commentsPath)) {
    fs.writeFileSync(commentsPath, JSON.stringify({ comments: [], nextId: 1 }, null, 2));
    console.log('💾 Created comments database');
  }
  if (!fs.existsSync(reactionsPath)) {
    fs.writeFileSync(reactionsPath, JSON.stringify({ reactions: [] }, null, 2));
    console.log('💾 Created reactions database');
  }
  if (!fs.existsSync(auditPath)) {
    fs.writeFileSync(auditPath, JSON.stringify({ events: [], nextId: 1 }, null, 2));
    console.log('💾 Created audit database');
  }

  // Admin users database
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
    console.log('💾 Created admin database with super admin');
  }
  if (!fs.existsSync(compilationsPath)) {
    fs.writeFileSync(compilationsPath, JSON.stringify({ compilations: [], nextId: 1 }, null, 2));
    console.log('💾 Created compilations database');
  }
  
}

function safeReadJson(filePath, fallback) {
  try {
    return JSON.parse(fs.readFileSync(filePath, 'utf8'));
  } catch (e) {
    return fallback;
  }
}

function safeWriteJson(filePath, data) {
  fs.writeFileSync(filePath, JSON.stringify(data, null, 2));
}

function readDB() {
  return safeReadJson(dbPath, { memories: [], nextId: 1 });
}

function writeDB(data) {
  safeWriteJson(dbPath, data);
}

function readSessions() {
  return safeReadJson(sessionsPath, { sessions: [] });
}

function writeSessions(data) {
  safeWriteJson(sessionsPath, data);
}

function readSettings() {
  return safeReadJson(settingsPath, { settings: {} });
}

function writeSettings(data) {
  safeWriteJson(settingsPath, data);
}

function readAdmins() {
  return safeReadJson(adminPath, { users: [] });
}

function writeAdmins(data) {
  safeWriteJson(adminPath, data);
}

function readComments() {
  return safeReadJson(commentsPath, { comments: [], nextId: 1 });
}

function writeComments(data) {
  safeWriteJson(commentsPath, data);
}

function readReactions() {
  return safeReadJson(reactionsPath, { reactions: [] });
}

function writeReactions(data) {
  safeWriteJson(reactionsPath, data);
}

function readAudit() {
  return safeReadJson(auditPath, { events: [], nextId: 1 });
}

function writeAudit(data) {
  safeWriteJson(auditPath, data);
}


function readCompilations() {
  return safeReadJson(compilationsPath, { compilations: [], nextId: 1 });
}

function writeCompilations(data) {
  safeWriteJson(compilationsPath, data);
}

initDatabase();
console.log(`💾 Database initialized: ${dbPath}`);

// ═══════════════════════════════════════════════════════════════════════════════
// FILE UPLOAD CONFIGURATION (MULTER)
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
  const allowedImageTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp'];
  const allowedVideoTypes = ['video/mp4', 'video/quicktime', 'video/x-msvideo', 'video/webm'];
  const allowedTypes = [...allowedImageTypes, ...allowedVideoTypes];

  if (allowedTypes.includes(file.mimetype)) cb(null, true);
  else cb(new Error(`Invalid file type: ${file.mimetype}`), false);
};

const upload = multer({
  storage,
  limits: { fileSize: MAX_FILE_SIZE, files: MAX_FILES },
  fileFilter
});

// 🚀 Special Admin Upload Instance: 2GB per file limit, up to 100 files
const adminUpload = multer({
  storage,
  limits: { fileSize: 2000 * 1024 * 1024, files: 100 }, // 2000 MB
  fileFilter
});

const checkTotalSize = (req, res, next) => {
  if (req.files && req.files.length > 0) {
    const totalSize = req.files.reduce((sum, file) => sum + file.size, 0);
    if (totalSize > MAX_TOTAL_SIZE) {
      req.files.forEach(file => {
        const filePath = path.join(uploadsDir, file.filename);
        if (fs.existsSync(filePath)) fs.unlinkSync(filePath);
      });
      return res.status(400).json({
        success: false,
        error: `Total upload size exceeds ${MAX_TOTAL_SIZE / 1024 / 1024}MB limit`
      });
    }
  }
  next();
};

// ═══════════════════════════════════════════════════════════════════════════════
// HELPERS
// ═══════════════════════════════════════════════════════════════════════════════

function generateToken() {
  return 'admin-' + Date.now() + '-' + Math.random().toString(36).substr(2, 12);
}

function cleanExpiredSessions() {
  const sessions = readSessions();
  const now = new Date();
  const before = sessions.sessions.length;
  sessions.sessions = sessions.sessions.filter(s => new Date(s.expiresAt) > now);
  if (sessions.sessions.length !== before) writeSessions(sessions);
}

function validateAdminToken(token) {
  if (!token) return false;
  cleanExpiredSessions();
  const data = readSessions();
  const now = new Date();
  const session = data.sessions.find(s => s.token === token && new Date(s.expiresAt) > now);
  return !!session;
}

function getSession(token) {
  if (!token) return null;
  cleanExpiredSessions();
  const data = readSessions();
  const now = new Date();
  return data.sessions.find(s => s.token === token && new Date(s.expiresAt) > now) || null;
}

function requireAdmin(req, res) {
  const token = req.headers.authorization?.replace('Bearer ', '');
  const session = getSession(token);
  if (!session) {
    res.status(401).json({ success: false, error: 'Unauthorized' });
    return null;
  }
  const admins = readAdmins();
  const user = admins.users.find(u => u.id === session.userId && !u.disabled);
  if (!user) {
    res.status(401).json({ success: false, error: 'Unauthorized' });
    return null;
  }
  return { token, user };
}

function hasPerm(user, perm) {
  if (!user) return false;
  if (user.role === 'superadmin') return true;
  return !!(user.permissions && user.permissions[perm]);
}

function audit(userId, action, meta = {}) {
  const a = readAudit();
  a.events.push({
    id: a.nextId++,
    userId,
    action,
    meta,
    createdAt: new Date().toISOString()
  });
  if (a.events.length > 5000) a.events = a.events.slice(-5000);
  writeAudit(a);
}

function broadcast(event, payload) {
  const msg = JSON.stringify({ event, payload });
  for (const client of wss.clients) {
    if (client.readyState === WebSocket.OPEN) client.send(msg);
  }
}

function formatFileSize(bytes) {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function getFileType(mimetype) {
  if (mimetype.startsWith('image/')) return 'image';
  if (mimetype.startsWith('video/')) return 'video';
  return 'unknown';
}

function sha256File(filePath) {
  const buf = fs.readFileSync(filePath);
  return crypto.createHash('sha256').update(buf).digest('hex');
}

function nowIso() {
  return new Date().toISOString();
}

function getEffectiveSettings() {
  const s = readSettings().settings || {};
  const defaults = {
    uploadsEnabled: true,
    commentsEnabled: true,
    profanityFilterEnabled: false,
    uploadWindowEnabled: false,
    uploadWindowStartIST: '',
    uploadWindowEndIST: '',
    autoApproveEnabled: false,
    autoApproveStartIST: '',
    autoApproveEndIST: '',
    theme: {}
  };
  return { ...defaults, ...s };
}

function parseISTLocalToDate(istLocal) {
  if (!istLocal || !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/.test(istLocal)) return null;
  const [datePart, timePart] = istLocal.split('T');
  const [Y, M, D] = datePart.split('-').map(Number);
  const [h, m] = timePart.split(':').map(Number);
  const utcMs = Date.UTC(Y, M - 1, D, h - 5, m - 30, 0);
  return new Date(utcMs);
}

function isNowWithinISTWindow(startIST, endIST) {
  const start = parseISTLocalToDate(startIST);
  const end = parseISTLocalToDate(endIST);
  if (!start || !end) return false;
  const now = new Date();
  return now >= start && now <= end;
}

// ═══════════════════════════════════════════════════════════════════════════════
// ADVANCED PROFANITY FILTER
// ═══════════════════════════════════════════════════════════════════════════════

function containsProfanity(text) {
  const t = String(text || '');
  if (!t.trim()) return false;

  try {
    // Check 1: bad-words library (450+ words, handles leetspeak)
    if (badWordsFilter.isProfane(t)) {
      console.log(`🚫 Profanity detected (bad-words): "${t.substring(0, 50)}..."`);
      return true;
    }

    // Check 2: obscenity library (best accuracy, handles spacing tricks)
    if (obscenityMatcher.hasMatch(t)) {
      console.log(`🚫 Profanity detected (obscenity): "${t.substring(0, 50)}..."`);
      return true;
    }

    // Check 3: Custom patterns (catches things both libraries might miss)
    const customPatterns = [
      /f+\s*u+\s*c+\s*k/i,           // f u c k, fuuuck, etc.
      /s+\s*h+\s*i+\s*t/i,           // s h i t, shiit, etc.
      /b+\s*i+\s*t+\s*c+\s*h/i,      // b i t c h
      /a+\s*s+\s*s+/i,               // a s s
      /d+\s*i+\s*c+\s*k/i,           // d i c k
      /p+\s*u+\s*s+\s*y/i,           // p u s s y
      /c+\s*u+\s*n+\s*t/i,           // c u n t
      /n+\s*i+\s*g+\s*g/i,           // n word variations
      /f+\s*a+\s*g+/i,               // f word variations
      /w+\s*h+\s*o+\s*r+\s*e/i,      // w h o r e
      /s+\s*l+\s*u+\s*t/i,           // s l u t
    ];

    // Normalize leetspeak
    const normalized = t.toLowerCase().replace(/[0-9@$!*]/g, (c) => {
      const map = { '0': 'o', '1': 'i', '3': 'e', '4': 'a', '5': 's', '7': 't', '@': 'a', '$': 's', '!': 'i', '*': '' };
      return map[c] || c;
    });

    for (const pattern of customPatterns) {
      if (pattern.test(normalized)) {
        console.log(`🚫 Profanity detected (custom pattern): "${t.substring(0, 50)}..."`);
        return true;
      }
    }

    // Check 4: Hindi/Regional patterns
    const hindiPatterns = [
      /ch+\s*u+\s*t/i,               // variations of chut
      /bh+\s*o+\s*s/i,               // variations of bhos
      /m+\s*a+\s*d+\s*a+\s*r/i,      // variations of madar
      /b+\s*e+\s*h+\s*e+\s*n/i,      // variations of behen (in bad context)
      /l+\s*u+\s*n+\s*d/i,           // variations
      /g+\s*a+\s*a+\s*n+\s*d/i,      // variations
      /r+\s*a+\s*n+\s*d+\s*i/i,      // variations
    ];

    for (const pattern of hindiPatterns) {
      if (pattern.test(normalized)) {
        console.log(`🚫 Profanity detected (hindi pattern): "${t.substring(0, 50)}..."`);
        return true;
      }
    }

    return false;
  } catch (error) {
    console.error('Profanity check error:', error);
    return false; // Don't block on error
  }
}

// ═══════════════════════════════════════════════════════════════════════════════
// MORE HELPERS
// ═══════════════════════════════════════════════════════════════════════════════

function sanitizeCsvCell(v) {
  const s = String(v ?? '');
  if (/^[=\-+@]/.test(s)) return `'${s}`;
  return s.replaceAll('"', '""');
}

function memoryPublicShape(m) {
  return {
    ...m,
    file_url: `/uploads/${m.file_path}`,
    file_size_formatted: formatFileSize(m.file_size || 0)
  };
}

function getReactionCountsForMemory(memoryId) {
  const rx = readReactions();
  const items = rx.reactions.filter(r => r.memoryId === memoryId);
  const counts = {};
  for (const t of REACTION_TYPES) counts[t] = 0;
  for (const r of items) {
    if (counts[r.type] !== undefined) counts[r.type]++;
  }
  return counts;
}

function getCommentTree(memoryId) {
  const cdb = readComments();
  const all = cdb.comments
    .filter(c => c.memoryId === memoryId && !c.deletedAt)
    .sort((a, b) => new Date(a.createdAt) - new Date(b.createdAt));

  const byId = new Map();
  all.forEach(c => byId.set(c.id, { ...c, replies: [] }));

  const roots = [];
  for (const c of byId.values()) {
    if (c.parentId) {
      const p = byId.get(c.parentId);
      if (p) p.replies.push(c);
      else roots.push(c);
    } else roots.push(c);
  }
  return roots;
}

// WebSocket
wss.on('connection', (ws) => {
  ws.send(JSON.stringify({ event: 'hello', payload: { ok: true } }));
});

// ═══════════════════════════════════════════════════════════════════════════════
// API ENDPOINTS - PUBLIC
// ═══════════════════════════════════════════════════════════════════════════════

// Get Site Settings (public)
app.get('/api/settings', (req, res) => {
  try {
    const data = readSettings();
    res.json({ success: true, settings: data.settings || {} });
  } catch (error) {
    console.error('Get settings error:', error);
    res.status(500).json({ success: false, error: error.message });
  }
});

// Upload Memory
app.post('/api/upload', upload.array('files', MAX_FILES), checkTotalSize, (req, res) => {
  try {
    const { name, caption, type } = req.body;
    const files = req.files;

    const settings = getEffectiveSettings();

    if (!settings.uploadsEnabled) {
      return res.status(403).json({ success: false, error: 'Uploads are currently disabled.' });
    }

    if (settings.uploadWindowEnabled) {
      const ok = isNowWithinISTWindow(settings.uploadWindowStartIST, settings.uploadWindowEndIST);
      if (!ok) return res.status(403).json({ success: false, error: 'Uploads are currently closed (outside upload window).' });
    }

    if (!name || !name.trim()) return res.status(400).json({ success: false, error: 'Student name is required' });
    if (!caption || !caption.trim()) return res.status(400).json({ success: false, error: 'Caption is required' });
    if (!type) return res.status(400).json({ success: false, error: 'Memory type is required' });
    if (!files || files.length === 0) return res.status(400).json({ success: false, error: 'Please select at least one file' });

    if (settings.profanityFilterEnabled) {
      if (containsProfanity(name) || containsProfanity(caption) || containsProfanity(type)) {
        files.forEach(file => {
          const fp = path.join(uploadsDir, file.filename);
          if (fs.existsSync(fp)) fs.unlinkSync(fp);
        });
        return res.status(400).json({ success: false, error: 'Content rejected by profanity filter.' });
      }
    }

    const db = readDB();
    const insertedIds = [];
    const duplicates = [];

    const autoApproveNow = settings.autoApproveEnabled
      ? isNowWithinISTWindow(settings.autoApproveStartIST, settings.autoApproveEndIST)
      : false;

    files.forEach(file => {
      const filePath = path.join(uploadsDir, file.filename);
      const hash = sha256File(filePath);

      const exists = db.memories.find(m => m.sha256 === hash && m.approved === 1 && !m.deletedAt && !m.purgedAt);
      if (exists) {
        duplicates.push({ originalId: exists.id, duplicateFile: file.originalname });
        if (fs.existsSync(filePath)) fs.unlinkSync(filePath);
        return;
      }

      const memory = {
        id: db.nextId++,
        student_name: name.trim(),
        caption: caption.trim().substring(0, 500),
        memory_type: type,
        file_path: file.filename,
        file_name: file.originalname,
        file_type: getFileType(file.mimetype),
        file_size: file.size,
        sha256: hash,
        approved: autoApproveNow ? 1 : 0,
        featured: 0,
        likes: 0,
        deletedAt: null,
        purgedAt: null,
        created_at: nowIso(),
        updated_at: nowIso()
      };

      db.memories.push(memory);
      insertedIds.push(memory.id);
    });

    writeDB(db);

    if (insertedIds.length === 0 && duplicates.length > 0) {
      return res.status(409).json({
        success: false,
        error: 'Duplicate upload detected (all files were duplicates).',
        duplicates
      });
    }

    console.log(`📤 New upload: ${insertedIds.length} file(s) from "${name}" (duplicates skipped: ${duplicates.length})`);
    broadcast('memory:new', { count: insertedIds.length });

    res.json({
      success: true,
      message: `Successfully uploaded ${insertedIds.length} memory${insertedIds.length > 1 ? 'ies' : ''}!`,
      count: insertedIds.length,
      ids: insertedIds,
      duplicates
    });
  } catch (error) {
    console.error('Upload error:', error);
    res.status(500).json({ success: false, error: error.message });
  }
});

// Get Approved Memories
app.get('/api/memories', (req, res) => {
  try {
    const db = readDB();

    const page = Math.max(1, parseInt(req.query.page || '1', 10));
    const limit = Math.min(50, Math.max(1, parseInt(req.query.limit || '20', 10)));
    const type = req.query.type || 'all';
    const cursor = req.query.cursor ? new Date(req.query.cursor) : null;

    let memories = db.memories
      .filter(m => m.approved === 1 && !m.deletedAt && !m.purgedAt);

    if (type !== 'all') memories = memories.filter(m => m.memory_type === type);

    if (cursor) memories = memories.filter(m => new Date(m.created_at) < cursor);

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

    const nextCursor = items.length ? items[items.length - 1].created_at : null;

    res.json({
      success: true,
      memories: items,
      page,
      limit,
      total,
      nextCursor,
      hasMore: start + limit < total
    });
  } catch (error) {
    console.error('Get memories error:', error);
    res.status(500).json({ success: false, error: error.message });
  }
});

// Like Memory
app.post('/api/like/:id', (req, res) => {
  try {
    const id = parseInt(req.params.id);
    const db = readDB();

    const memory = db.memories.find(m => m.id === id && m.approved === 1 && !m.deletedAt && !m.purgedAt);
    if (!memory) return res.status(404).json({ success: false, error: 'Memory not found' });

    memory.likes = (memory.likes || 0) + 1;
    memory.updated_at = nowIso();
    writeDB(db);

    const rx = readReactions();
    rx.reactions.push({ memoryId: id, type: 'like', createdAt: nowIso() });
    writeReactions(rx);

    broadcast('reaction:update', { memoryId: id });

    res.json({ success: true, likes: memory.likes, reactions: getReactionCountsForMemory(id) });
  } catch (error) {
    console.error('Like error:', error);
    res.status(500).json({ success: false, error: error.message });
  }
});

// Reactions
app.post('/api/reactions/:memoryId', (req, res) => {
  try {
    const memoryId = parseInt(req.params.memoryId, 10);
    const { type } = req.body || {};
    if (!REACTION_TYPES.includes(type)) return res.status(400).json({ success: false, error: 'Invalid reaction type' });

    const db = readDB();
    const memory = db.memories.find(m => m.id === memoryId && m.approved === 1 && !m.deletedAt && !m.purgedAt);
    if (!memory) return res.status(404).json({ success: false, error: 'Memory not found' });

    const rx = readReactions();
    rx.reactions.push({ memoryId, type, createdAt: nowIso() });
    writeReactions(rx);

    broadcast('reaction:update', { memoryId });

    res.json({ success: true, reactions: getReactionCountsForMemory(memoryId) });
  } catch (e) {
    res.status(500).json({ success: false, error: e.message });
  }
});

// Comments: list
app.get('/api/comments/:memoryId', (req, res) => {
  try {
    const settings = getEffectiveSettings();
    if (!settings.commentsEnabled) {
      return res.json({ success: true, comments: [], disabled: true });
    }

    const memoryId = parseInt(req.params.memoryId, 10);
    const db = readDB();
    const memory = db.memories.find(m => m.id === memoryId && m.approved === 1 && !m.deletedAt && !m.purgedAt);
    if (!memory) return res.status(404).json({ success: false, error: 'Memory not found' });

    res.json({ success: true, comments: getCommentTree(memoryId), disabled: false });
  } catch (e) {
    res.status(500).json({ success: false, error: e.message });
  }
});

// Comments: create
app.post('/api/comments/:memoryId', (req, res) => {
  try {
    const settings = getEffectiveSettings();
    if (!settings.commentsEnabled) {
      return res.status(403).json({ success: false, error: 'Comments are disabled.' });
    }

    const memoryId = parseInt(req.params.memoryId, 10);
    const { name, text, parentId } = req.body || {};

    if (!name || !String(name).trim()) return res.status(400).json({ success: false, error: 'Name is required' });
    if (!text || !String(text).trim()) return res.status(400).json({ success: false, error: 'Comment text is required' });

    if (settings.profanityFilterEnabled) {
      if (containsProfanity(name) || containsProfanity(text)) {
        return res.status(400).json({ success: false, error: 'Comment rejected by profanity filter.' });
      }
    }

    const db = readDB();
    const memory = db.memories.find(m => m.id === memoryId && m.approved === 1 && !m.deletedAt && !m.purgedAt);
    if (!memory) return res.status(404).json({ success: false, error: 'Memory not found' });

    const cdb = readComments();

    if (parentId) {
      const p = cdb.comments.find(c => c.id === Number(parentId) && c.memoryId === memoryId && !c.deletedAt);
      if (!p) return res.status(400).json({ success: false, error: 'Invalid parentId' });
    }

    const comment = {
      id: cdb.nextId++,
      memoryId,
      parentId: parentId ? Number(parentId) : null,
      name: String(name).trim().substring(0, 60),
      text: String(text).trim().substring(0, 800),
      createdAt: nowIso(),
      deletedAt: null
    };

    cdb.comments.push(comment);
    writeComments(cdb);

    broadcast('comment:new', { memoryId });

    res.json({ success: true, comment });
  } catch (e) {
    res.status(500).json({ success: false, error: e.message });
  }
});

// Stats
app.get('/api/stats', (req, res) => {
  try {
    const db = readDB();
    const approved = db.memories.filter(m => m.approved === 1 && !m.deletedAt && !m.purgedAt);
    const totalLikes = approved.reduce((sum, m) => sum + (m.likes || 0), 0);

    res.json({
      success: true,
      stats: { totalMemories: approved.length, totalLikes }
    });
  } catch (error) {
    console.error('Stats error:', error);
    res.status(500).json({ success: false, error: error.message });
  }
});

// ═══════════════════════════════════════════════════════════════════════════════
// API ENDPOINTS - ADMIN
// ═══════════════════════════════════════════════════════════════════════════════

// Admin login
app.post('/api/admin/login', (req, res) => {
  try {
    const { userId, password } = req.body || {};
    const uid = String(userId || '').trim() || 'super';
    const pwd = String(password || '').trim();

    const admins = readAdmins();
    const user = admins.users.find(u => u.id === uid);

    if (!user || user.disabled) {
      console.log('❌ Failed admin login (no user)');
      return res.status(401).json({ success: false, error: 'Invalid credentials' });
    }

    if (pwd !== user.password) {
      console.log('❌ Failed admin login (bad password)');
      return res.status(401).json({ success: false, error: 'Invalid credentials' });
    }

    const token = generateToken();
    const expiresAt = new Date(Date.now() + TOKEN_TTL_HOURS * 60 * 60 * 1000);

    const sessions = readSessions();
    sessions.sessions = sessions.sessions.filter(s => new Date(s.expiresAt) > new Date());
    sessions.sessions.push({ token, expiresAt: expiresAt.toISOString(), userId: user.id });
    writeSessions(sessions);

    audit(user.id, 'login', {});

    res.json({
      success: true,
      token,
      expiresAt: expiresAt.toISOString(),
      user: { id: user.id, name: user.name, role: user.role, permissions: user.permissions }
    });
  } catch (e) {
    res.status(500).json({ success: false, error: e.message });
  }
});

// Verify token
app.post('/api/admin/verify', (req, res) => {
  try {
    const token = req.headers.authorization?.replace('Bearer ', '');
    const session = getSession(token);
    if (!session) return res.json({ success: true, valid: false });

    const admins = readAdmins();
    const user = admins.users.find(u => u.id === session.userId && !u.disabled);
    if (!user) return res.json({ success: true, valid: false });

    res.json({
      success: true,
      valid: true,
      user: { id: user.id, name: user.name, role: user.role, permissions: user.permissions }
    });
  } catch {
    res.json({ success: true, valid: false });
  }
});

// Admin logout
app.post('/api/admin/logout', (req, res) => {
  try {
    const token = req.headers.authorization?.replace('Bearer ', '');
    if (token) {
      const sessions = readSessions();
      sessions.sessions = sessions.sessions.filter(s => s.token !== token);
      writeSessions(sessions);
    }
    res.json({ success: true, message: 'Logged out' });
  } catch (e) {
    res.status(500).json({ success: false, error: e.message });
  }
});

// Get All Memories (Admin)
app.get('/api/admin/memories', (req, res) => {
  try {
    const auth = requireAdmin(req, res);
    if (!auth) return;
    if (!hasPerm(auth.user, 'moderation')) return res.status(403).json({ success: false, error: 'Forbidden' });

    const { filter, sort, search, includeDeleted } = req.query;
    const page = Math.max(1, parseInt(req.query.page || '1', 10));
    const limit = Math.min(60, Math.max(1, parseInt(req.query.limit || '30', 10)));

    const db = readDB();
    let memories = [...db.memories];

    memories = memories.filter(m => !m.purgedAt);

    if (includeDeleted !== 'true') {
      memories = memories.filter(m => !m.deletedAt);
    }

    if (filter === 'approved') memories = memories.filter(m => m.approved === 1);
    else if (filter === 'pending') memories = memories.filter(m => m.approved === 0);
    else if (filter === 'featured') memories = memories.filter(m => (m.featured || 0) === 1);
    else if (filter === 'trash') memories = memories.filter(m => !!m.deletedAt);

    if (search) {
      const s = String(search).toLowerCase();
      memories = memories.filter(m =>
        String(m.student_name || '').toLowerCase().includes(s) ||
        String(m.caption || '').toLowerCase().includes(s) ||
        String(m.memory_type || '').toLowerCase().includes(s)
      );
    }

    if (sort === 'oldest') memories.sort((a, b) => new Date(a.created_at) - new Date(b.created_at));
    else if (sort === 'likes') memories.sort((a, b) => (b.likes || 0) - (a.likes || 0));
    else memories.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));

    const allMemories = db.memories.filter(m => !m.purgedAt);
    const stats = {
      total: allMemories.filter(m => !m.deletedAt).length,
      approved: allMemories.filter(m => m.approved === 1 && !m.deletedAt).length,
      pending: allMemories.filter(m => m.approved === 0 && !m.deletedAt).length,
      trash: allMemories.filter(m => !!m.deletedAt).length,
      totalSize: allMemories.filter(m => !m.deletedAt).reduce((sum, m) => sum + (m.file_size || 0), 0),
      totalSizeFormatted: formatFileSize(allMemories.filter(m => !m.deletedAt).reduce((sum, m) => sum + (m.file_size || 0), 0))
    };

    const start = (page - 1) * limit;
    const pageItems = memories.slice(start, start + limit).map(m => {
      const shaped = memoryPublicShape(m);
      shaped.reactions = getReactionCountsForMemory(m.id);
      shaped.commentCount = readComments().comments.filter(c => c.memoryId === m.id && !c.deletedAt).length;
      return shaped;
    });

    res.json({
      success: true,
      memories: pageItems,
      stats,
      page,
      limit,
      total: memories.length,
      hasMore: start + limit < memories.length
    });
  } catch (e) {
    res.status(500).json({ success: false, error: e.message });
  }
});

// Approve Memory
app.post('/api/admin/approve/:id', (req, res) => {
  try {
    const auth = requireAdmin(req, res);
    if (!auth) return;
    if (!hasPerm(auth.user, 'moderation')) return res.status(403).json({ success: false, error: 'Forbidden' });

    const id = parseInt(req.params.id, 10);
    const db = readDB();
    const memory = db.memories.find(m => m.id === id && !m.purgedAt);
    if (!memory) return res.status(404).json({ success: false, error: 'Memory not found' });

    memory.approved = 1;
    memory.updated_at = nowIso();
    writeDB(db);

    audit(auth.user.id, 'approve', { memoryId: id });
    broadcast('memory:update', { memoryId: id });

    res.json({ success: true, message: 'Memory approved' });
  } catch (e) {
    res.status(500).json({ success: false, error: e.message });
  }
});

// Approve All Pending
app.post('/api/admin/approve-all', (req, res) => {
  try {
    const auth = requireAdmin(req, res);
    if (!auth) return;
    if (!hasPerm(auth.user, 'bulk')) return res.status(403).json({ success: false, error: 'Forbidden' });

    const db = readDB();
    let count = 0;
    db.memories.forEach(m => {
      if (m.approved === 0 && !m.deletedAt && !m.purgedAt) {
        m.approved = 1;
        m.updated_at = nowIso();
        count++;
      }
    });
    writeDB(db);

    audit(auth.user.id, 'approve-all', { count });
    broadcast('memory:bulk', { type: 'approve', count });

    res.json({ success: true, message: `Approved ${count} memories`, count });
  } catch (e) {
    res.status(500).json({ success: false, error: e.message });
  }
});

// Soft Delete Memory
app.delete('/api/admin/delete/:id', (req, res) => {
  try {
    const auth = requireAdmin(req, res);
    if (!auth) return;
    if (!hasPerm(auth.user, 'trash')) return res.status(403).json({ success: false, error: 'Forbidden' });

    const id = parseInt(req.params.id, 10);
    const db = readDB();
    const memory = db.memories.find(m => m.id === id && !m.purgedAt);
    if (!memory) return res.status(404).json({ success: false, error: 'Memory not found' });

    memory.deletedAt = nowIso();
    memory.updated_at = nowIso();
    writeDB(db);

    audit(auth.user.id, 'trash', { memoryId: id });
    broadcast('memory:update', { memoryId: id });

    res.json({ success: true, message: 'Memory moved to trash' });
  } catch (e) {
    res.status(500).json({ success: false, error: e.message });
  }
});

// Restore from Trash
app.post('/api/admin/restore/:id', (req, res) => {
  try {
    const auth = requireAdmin(req, res);
    if (!auth) return;
    if (!hasPerm(auth.user, 'trash')) return res.status(403).json({ success: false, error: 'Forbidden' });

    const id = parseInt(req.params.id, 10);
    const db = readDB();
    const memory = db.memories.find(m => m.id === id && !m.purgedAt);
    if (!memory) return res.status(404).json({ success: false, error: 'Memory not found' });

    memory.deletedAt = null;
    memory.updated_at = nowIso();
    writeDB(db);

    audit(auth.user.id, 'restore', { memoryId: id });
    broadcast('memory:update', { memoryId: id });

    res.json({ success: true, message: 'Restored' });
  } catch (e) {
    res.status(500).json({ success: false, error: e.message });
  }
});

// Purge

// Reset/Scramble all SHA256 hashes to allow re-uploading duplicates
app.post('/api/admin/reset-hashes', (req, res) => {
  try {
    const auth = requireAdmin(req, res);
    if (!auth) return;
    if (auth.user.role !== 'superadmin') return res.status(403).json({ success: false, error: 'Super admin only' });

    const db = readDB();
    let count = 0;
    
    // Scramble hashes by appending a timestamp, making them unique from future uploads
    db.memories.forEach(m => {
      if (m.sha256 && !m.sha256.startsWith('RESET-')) {
        m.sha256 = `RESET-${Date.now()}-${m.sha256}`;
        count++;
      }
    });

    writeDB(db);
    audit(auth.user.id, 'reset-hashes', { count });
    
    console.log(`♻️  Reset duplicate detection for ${count} memories`);
    res.json({ success: true, count });
  } catch (e) {
    res.status(500).json({ success: false, error: e.message });
  }
});

app.delete('/api/admin/purge/:id', (req, res) => {
  try {
    const auth = requireAdmin(req, res);
    if (!auth) return;
    if (auth.user.role !== 'superadmin') return res.status(403).json({ success: false, error: 'Super admin only' });

    const id = parseInt(req.params.id, 10);
    const db = readDB();
    const memory = db.memories.find(m => m.id === id && !m.purgedAt);
    if (!memory) return res.status(404).json({ success: false, error: 'Memory not found' });

    const fp = path.join(uploadsDir, memory.file_path);
    if (fs.existsSync(fp)) fs.unlinkSync(fp);

    memory.purgedAt = nowIso();
    memory.updated_at = nowIso();
    writeDB(db);

    audit(auth.user.id, 'purge', { memoryId: id });
    broadcast('memory:update', { memoryId: id });

    res.json({ success: true, message: 'Purged permanently' });
  } catch (e) {
    res.status(500).json({ success: false, error: e.message });
  }
});

// Bulk actions
app.post('/api/admin/bulk', (req, res) => {
  try {
    const auth = requireAdmin(req, res);
    if (!auth) return;
    if (!hasPerm(auth.user, 'bulk')) return res.status(403).json({ success: false, error: 'Forbidden' });

    const { action, ids, memoryType } = req.body || {};
    if (!Array.isArray(ids) || ids.length === 0) return res.status(400).json({ success: false, error: 'ids required' });

    const db = readDB();
    const set = new Set(ids.map(x => Number(x)));
    let changed = 0;

    for (const m of db.memories) {
      if (!set.has(m.id) || m.purgedAt) continue;

      if (action === 'approve') {
        if (!m.deletedAt && m.approved === 0) {
          m.approved = 1;
          m.updated_at = nowIso();
          changed++;
        }
      } else if (action === 'trash') {
        if (!m.deletedAt) {
          m.deletedAt = nowIso();
          m.updated_at = nowIso();
          changed++;
        }
      } else if (action === 'restore') {
        if (m.deletedAt) {
          m.deletedAt = null;
          m.updated_at = nowIso();
          changed++;
        }
      } else if (action === 'setType') {
        if (typeof memoryType !== 'string' || !memoryType.trim()) {
          return res.status(400).json({ success: false, error: 'memoryType required' });
        }
        m.memory_type = memoryType.trim();
        m.updated_at = nowIso();
        changed++;
      } else if (action === 'feature') {
        m.featured = 1;
        m.updated_at = nowIso();
        changed++;
      } else if (action === 'unfeature') {
        m.featured = 0;
        m.updated_at = nowIso();
        changed++;
      }
    }

    writeDB(db);
    audit(auth.user.id, 'bulk', { action, changed });
    broadcast('memory:bulk', { type: action, changed });

    res.json({ success: true, changed });
  } catch (e) {
    res.status(500).json({ success: false, error: e.message });
  }
});


// Admin Batch Upload (Skips duplicate checks, profanity filters, and time windows)
app.post('/api/admin/upload-batch', adminUpload.array('files', 100), (req, res) => {
  try {
    const auth = requireAdmin(req, res);
    if (!auth) return;
    if (!hasPerm(auth.user, 'moderation')) return res.status(403).json({ success: false, error: 'Forbidden' });

    const { name, caption, type, autoApprove } = req.body;
    const files = req.files;

    if (!name || !name.trim()) return res.status(400).json({ success: false, error: 'Name required' });
    if (!caption || !caption.trim()) return res.status(400).json({ success: false, error: 'Caption required' });
    if (!files || files.length === 0) return res.status(400).json({ success: false, error: 'Files required' });

    const db = readDB();
    const insertedIds = [];
    const isApproved = autoApprove === 'true' ? 1 : 0;

    files.forEach(file => {
      const filePath = path.join(uploadsDir, file.filename);
      const hash = sha256File(filePath);

      // DELIBERATELY SKIPPING DUPLICATE CHECK
      
      const memory = {
        id: db.nextId++,
        student_name: name.trim(),
        caption: caption.trim().substring(0, 500),
        memory_type: type,
        file_path: file.filename,
        file_name: file.originalname,
        file_type: getFileType(file.mimetype),
        file_size: file.size,
        sha256: hash,
        approved: isApproved,
        featured: 0,
        likes: 0,
        deletedAt: null,
        purgedAt: null,
        created_at: nowIso(),
        updated_at: nowIso()
      };

      db.memories.push(memory);
      insertedIds.push(memory.id);
    });

    writeDB(db);
    audit(auth.user.id, 'batch-upload', { count: insertedIds.length });
    broadcast('memory:new', { count: insertedIds.length });

    res.json({ success: true, count: insertedIds.length, ids: insertedIds });
  } catch (error) {
    console.error('Batch upload error:', error);
    res.status(500).json({ success: false, error: error.message });
  }
});

// Edit memory metadata
app.post('/api/admin/memory/edit/:id', (req, res) => {
  try {
    const auth = requireAdmin(req, res);
    if (!auth) return;
    if (!hasPerm(auth.user, 'editMemory')) return res.status(403).json({ success: false, error: 'Forbidden' });

    const id = parseInt(req.params.id, 10);
    const { caption, memory_type, student_name, featured } = req.body || {};

    const db = readDB();
    const m = db.memories.find(x => x.id === id && !x.purgedAt);
    if (!m) return res.status(404).json({ success: false, error: 'Not found' });

    if (typeof caption === 'string') m.caption = caption.trim().substring(0, 500);
    if (typeof memory_type === 'string') m.memory_type = memory_type.trim();
    if (typeof student_name === 'string') m.student_name = student_name.trim().substring(0, 100);
    if (typeof featured === 'number') m.featured = featured ? 1 : 0;

    m.updated_at = nowIso();
    writeDB(db);

    audit(auth.user.id, 'edit-memory', { memoryId: id });
    broadcast('memory:update', { memoryId: id });

    res.json({ success: true, memory: memoryPublicShape(m) });
  } catch (e) {
    res.status(500).json({ success: false, error: e.message });
  }
});

// Replace file
app.post('/api/admin/memory/replace-file/:id', upload.single('file'), (req, res) => {
  try {
    const auth = requireAdmin(req, res);
    if (!auth) return;
    if (!hasPerm(auth.user, 'replaceFile')) return res.status(403).json({ success: false, error: 'Forbidden' });

    const id = parseInt(req.params.id, 10);
    const file = req.file;
    if (!file) return res.status(400).json({ success: false, error: 'file required' });

    const db = readDB();
    const m = db.memories.find(x => x.id === id && !x.purgedAt);
    if (!m) return res.status(404).json({ success: false, error: 'Not found' });

    const newPath = path.join(uploadsDir, file.filename);
    const hash = sha256File(newPath);
    const exists = db.memories.find(x => x.sha256 === hash && x.id !== id && x.approved === 1 && !x.deletedAt && !x.purgedAt);
    if (exists) {
      if (fs.existsSync(newPath)) fs.unlinkSync(newPath);
      return res.status(409).json({ success: false, error: `Duplicate of memory #${exists.id}` });
    }

    const oldPath = path.join(uploadsDir, m.file_path);
    if (fs.existsSync(oldPath)) fs.unlinkSync(oldPath);

    m.file_path = file.filename;
    m.file_name = file.originalname;
    m.file_type = getFileType(file.mimetype);
    m.file_size = file.size;
    m.sha256 = hash;
    m.updated_at = nowIso();

    writeDB(db);

    audit(auth.user.id, 'replace-file', { memoryId: id });
    broadcast('memory:update', { memoryId: id });

    res.json({ success: true, memory: memoryPublicShape(m) });
  } catch (e) {
    res.status(500).json({ success: false, error: e.message });
  }
});

// Download all approved as ZIP
app.get('/api/admin/download-all', (req, res) => {
  try {
    const token = req.query.token || req.headers.authorization?.replace('Bearer ', '');
    if (!validateAdminToken(token)) return res.status(401).json({ success: false, error: 'Unauthorized' });

    const db = readDB();
    const memories = db.memories.filter(m => m.approved === 1 && !m.deletedAt && !m.purgedAt);

    if (memories.length === 0) return res.status(404).json({ success: false, error: 'No approved memories to download' });

    const timestamp = new Date().toISOString().split('T')[0];
    const zipFilename = `cornerstone-memories-${timestamp}.zip`;

    res.attachment(zipFilename);
    res.setHeader('Content-Type', 'application/zip');

    const archive = archiver('zip', { zlib: { level: 5 } });
    archive.on('error', (err) => {
      console.error('Archive error:', err);
      res.status(500).end();
    });

    archive.pipe(res);
    memories.forEach(memory => {
      const filePath = path.join(uploadsDir, memory.file_path);
      if (fs.existsSync(filePath)) {
        const safeStudentName = memory.student_name.replace(/[^a-zA-Z0-9]/g, '_');
        const ext = path.extname(memory.file_path);
        const archiveName = `${memory.memory_type}/${safeStudentName}-${memory.id}${ext}`;
        archive.file(filePath, { name: archiveName });
      }
    });
    archive.finalize();
  } catch (e) {
    res.status(500).json({ success: false, error: e.message });
  }
});

// Settings save
app.post('/api/admin/settings', (req, res) => {
  try {
    const auth = requireAdmin(req, res);
    if (!auth) return;
    if (!hasPerm(auth.user, 'settings')) return res.status(403).json({ success: false, error: 'Forbidden' });

    const incoming = req.body?.settings;
    if (!incoming || typeof incoming !== 'object') return res.status(400).json({ success: false, error: 'Missing settings object' });

    const istFields = ['farewellIST', 'uploadWindowStartIST', 'uploadWindowEndIST', 'autoApproveStartIST', 'autoApproveEndIST'];
    for (const f of istFields) {
      if (incoming[f] && !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/.test(incoming[f])) {
        return res.status(400).json({ success: false, error: `Invalid ${f} format. Use YYYY-MM-DDTHH:mm` });
      }
    }

    if (incoming.theme && !hasPerm(auth.user, 'theme')) {
      return res.status(403).json({ success: false, error: 'No permission to edit theme' });
    }

    writeSettings({ settings: incoming });
    audit(auth.user.id, 'save-settings', {});
    broadcast('settings:update', {});

    res.json({ success: true });
  } catch (e) {
    res.status(500).json({ success: false, error: e.message });
  }
});

// Change own password
app.post('/api/admin/change-password', (req, res) => {
  try {
    const auth = requireAdmin(req, res);
    if (!auth) return;
    const { oldPassword, newPassword } = req.body || {};
    if (!oldPassword || !newPassword) return res.status(400).json({ success: false, error: 'Missing oldPassword or newPassword' });
    if (String(newPassword).length < 8) return res.status(400).json({ success: false, error: 'Password must be at least 8 characters' });

    const admins = readAdmins();
    const u = admins.users.find(x => x.id === auth.user.id);
    if (!u) return res.status(404).json({ success: false, error: 'User not found' });

    if (u.password !== oldPassword) return res.status(400).json({ success: false, error: 'Old password incorrect' });
    u.password = String(newPassword);
    u.updatedAt = nowIso();
    writeAdmins(admins);

    const sessions = readSessions();
    sessions.sessions = sessions.sessions.filter(s => s.userId !== u.id);
    writeSessions(sessions);

    audit(auth.user.id, 'change-password', {});
    res.json({ success: true });
  } catch (e) {
    res.status(500).json({ success: false, error: e.message });
  }
});

// User management: list
app.get('/api/admin/users', (req, res) => {
  const auth = requireAdmin(req, res);
  if (!auth) return;
  if (!hasPerm(auth.user, 'users')) return res.status(403).json({ success: false, error: 'Forbidden' });

  const admins = readAdmins();
  res.json({
    success: true,
    users: admins.users.map(u => ({
      id: u.id,
      name: u.name,
      role: u.role,
      disabled: !!u.disabled,
      permissions: u.permissions,
      createdAt: u.createdAt,
      updatedAt: u.updatedAt
    }))
  });
});

// User management: create
app.post('/api/admin/users', (req, res) => {
  const auth = requireAdmin(req, res);
  if (!auth) return;
  if (!hasPerm(auth.user, 'users')) return res.status(403).json({ success: false, error: 'Forbidden' });

  const { id, name, password, role, permissions } = req.body || {};
  const uid = String(id || '').trim();
  if (!uid || uid.length < 3) return res.status(400).json({ success: false, error: 'id too short' });
  if (!/^[a-zA-Z0-9_-]+$/.test(uid)) return res.status(400).json({ success: false, error: 'id must be alnum/_/-' });
  if (!password || String(password).length < 8) return res.status(400).json({ success: false, error: 'password min 8 chars' });

  const admins = readAdmins();
  if (admins.users.find(u => u.id === uid)) return res.status(409).json({ success: false, error: 'User already exists' });

  const now = nowIso();
  admins.users.push({
    id: uid,
    name: String(name || uid).trim().substring(0, 60),
    role: role === 'admin' ? 'admin' : 'moderator',
    password: String(password),
    createdAt: now,
    updatedAt: now,
    disabled: false,
    permissions: typeof permissions === 'object' && permissions ? permissions : {
      moderation: true,
      settings: false,
      theme: false,
      export: false,
      users: false,
      trash: true,
      replaceFile: false,
      editMemory: true,
      bulk: false,
      featured: false
    }
  });

  writeAdmins(admins);
  audit(auth.user.id, 'create-user', { id: uid });
  res.json({ success: true });
});

// User management: update
app.post('/api/admin/users/:id', (req, res) => {
  const auth = requireAdmin(req, res);
  if (!auth) return;
  if (!hasPerm(auth.user, 'users')) return res.status(403).json({ success: false, error: 'Forbidden' });

  const uid = String(req.params.id);
  if (uid === 'super') return res.status(400).json({ success: false, error: 'Cannot modify super via this endpoint' });

  const { name, password, disabled, permissions } = req.body || {};
  const admins = readAdmins();
  const u = admins.users.find(x => x.id === uid);
  if (!u) return res.status(404).json({ success: false, error: 'User not found' });

  if (typeof name === 'string') u.name = name.trim().substring(0, 60);
  if (typeof password === 'string' && password.length >= 8) u.password = password;
  if (typeof disabled === 'boolean') u.disabled = disabled;
  if (permissions && typeof permissions === 'object') u.permissions = permissions;

  u.updatedAt = nowIso();
  writeAdmins(admins);

  const sessions = readSessions();
  sessions.sessions = sessions.sessions.filter(s => s.userId !== uid);
  writeSessions(sessions);

  audit(auth.user.id, 'update-user', { id: uid });
  res.json({ success: true });
});

// Export CSV
app.get('/api/admin/export/csv', (req, res) => {
  const auth = requireAdmin(req, res);
  if (!auth) return;
  if (!hasPerm(auth.user, 'export')) return res.status(403).json({ success: false, error: 'Forbidden' });

  const db = readDB();
  const rows = db.memories.filter(m => !m.purgedAt).map(m => ({
    id: m.id,
    student_name: m.student_name,
    caption: m.caption,
    memory_type: m.memory_type,
    approved: m.approved,
    featured: m.featured || 0,
    likes: m.likes || 0,
    file_name: m.file_name,
    file_path: m.file_path,
    file_type: m.file_type,
    file_size: m.file_size,
    sha256: m.sha256,
    created_at: m.created_at,
    deletedAt: m.deletedAt || ''
  }));

  const header = Object.keys(rows[0] || { id: '' });
  const lines = [header.join(',')];
  for (const r of rows) {
    lines.push(header.map(h => `"${sanitizeCsvCell(r[h])}"`).join(','));
  }

  res.setHeader('Content-Type', 'text/csv; charset=utf-8');
  res.setHeader('Content-Disposition', `attachment; filename="memories-export-${new Date().toISOString().slice(0, 10)}.csv"`);
  res.send(lines.join('\n'));
});


// ═══════════════════════════════════════════════════════════════════════════════
// COMPILATIONS API
// ═══════════════════════════════════════════════════════════════════════════════

// Get all compilations (public)
app.get('/api/compilations', (req, res) => {
  try {
    const data = readCompilations();
    res.json({ success: true, compilations: data.compilations || [] });
  } catch (e) {
    res.status(500).json({ success: false, error: e.message });
  }
});

// Get single compilation (public)
app.get('/api/compilations/:id', (req, res) => {
  try {
    const id = parseInt(req.params.id, 10);
    const data = readCompilations();
    const comp = data.compilations.find(c => c.id === id);
    if (!comp) return res.status(404).json({ success: false, error: 'Not found' });
    res.json({ success: true, compilation: comp });
  } catch (e) {
    res.status(500).json({ success: false, error: e.message });
  }
});

// Create compilation (admin)
app.post('/api/admin/compilations', (req, res) => {
  try {
    const auth = requireAdmin(req, res);
    if (!auth) return;
    
    const { name, slides, displayMode, transitionType } = req.body || {};
    if (!name || !Array.isArray(slides)) {
      return res.status(400).json({ success: false, error: 'name and slides required' });
    }
    
    const data = readCompilations();
    const compilation = {
      id: data.nextId++,
      name: String(name).trim().substring(0, 100),
      slides: slides.map(s => ({
        memoryId: Number(s.memoryId),
        caption: String(s.caption || '').trim().substring(0, 300),
        duration: Math.min(60, Math.max(1, Number(s.duration) || 5))
      })),
      displayMode: displayMode === 'manual' ? 'manual' : 'auto',
      transitionType: ['fade', 'slide', 'zoom', 'flip'].includes(transitionType) ? transitionType : 'fade',
      createdAt: nowIso(),
      updatedAt: nowIso()
    };
    
    data.compilations.push(compilation);
    writeCompilations(data);
    
    audit(auth.user.id, 'create-compilation', { id: compilation.id });
    res.json({ success: true, compilation });
  } catch (e) {
    res.status(500).json({ success: false, error: e.message });
  }
});

// Update compilation (admin)
app.post('/api/admin/compilations/:id', (req, res) => {
  try {
    const auth = requireAdmin(req, res);
    if (!auth) return;
    
    const id = parseInt(req.params.id, 10);
    const data = readCompilations();
    const comp = data.compilations.find(c => c.id === id);
    if (!comp) return res.status(404).json({ success: false, error: 'Not found' });
    
    const { name, slides, displayMode, transitionType } = req.body || {};
    if (name) comp.name = String(name).trim().substring(0, 100);
    if (Array.isArray(slides)) {
      comp.slides = slides.map(s => ({
        memoryId: Number(s.memoryId),
        caption: String(s.caption || '').trim().substring(0, 300),
        duration: Math.min(60, Math.max(1, Number(s.duration) || 5))
      }));
    }
    if (displayMode) comp.displayMode = displayMode === 'manual' ? 'manual' : 'auto';
    if (transitionType && ['fade', 'slide', 'zoom', 'flip'].includes(transitionType)) {
      comp.transitionType = transitionType;
    }
    comp.updatedAt = nowIso();
    
    writeCompilations(data);
    audit(auth.user.id, 'update-compilation', { id });
    res.json({ success: true, compilation: comp });
  } catch (e) {
    res.status(500).json({ success: false, error: e.message });
  }
});

// Delete compilation (admin)
app.delete('/api/admin/compilations/:id', (req, res) => {
  try {
    const auth = requireAdmin(req, res);
    if (!auth) return;
    
    const id = parseInt(req.params.id, 10);
    const data = readCompilations();
    const idx = data.compilations.findIndex(c => c.id === id);
    if (idx === -1) return res.status(404).json({ success: false, error: 'Not found' });
    
    data.compilations.splice(idx, 1);
    writeCompilations(data);
    
    audit(auth.user.id, 'delete-compilation', { id });
    res.json({ success: true });
  } catch (e) {
    res.status(500).json({ success: false, error: e.message });
  }
});

// Edit comment (admin)
app.post('/api/admin/comments/:id', (req, res) => {
  try {
    const auth = requireAdmin(req, res);
    if (!auth) return;
    if (!hasPerm(auth.user, 'moderation')) return res.status(403).json({ success: false, error: 'Forbidden' });
    
    const id = parseInt(req.params.id, 10);
    const { text, deleted } = req.body || {};
    
    const cdb = readComments();
    const comment = cdb.comments.find(c => c.id === id);
    if (!comment) return res.status(404).json({ success: false, error: 'Comment not found' });
    
    if (typeof text === 'string') comment.text = text.trim().substring(0, 800);
    if (deleted === true) comment.deletedAt = nowIso();
    if (deleted === false) comment.deletedAt = null;
    
    writeComments(cdb);
    audit(auth.user.id, 'edit-comment', { commentId: id });
    
    res.json({ success: true, comment });
  } catch (e) {
    res.status(500).json({ success: false, error: e.message });
  }
});

// Upload intro video (admin)
app.post('/api/admin/upload-intro-video', adminUpload.single('video'), (req, res) => {
  try {
    const auth = requireAdmin(req, res);
    if (!auth) return;
    if (!hasPerm(auth.user, 'settings')) return res.status(403).json({ success: false, error: 'Forbidden' });
    
    const file = req.file;
    if (!file) return res.status(400).json({ success: false, error: 'No video file' });
    
    // Save path to settings
    const settings = readSettings();
    settings.settings = settings.settings || {};
    settings.settings.introVideoPath = file.filename;
    writeSettings(settings);
    
    audit(auth.user.id, 'upload-intro-video', { filename: file.filename });
    res.json({ success: true, path: file.filename });
  } catch (e) {
    res.status(500).json({ success: false, error: e.message });
  }
});

// Upload favicon (admin)
app.post('/api/admin/upload-favicon', upload.single('favicon'), (req, res) => {
  try {
    const auth = requireAdmin(req, res);
    if (!auth) return;
    if (!hasPerm(auth.user, 'settings')) return res.status(403).json({ success: false, error: 'Forbidden' });
    
    const file = req.file;
    if (!file) return res.status(400).json({ success: false, error: 'No file' });
    
    // Copy to favicon.ico in root
    const faviconDest = path.join(__dirname, 'favicon.ico');
    fs.copyFileSync(path.join(uploadsDir, file.filename), faviconDest);
    
    const settings = readSettings();
    settings.settings = settings.settings || {};
    settings.settings.faviconUploaded = true;
    writeSettings(settings);
    
    audit(auth.user.id, 'upload-favicon', {});
    res.json({ success: true });
  } catch (e) {
    res.status(500).json({ success: false, error: e.message });
  }
});

// Upload teacher image (admin)
app.post('/api/admin/upload-teacher-image', upload.single('image'), (req, res) => {
  try {
    const auth = requireAdmin(req, res);
    if (!auth) return;
    
    const file = req.file;
    if (!file) return res.status(400).json({ success: false, error: 'No image file' });
    
    res.json({ success: true, url: `/uploads/${file.filename}` });
  } catch (e) {
    res.status(500).json({ success: false, error: e.message });
  }
});

// ═══════════════════════════════════════════════════════════════════════════════
// SERVE FRONTEND
// ═══════════════════════════════════════════════════════════════════════════════

app.get('/', (req, res) => res.sendFile(path.join(__dirname, 'index.html')));
app.get('*', (req, res) => res.sendFile(path.join(__dirname, 'index.html')));

// ═══════════════════════════════════════════════════════════════════════════════
// ERROR HANDLING
// ═══════════════════════════════════════════════════════════════════════════════

app.use((err, req, res, next) => {
  console.error('Server error:', err);

  if (err instanceof multer.MulterError) {
    if (err.code === 'LIMIT_FILE_SIZE') {
      return res.status(400).json({ success: false, error: `File too large. Maximum size is ${MAX_FILE_SIZE / 1024 / 1024}MB per file.` });
    }
    if (err.code === 'LIMIT_FILE_COUNT') {
      return res.status(400).json({ success: false, error: `Too many files. Maximum is ${MAX_FILES} files per upload.` });
    }
  }
  res.status(500).json({ success: false, error: err.message || 'Internal server error' });
});

// ═══════════════════════════════════════════════════════════════════════════════
// START SERVER
// ═══════════════════════════════════════════════════════════════════════════════



// === SNIPER_SERVER_PATCH_V2_START ===
(() => {
  if (global.__SNIPER_SERVER_PATCH_V2__) return;
  global.__SNIPER_SERVER_PATCH_V2__ = true;

  const teacherAudioPath = path.join(databaseDir, 'teacher_audio.json');
  const paperNotesPath = path.join(databaseDir, 'paper_notes.json');
  const destinationsPath = path.join(databaseDir, 'destinations.json');

  function ensurePatchDb(filePath, fallback) {
    if (!fs.existsSync(filePath)) safeWriteJson(filePath, fallback);
  }

  ensurePatchDb(teacherAudioPath, { items: [], nextId: 1 });
  ensurePatchDb(paperNotesPath, { notes: [], nextId: 1 });
  ensurePatchDb(destinationsPath, { destinations: [], submissions: [], nextId: 1 });

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
  }

  function parseBearer(req) {
    return req.headers.authorization?.replace('Bearer ', '') || '';
  }

  function sendWs(event, payload) {
    try { broadcast(event, payload); } catch (_) {}
  }

  // Route aliases for frontend compatibility
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
      sendWs('settings:update', {});
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
      sendWs('settings:update', {});
      res.json({ success: true });
    } catch (e) {
      res.status(500).json({ success: false, error: e.message });
    }
  });

  // Teacher audio
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
      const teacherName = String(req.body.teacherName || '').trim();
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
      sendWs('settings:update', {});
      res.json({ success: true, item });
    } catch (e) {
      res.status(500).json({ success: false, error: e.message });
    }
  });

  // Destinations allowlist and submissions
  app.get('/api/destinations', (req, res) => {
    try {
      const db = readDestinationsDb();
      res.json({ success: true, destinations: db.destinations || [] });
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
      const cleaned = raw
        .map(x => String(typeof x === 'string' ? x : x?.name || '').trim())
        .filter(Boolean)
        .slice(0, 500)
        .map(name => ({ name }));

      const db = readDestinationsDb();
      db.destinations = cleaned;
      writeDestinationsDb(db);
      audit(auth.user.id, 'save-destinations', { count: cleaned.length });
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
      const ok = db.destinations.find(x => String(x.name || '').trim().toLowerCase() === destination.toLowerCase());
      if (!ok) return res.status(400).json({ success: false, error: 'Destination is not allowed' });

      db.submissions.push({
        id: db.nextId++,
        destination,
        ip: req.headers['x-forwarded-for'] || req.socket.remoteAddress || '',
        createdAt: nowIso()
      });
      if (db.submissions.length > 5000) db.submissions = db.submissions.slice(-5000);
      writeDestinationsDb(db);
      res.json({ success: true });
    } catch (e) {
      res.status(500).json({ success: false, error: e.message });
    }
  });

  // Paper notes
  app.post('/api/paper-notes', (req, res) => {
    try {
      const text = String(req.body?.text || '').trim().substring(0, 400);
      if (!text) return res.status(400).json({ success: false, error: 'text required' });
      const db = readPaperNotes();
      const note = {
        id: db.nextId++,
        text,
        ip: req.headers['x-forwarded-for'] || req.socket.remoteAddress || '',
        createdAt: nowIso()
      };
      db.notes.push(note);
      if (db.notes.length > 3000) db.notes = db.notes.slice(-3000);
      writePaperNotes(db);
      sendWs('paper:note', { id: note.id });
      res.json({ success: true, noteId: note.id });
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

  console.log('SNIPER patch server extension loaded.');
})();









// === SNIPER_SERVER_PATCH_V4_START ===
(() => {
  if (global.__SNIPER_SERVER_PATCH_V4__) return;
  global.__SNIPER_SERVER_PATCH_V4__ = true;

  const destinationsPathV4 = path.join(databaseDir, 'destinations.json');

  function readDestinationsV4() {
    return safeReadJson(destinationsPathV4, { destinations: [], submissions: [], nextId: 1 });
  }
  function writeDestinationsV4(data) {
    safeWriteJson(destinationsPathV4, data);
  }

  app.post('/api/admin/destinations-v2', (req, res) => {
    try {
      const auth = requireAdmin(req, res);
      if (!auth) return;
      if (!hasPerm(auth.user, 'settings')) return res.status(403).json({ success: false, error: 'Forbidden' });

      const places = Array.isArray(req.body?.places) ? req.body.places : [];
      const cleaned = places
        .map(x => String(x || '').trim())
        .filter(Boolean)
        .slice(0, 600)
        .map(place => ({ place }));

      const db = readDestinationsV4();
      db.destinations = cleaned;
      writeDestinationsV4(db);
      audit(auth.user.id, 'save-destinations-v2', { count: cleaned.length });
      res.json({ success: true, count: cleaned.length });
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

      const db = readDestinationsV4();
      const allowed = new Set((db.destinations || []).map(x => String(x.place || x.name || '').trim().toLowerCase()));

      if (schoolPlace && !allowed.has(schoolPlace.toLowerCase())) {
        return res.status(400).json({ success: false, error: 'School place is not allowed' });
      }
      if (universityPlace && !allowed.has(universityPlace.toLowerCase())) {
        return res.status(400).json({ success: false, error: 'University place is not allowed' });
      }

      const existing = (db.submissions || []).find(x => String(x.studentName || '').trim().toLowerCase() === studentName.toLowerCase());
      if (existing) {
        existing.schoolPlace = schoolPlace;
        existing.universityPlace = universityPlace;
        existing.updatedAt = nowIso();
      } else {
        db.submissions.push({
          id: db.nextId++,
          studentName,
          schoolPlace,
          universityPlace,
          createdAt: nowIso(),
          updatedAt: nowIso()
        });
      }

      if (db.submissions.length > 5000) db.submissions = db.submissions.slice(-5000);
      writeDestinationsV4(db);
      broadcast('destinations:update', { studentName });
      res.json({ success: true });
    } catch (e) {
      res.status(500).json({ success: false, error: e.message });
    }
  });

  app.get('/api/destinations/submissions', (req, res) => {
    try {
      const db = readDestinationsV4();
      res.json({ success: true, submissions: db.submissions || [] });
    } catch (e) {
      res.status(500).json({ success: false, error: e.message });
    }
  });

  console.log('SNIPER patch server v4 loaded.');
})();

















server.listen(PORT, '0.0.0.0', () => {
  console.log('');
  console.log('═══════════════════════════════════════════════════════════════════');
  console.log('🎓 CORNERSTONE INTERNATIONAL SCHOOL - FAREWELL 2025');
  console.log('═══════════════════════════════════════════════════════════════════');
  console.log(`🚀 Server running on: http://localhost:${PORT}`);
  console.log(`🌐 Network access: http://0.0.0.0:${PORT}`);
  console.log(`📁 Uploads folder: ${uploadsDir}`);
  console.log(`💾 Memories DB: ${dbPath}`);
  console.log(`⚙️ Settings DB: ${settingsPath}`);
  console.log(`🔐 Admin DB: ${adminPath}`);
  console.log(`💬 Comments DB: ${commentsPath}`);
  console.log(`😊 Reactions DB: ${reactionsPath}`);
  console.log(`🧾 Audit DB: ${auditPath}`);
  console.log(`📊 Max upload size: ${MAX_TOTAL_SIZE / 1024 / 1024}MB total`);
  console.log(`🛡️ Profanity filter: bad-words + obscenity + custom patterns`);
  console.log('═══════════════════════════════════════════════════════════════════');
  console.log('');
});

// Graceful shutdown
process.on('SIGTERM', () => {
  console.log('🛑 SIGTERM received. Closing server...');
  process.exit(0);
});
process.on('SIGINT', () => {
  console.log('🛑 SIGINT received. Closing server...');
  process.exit(0);
});