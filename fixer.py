import os
import re
from pathlib import Path

INDEX_FILE = Path("index.html")


def backup_file(path: Path) -> Path:
    backup = path.with_suffix(path.suffix + ".bak")
    backup.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
    return backup


def fix_skip_intro_block(html: str) -> str:
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

    if pattern.search(html):
        return pattern.sub(replacement, html, count=1)
    return html


def fix_intro_autoplay_fallback(html: str) -> str:
    broken = """} catch (err2) { if (unmuteOverlay) { unmuteOverlay.style.display = "flex"; unmuteOverlay.innerHTML = "<div style=\\"padding: 15px 30px; font-size: 1.5rem; background: var(--primary-gold); color: var(--navy-dark); font-weight: bold; border-radius: 50px; box-shadow: 0 4px 20px rgba(0,0,0,0.8); pointer-events: none;\\">Tap to Play Intro</div>"; } }"""
    fixed = """} catch (err2) {
 if (unmuteOverlay) {
 unmuteOverlay.style.display = 'flex';
 }
 }"""
    return html.replace(broken, fixed)


def ensure_force_unmute_is_clean(html: str) -> str:
    pattern = re.compile(
        r'window\.forceUnmute\s*=\s*function\s*\(\)\s*\{.*?\n\};',
        re.DOTALL
    )
    replacement = """window.forceUnmute = function() {
 const video = document.getElementById('introVideo');
 const overlay = document.getElementById('unmuteOverlay');
 if (video) {
 video.muted = false;
 video.currentTime = 0;
 video.play().catch(e => console.log('Play failed:', e));
 }
 if (overlay) overlay.style.display = 'none';
};"""
    if pattern.search(html):
        return pattern.sub(replacement, html, count=1)
    return html


def main():
    if not INDEX_FILE.exists():
        print("index.html not found in current directory")
        return

    backup = backup_file(INDEX_FILE)
    html = INDEX_FILE.read_text(encoding="utf-8")

    original = html
    html = fix_skip_intro_block(html)
    html = fix_intro_autoplay_fallback(html)
    html = ensure_force_unmute_is_clean(html)

    if html == original:
        print("No matching broken patch found. Backup created at:", backup.name)
    else:
        INDEX_FILE.write_text(html, encoding="utf-8")
        print("Patched index.html successfully")
        print("Backup created:", backup.name)


if __name__ == "__main__":
    main()