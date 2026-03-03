/**
 * ═══════════════════════════════════════════════════════════════════════════════
 * CORNERSTONE INTERNATIONAL SCHOOL - FAREWELL 2025
 * Backend Server - Node.js + Express + SQLite (sql.js)
 * (Currently uses JSON file-based storage for reliability)
 * ═══════════════════════════════════════════════════════════════════════════════
 */

const express = require('express');
const multer = require('multer');
const path = require('path');
const fs = require('fs');
const archiver = require('archiver');
const cors = require('cors');

// ═══════════════════════════════════════════════════════════════════════════════
// CONFIGURATION
// ═══════════════════════════════════════════════════════════════════════════════

const PORT = process.env.PORT || 3000;
const ADMIN_PASSWORD = 'cornerstone2025'; // ⚠️ CHANGE THIS IN PRODUCTION!
const MAX_FILE_SIZE = 100 * 1024 * 1024; // 100MB per file
const MAX_TOTAL_SIZE = 200 * 1024 * 1024; // 200MB total per upload
const MAX_FILES = 20; // Maximum files per upload

// ═══════════════════════════════════════════════════════════════════════════════
// INITIALIZE EXPRESS APP
// ═══════════════════════════════════════════════════════════════════════════════

const app = express();

// Middleware
app.use(cors());
app.use(express.json());
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
// JSON FILE-BASED DATABASE (Simple & Reliable Alternative)
// ═══════════════════════════════════════════════════════════════════════════════

const dbPath = path.join(databaseDir, 'memories.json');
const sessionsPath = path.join(databaseDir, 'sessions.json');

// NEW: Settings + Admin storage (for editable content + change password)
const settingsPath = path.join(databaseDir, 'settings.json');
const adminPath = path.join(databaseDir, 'admin.json');

// Initialize database files
function initDatabase() {
    if (!fs.existsSync(dbPath)) {
        fs.writeFileSync(dbPath, JSON.stringify({ memories: [], nextId: 1 }, null, 2));
        console.log('💾 Created memories database');
    }
    if (!fs.existsSync(sessionsPath)) {
        fs.writeFileSync(sessionsPath, JSON.stringify({ sessions: [] }, null, 2));
        console.log('💾 Created sessions database');
    }

    // NEW: settings database
    if (!fs.existsSync(settingsPath)) {
        fs.writeFileSync(settingsPath, JSON.stringify({ settings: {} }, null, 2));
        console.log('💾 Created settings database');
    }

    // NEW: admin database (stores current password)
    if (!fs.existsSync(adminPath)) {
        fs.writeFileSync(adminPath, JSON.stringify({ password: ADMIN_PASSWORD }, null, 2));
        console.log('💾 Created admin database');
    }
}

function readDB() {
    try {
        return JSON.parse(fs.readFileSync(dbPath, 'utf8'));
    } catch (e) {
        return { memories: [], nextId: 1 };
    }
}

function writeDB(data) {
    fs.writeFileSync(dbPath, JSON.stringify(data, null, 2));
}

function readSessions() {
    try {
        return JSON.parse(fs.readFileSync(sessionsPath, 'utf8'));
    } catch (e) {
        return { sessions: [] };
    }
}

function writeSessions(data) {
    fs.writeFileSync(sessionsPath, JSON.stringify(data, null, 2));
}

// NEW: settings helpers
function readSettings() {
    try {
        return JSON.parse(fs.readFileSync(settingsPath, 'utf8'));
    } catch (e) {
        return { settings: {} };
    }
}
function writeSettings(data) {
    fs.writeFileSync(settingsPath, JSON.stringify(data, null, 2));
}

// NEW: admin helpers
function readAdmin() {
    try {
        return JSON.parse(fs.readFileSync(adminPath, 'utf8'));
    } catch (e) {
        return { password: ADMIN_PASSWORD };
    }
}
function writeAdmin(data) {
    fs.writeFileSync(adminPath, JSON.stringify(data, null, 2));
}

initDatabase();
console.log(`💾 Database initialized: ${dbPath}`);

// ═══════════════════════════════════════════════════════════════════════════════
// FILE UPLOAD CONFIGURATION (MULTER)
// ═══════════════════════════════════════════════════════════════════════════════

const storage = multer.diskStorage({
    destination: (req, file, cb) => {
        cb(null, uploadsDir);
    },
    filename: (req, file, cb) => {
        const uniqueSuffix = Date.now() + '-' + Math.round(Math.random() * 1E9);
        const ext = path.extname(file.originalname).toLowerCase();
        const safeName = file.originalname.replace(/[^a-zA-Z0-9.-]/g, '_').substring(0, 50);
        cb(null, `${uniqueSuffix}-${safeName}`);
    }
});

const fileFilter = (req, file, cb) => {
    const allowedImageTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp'];
    const allowedVideoTypes = ['video/mp4', 'video/quicktime', 'video/x-msvideo', 'video/webm'];
    const allowedTypes = [...allowedImageTypes, ...allowedVideoTypes];

    if (allowedTypes.includes(file.mimetype)) {
        cb(null, true);
    } else {
        cb(new Error(`Invalid file type: ${file.mimetype}`), false);
    }
};

const upload = multer({
    storage: storage,
    limits: {
        fileSize: MAX_FILE_SIZE,
        files: MAX_FILES
    },
    fileFilter: fileFilter
});

// Check total upload size middleware
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
// HELPER FUNCTIONS
// ═══════════════════════════════════════════════════════════════════════════════

function generateToken() {
    return 'admin-' + Date.now() + '-' + Math.random().toString(36).substr(2, 9);
}

function validateAdminToken(token) {
    if (!token) return false;
    const data = readSessions();
    const now = new Date();
    const session = data.sessions.find(s => s.token === token && new Date(s.expiresAt) > now);
    return !!session;
}

// NEW: small helper for admin-only endpoints (keeps existing behavior intact)
function requireAdmin(req, res) {
    const token = req.headers.authorization?.replace('Bearer ', '');
    if (!validateAdminToken(token)) {
        res.status(401).json({ success: false, error: 'Unauthorized' });
        return null;
    }
    return token;
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

// ═══════════════════════════════════════════════════════════════════════════════
// API ENDPOINTS - PUBLIC
// ═══════════════════════════════════════════════════════════════════════════════

// NEW: Get Site Settings (public)
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

        if (!name || !name.trim()) {
            return res.status(400).json({ success: false, error: 'Student name is required' });
        }
        if (!caption || !caption.trim()) {
            return res.status(400).json({ success: false, error: 'Caption is required' });
        }
        if (!type) {
            return res.status(400).json({ success: false, error: 'Memory type is required' });
        }
        if (!files || files.length === 0) {
            return res.status(400).json({ success: false, error: 'Please select at least one file' });
        }

        const db = readDB();
        const insertedIds = [];

        files.forEach(file => {
            const memory = {
                id: db.nextId++,
                student_name: name.trim(),
                caption: caption.trim().substring(0, 500),
                memory_type: type,
                file_path: file.filename,
                file_name: file.originalname,
                file_type: getFileType(file.mimetype),
                file_size: file.size,
                approved: 0,
                likes: 0,
                created_at: new Date().toISOString()
            };
            db.memories.push(memory);
            insertedIds.push(memory.id);
        });

        writeDB(db);

        console.log(`📤 New upload: ${files.length} file(s) from "${name}"`);

        res.json({
            success: true,
            message: `Successfully uploaded ${files.length} memory${files.length > 1 ? 'ies' : ''}!`,
            count: files.length,
            ids: insertedIds
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
        const memories = db.memories
            .filter(m => m.approved === 1)
            .sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
            .map(m => ({
                ...m,
                file_url: `/uploads/${m.file_path}`
            }));

        res.json({
            success: true,
            memories: memories,
            count: memories.length
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

        const memory = db.memories.find(m => m.id === id && m.approved === 1);
        if (!memory) {
            return res.status(404).json({ success: false, error: 'Memory not found' });
        }

        memory.likes++;
        writeDB(db);

        res.json({ success: true, likes: memory.likes });

    } catch (error) {
        console.error('Like error:', error);
        res.status(500).json({ success: false, error: error.message });
    }
});

// Get Stats
app.get('/api/stats', (req, res) => {
    try {
        const db = readDB();
        const approved = db.memories.filter(m => m.approved === 1);
        const totalLikes = approved.reduce((sum, m) => sum + m.likes, 0);

        res.json({
            success: true,
            stats: {
                totalMemories: approved.length,
                totalLikes: totalLikes
            }
        });

    } catch (error) {
        console.error('Stats error:', error);
        res.status(500).json({ success: false, error: error.message });
    }
});

// ═══════════════════════════════════════════════════════════════════════════════
// API ENDPOINTS - ADMIN
// ═══════════════════════════════════════════════════════════════════════════════

// Admin Login
app.post('/api/admin/login', (req, res) => {
    try {
        const { password } = req.body;

        // NEW: read current password from admin.json (created on first run)
        const admin = readAdmin();

        if (password !== admin.password) {
            console.log('❌ Failed admin login attempt');
            return res.status(401).json({ success: false, error: 'Invalid password' });
        }

        const token = generateToken();
        const expiresAt = new Date(Date.now() + 24 * 60 * 60 * 1000); // 24 hours

        const sessions = readSessions();
        // Clean old sessions
        sessions.sessions = sessions.sessions.filter(s => new Date(s.expiresAt) > new Date());
        // Add new session
        sessions.sessions.push({ token, expiresAt: expiresAt.toISOString() });
        writeSessions(sessions);

        console.log('✅ Admin logged in');

        res.json({
            success: true,
            token: token,
            expiresAt: expiresAt.toISOString()
        });

    } catch (error) {
        console.error('Admin login error:', error);
        res.status(500).json({ success: false, error: error.message });
    }
});

// Verify Admin Token
app.post('/api/admin/verify', (req, res) => {
    try {
        const token = req.headers.authorization?.replace('Bearer ', '');
        const isValid = validateAdminToken(token);
        res.json({ success: true, valid: isValid });
    } catch (error) {
        res.json({ success: true, valid: false });
    }
});

// NEW: Save Site Settings (admin)
app.post('/api/admin/settings', (req, res) => {
    try {
        if (!requireAdmin(req, res)) return;

        const incoming = req.body?.settings;
        if (!incoming || typeof incoming !== 'object') {
            return res.status(400).json({ success: false, error: 'Missing settings object' });
        }

        // Basic validation (frontend uses this format)
        if (incoming.farewellIST && !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/.test(incoming.farewellIST)) {
            return res.status(400).json({
                success: false,
                error: 'Invalid farewellIST format. Use YYYY-MM-DDTHH:mm'
            });
        }

        writeSettings({ settings: incoming });
        console.log('⚙️ Site settings updated by admin');

        res.json({ success: true });
    } catch (error) {
        console.error('Save settings error:', error);
        res.status(500).json({ success: false, error: error.message });
    }
});

// NEW: Change Admin Password (admin)
app.post('/api/admin/change-password', (req, res) => {
    try {
        if (!requireAdmin(req, res)) return;

        const { oldPassword, newPassword } = req.body || {};
        if (!oldPassword || !newPassword) {
            return res.status(400).json({ success: false, error: 'Missing oldPassword or newPassword' });
        }

        if (String(newPassword).length < 8) {
            return res.status(400).json({ success: false, error: 'Password must be at least 8 characters' });
        }

        const admin = readAdmin();
        if (oldPassword !== admin.password) {
            return res.status(400).json({ success: false, error: 'Old password is incorrect' });
        }

        // Save new password
        writeAdmin({ password: String(newPassword) });

        // Invalidate all sessions (recommended for security)
        writeSessions({ sessions: [] });

        console.log('🔐 Admin password changed (all sessions invalidated)');

        res.json({ success: true });
    } catch (error) {
        console.error('Change password error:', error);
        res.status(500).json({ success: false, error: error.message });
    }
});

// Get All Memories (Admin)
app.get('/api/admin/memories', (req, res) => {
    try {
        const token = req.headers.authorization?.replace('Bearer ', '');
        if (!validateAdminToken(token)) {
            return res.status(401).json({ success: false, error: 'Unauthorized' });
        }

        const { filter, sort, search } = req.query;
        const db = readDB();

        let memories = [...db.memories];

        // Filter
        if (filter === 'approved') {
            memories = memories.filter(m => m.approved === 1);
        } else if (filter === 'pending') {
            memories = memories.filter(m => m.approved === 0);
        }

        // Search
        if (search) {
            const searchLower = search.toLowerCase();
            memories = memories.filter(m =>
                m.student_name.toLowerCase().includes(searchLower) ||
                m.caption.toLowerCase().includes(searchLower)
            );
        }

        // Sort
        if (sort === 'oldest') {
            memories.sort((a, b) => new Date(a.created_at) - new Date(b.created_at));
        } else if (sort === 'likes') {
            memories.sort((a, b) => b.likes - a.likes);
        } else {
            memories.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
        }

        // Calculate stats
        const allMemories = db.memories;
        const stats = {
            total: allMemories.length,
            approved: allMemories.filter(m => m.approved === 1).length,
            pending: allMemories.filter(m => m.approved === 0).length,
            totalSize: allMemories.reduce((sum, m) => sum + (m.file_size || 0), 0),
            totalSizeFormatted: formatFileSize(allMemories.reduce((sum, m) => sum + (m.file_size || 0), 0))
        };

        // Add URLs
        const memoriesWithUrls = memories.map(memory => ({
            ...memory,
            file_url: `/uploads/${memory.file_path}`,
            file_size_formatted: formatFileSize(memory.file_size || 0)
        }));

        res.json({
            success: true,
            memories: memoriesWithUrls,
            stats: stats
        });

    } catch (error) {
        console.error('Admin get memories error:', error);
        res.status(500).json({ success: false, error: error.message });
    }
});

// Approve Memory
app.post('/api/admin/approve/:id', (req, res) => {
    try {
        const token = req.headers.authorization?.replace('Bearer ', '');
        if (!validateAdminToken(token)) {
            return res.status(401).json({ success: false, error: 'Unauthorized' });
        }

        const id = parseInt(req.params.id);
        const db = readDB();

        const memory = db.memories.find(m => m.id === id);
        if (!memory) {
            return res.status(404).json({ success: false, error: 'Memory not found' });
        }

        memory.approved = 1;
        writeDB(db);

        console.log(`✅ Approved memory #${id}`);

        res.json({ success: true, message: 'Memory approved' });

    } catch (error) {
        console.error('Approve error:', error);
        res.status(500).json({ success: false, error: error.message });
    }
});

// Approve All
app.post('/api/admin/approve-all', (req, res) => {
    try {
        const token = req.headers.authorization?.replace('Bearer ', '');
        if (!validateAdminToken(token)) {
            return res.status(401).json({ success: false, error: 'Unauthorized' });
        }

        const db = readDB();
        let count = 0;

        db.memories.forEach(m => {
            if (m.approved === 0) {
                m.approved = 1;
                count++;
            }
        });

        writeDB(db);

        console.log(`✅ Approved ${count} memories`);

        res.json({
            success: true,
            message: `Approved ${count} memories`,
            count: count
        });

    } catch (error) {
        console.error('Approve all error:', error);
        res.status(500).json({ success: false, error: error.message });
    }
});

// Delete Memory
app.delete('/api/admin/delete/:id', (req, res) => {
    try {
        const token = req.headers.authorization?.replace('Bearer ', '');
        if (!validateAdminToken(token)) {
            return res.status(401).json({ success: false, error: 'Unauthorized' });
        }

        const id = parseInt(req.params.id);
        const db = readDB();

        const memoryIndex = db.memories.findIndex(m => m.id === id);
        if (memoryIndex === -1) {
            return res.status(404).json({ success: false, error: 'Memory not found' });
        }

        const memory = db.memories[memoryIndex];

        // Delete file
        const filePath = path.join(uploadsDir, memory.file_path);
        if (fs.existsSync(filePath)) {
            fs.unlinkSync(filePath);
        }

        // Remove from database
        db.memories.splice(memoryIndex, 1);
        writeDB(db);

        console.log(`🗑️ Deleted memory #${id}`);

        res.json({ success: true, message: 'Memory deleted' });

    } catch (error) {
        console.error('Delete error:', error);
        res.status(500).json({ success: false, error: error.message });
    }
});

// Download All as ZIP
app.get('/api/admin/download-all', (req, res) => {
    try {
        const token = req.query.token || req.headers.authorization?.replace('Bearer ', '');
        if (!validateAdminToken(token)) {
            return res.status(401).json({ success: false, error: 'Unauthorized' });
        }

        const db = readDB();
        const memories = db.memories.filter(m => m.approved === 1);

        if (memories.length === 0) {
            return res.status(404).json({ success: false, error: 'No approved memories to download' });
        }

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

        console.log(`📦 ZIP download started: ${memories.length} files`);

    } catch (error) {
        console.error('Download all error:', error);
        res.status(500).json({ success: false, error: error.message });
    }
});

// Admin Logout
app.post('/api/admin/logout', (req, res) => {
    try {
        const token = req.headers.authorization?.replace('Bearer ', '');
        if (token) {
            const sessions = readSessions();
            sessions.sessions = sessions.sessions.filter(s => s.token !== token);
            writeSessions(sessions);
        }
        res.json({ success: true, message: 'Logged out' });
    } catch (error) {
        res.status(500).json({ success: false, error: error.message });
    }
});

// ═══════════════════════════════════════════════════════════════════════════════
// SERVE FRONTEND
// ═══════════════════════════════════════════════════════════════════════════════

app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, 'index.html'));
});

app.get('*', (req, res) => {
    res.sendFile(path.join(__dirname, 'index.html'));
});

// ═══════════════════════════════════════════════════════════════════════════════
// ERROR HANDLING
// ═══════════════════════════════════════════════════════════════════════════════

app.use((err, req, res, next) => {
    console.error('Server error:', err);

    if (err instanceof multer.MulterError) {
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
    }

    res.status(500).json({ success: false, error: err.message || 'Internal server error' });
});

// ═══════════════════════════════════════════════════════════════════════════════
// START SERVER
// ═══════════════════════════════════════════════════════════════════════════════

app.listen(PORT, '0.0.0.0', () => {
    console.log('');
    console.log('═══════════════════════════════════════════════════════════════════');
    console.log('🎓 CORNERSTONE INTERNATIONAL SCHOOL - FAREWELL 2025');
    console.log('═══════════════════════════════════════════════════════════════════');
    console.log(`🚀 Server running on: http://localhost:${PORT}`);
    console.log(`🌐 Network access: http://0.0.0.0:${PORT}`);
    console.log(`📁 Uploads folder: ${uploadsDir}`);
    console.log(`💾 Database: ${dbPath}`);
    console.log(`🔐 Admin password (initial/default): ${ADMIN_PASSWORD}`);
    console.log(`📊 Max upload size: ${MAX_TOTAL_SIZE / 1024 / 1024}MB total`);
    console.log(`⚙️ Settings file: ${settingsPath}`);
    console.log(`🔐 Admin file: ${adminPath}`);
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