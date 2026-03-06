#!/usr/bin/env python3
"""
fix_syntax_error.py - Repairs the corrupted skipIntro and Compilation Timer functions
"""

import re

def fix_syntax():
    with open('index.html', 'r', encoding='utf-8') as f:
        content = f.read()

    # The clean, perfectly formatted version of the Video + Player code
    clean_code = """
  // ═══════════════════════════════════════════════════════════════════════════════
  // INTRO VIDEO
  // ═══════════════════════════════════════════════════════════════════════════════
  
  async function initIntroVideo() {
    console.log("🎬 [VIDEO] Initializing smart video player...");
    
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
    
    const safePath = ('/uploads/' + introPath).replace('//', '/');
    video.src = mediaUrl(safePath);
    
    try {
      video.muted = false; 
      await video.play();
      console.log("🎬 [VIDEO] Playing with sound successfully!");
      if (unmuteBtn) unmuteBtn.style.display = 'none';
    } catch (err) {
      console.warn("⚠️ [VIDEO] Browser blocked sound autoplay. Falling back to muted mode.");
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
      } catch (err2) {
        console.error("❌ [VIDEO] Failed completely:", err2);
        skipIntro();
      }
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
      setTimeout(() => { 
        overlay.style.display = 'none'; 
        overlay.classList.add('hidden'); 
      }, 500);
    }
    if (video) {
        video.pause();
        video.src = "";
    }
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
    
    if (compilationTimer) clearTimeout(compilationTimer);
    
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
"""

    # We will locate the broken block using regex boundaries
    # From "async function initIntroVideo()" down to just before "function nextCompilationSlide()"
    start_match = re.search(r'async function initIntroVideo\(\)', content)
    end_match = re.search(r'function nextCompilationSlide\(\)\s*\{', content)

    if start_match and end_match:
        # Move start_idx back a bit to catch the comments
        start_idx = content.rfind('// ════', 0, start_match.start())
        if start_idx == -1: start_idx = start_match.start()
        
        end_idx = end_match.start()
        
        # Splice the clean code into the file
        new_content = content[:start_idx] + clean_code.strip() + '\n  function nextCompilationSlide() {' + content[end_idx + len('function nextCompilationSlide() {'):]
        
        with open('index.html', 'w', encoding='utf-8') as f:
            f.write(new_content)
            
        print("✅ Successfully repaired the corrupted JavaScript block!")
        print("⚠️ ACTION REQUIRED: Hard-Refresh your browser (Ctrl+Shift+R).")
    else:
        print("❌ Could not find the boundaries. Please ensure you didn't manually delete 'initIntroVideo' or 'nextCompilationSlide'.")

if __name__ == '__main__':
    fix_syntax()