#!/usr/bin/env python3
"""
patch_farewell_sniper_v5.py

Final blind-run patcher for the provided current repo state.

Fixes requested:
- No ghost popup while intro video is showing/loading
- Replaces fake map with proper spherical 3D globe using globe.gl from CDN
- Removes dropdown-based location picking for users
- User now clicks directly on the globe to place pins
- Supports two pin types:
  - 11th/12th future place
  - University aim place
- Stores student name + both selected coordinates
- Shows dots and connecting arcs from school origin to all student pins
- Production-style globe panel and better formatting
- Safer popup timing and stronger guards

Run:
    python patch_farewell_sniper_v5.py
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path


HTML_MARKER = "/* === SNIPER_PATCH_V5_START === */"
SERVER_MARKER = "// === SNIPER_SERVER_PATCH_V5_START ==="


INDEX_APPEND = r"""
<style>
/* === SNIPER_PATCH_V5_START === */
#distanceMapSection{
  background:
    radial-gradient(circle at 50% 0%, rgba(212,175,55,.12), transparent 32%),
    linear-gradient(180deg, #060a14 0%, #0d1730 60%, #081120 100%) !important;
}
#distanceMapWrap{
  min-height:760px !important;
  height:760px !important;
  position:relative !important;
  background:radial-gradient(circle at center, rgba(16,35,68,.45), rgba(3,7,15,.95)) !important;
}
#distanceRealMapFrame{
  display:none !important;
}
#distanceGlobeCanvas{
  position:absolute;
  inset:0;
  width:100%;
  height:100%;
}
#distanceGlobeUi{
  position:absolute;
  left:18px;
  right:18px;
  top:18px;
  z-index:8;
  display:flex;
  justify-content:space-between;
  gap:12px;
  flex-wrap:wrap;
  pointer-events:none;
}
#distanceGlobeUi > *{
  pointer-events:auto;
}
.distance-globe-card{
  background:rgba(0,0,0,.45);
  border:1px solid rgba(255,255,255,.12);
  border-radius:18px;
  backdrop-filter:blur(10px);
  color:#fff;
  padding:12px 14px;
}
#distancePickerCard{
  max-width:420px;
}
#distancePickerCard h4{
  margin:0 0 8px;
  font-family:var(--font-display);
  color:var(--primary-gold);
}
#distancePickerCard p{
  margin:0 0 10px;
  color:rgba(255,255,255,.82);
  font-size:.92rem;
  line-height:1.6;
}
.distance-mode-btns{
  display:flex;
  gap:8px;
  flex-wrap:wrap;
  margin-bottom:10px;
}
.distance-mode-btn{
  border:1px solid rgba(255,255,255,.16);
  background:rgba(255,255,255,.08);
  color:#fff;
  border-radius:999px;
  padding:8px 12px;
  cursor:pointer;
  font-size:.84rem;
}
.distance-mode-btn.active{
  background:var(--primary-gold);
  color:var(--navy-dark);
  border-color:var(--primary-gold);
  font-weight:700;
}
#distanceSelectedInfo{
  display:grid;
  gap:8px;
}
.distance-selected-row{
  font-size:.88rem;
  color:rgba(255,255,255,.88);
}
.distance-selected-row strong{
  color:var(--primary-gold-light);
}
#distanceNameInline{
  width:220px;
  max-width:100%;
}
#distanceMiniLegend{
  display:flex;
  gap:8px;
  flex-wrap:wrap;
  align-items:center;
}
.legend-pill{
  border-radius:999px;
  padding:7px 10px;
  background:rgba(255,255,255,.07);
  border:1px solid rgba(255,255,255,.12);
  font-size:.8rem;
}
#distanceOverlayStats{
  position:static !important;
  transform:none !important;
  display:flex;
  gap:8px;
  flex-wrap:wrap;
}
.distance-stat-pill{
  background:rgba(255,255,255,.07) !important;
  border:1px solid rgba(255,255,255,.12) !important;
}
#distanceMapWrap .globe-tooltip{
  color:#fff !important;
}
#distanceBottomActions{
  position:absolute;
  bottom:20px;
  left:50%;
  transform:translateX(-50%);
  z-index:8;
  display:flex;
  gap:10px;
  flex-wrap:wrap;
}
#distanceBottomActions .btn{
  box-shadow:0 10px 30px rgba(0,0,0,.35);
}
@media (max-width: 900px){
  #distanceMapWrap{
    min-height:640px !important;
    height:640px !important;
  }
  #distanceGlobeUi{
    top:12px;
    left:12px;
    right:12px;
  }
  #distanceBottomActions{
    width:calc(100% - 24px);
    left:12px;
    right:12px;
    transform:none;
    justify-content:center;
  }
}
/* === /SNIPER_PATCH_V5_START === */
</style>

<script src="https://unpkg.com/three@0.160.0/build/three.min.js"></script>
<script src="https://unpkg.com/globe.gl"></script>

<script>
/* === SNIPER_PATCH_V5_START === */
(function(){
  if (window.__SNIPER_PATCH_V5__) return;
  window.__SNIPER_PATCH_V5__ = true;

  const SCHOOL_ORIGIN = { lat: 12.9716, lng: 77.5946, label: 'Cornerstone International School' };

  const v5 = {
    globe: null,
    globeReady: false,
    pickingMode: 'school',
    pendingSchoolPoint: null,
    pendingUniversityPoint: null,
    popupShown: false,
    popupTimer: null
  };

  function bootV5(){
    patchPopupTimingV5();
    buildGlobeUi();
    patchDistanceSectionV5();
    patchAdminPlacesHelpTextV5();
  }

  function introActuallyVisible(){
    const overlay = document.getElementById('introVideoOverlay');
    if (!overlay) return false;
    const style = getComputedStyle(overlay);
    if (style.display === 'none' || style.visibility === 'hidden' || Number(style.opacity || '1') === 0) return false;
    return !overlay.classList.contains('hidden');
  }

  function patchPopupTimingV5(){
    const oldInstall = window.installScrollTriggeredPopups;
    if (typeof oldInstall === 'function' && !oldInstall.__v5Wrapped){
      window.installScrollTriggeredPopups = function(){
        const openMaybe = () => {
          if (v5.popupShown) return;
          if (introActuallyVisible()) return;
          const countdown = document.getElementById('countdown');
          if (!countdown) return;
          const rect = countdown.getBoundingClientRect();
          const crossed = rect.bottom < (window.innerHeight * 0.35);
          if (!crossed) return;
          v5.popupShown = true;
          setTimeout(() => {
            if (!introActuallyVisible()) document.getElementById('ghostCursorPopup')?.classList.add('active');
          }, 600);
          setTimeout(() => {
            if (!introActuallyVisible()) document.getElementById('paperTutorial')?.classList.add('active');
          }, 1900);
          window.removeEventListener('scroll', openMaybe);
        };
        window.addEventListener('scroll', openMaybe, { passive: true });
        v5.popupTimer = setInterval(() => {
          if (v5.popupShown) {
            clearInterval(v5.popupTimer);
            return;
          }
          openMaybe();
        }, 1200);
      };
      window.installScrollTriggeredPopups.__v5Wrapped = true;
    }

    const oldSkipIntro = window.skipIntro;
    if (typeof oldSkipIntro === 'function' && !oldSkipIntro.__v5Wrapped){
      window.skipIntro = function(){
        const out = oldSkipIntro.apply(this, arguments);
        setTimeout(() => {
          if (typeof window.installScrollTriggeredPopups === 'function') {
            try { window.installScrollTriggeredPopups(); } catch(_){}
          }
        }, 700);
        return out;
      };
      window.skipIntro.__v5Wrapped = true;
    }
  }

  function buildGlobeUi(){
    const wrap = document.getElementById('distanceMapWrap');
    if (!wrap || document.getElementById('distanceGlobeCanvas')) return;

    wrap.innerHTML = `
      <div id="distanceGlobeCanvas"></div>
      <div id="distanceGlobeUi">
        <div class="distance-globe-card" id="distancePickerCard">
          <h4>Click the Globe to Place Your Future</h4>
          <p>Type your name, pick which future point you are placing, then click anywhere on the globe to drop the pin exactly where you want it.</p>
          <input class="form-input" id="distanceNameInline" placeholder="Your name" maxlength="80" />
          <div class="distance-mode-btns" style="margin-top:10px;">
            <button type="button" class="distance-mode-btn active" id="pickSchoolBtn">Place 11th / 12th point</button>
            <button type="button" class="distance-mode-btn" id="pickUniversityBtn">Place university point</button>
          </div>
          <div id="distanceSelectedInfo">
            <div class="distance-selected-row"><strong>11th / 12th:</strong> <span id="distanceSchoolSelectedText">Not placed yet</span></div>
            <div class="distance-selected-row"><strong>University:</strong> <span id="distanceUniversitySelectedText">Not placed yet</span></div>
          </div>
        </div>
        <div class="distance-globe-card">
          <div id="distanceOverlayStats"></div>
          <div id="distanceMiniLegend" style="margin-top:8px;">
            <div class="legend-pill">Gold = School origin</div>
            <div class="legend-pill">Blue = 11th / 12th</div>
            <div class="legend-pill">Rose = University</div>
          </div>
        </div>
      </div>
      <div id="distanceBottomActions">
        <button class="btn btn-primary" type="button" id="saveDistancePinsBtn">Save My Future Path</button>
        <button class="btn btn-secondary" type="button" id="distanceRefreshBtnV5">Refresh Globe</button>
        <button class="btn btn-secondary" type="button" id="distanceOpenMapsBtn">Open Last Pin in Google Maps</button>
      </div>
    `;

    document.getElementById('pickSchoolBtn')?.addEventListener('click', () => setPickMode('school'));
    document.getElementById('pickUniversityBtn')?.addEventListener('click', () => setPickMode('university'));
    document.getElementById('saveDistancePinsBtn')?.addEventListener('click', savePickedPinsV5);
    document.getElementById('distanceRefreshBtnV5')?.addEventListener('click', () => loadClassPathsGlobeV5(true));
    document.getElementById('distanceOpenMapsBtn')?.addEventListener('click', openLastPinInMapsV5);

    initRealGlobeV5();
  }

  function setPickMode(mode){
    v5.pickingMode = mode;
    document.getElementById('pickSchoolBtn')?.classList.toggle('active', mode === 'school');
    document.getElementById('pickUniversityBtn')?.classList.toggle('active', mode === 'university');
  }

  function patchDistanceSectionV5(){
    const oldMove = window.moveAndUpgradeDistanceSection;
    if (typeof oldMove === 'function' && !oldMove.__v5Wrapped){
      window.moveAndUpgradeDistanceSection = function(){
        const out = oldMove.apply(this, arguments);
        setTimeout(() => {
          buildGlobeUi();
          loadClassPathsGlobeV5(false);
        }, 120);
        return out;
      };
      window.moveAndUpgradeDistanceSection.__v5Wrapped = true;
    }
    setTimeout(() => {
      buildGlobeUi();
      loadClassPathsGlobeV5(false);
    }, 400);
  }

  function patchAdminPlacesHelpTextV5(){
    const old = window.renderSettingsPanelHtml;
    if (typeof old !== 'function' || old.__v5Wrapped) return;
    window.renderSettingsPanelHtml = function(){
      let html = old.apply(this, arguments);
      html = html.replace(
        'One place per line. Use real place names only, like <strong>Delhi</strong>, <strong>Bangalore</strong>, <strongLondon</strong>, <strong>Toronto</strong>.',
        'One place per line. These are just suggestion labels for the future map system. Students will still place exact pinpoints directly on the globe.'
      );
      return html;
    };
    window.renderSettingsPanelHtml.__v5Wrapped = true;
  }

  function initRealGlobeV5(){
    const el = document.getElementById('distanceGlobeCanvas');
    if (!el || v5.globe) return;

    const globe = Globe()
      .globeImageUrl('https://unpkg.com/three-globe/example/img/earth-blue-marble.jpg')
      .bumpImageUrl('https://unpkg.com/three-globe/example/img/earth-topology.png')
      .backgroundImageUrl('https://unpkg.com/three-globe/example/img/night-sky.png')
      .atmosphereColor('#9cc8ff')
      .atmosphereAltitude(0.22)
      .arcColor(d => d.color)
      .arcStroke(0.9)
      .arcDashLength(0.35)
      .arcDashGap(0.18)
      .arcDashAnimateTime(2400)
      .pointAltitude(d => d.alt || 0.03)
      .pointRadius(d => d.radius || 0.28)
      .pointColor(d => d.color)
      .labelText(d => d.label)
      .labelLat(d => d.lat)
      .labelLng(d => d.lng)
      .labelSize(1.3)
      .labelDotRadius(0.35)
      .labelColor(() => '#ffffff')
      .onGlobeClick((coords) => {
        placePickedPoint(coords);
      });

    globe(el);
    globe.pointOfView({ lat: 18, lng: 20, altitude: 2.05 }, 0);
    globe.controls().autoRotate = true;
    globe.controls().autoRotateSpeed = 0.55;

    v5.globe = globe;
    v5.globeReady = true;
  }

  function placePickedPoint(coords){
    const lat = Number(coords?.lat);
    const lng = Number(coords?.lng);
    if (!Number.isFinite(lat) || !Number.isFinite(lng)) return;

    const pt = { lat, lng };
    if (v5.pickingMode === 'school'){
      v5.pendingSchoolPoint = pt;
      const t = document.getElementById('distanceSchoolSelectedText');
      if (t) t.textContent = `${lat.toFixed(2)}, ${lng.toFixed(2)}`;
      setPickMode('university');
    } else {
      v5.pendingUniversityPoint = pt;
      const t = document.getElementById('distanceUniversitySelectedText');
      if (t) t.textContent = `${lat.toFixed(2)}, ${lng.toFixed(2)}`;
    }

    renderPendingPreviewV5();
  }

  function renderPendingPreviewV5(){
    if (!v5.globeReady) return;
    const points = [
      { ...SCHOOL_ORIGIN, color: '#ffd84d', radius: 0.38, alt: 0.06, label: 'Cornerstone International School' }
    ];
    const arcs = [];

    if (v5.pendingSchoolPoint){
      points.push({ ...v5.pendingSchoolPoint, color: '#55b9ff', radius: 0.3, alt: 0.05, label: '11th / 12th future point' });
      arcs.push({ startLat: SCHOOL_ORIGIN.lat, startLng: SCHOOL_ORIGIN.lng, endLat: v5.pendingSchoolPoint.lat, endLng: v5.pendingSchoolPoint.lng, color: ['#55b9ff'] });
    }
    if (v5.pendingUniversityPoint){
      points.push({ ...v5.pendingUniversityPoint, color: '#ff7aa8', radius: 0.3, alt: 0.05, label: 'University dream point' });
      arcs.push({ startLat: SCHOOL_ORIGIN.lat, startLng: SCHOOL_ORIGIN.lng, endLat: v5.pendingUniversityPoint.lat, endLng: v5.pendingUniversityPoint.lng, color: ['#ff7aa8'] });
    }

    v5.globe.pointsData(points);
    v5.globe.arcsData(arcs);
  }

  async function savePickedPinsV5(){
    const studentName = document.getElementById('distanceNameInline')?.value?.trim();
    if (!studentName){
      return window.showNotification?.('error', 'Name needed', 'Enter your name before saving your pins.');
    }
    if (!v5.pendingSchoolPoint && !v5.pendingUniversityPoint){
      return window.showNotification?.('error', 'Place a pin', 'Click on the globe to place at least one future point.');
    }

    try{
      const res = await fetch(apiUrl('/api/destinations/pin-submit'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          studentName,
          schoolPoint: v5.pendingSchoolPoint,
          universityPoint: v5.pendingUniversityPoint
        })
      });
      const data = await res.json();
      if (!data.success){
        return window.showNotification?.('error', 'Could not save', data.error || 'Pin save failed.');
      }
      window.showNotification?.('success', 'Future pinned', 'Your path is now part of the class globe.');
      await loadClassPathsGlobeV5(true);
    }catch(e){
      window.showNotification?.('error', 'Could not save', e.message);
    }
  }

  function openLastPinInMapsV5(){
    const target = v5.pendingUniversityPoint || v5.pendingSchoolPoint;
    if (!target){
      return window.showNotification?.('info', 'No pin yet', 'Place a point on the globe first.');
    }
    const q = encodeURIComponent(`${target.lat},${target.lng}`);
    window.open(`https://www.google.com/maps/search/?api=1&query=${q}`, '_blank');
  }

  async function loadClassPathsGlobeV5(excite){
    try{
      const res = await fetch(apiUrl('/api/destinations/pin-submissions'));
      const data = await res.json();
      if (!data.success) return;
      renderSavedGlobeV5(data.submissions || []);
      renderSavedStatsV5(data.submissions || []);
      if (excite && window.showNotification){
        showNotification('info', 'The future is unfolding', 'The class globe is lighting up with new paths.');
      }
    }catch(_){}
  }

  function renderSavedStatsV5(rows){
    const box = document.getElementById('distanceOverlayStats');
    if (!box) return;
    const students = rows.length;
    const schoolPins = rows.filter(r => r.schoolPoint).length;
    const uniPins = rows.filter(r => r.universityPoint).length;
    box.innerHTML = `
      <div class="distance-stat-pill">${students} students plotted</div>
      <div class="distance-stat-pill">${schoolPins} school paths</div>
      <div class="distance-stat-pill">${uniPins} university dreams</div>
    `;
  }

  function renderSavedGlobeV5(rows){
    if (!v5.globeReady) return;
    const points = [
      { ...SCHOOL_ORIGIN, color: '#ffd84d', radius: 0.42, alt: 0.065, label: SCHOOL_ORIGIN.label }
    ];
    const arcs = [];

    rows.forEach(r => {
      if (r.schoolPoint && Number.isFinite(r.schoolPoint.lat) && Number.isFinite(r.schoolPoint.lng)){
        points.push({
          lat: r.schoolPoint.lat,
          lng: r.schoolPoint.lng,
          color: '#55b9ff',
          radius: 0.28,
          alt: 0.05,
          label: `${r.studentName} • 11th / 12th`
        });
        arcs.push({
          startLat: SCHOOL_ORIGIN.lat,
          startLng: SCHOOL_ORIGIN.lng,
          endLat: r.schoolPoint.lat,
          endLng: r.schoolPoint.lng,
          color: ['#55b9ff']
        });
      }
      if (r.universityPoint && Number.isFinite(r.universityPoint.lat) && Number.isFinite(r.universityPoint.lng)){
        points.push({
          lat: r.universityPoint.lat,
          lng: r.universityPoint.lng,
          color: '#ff7aa8',
          radius: 0.28,
          alt: 0.05,
          label: `${r.studentName} • University`
        });
        arcs.push({
          startLat: SCHOOL_ORIGIN.lat,
          startLng: SCHOOL_ORIGIN.lng,
          endLat: r.universityPoint.lat,
          endLng: r.universityPoint.lng,
          color: ['#ff7aa8']
        });
      }
    });

    if (v5.pendingSchoolPoint){
      points.push({ ...v5.pendingSchoolPoint, color: '#8be1ff', radius: 0.33, alt: 0.055, label: 'Unsaved 11th / 12th point' });
    }
    if (v5.pendingUniversityPoint){
      points.push({ ...v5.pendingUniversityPoint, color: '#ff9ebd', radius: 0.33, alt: 0.055, label: 'Unsaved university point' });
    }

    v5.globe.pointsData(points);
    v5.globe.arcsData(arcs);
  }

  if (document.readyState === 'loading'){
    document.addEventListener('DOMContentLoaded', bootV5);
  } else {
    bootV5();
  }
})();
</script>
"""

SERVER_APPEND = r"""

// === SNIPER_SERVER_PATCH_V5_START ===
(() => {
  if (global.__SNIPER_SERVER_PATCH_V5__) return;
  global.__SNIPER_SERVER_PATCH_V5__ = true;

  const destinationsPathV5 = path.join(databaseDir, 'destinations.json');

  function readDestinationsV5() {
    return safeReadJson(destinationsPathV5, { destinations: [], submissions: [], nextId: 1 });
  }
  function writeDestinationsV5(data) {
    safeWriteJson(destinationsPathV5, data);
  }

  app.post('/api/destinations/pin-submit', (req, res) => {
    try {
      const studentName = String(req.body?.studentName || '').trim().substring(0, 80);
      const schoolPoint = req.body?.schoolPoint || null;
      const universityPoint = req.body?.universityPoint || null;

      if (!studentName) return res.status(400).json({ success: false, error: 'studentName required' });

      const validPoint = (p) => p && Number.isFinite(Number(p.lat)) && Number.isFinite(Number(p.lng));

      if (!validPoint(schoolPoint) && !validPoint(universityPoint)) {
        return res.status(400).json({ success: false, error: 'At least one valid point is required' });
      }

      const db = readDestinationsV5();
      let existing = (db.submissions || []).find(x => String(x.studentName || '').trim().toLowerCase() === studentName.toLowerCase());

      const payload = {
        studentName,
        schoolPoint: validPoint(schoolPoint) ? { lat: Number(schoolPoint.lat), lng: Number(schoolPoint.lng) } : null,
        universityPoint: validPoint(universityPoint) ? { lat: Number(universityPoint.lat), lng: Number(universityPoint.lng) } : null,
        updatedAt: nowIso()
      };

      if (existing) {
        existing.studentName = payload.studentName;
        existing.schoolPoint = payload.schoolPoint;
        existing.universityPoint = payload.universityPoint;
        existing.updatedAt = payload.updatedAt;
      } else {
        db.submissions.push({
          id: db.nextId++,
          createdAt: nowIso(),
          ...payload
        });
      }

      if (db.submissions.length > 5000) db.submissions = db.submissions.slice(-5000);
      writeDestinationsV5(db);
      broadcast('destinations:pin-update', { studentName });
      res.json({ success: true });
    } catch (e) {
      res.status(500).json({ success: false, error: e.message });
    }
  });

  app.get('/api/destinations/pin-submissions', (req, res) => {
    try {
      const db = readDestinationsV5();
      res.json({ success: true, submissions: db.submissions || [] });
    } catch (e) {
      res.status(500).json({ success: false, error: e.message });
    }
  });

  console.log('SNIPER patch server v5 loaded.');
})();
"""


def find_repo_root(start: Path) -> Path:
    for base in [start] + list(start.parents):
        if (base / "index.html").exists() and (base / "server.js").exists():
            return base
    return start


def backup(path: Path) -> None:
    bak = path.with_suffix(path.suffix + ".bak_sniper_v5")
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