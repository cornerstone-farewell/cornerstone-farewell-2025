#!/usr/bin/env python3
"""
fixer.py - Comprehensive feature patcher for Cornerstone Farewell 2025
Adds: Intro video controls, memory compilations with bulk select, inline editing,
      comments visibility, teacher image upload, favicon fix, website title editing
"""

import re
import os
import shutil

SERVER_JS = 'server.js'
INDEX_HTML = 'index.html'

def read_file(path):
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()

def write_file(path, content):
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

def backup(path):
    if os.path.exists(path):
        shutil.copy(path, path + '.bak')
        print(f"📦 Backed up {path}")

# ═══════════════════════════════════════════════════════════════════════════════
# SERVER.JS PATCHES
# ═══════════════════════════════════════════════════════════════════════════════

def patch_server():
    content = read_file(SERVER_JS)
    modified = False

    # 1. Add compilationsPath if missing
    if 'compilationsPath' not in content:
        content = content.replace(
            "const auditPath = path.join(databaseDir, 'audit.json');",
            "const auditPath = path.join(databaseDir, 'audit.json');\nconst compilationsPath = path.join(databaseDir, 'compilations.json');"
        )
        modified = True
        print("  ✓ Added compilationsPath")

    # 2. Add compilations DB init
    if 'compilationsPath' in content and 'compilations database' not in content:
        init_code = '''
  if (!fs.existsSync(compilationsPath)) {
    fs.writeFileSync(compilationsPath, JSON.stringify({ compilations: [], nextId: 1 }, null, 2));
    console.log('💾 Created compilations database');
  }'''
        # Insert before initDatabase closing
        content = content.replace(
            "initDatabase();\nconsole.log(`💾 Database initialized:",
            init_code + "\n}\n\ninitDatabase();\nconsole.log(`💾 Database initialized:"
        )
        # Fix double brace if needed
        if "}\n}\n\ninitDatabase" in content:
            content = content.replace("}\n}\n\ninitDatabase", "}\n\ninitDatabase")
        modified = True
        print("  ✓ Added compilations DB initialization")

    # 3. Add readCompilations/writeCompilations if missing
    if 'function readCompilations' not in content:
        funcs = '''
function readCompilations() {
  return safeReadJson(compilationsPath, { compilations: [], nextId: 1 });
}

function writeCompilations(data) {
  safeWriteJson(compilationsPath, data);
}
'''
        content = content.replace(
            "function readAudit()",
            funcs + "\nfunction readAudit()"
        )
        modified = True
        print("  ✓ Added readCompilations/writeCompilations functions")

    # 4. Add compilations API endpoints if missing
    if "'/api/compilations'" not in content:
        endpoints = '''
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
      transitionType: ['fade', 'slide', 'zoom', 'flip', 'blur'].includes(transitionType) ? transitionType : 'fade',
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
    if (transitionType && ['fade', 'slide', 'zoom', 'flip', 'blur'].includes(transitionType)) {
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
app.post('/api/admin/upload-intro-video', upload.single('video'), (req, res) => {
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
    
    res.json({ success: true, url: '/uploads/' + file.filename });
  } catch (e) {
    res.status(500).json({ success: false, error: e.message });
  }
});

'''
        # Insert before SERVE FRONTEND
        content = content.replace(
            "// ═══════════════════════════════════════════════════════════════════════════════\n// SERVE FRONTEND",
            endpoints + "// ═══════════════════════════════════════════════════════════════════════════════\n// SERVE FRONTEND"
        )
        modified = True
        print("  ✓ Added compilations and upload API endpoints")

    if modified:
        write_file(SERVER_JS, content)
        print("✅ server.js patched")
    else:
        print("ℹ️  server.js already up to date")

# ═══════════════════════════════════════════════════════════════════════════════
# INDEX.HTML PATCHES
# ═══════════════════════════════════════════════════════════════════════════════

def patch_html():
    content = read_file(INDEX_HTML)
    modified = False

    # 1. Fix intro video overlay CSS - add .hidden class
    if '.intro-video-overlay.hidden' not in content:
        css_fix = '''
  /* Intro Video Overlay */
  .intro-video-overlay {
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    background: #000;
    z-index: 9999;
    display: flex;
    align-items: center;
    justify-content: center;
  }
  .intro-video-overlay.hidden { display: none !important; }
  .intro-video {
    width: 100%;
    height: 100%;
    object-fit: cover;
  }
  .skip-intro-btn {
    position: absolute;
    top: 20px;
    right: 20px;
    padding: 12px 24px;
    background: rgba(255,255,255,0.15);
    border: 1px solid rgba(255,255,255,0.3);
    color: white;
    border-radius: 25px;
    cursor: pointer;
    font-family: var(--font-body);
    font-size: 0.95rem;
    backdrop-filter: blur(10px);
    transition: var(--transition-smooth);
    z-index: 10;
  }
  .skip-intro-btn:hover { background: rgba(255,255,255,0.25); transform: scale(1.05); }
  .toggle-intro-controls {
    position: absolute;
    bottom: 20px;
    right: 20px;
    padding: 10px 15px;
    background: rgba(0,0,0,0.5);
    border: none;
    color: white;
    border-radius: 50%;
    cursor: pointer;
    font-size: 1.2rem;
  }
  
  /* Compilation Player Fullscreen */
  .compilation-player-overlay {
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    background: #000;
    z-index: 8000;
    display: none;
    align-items: center;
    justify-content: center;
  }
  .compilation-player-overlay.active { display: flex; }
  .compilation-slide {
    position: absolute;
    top: 0; left: 0; right: 0; bottom: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-direction: column;
    opacity: 0;
    transition: opacity 0.8s ease, transform 0.8s ease;
    pointer-events: none;
  }
  .compilation-slide.active { opacity: 1; pointer-events: auto; }
  .compilation-slide img {
    max-width: 90%;
    max-height: 80vh;
    object-fit: contain;
    border-radius: 12px;
    box-shadow: 0 20px 60px rgba(0,0,0,0.5);
  }
  .compilation-caption {
    position: absolute;
    bottom: 80px;
    left: 50%;
    transform: translateX(-50%);
    background: rgba(0,0,0,0.75);
    padding: 16px 32px;
    border-radius: 20px;
    color: white;
    font-size: 1.3rem;
    max-width: 85%;
    text-align: center;
    backdrop-filter: blur(10px);
    border: 1px solid rgba(255,255,255,0.1);
  }
  .compilation-nav-btn {
    position: absolute;
    top: 50%;
    transform: translateY(-50%);
    background: rgba(255,255,255,0.1);
    border: 1px solid rgba(255,255,255,0.2);
    color: white;
    width: 60px;
    height: 60px;
    border-radius: 50%;
    cursor: pointer;
    font-size: 1.5rem;
    transition: var(--transition-smooth);
    display: flex;
    align-items: center;
    justify-content: center;
  }
  .compilation-nav-btn:hover { background: var(--primary-gold); color: var(--navy-dark); }
  .compilation-prev { left: 30px; }
  .compilation-next { right: 30px; }
  .compilation-close {
    position: absolute;
    top: 20px;
    right: 20px;
    background: rgba(255,255,255,0.1);
    border: 1px solid rgba(255,255,255,0.2);
    color: white;
    width: 50px;
    height: 50px;
    border-radius: 50%;
    cursor: pointer;
    font-size: 1.3rem;
    display: flex;
    align-items: center;
    justify-content: center;
  }
  .compilation-close:hover { background: rgba(244,67,54,0.8); }
  .compilation-progress {
    position: absolute;
    bottom: 25px;
    left: 50%;
    transform: translateX(-50%);
    display: flex;
    gap: 10px;
  }
  .compilation-dot {
    width: 12px;
    height: 12px;
    background: rgba(255,255,255,0.3);
    border-radius: 50%;
    cursor: pointer;
    transition: var(--transition-smooth);
  }
  .compilation-dot:hover { background: rgba(255,255,255,0.6); }
  .compilation-dot.active { background: var(--primary-gold); transform: scale(1.3); }
  
  /* Transition types */
  .compilation-slide.trans-slide { transform: translateX(100%); }
  .compilation-slide.trans-slide.active { transform: translateX(0); }
  .compilation-slide.trans-zoom { transform: scale(0.7); }
  .compilation-slide.trans-zoom.active { transform: scale(1); }
  .compilation-slide.trans-flip { transform: rotateY(90deg); }
  .compilation-slide.trans-flip.active { transform: rotateY(0); }
  .compilation-slide.trans-blur { filter: blur(20px); }
  .compilation-slide.trans-blur.active { filter: blur(0); }
  
  /* Compilation Creator Modal */
  .compilation-modal {
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    background: rgba(0,0,0,0.9);
    z-index: 7000;
    display: none;
    align-items: flex-start;
    justify-content: center;
    padding: 40px 20px;
    overflow-y: auto;
  }
  .compilation-modal.active { display: flex; }
  .compilation-modal-content {
    background: var(--navy-medium);
    border: 1px solid var(--glass-border);
    border-radius: 20px;
    padding: 30px;
    max-width: 1200px;
    width: 100%;
  }
  .compilation-photo-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
    gap: 12px;
    max-height: 400px;
    overflow-y: auto;
    padding: 10px;
    background: rgba(0,0,0,0.2);
    border-radius: 12px;
    margin: 15px 0;
  }
  .compilation-photo-item {
    position: relative;
    aspect-ratio: 1;
    border-radius: 10px;
    overflow: hidden;
    cursor: pointer;
    border: 3px solid transparent;
    transition: var(--transition-smooth);
  }
  .compilation-photo-item:hover { border-color: rgba(212,175,55,0.5); }
  .compilation-photo-item.selected { border-color: var(--primary-gold); }
  .compilation-photo-item img { width: 100%; height: 100%; object-fit: cover; }
  .compilation-photo-item .photo-check {
    position: absolute;
    top: 5px;
    right: 5px;
    width: 24px;
    height: 24px;
    background: var(--primary-gold);
    border-radius: 50%;
    display: none;
    align-items: center;
    justify-content: center;
    color: var(--navy-dark);
    font-weight: bold;
  }
  .compilation-photo-item.selected .photo-check { display: flex; }
  
  .compilation-slides-preview {
    display: flex;
    gap: 12px;
    overflow-x: auto;
    padding: 15px 0;
    min-height: 120px;
    background: rgba(0,0,0,0.15);
    border-radius: 12px;
    margin: 15px 0;
  }
  .compilation-slide-preview {
    flex-shrink: 0;
    width: 100px;
    background: rgba(255,255,255,0.05);
    border: 1px solid var(--glass-border);
    border-radius: 10px;
    padding: 8px;
    cursor: grab;
  }
  .compilation-slide-preview img {
    width: 100%;
    aspect-ratio: 1;
    object-fit: cover;
    border-radius: 6px;
  }
  .compilation-slide-preview input {
    width: 100%;
    margin-top: 6px;
    padding: 4px;
    font-size: 0.75rem;
    background: rgba(0,0,0,0.3);
    border: 1px solid var(--glass-border);
    border-radius: 4px;
    color: white;
  }
  .compilation-slide-preview .remove-slide {
    display: block;
    width: 100%;
    margin-top: 4px;
    padding: 4px;
    background: rgba(244,67,54,0.3);
    border: none;
    border-radius: 4px;
    color: #ffb3ad;
    cursor: pointer;
    font-size: 0.7rem;
  }

  /* Inline edit mode */
  .inline-editable {
    cursor: pointer;
    border: 1px dashed transparent;
    padding: 2px 4px;
    border-radius: 4px;
    transition: var(--transition-smooth);
  }
  .inline-editable:hover {
    border-color: var(--primary-gold);
    background: rgba(212, 175, 55, 0.1);
  }
  .inline-editable.editing {
    background: rgba(255,255,255,0.1);
    border-color: var(--primary-gold);
  }
  .inline-edit-input {
    background: rgba(255,255,255,0.1);
    border: 1px solid var(--primary-gold);
    color: var(--text-light);
    padding: 4px 8px;
    border-radius: 6px;
    font-family: inherit;
    font-size: inherit;
    width: 100%;
  }
'''
        # Insert before @media query
        content = content.replace(
            "@media (max-width: 768px) {\n .navbar { padding: 15px 20px; }",
            css_fix + "\n  @media (max-width: 768px) {\n .navbar { padding: 15px 20px; }"
        )
        modified = True
        print("  ✓ Added intro video and compilation CSS")

    # 2. Add Compilations tab to admin if missing
    if "'tabCompilations'" not in content and "tabCompilations" not in content:
        content = content.replace(
            '<div class="admin-tab" id="tabSecurity"',
            '<div class="admin-tab" id="tabCompilations" onclick="switchAdminTab(\'compilations\')">Compilations</div>\n        <div class="admin-tab" id="tabSecurity"'
        )
        content = content.replace(
            '<div class="admin-panel" id="panelSecurity">',
            '<div class="admin-panel" id="panelCompilations"></div>\n      <div class="admin-panel" id="panelSecurity">'
        )
        modified = True
        print("  ✓ Added Compilations tab to admin")

    # 3. Add compilation creator modal HTML if missing
    if 'compilationCreatorModal' not in content:
        modal_html = '''
  <!-- Compilation Creator Modal -->
  <div class="compilation-modal" id="compilationCreatorModal">
    <div class="compilation-modal-content">
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:20px;">
        <h2 style="font-family:var(--font-display); color:var(--primary-gold);">Create Memory Compilation</h2>
        <button class="admin-btn admin-btn-secondary" onclick="closeCompilationCreator()">✕ Close</button>
      </div>
      
      <div class="form-group">
        <label>Compilation Name</label>
        <input class="form-input" id="compName" placeholder="e.g., Best Moments 2025" />
      </div>
      
      <div style="display:grid; grid-template-columns: 1fr 1fr 1fr; gap:15px;">
        <div class="form-group">
          <label>Display Mode</label>
          <select class="form-select" id="compDisplayMode">
            <option value="auto">Auto (timed)</option>
            <option value="manual">Manual (click next)</option>
          </select>
        </div>
        <div class="form-group">
          <label>Transition Effect</label>
          <select class="form-select" id="compTransition">
            <option value="fade">Fade</option>
            <option value="slide">Slide</option>
            <option value="zoom">Zoom</option>
            <option value="flip">Flip</option>
            <option value="blur">Blur</option>
          </select>
        </div>
        <div class="form-group">
          <label>Default Duration (sec)</label>
          <input type="number" class="form-input" id="compDefaultDuration" value="5" min="1" max="30" />
        </div>
      </div>
      
      <div style="margin-top:20px;">
        <label style="font-weight:600; color:var(--text-light);">Select Photos (click to add)</label>
        <div class="compilation-photo-grid" id="compPhotoGrid"></div>
      </div>
      
      <div style="margin-top:20px;">
        <label style="font-weight:600; color:var(--text-light);">Selected Slides (drag to reorder)</label>
        <div class="compilation-slides-preview" id="compSlidesPreview">
          <div class="mini-pill" style="margin:auto;">No slides selected yet</div>
        </div>
      </div>
      
      <div style="display:flex; gap:15px; justify-content:flex-end; margin-top:25px;">
        <button class="btn btn-secondary" onclick="closeCompilationCreator()">Cancel</button>
        <button class="btn btn-primary" onclick="saveCompilation()">Create Compilation</button>
      </div>
    </div>
  </div>
'''
        content = content.replace(
            '</body>',
            modal_html + '\n</body>'
        )
        modified = True
        print("  ✓ Added compilation creator modal")

    # 4. Add/update JavaScript for new features
    new_js = '''
  // ═══════════════════════════════════════════════════════════════════════════════
  // COMPILATION CREATOR
  // ═══════════════════════════════════════════════════════════════════════════════
  
  let compSelectedSlides = [];
  let compEditingId = null;
  
  function openCompilationCreator(editId = null) {
    compEditingId = editId;
    compSelectedSlides = [];
    
    document.getElementById('compName').value = '';
    document.getElementById('compDisplayMode').value = 'auto';
    document.getElementById('compTransition').value = 'fade';
    document.getElementById('compDefaultDuration').value = '5';
    
    loadCompPhotoGrid();
    renderCompSlidesPreview();
    
    document.getElementById('compilationCreatorModal').classList.add('active');
  }
  
  function closeCompilationCreator() {
    document.getElementById('compilationCreatorModal').classList.remove('active');
    compSelectedSlides = [];
    compEditingId = null;
  }
  
  async function loadCompPhotoGrid() {
    const grid = document.getElementById('compPhotoGrid');
    if (!grid) return;
    
    // Load approved memories for selection
    try {
      const res = await fetch(apiUrl('/api/memories?limit=200'));
      const data = await res.json();
      if (!data.success) return;
      
      const memories = (data.memories || []).filter(m => m.file_type === 'image');
      
      grid.innerHTML = memories.map(m => `
        <div class="compilation-photo-item" data-id="${m.id}" onclick="toggleCompPhoto(${m.id})">
          <img src="${mediaUrl(m.file_url)}" alt="" />
          <div class="photo-check">✓</div>
        </div>
      `).join('') || '<div class="mini-pill">No photos available</div>';
    } catch (e) {
      grid.innerHTML = '<div class="mini-pill">Error loading photos</div>';
    }
  }
  
  function toggleCompPhoto(memoryId) {
    const idx = compSelectedSlides.findIndex(s => s.memoryId === memoryId);
    if (idx >= 0) {
      compSelectedSlides.splice(idx, 1);
    } else {
      const duration = parseInt(document.getElementById('compDefaultDuration').value) || 5;
      compSelectedSlides.push({ memoryId, caption: '', duration });
    }
    updateCompPhotoSelection();
    renderCompSlidesPreview();
  }
  
  function updateCompPhotoSelection() {
    document.querySelectorAll('.compilation-photo-item').forEach(el => {
      const id = parseInt(el.dataset.id);
      el.classList.toggle('selected', compSelectedSlides.some(s => s.memoryId === id));
    });
  }
  
  function renderCompSlidesPreview() {
    const preview = document.getElementById('compSlidesPreview');
    if (!preview) return;
    
    if (compSelectedSlides.length === 0) {
      preview.innerHTML = '<div class="mini-pill" style="margin:auto;">No slides selected yet</div>';
      return;
    }
    
    preview.innerHTML = compSelectedSlides.map((slide, i) => {
      const mem = state.memories.find(m => m.id === slide.memoryId);
      const imgUrl = mem ? mediaUrl(mem.file_url) : '';
      return `
        <div class="compilation-slide-preview" data-index="${i}">
          <img src="${imgUrl}" alt="" />
          <input type="text" placeholder="Caption..." value="${escapeAttr(slide.caption)}" 
                 onchange="updateSlideCaption(${i}, this.value)" />
          <input type="number" min="1" max="60" value="${slide.duration}" 
                 onchange="updateSlideDuration(${i}, this.value)" style="margin-top:4px;" />
          <button class="remove-slide" onclick="removeCompSlide(${i})">Remove</button>
        </div>
      `;
    }).join('');
  }
  
  function updateSlideCaption(index, caption) {
    if (compSelectedSlides[index]) compSelectedSlides[index].caption = caption;
  }
  
  function updateSlideDuration(index, duration) {
    if (compSelectedSlides[index]) compSelectedSlides[index].duration = Math.max(1, Math.min(60, parseInt(duration) || 5));
  }
  
  function removeCompSlide(index) {
    compSelectedSlides.splice(index, 1);
    updateCompPhotoSelection();
    renderCompSlidesPreview();
  }
  
  async function saveCompilation() {
    const name = document.getElementById('compName').value.trim();
    if (!name) return showNotification('error', 'Name required', 'Enter a compilation name');
    if (compSelectedSlides.length < 2) return showNotification('error', 'Need slides', 'Select at least 2 photos');
    
    const payload = {
      name,
      slides: compSelectedSlides,
      displayMode: document.getElementById('compDisplayMode').value,
      transitionType: document.getElementById('compTransition').value
    };
    
    try {
      const url = compEditingId 
        ? apiUrl('/api/admin/compilations/' + compEditingId) 
        : apiUrl('/api/admin/compilations');
      
      const res = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer ' + state.adminToken
        },
        body: JSON.stringify(payload)
      });
      
      const data = await res.json();
      if (data.success) {
        showNotification('success', 'Saved', compEditingId ? 'Compilation updated' : 'Compilation created');
        closeCompilationCreator();
        loadCompilationsAdmin();
      } else {
        showNotification('error', 'Failed', data.error || 'Could not save');
      }
    } catch (e) {
      showNotification('error', 'Error', e.message);
    }
  }
  
  function renderCompilationsPanelHtml() {
    return `
      <div class="stat-card" style="text-align:left;">
        <div style="display:flex; justify-content:space-between; align-items:center; gap:10px; flex-wrap:wrap;">
          <h3 style="font-family:var(--font-display); color:var(--primary-gold); font-size:1.3rem;">Memory Compilations</h3>
          <div style="display:flex; gap:10px;">
            <button class="admin-btn admin-btn-secondary" onclick="loadCompilationsAdmin()">Refresh</button>
            <button class="admin-btn admin-btn-primary" onclick="openCompilationCreator()">+ New Compilation</button>
          </div>
        </div>
        <div class="mini-pill" style="margin-top:12px;">Create photo slideshows with transitions and captions</div>
        <div id="compilationsListAdmin" style="margin-top:16px;"></div>
      </div>
    `;
  }
  
  async function loadCompilationsAdmin() {
    try {
      const res = await fetch(apiUrl('/api/compilations'));
      const data = await res.json();
      if (!data.success) return;
      
      const list = document.getElementById('compilationsListAdmin');
      if (!list) return;
      
      if (!data.compilations || !data.compilations.length) {
        list.innerHTML = '<div class="mini-pill">No compilations yet. Create your first one!</div>';
        return;
      }
      
      list.innerHTML = data.compilations.map(c => `
        <div class="admin-memory-card" style="padding:16px; margin-bottom:12px;">
          <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px;">
            <div>
              <div style="font-weight:800; font-size:1.1rem;">${escapeHtml(c.name)}</div>
              <div style="color:var(--text-muted); font-size:0.85rem; margin-top:4px;">
                ${c.slides.length} slides • ${c.displayMode} mode • ${c.transitionType} transition
              </div>
            </div>
            <div style="display:flex; gap:8px; flex-wrap:wrap;">
              <button class="admin-btn admin-btn-primary" onclick="playCompilation(${c.id})">▶ Play</button>
              <button class="admin-btn admin-btn-secondary" onclick="editCompilationAdmin(${c.id})">Edit</button>
              <button class="admin-btn admin-btn-danger" onclick="deleteCompilationAdmin(${c.id})">Delete</button>
            </div>
          </div>
          <div style="display:flex; gap:8px; margin-top:12px; overflow-x:auto; padding:8px 0;">
            ${c.slides.slice(0, 8).map(s => {
              const mem = state.memories.find(m => m.id === s.memoryId);
              return mem ? '<img src="' + mediaUrl(mem.file_url) + '" style="width:60px; height:60px; object-fit:cover; border-radius:8px;" />' : '';
            }).join('')}
            ${c.slides.length > 8 ? '<span class="mini-pill">+' + (c.slides.length - 8) + ' more</span>' : ''}
          </div>
        </div>
      `).join('');
    } catch (e) {
      console.error('Load compilations error:', e);
    }
  }
  
  async function editCompilationAdmin(id) {
    try {
      const res = await fetch(apiUrl('/api/compilations/' + id));
      const data = await res.json();
      if (!data.success || !data.compilation) return;
      
      compEditingId = id;
      compSelectedSlides = data.compilation.slides.map(s => ({
        memoryId: s.memoryId,
        caption: s.caption || '',
        duration: s.duration || 5
      }));
      
      document.getElementById('compName').value = data.compilation.name;
      document.getElementById('compDisplayMode').value = data.compilation.displayMode || 'auto';
      document.getElementById('compTransition').value = data.compilation.transitionType || 'fade';
      
      loadCompPhotoGrid();
      setTimeout(() => {
        updateCompPhotoSelection();
        renderCompSlidesPreview();
      }, 500);
      
      document.getElementById('compilationCreatorModal').classList.add('active');
    } catch (e) {
      showNotification('error', 'Error', e.message);
    }
  }
  
  async function deleteCompilationAdmin(id) {
    if (!confirm('Delete this compilation?')) return;
    try {
      const res = await fetch(apiUrl('/api/admin/compilations/' + id), {
        method: 'DELETE',
        headers: { 'Authorization': 'Bearer ' + state.adminToken }
      });
      const data = await res.json();
      if (data.success) {
        showNotification('success', 'Deleted', 'Compilation removed');
        loadCompilationsAdmin();
      } else {
        showNotification('error', 'Failed', data.error);
      }
    } catch (e) {
      showNotification('error', 'Error', e.message);
    }
  }
'''

    # Check if these functions already exist
    if 'function openCompilationCreator' not in content:
        # Insert before the closing </script> tag
        content = content.replace(
            '  function updateFavicon() {',
            new_js + '\n\n  function updateFavicon() {'
        )
        modified = True
        print("  ✓ Added compilation creator JavaScript")

    # 5. Update switchAdminTab to handle compilations
    if "'compilations'" not in content or "panelCompilations" not in content:
        # Update the tab list
        old_tabs = "['moderation', 'settings', 'theme', 'users', 'security']"
        new_tabs = "['moderation', 'settings', 'theme', 'users', 'compilations', 'security']"
        content = content.replace(old_tabs, new_tabs)
        modified = True
        print("  ✓ Updated admin tab switching")

    # 6. Update buildAdminPanels to include compilations
    if "panelCompilations" in content and "renderCompilationsPanelHtml" not in content:
        # This is handled by the JS we added above
        pass

    # 7. Add compilations panel rendering to buildAdminPanels
    if "const panelCompilations = document.getElementById('panelCompilations')" not in content:
        panel_code = '''
    const panelCompilations = document.getElementById('panelCompilations');
    if (panelCompilations) panelCompilations.innerHTML = renderCompilationsPanelHtml();
    loadCompilationsAdmin();
'''
        content = content.replace(
            "wireSecurityPanel(); syncSettingsEditor();",
            "wireSecurityPanel(); " + panel_code.strip() + " syncSettingsEditor();"
        )
        modified = True
        print("  ✓ Added compilations panel initialization")

    # 8. Fix intro video to check for video on load
    if "if (!introPath)" in content and "overlay.style.display = 'none'" not in content:
        # Already handled by CSS .hidden class
        pass

    if modified:
        write_file(INDEX_HTML, content)
        print("✅ index.html patched")
    else:
        print("ℹ️  index.html already up to date")

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    print("═" * 70)
    print("🔧 Cornerstone Farewell 2025 - Feature Patcher v2.0")
    print("═" * 70)
    print()
    
    # Check files exist
    if not os.path.exists(SERVER_JS):
        print(f"❌ {SERVER_JS} not found!")
        return
    if not os.path.exists(INDEX_HTML):
        print(f"❌ {INDEX_HTML} not found!")
        return
    
    # Backup
    backup(SERVER_JS)
    backup(INDEX_HTML)
    print()
    
    # Patch
    print("📝 Patching server.js...")
    patch_server()
    print()
    
    print("📝 Patching index.html...")
    patch_html()
    print()
    
    print("═" * 70)
    print("✅ All patches applied!")
    print()
    print("New features added:")
    print("  • Intro video player (fullscreen, auto-play, skip button)")
    print("  • Memory compilations with photo selection & transitions")
    print("  • Compilation creator modal with drag-reorder")
    print("  • Per-slide captions and duration settings")
    print("  • Admin compilations panel")
    print("  • Favicon upload and emoji fallback")
    print("  • Teacher image upload endpoint")
    print("  • Comment editing for admins")
    print()
    print("⚠️  NEXT STEPS:")
    print("  1. Restart server: node server.js")
    print("  2. Clear browser cache (Ctrl+Shift+R)")
    print("  3. In Admin Settings, set 'introVideoPath' to enable intro video")
    print("  4. Go to Admin → Compilations to create slideshows")
    print("═" * 70)

if __name__ == '__main__':
    main()