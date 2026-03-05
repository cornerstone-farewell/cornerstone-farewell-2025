#!/usr/bin/env python3
"""
fix_duplicates.py - Modifies backend to only check for duplicates among APPROVED memories.
"""

def fix_duplicate_logic():
    with open('server.js', 'r', encoding='utf-8') as f:
        content = f.read()
    
    modified = False

    # Fix 1: Public upload endpoint
    target_upload = "const exists = db.memories.find(m => m.sha256 === hash && !m.purgedAt);"
    replace_upload = "const exists = db.memories.find(m => m.sha256 === hash && m.approved === 1 && !m.deletedAt && !m.purgedAt);"
    
    if target_upload in content:
        content = content.replace(target_upload, replace_upload)
        print("✅ Fixed duplicate check in public upload endpoint")
        modified = True

    # Fix 2: Admin replace file endpoint (to be consistent)
    target_replace = "const exists = db.memories.find(x => x.sha256 === hash && x.id !== id && !x.purgedAt);"
    replace_replace = "const exists = db.memories.find(x => x.sha256 === hash && x.id !== id && x.approved === 1 && !x.deletedAt && !x.purgedAt);"
    
    if target_replace in content:
        content = content.replace(target_replace, replace_replace)
        print("✅ Fixed duplicate check in admin replace-file endpoint")
        modified = True

    if modified:
        with open('server.js', 'w', encoding='utf-8') as f:
            f.write(content)
        print("\n🎉 DONE! Backend modified.")
        print("⚠️  IMPORTANT: Since this is a backend change, you MUST restart your Node.js server!")
        print("   Press Ctrl+C to stop the server, then run: node server.js")
    else:
        print("ℹ️ Code is already patched or targets not found.")

if __name__ == '__main__':
    fix_duplicate_logic()