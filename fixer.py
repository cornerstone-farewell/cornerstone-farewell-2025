import re
import os

def fix_loading_behavior(filepath="index.html"):
    if not os.path.exists(filepath):
        print(f"❌ Error: Could not find '{filepath}'.")
        return

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        # 1. Rewrite the auto-loader to fetch ALL pages immediately upon page load
        new_autofill_logic = """async function autoFillMemoriesOnLoad() {
    let safety = 0;
    // Force load all pages sequentially until the server says no more memories
    while (state.memHasMore && safety < 100) {
        safety++;
        await loadMemories(false);
    }
}"""
        
        # Safely find and replace the old constrained autoFill function
        content = re.sub(
            r'async function autoFillMemoriesOnLoad\(\)\s*\{[\s\S]*?(?:safety\s*\+=\s*1|safety\+\+);[\s\S]*?await loadMemories\(false\);\s*\}\s*\}',
            new_autofill_logic,
            content,
            flags=re.IGNORECASE
        )

        # 2. Disable the "dumb" scroll event listener that checked the bottom of the page
        content = re.sub(
            r"window\.addEventListener\('scroll', debounce\(async \(\) => \{[\s\S]*?pageHeight - 1000[\s\S]*?\}, 200\)\);",
            "// Scroll listener removed; all images load automatically now.",
            content,
            flags=re.IGNORECASE
        )

        # 3. Hide the "Infinite Scroll" toggle button from the UI (since it's not needed anymore)
        content = re.sub(
            r'<button class="filter-btn" id="toggleInfiniteBtn"[^>]*>.*?</button>',
            '<!-- Infinite Scroll Toggle Removed -->',
            content,
            flags=re.IGNORECASE
        )

        # Save the updated file
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

        print("✅ Success! The dumb scroll behavior has been eradicated.")
        print(" ➔ All images will now load sequentially and automatically the moment the page opens.")
        print(" ➔ Useless scroll listener removed.")
        print("\nRefresh your webpage (Ctrl+F5) to see it in action!")

    except Exception as e:
        print(f"❌ Error while editing the file: {e}")

if __name__ == "__main__":
    fix_loading_behavior("index.html")