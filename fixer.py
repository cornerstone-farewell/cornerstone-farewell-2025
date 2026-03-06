#!/usr/bin/env python3
"""
fix_final_tweaks.py - Unmutes the video by default and fixes Compilation image limits.
"""

import re

def apply_fixes():
    with open('index.html', 'r', encoding='utf-8') as f:
        content = f.read()

    modified = False

    # 1. FIX THE VIDEO HTML (Remove 'muted' attribute)
    target_video = '<video id="introVideo" class="intro-video" autoplay muted playsinline></video>'
    replace_video = '<video id="introVideo" class="intro-video" autoplay playsinline></video>'
    
    if target_video in content:
        content = content.replace(target_video, replace_video)
        print("✅ Removed hardcoded 'muted' attribute from video tag")
        modified = True
    elif 'autoplay playsinline' in content:
        print("ℹ️ Video tag already unmuted")

    # 2. FIX THE COMPILATION LIMIT (Change to Admin API, Limit 5000)
    # We use regex to find the old fetch line because the limit number might vary
    old_fetch_pattern = re.compile(r"const res = await fetch\(apiUrl\('/api/memories\?limit=\d+'\)\);")
    
    new_fetch = """const res = await fetch(apiUrl('/api/admin/memories?limit=5000&filter=approved'), {
        headers: { 'Authorization': 'Bearer ' + state.adminToken }
      });"""

    if old_fetch_pattern.search(content):
        content = old_fetch_pattern.sub(new_fetch, content)
        print("✅ Upgraded Compilation selector to load up to 5000 images")
        modified = True
    elif 'limit=5000' in content:
        print("ℹ️ Compilation limit already upgraded")

    if modified:
        with open('index.html', 'w', encoding='utf-8') as f:
            f.write(content)
        print("\n🎉 DONE! Please Hard-Refresh your browser (Ctrl+Shift+R)!")
    else:
        print("\nℹ️ No changes made (Code already patched or targets not found).")

if __name__ == '__main__':
    apply_fixes()