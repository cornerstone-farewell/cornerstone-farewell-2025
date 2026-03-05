#!/usr/bin/env python3
"""
fix_css.py - Injects missing CSS and wires up Inline Editing for Admin Memories
"""

import os

def fix_html():
    with open('index.html', 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. THE MISSING CSS
    css_to_add = """
  /* ==================================================== */
  /* NEW FEATURE CSS (Compilations, Video, Inline Edit)   */
  /* ==================================================== */
  
  .intro-video-overlay { position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: #000; z-index: 9999; display: flex; align-items: center; justify-content: center; }
  .intro-video-overlay.hidden { display: none !important; }
  .intro-video { width: 100%; height: 100%; object-fit: cover; }
  .skip-intro-btn { position: absolute; top: 20px; right: 20px; padding: 12px 24px; background: rgba(255,255,255,0.15); border: 1px solid rgba(255,255,255,0.3); color: white; border-radius: 25px; cursor: pointer; font-family: var(--font-body); font-size: 0.95rem; backdrop-filter: blur(10px); transition: var(--transition-smooth); z-index: 10; }
  .skip-intro-btn:hover { background: rgba(255,255,255,0.25); transform: scale(1.05); }
  .toggle-intro-controls { position: absolute; bottom: 20px; right: 20px; padding: 10px 15px; background: rgba(0,0,0,0.5); border: none; color: white; border-radius: 50%; cursor: pointer; font-size: 1.2rem; }
  
  .compilation-player-overlay { position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: #000; z-index: 8000; display: none; align-items: center; justify-content: center; }
  .compilation-player-overlay.active { display: flex; }
  .compilation-slide { position: absolute; top: 0; left: 0; right: 0; bottom: 0; display: flex; align-items: center; justify-content: center; flex-direction: column; opacity: 0; transition: opacity 0.8s ease, transform 0.8s ease; pointer-events: none; }
  .compilation-slide.active { opacity: 1; pointer-events: auto; }
  .compilation-slide img { max-width: 90%; max-height: 80vh; object-fit: contain; border-radius: 12px; box-shadow: 0 20px 60px rgba(0,0,0,0.5); }
  .compilation-caption { position: absolute; bottom: 80px; left: 50%; transform: translateX(-50%); background: rgba(0,0,0,0.75); padding: 16px 32px; border-radius: 20px; color: white; font-size: 1.3rem; max-width: 85%; text-align: center; backdrop-filter: blur(10px); border: 1px solid rgba(255,255,255,0.1); }
  .compilation-nav-btn { position: absolute; top: 50%; transform: translateY(-50%); background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.2); color: white; width: 60px; height: 60px; border-radius: 50%; cursor: pointer; font-size: 1.5rem; transition: var(--transition-smooth); display: flex; align-items: center; justify-content: center; }
  .compilation-nav-btn:hover { background: var(--primary-gold); color: var(--navy-dark); }
  .compilation-prev { left: 30px; }
  .compilation-next { right: 30px; }
  .compilation-close { position: absolute; top: 20px; right: 20px; background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.2); color: white; width: 50px; height: 50px; border-radius: 50%; cursor: pointer; font-size: 1.3rem; display: flex; align-items: center; justify-content: center; }
  .compilation-close:hover { background: rgba(244,67,54,0.8); }
  .compilation-progress { position: absolute; bottom: 25px; left: 50%; transform: translateX(-50%); display: flex; gap: 10px; }
  .compilation-dot { width: 12px; height: 12px; background: rgba(255,255,255,0.3); border-radius: 50%; cursor: pointer; transition: var(--transition-smooth); }
  .compilation-dot:hover { background: rgba(255,255,255,0.6); }
  .compilation-dot.active { background: var(--primary-gold); transform: scale(1.3); }
  
  .compilation-slide.trans-slide { transform: translateX(100%); }
  .compilation-slide.trans-slide.active { transform: translateX(0); }
  .compilation-slide.trans-zoom { transform: scale(0.7); }
  .compilation-slide.trans-zoom.active { transform: scale(1); }
  .compilation-slide.trans-flip { transform: rotateY(90deg); }
  .compilation-slide.trans-flip.active { transform: rotateY(0); }
  .compilation-slide.trans-blur { filter: blur(20px); }
  .compilation-slide.trans-blur.active { filter: blur(0); }
  
  .compilation-modal { position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.9); z-index: 7000; display: none; align-items: flex-start; justify-content: center; padding: 40px 20px; overflow-y: auto; }
  .compilation-modal.active { display: flex; }
  .compilation-modal-content { background: var(--navy-medium); border: 1px solid var(--glass-border); border-radius: 20px; padding: 30px; max-width: 1200px; width: 100%; margin-top: 5vh; }
  .compilation-photo-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(120px, 1fr)); gap: 12px; max-height: 400px; overflow-y: auto; padding: 10px; background: rgba(0,0,0,0.2); border-radius: 12px; margin: 15px 0; }
  .compilation-photo-item { position: relative; aspect-ratio: 1; border-radius: 10px; overflow: hidden; cursor: pointer; border: 3px solid transparent; transition: var(--transition-smooth); }
  .compilation-photo-item:hover { border-color: rgba(212,175,55,0.5); }
  .compilation-photo-item.selected { border-color: var(--primary-gold); }
  .compilation-photo-item img { width: 100%; height: 100%; object-fit: cover; }
  .compilation-photo-item .photo-check { position: absolute; top: 5px; right: 5px; width: 24px; height: 24px; background: var(--primary-gold); border-radius: 50%; display: none; align-items: center; justify-content: center; color: var(--navy-dark); font-weight: bold; }
  .compilation-photo-item.selected .photo-check { display: flex; }
  
  .compilation-slides-preview { display: flex; gap: 12px; overflow-x: auto; padding: 15px 0; min-height: 120px; background: rgba(0,0,0,0.15); border-radius: 12px; margin: 15px 0; }
  .compilation-slide-preview { flex-shrink: 0; width: 100px; background: rgba(255,255,255,0.05); border: 1px solid var(--glass-border); border-radius: 10px; padding: 8px; cursor: grab; }
  .compilation-slide-preview img { width: 100%; aspect-ratio: 1; object-fit: cover; border-radius: 6px; }
  .compilation-slide-preview input { width: 100%; margin-top: 6px; padding: 4px; font-size: 0.75rem; background: rgba(0,0,0,0.3); border: 1px solid var(--glass-border); border-radius: 4px; color: white; }
  .compilation-slide-preview .remove-slide { display: block; width: 100%; margin-top: 4px; padding: 4px; background: rgba(244,67,54,0.3); border: none; border-radius: 4px; color: #ffb3ad; cursor: pointer; font-size: 0.7rem; }

  .inline-editable { cursor: pointer; border: 1px dashed transparent; padding: 2px 4px; border-radius: 4px; transition: var(--transition-smooth); }
  .inline-editable:hover { border-color: var(--primary-gold); background: rgba(212, 175, 55, 0.1); }
  .inline-editable.editing { background: rgba(255,255,255,0.1); border-color: var(--primary-gold); }
  .inline-edit-input { background: rgba(255,255,255,0.1); border: 1px solid var(--primary-gold); color: var(--text-light); padding: 4px 8px; border-radius: 6px; font-family: inherit; font-size: inherit; width: 100%; }
"""

    modified = False

    # Inject CSS securely before the very first </style> tag it finds
    if "compilation-player-overlay" not in content:
        content = content.replace("</style>", css_to_add + "\n</style>", 1)
        print("✅ Added missing CSS for Compilations, Video, and Inline Edit")
        modified = True

    # 2. ADD INLINE-EDIT HOOKS TO ADMIN CARDS
    target_name = '''class="admin-memory-name">${escapeHtml(memory.student_name || '')}</div>'''
    replace_name = '''class="admin-memory-name inline-editable" title="Double click to edit" ondblclick="this.setAttribute('data-memory-id', ${memory.id}); this.setAttribute('data-field', 'student_name'); startInlineEdit(this)">${escapeHtml(memory.student_name || '')}</div>'''
    
    if target_name in content:
        content = content.replace(target_name, replace_name)
        print("✅ Wired up inline-edit for Name")
        modified = True

    target_cap = '''class="admin-memory-caption">${escapeHtml(memory.caption || '')}</div>'''
    replace_cap = '''class="admin-memory-caption inline-editable" title="Double click to edit" ondblclick="this.setAttribute('data-memory-id', ${memory.id}); this.setAttribute('data-field', 'caption'); startInlineEdit(this)">${escapeHtml(memory.caption || '')}</div>'''
    
    if target_cap in content:
        content = content.replace(target_cap, replace_cap)
        print("✅ Wired up inline-edit for Caption")
        modified = True

    target_type = '''<span>${escapeHtml(memory.memory_type || '')}</span>'''
    replace_type = '''<span class="inline-editable" title="Double click to edit" ondblclick="this.setAttribute('data-memory-id', ${memory.id}); this.setAttribute('data-field', 'memory_type'); startInlineEdit(this)">${escapeHtml(memory.memory_type || '')}</span>'''
    
    if target_type in content:
        content = content.replace(target_type, replace_type)
        print("✅ Wired up inline-edit for Category")
        modified = True

    if modified:
        with open('index.html', 'w', encoding='utf-8') as f:
            f.write(content)
        print("\n🎉 DONE! Please refresh your browser (Ctrl+Shift+R).")
    else:
        print("ℹ️ Code is already patched.")

if __name__ == '__main__':
    fix_html()