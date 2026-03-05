#!/usr/bin/env python3
"""Quick fix for compilations tab not showing"""

import re

def fix_html():
    with open('index.html', 'r', encoding='utf-8') as f:
        content = f.read()
    
    modified = False
    
    # 1. Fix switchAdminTab to include 'compilations'
    old_tabs = "['moderation', 'settings', 'theme', 'users', 'security']"
    new_tabs = "['moderation', 'settings', 'theme', 'users', 'compilations', 'security']"
    
    if old_tabs in content:
        content = content.replace(old_tabs, new_tabs)
        modified = True
        print("✅ Fixed switchAdminTab array")
    
    # 2. Add tabCompilations if missing
    if 'id="tabCompilations"' not in content:
        # Find tabSecurity and add before it
        content = content.replace(
            '<div class="admin-tab" id="tabSecurity"',
            '<div class="admin-tab" id="tabCompilations" onclick="switchAdminTab(\'compilations\')">Compilations</div>\n        <div class="admin-tab" id="tabSecurity"'
        )
        modified = True
        print("✅ Added tabCompilations element")
    
    # 3. Add panelCompilations if missing
    if 'id="panelCompilations"' not in content:
        # Find panelSecurity and add before it
        content = content.replace(
            '<div class="admin-panel" id="panelSecurity"',
            '<div class="admin-panel" id="panelCompilations"></div>\n      <div class="admin-panel" id="panelSecurity"'
        )
        modified = True
        print("✅ Added panelCompilations element")
    
    if modified:
        with open('index.html', 'w', encoding='utf-8') as f:
            f.write(content)
        print("\n✅ index.html updated! Refresh your browser.")
    else:
        print("ℹ️  No changes needed or patterns not found.")
        print("   Check if your HTML structure matches expected patterns.")

if __name__ == '__main__':
    fix_html()