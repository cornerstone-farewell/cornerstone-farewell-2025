#!/usr/bin/env python3
"""
add_video_ui.py - Adds the Intro Video Upload & Settings UI to the Admin Panel
"""

def add_ui():
    with open('index.html', 'r', encoding='utf-8') as f:
        content = f.read()

    modified = False

    # 1. Add the UI block inside renderSettingsPanelHtml
    target_html = '<div class="form-group"><label>Footer Copyright</label><input class="form-input" id="setFooterCopyright"/></div>'
    video_ui_html = """<div class="form-group"><label>Footer Copyright</label><input class="form-input" id="setFooterCopyright"/></div>
    <div style="margin-top:16px; border:1px solid var(--glass-border); border-radius:16px; padding:14px; background:rgba(255,255,255,0.03);">
      <h4 style="font-family:var(--font-display); color:var(--primary-gold); margin-bottom:10px;">Intro Video Settings</h4>
      <div style="display:grid; grid-template-columns: 1fr 1fr; gap: 12px; align-items: end;">
        <div class="form-group">
          <label>Upload Intro Video (MP4/WebM)</label>
          <input type="file" class="form-input" accept="video/mp4,video/webm" onchange="uploadIntroVideoFile(this.files[0])" style="padding: 6px;" />
          <div class="mini-pill" style="margin-top:6px; display:inline-block;" id="currentIntroVideoStatus"></div>
        </div>
        <div class="form-group">
          <label>Hide "Skip" Button?</label>
          <select class="form-select" id="setIntroHideSkip" style="margin-bottom: 6px;">
            <option value="false">false (Users can skip)</option>
            <option value="true">true (Forced to watch)</option>
          </select>
          <button class="admin-btn admin-btn-danger" style="width:100%; justify-content:center;" type="button" onclick="removeIntroVideo()">Remove Video (Disable)</button>
        </div>
      </div>
    </div>"""

    if "Intro Video Settings" not in content and target_html in content:
        content = content.replace(target_html, video_ui_html)
        print("✅ Added Intro Video UI to Settings Panel")
        modified = True

    # 2. Wire it up in syncSettingsEditor
    target_sync = "setVal('setFooterCopyright', s.footerCopyright);"
    sync_code = """setVal('setFooterCopyright', s.footerCopyright);
    setVal('setIntroHideSkip', String(!!s.introHideSkip));
    const vidStatus = document.getElementById('currentIntroVideoStatus');
    if (vidStatus) vidStatus.textContent = s.introVideoPath ? '🟢 Active: ' + s.introVideoPath : '🔴 No video uploaded (Disabled)';"""
    
    if "setIntroHideSkip" not in content and target_sync in content:
        content = content.replace(target_sync, sync_code)
        print("✅ Wired up UI synchronization")
        modified = True

    # 3. Wire it up in readSettingsFromEditor
    target_read = "s.footerCopyright = getVal('setFooterCopyright');"
    read_code = "s.footerCopyright = getVal('setFooterCopyright'); s.introHideSkip = getVal('setIntroHideSkip') === 'true';"
    
    if "s.introHideSkip =" not in content and target_read in content:
        content = content.replace(target_read, read_code)
        print("✅ Wired up settings saving")
        modified = True

    # 4. Add the Upload/Remove JavaScript functions
    js_funcs = """
    async function uploadIntroVideoFile(file) {
      if (!file) return;
      const fd = new FormData();
      fd.append('video', file);
      showNotification('info', 'Uploading...', 'Please wait.');
      try {
        const res = await fetch(apiUrl('/api/admin/upload-intro-video'), {
          method: 'POST',
          headers: { 'Authorization': `Bearer ${state.adminToken}` },
          body: fd
        });
        const data = await res.json();
        if (data.success) {
          showNotification('success', 'Uploaded', 'Intro video saved!');
          reloadSettingsAdmin();
        } else {
          showNotification('error', 'Failed', data.error || 'Upload failed');
        }
      } catch (e) {
        showNotification('error', 'Error', e.message);
      }
    }
    
    async function removeIntroVideo() {
      if (!confirm("Are you sure you want to remove the intro video? This will disable it.")) return;
      state.settings.introVideoPath = null;
      await saveSettingsFromEditor();
      reloadSettingsAdmin();
    }
    """
    
    if "async function uploadIntroVideoFile" not in content:
        # Insert right before the script tag closes
        content = content.replace("</script>", js_funcs + "\n</script>")
        print("✅ Added Video Upload JavaScript logic")
        modified = True

    if modified:
        with open('index.html', 'w', encoding='utf-8') as f:
            f.write(content)
        print("\n🎉 DONE! Please Hard-Refresh your browser (Ctrl+Shift+R).")
    else:
        print("ℹ️ UI already exists or targets not found.")

if __name__ == '__main__':
    add_ui()