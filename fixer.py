import re
from pathlib import Path

FILE = Path("index.html")


def backup(path: Path) -> Path:
    bak = path.with_name(path.name + ".video_fix_backup")
    bak.write_text(path.read_text(encoding="utf-8", errors="ignore"), encoding="utf-8")
    return bak


def replace_once(text: str, old: str, new: str) -> str:
    return text.replace(old, new, 1)


def fix_teacher_timeline_idx(text: str) -> str:
    text = text.replace('data-teacher-idx="${idx}{idx}"', 'data-teacher-idx="${idx}"')
    text = text.replace('data-timeline-idx="${idx}{idx}"', 'data-timeline-idx="${idx}"')
    return text


def fix_domcontentloaded_intro_call(text: str) -> str:
    old = """      await loadSettings(); applySettingsToUI(); applyThemeToCSS(); initCountdown(); updateFavicon(); initIntroVideo();
      renderTeachers(); renderTimeline(); await loadMemories(true);"""
    new = """      await loadSettings();
      applySettingsToUI();
      applyThemeToCSS();
      initCountdown();
      updateFavicon();
      renderTeachers();
      renderTimeline();
      await loadMemories(true);
      setTimeout(() => { initIntroVideo(); }, 50);"""
    if old in text:
        return text.replace(old, new)
    return text


def fix_intro_block(text: str) -> str:
    pattern = re.compile(
        r'window\.forceUnmute\s*=\s*function\(\)\s*\{.*?function\s+skipIntro\s*\(\)\s*\{.*?\n\}',
        re.DOTALL
    )

    replacement = """window.forceUnmute = function() {
  const video = document.getElementById('introVideo');
  const overlay = document.getElementById('unmuteOverlay');

  if (video) {
    video.muted = false;
    video.currentTime = 0;
    video.play().catch((e) => console.log('Play failed:', e));
  }

  if (overlay) {
    overlay.style.display = 'none';
  }
};

async function initIntroVideo() {
  const overlay = document.getElementById('introVideoOverlay');
  const video = document.getElementById('introVideo');
  const skipBtn = document.getElementById('skipIntroBtn');
  const unmuteOverlay = document.getElementById('unmuteOverlay');

  try {
    localStorage.removeItem('introSeen');
    sessionStorage.removeItem('introSeen');
  } catch (e) {}

  if (!overlay || !video) return;

  const introPath = state.settings?.introVideoPath;
  if (!introPath) {
    overlay.style.display = 'none';
    overlay.classList.add('hidden');
    return;
  }

  overlay.style.display = 'flex';
  overlay.classList.remove('hidden');
  overlay.style.opacity = '1';

  if (unmuteOverlay) {
    unmuteOverlay.style.display = 'none';
  }

  const src = mediaUrl(('/uploads/' + introPath).replace(/\\/+/g, '/'));

  video.pause();
  video.removeAttribute('src');
  video.load();
  video.src = src;
  video.currentTime = 0;
  video.load();

  video.onended = () => skipIntro();
  video.onerror = () => skipIntro();

  if (skipBtn) {
    skipBtn.onclick = (e) => {
      e.stopPropagation();
      skipIntro();
    };
    skipBtn.style.display = state.settings?.introHideSkip ? 'none' : '';
  }

  try {
    video.muted = false;
    await video.play();
    if (unmuteOverlay) unmuteOverlay.style.display = 'none';
  } catch (err) {
    try {
      video.muted = true;
      await video.play();
      if (unmuteOverlay) unmuteOverlay.style.display = 'flex';
    } catch (err2) {
      if (unmuteOverlay) unmuteOverlay.style.display = 'flex';
    }
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
    video.currentTime = 0;
  }
}"""

    return pattern.sub(replacement, text, count=1)


def main():
    if not FILE.exists():
        print("index.html not found")
        return

    bak = backup(FILE)
    text = FILE.read_text(encoding="utf-8", errors="ignore")

    text = fix_teacher_timeline_idx(text)
    text = fix_domcontentloaded_intro_call(text)
    text = fix_intro_block(text)

    FILE.write_text(text, encoding="utf-8")

    print("Patched index.html")
    print(f"Backup created: {bak.name}")


if __name__ == "__main__":
    main()