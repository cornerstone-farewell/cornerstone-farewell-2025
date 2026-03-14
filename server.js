/**
 * ═══════════════════════════════════════════════════════════════════════════════
 * CORNERSTONE FAREWELL 2025 - COMPLETE SERVER REWRITE
 * Part 1 of 3: Core Setup, Utilities, Database, Auth, Public APIs
 * ═══════════════════════════════════════════════════════════════════════════════
 * CLAUDE OPUS 4-5
 */

const express = require('express');
const multer = require('multer');
const path = require('path');
const fs = require('fs');
const crypto = require('crypto');
const http = require('http');
const archiver = require('archiver');
const cors = require('cors');

// ═══════════════════════════════════════════════════════════════════════════════
// CONFIGURATION
// ═══════════════════════════════════════════════════════════════════════════════
const PORT = process.env.PORT || 3000;
const ADMIN_PASSWORD = process.env.ADMIN_PASSWORD || 'cornerstone2025';
const MAX_FILE_SIZE = 100 * 1024 * 1024; // 100MB
const MAX_TOTAL_SIZE = 200 * 1024 * 1024; // 200MB
const MAX_FILES = 20;
const TOKEN_TTL_MS = 24 * 60 * 60 * 1000; // 24 hours
const REACTION_TYPES = ['like', 'love', 'laugh', 'wow', 'sad'];

// ═══════════════════════════════════════════════════════════════════════════════
// EXPRESS + HTTP SERVER SETUP
// ═══════════════════════════════════════════════════════════════════════════════
const app = express();
const server = http.createServer(app);

// WebSocket setup
let WebSocket;
let wss;
try {
    WebSocket = require('ws');
    wss = new WebSocket.Server({ server });
    wss.on('connection', (ws) => {
        ws.send(JSON.stringify({ event: 'connected', payload: { ok: true } }));
    });
} catch (e) {
    console.log('WebSocket not available, continuing without real-time updates');
    wss = { clients: new Set() };
}

// Middleware
app.use(cors({
    origin: '*',
    methods: ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS'],
    allowedHeaders: ['Content-Type', 'Authorization']
}));
app.use(express.json({ limit: '10mb' }));
app.use(express.urlencoded({ extended: true, limit: '10mb' }));

// ═══════════════════════════════════════════════════════════════════════════════
// DIRECTORY SETUP
// ═══════════════════════════════════════════════════════════════════════════════
const uploadsDir = path.join(__dirname, 'uploads');
const databaseDir = path.join(__dirname, 'database');
const musicDir = path.join(__dirname, 'music');
const funDir = path.join(databaseDir, 'fun');

[uploadsDir, databaseDir, musicDir, funDir].forEach(dir => {
    if (!fs.existsSync(dir)) {
        fs.mkdirSync(dir, { recursive: true });
        console.log(`Created directory: ${dir}`);
    }
});

// Block sensitive files
app.use((req, res, next) => {
    const blocked = ['/database', '/logs', '/server.js', '/package.json', '/package-lock.json', '/.env'];
    const reqPath = decodeURIComponent(req.path || '');
    if (blocked.some(b => reqPath.startsWith(b) || reqPath === b)) {
        return res.status(404).end();
    }
    next();
});

// Static files
app.use('/uploads', express.static(uploadsDir));
app.use('/music', express.static(musicDir));
app.use(express.static(__dirname));

// ═══════════════════════════════════════════════════════════════════════════════
// DATABASE PATHS
// ═══════════════════════════════════════════════════════════════════════════════
const DB_PATHS = {
    memories: path.join(databaseDir, 'memories.json'),
    sessions: path.join(databaseDir, 'sessions.json'),
    settings: path.join(databaseDir, 'settings.json'),
    admin: path.join(databaseDir, 'admin.json'),
    comments: path.join(databaseDir, 'comments.json'),
    reactions: path.join(databaseDir, 'reactions.json'),
    audit: path.join(databaseDir, 'audit.json'),
    destinations: path.join(databaseDir, 'destinations.json'),
    compilations: path.join(databaseDir, 'compilations.json'),
    teacherAudio: path.join(databaseDir, 'teacher_audio.json'),
    studentDirectory: path.join(databaseDir, 'student_directory.json'),
    paperNotes: path.join(databaseDir, 'paper_notes.json'),
    advice: path.join(databaseDir, 'advice.json'),
    bans: path.join(databaseDir, 'bans.json'),
    // Fun features
    gratitude: path.join(funDir, 'gratitude.json'),
    superlatives: path.join(funDir, 'superlatives.json'),
    wishes: path.join(funDir, 'wishes.json'),
    dedications: path.join(funDir, 'dedications.json'),
    mood: path.join(funDir, 'mood.json'),
    capsules: path.join(funDir, 'capsules.json'),
    funSettings: path.join(funDir, 'settings.json')
};

// ═══════════════════════════════════════════════════════════════════════════════
// DATABASE DEFAULTS
// ═══════════════════════════════════════════════════════════════════════════════
const DB_DEFAULTS = {
    memories: { memories: [], nextId: 1 },
    sessions: { sessions: [] },
    settings: { settings: {} },
    admin: {
        users: [{
            id: 'super',
            name: 'Super Admin',
            role: 'superadmin',
            password: ADMIN_PASSWORD,
            createdAt: new Date().toISOString(),
            updatedAt: new Date().toISOString(),
            disabled: false,
            permissions: {
                moderation: true, settings: true, theme: true, export: true,
                users: true, trash: true, replaceFile: true, editMemory: true,
                bulk: true, featured: true
            }
        }]
    },
    comments: { comments: [], nextId: 1 },
    reactions: { reactions: [] },
    audit: { events: [], nextId: 1 },
    destinations: { pins: [], nextId: 1 },
    compilations: { compilations: [], nextId: 1 },
    teacherAudio: { tracks: [], nextId: 1 },
    studentDirectory: { students: [] },
    paperNotes: { notes: [], nextId: 1 },
    advice: { entries: [], nextId: 1 },
    bans: { bans: [], nextId: 1 },
    gratitude: { entries: [], nextId: 1 },
    superlatives: { categories: [], nextId: 1 },
    wishes: { entries: [], nextId: 1 },
    dedications: { entries: [], nextId: 1 },
    mood: { votes: [], options: ['Excited', 'Happy', 'Nostalgic', 'Bittersweet', 'Emotional'] },
    capsules: { entries: [], nextId: 1 },
    funSettings: { enabled: { gratitude: true, superlatives: true, wishes: true, dedications: true, mood: true, capsules: true } }
};

// ═══════════════════════════════════════════════════════════════════════════════
// DATABASE UTILITIES
// ═══════════════════════════════════════════════════════════════════════════════
function readJSON(filePath, fallback = {}) {
    try {
        if (!fs.existsSync(filePath)) return fallback;
        const data = fs.readFileSync(filePath, 'utf8');
        return JSON.parse(data);
    } catch (e) {
        console.error(`Error reading ${filePath}:`, e.message);
        return fallback;
    }
}

function writeJSON(filePath, data) {
    try {
        fs.writeFileSync(filePath, JSON.stringify(data, null, 2));
        return true;
    } catch (e) {
        console.error(`Error writing ${filePath}:`, e.message);
        return false;
    }
}

function db(name) {
    return readJSON(DB_PATHS[name], DB_DEFAULTS[name] || {});
}

function saveDb(name, data) {
    return writeJSON(DB_PATHS[name], data);
}

// Initialize all databases
function initDatabases() {
    Object.entries(DB_PATHS).forEach(([name, filePath]) => {
        if (!fs.existsSync(filePath)) {
            writeJSON(filePath, DB_DEFAULTS[name] || {});
            console.log(`Initialized: ${name}`);
        }
    });
}

initDatabases();

// ═══════════════════════════════════════════════════════════════════════════════
// UTILITY FUNCTIONS
// ═══════════════════════════════════════════════════════════════════════════════
function nowISO() {
    return new Date().toISOString();
}

function generateToken() {
    return `admin-${Date.now()}-${crypto.randomBytes(16).toString('hex')}`;
}

function sha256(buffer) {
    return crypto.createHash('sha256').update(buffer).digest('hex');
}

function sha256File(filePath) {
    try {
        const buffer = fs.readFileSync(filePath);
        return sha256(buffer);
    } catch (e) {
        return null;
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
    if (!mimetype) return 'unknown';
    if (mimetype.startsWith('image/')) return 'image';
    if (mimetype.startsWith('video/')) return 'video';
    if (mimetype.startsWith('audio/')) return 'audio';
    return 'unknown';
}

function broadcast(event, payload) {
    if (!wss || !wss.clients) return;
    const msg = JSON.stringify({ event, payload });
    wss.clients.forEach(client => {
        if (client.readyState === 1) { // WebSocket.OPEN
            try { client.send(msg); } catch (e) { }
        }
    });
}

function containsProfanity(text) {
    const badWords = ['fuck', 'shit', 'bitch', 'asshole', 'bastard', 'dick', 'pussy', 'slut', 'cunt'];
    const t = String(text || '').toLowerCase();
    return badWords.some(w => t.includes(w));
}

function sanitizeCSV(val) {
    const s = String(val ?? '');
    if (/^[=\-+@]/.test(s)) return `'${s}`;
    return s.replace(/"/g, '""');
}

function audit(userId, action, meta = {}) {
    try {
        const data = db('audit');
        data.events.push({
            id: data.nextId++,
            userId,
            action,
            meta,
            createdAt: nowISO()
        });
        if (data.events.length > 5000) data.events = data.events.slice(-5000);
        saveDb('audit', data);
    } catch (e) { }
}

// ═══════════════════════════════════════════════════════════════════════════════
// SETTINGS HELPERS
// ═══════════════════════════════════════════════════════════════════════════════
function getSettings() {
    const data = db('settings');
    const defaults = {
        uploadsEnabled: true,
        commentsEnabled: true,
        profanityFilterEnabled: false,
        maintenanceMode: false,
        uploadWindowEnabled: false,
        uploadWindowStartIST: '',
        uploadWindowEndIST: '',
        autoApproveEnabled: false,
        autoApproveStartIST: '',
        autoApproveEndIST: '',
        theme: {}
    };
    return { ...defaults, ...(data.settings || {}) };
}

function parseISTToDate(istString) {
    if (!istString || !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/.test(istString)) return null;
    const [datePart, timePart] = istString.split('T');
    const [Y, M, D] = datePart.split('-').map(Number);
    const [h, m] = timePart.split(':').map(Number);
    // IST is UTC+5:30
    return new Date(Date.UTC(Y, M - 1, D, h - 5, m - 30));
}

function isWithinWindow(startIST, endIST) {
    const start = parseISTToDate(startIST);
    const end = parseISTToDate(endIST);
    if (!start || !end) return false;
    const now = new Date();
    return now >= start && now <= end;
}

// ═══════════════════════════════════════════════════════════════════════════════
// AUTH HELPERS
// ═══════════════════════════════════════════════════════════════════════════════
function cleanExpiredSessions() {
    const data = db('sessions');
    const now = Date.now();
    const before = data.sessions.length;
    data.sessions = data.sessions.filter(s => new Date(s.expiresAt).getTime() > now);
    if (data.sessions.length !== before) saveDb('sessions', data);
}

function getSession(token) {
    if (!token) return null;
    cleanExpiredSessions();
    const data = db('sessions');
    return data.sessions.find(s => s.token === token) || null;
}

function validateToken(token) {
    return !!getSession(token);
}

function extractToken(req) {
    const auth = req.headers.authorization;
    if (auth && auth.startsWith('Bearer ')) {
        return auth.slice(7);
    }
    return req.query.token || req.body?.token || null;
}

function requireAdmin(req, res) {
    const token = extractToken(req);
    const session = getSession(token);
    if (!session) {
        res.status(401).json({ success: false, error: 'Unauthorized' });
        return null;
    }
    const admins = db('admin');
    const user = admins.users.find(u => u.id === session.userId && !u.disabled);
    if (!user) {
        res.status(401).json({ success: false, error: 'Unauthorized' });
        return null;
    }
    return { token, session, user };
}

function hasPerm(user, perm) {
    if (!user) return false;
    if (user.role === 'superadmin') return true;
    return !!(user.permissions && user.permissions[perm]);
}

// ═══════════════════════════════════════════════════════════════════════════════
// MULTER SETUP
// ═══════════════════════════════════════════════════════════════════════════════
const storage = multer.diskStorage({
    destination: (req, file, cb) => cb(null, uploadsDir),
    filename: (req, file, cb) => {
        const unique = `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
        const ext = path.extname(file.originalname).toLowerCase();
        const safeName = file.originalname.replace(/[^a-zA-Z0-9.-]/g, '_').substring(0, 40);
        cb(null, `${unique}-${safeName}`);
    }
});

const fileFilter = (req, file, cb) => {
    const allowed = [
        'image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp',
        'video/mp4', 'video/quicktime', 'video/x-msvideo', 'video/webm',
        'audio/mpeg', 'audio/mp3', 'audio/wav', 'audio/ogg', 'audio/webm'
    ];
    if (allowed.includes(file.mimetype)) cb(null, true);
    else cb(new Error(`Invalid file type: ${file.mimetype}`), false);
};

const upload = multer({
    storage,
    limits: { fileSize: MAX_FILE_SIZE, files: MAX_FILES },
    fileFilter
});

const musicStorage = multer.diskStorage({
    destination: (req, file, cb) => cb(null, musicDir),
    filename: (req, file, cb) => {
        const ext = path.extname(file.originalname).toLowerCase();
        cb(null, `bg-music-${Date.now()}${ext}`);
    }
});

const uploadMusic = multer({
    storage: musicStorage,
    fileFilter: (req, file, cb) => {
        if (file.mimetype.startsWith('audio/')) cb(null, true);
        else cb(new Error('Only audio files allowed'), false);
    }
});

// ═══════════════════════════════════════════════════════════════════════════════
// MEMORY HELPERS
// ═══════════════════════════════════════════════════════════════════════════════
function memoryToPublic(m) {
    return {
        ...m,
        file_url: `/uploads/${m.file_path}`,
        file_size_formatted: formatFileSize(m.file_size || 0)
    };
}

function getReactionCounts(memoryId) {
    const data = db('reactions');
    const counts = {};
    REACTION_TYPES.forEach(t => counts[t] = 0);
    data.reactions.filter(r => r.memoryId === memoryId).forEach(r => {
        if (counts[r.type] !== undefined) counts[r.type]++;
    });
    return counts;
}

function getCommentTree(memoryId) {
    const data = db('comments');
    const all = data.comments
        .filter(c => c.memoryId === memoryId && !c.deletedAt)
        .sort((a, b) => new Date(a.createdAt) - new Date(b.createdAt));

    const byId = new Map();
    all.forEach(c => byId.set(c.id, { ...c, replies: [] }));

    const roots = [];
    byId.forEach(c => {
        if (c.parentId && byId.has(c.parentId)) {
            byId.get(c.parentId).replies.push(c);
        } else {
            roots.push(c);
        }
    });
    return roots;
}

// ═══════════════════════════════════════════════════════════════════════════════
// PUBLIC API: SETTINGS
// ═══════════════════════════════════════════════════════════════════════════════
app.get('/api/settings', (req, res) => {
    try {
        const data = db('settings');
        res.json({ success: true, settings: data.settings || {} });
    } catch (e) {
        res.status(500).json({ success: false, error: e.message });
    }
});

// ═══════════════════════════════════════════════════════════════════════════════
// PUBLIC API: UPLOAD MEMORY
// ═══════════════════════════════════════════════════════════════════════════════
app.post('/api/upload', (req, res) => {
    // Handle multiple field name variations from frontend
    const uploadHandler = upload.any();

    uploadHandler(req, res, (err) => {
        if (err) {
            return res.status(400).json({ success: false, error: err.message });
        }

        try {
            const settings = getSettings();

            // Check maintenance mode
            if (settings.maintenanceMode) {
                if (req.files) req.files.forEach(f => {
                    try { fs.unlinkSync(path.join(uploadsDir, f.filename)); } catch (e) { }
                });
                return res.status(503).json({ success: false, error: 'Site is in maintenance mode.' });
            }

            // Check uploads enabled
            if (!settings.uploadsEnabled) {
                if (req.files) req.files.forEach(f => {
                    try { fs.unlinkSync(path.join(uploadsDir, f.filename)); } catch (e) { }
                });
                return res.status(403).json({ success: false, error: 'Uploads are currently disabled.' });
            }

            // Check upload window
            if (settings.uploadWindowEnabled) {
                if (!isWithinWindow(settings.uploadWindowStartIST, settings.uploadWindowEndIST)) {
                    if (req.files) req.files.forEach(f => {
                        try { fs.unlinkSync(path.join(uploadsDir, f.filename)); } catch (e) { }
                    });
                    return res.status(403).json({ success: false, error: 'Uploads are currently closed.' });
                }
            }

            const name = req.body.name || req.body.student_name;
            const caption = req.body.caption;
            const type = req.body.type || req.body.memory_type || 'general';
            const files = req.files || [];

            if (!name || !name.trim()) {
                files.forEach(f => { try { fs.unlinkSync(path.join(uploadsDir, f.filename)); } catch (e) { } });
                return res.status(400).json({ success: false, error: 'Student name is required' });
            }

            if (!caption || !caption.trim()) {
                files.forEach(f => { try { fs.unlinkSync(path.join(uploadsDir, f.filename)); } catch (e) { } });
                return res.status(400).json({ success: false, error: 'Caption is required' });
            }

            if (files.length === 0) {
                return res.status(400).json({ success: false, error: 'Please select at least one file' });
            }

            // Check total size
            const totalSize = files.reduce((sum, f) => sum + f.size, 0);
            if (totalSize > MAX_TOTAL_SIZE) {
                files.forEach(f => { try { fs.unlinkSync(path.join(uploadsDir, f.filename)); } catch (e) { } });
                return res.status(400).json({ success: false, error: `Total upload size exceeds ${MAX_TOTAL_SIZE / 1024 / 1024}MB` });
            }

            // Profanity filter
            if (settings.profanityFilterEnabled) {
                if (containsProfanity(name) || containsProfanity(caption)) {
                    files.forEach(f => { try { fs.unlinkSync(path.join(uploadsDir, f.filename)); } catch (e) { } });
                    return res.status(400).json({ success: false, error: 'Content rejected by profanity filter.' });
                }
            }

            const data = db('memories');
            const insertedIds = [];
            const duplicates = [];

            const autoApprove = settings.autoApproveEnabled &&
                isWithinWindow(settings.autoApproveStartIST, settings.autoApproveEndIST);

            files.forEach(file => {
                const filePath = path.join(uploadsDir, file.filename);
                const hash = sha256File(filePath);

                // Check for duplicates
                if (hash) {
                    const existing = data.memories.find(m => m.sha256 === hash && !m.purgedAt);
                    if (existing) {
                        duplicates.push({ originalId: existing.id, duplicateFile: file.originalname });
                        try { fs.unlinkSync(filePath); } catch (e) { }
                        return;
                    }
                }

                const memory = {
                    id: data.nextId++,
                    student_name: name.trim(),
                    caption: caption.trim().substring(0, 1000),
                    memory_type: type,
                    file_path: file.filename,
                    file_name: file.originalname,
                    file_type: getFileType(file.mimetype),
                    file_size: file.size,
                    sha256: hash,
                    approved: autoApprove ? 1 : 0,
                    featured: 0,
                    likes: 0,
                    deletedAt: null,
                    purgedAt: null,
                    created_at: nowISO(),
                    updated_at: nowISO()
                };

                data.memories.push(memory);
                insertedIds.push(memory.id);
            });

            saveDb('memories', data);

            if (insertedIds.length === 0 && duplicates.length > 0) {
                return res.status(409).json({
                    success: false,
                    error: 'All files were duplicates.',
                    duplicates
                });
            }

            broadcast('memory:new', { count: insertedIds.length });

            res.json({
                success: true,
                message: `Uploaded ${insertedIds.length} memory(s)!`,
                count: insertedIds.length,
                ids: insertedIds,
                duplicates
            });

        } catch (e) {
            console.error('Upload error:', e);
            res.status(500).json({ success: false, error: e.message });
        }
    });
});

// ═══════════════════════════════════════════════════════════════════════════════
// PUBLIC API: GET MEMORIES
// ═══════════════════════════════════════════════════════════════════════════════
app.get('/api/memories', (req, res) => {
    try {
        const data = db('memories');
        const page = Math.max(1, parseInt(req.query.page) || 1);
        const limit = Math.min(500, Math.max(1, parseInt(req.query.limit) || 20));
        const type = req.query.type || 'all';

        let memories = data.memories.filter(m =>
            m.approved === 1 && !m.deletedAt && !m.purgedAt
        );

        if (type !== 'all') {
            memories = memories.filter(m => m.memory_type === type);
        }

        // Sort: featured first, then newest
        memories.sort((a, b) => {
            if ((b.featured || 0) !== (a.featured || 0)) {
                return (b.featured || 0) - (a.featured || 0);
            }
            return new Date(b.created_at) - new Date(a.created_at);
        });

        const total = memories.length;
        const start = (page - 1) * limit;
        const items = memories.slice(start, start + limit).map(m => {
            const pub = memoryToPublic(m);
            pub.reactions = getReactionCounts(m.id);
            return pub;
        });

        res.json({
            success: true,
            memories: items,
            page,
            limit,
            total,
            hasMore: start + limit < total
        });

    } catch (e) {
        res.status(500).json({ success: false, error: e.message });
    }
});

// ═══════════════════════════════════════════════════════════════════════════════
// PUBLIC API: LIKE MEMORY (Legacy)
// ═══════════════════════════════════════════════════════════════════════════════
app.post('/api/like/:id', (req, res) => {
    try {
        const id = parseInt(req.params.id);
        const data = db('memories');
        const memory = data.memories.find(m => m.id === id && m.approved === 1 && !m.deletedAt && !m.purgedAt);

        if (!memory) {
            return res.status(404).json({ success: false, error: 'Memory not found' });
        }

        memory.likes = (memory.likes || 0) + 1;
        memory.updated_at = nowISO();
        saveDb('memories', data);

        // Also add as reaction
        const reactions = db('reactions');
        reactions.reactions.push({ memoryId: id, type: 'like', createdAt: nowISO() });
        saveDb('reactions', reactions);

        broadcast('reaction:update', { memoryId: id });

        res.json({
            success: true,
            likes: memory.likes,
            reactions: getReactionCounts(id)
        });

    } catch (e) {
        res.status(500).json({ success: false, error: e.message });
    }
});

// ═══════════════════════════════════════════════════════════════════════════════
// PUBLIC API: REACTIONS
// ═══════════════════════════════════════════════════════════════════════════════
app.post('/api/reactions/:memoryId', (req, res) => {
    try {
        const memoryId = parseInt(req.params.memoryId);
        const { type } = req.body || {};

        if (!REACTION_TYPES.includes(type)) {
            return res.status(400).json({ success: false, error: 'Invalid reaction type' });
        }

        const memData = db('memories');
        const memory = memData.memories.find(m =>
            m.id === memoryId && m.approved === 1 && !m.deletedAt && !m.purgedAt
        );

        if (!memory) {
            return res.status(404).json({ success: false, error: 'Memory not found' });
        }

        const reactions = db('reactions');
        reactions.reactions.push({ memoryId, type, createdAt: nowISO() });
        saveDb('reactions', reactions);

        broadcast('reaction:update', { memoryId });

        res.json({ success: true, reactions: getReactionCounts(memoryId) });

    } catch (e) {
        res.status(500).json({ success: false, error: e.message });
    }
});

// ═══════════════════════════════════════════════════════════════════════════════
// PUBLIC API: COMMENTS
// ═══════════════════════════════════════════════════════════════════════════════
app.get('/api/comments/:memoryId', (req, res) => {
    try {
        const settings = getSettings();
        const memoryId = parseInt(req.params.memoryId);

        if (!settings.commentsEnabled) {
            return res.json({ success: true, comments: [], disabled: true });
        }

        const memData = db('memories');
        const memory = memData.memories.find(m =>
            m.id === memoryId && m.approved === 1 && !m.deletedAt && !m.purgedAt
        );

        if (!memory) {
            return res.status(404).json({ success: false, error: 'Memory not found' });
        }

        res.json({
            success: true,
            comments: getCommentTree(memoryId),
            disabled: false
        });

    } catch (e) {
        res.status(500).json({ success: false, error: e.message });
    }
});

app.post('/api/comments/:memoryId', (req, res) => {
    try {
        const settings = getSettings();

        if (!settings.commentsEnabled) {
            return res.status(403).json({ success: false, error: 'Comments are disabled.' });
        }

        const memoryId = parseInt(req.params.memoryId);
        const { name, text, parentId } = req.body || {};

        if (!name || !name.trim()) {
            return res.status(400).json({ success: false, error: 'Name is required' });
        }

        if (!text || !text.trim()) {
            return res.status(400).json({ success: false, error: 'Comment text is required' });
        }

        if (settings.profanityFilterEnabled) {
            if (containsProfanity(name) || containsProfanity(text)) {
                return res.status(400).json({ success: false, error: 'Comment rejected by profanity filter.' });
            }
        }

        const memData = db('memories');
        const memory = memData.memories.find(m =>
            m.id === memoryId && m.approved === 1 && !m.deletedAt && !m.purgedAt
        );

        if (!memory) {
            return res.status(404).json({ success: false, error: 'Memory not found' });
        }

        const comments = db('comments');

        // Validate parent
        if (parentId) {
            const parent = comments.comments.find(c =>
                c.id === Number(parentId) && c.memoryId === memoryId && !c.deletedAt
            );
            if (!parent) {
                return res.status(400).json({ success: false, error: 'Invalid parentId' });
            }
        }

        const comment = {
            id: comments.nextId++,
            memoryId,
            parentId: parentId ? Number(parentId) : null,
            name: name.trim().substring(0, 60),
            text: text.trim().substring(0, 800),
            createdAt: nowISO(),
            deletedAt: null
        };

        comments.comments.push(comment);
        saveDb('comments', comments);

        broadcast('comment:new', { memoryId });

        res.json({ success: true, comment });

    } catch (e) {
        res.status(500).json({ success: false, error: e.message });
    }
});

// ═══════════════════════════════════════════════════════════════════════════════
// PUBLIC API: STATS
// ═══════════════════════════════════════════════════════════════════════════════
app.get('/api/stats', (req, res) => {
    try {
        const data = db('memories');
        const approved = data.memories.filter(m =>
            m.approved === 1 && !m.deletedAt && !m.purgedAt
        );
        const totalLikes = approved.reduce((sum, m) => sum + (m.likes || 0), 0);

        res.json({
            success: true,
            stats: {
                totalMemories: approved.length,
                totalLikes
            }
        });

    } catch (e) {
        res.status(500).json({ success: false, error: e.message });
    }
});

// ═══════════════════════════════════════════════════════════════════════════════
// END OF PART 1
// Continue with Part 2 for Admin APIs
// ═══════════════════════════════════════════════════════════════════════════════

// ═══════════════════════════════════════════════════════════════════════════════
// PART 2: ADMIN AUTHENTICATION & CORE ADMIN APIS
// ═══════════════════════════════════════════════════════════════════════════════

// ═══════════════════════════════════════════════════════════════════════════════
// ADMIN API: LOGIN
// ═══════════════════════════════════════════════════════════════════════════════
app.post('/api/admin/login', (req, res) => {
    try {
        const { userId, password } = req.body || {};
        const uid = String(userId || 'super').trim();
        const pwd = String(password || '').trim();

        const admins = db('admin');
        const user = admins.users.find(u => u.id === uid);

        if (!user || user.disabled) {
            return res.status(401).json({ success: false, error: 'Invalid credentials' });
        }

        if (pwd !== user.password) {
            return res.status(401).json({ success: false, error: 'Invalid credentials' });
        }

        const token = generateToken();
        const expiresAt = new Date(Date.now() + TOKEN_TTL_MS).toISOString();

        const sessions = db('sessions');
        sessions.sessions.push({
            token,
            userId: user.id,
            expiresAt,
            createdAt: nowISO(),
            ip: req.headers['x-forwarded-for']?.split(',')[0]?.trim() || req.socket?.remoteAddress || 'unknown',
            ua: req.headers['user-agent'] || ''
        });
        saveDb('sessions', sessions);

        audit(user.id, 'login', {});

        res.json({
            success: true,
            token,
            expiresAt,
            user: {
                id: user.id,
                name: user.name,
                role: user.role,
                permissions: user.permissions
            }
        });

    } catch (e) {
        res.status(500).json({ success: false, error: e.message });
    }
});

// ═══════════════════════════════════════════════════════════════════════════════
// ADMIN API: VERIFY TOKEN
// ═══════════════════════════════════════════════════════════════════════════════
app.post('/api/admin/verify', (req, res) => {
    try {
        const token = extractToken(req);
        const session = getSession(token);

        if (!session) {
            return res.json({ success: true, valid: false });
        }

        const admins = db('admin');
        const user = admins.users.find(u => u.id === session.userId && !u.disabled);

        if (!user) {
            return res.json({ success: true, valid: false });
        }

        res.json({
            success: true,
            valid: true,
            user: {
                id: user.id,
                name: user.name,
                role: user.role,
                permissions: user.permissions
            }
        });

    } catch (e) {
        res.json({ success: true, valid: false });
    }
});

// ═══════════════════════════════════════════════════════════════════════════════
// ADMIN API: LOGOUT
// ═══════════════════════════════════════════════════════════════════════════════
app.post('/api/admin/logout', (req, res) => {
    try {
        const token = extractToken(req);
        if (token) {
            const sessions = db('sessions');
            sessions.sessions = sessions.sessions.filter(s => s.token !== token);
            saveDb('sessions', sessions);
        }
        res.json({ success: true, message: 'Logged out' });
    } catch (e) {
        res.status(500).json({ success: false, error: e.message });
    }
});

// ═══════════════════════════════════════════════════════════════════════════════
// ADMIN API: GET MEMORIES (with filters, pagination, stats)
// ═══════════════════════════════════════════════════════════════════════════════
app.get('/api/admin/memories', (req, res) => {
    try {
        const auth = requireAdmin(req, res);
        if (!auth) return;

        if (!hasPerm(auth.user, 'moderation')) {
            return res.status(403).json({ success: false, error: 'Forbidden' });
        }

        const { filter, sort, search, includeDeleted } = req.query;
        const page = Math.max(1, parseInt(req.query.page) || 1);
        const limit = Math.min(100, Math.max(1, parseInt(req.query.limit) || 30));

        const data = db('memories');
        let memories = [...data.memories].filter(m => !m.purgedAt);

        // Include deleted filter
        if (includeDeleted !== 'true') {
            memories = memories.filter(m => !m.deletedAt);
        }

        // Status filters
        if (filter === 'approved') {
            memories = memories.filter(m => m.approved === 1 && !m.deletedAt);
        } else if (filter === 'pending') {
            memories = memories.filter(m => m.approved === 0 && !m.deletedAt);
        } else if (filter === 'featured') {
            memories = memories.filter(m => m.featured === 1 && !m.deletedAt);
        } else if (filter === 'trash') {
            memories = memories.filter(m => !!m.deletedAt);
        }

        // Search
        if (search) {
            const s = search.toLowerCase();
            memories = memories.filter(m =>
                (m.student_name || '').toLowerCase().includes(s) ||
                (m.caption || '').toLowerCase().includes(s) ||
                (m.memory_type || '').toLowerCase().includes(s)
            );
        }

        // Sorting
        if (sort === 'oldest') {
            memories.sort((a, b) => new Date(a.created_at) - new Date(b.created_at));
        } else if (sort === 'likes') {
            memories.sort((a, b) => (b.likes || 0) - (a.likes || 0));
        } else {
            memories.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
        }

        // Calculate stats from all non-purged memories
        const allMemories = data.memories.filter(m => !m.purgedAt);
        const stats = {
            total: allMemories.filter(m => !m.deletedAt).length,
            approved: allMemories.filter(m => m.approved === 1 && !m.deletedAt).length,
            pending: allMemories.filter(m => m.approved === 0 && !m.deletedAt).length,
            trash: allMemories.filter(m => !!m.deletedAt).length,
            totalSize: allMemories.filter(m => !m.deletedAt).reduce((sum, m) => sum + (m.file_size || 0), 0),
            totalSizeFormatted: formatFileSize(
                allMemories.filter(m => !m.deletedAt).reduce((sum, m) => sum + (m.file_size || 0), 0)
            )
        };

        // Pagination
        const total = memories.length;
        const start = (page - 1) * limit;
        const items = memories.slice(start, start + limit).map(m => {
            const pub = memoryToPublic(m);
            pub.reactions = getReactionCounts(m.id);
            const commentsData = db('comments');
            pub.commentCount = commentsData.comments.filter(c => c.memoryId === m.id && !c.deletedAt).length;
            return pub;
        });

        res.json({
            success: true,
            memories: items,
            stats,
            page,
            limit,
            total,
            hasMore: start + limit < total
        });

    } catch (e) {
        res.status(500).json({ success: false, error: e.message });
    }
});

// ═══════════════════════════════════════════════════════════════════════════════
// ADMIN API: APPROVE MEMORY
// ═══════════════════════════════════════════════════════════════════════════════
app.post('/api/admin/approve/:id', (req, res) => {
    try {
        const auth = requireAdmin(req, res);
        if (!auth) return;

        if (!hasPerm(auth.user, 'moderation')) {
            return res.status(403).json({ success: false, error: 'Forbidden' });
        }

        const id = parseInt(req.params.id);
        const data = db('memories');
        const memory = data.memories.find(m => m.id === id && !m.purgedAt);

        if (!memory) {
            return res.status(404).json({ success: false, error: 'Memory not found' });
        }

        memory.approved = 1;
        memory.updated_at = nowISO();
        saveDb('memories', data);

        audit(auth.user.id, 'approve', { memoryId: id });
        broadcast('memory:update', { memoryId: id });

        res.json({ success: true, message: 'Memory approved' });

    } catch (e) {
        res.status(500).json({ success: false, error: e.message });
    }
});

// ═══════════════════════════════════════════════════════════════════════════════
// ADMIN API: APPROVE ALL PENDING
// ═══════════════════════════════════════════════════════════════════════════════
app.post('/api/admin/approve-all', (req, res) => {
    try {
        const auth = requireAdmin(req, res);
        if (!auth) return;

        if (!hasPerm(auth.user, 'bulk')) {
            return res.status(403).json({ success: false, error: 'Forbidden' });
        }

        const data = db('memories');
        let count = 0;

        data.memories.forEach(m => {
            if (m.approved === 0 && !m.deletedAt && !m.purgedAt) {
                m.approved = 1;
                m.updated_at = nowISO();
                count++;
            }
        });

        saveDb('memories', data);
        audit(auth.user.id, 'approve-all', { count });
        broadcast('memory:bulk', { type: 'approve', count });

        res.json({ success: true, message: `Approved ${count} memories`, count });

    } catch (e) {
        res.status(500).json({ success: false, error: e.message });
    }
});

// ═══════════════════════════════════════════════════════════════════════════════
// ADMIN API: SOFT DELETE (TRASH)
// ═══════════════════════════════════════════════════════════════════════════════
app.delete('/api/admin/delete/:id', (req, res) => {
    try {
        const auth = requireAdmin(req, res);
        if (!auth) return;

        if (!hasPerm(auth.user, 'trash')) {
            return res.status(403).json({ success: false, error: 'Forbidden' });
        }

        const id = parseInt(req.params.id);
        const data = db('memories');
        const memory = data.memories.find(m => m.id === id && !m.purgedAt);

        if (!memory) {
            return res.status(404).json({ success: false, error: 'Memory not found' });
        }

        memory.deletedAt = nowISO();
        memory.updated_at = nowISO();
        saveDb('memories', data);

        audit(auth.user.id, 'trash', { memoryId: id });
        broadcast('memory:update', { memoryId: id });

        res.json({ success: true, message: 'Memory moved to trash' });

    } catch (e) {
        res.status(500).json({ success: false, error: e.message });
    }
});

// ═══════════════════════════════════════════════════════════════════════════════
// ADMIN API: RESTORE FROM TRASH
// ═══════════════════════════════════════════════════════════════════════════════
app.post('/api/admin/restore/:id', (req, res) => {
    try {
        const auth = requireAdmin(req, res);
        if (!auth) return;

        if (!hasPerm(auth.user, 'trash')) {
            return res.status(403).json({ success: false, error: 'Forbidden' });
        }

        const id = parseInt(req.params.id);
        const data = db('memories');
        const memory = data.memories.find(m => m.id === id && !m.purgedAt);

        if (!memory) {
            return res.status(404).json({ success: false, error: 'Memory not found' });
        }

        memory.deletedAt = null;
        memory.updated_at = nowISO();
        saveDb('memories', data);

        audit(auth.user.id, 'restore', { memoryId: id });
        broadcast('memory:update', { memoryId: id });

        res.json({ success: true, message: 'Memory restored' });

    } catch (e) {
        res.status(500).json({ success: false, error: e.message });
    }
});

// ═══════════════════════════════════════════════════════════════════════════════
// ADMIN API: PURGE (HARD DELETE)
// ═══════════════════════════════════════════════════════════════════════════════
app.delete('/api/admin/purge/:id', (req, res) => {
    try {
        const auth = requireAdmin(req, res);
        if (!auth) return;

        if (auth.user.role !== 'superadmin') {
            return res.status(403).json({ success: false, error: 'Super admin only' });
        }

        const id = parseInt(req.params.id);
        const data = db('memories');
        const memory = data.memories.find(m => m.id === id && !m.purgedAt);

        if (!memory) {
            return res.status(404).json({ success: false, error: 'Memory not found' });
        }

        // Delete file from disk
        const filePath = path.join(uploadsDir, memory.file_path);
        if (fs.existsSync(filePath)) {
            try { fs.unlinkSync(filePath); } catch (e) { }
        }

        memory.purgedAt = nowISO();
        memory.updated_at = nowISO();
        saveDb('memories', data);

        audit(auth.user.id, 'purge', { memoryId: id });
        broadcast('memory:update', { memoryId: id });

        res.json({ success: true, message: 'Memory permanently deleted' });

    } catch (e) {
        res.status(500).json({ success: false, error: e.message });
    }
});

// ═══════════════════════════════════════════════════════════════════════════════
// ADMIN API: BULK ACTIONS
// ═══════════════════════════════════════════════════════════════════════════════
app.post('/api/admin/bulk', (req, res) => {
    try {
        const auth = requireAdmin(req, res);
        if (!auth) return;

        if (!hasPerm(auth.user, 'bulk')) {
            return res.status(403).json({ success: false, error: 'Forbidden' });
        }

        const { action, ids, memoryType } = req.body || {};

        if (!Array.isArray(ids) || ids.length === 0) {
            return res.status(400).json({ success: false, error: 'ids array required' });
        }

        const data = db('memories');
        const idSet = new Set(ids.map(Number));
        let changed = 0;

        data.memories.forEach(m => {
            if (!idSet.has(m.id) || m.purgedAt) return;

            switch (action) {
                case 'approve':
                    if (!m.deletedAt && m.approved === 0) {
                        m.approved = 1;
                        m.updated_at = nowISO();
                        changed++;
                    }
                    break;
                case 'trash':
                    if (!m.deletedAt) {
                        m.deletedAt = nowISO();
                        m.updated_at = nowISO();
                        changed++;
                    }
                    break;
                case 'restore':
                    if (m.deletedAt) {
                        m.deletedAt = null;
                        m.updated_at = nowISO();
                        changed++;
                    }
                    break;
                case 'setType':
                    if (memoryType && typeof memoryType === 'string') {
                        m.memory_type = memoryType.trim();
                        m.updated_at = nowISO();
                        changed++;
                    }
                    break;
                case 'feature':
                    m.featured = 1;
                    m.updated_at = nowISO();
                    changed++;
                    break;
                case 'unfeature':
                    m.featured = 0;
                    m.updated_at = nowISO();
                    changed++;
                    break;
            }
        });

        saveDb('memories', data);
        audit(auth.user.id, 'bulk', { action, changed });
        broadcast('memory:bulk', { type: action, changed });

        res.json({ success: true, changed });

    } catch (e) {
        res.status(500).json({ success: false, error: e.message });
    }
});

// ═══════════════════════════════════════════════════════════════════════════════
// ADMIN API: EDIT MEMORY METADATA
// ═══════════════════════════════════════════════════════════════════════════════
app.post('/api/admin/memory/edit/:id', (req, res) => {
    try {
        const auth = requireAdmin(req, res);
        if (!auth) return;

        if (!hasPerm(auth.user, 'editMemory')) {
            return res.status(403).json({ success: false, error: 'Forbidden' });
        }

        const id = parseInt(req.params.id);
        const { caption, memory_type, student_name, featured } = req.body || {};

        const data = db('memories');
        const memory = data.memories.find(m => m.id === id && !m.purgedAt);

        if (!memory) {
            return res.status(404).json({ success: false, error: 'Memory not found' });
        }

        if (typeof caption === 'string') memory.caption = caption.trim().substring(0, 1000);
        if (typeof memory_type === 'string') memory.memory_type = memory_type.trim();
        if (typeof student_name === 'string') memory.student_name = student_name.trim().substring(0, 100);
        if (typeof featured === 'number' || typeof featured === 'boolean') {
            memory.featured = featured ? 1 : 0;
        }

        memory.updated_at = nowISO();
        saveDb('memories', data);

        audit(auth.user.id, 'edit-memory', { memoryId: id });
        broadcast('memory:update', { memoryId: id });

        res.json({ success: true, memory: memoryToPublic(memory) });

    } catch (e) {
        res.status(500).json({ success: false, error: e.message });
    }
});

// ═══════════════════════════════════════════════════════════════════════════════
// ADMIN API: REPLACE FILE
// ═══════════════════════════════════════════════════════════════════════════════
app.post('/api/admin/memory/replace-file/:id', upload.single('file'), (req, res) => {
    try {
        const auth = requireAdmin(req, res);
        if (!auth) return;

        if (!hasPerm(auth.user, 'replaceFile')) {
            return res.status(403).json({ success: false, error: 'Forbidden' });
        }

        const id = parseInt(req.params.id);
        const file = req.file;

        if (!file) {
            return res.status(400).json({ success: false, error: 'File required' });
        }

        const data = db('memories');
        const memory = data.memories.find(m => m.id === id && !m.purgedAt);

        if (!memory) {
            fs.unlinkSync(path.join(uploadsDir, file.filename));
            return res.status(404).json({ success: false, error: 'Memory not found' });
        }

        const newPath = path.join(uploadsDir, file.filename);
        const hash = sha256File(newPath);

        // Check for duplicates
        const existing = data.memories.find(m => m.sha256 === hash && m.id !== id && !m.purgedAt);
        if (existing) {
            fs.unlinkSync(newPath);
            return res.status(409).json({ success: false, error: `Duplicate of memory #${existing.id}` });
        }

        // Delete old file
        const oldPath = path.join(uploadsDir, memory.file_path);
        if (fs.existsSync(oldPath)) {
            try { fs.unlinkSync(oldPath); } catch (e) { }
        }

        memory.file_path = file.filename;
        memory.file_name = file.originalname;
        memory.file_type = getFileType(file.mimetype);
        memory.file_size = file.size;
        memory.sha256 = hash;
        memory.updated_at = nowISO();

        saveDb('memories', data);
        audit(auth.user.id, 'replace-file', { memoryId: id });
        broadcast('memory:update', { memoryId: id });

        res.json({ success: true, memory: memoryToPublic(memory) });

    } catch (e) {
        res.status(500).json({ success: false, error: e.message });
    }
});

// ═══════════════════════════════════════════════════════════════════════════════
// ADMIN API: SAVE SETTINGS
// ═══════════════════════════════════════════════════════════════════════════════
app.post('/api/admin/settings', (req, res) => {
    try {
        const auth = requireAdmin(req, res);
        if (!auth) return;

        if (!hasPerm(auth.user, 'settings')) {
            return res.status(403).json({ success: false, error: 'Forbidden' });
        }

        const incoming = req.body?.settings;
        if (!incoming || typeof incoming !== 'object') {
            return res.status(400).json({ success: false, error: 'Missing settings object' });
        }

        // Validate theme permission
        if (incoming.theme && !hasPerm(auth.user, 'theme')) {
            return res.status(403).json({ success: false, error: 'No permission to edit theme' });
        }

        saveDb('settings', { settings: incoming });
        audit(auth.user.id, 'save-settings', {});
        broadcast('settings:update', {});

        res.json({ success: true });

    } catch (e) {
        res.status(500).json({ success: false, error: e.message });
    }
});

// ═══════════════════════════════════════════════════════════════════════════════
// ADMIN API: UPLOAD INTRO VIDEO
// ═══════════════════════════════════════════════════════════════════════════════
app.post('/api/admin/upload-intro-video', upload.single('video'), (req, res) => {
    try {
        const auth = requireAdmin(req, res);
        if (!auth) return;

        if (!hasPerm(auth.user, 'settings')) {
            return res.status(403).json({ success: false, error: 'Forbidden' });
        }

        const file = req.file;
        if (!file) {
            return res.status(400).json({ success: false, error: 'No video file provided' });
        }

        const data = db('settings');
        data.settings = data.settings || {};

        // Remove old intro video
        if (data.settings.introVideoPath) {
            const oldFile = path.join(uploadsDir, path.basename(data.settings.introVideoPath));
            if (fs.existsSync(oldFile)) {
                try { fs.unlinkSync(oldFile); } catch (e) { }
            }
        }

        data.settings.introVideoPath = file.filename;
        saveDb('settings', data);

        audit(auth.user.id, 'upload-intro-video', {});
        broadcast('settings:update', {});

        res.json({
            success: true,
            introVideoPath: file.filename,
            introVideoUrl: `/uploads/${file.filename}`
        });

    } catch (e) {
        res.status(500).json({ success: false, error: e.message });
    }
});

// ═══════════════════════════════════════════════════════════════════════════════
// ADMIN API: UPLOAD MUSIC
// ═══════════════════════════════════════════════════════════════════════════════
app.post('/api/admin/upload-music', uploadMusic.single('music'), (req, res) => {
    try {
        const auth = requireAdmin(req, res);
        if (!auth) return;

        if (!req.file) {
            return res.status(400).json({ success: false, error: 'No file uploaded' });
        }

        res.json({ success: true, path: `/music/${req.file.filename}` });

    } catch (e) {
        res.status(500).json({ success: false, error: e.message });
    }
});

// ═══════════════════════════════════════════════════════════════════════════════
// ADMIN API: GET MUSIC FILES
// ═══════════════════════════════════════════════════════════════════════════════
app.get('/api/admin/music-files', (req, res) => {
    try {
        const auth = requireAdmin(req, res);
        if (!auth) return;

        const files = fs.readdirSync(musicDir).map(f => ({
            name: f,
            path: `/music/${f}`
        }));

        res.json({ success: true, files });

    } catch (e) {
        res.status(500).json({ success: false, error: e.message });
    }
});

// ═══════════════════════════════════════════════════════════════════════════════
// ADMIN API: USER MANAGEMENT
// ═══════════════════════════════════════════════════════════════════════════════
app.get('/api/admin/users', (req, res) => {
    try {
        const auth = requireAdmin(req, res);
        if (!auth) return;

        if (!hasPerm(auth.user, 'users')) {
            return res.status(403).json({ success: false, error: 'Forbidden' });
        }

        const admins = db('admin');

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

    } catch (e) {
        res.status(500).json({ success: false, error: e.message });
    }
});

app.post('/api/admin/users', (req, res) => {
    try {
        const auth = requireAdmin(req, res);
        if (!auth) return;

        if (!hasPerm(auth.user, 'users')) {
            return res.status(403).json({ success: false, error: 'Forbidden' });
        }

        const { id, name, password, role, permissions } = req.body || {};
        const uid = String(id || '').trim();

        if (!uid || uid.length < 3) {
            return res.status(400).json({ success: false, error: 'ID must be at least 3 characters' });
        }

        if (!/^[a-zA-Z0-9_-]+$/.test(uid)) {
            return res.status(400).json({ success: false, error: 'ID must be alphanumeric with _ or -' });
        }

        if (!password || password.length < 8) {
            return res.status(400).json({ success: false, error: 'Password must be at least 8 characters' });
        }

        const admins = db('admin');

        if (admins.users.find(u => u.id === uid)) {
            return res.status(409).json({ success: false, error: 'User already exists' });
        }

        const now = nowISO();
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

        saveDb('admin', admins);
        audit(auth.user.id, 'create-user', { id: uid });

        res.json({ success: true });

    } catch (e) {
        res.status(500).json({ success: false, error: e.message });
    }
});

app.post('/api/admin/users/:id', (req, res) => {
    try {
        const auth = requireAdmin(req, res);
        if (!auth) return;

        if (!hasPerm(auth.user, 'users')) {
            return res.status(403).json({ success: false, error: 'Forbidden' });
        }

        const uid = req.params.id;

        if (uid === 'super' && auth.user.id !== 'super') {
            return res.status(403).json({ success: false, error: 'Cannot modify super admin' });
        }

        const { name, password, disabled, permissions } = req.body || {};
        const admins = db('admin');
        const user = admins.users.find(u => u.id === uid);

        if (!user) {
            return res.status(404).json({ success: false, error: 'User not found' });
        }

        if (typeof name === 'string') user.name = name.trim().substring(0, 60);
        if (typeof password === 'string' && password.length >= 8) user.password = password;
        if (typeof disabled === 'boolean') user.disabled = disabled;
        if (permissions && typeof permissions === 'object') user.permissions = permissions;

        user.updatedAt = nowISO();
        saveDb('admin', admins);

        // Invalidate user sessions
        const sessions = db('sessions');
        sessions.sessions = sessions.sessions.filter(s => s.userId !== uid);
        saveDb('sessions', sessions);

        audit(auth.user.id, 'update-user', { id: uid });

        res.json({ success: true });

    } catch (e) {
        res.status(500).json({ success: false, error: e.message });
    }
});

// PATCH for changing own password
app.patch('/api/admin/users/:id', (req, res) => {
    try {
        const auth = requireAdmin(req, res);
        if (!auth) return;

        const uid = req.params.id;
        const { oldPassword, password } = req.body || {};

        // Can only change own password via PATCH
        if (uid !== auth.user.id) {
            return res.status(403).json({ success: false, error: 'Can only change your own password' });
        }

        if (!oldPassword || !password) {
            return res.status(400).json({ success: false, error: 'oldPassword and password required' });
        }

        if (password.length < 8) {
            return res.status(400).json({ success: false, error: 'Password must be at least 8 characters' });
        }

        const admins = db('admin');
        const user = admins.users.find(u => u.id === uid);

        if (!user) {
            return res.status(404).json({ success: false, error: 'User not found' });
        }

        if (user.password !== oldPassword) {
            return res.status(400).json({ success: false, error: 'Old password incorrect' });
        }

        user.password = password;
        user.updatedAt = nowISO();
        saveDb('admin', admins);

        // Invalidate all sessions for this user
        const sessions = db('sessions');
        sessions.sessions = sessions.sessions.filter(s => s.userId !== uid);
        saveDb('sessions', sessions);

        audit(auth.user.id, 'change-password', {});

        res.json({ success: true });

    } catch (e) {
        res.status(500).json({ success: false, error: e.message });
    }
});

// ═══════════════════════════════════════════════════════════════════════════════
// ADMIN API: SESSIONS MANAGEMENT
// ═══════════════════════════════════════════════════════════════════════════════
app.get('/api/admin/sessions', (req, res) => {
    try {
        const auth = requireAdmin(req, res);
        if (!auth) return;

        if (!hasPerm(auth.user, 'users')) {
            return res.status(403).json({ success: false, error: 'Forbidden' });
        }

        cleanExpiredSessions();
        const sessions = db('sessions');

        res.json({
            success: true,
            sessions: sessions.sessions.map(s => ({
                oderId: s.userId,
                createdAt: s.createdAt,
                expiresAt: s.expiresAt,
                ip: s.ip,
                ua: s.ua
            }))
        });

    } catch (e) {
        res.status(500).json({ success: false, error: e.message });
    }
});

app.delete('/api/admin/sessions', (req, res) => {
    try {
        const auth = requireAdmin(req, res);
        if (!auth) return;

        if (auth.user.role !== 'superadmin') {
            return res.status(403).json({ success: false, error: 'Super admin only' });
        }

        // Keep current session, remove all others
        const sessions = db('sessions');
        sessions.sessions = sessions.sessions.filter(s => s.token === auth.token);
        saveDb('sessions', sessions);

        audit(auth.user.id, 'force-logout-all', {});

        res.json({ success: true, message: 'All other sessions terminated' });

    } catch (e) {
        res.status(500).json({ success: false, error: e.message });
    }
});

app.delete('/api/admin/sessions/:id', (req, res) => {
    try {
        const auth = requireAdmin(req, res);
        if (!auth) return;

        if (!hasPerm(auth.user, 'users')) {
            return res.status(403).json({ success: false, error: 'Forbidden' });
        }

        const targetUserId = req.params.id;
        const sessions = db('sessions');
        const before = sessions.sessions.length;
        sessions.sessions = sessions.sessions.filter(s => s.userId !== targetUserId);
        saveDb('sessions', sessions);

        res.json({ success: true, terminated: before - sessions.sessions.length });

    } catch (e) {
        res.status(500).json({ success: false, error: e.message });
    }
});

// ═══════════════════════════════════════════════════════════════════════════════
// ADMIN API: AUDIT LOG
// ═══════════════════════════════════════════════════════════════════════════════
app.get('/api/admin/audit-log', (req, res) => {
    try {
        const auth = requireAdmin(req, res);
        if (!auth) return;

        if (auth.user.role !== 'superadmin') {
            return res.status(403).json({ success: false, error: 'Super admin only' });
        }

        const data = db('audit');
        const events = [...data.events].reverse().slice(0, 500);

        res.json({ success: true, events });

    } catch (e) {
        res.status(500).json({ success: false, error: e.message });
    }
});

// ═══════════════════════════════════════════════════════════════════════════════
// ADMIN API: BANS
// ═══════════════════════════════════════════════════════════════════════════════
app.get('/api/admin/bans', (req, res) => {
    try {
        const auth = requireAdmin(req, res);
        if (!auth) return;

        const data = db('bans');
        res.json({ success: true, bans: data.bans || [] });

    } catch (e) {
        res.status(500).json({ success: false, error: e.message });
    }
});

app.post('/api/admin/bans', (req, res) => {
    try {
        const auth = requireAdmin(req, res);
        if (!auth) return;

        const { value, reason } = req.body || {};

        if (!value || !value.trim()) {
            return res.status(400).json({ success: false, error: 'Ban value required' });
        }

        const data = db('bans');
        data.bans = data.bans || [];

        data.bans.push({
            id: data.nextId++,
            value: value.trim(),
            reason: (reason || '').trim(),
            createdAt: nowISO(),
            createdBy: auth.user.id
        });

        saveDb('bans', data);
        audit(auth.user.id, 'add-ban', { value });

        res.json({ success: true });

    } catch (e) {
        res.status(500).json({ success: false, error: e.message });
    }
});

app.delete('/api/admin/bans/:id', (req, res) => {
    try {
        const auth = requireAdmin(req, res);
        if (!auth) return;

        const id = parseInt(req.params.id);
        const data = db('bans');
        data.bans = (data.bans || []).filter(b => b.id !== id);
        saveDb('bans', data);

        audit(auth.user.id, 'remove-ban', { id });

        res.json({ success: true });

    } catch (e) {
        res.status(500).json({ success: false, error: e.message });
    }
});

// ═══════════════════════════════════════════════════════════════════════════════
// ADMIN API: MAINTENANCE MODE
// ═══════════════════════════════════════════════════════════════════════════════
app.post('/api/admin/maintenance', (req, res) => {
    try {
        const auth = requireAdmin(req, res);
        if (!auth) return;

        if (auth.user.role !== 'superadmin') {
            return res.status(403).json({ success: false, error: 'Super admin only' });
        }

        const { enabled } = req.body || {};
        const data = db('settings');
        data.settings = data.settings || {};
        data.settings.maintenanceMode = !!enabled;
        saveDb('settings', data);

        audit(auth.user.id, 'maintenance-toggle', { enabled: !!enabled });
        broadcast('settings:update', {});

        res.json({ success: true, maintenanceMode: !!enabled });

    } catch (e) {
        res.status(500).json({ success: false, error: e.message });
    }
});

// ═══════════════════════════════════════════════════════════════════════════════
// ADMIN API: RESET HASHES
// ═══════════════════════════════════════════════════════════════════════════════
app.post('/api/admin/reset-hashes', (req, res) => {
    try {
        const auth = requireAdmin(req, res);
        if (!auth) return;

        if (auth.user.role !== 'superadmin') {
            return res.status(403).json({ success: false, error: 'Super admin only' });
        }

        const data = db('memories');
        let updated = 0;

        data.memories.forEach(m => {
            if (m.purgedAt) return;
            const fp = path.join(uploadsDir, m.file_path);
            if (fs.existsSync(fp)) {
                m.sha256 = sha256File(fp);
                m.updated_at = nowISO();
                updated++;
            }
        });

        saveDb('memories', data);
        audit(auth.user.id, 'reset-hashes', { updated });

        res.json({ success: true, updated });

    } catch (e) {
        res.status(500).json({ success: false, error: e.message });
    }
});

// ═══════════════════════════════════════════════════════════════════════════════
// ADMIN API: WIPE ALL MEMORIES
// ═══════════════════════════════════════════════════════════════════════════════
app.delete('/api/admin/wipe-memories', (req, res) => {
    try {
        const auth = requireAdmin(req, res);
        if (!auth) return;

        if (auth.user.role !== 'superadmin') {
            return res.status(403).json({ success: false, error: 'Super admin only' });
        }

        const data = db('memories');
        const count = data.memories.length;

        // Delete all files
        data.memories.forEach(m => {
            if (m.file_path) {
                const fp = path.join(uploadsDir, m.file_path);
                if (fs.existsSync(fp)) {
                    try { fs.unlinkSync(fp); } catch (e) { }
                }
            }
        });

        // Reset database
        saveDb('memories', { memories: [], nextId: 1 });
        saveDb('comments', { comments: [], nextId: 1 });
        saveDb('reactions', { reactions: [] });

        audit(auth.user.id, 'wipe-memories', { count });

        res.json({ success: true, deleted: count });

    } catch (e) {
        res.status(500).json({ success: false, error: e.message });
    }
});

// ═══════════════════════════════════════════════════════════════════════════════
// ADMIN API: EXPORTS
// ═══════════════════════════════════════════════════════════════════════════════
app.get('/api/admin/export/csv', (req, res) => {
    try {
        const auth = requireAdmin(req, res);
        if (!auth) return;

        if (!hasPerm(auth.user, 'export')) {
            return res.status(403).json({ success: false, error: 'Forbidden' });
        }

        const data = db('memories');
        const rows = data.memories.filter(m => !m.purgedAt);

        if (rows.length === 0) {
            res.setHeader('Content-Type', 'text/csv');
            res.setHeader('Content-Disposition', 'attachment; filename="memories-export.csv"');
            return res.send('No data\n');
        }

        const headers = ['id', 'student_name', 'caption', 'memory_type', 'approved', 'featured', 'likes', 'file_name', 'file_path', 'file_type', 'file_size', 'created_at', 'deletedAt'];
        const lines = [headers.join(',')];

        rows.forEach(r => {
            lines.push(headers.map(h => `"${sanitizeCSV(r[h] ?? '')}"`).join(','));
        });

        res.setHeader('Content-Type', 'text/csv; charset=utf-8');
        res.setHeader('Content-Disposition', `attachment; filename="memories-export-${new Date().toISOString().slice(0, 10)}.csv"`);
        res.send(lines.join('\n'));

    } catch (e) {
        res.status(500).json({ success: false, error: e.message });
    }
});

app.get('/api/admin/export/json', (req, res) => {
    try {
        const auth = requireAdmin(req, res);
        if (!auth) return;

        if (!hasPerm(auth.user, 'export')) {
            return res.status(403).json({ success: false, error: 'Forbidden' });
        }

        const memories = db('memories');
        const settings = db('settings');
        const comments = db('comments');

        const exportData = {
            exportedAt: nowISO(),
            memories: memories.memories.filter(m => !m.purgedAt),
            settings: settings.settings,
            comments: comments.comments
        };

        res.setHeader('Content-Type', 'application/json');
        res.setHeader('Content-Disposition', `attachment; filename="backup-${new Date().toISOString().slice(0, 10)}.json"`);
        res.send(JSON.stringify(exportData, null, 2));

    } catch (e) {
        res.status(500).json({ success: false, error: e.message });
    }
});

app.get('/api/admin/export/zip', (req, res) => {
    try {
        const auth = requireAdmin(req, res);
        if (!auth) return;

        if (!hasPerm(auth.user, 'export')) {
            return res.status(403).json({ success: false, error: 'Forbidden' });
        }

        const data = db('memories');
        const memories = data.memories.filter(m => m.approved === 1 && !m.deletedAt && !m.purgedAt);

        if (memories.length === 0) {
            return res.status(404).json({ success: false, error: 'No memories to export' });
        }

        const timestamp = new Date().toISOString().split('T')[0];
        res.attachment(`memories-${timestamp}.zip`);
        res.setHeader('Content-Type', 'application/zip');

        const archive = archiver('zip', { zlib: { level: 5 } });
        archive.on('error', err => {
            console.error('Archive error:', err);
            res.status(500).end();
        });

        archive.pipe(res);

        memories.forEach(m => {
            const fp = path.join(uploadsDir, m.file_path);
            if (fs.existsSync(fp)) {
                const safeName = m.student_name.replace(/[^a-zA-Z0-9]/g, '_');
                const ext = path.extname(m.file_path);
                archive.file(fp, { name: `${m.memory_type}/${safeName}-${m.id}${ext}` });
            }
        });

        archive.finalize();

    } catch (e) {
        res.status(500).json({ success: false, error: e.message });
    }
});

app.get('/api/admin/download-all', (req, res) => {
    // Alias for export/zip
    req.query.token = req.query.token || extractToken(req);
    return res.redirect(`/api/admin/export/zip?token=${req.query.token}`);
});

// ═══════════════════════════════════════════════════════════════════════════════
// DESTINATIONS API (Globe)
// ═══════════════════════════════════════════════════════════════════════════════
app.get('/api/destinations', (req, res) => {
    try {
        const data = db('destinations');
        const approved = (data.pins || []).filter(p => p.approved && !p.deletedAt);
        res.json({ success: true, destinations: approved });
    } catch (e) {
        res.status(500).json({ success: false, error: e.message });
    }
});

app.get('/api/destinations/list', (req, res) => {
    try {
        const data = db('destinations');
        const approved = (data.pins || []).filter(p => p.approved && !p.deletedAt);
        res.json({ success: true, destinations: approved, count: approved.length });
    } catch (e) {
        res.status(500).json({ success: false, error: e.message });
    }
});

app.get('/api/destinations/pin-submissions', (req, res) => {
    try {
        const data = db('destinations');
        const pending = (data.pins || []).filter(p => !p.approved && !p.deletedAt);
        res.json({ success: true, submissions: pending });
    } catch (e) {
        res.status(500).json({ success: false, error: e.message });
    }
});

app.get('/api/destinations/submissions', (req, res) => {
    try {
        const data = db('destinations');
        const pending = (data.pins || []).filter(p => !p.approved && !p.deletedAt);
        res.json({ success: true, submissions: pending });
    } catch (e) {
        res.status(500).json({ success: false, error: e.message });
    }
});

// Submit destination (multiple endpoint variations for frontend compatibility)
const submitDestination = (req, res) => {
    try {
        const { name, school, city, country, lat, lng, type, note, emoji } = req.body || {};

        if (!name || !name.trim()) {
            return res.status(400).json({ success: false, error: 'Name is required' });
        }

        const data = db('destinations');
        data.pins = data.pins || [];
        data.nextId = data.nextId || 1;

        const pin = {
            id: data.nextId++,
            name: String(name).trim().substring(0, 80),
            school: String(school || '').trim().substring(0, 120),
            city: String(city || '').trim().substring(0, 80),
            country: String(country || '').trim().substring(0, 80),
            lat: parseFloat(lat) || 0,
            lng: parseFloat(lng) || 0,
            type: String(type || 'university').trim(),
            emoji: String(emoji || '🎓').substring(0, 4),
            note: String(note || '').trim().substring(0, 300),
            approved: false,
            deletedAt: null,
            createdAt: nowISO()
        };

        data.pins.push(pin);
        saveDb('destinations', data);

        broadcast('destination:new', { id: pin.id });

        res.json({ success: true, pin });

    } catch (e) {
        res.status(500).json({ success: false, error: e.message });
    }
};

app.post('/api/destinations/submit', submitDestination);
app.post('/api/destinations/submit-v2', submitDestination);
app.post('/api/destinations/pin-submit', submitDestination);

// Admin destination management
app.post('/api/admin/destinations', (req, res) => {
    try {
        const auth = requireAdmin(req, res);
        if (!auth) return;

        const { action, id, ids } = req.body || {};
        const data = db('destinations');
        const targets = ids ? ids.map(Number) : (id ? [Number(id)] : []);

        let changed = 0;

        (data.pins || []).forEach(p => {
            if (!targets.includes(p.id)) return;

            if (action === 'approve') {
                p.approved = true;
                changed++;
            } else if (action === 'delete') {
                p.deletedAt = nowISO();
                changed++;
            } else if (action === 'restore') {
                p.deletedAt = null;
                changed++;
            }
        });

        saveDb('destinations', data);
        audit(auth.user.id, `destinations-${action}`, { changed });
        broadcast('destinations:update', {});

        res.json({ success: true, changed });

    } catch (e) {
        res.status(500).json({ success: false, error: e.message });
    }
});

app.post('/api/admin/destinations-v2', (req, res) => {
    // Alias
    return app._router.handle(Object.assign(req, { url: '/api/admin/destinations' }), res, () => { });
});

// ═══════════════════════════════════════════════════════════════════════════════
// COMPILATIONS API
// ═══════════════════════════════════════════════════════════════════════════════
function enrichCompilation(comp) {
    const memData = db('memories');
    const memById = new Map(memData.memories.map(m => [m.id, m]));

    const slides = (comp.slides || []).map(s => {
        const mem = memById.get(Number(s.memoryId));
        return {
            memoryId: Number(s.memoryId),
            caption: String(s.caption || ''),
            duration: Math.max(1, Math.min(60, Number(s.duration) || 5)),
            file_url: mem && !mem.purgedAt ? `/uploads/${mem.file_path}` : null
        };
    });

    return { ...comp, slides };
}

app.get('/api/compilations', (req, res) => {
    try {
        const data = db('compilations');
        const comps = (data.compilations || []).map(enrichCompilation);
        res.json({ success: true, compilations: comps });
    } catch (e) {
        res.status(500).json({ success: false, error: e.message });
    }
});

app.get('/api/compilations/:id', (req, res) => {
    try {
        const id = Number(req.params.id);
        const data = db('compilations');
        const comp = (data.compilations || []).find(c => c.id === id);

        if (!comp) {
            return res.status(404).json({ success: false, error: 'Compilation not found' });
        }

        res.json({ success: true, compilation: enrichCompilation(comp) });

    } catch (e) {
        res.status(500).json({ success: false, error: e.message });
    }
});

app.post('/api/admin/compilations', (req, res) => {
    try {
        const auth = requireAdmin(req, res);
        if (!auth) return;

        const { name, slides, displayMode, transitionType } = req.body || {};

        if (!name || !name.trim()) {
            return res.status(400).json({ success: false, error: 'Name required' });
        }

        if (!Array.isArray(slides) || slides.length < 2) {
            return res.status(400).json({ success: false, error: 'At least 2 slides required' });
        }

        const data = db('compilations');
        data.compilations = data.compilations || [];
        data.nextId = data.nextId || 1;

        const comp = {
            id: data.nextId++,
            name: String(name).trim().substring(0, 120),
            slides: slides.map(s => ({
                memoryId: Number(s.memoryId),
                caption: String(s.caption || '').substring(0, 250),
                duration: Math.max(1, Math.min(60, Number(s.duration) || 5))
            })),
            displayMode: displayMode === 'manual' ? 'manual' : 'auto',
            transitionType: String(transitionType || 'fade').substring(0, 20),
            createdAt: nowISO(),
            updatedAt: nowISO()
        };

        data.compilations.push(comp);
        saveDb('compilations', data);

        audit(auth.user.id, 'create-compilation', { id: comp.id });

        res.json({ success: true, compilation: enrichCompilation(comp) });

    } catch (e) {
        res.status(500).json({ success: false, error: e.message });
    }
});

app.post('/api/admin/compilations/:id', (req, res) => {
    try {
        const auth = requireAdmin(req, res);
        if (!auth) return;

        const id = Number(req.params.id);
        const data = db('compilations');
        const comp = (data.compilations || []).find(c => c.id === id);

        if (!comp) {
            return res.status(404).json({ success: false, error: 'Compilation not found' });
        }

        const { name, slides, displayMode, transitionType } = req.body || {};

        if (typeof name === 'string' && name.trim()) {
            comp.name = name.trim().substring(0, 120);
        }

        if (Array.isArray(slides) && slides.length >= 2) {
            comp.slides = slides.map(s => ({
                memoryId: Number(s.memoryId),
                caption: String(s.caption || '').substring(0, 250),
                duration: Math.max(1, Math.min(60, Number(s.duration) || 5))
            }));
        }

        if (displayMode) comp.displayMode = displayMode === 'manual' ? 'manual' : 'auto';
        if (transitionType) comp.transitionType = String(transitionType).substring(0, 20);

        comp.updatedAt = nowISO();
        saveDb('compilations', data);

        audit(auth.user.id, 'update-compilation', { id });

        res.json({ success: true, compilation: enrichCompilation(comp) });

    } catch (e) {
        res.status(500).json({ success: false, error: e.message });
    }
});

app.delete('/api/admin/compilations/:id', (req, res) => {
    try {
        const auth = requireAdmin(req, res);
        if (!auth) return;

        const id = Number(req.params.id);
        const data = db('compilations');
        const idx = (data.compilations || []).findIndex(c => c.id === id);

        if (idx === -1) {
            return res.status(404).json({ success: false, error: 'Compilation not found' });
        }

        data.compilations.splice(idx, 1);
        saveDb('compilations', data);

        audit(auth.user.id, 'delete-compilation', { id });

        res.json({ success: true });

    } catch (e) {
        res.status(500).json({ success: false, error: e.message });
    }
});

// ═══════════════════════════════════════════════════════════════════════════════
// TEACHER AUDIO API
// ═══════════════════════════════════════════════════════════════════════════════
app.get('/api/teacher-audio', (req, res) => {
    try {
        const data = db('teacherAudio');
        const tracks = (data.tracks || []).filter(t => !t.deletedAt);
        res.json({ success: true, tracks });
    } catch (e) {
        res.status(500).json({ success: false, error: e.message });
    }
});

app.post('/api/admin/teacher-audio', upload.single('audio'), (req, res) => {
    try {
        const auth = requireAdmin(req, res);
        if (!auth) return;

        const file = req.file;
        const { teacherName, subject, message } = req.body || {};

        if (!teacherName || !teacherName.trim()) {
            return res.status(400).json({ success: false, error: 'Teacher name required' });
        }

        const data = db('teacherAudio');
        data.tracks = data.tracks || [];
        data.nextId = data.nextId || 1;

        const track = {
            id: data.nextId++,
            teacherName: String(teacherName).trim().substring(0, 80),
            subject: String(subject || '').trim().substring(0, 80),
            message: String(message || '').trim().substring(0, 500),
            file_path: file ? file.filename : null,
            file_url: file ? `/uploads/${file.filename}` : null,
            deletedAt: null,
            createdAt: nowISO()
        };

        data.tracks.push(track);
        saveDb('teacherAudio', data);

        audit(auth.user.id, 'add-teacher-audio', { id: track.id });
        broadcast('teacher-audio:new', { id: track.id });

        res.json({ success: true, track });

    } catch (e) {
        res.status(500).json({ success: false, error: e.message });
    }
});

app.delete('/api/admin/teacher-audio/:id', (req, res) => {
    try {
        const auth = requireAdmin(req, res);
        if (!auth) return;

        const id = Number(req.params.id);
        const data = db('teacherAudio');
        const track = (data.tracks || []).find(t => t.id === id && !t.deletedAt);

        if (!track) {
            return res.status(404).json({ success: false, error: 'Track not found' });
        }

        track.deletedAt = nowISO();

        if (track.file_path) {
            const fp = path.join(uploadsDir, track.file_path);
            if (fs.existsSync(fp)) {
                try { fs.unlinkSync(fp); } catch (e) { }
            }
        }

        saveDb('teacherAudio', data);
        audit(auth.user.id, 'delete-teacher-audio', { id: track.id });

        res.json({ success: true });

    } catch (e) {
        res.status(500).json({ success: false, error: e.message });
    }
});

// ═══════════════════════════════════════════════════════════════════════════════
// STUDENT DIRECTORY API
// ═══════════════════════════════════════════════════════════════════════════════
app.get('/api/student-directory', (req, res) => {
    try {
        const data = db('studentDirectory');
        res.json({ success: true, students: data.students || [] });
    } catch (e) {
        res.status(500).json({ success: false, error: e.message });
    }
});

app.post('/api/admin/student-directory', (req, res) => {
    try {
        const auth = requireAdmin(req, res);
        if (!auth) return;

        if (!hasPerm(auth.user, 'settings')) {
            return res.status(403).json({ success: false, error: 'Forbidden' });
        }

        const { students } = req.body || {};

        if (!Array.isArray(students)) {
            return res.status(400).json({ success: false, error: 'Students array required' });
        }

        const normalized = students.map(s => ({
            name: String(s.name || '').trim().substring(0, 80),
            section: String(s.section || '').trim().substring(0, 40),
            photo: String(s.photo || '').trim(),
            quote: String(s.quote || '').trim().substring(0, 200),
            destination: String(s.destination || '').trim().substring(0, 120)
        })).filter(s => s.name);

        saveDb('studentDirectory', { students: normalized });
        audit(auth.user.id, 'update-student-directory', { count: normalized.length });

        res.json({ success: true, count: normalized.length });

    } catch (e) {
        res.status(500).json({ success: false, error: e.message });
    }
});

app.post('/api/admin/student-directory/import', (req, res) => {
    try {
        const auth = requireAdmin(req, res);
        if (!auth) return;

        if (!hasPerm(auth.user, 'settings')) {
            return res.status(403).json({ success: false, error: 'Forbidden' });
        }

        const { students } = req.body || {};

        if (!Array.isArray(students)) {
            return res.status(400).json({ success: false, error: 'Students array required' });
        }

        const allowedSections = new Set(['10A', '10B', '10C', '10D']);

        const normalized = students.map(s => {
            const section = String(s.section || '').trim().toUpperCase();
            return {
                name: String(s.name || '').trim().substring(0, 80),
                section: allowedSections.has(section) ? section : '',
                photo: String(s.photo || '').trim(),
                quote: String(s.quote || '').trim().substring(0, 200),
                destination: String(s.destination || '').trim().substring(0, 120)
            };
        }).filter(s => s.name);

        saveDb('studentDirectory', { students: normalized });
        audit(auth.user.id, 'import-student-directory', { count: normalized.length });

        res.json({ success: true, count: normalized.length, students: normalized });

    } catch (e) {
        res.status(500).json({ success: false, error: e.message });
    }
});

function normalizeNameKey(s) {
    return String(s || '').trim().toLowerCase().replace(/[^a-z0-9]/g, '');
}

app.post('/api/admin/student-directory/photos-bulk', upload.array('photos', 500), (req, res) => {
    try {
        const auth = requireAdmin(req, res);
        if (!auth) return;

        if (!hasPerm(auth.user, 'settings')) {
            return res.status(403).json({ success: false, error: 'Forbidden' });
        }

        const files = req.files || [];

        if (!files.length) {
            return res.status(400).json({ success: false, error: 'No photos uploaded' });
        }

        const data = db('studentDirectory');
        const students = data.students || [];
        const mapped = [];

        files.forEach(file => {
            const basename = path.parse(file.originalname).name;
            const fileKey = normalizeNameKey(basename);

            const student = students.find(s => normalizeNameKey(s.name) === fileKey);
            if (student) {
                student.photo = `/uploads/${file.filename}`;
                mapped.push({
                    name: student.name,
                    photo: student.photo,
                    original: file.originalname
                });
            }
        });

        saveDb('studentDirectory', { students });
        audit(auth.user.id, 'bulk-student-photos', { mapped: mapped.length, uploaded: files.length });

        res.json({
            success: true,
            mapped,
            uploaded: files.length,
            mappedCount: mapped.length
        });

    } catch (e) {
        res.status(500).json({ success: false, error: e.message });
    }
});

// ═══════════════════════════════════════════════════════════════════════════════
// PAPER NOTES API
// ═══════════════════════════════════════════════════════════════════════════════
app.get('/api/paper-notes/random', (req, res) => {
    try {
        const since = req.query.since ? Number(req.query.since) : 0;
        const data = db('paperNotes');
        const pool = (data.notes || []).filter(n =>
            !n.deletedAt && new Date(n.createdAt).getTime() > since
        );

        if (!pool.length) {
            return res.json({ success: true, note: null });
        }

        const note = pool[Math.floor(Math.random() * pool.length)];
        res.json({ success: true, note });

    } catch (e) {
        res.status(500).json({ success: false, error: e.message });
    }
});

app.get('/api/paper-notes/random-memory', (req, res) => {
    try {
        const data = db('memories');
        const approved = data.memories.filter(m =>
            m.approved === 1 && !m.deletedAt && !m.purgedAt
        );

        if (!approved.length) {
            return res.json({ success: true, memory: null });
        }

        const mem = approved[Math.floor(Math.random() * approved.length)];

        res.json({
            success: true,
            memory: {
                id: mem.id,
                student_name: mem.student_name,
                caption: mem.caption,
                memory_type: mem.memory_type,
                file_url: `/uploads/${mem.file_path}`,
                file_type: mem.file_type
            }
        });

    } catch (e) {
        res.status(500).json({ success: false, error: e.message });
    }
});

app.post('/api/paper-notes', (req, res) => {
    try {
        const { name, message, color } = req.body || {};

        if (!message || !message.trim()) {
            return res.status(400).json({ success: false, error: 'Message required' });
        }

        const data = db('paperNotes');
        data.notes = data.notes || [];
        data.nextId = data.nextId || 1;

        const note = {
            id: data.nextId++,
            name: String(name || 'Anonymous').trim().substring(0, 60),
            message: String(message).trim().substring(0, 300),
            color: String(color || '#ffffff').substring(0, 20),
            deletedAt: null,
            createdAt: nowISO()
        };

        data.notes.push(note);

        // Keep bounded
        if (data.notes.length > 2000) {
            data.notes = data.notes.slice(-2000);
        }

        saveDb('paperNotes', data);
        broadcast('paper:note', note);

        res.json({ success: true, note });

    } catch (e) {
        res.status(500).json({ success: false, error: e.message });
    }
});

app.post('/api/paper-notes/from-memory', (req, res) => {
    try {
        const { memoryId, color } = req.body || {};

        if (!memoryId) {
            return res.status(400).json({ success: false, error: 'memoryId required' });
        }

        const memData = db('memories');
        const mem = memData.memories.find(m =>
            m.id === Number(memoryId) && m.approved === 1 && !m.deletedAt && !m.purgedAt
        );

        if (!mem) {
            return res.status(404).json({ success: false, error: 'Memory not found' });
        }

        const data = db('paperNotes');
        data.notes = data.notes || [];
        data.nextId = data.nextId || 1;

        const note = {
            id: data.nextId++,
            name: mem.student_name,
            message: mem.caption,
            color: String(color || '#fffde7').substring(0, 20),
            memoryId: mem.id,
            file_url: `/uploads/${mem.file_path}`,
            file_type: mem.file_type,
            deletedAt: null,
            createdAt: nowISO()
        };

        data.notes.push(note);

        if (data.notes.length > 2000) {
            data.notes = data.notes.slice(-2000);
        }

        saveDb('paperNotes', data);
        broadcast('paper:note', note);

        res.json({ success: true, note });

    } catch (e) {
        res.status(500).json({ success: false, error: e.message });
    }
});

app.get('/api/admin/paper-notes', (req, res) => {
    try {
        const auth = requireAdmin(req, res);
        if (!auth) return;

        const data = db('paperNotes');
        res.json({
            success: true,
            notes: (data.notes || []).filter(n => !n.deletedAt)
        });

    } catch (e) {
        res.status(500).json({ success: false, error: e.message });
    }
});

app.delete('/api/admin/paper-notes/:id', (req, res) => {
    try {
        const auth = requireAdmin(req, res);
        if (!auth) return;

        const id = Number(req.params.id);
        const data = db('paperNotes');
        const note = (data.notes || []).find(n => n.id === id && !n.deletedAt);

        if (!note) {
            return res.status(404).json({ success: false, error: 'Note not found' });
        }

        note.deletedAt = nowISO();
        saveDb('paperNotes', data);

        audit(auth.user.id, 'delete-paper-note', { id });

        res.json({ success: true });

    } catch (e) {
        res.status(500).json({ success: false, error: e.message });
    }
});

// ═══════════════════════════════════════════════════════════════════════════════
// END OF PART 2
// Continue with Part 3 for Fun Features, Advice Wall, and Server Start
// ═══════════════════════════════════════════════════════════════════════════════

// ═══════════════════════════════════════════════════════════════════════════════
// PART 3: FUN FEATURES, ADVICE WALL, ADMIN STATS & SERVER STARTUP
// ═══════════════════════════════════════════════════════════════════════════════

// ═══════════════════════════════════════════════════════════════════════════════
// SENIOR ADVICE WALL API
// ═══════════════════════════════════════════════════════════════════════════════
app.get('/api/fun/advice', (req, res) => {
    try {
        const data = db('advice');
        const entries = (data.entries || []).filter(e => !e.deletedAt);
        res.json({ success: true, entries });
    } catch (e) {
        res.status(500).json({ success: false, error: e.message });
    }
});

app.post('/api/fun/advice', (req, res) => {
    try {
        const settings = getSettings();

        if (settings.maintenanceMode) {
            return res.status(503).json({ success: false, error: 'Site is in maintenance mode.' });
        }

        const { name, batch, category, text } = req.body || {};

        if (!name || !name.trim()) {
            return res.status(400).json({ success: false, error: 'Name is required' });
        }

        if (!text || !text.trim()) {
            return res.status(400).json({ success: false, error: 'Advice text is required' });
        }

        if (text.trim().length < 10) {
            return res.status(400).json({ success: false, error: 'Advice must be at least 10 characters' });
        }

        if (settings.profanityFilterEnabled) {
            if (containsProfanity(name) || containsProfanity(text)) {
                return res.status(400).json({ success: false, error: 'Content rejected by profanity filter.' });
            }
        }

        const data = db('advice');
        data.entries = data.entries || [];
        data.nextId = data.nextId || 1;

        const entry = {
            id: data.nextId++,
            name: String(name).trim().substring(0, 60),
            batch: String(batch || '').trim().substring(0, 20),
            category: String(category || 'general').trim().substring(0, 30),
            text: String(text).trim().substring(0, 500),
            likes: 0,
            featured: false,
            createdAt: nowISO(),
            deletedAt: null
        };

        data.entries.push(entry);
        saveDb('advice', data);

        broadcast('advice:new', { id: entry.id });

        res.json({ success: true, entry });

    } catch (e) {
        res.status(500).json({ success: false, error: e.message });
    }
});

app.post('/api/fun/advice/:id/like', (req, res) => {
    try {
        const id = parseInt(req.params.id);
        const { unlike } = req.body || {};

        const data = db('advice');
        const entry = (data.entries || []).find(e => e.id === id && !e.deletedAt);

        if (!entry) {
            return res.status(404).json({ success: false, error: 'Advice not found' });
        }

        if (unlike) {
            entry.likes = Math.max(0, (entry.likes || 0) - 1);
        } else {
            entry.likes = (entry.likes || 0) + 1;
        }

        saveDb('advice', data);
        broadcast('advice:like', { id, likes: entry.likes });

        res.json({ success: true, likes: entry.likes });

    } catch (e) {
        res.status(500).json({ success: false, error: e.message });
    }
});

app.delete('/api/fun/advice/:id', (req, res) => {
    try {
        const auth = requireAdmin(req, res);
        if (!auth) return;

        const id = parseInt(req.params.id);
        const data = db('advice');
        const entry = (data.entries || []).find(e => e.id === id);

        if (!entry) {
            return res.status(404).json({ success: false, error: 'Not found' });
        }

        entry.deletedAt = nowISO();
        saveDb('advice', data);

        res.json({ success: true });

    } catch (e) {
        res.status(500).json({ success: false, error: e.message });
    }
});

app.post('/api/fun/advice/:id/feature', (req, res) => {
    try {
        const auth = requireAdmin(req, res);
        if (!auth) return;

        const id = parseInt(req.params.id);
        const { featured } = req.body || {};

        const data = db('advice');
        const entry = (data.entries || []).find(e => e.id === id && !e.deletedAt);

        if (!entry) {
            return res.status(404).json({ success: false, error: 'Not found' });
        }

        entry.featured = !!featured;
        saveDb('advice', data);

        res.json({ success: true, featured: entry.featured });

    } catch (e) {
        res.status(500).json({ success: false, error: e.message });
    }
});

// ═══════════════════════════════════════════════════════════════════════════════
// FUN FEATURES: SETTINGS
// ═══════════════════════════════════════════════════════════════════════════════
app.get('/api/fun/settings', (req, res) => {
    try {
        const data = db('funSettings');
        res.json({ success: true, settings: data });
    } catch (e) {
        res.status(500).json({ success: false, error: e.message });
    }
});

app.post('/api/fun/settings', (req, res) => {
    try {
        const auth = requireAdmin(req, res);
        if (!auth) return;

        const data = db('funSettings');

        if (req.body?.enabled && typeof req.body.enabled === 'object') {
            data.enabled = { ...data.enabled, ...req.body.enabled };
        }

        saveDb('funSettings', data);
        broadcast('ff:settings', data.enabled);

        res.json({ success: true, settings: data });

    } catch (e) {
        res.status(500).json({ success: false, error: e.message });
    }
});

// ═══════════════════════════════════════════════════════════════════════════════
// FUN FEATURES: GRATITUDE WALL
// ═══════════════════════════════════════════════════════════════════════════════
app.get('/api/fun/gratitude', (req, res) => {
    try {
        const data = db('gratitude');
        res.json({ success: true, entries: data.entries || [] });
    } catch (e) {
        res.status(500).json({ success: false, error: e.message });
    }
});

app.post('/api/fun/gratitude', (req, res) => {
    try {
        const { from, to, message } = req.body || {};

        if (!from || !from.trim()) {
            return res.status(400).json({ success: false, error: 'From is required' });
        }

        if (!to || !to.trim()) {
            return res.status(400).json({ success: false, error: 'To is required' });
        }

        if (!message || !message.trim()) {
            return res.status(400).json({ success: false, error: 'Message is required' });
        }

        const settings = getSettings();
        if (settings.profanityFilterEnabled) {
            if (containsProfanity(from) || containsProfanity(to) || containsProfanity(message)) {
                return res.status(400).json({ success: false, error: 'Content rejected by profanity filter.' });
            }
        }

        const data = db('gratitude');
        data.entries = data.entries || [];
        data.nextId = data.nextId || 1;

        const entry = {
            id: data.nextId++,
            from: String(from).trim().substring(0, 60),
            to: String(to).trim().substring(0, 60),
            message: String(message).trim().substring(0, 400),
            createdAt: nowISO()
        };

        data.entries.push(entry);
        saveDb('gratitude', data);

        broadcast('ff:gratitude:new', { id: entry.id });

        res.json({ success: true, entry });

    } catch (e) {
        res.status(500).json({ success: false, error: e.message });
    }
});

app.delete('/api/fun/gratitude/:id', (req, res) => {
    try {
        const auth = requireAdmin(req, res);
        if (!auth) return;

        const id = parseInt(req.params.id);
        const data = db('gratitude');
        const idx = (data.entries || []).findIndex(e => e.id === id);

        if (idx === -1) {
            return res.status(404).json({ success: false, error: 'Not found' });
        }

        data.entries.splice(idx, 1);
        saveDb('gratitude', data);

        res.json({ success: true });

    } catch (e) {
        res.status(500).json({ success: false, error: e.message });
    }
});

// ═══════════════════════════════════════════════════════════════════════════════
// FUN FEATURES: SUPERLATIVES
// ═══════════════════════════════════════════════════════════════════════════════
app.get('/api/fun/superlatives', (req, res) => {
    try {
        const data = db('superlatives');
        res.json({ success: true, categories: data.categories || [] });
    } catch (e) {
        res.status(500).json({ success: false, error: e.message });
    }
});

app.post('/api/fun/superlatives', (req, res) => {
    try {
        const auth = requireAdmin(req, res);
        if (!auth) return;

        const { categories } = req.body || {};

        if (!Array.isArray(categories)) {
            return res.status(400).json({ success: false, error: 'Categories array required' });
        }

        const data = db('superlatives');
        data.nextId = data.nextId || 1;

        data.categories = categories.map(c => ({
            id: c.id || data.nextId++,
            title: String(c.title || '').trim().substring(0, 100),
            nominees: Array.isArray(c.nominees)
                ? c.nominees.map(n => ({
                    name: String(n.name || '').trim().substring(0, 60),
                    votes: Number(n.votes) || 0,
                    imageUrl: n.imageUrl || null
                }))
                : [],
            imageUrl: c.imageUrl || null
        }));

        saveDb('superlatives', data);

        res.json({ success: true, categories: data.categories });

    } catch (e) {
        res.status(500).json({ success: false, error: e.message });
    }
});

app.post('/api/fun/superlatives/nominee', (req, res) => {
    try {
        const { categoryId, name } = req.body || {};

        if (!name || !name.trim()) {
            return res.status(400).json({ success: false, error: 'Name required' });
        }

        const data = db('superlatives');
        const cat = (data.categories || []).find(c => c.id === Number(categoryId));

        if (!cat) {
            return res.status(404).json({ success: false, error: 'Category not found' });
        }

        const normalizedName = name.trim().toLowerCase();
        const exists = cat.nominees.find(n => n.name.toLowerCase() === normalizedName);

        if (!exists) {
            cat.nominees.push({
                name: name.trim().substring(0, 60),
                votes: 0,
                imageUrl: null
            });
            saveDb('superlatives', data);
        }

        res.json({ success: true, categories: data.categories });

    } catch (e) {
        res.status(500).json({ success: false, error: e.message });
    }
});

app.post('/api/fun/superlatives/vote', (req, res) => {
    try {
        const { categoryId, nomineeName } = req.body || {};

        const data = db('superlatives');
        const cat = (data.categories || []).find(c => c.id === Number(categoryId));

        if (!cat) {
            return res.status(404).json({ success: false, error: 'Category not found' });
        }

        const nominee = cat.nominees.find(n => n.name === nomineeName);

        if (!nominee) {
            return res.status(404).json({ success: false, error: 'Nominee not found' });
        }

        nominee.votes = (nominee.votes || 0) + 1;
        saveDb('superlatives', data);

        broadcast('ff:superlatives:vote', { categoryId, nomineeName });

        res.json({ success: true });

    } catch (e) {
        res.status(500).json({ success: false, error: e.message });
    }
});

app.post('/api/fun/superlatives/upload-image', upload.single('image'), (req, res) => {
    try {
        const auth = requireAdmin(req, res);
        if (!auth) return;

        const file = req.file;
        if (!file) {
            return res.status(400).json({ success: false, error: 'No image file' });
        }

        const { categoryId, nomineeName } = req.body || {};
        const data = db('superlatives');
        const cat = (data.categories || []).find(c => c.id === Number(categoryId));

        if (!cat) {
            return res.status(404).json({ success: false, error: 'Category not found' });
        }

        const imageUrl = `/uploads/${file.filename}`;

        if (nomineeName) {
            const nominee = cat.nominees.find(n => n.name === nomineeName);
            if (nominee) {
                nominee.imageUrl = imageUrl;
            }
        } else {
            cat.imageUrl = imageUrl;
        }

        saveDb('superlatives', data);

        res.json({ success: true, imageUrl });

    } catch (e) {
        res.status(500).json({ success: false, error: e.message });
    }
});

app.post('/api/admin/superlatives/map-images-from-students', (req, res) => {
    try {
        const auth = requireAdmin(req, res);
        if (!auth) return;

        const studentData = db('studentDirectory');
        const students = studentData.students || [];

        const data = db('superlatives');
        let mapped = 0;

        (data.categories || []).forEach(cat => {
            (cat.nominees || []).forEach(n => {
                const student = students.find(s =>
                    normalizeNameKey(s.name) === normalizeNameKey(n.name)
                );
                if (student && student.photo) {
                    n.imageUrl = student.photo;
                    mapped++;
                }
            });
        });

        saveDb('superlatives', data);
        audit(auth.user.id, 'map-superlative-images', { mapped });

        res.json({ success: true, mapped, categories: data.categories });

    } catch (e) {
        res.status(500).json({ success: false, error: e.message });
    }
});

// ═══════════════════════════════════════════════════════════════════════════════
// FUN FEATURES: WISHES
// ═══════════════════════════════════════════════════════════════════════════════
app.get('/api/fun/wishes', (req, res) => {
    try {
        const data = db('wishes');
        res.json({ success: true, entries: data.entries || [] });
    } catch (e) {
        res.status(500).json({ success: false, error: e.message });
    }
});

app.post('/api/fun/wishes', (req, res) => {
    try {
        const { name, category, text } = req.body || {};

        if (!name || !name.trim()) {
            return res.status(400).json({ success: false, error: 'Name required' });
        }

        if (!text || !text.trim()) {
            return res.status(400).json({ success: false, error: 'Wish text required' });
        }

        const settings = getSettings();
        if (settings.profanityFilterEnabled) {
            if (containsProfanity(name) || containsProfanity(text)) {
                return res.status(400).json({ success: false, error: 'Content rejected by profanity filter.' });
            }
        }

        const data = db('wishes');
        data.entries = data.entries || [];
        data.nextId = data.nextId || 1;

        const entry = {
            id: data.nextId++,
            name: String(name).trim().substring(0, 60),
            category: String(category || 'General').trim().substring(0, 40),
            text: String(text).trim().substring(0, 500),
            createdAt: nowISO()
        };

        data.entries.push(entry);
        saveDb('wishes', data);

        broadcast('ff:wish:new', { id: entry.id });

        res.json({ success: true, entry });

    } catch (e) {
        res.status(500).json({ success: false, error: e.message });
    }
});

app.delete('/api/fun/wishes/:id', (req, res) => {
    try {
        const auth = requireAdmin(req, res);
        if (!auth) return;

        const id = parseInt(req.params.id);
        const data = db('wishes');
        const idx = (data.entries || []).findIndex(e => e.id === id);

        if (idx === -1) {
            return res.status(404).json({ success: false, error: 'Not found' });
        }

        data.entries.splice(idx, 1);
        saveDb('wishes', data);

        res.json({ success: true });

    } catch (e) {
        res.status(500).json({ success: false, error: e.message });
    }
});

// ═══════════════════════════════════════════════════════════════════════════════
// FUN FEATURES: DEDICATIONS
// ═══════════════════════════════════════════════════════════════════════════════
app.get('/api/fun/dedications', (req, res) => {
    try {
        const data = db('dedications');
        res.json({ success: true, entries: data.entries || [] });
    } catch (e) {
        res.status(500).json({ success: false, error: e.message });
    }
});

app.post('/api/fun/dedications', (req, res) => {
    try {
        const { from, to, song, message } = req.body || {};

        if (!from || !from.trim()) {
            return res.status(400).json({ success: false, error: 'From required' });
        }

        if (!to || !to.trim()) {
            return res.status(400).json({ success: false, error: 'To required' });
        }

        if (!song || !song.trim()) {
            return res.status(400).json({ success: false, error: 'Song required' });
        }

        const settings = getSettings();
        if (settings.profanityFilterEnabled) {
            if (containsProfanity(from) || containsProfanity(to) || containsProfanity(message)) {
                return res.status(400).json({ success: false, error: 'Content rejected by profanity filter.' });
            }
        }

        const data = db('dedications');
        data.entries = data.entries || [];
        data.nextId = data.nextId || 1;

        const entry = {
            id: data.nextId++,
            from: String(from).trim().substring(0, 60),
            to: String(to).trim().substring(0, 60),
            song: String(song).trim().substring(0, 100),
            message: String(message || '').trim().substring(0, 400),
            createdAt: nowISO()
        };

        data.entries.push(entry);
        saveDb('dedications', data);

        broadcast('ff:dedication:new', { id: entry.id });

        res.json({ success: true, entry });

    } catch (e) {
        res.status(500).json({ success: false, error: e.message });
    }
});

app.delete('/api/fun/dedications/:id', (req, res) => {
    try {
        const auth = requireAdmin(req, res);
        if (!auth) return;

        const id = parseInt(req.params.id);
        const data = db('dedications');
        const idx = (data.entries || []).findIndex(e => e.id === id);

        if (idx === -1) {
            return res.status(404).json({ success: false, error: 'Not found' });
        }

        data.entries.splice(idx, 1);
        saveDb('dedications', data);

        res.json({ success: true });

    } catch (e) {
        res.status(500).json({ success: false, error: e.message });
    }
});

// ═══════════════════════════════════════════════════════════════════════════════
// FUN FEATURES: MOOD TRACKER
// ═══════════════════════════════════════════════════════════════════════════════
app.get('/api/fun/mood', (req, res) => {
    try {
        const data = db('mood');
        const votes = data.votes || [];
        const options = data.options || ['Excited', 'Happy', 'Nostalgic', 'Bittersweet', 'Emotional'];

        const counts = {};
        options.forEach(o => counts[o] = 0);
        votes.forEach(v => {
            if (counts[v.mood] !== undefined) {
                counts[v.mood]++;
            }
        });

        res.json({ success: true, votes, options, counts });

    } catch (e) {
        res.status(500).json({ success: false, error: e.message });
    }
});

app.post('/api/fun/mood', (req, res) => {
    try {
        const { name, mood, oldMood } = req.body || {};

        if (!mood || !mood.trim()) {
            return res.status(400).json({ success: false, error: 'Mood required' });
        }

        const data = db('mood');
        data.votes = data.votes || [];

        // Remove previous vote if editing
        if (oldMood) {
            const idx = data.votes.findIndex(v => v.mood === oldMood);
            if (idx !== -1) {
                data.votes.splice(idx, 1);
            }
        }

        data.votes.push({
            name: String(name || 'Anonymous').trim().substring(0, 60),
            mood: String(mood).trim().substring(0, 40),
            createdAt: nowISO()
        });

        // Keep bounded
        if (data.votes.length > 5000) {
            data.votes = data.votes.slice(-5000);
        }

        saveDb('mood', data);
        broadcast('ff:mood:new', {});

        res.json({ success: true });

    } catch (e) {
        res.status(500).json({ success: false, error: e.message });
    }
});

app.delete('/api/fun/mood/:idx', (req, res) => {
    try {
        const auth = requireAdmin(req, res);
        if (!auth) return;

        const idx = parseInt(req.params.idx);
        const data = db('mood');

        if (idx < 0 || idx >= (data.votes || []).length) {
            return res.status(404).json({ success: false, error: 'Not found' });
        }

        data.votes.splice(idx, 1);
        saveDb('mood', data);

        res.json({ success: true });

    } catch (e) {
        res.status(500).json({ success: false, error: e.message });
    }
});

// ═══════════════════════════════════════════════════════════════════════════════
// FUN FEATURES: TIME CAPSULES
// ═══════════════════════════════════════════════════════════════════════════════
app.get('/api/fun/capsules', (req, res) => {
    try {
        const data = db('capsules');
        const now = new Date();

        const entries = (data.entries || []).map(e => {
            const revealed = new Date(e.revealDate) <= now;
            return {
                id: e.id,
                name: e.name,
                revealDate: e.revealDate,
                createdAt: e.createdAt,
                revealed,
                letter: revealed ? e.letter : null
            };
        });

        res.json({ success: true, entries });

    } catch (e) {
        res.status(500).json({ success: false, error: e.message });
    }
});

app.post('/api/fun/capsules', (req, res) => {
    try {
        const { name, revealDate, letter } = req.body || {};

        if (!name || !name.trim()) {
            return res.status(400).json({ success: false, error: 'Name required' });
        }

        if (!revealDate) {
            return res.status(400).json({ success: false, error: 'Reveal date required' });
        }

        if (!letter || !letter.trim()) {
            return res.status(400).json({ success: false, error: 'Letter content required' });
        }

        const settings = getSettings();
        if (settings.profanityFilterEnabled) {
            if (containsProfanity(name) || containsProfanity(letter)) {
                return res.status(400).json({ success: false, error: 'Content rejected by profanity filter.' });
            }
        }

        const data = db('capsules');
        data.entries = data.entries || [];
        data.nextId = data.nextId || 1;

        const entry = {
            id: data.nextId++,
            name: String(name).trim().substring(0, 60),
            revealDate,
            letter: String(letter).trim().substring(0, 2000),
            createdAt: nowISO()
        };

        data.entries.push(entry);
        saveDb('capsules', data);

        res.json({
            success: true,
            entry: {
                id: entry.id,
                name: entry.name,
                revealDate: entry.revealDate,
                createdAt: entry.createdAt
            }
        });

    } catch (e) {
        res.status(500).json({ success: false, error: e.message });
    }
});

app.delete('/api/fun/capsules/:id', (req, res) => {
    try {
        const auth = requireAdmin(req, res);
        if (!auth) return;

        const id = parseInt(req.params.id);
        const data = db('capsules');
        const idx = (data.entries || []).findIndex(e => e.id === id);

        if (idx === -1) {
            return res.status(404).json({ success: false, error: 'Not found' });
        }

        data.entries.splice(idx, 1);
        saveDb('capsules', data);

        res.json({ success: true });

    } catch (e) {
        res.status(500).json({ success: false, error: e.message });
    }
});

// ═══════════════════════════════════════════════════════════════════════════════
// ADMIN: FUN FEATURES STATS
// ═══════════════════════════════════════════════════════════════════════════════
app.get('/api/admin/fun/stats', (req, res) => {
    try {
        const auth = requireAdmin(req, res);
        if (!auth) return;

        const gratitude = db('gratitude');
        const wishes = db('wishes');
        const dedications = db('dedications');
        const capsules = db('capsules');
        const mood = db('mood');
        const advice = db('advice');

        const moodCounts = {};
        (mood.votes || []).forEach(v => {
            moodCounts[v.mood] = (moodCounts[v.mood] || 0) + 1;
        });

        res.json({
            success: true,
            stats: {
                gratitude: {
                    count: (gratitude.entries || []).length,
                    entries: gratitude.entries || []
                },
                wishes: {
                    count: (wishes.entries || []).length,
                    entries: wishes.entries || []
                },
                dedications: {
                    count: (dedications.entries || []).length,
                    entries: dedications.entries || []
                },
                capsules: {
                    count: (capsules.entries || []).length,
                    entries: capsules.entries || []
                },
                mood: {
                    total: (mood.votes || []).length,
                    votes: moodCounts
                },
                advice: {
                    count: (advice.entries || []).filter(e => !e.deletedAt).length,
                    entries: (advice.entries || []).filter(e => !e.deletedAt)
                }
            }
        });

    } catch (e) {
        res.status(500).json({ success: false, error: e.message });
    }
});

// ═══════════════════════════════════════════════════════════════════════════════
// ADMIN: FUN FEATURES EXPORT
// ═══════════════════════════════════════════════════════════════════════════════
app.get('/api/admin/fun/export/:feature', (req, res) => {
    try {
        const auth = requireAdmin(req, res);
        if (!auth) return;

        if (!hasPerm(auth.user, 'export')) {
            return res.status(403).json({ success: false, error: 'Forbidden' });
        }

        const feature = req.params.feature;
        const validFeatures = ['gratitude', 'wishes', 'dedications', 'capsules', 'mood', 'advice'];

        if (!validFeatures.includes(feature)) {
            return res.status(400).json({ success: false, error: 'Invalid feature' });
        }

        const data = db(feature);
        const items = data.entries || data.votes || [];

        if (!items.length) {
            res.setHeader('Content-Type', 'text/csv');
            res.setHeader('Content-Disposition', `attachment; filename="${feature}-export.csv"`);
            return res.send('No data\n');
        }

        const headers = Object.keys(items[0]);
        const lines = [
            headers.join(','),
            ...items.map(r => headers.map(h => `"${sanitizeCSV(r[h] ?? '')}"`).join(','))
        ];

        res.setHeader('Content-Type', 'text/csv; charset=utf-8');
        res.setHeader('Content-Disposition', `attachment; filename="${feature}-export-${new Date().toISOString().slice(0, 10)}.csv"`);
        res.send(lines.join('\n'));

    } catch (e) {
        res.status(500).json({ success: false, error: e.message });
    }
});

// ═══════════════════════════════════════════════════════════════════════════════
// ADMIN: BATCH UPLOAD (bypasses window, auto-approved)
// ═══════════════════════════════════════════════════════════════════════════════
app.post('/api/admin/upload-batch', upload.array('files', 50), (req, res) => {
    try {
        const auth = requireAdmin(req, res);
        if (!auth) return;

        if (!hasPerm(auth.user, 'bulk')) {
            return res.status(403).json({ success: false, error: 'Forbidden' });
        }

        const files = req.files || [];

        if (!files.length) {
            return res.status(400).json({ success: false, error: 'No files provided' });
        }

        const {
            name = 'Admin Upload',
            caption = 'Batch upload',
            type = 'general'
        } = req.body;

        const data = db('memories');
        const insertedIds = [];
        const duplicates = [];

        files.forEach(file => {
            const filePath = path.join(uploadsDir, file.filename);
            const hash = sha256File(filePath);

            // Check duplicates
            if (hash) {
                const existing = data.memories.find(m => m.sha256 === hash && !m.purgedAt);
                if (existing) {
                    duplicates.push({ originalId: existing.id, file: file.originalname });
                    try { fs.unlinkSync(filePath); } catch (e) { }
                    return;
                }
            }

            const memory = {
                id: data.nextId++,
                student_name: String(name).trim().substring(0, 100),
                caption: String(caption).trim().substring(0, 1000),
                memory_type: String(type).trim(),
                file_path: file.filename,
                file_name: file.originalname,
                file_type: getFileType(file.mimetype),
                file_size: file.size,
                sha256: hash,
                approved: 1,
                featured: 0,
                likes: 0,
                deletedAt: null,
                purgedAt: null,
                created_at: nowISO(),
                updated_at: nowISO()
            };

            data.memories.push(memory);
            insertedIds.push(memory.id);
        });

        saveDb('memories', data);
        audit(auth.user.id, 'batch-upload', { count: insertedIds.length });
        broadcast('memory:bulk', { type: 'new', count: insertedIds.length });

        res.json({
            success: true,
            count: insertedIds.length,
            ids: insertedIds,
            duplicates
        });

    } catch (e) {
        res.status(500).json({ success: false, error: e.message });
    }
});

// ═══════════════════════════════════════════════════════════════════════════════
// ADMIN: INTRO VIDEO MANAGEMENT
// ═══════════════════════════════════════════════════════════════════════════════
app.post('/api/admin/settings/intro-video', (req, res) => {
    try {
        const auth = requireAdmin(req, res);
        if (!auth) return;

        if (!hasPerm(auth.user, 'settings')) {
            return res.status(403).json({ success: false, error: 'Forbidden' });
        }

        const { introVideoPath } = req.body || {};

        if (!introVideoPath) {
            return res.status(400).json({ success: false, error: 'introVideoPath required' });
        }

        const data = db('settings');
        data.settings = data.settings || {};
        data.settings.introVideoPath = String(introVideoPath).trim();
        saveDb('settings', data);

        audit(auth.user.id, 'set-intro-video', {});
        broadcast('settings:update', {});

        res.json({ success: true, introVideoPath: data.settings.introVideoPath });

    } catch (e) {
        res.status(500).json({ success: false, error: e.message });
    }
});

app.delete('/api/admin/settings/intro-video', (req, res) => {
    try {
        const auth = requireAdmin(req, res);
        if (!auth) return;

        if (!hasPerm(auth.user, 'settings')) {
            return res.status(403).json({ success: false, error: 'Forbidden' });
        }

        const data = db('settings');

        if (data.settings?.introVideoPath) {
            const oldFile = path.join(uploadsDir, path.basename(String(data.settings.introVideoPath)));
            if (fs.existsSync(oldFile)) {
                try { fs.unlinkSync(oldFile); } catch (e) { }
            }
            delete data.settings.introVideoPath;
            saveDb('settings', data);
        }

        audit(auth.user.id, 'remove-intro-video', {});
        broadcast('settings:update', {});

        res.json({ success: true });

    } catch (e) {
        res.status(500).json({ success: false, error: e.message });
    }
});

// ═══════════════════════════════════════════════════════════════════════════════
// ADMIN: CHANGE PASSWORD (Legacy endpoint)
// ═══════════════════════════════════════════════════════════════════════════════
app.post('/api/admin/change-password', (req, res) => {
    try {
        const auth = requireAdmin(req, res);
        if (!auth) return;

        const { oldPassword, newPassword } = req.body || {};

        if (!oldPassword || !newPassword) {
            return res.status(400).json({ success: false, error: 'Missing oldPassword or newPassword' });
        }

        if (newPassword.length < 8) {
            return res.status(400).json({ success: false, error: 'Password must be at least 8 characters' });
        }

        const admins = db('admin');
        const user = admins.users.find(u => u.id === auth.user.id);

        if (!user) {
            return res.status(404).json({ success: false, error: 'User not found' });
        }

        if (user.password !== oldPassword) {
            return res.status(400).json({ success: false, error: 'Old password incorrect' });
        }

        user.password = newPassword;
        user.updatedAt = nowISO();
        saveDb('admin', admins);

        // Invalidate all sessions for this user
        const sessions = db('sessions');
        sessions.sessions = sessions.sessions.filter(s => s.userId !== user.id);
        saveDb('sessions', sessions);

        audit(auth.user.id, 'change-password', {});

        res.json({ success: true });

    } catch (e) {
        res.status(500).json({ success: false, error: e.message });
    }
});

// ═══════════════════════════════════════════════════════════════════════════════
// CATCH-ALL: SERVE FRONTEND
// ═══════════════════════════════════════════════════════════════════════════════
app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, 'index.html'));
});

app.get('*', (req, res) => {
    // Check if it's an API call that wasn't matched
    if (req.path.startsWith('/api/')) {
        return res.status(404).json({ success: false, error: 'Endpoint not found' });
    }
    res.sendFile(path.join(__dirname, 'index.html'));
});

// ═══════════════════════════════════════════════════════════════════════════════
// ERROR HANDLING MIDDLEWARE
// ═══════════════════════════════════════════════════════════════════════════════
app.use((err, req, res, next) => {
    console.error('Server error:', err);

    // Handle Multer errors
    if (err && err.name === 'MulterError') {
        if (err.code === 'LIMIT_FILE_SIZE') {
            return res.status(400).json({
                success: false,
                error: `File too large. Maximum size is ${MAX_FILE_SIZE / 1024 / 1024}MB per file.`
            });
        }
        if (err.code === 'LIMIT_FILE_COUNT') {
            return res.status(400).json({
                success: false,
                error: `Too many files. Maximum is ${MAX_FILES} files per upload.`
            });
        }
        return res.status(400).json({ success: false, error: err.message });
    }

    // Handle other errors
    res.status(500).json({
        success: false,
        error: err.message || 'Internal server error'
    });
});

// ═══════════════════════════════════════════════════════════════════════════════
// START SERVER
// ═══════════════════════════════════════════════════════════════════════════════
server.listen(PORT, '0.0.0.0', () => {
    console.log('');
    console.log('═══════════════════════════════════════════════════════════════════');
    console.log('   CORNERSTONE FAREWELL 2025 - SERVER STARTED');
    console.log('═══════════════════════════════════════════════════════════════════');
    console.log(`   Server running on: http://localhost:${PORT}`);
    console.log(`   Network access:    http://0.0.0.0:${PORT}`);
    console.log('───────────────────────────────────────────────────────────────────');
    console.log(`   Uploads folder:    ${uploadsDir}`);
    console.log(`   Database folder:   ${databaseDir}`);
    console.log(`   Music folder:      ${musicDir}`);
    console.log('───────────────────────────────────────────────────────────────────');
    console.log(`   Max file size:     ${MAX_FILE_SIZE / 1024 / 1024}MB per file`);
    console.log(`   Max total size:    ${MAX_TOTAL_SIZE / 1024 / 1024}MB per upload`);
    console.log(`   Max files:         ${MAX_FILES} per upload`);
    console.log('───────────────────────────────────────────────────────────────────');
    console.log('   Default admin:     super / cornerstone2025');
    console.log('═══════════════════════════════════════════════════════════════════');
    console.log('');
});

// ═══════════════════════════════════════════════════════════════════════════════
// GRACEFUL SHUTDOWN
// ═══════════════════════════════════════════════════════════════════════════════
process.on('SIGTERM', () => {
    console.log('SIGTERM received. Closing server...');
    server.close(() => {
        console.log('Server closed.');
        process.exit(0);
    });
});

process.on('SIGINT', () => {
    console.log('SIGINT received. Closing server...');
    server.close(() => {
        console.log('Server closed.');
        process.exit(0);
    });
});

process.on('uncaughtException', (err) => {
    console.error('Uncaught Exception:', err);
});

process.on('unhandledRejection', (reason, promise) => {
    console.error('Unhandled Rejection at:', promise, 'reason:', reason);
});

// ═══════════════════════════════════════════════════════════════════════════════
// END OF SERVER.JS
// ═══════════════════════════════════════════════════════════════════════════════