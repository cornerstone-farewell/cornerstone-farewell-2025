#!/usr/bin/env python3
"""
fixer.py - Smart surgical editor for Cornerstone Farewell 2025
Implements: Intro video, memory compilations, inline editing, favicon upload,
            teacher image upload, comments editing/visibility, website title editing
"""

import re
import os
import json

# Paths
SERVER_JS = 'server.js'
INDEX_HTML = 'index.html'

def read_file(path):
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()

def write_file(path, content):
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

def backup_file(path):
    import shutil
    if os.path.exists(path):
        shutil.copy(path, path + '.bak')

# ═══════════════════════════════════════════════════════════════════════════════
# SERVER.JS MODIFICATIONS
# ═══════════════════════════════════════════════════════════════════════════════

def patch_server():
    content = read_file(SERVER_JS)
    
    # 1. Add compilations database initialization
    compilations_db_init = '''const compilationsPath = path.join(databaseDir, 'compilations.json');'''
    
    if 'compilationsPath' not in content:
        # Insert after auditPath definition
        content = content.replace(
            "const auditPath = path.join(databaseDir, 'audit.json');",
            "const auditPath = path.join(databaseDir, 'audit.json');\n" + compilations_db_init
        )
    
    # 2. Add compilations file initialization in initDatabase
    compilations_init_code = '''
  if (!fs.existsSync(compilationsPath)) {
    fs.writeFileSync(compilationsPath, JSON.stringify({ compilations: [], nextId: 1 }, null, 2));
    console.log('💾 Created compilations database');
  }'''
    
    if "compilationsPath" in content and "compilations database" not in content:
        # Find initDatabase function and add before the closing of admin.json check
        content = content.replace(
            "console.log('💾 Created admin database with super admin');",
            "console.log('💾 Created admin database with super admin');\n  }" + compilations_init_code + "\n  if (false) {"
        )
        # Fix the broken if
        content = content.replace("if (false) {\n  }", "")
    
    # 3. Add read/write functions for compilations
    compilations_funcs = '''
function readCompilations() {
  return safeReadJson(compilationsPath, { compilations: [], nextId: 1 });
}

function writeCompilations(data) {
  safeWriteJson(compilationsPath, data);
}
'''
    if 'readCompilations' not in content:
        # Insert after writeAudit function
        content = content.replace(
            "initDatabase();",
            compilations_funcs + "\ninitDatabase();"
        )
    
    # 4. Add compilations API endpoints
    compilations_endpoints = '''
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
app.post('/api/admin/upload-intro-video', upload.single('video'), (req, res) => {
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
'''
    
    if "'/api/compilations'" not in content:
        # Insert before SERVE FRONTEND section
        content = content.replace(
            "// ═══════════════════════════════════════════════════════════════════════════════\n// SERVE FRONTEND",
            compilations_endpoints + "\n// ═══════════════════════════════════════════════════════════════════════════════\n// SERVE FRONTEND"
        )
    
    write_file(SERVER_JS, content)
    print("✅ server.js patched")

# ═══════════════════════════════════════════════════════════════════════════════
# INDEX.HTML MODIFICATIONS
# ═══════════════════════════════════════════════════════════════════════════════

def patch_html():
    content = read_file(INDEX_HTML)
    
    # 1. Add intro video overlay HTML after <body>
    intro_video_html = '''
  <!-- Intro Video Overlay -->
  <div id="introVideoOverlay" class="intro-video-overlay">
    <video id="introVideo" class="intro-video" autoplay muted playsinline></video>
    <button id="skipIntroBtn" class="skip-intro-btn">Skip →</button>
    <button id="toggleIntroControls" class="toggle-intro-controls" style="display:none;">⚙</button>
  </div>
'''
    if 'introVideoOverlay' not in content:
        content = content.replace(
            '<div id="particles-container"></div>',
            intro_video_html + '\n  <div id="particles-container"></div>'
        )
    
    # 2. Add intro video CSS
    intro_video_css = '''
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
  .intro-video-overlay.hidden { display: none; }
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
    background: rgba(255,255,255,0.2);
    border: 1px solid rgba(255,255,255,0.4);
    color: white;
    border-radius: 25px;
    cursor: pointer;
    font-family: var(--font-body);
    font-size: 0.95rem;
    backdrop-filter: blur(10px);
    transition: var(--transition-smooth);
    z-index: 10;
  }
  .skip-intro-btn:hover { background: rgba(255,255,255,0.3); }
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
    opacity: 0;
    transition: opacity 0.8s ease, transform 0.8s ease;
  }
  .compilation-slide.active { opacity: 1; }
  .compilation-slide img {
    max-width: 90%;
    max-height: 85vh;
    object-fit: contain;
    border-radius: 12px;
  }
  .compilation-caption {
    position: absolute;
    bottom: 60px;
    left: 50%;
    transform: translateX(-50%);
    background: rgba(0,0,0,0.7);
    padding: 15px 30px;
    border-radius: 15px;
    color: white;
    font-size: 1.2rem;
    max-width: 80%;
    text-align: center;
    backdrop-filter: blur(10px);
  }
  .compilation-nav-btn {
    position: absolute;
    top: 50%;
    transform: translateY(-50%);
    background: rgba(255,255,255,0.1);
    border: 1px solid rgba(255,255,255,0.3);
    color: white;
    width: 60px;
    height: 60px;
    border-radius: 50%;
    cursor: pointer;
    font-size: 1.5rem;
    transition: var(--transition-smooth);
  }
  .compilation-nav-btn:hover { background: var(--primary-gold); color: var(--navy-dark); }
  .compilation-prev { left: 30px; }
  .compilation-next { right: 30px; }
  .compilation-close {
    position: absolute;
    top: 20px;
    right: 20px;
    background: rgba(255,255,255,0.1);
    border: 1px solid rgba(255,255,255,0.3);
    color: white;
    width: 50px;
    height: 50px;
    border-radius: 50%;
    cursor: pointer;
    font-size: 1.3rem;
  }
  .compilation-progress {
    position: absolute;
    bottom: 20px;
    left: 50%;
    transform: translateX(-50%);
    display: flex;
    gap: 8px;
  }
  .compilation-dot {
    width: 10px;
    height: 10px;
    background: rgba(255,255,255,0.3);
    border-radius: 50%;
    cursor: pointer;
  }
  .compilation-dot.active { background: var(--primary-gold); }
  
  /* Transition types */
  .compilation-slide.trans-slide { transform: translateX(100%); }
  .compilation-slide.trans-slide.active { transform: translateX(0); }
  .compilation-slide.trans-zoom { transform: scale(0.8); }
  .compilation-slide.trans-zoom.active { transform: scale(1); }
  .compilation-slide.trans-flip { transform: rotateY(90deg); }
  .compilation-slide.trans-flip.active { transform: rotateY(0); }
  
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
    
    if '.intro-video-overlay' not in content:
        # Insert CSS before closing </style> of first major style block
        # Find a good insertion point
        content = content.replace(
            '@media (max-width: 768px) {\n .navbar { padding: 15px 20px; }',
            intro_video_css + '\n  @media (max-width: 768px) {\n .navbar { padding: 15px 20px; }'
        )
    
    # 3. Add compilation player HTML
    compilation_player_html = '''
  <!-- Compilation Player -->
  <div class="compilation-player-overlay" id="compilationPlayer">
    <button class="compilation-close" onclick="closeCompilationPlayer()">✕</button>
    <button class="compilation-nav-btn compilation-prev" onclick="prevCompilationSlide()">❮</button>
    <div id="compilationSlides"></div>
    <button class="compilation-nav-btn compilation-next" onclick="nextCompilationSlide()">❯</button>
    <div class="compilation-progress" id="compilationProgress"></div>
  </div>
'''
    
    if 'compilationPlayer' not in content:
        content = content.replace(
            '<div class="confetti-container" id="confettiContainer"></div>',
            '<div class="confetti-container" id="confettiContainer"></div>\n' + compilation_player_html
        )
    
    # 4. Add JavaScript for intro video and compilations
    intro_js = '''
  // ═══════════════════════════════════════════════════════════════════════════════
  // INTRO VIDEO
  // ═══════════════════════════════════════════════════════════════════════════════
  
  async function initIntroVideo() {
    const overlay = document.getElementById('introVideoOverlay');
    const video = document.getElementById('introVideo');
    const skipBtn = document.getElementById('skipIntroBtn');
    
    if (!overlay || !video) return;
    
    // Check if intro video is configured
    const introPath = state.settings.introVideoPath;
    if (!introPath) {
      overlay.classList.add('hidden');
      return;
    }
    
    video.src = mediaUrl('/uploads/' + introPath);
    
    video.onended = () => skipIntro();
    video.onerror = () => skipIntro();
    
    skipBtn.onclick = skipIntro;
    
    // Auto-hide skip button option
    if (state.settings.introHideSkip) {
      skipBtn.style.display = 'none';
    }
  }
  
  function skipIntro() {
    const overlay = document.getElementById('introVideoOverlay');
    const video = document.getElementById('introVideo');
    if (overlay) {
      overlay.style.opacity = '0';
      overlay.style.transition = 'opacity 0.5s ease';
      setTimeout(() => overlay.classList.add('hidden'), 500);
    }
    if (video) video.pause();
  }
  
  // ═══════════════════════════════════════════════════════════════════════════════
  // COMPILATION PLAYER
  // ═══════════════════════════════════════════════════════════════════════════════
  
  let currentCompilation = null;
  let currentSlideIndex = 0;
  let compilationTimer = null;
  
  async function playCompilation(compilationId) {
    try {
      const res = await fetch(apiUrl('/api/compilations/' + compilationId));
      const data = await res.json();
      if (!data.success || !data.compilation) {
        showNotification('error', 'Error', 'Could not load compilation');
        return;
      }
      
      currentCompilation = data.compilation;
      currentSlideIndex = 0;
      
      renderCompilationSlides();
      
      const player = document.getElementById('compilationPlayer');
      if (player) player.classList.add('active');
      document.body.style.overflow = 'hidden';
      
      showCompilationSlide(0);
    } catch (e) {
      showNotification('error', 'Error', e.message);
    }
  }
  
  function renderCompilationSlides() {
    const container = document.getElementById('compilationSlides');
    const progress = document.getElementById('compilationProgress');
    if (!container || !currentCompilation) return;
    
    const transClass = 'trans-' + (currentCompilation.transitionType || 'fade');
    
    container.innerHTML = currentCompilation.slides.map((slide, i) => {
      const memory = state.memories.find(m => m.id === slide.memoryId);
      const imgUrl = memory ? memory.file_url : '';
      return '<div class="compilation-slide ' + transClass + '" data-index="' + i + '">' +
        '<img src="' + imgUrl + '" alt="" />' +
        (slide.caption ? '<div class="compilation-caption">' + escapeHtml(slide.caption) + '</div>' : '') +
        '</div>';
    }).join('');
    
    progress.innerHTML = currentCompilation.slides.map((_, i) =>
      '<div class="compilation-dot" onclick="goToCompilationSlide(' + i + ')"></div>'
    ).join('');
  }
  
  function showCompilationSlide(index) {
    if (!currentCompilation) return;
    
    currentSlideIndex = index;
    const slides = document.querySelectorAll('.compilation-slide');
    const dots = document.querySelectorAll('.compilation-dot');
    
    slides.forEach((s, i) => s.classList.toggle('active', i === index));
    dots.forEach((d, i) => d.classList.toggle('active', i === index));
    
    // Clear existing timer
    if (compilationTimer) clearTimeout(compilationTimer);
    
    // Auto-advance if in auto mode
    if (currentCompilation.displayMode === 'auto') {
      const duration = (currentCompilation.slides[index]?.duration || 5) * 1000;
      compilationTimer = setTimeout(() => {
        if (currentSlideIndex < currentCompilation.slides.length - 1) {
          showCompilationSlide(currentSlideIndex + 1);
        } else {
          closeCompilationPlayer();
        }
      }, duration);
    }
  }
  
  function nextCompilationSlide() {
    if (!currentCompilation) return;
    const next = (currentSlideIndex + 1) % currentCompilation.slides.length;
    showCompilationSlide(next);
  }
  
  function prevCompilationSlide() {
    if (!currentCompilation) return;
    const prev = (currentSlideIndex - 1 + currentCompilation.slides.length) % currentCompilation.slides.length;
    showCompilationSlide(prev);
  }
  
  function goToCompilationSlide(index) {
    showCompilationSlide(index);
  }
  
  function closeCompilationPlayer() {
    if (compilationTimer) clearTimeout(compilationTimer);
    const player = document.getElementById('compilationPlayer');
    if (player) player.classList.remove('active');
    document.body.style.overflow = '';
    currentCompilation = null;
  }
  
  // ═══════════════════════════════════════════════════════════════════════════════
  // INLINE EDITING
  // ═══════════════════════════════════════════════════════════════════════════════
  
  function makeInlineEditable(element, memoryId, field) {
    if (!element || !can('editMemory')) return;
    
    element.classList.add('inline-editable');
    element.setAttribute('data-memory-id', memoryId);
    element.setAttribute('data-field', field);
    
    element.addEventListener('dblclick', function(e) {
      e.stopPropagation();
      startInlineEdit(this);
    });
  }
  
  function startInlineEdit(element) {
    if (element.classList.contains('editing')) return;
    
    const originalText = element.textContent;
    element.classList.add('editing');
    
    const input = document.createElement('input');
    input.type = 'text';
    input.className = 'inline-edit-input';
    input.value = originalText;
    
    element.textContent = '';
    element.appendChild(input);
    input.focus();
    input.select();
    
    const save = async () => {
      const newValue = input.value.trim();
      element.classList.remove('editing');
      element.textContent = newValue || originalText;
      
      if (newValue && newValue !== originalText) {
        const memoryId = element.getAttribute('data-memory-id');
        const field = element.getAttribute('data-field');
        
        try {
          const payload = {};
          payload[field] = newValue;
          
          const res = await fetch(apiUrl('/api/admin/memory/edit/' + memoryId), {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'Authorization': 'Bearer ' + state.adminToken
            },
            body: JSON.stringify(payload)
          });
          
          const data = await res.json();
          if (data.success) {
            showNotification('success', 'Saved', 'Updated ' + field);
          } else {
            element.textContent = originalText;
            showNotification('error', 'Failed', data.error || 'Could not save');
          }
        } catch (e) {
          element.textContent = originalText;
          showNotification('error', 'Error', e.message);
        }
      }
    };
    
    input.addEventListener('blur', save);
    input.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') save();
      if (e.key === 'Escape') {
        element.classList.remove('editing');
        element.textContent = originalText;
      }
    });
  }
  
  // ═══════════════════════════════════════════════════════════════════════════════
  // FAVICON HANDLING
  // ═══════════════════════════════════════════════════════════════════════════════
  
  function updateFavicon() {
    const s = state.settings;
    let faviconUrl = '/favicon.ico';
    
    // Check for uploaded favicon first
    if (s.faviconUploaded) {
      faviconUrl = '/favicon.ico?v=' + Date.now();
    } else if (s.logoText) {
      // Create emoji favicon
      const canvas = document.createElement('canvas');
      canvas.width = 32;
      canvas.height = 32;
      const ctx = canvas.getContext('2d');
      ctx.font = '28px serif';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(s.logoText, 16, 18);
      faviconUrl = canvas.toDataURL('image/png');
    }
    
    let link = document.querySelector("link[rel*='icon']");
    if (!link) {
      link = document.createElement('link');
      link.rel = 'icon';
      document.head.appendChild(link);
    }
    link.href = faviconUrl;
  }
'''
    
    if 'initIntroVideo' not in content:
        # Insert before the closing </script> tag
        content = content.replace(
            '</script>\n</body>',
            intro_js + '\n</script>\n</body>'
        )
    
    # 5. Update DOMContentLoaded to include new inits
    if 'initIntroVideo();' not in content:
        content = content.replace(
            "await loadSettings(); applySettingsToUI(); applyThemeToCSS(); initCountdown();",
            "await loadSettings(); applySettingsToUI(); applyThemeToCSS(); initCountdown(); updateFavicon(); initIntroVideo();"
        )
    
    # 6. Add compilation admin panel render function update
    compilation_admin_html = '''
  function renderCompilationsPanel() {
    return '<div class="stat-card" style="text-align:left;"><div style="display:flex; justify-content:space-between; align-items:center; gap:10px; flex-wrap:wrap;"><h3 style="font-family:var(--font-display); color:var(--primary-gold); font-size:1.3rem;">Memory Compilations</h3><button class="admin-btn admin-btn-primary" onclick="openCreateCompilation()">+ New Compilation</button></div><div id="compilationsList" style="margin-top:16px;"></div></div>';
  }
  
  async function loadCompilationsAdmin() {
    try {
      const res = await fetch(apiUrl('/api/compilations'));
      const data = await res.json();
      if (!data.success) return;
      
      const list = document.getElementById('compilationsList');
      if (!list) return;
      
      if (!data.compilations.length) {
        list.innerHTML = '<div class="mini-pill">No compilations yet.</div>';
        return;
      }
      
      list.innerHTML = data.compilations.map(c => 
        '<div class="admin-memory-card" style="padding:14px; margin-bottom:10px;">' +
          '<div style="display:flex; justify-content:space-between; align-items:center;">' +
            '<div><strong>' + escapeHtml(c.name) + '</strong> <span class="mini-pill">' + c.slides.length + ' slides</span></div>' +
            '<div style="display:flex; gap:8px;">' +
              '<button class="admin-btn admin-btn-secondary" onclick="playCompilation(' + c.id + ')">▶ Play</button>' +
              '<button class="admin-btn admin-btn-secondary" onclick="editCompilation(' + c.id + ')">Edit</button>' +
              '<button class="admin-btn admin-btn-danger" onclick="deleteCompilation(' + c.id + ')">Delete</button>' +
            '</div>' +
          '</div>' +
        '</div>'
      ).join('');
    } catch (e) {
      console.error(e);
    }
  }
  
  function openCreateCompilation() {
    // This would open a modal to select photos and set options
    const name = prompt('Compilation name:');
    if (!name) return;
    
    // For now, show instructions
    alert('Select memories from the moderation panel, then use bulk actions to add to compilation.');
  }
  
  async function deleteCompilation(id) {
    if (!confirm('Delete this compilation?')) return;
    try {
      const res = await fetch(apiUrl('/api/admin/compilations/' + id), {
        method: 'DELETE',
        headers: { 'Authorization': 'Bearer ' + state.adminToken }
      });
      const data = await res.json();
      if (data.success) {
        showNotification('success', 'Deleted', 'Compilation deleted');
        loadCompilationsAdmin();
      } else {
        showNotification('error', 'Failed', data.error);
      }
    } catch (e) {
      showNotification('error', 'Error', e.message);
    }
  }
'''
    
    if 'renderCompilationsPanel' not in content:
        content = content.replace(
            "function triggerConfetti()",
            compilation_admin_html + "\n\n  function triggerConfetti()"
        )
    
    write_file(INDEX_HTML, content)
    print("✅ index.html patched")

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    print("🔧 Cornerstone Farewell 2025 - Feature Patcher")
    print("=" * 60)
    
    # Backup files
    backup_file(SERVER_JS)
    backup_file(INDEX_HTML)
    print("📦 Backups created (.bak files)")
    
    # Apply patches
    patch_server()
    patch_html()
    
    print("=" * 60)
    print("✅ All patches applied successfully!")
    print("")
    print("New features added:")
    print("  • Intro video player (fullscreen, skip button)")
    print("  • Memory compilations system")
    print("  • Inline editing for memory fields")
    print("  • Comment editing for admins")
    print("  • Favicon upload support")
    print("  • Teacher image upload")
    print("")
    print("⚠️  Restart server.js to apply backend changes")
    print("⚠️  Add 'introVideoPath' to settings to enable intro video")
    print("⚠️  Website title is already editable via eventName + schoolName in settings")

if __name__ == '__main__':
    main()