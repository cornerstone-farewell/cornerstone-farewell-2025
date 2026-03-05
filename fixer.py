#!/usr/bin/env python3
"""
add_hash_reset.py - Adds a feature to reset/scramble existing file hashes 
to allow re-uploading of duplicate files.
"""

def patch_server():
    with open('server.js', 'r', encoding='utf-8') as f:
        content = f.read()

    modified = False

    # Define the new endpoint
    reset_endpoint = """
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
"""

    if '/api/admin/reset-hashes' not in content:
        # Insert before the purge endpoint
        target = "app.delete('/api/admin/purge/:id'"
        if target in content:
            content = content.replace(target, reset_endpoint + '\n' + target)
            print("✅ Added '/api/admin/reset-hashes' endpoint to server.js")
            modified = True
            
            with open('server.js', 'w', encoding='utf-8') as f:
                f.write(content)

def patch_html():
    with open('index.html', 'r', encoding='utf-8') as f:
        content = f.read()

    modified = False

    # 1. Add the Reset Button to the Security Panel
    # We look for the closing div of the security panel content
    target_panel = '<div class="form-group"><label>&nbsp;</label><button class="btn btn-primary" style="width:100%;" onclick="changeAdminPassword()">Change</button></div></div></div>'
    
    new_ui = """<div class="form-group"><label>&nbsp;</label><button class="btn btn-primary" style="width:100%;" onclick="changeAdminPassword()">Change</button></div></div>
    
    <div style="margin-top: 25px; border-top: 1px solid var(--glass-border); padding-top: 20px;">
        <h4 style="font-family:var(--font-display); color:var(--error-red); margin-bottom:10px;">Danger Zone</h4>
        <div style="background: rgba(244, 67, 54, 0.1); border: 1px solid rgba(244, 67, 54, 0.3); padding: 15px; border-radius: 12px;">
            <div style="font-weight: bold; color: #ffb3ad; margin-bottom: 5px;">Reset Duplicate Detection</div>
            <p style="font-size: 0.85rem; color: var(--text-muted); margin-bottom: 12px;">
                This modifies the database so previously uploaded files are no longer considered duplicates. 
                Use this if you need to re-upload files that were deleted or rejected.
            </p>
            <button class="admin-btn admin-btn-danger" style="width:100%; justify-content:center;" onclick="resetUploadHashes()">
                ♻️ Reset All Upload Hashes
            </button>
        </div>
    </div>
    </div>"""

    if "Reset All Upload Hashes" not in content and target_panel in content:
        content = content.replace(target_panel, new_ui)
        print("✅ Added Reset Hashes UI to Security Panel")
        modified = True

    # 2. Add the JavaScript function
    js_code = """
    async function resetUploadHashes() {
      if (!confirm("Are you sure? This allows ALL existing files to be re-uploaded as duplicates.")) return;
      
      try {
        const res = await fetch(apiUrl('/api/admin/reset-hashes'), {
          method: 'POST',
          headers: { 'Authorization': `Bearer ${state.adminToken}` }
        });
        const data = await res.json();
        
        if (data.success) {
          showNotification('success', 'Reset Complete', `Cleared hashes for ${data.count} memories.`);
        } else {
          showNotification('error', 'Failed', data.error);
        }
      } catch (e) {
        showNotification('error', 'Error', e.message);
      }
    }
    """

    if "async function resetUploadHashes" not in content:
        content = content.replace("</script>", js_code + "\n</script>")
        print("✅ Added Reset Hashes JavaScript")
        modified = True

    if modified:
        with open('index.html', 'w', encoding='utf-8') as f:
            f.write(content)

if __name__ == '__main__':
    patch_server()
    patch_html()
    print("\n🎉 DONE! Updates applied.")
    print("⚠️  ACTION REQUIRED:")
    print("   1. Stop your node server (Ctrl+C).")
    print("   2. Start your node server (node server.js).")
    print("   3. Hard refresh your browser (Ctrl+Shift+R).")
    print("   4. Go to Admin -> Security Tab to find the new button.")