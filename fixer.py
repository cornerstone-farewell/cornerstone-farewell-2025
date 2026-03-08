#!/usr/bin/env python3
"""
patch_farewell_sniper_v6.py

Fix patch for the current repo state.

It addresses:
- Globe overlay cards covering the globe too much
- Moves overlay cards fully above the canvas area in a safer top bar layout
- Prevents duplicate ghost popup:
  - not during intro loading/video
  - not both before and after scroll
- After intro video ends, force scroll to top/home
- Adds stronger popup guards and disables previous popup behavior
- Keeps append-only idempotent patching

Run:
    python patch_farewell_sniper_v6.py
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path


HTML_MARKER = "/* === SNIPER_PATCH_V6_START === */"
SERVER_MARKER = "// === SNIPER_SERVER_PATCH_V6_START ==="


INDEX_APPEND = r"""
<style>
/* === SNIPER_PATCH_V6_START === */
#distanceMapWrap{
  margin-top:18px !important;
}
#distanceGlobeUi{
  position:relative !important;
  left:auto !important;
  right:auto !important;
  top:auto !important;
  transform:none !important;
  display:grid !important;
  grid-template-columns:minmax(280px, 430px) minmax(260px, 1fr);
  gap:12px !important;
  margin:0 auto 14px !important;
  max-width:1200px !important;
  pointer-events:auto !important;
  z-index:2 !important;
}
#distanceGlobeUi > *{
  min-width:0;
}
#distanceMapWrap .distance-globe-card{
  box-shadow:0 14px 30px rgba(0,0,0,.20);
}
#distanceMapWrap #distanceBottomActions{
  position:relative !important;
  left:auto !important;
  right:auto !important;
  bottom:auto !important;
  transform:none !important;
  margin:14px auto 0 !important;
  justify-content:center !important;
  z-index:2 !important;
}
#distanceMapWrap #distanceGlobeCanvas{
  position:relative !important;
  inset:auto !important;
  width:100% !important;
  height:650px !important;
  border-radius:24px;
  overflow:hidden;
}
#distanceMapWrap{
  display:flex !important;
  flex-direction:column !important;
  min-height:unset !important;
  height:auto !important;
  padding:0 0 16px !important;
}
#distanceOverlayStats{
  position:static !important;
  display:flex !important;
  flex-wrap:wrap !important;
  gap:8px !important;
}
#distanceMiniLegend{
  margin-top:10px !important;
}
@media (max-width: 980px){
  #distanceGlobeUi{
    grid-template-columns:1fr !important;
  }
  #distanceMapWrap #distanceGlobeCanvas{
    height:560px !important;
  }
}
/* === /SNIPER_PATCH_V6_START === */
</style>

<script>
/* === SNIPER_PATCH_V6_START === */
(function(){
  if (window.__SNIPER_PATCH_V6__) return;
  window.__SNIPER_PATCH_V6__ = true;

  const v6 = {
    popupTriggered: false,
    popupBound: false
  };

  function bootV6(){
    patchGhostPopupLogic();
    patchIntroReturnToTop();
    refineGlobeLayout();
  }

  function introOverlayVisibleV6(){
    const overlay = document.getElementById('introVideoOverlay');
    if (!overlay) return false;
    const cs = getComputedStyle(overlay);
    if (cs.display === 'none' || cs.visibility === 'hidden') return false;
    if (overlay.classList.contains('hidden')) return false;
    return true;
  }

  function refineGlobeLayout(){
    const wrap = document.getElementById('distanceMapWrap');
    const ui = document.getElementById('distanceGlobeUi');
    const canvas = document.getElementById('distanceGlobeCanvas');
    const actions = document.getElementById('distanceBottomActions');
    if (!wrap || !ui || !canvas || !actions) return;

    if (!ui.dataset.v6Fixed){
      ui.dataset.v6Fixed = '1';
      if (ui.parentElement === wrap) {
        wrap.parentNode.insertBefore(ui, wrap);
      }
    }
    if (!actions.dataset.v6Fixed){
      actions.dataset.v6Fixed = '1';
      if (actions.parentElement === wrap) {
        wrap.insertAdjacentElement('afterend', actions);
      }
    }
  }

  function patchGhostPopupLogic(){
    if (v6.popupBound) return;
    v6.popupBound = true;

    const ghostPopup = document.getElementById('ghostCursorPopup');
    const paperPopup = document.getElementById('paperTutorial');
    if (ghostPopup) ghostPopup.classList.remove('active');
    if (paperPopup) paperPopup.classList.remove('active');

    const originalInstall = window.installScrollTriggeredPopups;
    if (typeof originalInstall === 'function' && !originalInstall.__v6Wrapped){
      window.installScrollTriggeredPopups = function(){
        if (window.__sniperV6PopupInstalled) return;
        window.__sniperV6PopupInstalled = true;

        const tryShow = () => {
          if (v6.popupTriggered) return;
          if (introOverlayVisibleV6()) return;

          const countdown = document.getElementById('countdown');
          if (!countdown) return;

          const rect = countdown.getBoundingClientRect();
          const crossed = rect.bottom < window.innerHeight * 0.35;
          if (!crossed) return;

          v6.popupTriggered = true;
          setTimeout(() => {
            if (!introOverlayVisibleV6()) document.getElementById('ghostCursorPopup')?.classList.add('active');
          }, 500);
          setTimeout(() => {
            if (!introOverlayVisibleV6()) document.getElementById('paperTutorial')?.classList.add('active');
          }, 1700);

          window.removeEventListener('scroll', tryShow);
        };

        window.addEventListener('scroll', tryShow, { passive: true });
      };
      window.installScrollTriggeredPopups.__v6Wrapped = true;
    }

    const oldSetupGhost = window.setupGhostCursors;
    if (typeof oldSetupGhost === 'function' && !oldSetupGhost.__v6Wrapped){
      window.setupGhostCursors = function(){
        const out = oldSetupGhost.apply(this, arguments);
        document.getElementById('ghostCursorPopup')?.classList.remove('active');
        document.getElementById('paperTutorial')?.classList.remove('active');
        return out;
      };
      window.setupGhostCursors.__v6Wrapped = true;
    }

    const oldInitPaper = window.initPaperAirplanes;
    if (typeof oldInitPaper === 'function' && !oldInitPaper.__v6Wrapped){
      window.initPaperAirplanes = function(){
        const out = oldInitPaper.apply(this, arguments);
        document.getElementById('paperTutorial')?.classList.remove('active');
        return out;
      };
      window.initPaperAirplanes.__v6Wrapped = true;
    }
  }

  function patchIntroReturnToTop(){
    const oldSkip = window.skipIntro;
    if (typeof oldSkip === 'function' && !oldSkip.__v6Wrapped){
      window.skipIntro = function(){
        const out = oldSkip.apply(this, arguments);
        setTimeout(() => {
          try{
            window.scrollTo({ top: 0, behavior: 'auto' });
            location.hash = '#home';
          }catch(_){}
        }, 620);
        setTimeout(() => {
          if (typeof window.installScrollTriggeredPopups === 'function') {
            try { window.installScrollTriggeredPopups(); } catch(_){}
          }
        }, 900);
        return out;
      };
      window.skipIntro.__v6Wrapped = true;
    }

    const introVideo = document.getElementById('introVideo');
    if (introVideo && !introVideo.dataset.v6Bound){
      introVideo.dataset.v6Bound = '1';
      introVideo.addEventListener('ended', () => {
        setTimeout(() => {
          try{
            window.scrollTo({ top: 0, behavior: 'auto' });
            location.hash = '#home';
          }catch(_){}
        }, 650);
      });
    }
  }

  if (document.readyState === 'loading'){
    document.addEventListener('DOMContentLoaded', bootV6);
  } else {
    bootV6();
  }
})();
</script>
"""

SERVER_APPEND = r"""

// === SNIPER_SERVER_PATCH_V6_START ===
(() => {
  if (global.__SNIPER_SERVER_PATCH_V6__) return;
  global.__SNIPER_SERVER_PATCH_V6__ = true;
  console.log('SNIPER patch server v6 loaded.');
})();
"""


def find_repo_root(start: Path) -> Path:
    for base in [start] + list(start.parents):
        if (base / "index.html").exists() and (base / "server.js").exists():
            return base
    return start


def backup(path: Path) -> None:
    bak = path.with_suffix(path.suffix + ".bak_sniper_v6")
    if not bak.exists():
        shutil.copy2(path, bak)


def patch_html(path: Path) -> bool:
    text = path.read_text(encoding="utf-8", errors="replace")
    if HTML_MARKER in text:
        return False
    if "</body>" not in text:
        raise RuntimeError("index.html missing </body>")
    new_text = text.replace("</body>", INDEX_APPEND + "\n</body>")
    backup(path)
    path.write_text(new_text, encoding="utf-8", newline="\n")
    return True


def patch_server(path: Path) -> bool:
    text = path.read_text(encoding="utf-8", errors="replace")
    if SERVER_MARKER in text:
        return False
    pos = text.rfind("server.listen(")
    if pos == -1:
        raise RuntimeError("server.js missing server.listen")
    new_text = text[:pos] + SERVER_APPEND + "\n\n" + text[pos:]
    backup(path)
    path.write_text(new_text, encoding="utf-8", newline="\n")
    return True


def main() -> int:
    root = find_repo_root(Path.cwd())
    index_html = root / "index.html"
    server_js = root / "server.js"

    if not index_html.exists():
        print("ERROR: index.html not found", file=sys.stderr)
        return 1
    if not server_js.exists():
        print("ERROR: server.js not found", file=sys.stderr)
        return 1

    changed = []
    try:
        if patch_html(index_html):
            changed.append("index.html")
        if patch_server(server_js):
            changed.append("server.js")
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if changed:
        print("Patched:", ", ".join(changed))
    else:
        print("Already patched.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())