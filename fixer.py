#!/usr/bin/env python3
"""
fix_button.py - Injects the missing Purple Batch Upload button into the Admin header
"""

def fix_button():
    with open('index.html', 'r', encoding='utf-8') as f:
        content = f.read()

    # This is the exact button currently in your HTML
    target = '<button class="admin-btn admin-btn-secondary" id="btnExportCsv" onclick="exportCSV()">Export CSV</button>'
    
    # This is our new purple button
    new_btn = '<button class="admin-btn" onclick="openBatchUpload()" style="background:var(--accent-purple); color:white; border:none; box-shadow:0 4px 15px rgba(123, 45, 142, 0.4);">Batch Upload</button>'

    if "openBatchUpload()" not in target and target in content:
        if "Batch Upload" not in content[:content.find(target) + 200]: # Ensure we don't add it twice
            content = content.replace(target, new_btn + '\n        ' + target)
            with open('index.html', 'w', encoding='utf-8') as f:
                f.write(content)
            print("✅ FIXED: Purple Batch Upload button added to the header!")
            return

    print("ℹ️ Button already exists or target not found.")

if __name__ == '__main__':
    fix_button()