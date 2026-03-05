#!/usr/bin/env python3
"""
fix_batch_nodupe.py - Adds a dedicated Admin Batch Upload endpoint that skips duplicate checks.
"""

import re

def patch_server():
    with open('server.js', 'r', encoding='utf-8') as f:
        content = f.read()

    modified = False

    admin_endpoint = """
// Admin Batch Upload (Skips duplicate checks, profanity filters, and time windows)
app.post('/api/admin/upload-batch', upload.array('files', MAX_FILES), checkTotalSize, (req, res) => {
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
"""
    if "'/api/admin/upload-batch'" not in content:
        # Insert it right before the // Edit memory metadata line
        target = "// Edit memory metadata"
        content = content.replace(target, admin_endpoint + '\n' + target)
        print("✅ Added Admin Batch Upload endpoint to server.js (Bypasses Duplicates)")
        modified = True
        
        with open('server.js', 'w', encoding='utf-8') as f:
            f.write(content)
    else:
        print("ℹ️ Admin Batch Upload endpoint already exists in server.js")


def patch_html():
    with open('index.html', 'r', encoding='utf-8') as f:
        content = f.read()

    modified = False

    # 1. ADD THE BUTTON IF MISSING
    target_btn = '<button class="admin-header-btn" id="btnExportCsv"'
    batch_btn = '<button class="admin-header-btn" onclick="openBatchUpload()" style="background:var(--accent-purple); border-color:var(--accent-purple);">Batch Upload</button>'
    
    if 'openBatchUpload()' not in content and target_btn in content:
        # Put it before export CSV
        content = content.replace(target_btn, batch_btn + '\n      ' + target_btn)
        print("✅ Added Batch Upload button to HTML")
        modified = True

    # 2. ADD THE MODAL IF MISSING
    target_modal_end = '<!-- Compilation Creator Modal -->'
    batch_modal_html = """
  <!-- Batch Upload Modal -->
  <div class="compilation-modal" id="batchUploadModal">
    <div class="compilation-modal-content" style="max-width: 600px;">
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:20px;">
        <h2 style="font-family:var(--font-display); color:var(--primary-gold);">Batch Upload</h2>
        <button class="admin-btn admin-btn-secondary" onclick="closeBatchUpload()">✕ Close</button>
      </div>
      
      <div class="mini-pill" style="margin-bottom: 20px; background: rgba(123, 45, 142, 0.3); border-color: var(--accent-purple);">
        Admin Upload: Skips duplicate checks, skips profanity filters.
      </div>

      <div class="form-group">
        <label>Student Name (or Event Name)</label>
        <input class="form-input" id="batchName" placeholder="e.g. Class Trip 2025" />
      </div>
      
      <div class="form-group">
        <label>Caption</label>
        <textarea class="form-textarea" id="batchCaption" placeholder="Shared caption for all photos..." rows="3"></textarea>
      </div>

      <div class="form-group">
        <label>Category</label>
        <select class="form-select" id="batchType">
          <option value="Funny">Funny</option>
          <option value="Emotional">Emotional</option>
          <option value="Friends" selected>Friends</option>
          <option value="Teachers">Teachers</option>
          <option value="Events">Events</option>
          <option value="Campus">Campus</option>
          <option value="Classroom">Classroom</option>
        </select>
      </div>

      <div class="form-group" style="margin-top: 20px; border: 2px dashed var(--glass-border); padding: 20px; text-align: center; border-radius: 12px; cursor: pointer;" onclick="document.getElementById('batchFiles').click()">
        <input type="file" id="batchFiles" multiple style="display: none;" onchange="updateBatchFileCount(this)" />
        <div style="font-size: 2rem; margin-bottom: 10px;">📂</div>
        <div id="batchFileLabel" style="color: var(--text-muted);">Click to select files</div>
      </div>

      <div class="form-group" style="margin-top: 15px;">
        <label style="display:flex; align-items:center; gap: 10px; cursor: pointer;">
          <input type="checkbox" id="batchAutoApprove" checked style="transform: scale(1.2);" />
          <span>Auto-approve immediately?</span>
        </label>
      </div>
      
      <div id="batchProgress" style="display:none; margin-top: 20px;">
        <div class="upload-progress-bar"><div class="upload-progress-fill" id="batchProgressFill" style="width:0%"></div></div>
        <div id="batchProgressText" style="text-align: center; font-size: 0.85rem; margin-top: 6px; color: var(--text-muted);">Uploading...</div>
      </div>

      <div style="display:flex; gap:15px; justify-content:flex-end; margin-top:25px;">
        <button class="btn btn-secondary" onclick="closeBatchUpload()">Cancel</button>
        <button class="btn btn-primary" id="btnStartBatch" onclick="submitBatchUpload()" style="background: var(--accent-purple); border-color: var(--accent-purple);">Start Upload</button>
      </div>
    </div>
  </div>
"""
    if 'id="batchUploadModal"' not in content:
        content = content.replace(target_modal_end, batch_modal_html + '\n  ' + target_modal_end)
        print("✅ Added Batch Upload Modal HTML")
        modified = True

    # 3. ADD OR REPLACE JAVASCRIPT
    new_js = """
  // ═══════════════════════════════════════════════════════════════════════════════
  // BATCH UPLOAD (ADMIN SECURE)
  // ═══════════════════════════════════════════════════════════════════════════════

  function openBatchUpload() {
    document.getElementById('batchUploadModal').classList.add('active');
    document.getElementById('batchName').value = '';
    document.getElementById('batchCaption').value = '';
    document.getElementById('batchType').value = 'Friends';
    document.getElementById('batchFiles').value = '';
    document.getElementById('batchFileLabel').textContent = 'Click to select files';
    document.getElementById('batchProgress').style.display = 'none';
    document.getElementById('btnStartBatch').disabled = false;
  }

  function closeBatchUpload() {
    document.getElementById('batchUploadModal').classList.remove('active');
  }

  function updateBatchFileCount(input) {
    const count = input.files ? input.files.length : 0;
    document.getElementById('batchFileLabel').textContent = count > 0 ? `${count} file(s) selected` : 'Click to select files';
  }

  async function submitBatchUpload() {
    const name = document.getElementById('batchName').value.trim();
    const caption = document.getElementById('batchCaption').value.trim();
    const type = document.getElementById('batchType').value;
    const fileInput = document.getElementById('batchFiles');
    const autoApprove = document.getElementById('batchAutoApprove').checked;

    if (!name) return showNotification('error', 'Name required', 'Please enter a name.');
    if (!caption) return showNotification('error', 'Caption required', 'Please enter a caption.');
    if (!fileInput.files || fileInput.files.length === 0) return showNotification('error', 'No files', 'Select at least one file.');

    const files = Array.from(fileInput.files);
    const total = files.length;
    let successCount = 0;
    
    document.getElementById('btnStartBatch').disabled = true;
    const progressDiv = document.getElementById('batchProgress');
    const fill = document.getElementById('batchProgressFill');
    const text = document.getElementById('batchProgressText');
    progressDiv.style.display = 'block';

    const CHUNK_SIZE = 5;
    for (let i = 0; i < total; i += CHUNK_SIZE) {
        const chunk = files.slice(i, i + CHUNK_SIZE);
        
        const fd = new FormData();
        fd.append('name', name);
        fd.append('caption', caption);
        fd.append('type', type);
        fd.append('autoApprove', autoApprove ? 'true' : 'false');
        
        chunk.forEach(f => fd.append('files', f));

        try {
            text.textContent = `Uploading batch ${Math.ceil((i+1)/CHUNK_SIZE)} of ${Math.ceil(total/CHUNK_SIZE)}...`;
            
            // Note: Calling the NEW Admin secure endpoint
            const res = await fetch(apiUrl('/api/admin/upload-batch'), {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${state.adminToken}` },
                body: fd
            });
            
            const data = await res.json();
            
            if (data.success) {
                successCount += (data.count || 0);
            } else {
                showNotification('error', 'Error in chunk', data.error);
            }
            
            const percent = Math.min(100, Math.round(((i + chunk.length) / total) * 100));
            fill.style.width = percent + '%';
            
        } catch (e) {
            console.error(e);
        }
    }
    
    showNotification('success', 'Batch Complete', `${successCount} uploaded successfully.`);
    closeBatchUpload();
    loadAdminMemories(true);
  }
"""
    # If the old submitBatchUpload exists, replace the whole block via regex
    if 'async function submitBatchUpload()' in content:
        content = re.sub(r'// ═══════════════════════════════════════════════════════════════════════════════\n\s*// BATCH UPLOAD.*?(?=\n  // ════|</script>)', new_js, content, flags=re.DOTALL)
        print("✅ Updated Batch Upload JavaScript in HTML to use Admin API")
        modified = True
    elif 'function openBatchUpload' not in content:
        # If it wasn't there at all, just inject it
        content = content.replace("</script>\n</body>", new_js + "\n</script>\n</body>")
        print("✅ Injected Batch Upload JavaScript into HTML")
        modified = True

    if modified:
        with open('index.html', 'w', encoding='utf-8') as f:
            f.write(content)
            
if __name__ == '__main__':
    patch_server()
    patch_html()
    print("\n🎉 DONE!")
    print("⚠️  ACTION REQUIRED:")
    print("   1. Stop your node server (Ctrl+C).")
    print("   2. Start your node server (node server.js).")
    print("   3. Hard refresh your browser (Ctrl+Shift+R).")