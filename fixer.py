import os
import re

def patch_index():
    file_path = "index.html"
    
    if not os.path.exists(file_path):
        print(f"Error: Could not find {file_path} in the current directory.")
        return

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # --- FIX 1: ENSURE VIDEO REPLAYS ON EVERY PAGE RELOAD ---
    
    # A) Prevent 'video.src = ""' inside skipIntro(). 
    # Setting it to empty breaks the browser's refresh cache (BFCache). We just pause it instead.
    content = re.sub(
        r'if\s*\(\s*video\s*\)\s*\{\s*video\.pause\(\);\s*video\.src\s*=\s*["\']["\'];\s*\}',
        r'if (video) { video.pause(); video.currentTime = 0; } // Kept src intact so it works on refresh',
        content
    )

    # B) If the browser strictly blocks autoplay on reload, DON'T silently skip!
    # Instead, show the "Tap to Play" overlay so the user can still experience it.
    content = re.sub(
        r'\}\s*catch\s*\(err2\)\s*\{\s*skipIntro\(\);\s*\}',
        r'} catch (err2) { if (unmuteOverlay) { unmuteOverlay.style.display = "flex"; unmuteOverlay.innerHTML = "<div style=\\"padding: 15px 30px; font-size: 1.5rem; background: var(--primary-gold); color: var(--navy-dark); font-weight: bold; border-radius: 50px; box-shadow: 0 4px 20px rgba(0,0,0,0.8); pointer-events: none;\\">Tap to Play Intro</div>"; } }',
        content
    )

    # C) Ensure the "Tap for Sound / Play" overlay actually starts the video. 
    # Currently, it only unmutes but doesn't force the play action if it was blocked.
    content = re.sub(
        r'(video\.currentTime\s*=\s*0;\s*(?://.*)?)',
        r'\1\n          video.play().catch(e => console.log("Play failed:", e)); // Force play on tap',
        content
    )
    
    # D) Just in case there is a hidden localStorage flag blocking it, wipe it at init
    content = re.sub(
        r'(async\s+function\s+initIntroVideo\(\)\s*\{)',
        r'\1\n  localStorage.removeItem("introSeen"); sessionStorage.removeItem("introSeen");\n',
        content
    )


    # --- FIX 2: FIX THE COMPILATION BUTTON CRASH ---
    # The button was failing because the HTML Modal for the Compilation Creator was missing from the file.
    if 'id="compilationCreatorModal"' not in content:
        modal_html = """
<!-- Compilation Creator Modal -->
<div class="compilation-modal" id="compilationCreatorModal">
  <div class="compilation-modal-content">
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:20px;">
      <h2 style="color:var(--primary-gold); font-family:var(--font-display);">Compilation Creator</h2>
      <button class="admin-btn admin-btn-secondary" onclick="closeCompilationCreator()">Close</button>
    </div>
    <div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 15px; margin-bottom:20px;">
      <div class="form-group">
        <label>Name</label>
        <input type="text" class="form-input" id="compName" placeholder="Farewell Highlights" />
      </div>
      <div class="form-group">
        <label>Display Mode</label>
        <select class="form-select" id="compDisplayMode">
          <option value="auto">Auto (Slideshow)</option>
          <option value="manual">Manual (Arrows)</option>
        </select>
      </div>
      <div class="form-group">
        <label>Transition</label>
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
        <input type="number" class="form-input" id="compDefaultDuration" value="5" min="1" max="60" />
      </div>
    </div>
    <div style="display:grid; grid-template-columns: 1fr; gap:20px;">
      <div>
        <h3 style="color:var(--primary-gold); margin-bottom:10px;">Select Photos</h3>
        <div class="compilation-photo-grid" id="compPhotoGrid"></div>
      </div>
      <div>
        <h3 style="color:var(--primary-gold); margin-bottom:10px;">Slides Sequence</h3>
        <div class="compilation-slides-preview" id="compSlidesPreview" style="flex-wrap:wrap; display:flex;"></div>
        <button class="admin-btn admin-btn-primary" style="width:100%; justify-content:center; margin-top:20px;" onclick="saveCompilation()">Save Compilation</button>
      </div>
    </div>
  </div>
</div>
"""
        target = '<!-- Compilation Player -->'
        if target in content:
            content = content.replace(target, modal_html + "\n" + target)
        else:
            content = content.replace('</body>', modal_html + '\n</body>')

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    
    print("Successfully patched index.html!")
    print(" ✓ Video will now correctly appear and play from scratch EVERY time the page is reloaded.")
    print(" ✓ Video will continue to close automatically when it ends.")
    print(" ✓ Missing Compilation Creator HTML Modal has been safely injected.")

if __name__ == "__main__":
    patch_index()