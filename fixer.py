#!/usr/bin/env python3
"""
fix_sound_ui.py - Adds a massive Tap-to-Unmute overlay to bypass browser audio blockers.
"""

import re

def fix_sound():
    with open('index.html', 'r', encoding='utf-8') as f:
        content = f.read()

    modified = False

    # 1. INJECT THE UNMUTE OVERLAY HTML INSIDE THE VIDEO PLAYER
    target_html = '<button id="skipIntroBtn" class="skip-intro-btn">'
    overlay_html = """
    <div id="unmuteOverlay" style="position: absolute; top: 0; left: 0; right: 0; bottom: 0; z-index: 15; display: none; align-items: center; justify-content: center; cursor: pointer; background: rgba(0,0,0,0.3);" onclick="forceUnmute()">
        <div style="padding: 15px 30px; font-size: 1.5rem; background: var(--primary-gold); color: var(--navy-dark); font-weight: bold; border-radius: 50px; box-shadow: 0 4px 20px rgba(0,0,0,0.8); pointer-events: none;">🔊 Tap Anywhere for Sound</div>
    </div>
    <button id="skipIntroBtn" class="skip-intro-btn" style="z-index: 20;">"""
    
    if "unmuteOverlay" not in content and target_html in content:
        content = content.replace(target_html, overlay_html)
        print("✅ Added Full-Screen Tap-to-Unmute HTML")
        modified = True

    # 2. ADD THE FORCE UNMUTE JS LOGIC
    force_unmute_js = """
  // ═══════════════════════════════════════════════════════════════════════════════
  // INTRO VIDEO
  // ═══════════════════════════════════════════════════════════════════════════════
  
  window.forceUnmute = function() {
      const video = document.getElementById('introVideo');
      const overlay = document.getElementById('unmuteOverlay');
      if (video) {
          video.muted = false;
          video.currentTime = 0; // Restart from the beginning so they hear it all
      }
      if (overlay) overlay.style.display = 'none';
  };

  async function initIntroVideo() {
    const overlay = document.getElementById('introVideoOverlay');
    const video = document.getElementById('introVideo');
    const skipBtn = document.getElementById('skipIntroBtn');
    const unmuteOverlay = document.getElementById('unmuteOverlay');
    
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
      // 1. Try to autoplay WITH sound (works if user has visited site before)
      video.muted = false; 
      await video.play();
      if (unmuteOverlay) unmuteOverlay.style.display = 'none';
    } catch (err) {
      // 2. Browser blocked sound. Play muted, and show the Tap-to-Unmute screen
      video.muted = true;
      try {
        await video.play();
        if (unmuteOverlay) unmuteOverlay.style.display = 'flex';
      } catch (err2) { 
        skipIntro(); 
      }
    }
    
    video.onended = () => skipIntro();
    video.onerror = () => skipIntro();
    if (skipBtn) { 
        skipBtn.onclick = (e) => { e.stopPropagation(); skipIntro(); };
        if (state.settings.introHideSkip) skipBtn.style.display = 'none'; 
    }
  }
"""

    # Replace the old initIntroVideo function
    if "window.forceUnmute" not in content:
        pattern = re.compile(r'// ════.*?INTRO VIDEO.*?async function initIntroVideo\(\).*?(?=function skipIntro\(\))', re.DOTALL)
        if pattern.search(content):
            content = pattern.sub(force_unmute_js.strip() + "\n\n  ", content)
            print("✅ Upgraded Javascript for Tap-to-Unmute logic")
            modified = True

    if modified:
        with open('index.html', 'w', encoding='utf-8') as f:
            f.write(content)
        print("\n🎉 DONE! The video will now guarantee a way to turn on the sound.")
        print("⚠️ IMPORTANT: Please Hard-Refresh your browser (Ctrl+Shift+R)!")
    else:
        print("ℹ️ Code is already patched.")

if __name__ == '__main__':
    fix_sound()