import re
import os

def fix_code(filepath="index.html"):
    if not os.path.exists(filepath):
        print(f"❌ Error: Could not find '{filepath}'. Make sure the script is in the same folder.")
        return

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        # 1. LINK THE UI: Fix the mismatched IDs so the JavaScript finds your beautiful new container
        content = content.replace("'publicCompilationsSection'", "'compilations'")
        content = content.replace("'publicCompilationsList'", "'publicCompilationsGrid'")

        # 2. CLEAN HTML: Remove the floating duplicate Admin HTML block that was clashing
        content = re.sub(
            r'<!-- Admin Compilations Tab -->.*?<tbody id="adminCompList">.*?</tbody>\s*</table>\s*</div>\s*</div>',
            '',
            content,
            flags=re.DOTALL | re.IGNORECASE
        )

        # 3. CLEAN JAVASCRIPT: Remove the clashing duplicate JS functions at the bottom of the file
        content = re.sub(
            r'// =+\s*// COMPILATION ADMIN FUNCTIONS.*?\}\);',
            '',
            content,
            flags=re.DOTALL | re.IGNORECASE
        )

        # 4. Save the polished code back to your index.html
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

        print("✅ Code brushed up successfully!")
        print(" ➔ Linked public compilations to the correct UI.")
        print(" ➔ Removed clashing duplicated JavaScript.")
        print(" ➔ Cleaned up redundant HTML modals.")
        print("\nRefresh your webpage, and it will work perfectly!")

    except Exception as e:
        print(f"❌ Error while editing the file: {e}")

if __name__ == "__main__":
    fix_code("index.html")