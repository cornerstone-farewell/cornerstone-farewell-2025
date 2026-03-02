/**
 * ═══════════════════════════════════════════════════════════════════════════════
 * CORNERSTONE INTERNATIONAL SCHOOL - FAREWELL 2025
 * Backend Server - Node.js + Express + SQLite
 * ═══════════════════════════════════════════════════════════════════════════════
 */

const express = require('express');
const multer = require('multer');
const Database = require('better-sqlite3');
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
// DATABASE SETUP
// ═══════════════════════════════════════════════════════════════════════════════

const dbPath = path.join(databaseDir, 'memories.db');
const db = new Database(dbPath);

// Create tables
db.exec(`
    CREATE TABLE IF NOT EXISTS memories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_name TEXT NOT NULL,
        caption TEXT NOT NULL,
        memory_type TEXT NOT NULL,
        file_path TEXT NOT NULL,
        file_name TEXT NOT NULL,
        file_type TEXT NOT NULL,
        file_size INTEGER DEFAULT 0,
        approved INTEGER DEFAULT 0,
        likes INTEGER DEFAULT 0,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS admin_sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        token TEXT UNIQUE NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        expires_at DATETIME NOT NULL
    );

    CREATE INDEX IF NOT EXISTS idx_memories_approved ON memories(approved);
    CREATE INDEX IF NOT EXISTS idx_memories_created ON memories(created_at);
`);

console.log(`💾 Database initialized: ${dbPath}`);

// ═══════════════════════════════════════════════════════════════════════════════
// FILE UPLOAD CONFIGURATION (MULTER)
// ═══════════════════════════════════════════════════════════════════════════════

const storage = multer.diskStorage({
    destination: (req, file, cb) => {
        cb(null, uploadsDir);
    },
    filename: (req, file, cb) => {
        // Generate unique filename
        const uniqueSuffix = Date.now() + '-' + Math.round(Math.random() * 1E9);
        const ext = path.extname(file.originalname).toLowerCase();
        const safeName = file.originalname.replace(/[^a-zA-Z0-9.-]/g, '_');
        cb(null, `${uniqueSuffix}-${safeName}`);
    }
});

const fileFilter = (req, file, cb) => {
    // Allowed file types
    const allowedImageTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp'];
    const allowedVideoTypes = ['video/mp4', 'video/quicktime', 'video/x-msvideo', 'video/webm', 'video/avi'];
    const allowedTypes = [...allowedImageTypes, ...allowedVideoTypes];

    if (allowedTypes.includes(file.mimetype)) {
        cb(null, true);
    } else {
        cb(new Error(`Invalid file type: ${file.mimetype}. Allowed: JPG, PNG, GIF, WEBP, MP4, MOV, AVI, WEBM`), false);
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

// Custom middleware to check total upload size
const checkTotalSize = (req, res, next) => {
    if (req.files && req.files.length > 0) {
        const totalSize = req.files.reduce((sum, file) => sum + file.size, 0);
        if (totalSize > MAX_TOTAL_SIZE) {
            // Delete uploaded files
            req.files.forEach(file => {
                const filePath = path.join(uploadsDir, file.filename);
                if (fs.existsSync(filePath)) {
                    fs.unlinkSync(filePath);
                }
            });
            return res.status(400).json({
                success: false,
                error: `Total upload size (${(totalSize / 1024 / 1024).toFixed(2)}MB) exceeds limit of ${MAX_TOTAL_SIZE / 1024 / 1024}MB`
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
    const session = db.prepare('SELECT * FROM admin_sessions WHERE token = ? AND expires_at > datetime("now")').get(token);
    return !!session;
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

/**
 * POST /api/upload
 * Upload memories (images/videos)
 */
app.post('/api/upload', upload.array('files', MAX_FILES), checkTotalSize, (req, res) => {
    try {
        const { name, caption, type } = req.body;
        const files = req.files;

        // Validation
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

        // Insert each file into database
        const insert = db.prepare(`
            INSERT INTO memories (student_name, caption, memory_type, file_path, file_name, file_type, file_size)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        `);

        const insertedIds = [];
        const transaction = db.transaction(() => {
            files.forEach(file => {
                const fileType = getFileType(file.mimetype);
                const result = insert.run(
                    name.trim(),
                    caption.trim().substring(0, 500),
                    type,
                    file.filename,
                    file.originalname,
                    fileType,
                    file.size
                );
                insertedIds.push(result.lastInsertRowid);
            });
        });

        transaction();

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

/**
 * GET /api/memories
 * Get all approved memories for public display
 */
app.get('/api/memories', (req, res) => {
    try {
        const memories = db.prepare(`
            SELECT id, student_name, caption, memory_type, file_path, file_type, likes, created_at
            FROM memories
            WHERE approved = 1
            ORDER BY created_at DESC
        `).all();

        // Add full URL for files
        const memoriesWithUrls = memories.map(memory => ({
            ...memory,
            file_url: `/uploads/${memory.file_path}`
        }));

        res.json({
            success: true,
            memories: memoriesWithUrls,
            count: memories.length
        });

    } catch (error) {
        console.error('Get memories error:', error);
        res.status(500).json({ success: false, error: error.message });
    }
});

/**
 * POST /api/like/:id
 * Like a memory
 */
app.post('/api/like/:id', (req, res) => {
    try {
        const { id } = req.params;

        const memory = db.prepare('SELECT id, likes FROM memories WHERE id = ? AND approved = 1').get(id);
        if (!memory) {
            return res.status(404).json({ success: false, error: 'Memory not found' });
        }

        db.prepare('UPDATE memories SET likes = likes + 1 WHERE id = ?').run(id);

        const updated = db.prepare('SELECT likes FROM memories WHERE id = ?').get(id);

        res.json({
            success: true,
            likes: updated.likes
        });

    } catch (error) {
        console.error('Like error:', error);
        res.status(500).json({ success: false, error: error.message });
    }
});

/**
 * GET /api/stats
 * Get public statistics
 */
app.get('/api/stats', (req, res) => {
    try {
        const stats = db.prepare(`
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN approved = 1 THEN 1 ELSE 0 END) as approved,
                SUM(likes) as totalLikes
            FROM memories
        `).get();

        res.json({
            success: true,
            stats: {
                totalMemories: stats.approved || 0,
                totalLikes: stats.totalLikes || 0
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

/**
 * POST /api/admin/login
 * Admin login
 */
app.post('/api/admin/login', (req, res) => {
    try {
        const { password } = req.body;

        if (password !== ADMIN_PASSWORD) {
            console.log('❌ Failed admin login attempt');
            return res.status(401).json({ success: false, error: 'Invalid password' });
        }

        // Generate token
        const token = generateToken();
        const expiresAt = new Date(Date.now() + 24 * 60 * 60 * 1000); // 24 hours

        // Clean up old sessions
        db.prepare('DELETE FROM admin_sessions WHERE expires_at < datetime("now")').run();

        // Insert new session
        db.prepare('INSERT INTO admin_sessions (token, expires_at) VALUES (?, ?)').run(token, expiresAt.toISOString());

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

/**
 * POST /api/admin/verify
 * Verify admin token
 */
app.post('/api/admin/verify', (req, res) => {
    const token = req.headers.authorization?.replace('Bearer ', '');
    const isValid = validateAdminToken(token);
    res.json({ success: true, valid: isValid });
});

/**
 * GET /api/admin/memories
 * Get all memories (admin)
 */
app.get('/api/admin/memories', (req, res) => {
    try {
        const token = req.headers.authorization?.replace('Bearer ', '');
        if (!validateAdminToken(token)) {
            return res.status(401).json({ success: false, error: 'Unauthorized' });
        }

        const { filter, sort, search } = req.query;

        let query = 'SELECT * FROM memories WHERE 1=1';
        const params = [];

        // Filter
        if (filter === 'approved') {
            query += ' AND approved = 1';
        } else if (filter === 'pending') {
            query += ' AND approved = 0';
        }

        // Search
        if (search) {
            query += ' AND (student_name LIKE ? OR caption LIKE ?)';
            params.push(`%${search}%`, `%${search}%`);
        }

        // Sort
        if (sort === 'oldest') {
            query += ' ORDER BY created_at ASC';
        } else if (sort === 'likes') {
            query += ' ORDER BY likes DESC';
        } else {
            query += ' ORDER BY created_at DESC';
        }

        const memories = db.prepare(query).all(...params);

        // Calculate stats
        const allMemories = db.prepare('SELECT * FROM memories').all();
        const stats = {
            total: allMemories.length,
            approved: allMemories.filter(m => m.approved === 1).length,
            pending: allMemories.filter(m => m.approved === 0).length,
            totalSize: allMemories.reduce((sum, m) => sum + (m.file_size || 0), 0),
            totalSizeFormatted: formatFileSize(allMemories.reduce((sum, m) => sum + (m.file_size || 0), 0))
        };

        // Add URLs to memories
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

/**
 * POST /api/admin/approve/:id
 * Approve a memory
 */
app.post('/api/admin/approve/:id', (req, res) => {
    try {
        const token = req.headers.authorization?.replace('Bearer ', '');
        if (!validateAdminToken(token)) {
            return res.status(401).json({ success: false, error: 'Unauthorized' });
        }

        const { id } = req.params;

        const memory = db.prepare('SELECT id FROM memories WHERE id = ?').get(id);
        if (!memory) {
            return res.status(404).json({ success: false, error: 'Memory not found' });
        }

        db.prepare('UPDATE memories SET approved = 1 WHERE id = ?').run(id);

        console.log(`✅ Approved memory #${id}`);

        res.json({ success: true, message: 'Memory approved' });

    } catch (error) {
        console.error('Approve error:', error);
        res.status(500).json({ success: false, error: error.message });
    }
});

/**
 * POST /api/admin/approve-all
 * Approve all pending memories
 */
app.post('/api/admin/approve-all', (req, res) => {
    try {
        const token = req.headers.authorization?.replace('Bearer ', '');
        if (!validateAdminToken(token)) {
            return res.status(401).json({ success: false, error: 'Unauthorized' });
        }

        const result = db.prepare('UPDATE memories SET approved = 1 WHERE approved = 0').run();

        console.log(`✅ Approved ${result.changes} memories`);

        res.json({
            success: true,
            message: `Approved ${result.changes} memories`,
            count: result.changes
        });

    } catch (error) {
        console.error('Approve all error:', error);
        res.status(500).json({ success: false, error: error.message });
    }
});

/**
 * DELETE /api/admin/delete/:id
 * Delete a memory
 */
app.delete('/api/admin/delete/:id', (req, res) => {
    try {
        const token = req.headers.authorization?.replace('Bearer ', '');
        if (!validateAdminToken(token)) {
            return res.status(401).json({ success: false, error: 'Unauthorized' });
        }

        const { id } = req.params;

        const memory = db.prepare('SELECT file_path FROM memories WHERE id = ?').get(id);
        if (!memory) {
            return res.status(404).json({ success: false, error: 'Memory not found' });
        }

        // Delete file from disk
        const filePath = path.join(uploadsDir, memory.file_path);
        if (fs.existsSync(filePath)) {
            fs.unlinkSync(filePath);
        }

        // Delete from database
        db.prepare('DELETE FROM memories WHERE id = ?').run(id);

        console.log(`🗑️ Deleted memory #${id}`);

        res.json({ success: true, message: 'Memory deleted' });

    } catch (error) {
        console.error('Delete error:', error);
        res.status(500).json({ success: false, error: error.message });
    }
});

/**
 * GET /api/admin/download-all
 * Download all approved memories as ZIP
 */
app.get('/api/admin/download-all', (req, res) => {
    try {
        const token = req.query.token || req.headers.authorization?.replace('Bearer ', '');
        if (!validateAdminToken(token)) {
            return res.status(401).json({ success: false, error: 'Unauthorized' });
        }

        const memories = db.prepare('SELECT * FROM memories WHERE approved = 1').all();

        if (memories.length === 0) {
            return res.status(404).json({ success: false, error: 'No approved memories to download' });
        }

        const timestamp = new Date().toISOString().split('T')[0];
        const zipFilename = `cornerstone-memories-${timestamp}.zip`;

        res.attachment(zipFilename);
        res.setHeader('Content-Type', 'application/zip');

        const archive = archiver('zip', {
            zlib: { level: 5 } // Compression level
        });

        archive.on('error', (err) => {
            console.error('Archive error:', err);
            res.status(500).end();
        });

        archive.pipe(res);

        // Add files to archive
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

/**
 * POST /api/admin/logout
 * Admin logout
 */
app.post('/api/admin/logout', (req, res) => {
    try {
        const token = req.headers.authorization?.replace('Bearer ', '');
        if (token) {
            db.prepare('DELETE FROM admin_sessions WHERE token = ?').run(token);
        }
        res.json({ success: true, message: 'Logged out' });
    } catch (error) {
        res.status(500).json({ success: false, error: error.message });
    }
});

// ═══════════════════════════════════════════════════════════════════════════════
// SERVE FRONTEND
// ═══════════════════════════════════════════════════════════════════════════════

// Serve index.html for all routes (SPA style)
app.get('*', (req, res) => {
    res.sendFile(path.join(__dirname, 'index.html'));
});

// ═══════════════════════════════════════════════════════════════════════════════
// ERROR HANDLING
// ═══════════════════════════════════════════════════════════════════════════════

// Multer error handling
app.use((err, req, res, next) => {
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
        return res.status(400).json({ success: false, error: err.message });
    }

    if (err) {
        console.error('Server error:', err);
        return res.status(500).json({ success: false, error: err.message });
    }

    next();
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
    console.log(`🔐 Admin password: ${ADMIN_PASSWORD}`);
    console.log(`📊 Max upload size: ${MAX_TOTAL_SIZE / 1024 / 1024}MB total`);
    console.log('═══════════════════════════════════════════════════════════════════');
    console.log('');
});

// Graceful shutdown
process.on('SIGTERM', () => {
    console.log('🛑 SIGTERM received. Closing server...');
    db.close();
    process.exit(0);
});

process.on('SIGINT', () => {
    console.log('🛑 SIGINT received. Closing server...');
    db.close();
    process.exit(0);
});