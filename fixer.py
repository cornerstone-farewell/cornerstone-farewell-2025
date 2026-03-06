import re
from pathlib import Path

INDEX = Path("index.html")


def backup(path: Path) -> Path:
    bak = path.with_suffix(path.suffix + ".bak")
    bak.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
    return bak


def remove_bad_global_video_play(html: str) -> str:
    html = re.sub(
        r'^\s*video\.play\(\)\.catch\(e\s*=>\s*console\.log\([^\n]*\)\);\s*//[^\n]*\n?',
        '',
        html,
        flags=re.MULTILINE
    )
    return html


def fix_skip_intro(html: str) -> str:
    pattern = re.compile(
        r'function\s+skipIntro\s*\(\)\s*\{.*?\n\s*\}',
        re.DOTALL
    )

    replacement = """function skipIntro() {
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
    video.currentTime = 0;
  }
}"""

    return pattern.sub(replacement, html, count=1)


def clear_intro_seen_flags(html: str) -> str:
    if 'localStorage.removeItem("introSeen")' in html or "localStorage.removeItem('introSeen')" in html:
        return html

    pattern = re.compile(r'(async\s+function\s+initIntroVideo\s*\(\)\s*\{)')
    replacement = r"""\1
  try {
    localStorage.removeItem('introSeen');
    sessionStorage.removeItem('introSeen');
  } catch (e) {}
"""
    return pattern.sub(replacement, html, count=1)


def main():
    if not INDEX.exists():
        print("index.html not found")
        return

    bak = backup(INDEX)
    html = INDEX.read_text(encoding="utf-8")

    html = remove_bad_global_video_play(html)
    html = fix_skip_intro(html)
    html = clear_intro_seen_flags(html)

    INDEX.write_text(html, encoding="utf-8")

    print(f"Fixed index.html")
    print(f"Backup created: {bak.name}")


if __name__ == "__main__":
    main()