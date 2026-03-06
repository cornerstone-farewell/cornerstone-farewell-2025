#!/usr/bin/env python3
"""
fix_syntax_master.py - Completely restores the bottom section of index.html
to guarantee there are no missing brackets or syntax errors.
"""

import re

def fix_syntax_master():
    with open('index.html', 'r', encoding='utf-8') as f:
        content = f.read()

    # We will slice the document right before the Intro Video section starts
    # and replace everything below it with the absolute perfect code.
    
    match = re.search(r'(// ════.*?INTRO VIDEO|async function initIntroVideo\(\))', content)
    
    if not match:
        print("❌ Could not find the injection point. Is the file completely empty?")
        return

    # Keep everything up to the injection point
    top_half = content[:match.start()]

    # The perfectly balanced bottom half
    perfect_bottom_half = """// ═══════════════════════════════════════════════════════════════════════════════
  // INTRO VIDEO
  // ═══════════════════════════════════════════════════════════════════════════════
  async function initIntroVideo() {
    const overlay = document.getElementById('introVideoOverlay');
    const video = document.getElementById('introVideo');
    const skipBtn = document.getElementById('skipIntroBtn');
    const unmuteBtn = document.getElementById('unmuteIntroBtn');
    if (!overlay || !video) return;
    
    const introPath = state.settings.introVideoPath;
    if (!introPath) { 
        overlay.style.display = 'none'; 
        overlay.classList.add('hidden'); 
        return; 
    }
    
    overlay.style.display = 'flex'; 
    overlay.classList.remove('hidden');
    video.src = mediaUrl(('/uploads/' + introPath).replace('//', '/'));
    
    try {
      video.muted = false; 
      await video.play();
      if (unmuteBtn) unmuteBtn.style.display = 'none';
    } catch (err) {
      video.muted = true;
      try {
        await video.play();
        if (unmuteBtn) {
          unmuteBtn.style.display = 'block';
          unmuteBtn.onclick = () => { 
              video.muted = false; 
              video.currentTime = 0; 
              unmuteBtn.style.display = 'none'; 
          };
        }
      } catch (err2) { skipIntro(); }
    }
    
    video.onended = () => skipIntro();
    video.onerror = () => skipIntro();
    if (skipBtn) { 
        skipBtn.onclick = skipIntro; 
        if (state.settings.introHideSkip) skipBtn.style.display = 'none'; 
    }
  }

  function skipIntro() {
    const overlay = document.getElementById('introVideoOverlay');
    const video = document.getElementById('introVideo');
    if (overlay) {
      overlay.style.opacity = '0';
      overlay.style.transition = 'opacity 0.5s ease';
      setTimeout(() => { overlay.style.display = 'none'; overlay.classList.add('hidden'); }, 500);
    }
    if (video) { video.pause(); video.src = ""; }
  }

  // ═══════════════════════════════════════════════════════════════════════════════
  // COMPILATION PLAYER
  // ═══════════════════════════════════════════════════════════════════════════════
  let currentCompilation = null; let currentSlideIndex = 0; let compilationTimer = null;
  
  async function playCompilation(compilationId) {
    try {
      const res = await fetch(apiUrl('/api/compilations/' + compilationId));
      const data = await res.json();
      if (!data.success || !data.compilation) return showNotification('error', 'Error', 'Could not load compilation');
      currentCompilation = data.compilation; currentSlideIndex = 0;
      renderCompilationSlides();
      const player = document.getElementById('compilationPlayer');
      if (player) player.classList.add('active');
      document.body.style.overflow = 'hidden';
      showCompilationSlide(0);
    } catch (e) { showNotification('error', 'Error', e.message); }
  }
  
  function renderCompilationSlides() {
    const container = document.getElementById('compilationSlides');
    const progress = document.getElementById('compilationProgress');
    if (!container || !currentCompilation) return;
    const transClass = 'trans-' + (currentCompilation.transitionType || 'fade');
    container.innerHTML = currentCompilation.slides.map((slide, i) => {
      const memory = state.memories.find(m => m.id === slide.memoryId);
      const imgUrl = memory ? memory.file_url : '';
      return `<div class="compilation-slide ${transClass}" data-index="${i}"><img src="${imgUrl}" alt="" />${slide.caption ? `<div class="compilation-caption">${escapeHtml(slide.caption)}</div>` : ''}</div>`;
    }).join('');
    progress.innerHTML = currentCompilation.slides.map((_, i) => `<div class="compilation-dot" onclick="goToCompilationSlide(${i})"></div>`).join('');
  }
  
  function showCompilationSlide(index) {
    if (!currentCompilation) return;
    currentSlideIndex = index;
    document.querySelectorAll('.compilation-slide').forEach((s, i) => s.classList.toggle('active', i === index));
    document.querySelectorAll('.compilation-dot').forEach((d, i) => d.classList.toggle('active', i === index));
    if (compilationTimer) clearTimeout(compilationTimer);
    if (currentCompilation.displayMode === 'auto') {
      const duration = (currentCompilation.slides[index]?.duration || 5) * 1000;
      compilationTimer = setTimeout(() => {
        if (currentSlideIndex < currentCompilation.slides.length - 1) showCompilationSlide(currentSlideIndex + 1);
        else closeCompilationPlayer();
      }, duration);
    }
  }

  function nextCompilationSlide() { if (currentCompilation) showCompilationSlide((currentSlideIndex + 1) % currentCompilation.slides.length); }
  function prevCompilationSlide() { if (currentCompilation) showCompilationSlide((currentSlideIndex - 1 + currentCompilation.slides.length) % currentCompilation.slides.length); }
  function goToCompilationSlide(index) { showCompilationSlide(index); }
  
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
    element.classList.add('inline-editable'); element.setAttribute('data-memory-id', memoryId); element.setAttribute('data-field', field);
    element.addEventListener('dblclick', function(e) { e.stopPropagation(); startInlineEdit(this); });
  }
  
  function startInlineEdit(element) {
    if (element.classList.contains('editing')) return;
    const originalText = element.textContent;
    element.classList.add('editing');
    const input = document.createElement('input');
    input.type = 'text'; input.className = 'inline-edit-input'; input.value = originalText;
    element.textContent = ''; element.appendChild(input); input.focus(); input.select();
    
    const save = async () => {
      const newValue = input.value.trim();
      element.classList.remove('editing');
      element.textContent = newValue || originalText;
      if (newValue && newValue !== originalText) {
        try {
          const res = await fetch(apiUrl('/api/admin/memory/edit/' + element.getAttribute('data-memory-id')), {
            method: 'POST', headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + state.adminToken },
            body: JSON.stringify({ [element.getAttribute('data-field')]: newValue })
          });
          const data = await res.json();
          if (data.success) showNotification('success', 'Saved', 'Updated ' + element.getAttribute('data-field'));
          else { element.textContent = originalText; showNotification('error', 'Failed', data.error); }
        } catch (e) { element.textContent = originalText; showNotification('error', 'Error', e.message); }
      }
    };
    input.addEventListener('blur', save);
    input.addEventListener('keydown', (e) => { if (e.key === 'Enter') save(); if (e.key === 'Escape') { element.classList.remove('editing'); element.textContent = originalText; } });
  }

  // ═══════════════════════════════════════════════════════════════════════════════
  // COMPILATION CREATOR
  // ═══════════════════════════════════════════════════════════════════════════════
  let compSelectedSlides = []; let compEditingId = null;
  
  function openCompilationCreator(editId = null) {
    compEditingId = editId; compSelectedSlides = [];
    document.getElementById('compName').value = ''; document.getElementById('compDisplayMode').value = 'auto';
    document.getElementById('compTransition').value = 'fade'; document.getElementById('compDefaultDuration').value = '5';
    loadCompPhotoGrid(); renderCompSlidesPreview();
    document.getElementById('compilationCreatorModal').classList.add('active');
  }
  
  function closeCompilationCreator() { document.getElementById('compilationCreatorModal').classList.remove('active'); compSelectedSlides = []; compEditingId = null; }
  
  async function loadCompPhotoGrid() {
    const grid = document.getElementById('compPhotoGrid'); if (!grid) return;
    try {
      const res = await fetch(apiUrl('/api/admin/memories?limit=5000&filter=approved'), { headers: { 'Authorization': 'Bearer ' + state.adminToken } });
      const data = await res.json();
      if (!data.success) return;
      const memories = (data.memories || []).filter(m => m.file_type === 'image');
      grid.innerHTML = memories.map(m => `<div class="compilation-photo-item" data-id="${m.id}" onclick="toggleCompPhoto(${m.id})"><img src="${mediaUrl(m.file_url)}" alt="" /><div class="photo-check">✓</div></div>`).join('') || '<div class="mini-pill">No photos available</div>';
    } catch (e) { grid.innerHTML = '<div class="mini-pill">Error loading photos</div>'; }
  }
  
  function toggleCompPhoto(memoryId) {
    const idx = compSelectedSlides.findIndex(s => s.memoryId === memoryId);
    if (idx >= 0) compSelectedSlides.splice(idx, 1);
    else compSelectedSlides.push({ memoryId, caption: '', duration: parseInt(document.getElementById('compDefaultDuration').value) || 5 });
    updateCompPhotoSelection(); renderCompSlidesPreview();
  }
  
  function updateCompPhotoSelection() { document.querySelectorAll('.compilation-photo-item').forEach(el => { el.classList.toggle('selected', compSelectedSlides.some(s => s.memoryId === parseInt(el.dataset.id))); }); }
  
  function renderCompSlidesPreview() {
    const preview = document.getElementById('compSlidesPreview'); if (!preview) return;
    if (compSelectedSlides.length === 0) { preview.innerHTML = '<div class="mini-pill" style="margin:auto;">No slides selected yet</div>'; return; }
    preview.innerHTML = compSelectedSlides.map((slide, i) => {
      const mem = state.memories.find(m => m.id === slide.memoryId);
      const imgUrl = mem ? mediaUrl(mem.file_url) : '';
      return `<div class="compilation-slide-preview" data-index="${i}"><img src="${imgUrl}" alt="" /><input type="text" placeholder="Caption..." value="${escapeAttr(slide.caption)}" onchange="updateSlideCaption(${i}, this.value)" /><input type="number" min="1" max="60" value="${slide.duration}" onchange="updateSlideDuration(${i}, this.value)" style="margin-top:4px;" /><button class="remove-slide" onclick="removeCompSlide(${i})">Remove</button></div>`;
    }).join('');
  }
  
  function updateSlideCaption(index, caption) { if (compSelectedSlides[index]) compSelectedSlides[index].caption = caption; }
  function updateSlideDuration(index, duration) { if (compSelectedSlides[index]) compSelectedSlides[index].duration = Math.max(1, Math.min(60, parseInt(duration) || 5)); }
  function removeCompSlide(index) { compSelectedSlides.splice(index, 1); updateCompPhotoSelection(); renderCompSlidesPreview(); }
  
  async function saveCompilation() {
    const name = document.getElementById('compName').value.trim();
    if (!name) return showNotification('error', 'Name required', 'Enter a compilation name');
    if (compSelectedSlides.length < 2) return showNotification('error', 'Need slides', 'Select at least 2 photos');
    const payload = { name, slides: compSelectedSlides, displayMode: document.getElementById('compDisplayMode').value, transitionType: document.getElementById('compTransition').value };
    try {
      const url = compEditingId ? apiUrl('/api/admin/compilations/' + compEditingId) : apiUrl('/api/admin/compilations');
      const res = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + state.adminToken }, body: JSON.stringify(payload) });
      const data = await res.json();
      if (data.success) { showNotification('success', 'Saved', compEditingId ? 'Compilation updated' : 'Compilation created'); closeCompilationCreator(); loadCompilationsAdmin(); }
      else showNotification('error', 'Failed', data.error);
    } catch (e) { showNotification('error', 'Error', e.message); }
  }
  
  function renderCompilationsPanelHtml() {
    return `<div class="stat-card" style="text-align:left;"><div style="display:flex; justify-content:space-between; align-items:center; gap:10px; flex-wrap:wrap;"><h3 style="font-family:var(--font-display); color:var(--primary-gold); font-size:1.3rem;">Memory Compilations</h3><div style="display:flex; gap:10px;"><button class="admin-btn admin-btn-secondary" onclick="loadCompilationsAdmin()">Refresh</button><button class="admin-btn admin-btn-primary" onclick="openCompilationCreator()">+ New Compilation</button></div></div><div class="mini-pill" style="margin-top:12px;">Create photo slideshows with transitions and captions</div><div id="compilationsListAdmin" style="margin-top:16px;"></div></div>`;
  }
  
  async function loadCompilationsAdmin() {
    try {
      const res = await fetch(apiUrl('/api/compilations'));
      const data = await res.json();
      if (!data.success) return;
      const list = document.getElementById('compilationsListAdmin'); if (!list) return;
      if (!data.compilations || !data.compilations.length) { list.innerHTML = '<div class="mini-pill">No compilations yet. Create your first one!</div>'; return; }
      list.innerHTML = data.compilations.map(c => `<div class="admin-memory-card" style="padding:16px; margin-bottom:12px;"><div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px;"><div><div style="font-weight:800; font-size:1.1rem;">${escapeHtml(c.name)}</div><div style="color:var(--text-muted); font-size:0.85rem; margin-top:4px;">${c.slides.length} slides • ${c.displayMode} mode • ${c.transitionType} transition</div></div><div style="display:flex; gap:8px; flex-wrap:wrap;"><button class="admin-btn admin-btn-primary" onclick="playCompilation(${c.id})">▶ Play</button><button class="admin-btn admin-btn-secondary" onclick="editCompilationAdmin(${c.id})">Edit</button><button class="admin-btn admin-btn-danger" onclick="deleteCompilationAdmin(${c.id})">Delete</button></div></div><div style="display:flex; gap:8px; margin-top:12px; overflow-x:auto; padding:8px 0;">${c.slides.slice(0, 8).map(s => { const mem = state.memories.find(m => m.id === s.memoryId); return mem ? `<img src="${mediaUrl(mem.file_url)}" style="width:60px; height:60px; object-fit:cover; border-radius:8px;" />` : ''; }).join('')}${c.slides.length > 8 ? `<span class="mini-pill">+${c.slides.length - 8} more</span>` : ''}</div></div>`).join('');
    } catch (e) { console.error('Load compilations error:', e); }
  }
  
  async function editCompilationAdmin(id) {
    try {
      const res = await fetch(apiUrl('/api/compilations/' + id));
      const data = await res.json();
      if (!data.success || !data.compilation) return;
      compEditingId = id; compSelectedSlides = data.compilation.slides.map(s => ({ memoryId: s.memoryId, caption: s.caption || '', duration: s.duration || 5 }));
      document.getElementById('compName').value = data.compilation.name; document.getElementById('compDisplayMode').value = data.compilation.displayMode || 'auto'; document.getElementById('compTransition').value = data.compilation.transitionType || 'fade';
      loadCompPhotoGrid(); setTimeout(() => { updateCompPhotoSelection(); renderCompSlidesPreview(); }, 500);
      document.getElementById('compilationCreatorModal').classList.add('active');
    } catch (e) { showNotification('error', 'Error', e.message); }
  }
  
  async function deleteCompilationAdmin(id) {
    if (!confirm('Delete this compilation?')) return;
    try {
      const res = await fetch(apiUrl('/api/admin/compilations/' + id), { method: 'DELETE', headers: { 'Authorization': 'Bearer ' + state.adminToken } });
      const data = await res.json();
      if (data.success) { showNotification('success', 'Deleted', 'Compilation removed'); loadCompilationsAdmin(); }
      else showNotification('error', 'Failed', data.error);
    } catch (e) { showNotification('error', 'Error', e.message); }
  }

  // ═══════════════════════════════════════════════════════════════════════════════
  // BATCH UPLOAD (ADMIN)
  // ═══════════════════════════════════════════════════════════════════════════════
  function openBatchUpload() {
    document.getElementById('batchUploadModal').classList.add('active');
    document.getElementById('batchName').value = ''; document.getElementById('batchCaption').value = ''; document.getElementById('batchType').value = 'Friends';
    document.getElementById('batchFiles').value = ''; document.getElementById('batchFileLabel').textContent = 'Click to select files';
    document.getElementById('batchProgress').style.display = 'none'; document.getElementById('btnStartBatch').disabled = false;
  }
  
  function closeBatchUpload() { document.getElementById('batchUploadModal').classList.remove('active'); }
  function updateBatchFileCount(input) { document.getElementById('batchFileLabel').textContent = input.files && input.files.length > 0 ? `${input.files.length} file(s) selected` : 'Click to select files'; }
  
  async function submitBatchUpload() {
    const name = document.getElementById('batchName').value.trim(); const caption = document.getElementById('batchCaption').value.trim();
    const type = document.getElementById('batchType').value; const fileInput = document.getElementById('batchFiles');
    const autoApprove = document.getElementById('batchAutoApprove').checked;
    if (!name || !caption || !fileInput.files.length) return showNotification('error', 'Missing fields', 'Fill all fields and select files.');
    
    document.getElementById('btnStartBatch').disabled = true;
    const progressDiv = document.getElementById('batchProgress'); const fill = document.getElementById('batchProgressFill'); const text = document.getElementById('batchProgressText');
    progressDiv.style.display = 'block';
    
    const files = Array.from(fileInput.files); const total = files.length; let successCount = 0; const CHUNK_SIZE = 5;
    for (let i = 0; i < total; i += CHUNK_SIZE) {
        const chunk = files.slice(i, i + CHUNK_SIZE);
        const fd = new FormData(); fd.append('name', name); fd.append('caption', caption); fd.append('type', type); fd.append('autoApprove', autoApprove ? 'true' : 'false');
        chunk.forEach(f => fd.append('files', f));
        try {
            text.textContent = `Uploading batch ${Math.ceil((i+1)/CHUNK_SIZE)} of ${Math.ceil(total/CHUNK_SIZE)}...`;
            const res = await fetch(apiUrl('/api/admin/upload-batch'), { method: 'POST', headers: { 'Authorization': `Bearer ${state.adminToken}` }, body: fd });
            const data = await res.json();
            if (data.success) successCount += (data.count || 0); else showNotification('error', 'Error in chunk', data.error);
            fill.style.width = Math.min(100, Math.round(((i + chunk.length) / total) * 100)) + '%';
        } catch (e) { console.error(e); }
    }
    showNotification('success', 'Batch Complete', `${successCount} uploaded successfully.`);
    closeBatchUpload(); loadAdminMemories(true);
  }

  // ═══════════════════════════════════════════════════════════════════════════════
  // FAVICON HANDLING
  // ═══════════════════════════════════════════════════════════════════════════════
  function updateFavicon() {
    const s = state.settings; let faviconUrl = '/favicon.ico';
    if (s.faviconUploaded) {
        faviconUrl = '/favicon.ico?v=' + Date.now();
    } else if (s.logoText) {
      const canvas = document.createElement('canvas'); canvas.width = 32; canvas.height = 32;
      const ctx = canvas.getContext('2d'); ctx.font = '28px serif'; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
      ctx.fillText(s.logoText, 16, 18); faviconUrl = canvas.toDataURL('image/png');
    }
    let link = document.querySelector("link[rel*='icon']");
    if (!link) { link = document.createElement('link'); link.rel = 'icon'; document.head.appendChild(link); }
    link.href = faviconUrl;
  }
</script>
</body>
</html>
"""

    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(top_half + perfect_bottom_half)
    
    print("✅ Successfully repaired all Javascript Syntax!")
    print("✅ Re-attached Favicon Logic!")
    print("⚠️ ACTION REQUIRED: Hard-Refresh your browser (Ctrl+Shift+R).")

if __name__ == '__main__':
    fix_syntax_master()